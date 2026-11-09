"""Tests for the joystick backend layer and the mock (hardware-free) backend.

None of these need a physical joystick or pygame: they drive the mock
backend and the shared event translator directly.
"""
import os
import sys
import threading
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from utils import joystick_backend as jb
from utils.joystick_backend import JoyEvent, MockBackend, translate_event

FIXTURES = os.path.join(ROOT, "tests", "fixtures", "mock_devices")
HOTAS = os.path.join(FIXTURES, "vkb_gladiator_twcs.json")
RECORDED = os.path.join(FIXTURES, "recorded_session.json")


class TestTranslateEvent(unittest.TestCase):

    def test_button_press_is_one_based(self):
        self.assertEqual(translate_event(JoyEvent("button", 0, 4, 1)),
                         ("js1_button5", "Joystick 1 Button 5"))

    def test_button_release_is_ignored(self):
        self.assertIsNone(translate_event(JoyEvent("button", 0, 4, 0)))

    def test_hat_directions(self):
        cases = {(0, 1): "up", (0, -1): "down", (1, 0): "right", (-1, 0): "left"}
        for value, direction in cases.items():
            code, _ = translate_event(JoyEvent("hat", 1, 0, value))
            self.assertEqual(code, f"js2_hat1_{direction}")

    def test_hat_center_is_ignored(self):
        self.assertIsNone(translate_event(JoyEvent("hat", 0, 0, (0, 0))))

    def test_axis_names(self):
        code, desc = translate_event(JoyEvent("axis", 0, 3, -0.9), {})
        self.assertEqual(code, "js1_rotz")
        self.assertIn("(-)", desc)
        self.assertEqual(translate_event(JoyEvent("axis", 0, 9, 1.0), {})[0], "js1_axis9")

    def test_axis_below_threshold_is_ignored(self):
        self.assertIsNone(translate_event(JoyEvent("axis", 0, 0, 0.3), {}))

    def test_axis_fires_once_per_threshold_crossing(self):
        state = {}
        self.assertIsNotNone(translate_event(JoyEvent("axis", 0, 0, 0.8), state))
        self.assertIsNone(translate_event(JoyEvent("axis", 0, 0, 0.9), state))
        self.assertIsNone(translate_event(JoyEvent("axis", 0, 0, 0.1), state))
        self.assertIsNotNone(translate_event(JoyEvent("axis", 0, 0, -0.7), state))

    def test_ignored_inputs_are_filtered(self):
        self.assertIsNone(translate_event(JoyEvent("button", 0, 0, 1), ignored={"js1_button1"}))


class TestMockBackend(unittest.TestCase):

    def tearDown(self):
        jb.set_backend(None)
        os.environ.pop(jb.ENV_VAR, None)

    def test_devices_from_fixture_carry_vid_pid(self):
        backend = MockBackend.from_file(HOTAS)
        infos = backend.list_joysticks()
        self.assertEqual([i.vid_pid for i in infos], [(0x231D, 0x0200), (0x044F, 0xB687)])
        devices = jb.joystick_infos_to_devices(infos)
        self.assertEqual(devices[1]["instance"], 2)
        self.assertEqual(devices[1]["type"], "joystick")

    def test_injected_events_are_polled_once(self):
        backend = MockBackend.from_file(HOTAS)
        backend.open()
        backend.inject(JoyEvent("button", 1, 2, 1))
        self.assertEqual(backend.poll(), [JoyEvent("button", 1, 2, 1)])
        self.assertEqual(backend.poll(), [])

    def test_open_drops_stale_clicks(self):
        backend = MockBackend.from_file(HOTAS)
        backend.inject(JoyEvent("button", 0, 0, 1))
        backend.open()
        self.assertEqual(backend.poll(), [])

    def test_inject_rejects_unknown_stick(self):
        backend = MockBackend.from_file(HOTAS)
        with self.assertRaises(ValueError):
            backend.inject(JoyEvent("button", 5, 0, 1))

    def test_env_var_selects_mock(self):
        os.environ[jb.ENV_VAR] = HOTAS
        jb.set_backend(None)
        self.assertTrue(jb.get_backend().is_mock)

    def test_env_var_one_uses_default_preset(self):
        os.environ[jb.ENV_VAR] = "1"
        jb.set_backend(None)
        self.assertEqual(jb.get_backend().source, jb.DEFAULT_MOCK_DEVICES)

    def test_missing_devices_file_falls_back_to_pygame(self):
        os.environ[jb.ENV_VAR] = os.path.join(FIXTURES, "does_not_exist.json")
        jb.set_backend(None)
        self.assertIsInstance(jb.get_backend(), jb.PygameBackend)

    def test_no_env_var_means_pygame(self):
        jb.set_backend(None)
        self.assertIsInstance(jb.get_backend(), jb.PygameBackend)

    def test_cli_flag_is_stripped_from_argv(self):
        argv = ["main.py", "--mock-joysticks", HOTAS, "--other"]
        self.assertEqual(jb.configure_from_argv(argv), HOTAS)
        self.assertEqual(argv, ["main.py", "--other"])
        self.assertEqual(os.environ[jb.ENV_VAR], HOTAS)

    def test_cli_flag_without_path_uses_default(self):
        argv = ["main.py", "--mock-joysticks"]
        self.assertEqual(jb.configure_from_argv(argv), jb.DEFAULT_MOCK_DEVICES)
        self.assertEqual(argv, ["main.py"])

    def test_backend_is_shared_across_import_spellings(self):
        from src.utils import joystick_backend as other
        mock = MockBackend.from_file(HOTAS)
        other.set_backend(mock)
        self.assertIs(jb.get_backend(), mock)


class TestMockDevicesMatchProfile(unittest.TestCase):
    """The default preset should map onto its profile by VID/PID, exactly
    as real sticks would on the joystick machine."""

    def test_hotas_preset_matches_profile_js_slots(self):
        from utils.device_joystick_mapper import create_mapper_from_xml
        mapper = create_mapper_from_xml(os.path.join(ROOT, "example-profiles", "layout_HOTAS-SCPE.xml"))
        infos = MockBackend.from_file(HOTAS).list_joysticks()
        self.assertEqual(mapper.get_js_index_for_vid_pid(infos[0].vid_pid), "js1")
        self.assertEqual(mapper.get_js_index_for_vid_pid(infos[1].vid_pid), "js2")


class TestDetectorWithMock(unittest.TestCase):
    """Runs the real InputDetectorThread joystick loop against a recorded
    script, without starting Qt's event loop or touching hardware."""

    def setUp(self):
        try:
            from utils.input_detector import InputDetectorThread
        except ImportError as e:  # PyQt6 missing on this machine
            self.skipTest(f"PyQt6 unavailable: {e}")
        self.Thread = InputDetectorThread
        jb.set_backend(MockBackend.from_file(RECORDED))

    def tearDown(self):
        jb.set_backend(None)

    def _detect(self, ignored=()):
        detector = self.Thread(timeout_ms=2000)
        detector.ignored_inputs = set(ignored)
        detector.running = True
        found = threading.Event()
        result = {"code": None, "description": None}
        detector._detect_joystick(found, result)
        return found.is_set(), result["code"]

    def test_replay_reports_first_real_input(self):
        self.assertEqual(self._detect(), (True, "js2_hat1_up"))

    def test_replay_respects_ignored_inputs(self):
        self.assertEqual(self._detect(ignored={"js2_hat1_up"}), (True, "js1_button5"))

    def test_get_available_devices_uses_mock(self):
        from utils.input_detector import InputDetector
        names = [d["name"] for d in InputDetector.get_available_devices() if d["type"] == "joystick"]
        self.assertEqual(names, ["VKBsim Gladiator EVO R", "TWCS Throttle"])


if __name__ == "__main__":
    unittest.main()
