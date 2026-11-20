"""Tests for the Check Profile logic (utils.profile_checker) and the
system-device listing it compares against, using mock joysticks."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from utils import joystick_backend as jb
from utils.joystick_backend import JoystickInfo, MockBackend
from utils.profile_checker import check_profile, ERROR, WARNING, INFO
from utils.system_devices import list_system_joysticks, SOURCE_MOCK

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "profiles", "check_profile_problems.xml")
SWAPPED = os.path.join(ROOT, "tests", "fixtures", "mock_devices", "check_profile_swapped.json")
EXAMPLES = os.path.join(ROOT, "example-profiles")

FSM = (0x231D, 0x2220)
RUDDER = (0x231D, 0x011F)
EVO_L = (0x231D, 0x0201)


def stick(name, vid_pid, buttons=64, hats=2):
    return JoystickInfo(name=name, vid_pid=vid_pid, buttons=buttons, hats=hats, axes=6)


IN_PROFILE_ORDER = [stick("VKBSim NXT FSM.GA", FSM), stick("VKBSim T-Rudder", RUDDER),
                    stick("VKBsim Gladiator EVO L", EVO_L)]


def of(report, check, severity=None):
    return [f for f in report.findings if f.check == check and (severity is None or f.severity == severity)]


class TestProfileOnlyChecks(unittest.TestCase):
    """Checks that need only the XML (the four problems from the 2026-11-18 repair)."""

    @classmethod
    def setUpClass(cls):
        cls.report = check_profile(FIXTURE, None)

    def test_forced_press_on_view_action(self):
        found = of(self.report, "forced_press", WARNING)
        self.assertEqual([f.inputs for f in found], [["js3_hat1_down"]])
        self.assertIn("v_view_look_behind", found[0].title)

    def test_forced_press_on_hold_action_is_info(self):
        found = of(self.report, "forced_press", INFO)
        self.assertEqual(len(found), 1)
        self.assertIn("_hold", found[0].title)

    def test_cleared_view_actions_are_not_flagged_as_forced_press(self):
        titles = " ".join(f.title for f in of(self.report, "forced_press"))
        self.assertNotIn("yaw", titles)

    def test_partial_hat_with_cleared_view_actions_is_a_warning(self):
        found = of(self.report, "partial_hat")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, WARNING)
        self.assertEqual(found[0].inputs, ["js3_hat1_up", "js3_hat1_left", "js3_hat1_right"])
        self.assertIn("v_view_yaw_left", found[0].detail)

    def test_one_button_two_modes(self):
        found = of(self.report, "mode_switch_clash")
        self.assertEqual([f.inputs for f in found], [["js3_button27"]])
        self.assertIn("v_set_salvage_mode", found[0].detail)
        self.assertIn("v_toggle_mining_mode", found[0].detail)

    def test_set_and_toggle_of_the_same_mode_is_fine(self):
        self.assertNotIn(["js3_button29"], [f.inputs for f in of(self.report, "mode_switch_clash")])

    def test_tuning_under_old_device_id(self):
        warn = of(self.report, "stale_tuning", WARNING)
        self.assertEqual(len(warn), 1)
        self.assertIn("231D:0205", warn[0].title)
        self.assertIn("js3", warn[0].detail)
        info = of(self.report, "stale_tuning", INFO)
        self.assertEqual(len(info), 1)
        self.assertIn("T.16000M", info[0].title)

    def test_js1_never_cleared(self):
        self.assertEqual(len(of(self.report, "js1_defaults")), 1)

    def test_no_device_checks_without_system(self):
        self.assertFalse(of(self.report, "device_order"))
        self.assertFalse(of(self.report, "device_missing"))
        self.assertFalse(self.report.system_checked)

    def test_live_actionmaps_wrapper_is_read(self):
        """The live actionmaps.xml nests everything in <ActionProfiles>."""
        import tempfile
        with open(FIXTURE, encoding="utf-8") as f:
            body = f.read()
        body = body.replace("<ActionMaps ", "<ActionMaps>\n<ActionProfiles ", 1).replace(
            "profileName=\"CheckProfileProblems\"", "profileName=\"default\"", 1)
        body = body.replace("</ActionMaps>", "</ActionProfiles>\n</ActionMaps>")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "actionmaps.xml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            report = check_profile(path, IN_PROFILE_ORDER)
        self.assertEqual(len(of(report, "mode_switch_clash")), 1)
        self.assertEqual(len(of(report, "stale_tuning", WARNING)), 1)
        self.assertFalse(of(report, "device_order"))


class TestDeviceNumbering(unittest.TestCase):

    def test_matching_order_is_clean(self):
        report = check_profile(FIXTURE, IN_PROFILE_ORDER)
        self.assertFalse(of(report, "device_order"))
        self.assertFalse(of(report, "device_missing"))
        self.assertEqual([r.status for r in report.devices], ["ok", "ok", "ok"])

    def test_swapped_sticks_are_errors(self):
        system = [IN_PROFILE_ORDER[1], IN_PROFILE_ORDER[0], IN_PROFILE_ORDER[2]]
        report = check_profile(FIXTURE, system)
        errors = of(report, "device_order", ERROR)
        self.assertEqual(len(errors), 2)
        self.assertIn("FSM.GA is js1 in the profile but js2 on this PC", errors[0].title)
        self.assertIn("T-Rudder", errors[0].detail)
        self.assertEqual([r.status for r in report.devices], ["swapped", "swapped", "ok"])
        # Errors sort first.
        self.assertEqual(report.findings[0].severity, ERROR)

    def test_missing_stick(self):
        report = check_profile(FIXTURE, [IN_PROFILE_ORDER[0], IN_PROFILE_ORDER[1]])
        missing = of(report, "device_missing", WARNING)
        self.assertEqual(len(missing), 1)
        self.assertIn("EVO L", missing[0].title)
        self.assertEqual(report.devices[2].status, "missing")

    def test_extra_stick_shifts_the_rest(self):
        extra = stick("VPC MongoosT-50CM3", (0x3344, 0x0194))
        report = check_profile(FIXTURE, [extra] + IN_PROFILE_ORDER)
        self.assertEqual(len(of(report, "device_order", ERROR)), 3)
        self.assertEqual(len(of(report, "device_missing", INFO)), 1)

    def test_identical_sticks_are_noted(self):
        report = check_profile(FIXTURE, IN_PROFILE_ORDER + [stick("VKBsim Gladiator EVO L", EVO_L)])
        self.assertTrue(any("identical" in f.title for f in of(report, "device_order", INFO)))

    def test_bindings_on_inputs_the_stick_lacks(self):
        rudder = stick("VKBSim T-Rudder", RUDDER, buttons=0, hats=0)
        report = check_profile(FIXTURE, [IN_PROFILE_ORDER[0], rudder, IN_PROFILE_ORDER[2]])
        found = of(report, "no_such_input")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].inputs, ["js2_button3"])

    def test_bindings_on_a_slot_with_no_device(self):
        import tempfile
        with open(FIXTURE, encoding="utf-8") as f:
            body = f.read().replace('<rebind input="js1_button1"/>', '<rebind input="js4_button1"/>')
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "p.xml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            report = check_profile(path, IN_PROFILE_ORDER)
        found = of(report, "device_unknown")
        self.assertEqual(len(found), 1)
        self.assertIn("js4", found[0].title)


class TestWithMockJoysticks(unittest.TestCase):
    """The dialog's path: list_system_joysticks() + check_profile()."""

    def tearDown(self):
        jb.set_backend(None)

    def test_mock_backend_is_the_system(self):
        jb.set_backend(MockBackend.from_file(SWAPPED))
        system = list_system_joysticks()
        self.assertEqual(system.source, SOURCE_MOCK)
        self.assertTrue(system.exact_order)
        report = check_profile(FIXTURE, system.devices)
        self.assertEqual(len(of(report, "device_order", ERROR)), 2)
        # The rudder has no buttons, but js2 is already reported as swapped,
        # so its button binding isn't reported a second time.
        self.assertFalse(of(report, "no_such_input"))

    def test_mock_mirroring_the_profile_matches(self):
        jb.set_backend(MockBackend.from_path(FIXTURE))
        report = check_profile(FIXTURE, list_system_joysticks().devices)
        self.assertFalse(of(report, "device_order"))
        self.assertFalse(of(report, "device_missing"))


class TestExampleProfiles(unittest.TestCase):

    def test_every_example_profile_checks_without_crashing(self):
        for name in sorted(os.listdir(EXAMPLES)):
            if not name.endswith(".xml"):
                continue
            path = os.path.join(EXAMPLES, name)
            with self.subTest(profile=name):
                report = check_profile(path, MockBackend.from_path(path).list_joysticks())
                self.assertFalse(of(report, "device_order", ERROR))


if __name__ == "__main__":
    unittest.main()
