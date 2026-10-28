"""
Unit tests for XML parser and label generator
"""

import unittest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from parser.xml_parser import ProfileParser
from parser.label_generator import LabelGenerator


class TestProfileParser(unittest.TestCase):
    """Test cases for ProfileParser"""

    def setUp(self):
        """Set up test fixtures"""
        # Get path to example profiles
        self.test_dir = Path(__file__).parent.parent
        self.example_dir = self.test_dir / "example-profiles"

        # Committed VKB profile: keyboard, mouse and two Gladiator EVO joysticks
        self.test_file = self.example_dir / "layout_osiris-vkb-2025-10-25_exported.xml"

        # Same profile doubles as the joystick-info fixture
        self.test_file_joystick = self.test_file

    def test_parser_initialization(self):
        """Test parser can be initialized"""
        parser = ProfileParser(str(self.test_file))
        self.assertIsNotNone(parser)
        self.assertEqual(parser.xml_path, str(self.test_file))

    def test_parse_basic_profile(self):
        """Test parsing a basic profile"""
        parser = ProfileParser(str(self.test_file))
        profile = parser.parse()

        self.assertIsNotNone(profile)
        self.assertEqual(profile.profile_name, "osiris-vkb-2025-10-25")
        self.assertGreater(len(profile.devices), 0)
        self.assertGreater(len(profile.action_maps), 0)

    def test_parse_profile_name(self):
        """Test profile name extraction"""
        parser = ProfileParser(str(self.test_file))
        parser.parse()

        name = parser.get_profile_name()
        self.assertEqual(name, "osiris-vkb-2025-10-25")

    def test_parse_devices(self):
        """Test device extraction"""
        parser = ProfileParser(str(self.test_file_joystick))
        profile = parser.parse()

        # Fixture profile has keyboard, mouse, and 2 joysticks
        self.assertGreaterEqual(len(profile.devices), 2)

        # Check for keyboard
        keyboards = [d for d in profile.devices if d.device_type == 'keyboard']
        self.assertGreater(len(keyboards), 0)

        # Check for joysticks
        joysticks = [d for d in profile.devices if d.device_type == 'joystick']
        self.assertEqual(len(joysticks), 2)

        # Verify joystick product names
        for js in joysticks:
            self.assertIsNotNone(js.product_name)
            self.assertIn('VKBsim Gladiator EVO', js.product_name)

    def test_parse_action_maps(self):
        """Test action map extraction"""
        parser = ProfileParser(str(self.test_file))
        profile = parser.parse()

        # Should have multiple action maps
        self.assertGreater(len(profile.action_maps), 0)

        # Each action map should have a name and actions
        for action_map in profile.action_maps:
            self.assertIsNotNone(action_map.name)
            self.assertGreater(len(action_map.actions), 0)

    def test_parse_action_bindings(self):
        """Test action binding extraction"""
        parser = ProfileParser(str(self.test_file))
        profile = parser.parse()

        # Get all bindings
        all_bindings = profile.get_all_bindings()
        self.assertGreater(len(all_bindings), 0)

        # Each binding should have required fields
        for binding in all_bindings:
            self.assertIsNotNone(binding.action_name)
            self.assertIsNotNone(binding.input_code)

    def test_categories_extraction(self):
        """Test category extraction"""
        parser = ProfileParser(str(self.test_file))
        profile = parser.parse()

        # Should have some categories
        self.assertGreater(len(profile.categories), 0)


class TestLabelGenerator(unittest.TestCase):
    """Test cases for LabelGenerator"""

    def test_generate_action_label_basic(self):
        """Test basic action label generation"""
        label = LabelGenerator.generate_action_label("v_view_pitch")
        self.assertEqual(label, "View Pitch")

        label = LabelGenerator.generate_action_label("v_afterburner")
        self.assertEqual(label, "Afterburner")

    def test_generate_action_label_with_prefix(self):
        """Test action label with prefix"""
        label = LabelGenerator.generate_action_label("foip_pushtotalk")
        self.assertEqual(label, "FOIP: Pushtotalk")

        label = LabelGenerator.generate_action_label("turret_pitch")
        self.assertEqual(label, "Turret: Pitch")

    def test_generate_input_label_keyboard(self):
        """Test keyboard input label generation"""
        label = LabelGenerator.generate_input_label("kb1_down")
        self.assertEqual(label, "Keyboard: Down Arrow")

        label = LabelGenerator.generate_input_label("kb1_space")
        self.assertEqual(label, "Keyboard: Space")

        label = LabelGenerator.generate_input_label("kb1_f1")
        self.assertEqual(label, "Keyboard: F1")

    def test_generate_input_label_joystick_button(self):
        """Test joystick button label generation"""
        label = LabelGenerator.generate_input_label("js1_button5")
        self.assertEqual(label, "Joystick 1: Button 5")

        label = LabelGenerator.generate_input_label("js2_button12")
        self.assertEqual(label, "Joystick 2: Button 12")

    def test_generate_input_label_joystick_hat(self):
        """Test joystick hat label generation"""
        label = LabelGenerator.generate_input_label("js1_hat1_up")
        self.assertEqual(label, "Joystick 1: Hat 1 Up")

        label = LabelGenerator.generate_input_label("js2_hat2_left")
        self.assertEqual(label, "Joystick 2: Hat 2 Left")

    def test_generate_input_label_mouse(self):
        """Test mouse input label generation"""
        label = LabelGenerator.generate_input_label("kb1_mouse1")
        self.assertEqual(label, "Keyboard: Left Click")

        label = LabelGenerator.generate_input_label("kb1_mouse4")
        self.assertEqual(label, "Keyboard: Mouse Button 4")

    def test_generate_input_label_empty(self):
        """Test empty input handling"""
        label = LabelGenerator.generate_input_label("")
        self.assertEqual(label, "Unbound")

        label = LabelGenerator.generate_input_label("   ")
        self.assertEqual(label, "Unbound")

    def test_generate_actionmap_label(self):
        """Test action map label generation"""
        label = LabelGenerator.generate_actionmap_label("spaceship_movement")
        self.assertEqual(label, "Spaceship Movement")

        label = LabelGenerator.generate_actionmap_label("player_choice")
        self.assertEqual(label, "Player Choice")


if __name__ == "__main__":
    unittest.main()
