"""Tests for utils.profile_fixer: every fix Check Profile offers, applied to
the problem fixture, leaves a profile that checks clean for that problem."""
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from utils.joystick_backend import JoystickInfo
from utils.profile_checker import check_profile
from utils.profile_fixer import apply_fixes, FixError

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "profiles", "check_profile_problems.xml")
FSM = (0x231D, 0x2220)
RUDDER = (0x231D, 0x011F)
EVO_L = (0x231D, 0x0201)


def stick(name, vid_pid, buttons=64, hats=2):
    return JoystickInfo(name=name, vid_pid=vid_pid, buttons=buttons, hats=hats, axes=6)


IN_ORDER = [stick("FSM.GA", FSM), stick("T-Rudder", RUDDER), stick("EVO L", EVO_L)]
SWAPPED = [IN_ORDER[1], IN_ORDER[0], IN_ORDER[2]]


class FixerTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = os.path.join(self.tmp.name, "fixed.xml")

    def tearDown(self):
        self.tmp.cleanup()

    def fix(self, check, system=IN_ORDER, choices=None, path=FIXTURE):
        report = check_profile(path, system)
        fixes = [f.fix for f in report.findings if f.check == check and f.fix]
        self.assertTrue(fixes, f"no fix offered for {check}")
        changes = apply_fixes(path, fixes, self.out, choices)
        return changes, check_profile(self.out, system)

    def checks(self, report, check):
        return [f for f in report.findings if f.check == check]

    def rebinds(self, action):
        root = ET.parse(self.out).getroot()
        return [rb.attrib for a in root.iter("action") if a.get("name") == action for rb in a.findall("rebind")]

    def test_forced_press(self):
        _, after = self.fix("forced_press")
        self.assertFalse(self.checks(after, "forced_press"))
        self.assertEqual(self.rebinds("v_view_look_behind"), [{"input": "js3_hat1_down"}])

    def test_mode_switch_keep_one(self):
        changes, after = self.fix("mode_switch_clash", choices={0: "v_toggle_mining_mode"})
        self.assertFalse(self.checks(after, "mode_switch_clash"))
        self.assertEqual(self.rebinds("v_toggle_mining_mode"), [{"input": "js3_button27"}])
        self.assertEqual(self.rebinds("v_set_salvage_mode"), [{"input": "js3_ "}])
        self.assertIn("v_toggle_mining_mode", changes[0])

    def test_mode_switch_needs_a_choice(self):
        with self.assertRaises(FixError):
            self.fix("mode_switch_clash")

    def test_move_tuning(self):
        _, after = self.fix("stale_tuning")
        self.assertFalse([f for f in self.checks(after, "stale_tuning") if f.severity == "warning"])
        names = [d.get("name") for d in ET.parse(self.out).getroot().findall("deviceoptions")]
        self.assertTrue(any("{0201231D" in n for n in names))
        self.assertFalse(any("{0205231D" in n for n in names))

    def test_restore_hat(self):
        _, after = self.fix("partial_hat")
        self.assertEqual(self.rebinds("v_view_yaw_left"), [{"input": "js3_hat1_left"}])
        self.assertEqual(self.rebinds("v_view_yaw_right"), [{"input": "js3_hat1_right"}])
        hats = self.checks(after, "partial_hat")
        self.assertEqual([f.inputs for f in hats], [["js3_hat1_up"]])

    def test_unbind_missing_inputs(self):
        rudder = stick("T-Rudder", RUDDER, buttons=0, hats=0)
        _, after = self.fix("no_such_input", system=[IN_ORDER[0], rudder, IN_ORDER[2]])
        self.assertFalse(self.checks(after, "no_such_input"))
        self.assertEqual(self.rebinds("v_strafe_up"), [{"input": "js2_ "}])

    def test_renumber_to_match_this_pc(self):
        changes, after = self.fix("device_order", system=SWAPPED)
        self.assertFalse(self.checks(after, "device_order"))
        self.assertEqual([r.status for r in after.devices], ["ok", "ok", "ok"])
        # FSM.GA's binding followed it from js1 to js2, the rudder's the other way.
        self.assertEqual(self.rebinds("v_boost"), [{"input": "js2_button1"}])
        self.assertEqual(self.rebinds("v_strafe_up"), [{"input": "js1_button3"}])
        self.assertEqual(len(changes), 1)  # one renumber even though two findings carry it
        root = ET.parse(self.out).getroot()
        insts = [o.get("instance") for o in root.findall("options") if o.get("type") == "joystick"]
        self.assertEqual(len(insts), len(set(insts)))

    def test_renumber_not_offered_with_a_stick_missing(self):
        report = check_profile(FIXTURE, [IN_ORDER[1], IN_ORDER[0]])
        self.assertFalse([f for f in report.findings if f.fix and f.fix["kind"] == "renumber"])

    def test_fix_all_safe_then_clean(self):
        report = check_profile(FIXTURE, SWAPPED)
        safe = []
        for f in report.findings:
            if f.fix and f.fix.get("safe") and f.fix not in safe:
                safe.append(f.fix)
        apply_fixes(FIXTURE, safe, self.out)
        after = check_profile(self.out, SWAPPED)
        left = {f.check for f in after.findings if f.severity in ("error", "warning")}
        # Only the ones that need a choice from the user remain.
        self.assertEqual(left, {"mode_switch_clash", "partial_hat"})

    def test_original_file_untouched(self):
        with open(FIXTURE, "rb") as f:
            before = f.read()
        self.fix("forced_press")
        with open(FIXTURE, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_live_actionmaps_wrapper(self):
        with open(FIXTURE, encoding="utf-8") as f:
            body = f.read()
        body = body.replace("<ActionMaps ", "<ActionMaps>\n<ActionProfiles ", 1).replace(
            'profileName="CheckProfileProblems"', 'profileName="default"', 1)
        body = body.replace("</ActionMaps>", "</ActionProfiles>\n</ActionMaps>")
        live = os.path.join(self.tmp.name, "actionmaps.xml")
        with open(live, "w", encoding="utf-8") as f:
            f.write(body)
        _, after = self.fix("device_order", system=SWAPPED, path=live)
        self.assertFalse(self.checks(after, "device_order"))
        self.assertEqual(ET.parse(self.out).getroot().tag, "ActionMaps")


if __name__ == "__main__":
    unittest.main()
