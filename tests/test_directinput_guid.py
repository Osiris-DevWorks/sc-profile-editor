"""Unit tests for DirectInput product-GUID parsing."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from utils.directinput_guid import (
    parse_di_product_guid,
    make_di_product_guid,
    parse_sdl_joystick_guid,
    vid_pid_from_any,
)


class TestDirectInputProductGUID(unittest.TestCase):
    """The DI product GUID is a pure function of VID/PID."""

    def test_vkb_gunfighter_scg_round_trip(self):
        # From default-bindings/presets/layout_vkb_scg_prem_dual.xml:
        # "VKB-Sim Space Gunfighter  {0126231D-0000-0000-0000-504944564944}"
        # VID 0x231D = VKB-Sim, PID 0x0126 = Gunfighter SCG
        guid = "{0126231D-0000-0000-0000-504944564944}"
        self.assertEqual(parse_di_product_guid(guid), (0x231D, 0x0126))
        self.assertEqual(make_di_product_guid(0x231D, 0x0126), guid)

    def test_vkb_gunfighter_lh_variant(self):
        # Same vendor, different product
        self.assertEqual(
            parse_di_product_guid("{0127231D-0000-0000-0000-504944564944}"),
            (0x231D, 0x0127),
        )

    def test_t16000m(self):
        # Thrustmaster T.16000M: VID 0x044F, PID 0xB10A
        # MAKELONG(VID, PID) = (PID << 16) | VID = 0xB10A044F
        guid = make_di_product_guid(0x044F, 0xB10A)
        self.assertEqual(guid, "{B10A044F-0000-0000-0000-504944564944}")
        self.assertEqual(parse_di_product_guid(guid), (0x044F, 0xB10A))

    def test_extracts_from_full_product_string(self):
        # SC profile attribute format — name + GUID + extra whitespace
        product = "  VKB-Sim Space Gunfighter   {0126231D-0000-0000-0000-504944564944}"
        self.assertEqual(parse_di_product_guid(product), (0x231D, 0x0126))

    def test_keyboard_class_guid_returns_none(self):
        # SC writes a Windows class GUID for keyboard, NOT a DI product GUID.
        # Trailing bytes are 444553540000 ("DEST") — different signature.
        kb = "Keyboard  {6F1D2B61-D5A0-11CF-BFC7-444553540000}"
        self.assertIsNone(parse_di_product_guid(kb))

    def test_mouse_class_guid_returns_none(self):
        ms = "Mouse  {6F1D2B62-D5A0-11CF-BFC7-444553540000}"
        self.assertIsNone(parse_di_product_guid(ms))

    def test_empty_and_garbage_input(self):
        self.assertIsNone(parse_di_product_guid(""))
        self.assertIsNone(parse_di_product_guid("Thrustmaster X-56"))  # name only, no GUID
        self.assertIsNone(parse_di_product_guid(None))

    def test_case_insensitive(self):
        # GUID matching must be case-insensitive — SC and Windows use mixed case
        lower = "{0126231d-0000-0000-0000-504944564944}"
        self.assertEqual(parse_di_product_guid(lower), (0x231D, 0x0126))

    def test_make_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            make_di_product_guid(-1, 0x0126)
        with self.assertRaises(ValueError):
            make_di_product_guid(0x231D, 0x10000)


class TestSDLJoystickGUID(unittest.TestCase):
    """SDL joystick GUID parsing (what pygame returns)."""

    def test_t16000m_sdl_guid(self):
        # Synthesized SDL GUID for VID 0x044F, PID 0xB10A on USB:
        # bytes: 03 00 00 00 4f 04 00 00 0a b1 00 00 14 01 00 00
        sdl = "030000004f0400000ab1000014010000"
        self.assertEqual(parse_sdl_joystick_guid(sdl), (0x044F, 0xB10A))

    def test_xinput_synthetic_returns_none(self):
        # XInput devices use bus 0x00 and don't carry VID/PID at standard offsets
        sdl = "00000000000000000000000000000000"
        self.assertIsNone(parse_sdl_joystick_guid(sdl))

    def test_invalid_length_returns_none(self):
        self.assertIsNone(parse_sdl_joystick_guid("toolong" * 10))
        self.assertIsNone(parse_sdl_joystick_guid("short"))
        self.assertIsNone(parse_sdl_joystick_guid(""))

    def test_strips_dashes(self):
        # Some libraries return dash-formatted GUIDs
        sdl = "03000000-4f04-0000-0ab1-000014010000"
        self.assertEqual(parse_sdl_joystick_guid(sdl), (0x044F, 0xB10A))


class TestUnifiedExtractor(unittest.TestCase):
    def test_di_takes_precedence(self):
        # When both a DI product GUID and an SDL-shaped string are plausible,
        # the DI signature wins because it's unambiguous.
        di = "{0126231D-0000-0000-0000-504944564944}"
        self.assertEqual(vid_pid_from_any(di), (0x231D, 0x0126))

    def test_falls_through_to_sdl(self):
        sdl = "030000004f0400000ab1000014010000"
        self.assertEqual(vid_pid_from_any(sdl), (0x044F, 0xB10A))


if __name__ == "__main__":
    unittest.main()
