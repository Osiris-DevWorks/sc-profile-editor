"""Unit tests for the Logitech JOY_X label parser used by the auto_map step."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from generate_pdf_template import parse_joy_label


class TestParseJoyLabel(unittest.TestCase):
    def test_buttons(self):
        self.assertEqual(parse_joy_label("JOY_1"), ("button", 1))
        self.assertEqual(parse_joy_label("JOY_25"), ("button", 25))
        self.assertEqual(parse_joy_label("JOY_32"), ("button", 32))

    def test_axes_with_direction(self):
        self.assertEqual(parse_joy_label("JOY_X+"), ("axis", "x"))
        self.assertEqual(parse_joy_label("JOY_X-"), ("axis", "x"))
        self.assertEqual(parse_joy_label("JOY_Y+"), ("axis", "y"))
        self.assertEqual(parse_joy_label("JOY_Z+"), ("axis", "z"))
        self.assertEqual(parse_joy_label("JOY_Z-"), ("axis", "z"))

    def test_axes_rotated(self):
        self.assertEqual(parse_joy_label("JOY_RX+"), ("axis", "rotx"))
        self.assertEqual(parse_joy_label("JOY_RY-"), ("axis", "roty"))
        self.assertEqual(parse_joy_label("JOY_RZ+"), ("axis", "rotz"))

    def test_axes_no_direction(self):
        # The +/- is optional for cardinal axes — sometimes labels are bare
        self.assertEqual(parse_joy_label("JOY_Y"), ("axis", "y"))
        self.assertEqual(parse_joy_label("JOY_Z"), ("axis", "z"))

    def test_sliders(self):
        self.assertEqual(parse_joy_label("JOY_SLIDER1"), ("axis", "slider1"))
        self.assertEqual(parse_joy_label("JOY_SLIDER2"), ("axis", "slider2"))

    def test_hats_long(self):
        self.assertEqual(parse_joy_label("POV1_UP"), ("hat", "hat1_up"))
        self.assertEqual(parse_joy_label("POV1_DOWN"), ("hat", "hat1_down"))
        self.assertEqual(parse_joy_label("POV1_LEFT"), ("hat", "hat1_left"))
        self.assertEqual(parse_joy_label("POV1_RIGHT"), ("hat", "hat1_right"))

    def test_hats_short(self):
        # Common abbreviated form in the X56 layout
        self.assertEqual(parse_joy_label("POV1_U"), ("hat", "hat1_up"))
        self.assertEqual(parse_joy_label("POV1_D"), ("hat", "hat1_down"))
        self.assertEqual(parse_joy_label("POV1_L"), ("hat", "hat1_left"))
        self.assertEqual(parse_joy_label("POV1_R"), ("hat", "hat1_right"))

    def test_high_number_with_direction_is_slider(self):
        # JOY_33+/- on the X56's SLD throttle — non-standard slider mapping
        self.assertEqual(parse_joy_label("JOY_33+"), ("axis", "slider2"))
        self.assertEqual(parse_joy_label("JOY_33-"), ("axis", "slider2"))

    def test_high_number_without_direction_is_button(self):
        # Boundary case: JOY_33 (no sign) is a button, JOY_33+ is a slider.
        # If this test starts failing, the slider33 regex likely went greedy.
        self.assertEqual(parse_joy_label("JOY_33"), ("button", 33))

    def test_unrecognized_returns_none(self):
        self.assertIsNone(parse_joy_label("GARBAGE"))
        self.assertIsNone(parse_joy_label(""))
        self.assertIsNone(parse_joy_label("MODULE"))
        self.assertIsNone(parse_joy_label("X/Y"))

    def test_case_insensitive_and_whitespace(self):
        # OCR sometimes returns lowercase or with stray spaces
        self.assertEqual(parse_joy_label("joy_7"), ("button", 7))
        self.assertEqual(parse_joy_label(" JOY_7 "), ("button", 7))
        self.assertEqual(parse_joy_label("J O Y _ 7"), ("button", 7))


if __name__ == "__main__":
    unittest.main()
