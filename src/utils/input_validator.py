"""
Input code validation and parsing utilities for Star Citizen controls
"""

import re
from typing import Optional, Dict, List, Tuple


class InputValidator:
    """Validates and parses Star Citizen input codes"""

    # Regular expressions for different input types
    BUTTON_PATTERN = re.compile(r'^js(\d+)_button(\d+)$')
    AXIS_PATTERN = re.compile(r'^js(\d+)_(x|y|z|rotx|roty|rotz|slider\d+)$')
    HAT_PATTERN = re.compile(r'^js(\d+)_hat(\d+)_(up|down|left|right)$')
    # Keyboard pattern with optional modifier: kb1_lctrl+a or kb1_a
    KEYBOARD_PATTERN = re.compile(r'^kb(\d+)_(?:(lctrl|rctrl|lalt|ralt|lshift|rshift)\+)?(.+)$')
    MOUSE_PATTERN = re.compile(r'^mouse(\d+)$')
    MOUSEWHEEL_PATTERN = re.compile(r'^mwheel_(up|down)$')
    UNBOUND_PATTERN = re.compile(r'^(js|kb|mouse)(\d+)_ $')

    # Valid modifier keys
    VALID_MODIFIERS = {"lctrl", "rctrl", "lalt", "ralt", "lshift", "rshift"}

    # Valid activation modes
    ACTIVATION_MODES = [
        "press",
        "release",
        "hold",
        "double_tap",
        "tap",
        None  # No activation mode specified
    ]

    @classmethod
    def validate(cls, input_code: str) -> bool:
        """
        Validate if an input code follows Star Citizen format

        Args:
            input_code: Input code to validate (e.g., "js1_button5")

        Returns:
            True if valid, False otherwise
        """
        if not input_code:
            return False

        input_code = input_code.strip()

        # Check against all patterns
        return bool(
            cls.BUTTON_PATTERN.match(input_code) or
            cls.AXIS_PATTERN.match(input_code) or
            cls.HAT_PATTERN.match(input_code) or
            cls.KEYBOARD_PATTERN.match(input_code) or
            cls.MOUSE_PATTERN.match(input_code) or
            cls.MOUSEWHEEL_PATTERN.match(input_code) or
            cls.UNBOUND_PATTERN.match(input_code)
        )

    @classmethod
    def parse(cls, input_code: str) -> Optional[Dict[str, any]]:
        """
        Parse an input code into its components

        Args:
            input_code: Input code to parse

        Returns:
            Dictionary with keys: device_type, device_instance, input_type, input_value
            Returns None if invalid
        """
        if not input_code:
            return None

        input_code = input_code.strip()

        # Try button pattern
        match = cls.BUTTON_PATTERN.match(input_code)
        if match:
            return {
                "device_type": "joystick",
                "device_instance": int(match.group(1)),
                "input_type": "button",
                "input_value": int(match.group(2)),
                "input_detail": None
            }

        # Try axis pattern
        match = cls.AXIS_PATTERN.match(input_code)
        if match:
            return {
                "device_type": "joystick",
                "device_instance": int(match.group(1)),
                "input_type": "axis",
                "input_value": match.group(2),
                "input_detail": None
            }

        # Try hat pattern
        match = cls.HAT_PATTERN.match(input_code)
        if match:
            return {
                "device_type": "joystick",
                "device_instance": int(match.group(1)),
                "input_type": "hat",
                "input_value": int(match.group(2)),
                "input_detail": match.group(3)  # direction: up/down/left/right
            }

        # Try keyboard pattern
        match = cls.KEYBOARD_PATTERN.match(input_code)
        if match:
            return {
                "device_type": "keyboard",
                "device_instance": int(match.group(1)),
                "input_type": "key",
                "input_value": match.group(3),  # Key is now in group 3 (after optional modifier)
                "input_detail": match.group(2) if match.group(2) else None  # Modifier in group 2
            }

        # Try mouse pattern
        match = cls.MOUSE_PATTERN.match(input_code)
        if match:
            return {
                "device_type": "mouse",
                "device_instance": int(match.group(1)),
                "input_type": "button",
                "input_value": int(match.group(1)),
                "input_detail": None
            }

        # Try mouse wheel pattern
        match = cls.MOUSEWHEEL_PATTERN.match(input_code)
        if match:
            return {
                "device_type": "mouse",
                "device_instance": 1,
                "input_type": "wheel",
                "input_value": match.group(1),  # up or down
                "input_detail": None
            }

        # Try unbound pattern
        match = cls.UNBOUND_PATTERN.match(input_code)
        if match:
            device_type_map = {"js": "joystick", "kb": "keyboard", "mouse": "mouse"}
            return {
                "device_type": device_type_map.get(match.group(1), "unknown"),
                "device_instance": int(match.group(2)),
                "input_type": "unbound",
                "input_value": None,
                "input_detail": None
            }

        return None

    @classmethod
    def format(cls, device_type: str, device_instance: int, input_type: str,
               input_value: any, input_detail: Optional[str] = None) -> str:
        """
        Format components into an input code

        Args:
            device_type: "joystick", "keyboard", "mouse"
            device_instance: Device number (1, 2, 3...)
            input_type: "button", "axis", "hat", "key", "wheel", "unbound"
            input_value: Button number, axis name, key name, etc.
            input_detail: Additional detail (e.g., hat direction)

        Returns:
            Formatted input code string
        """
        if device_type == "joystick":
            if input_type == "button":
                return f"js{device_instance}_button{input_value}"
            elif input_type == "axis":
                return f"js{device_instance}_{input_value}"
            elif input_type == "hat" and input_detail:
                return f"js{device_instance}_hat{input_value}_{input_detail}"
            elif input_type == "unbound":
                return f"js{device_instance}_ "

        elif device_type == "keyboard":
            if input_type == "key":
                if input_detail and input_detail in cls.VALID_MODIFIERS:
                    return f"kb{device_instance}_{input_detail}+{input_value}"
                else:
                    return f"kb{device_instance}_{input_value}"
            elif input_type == "unbound":
                return f"kb{device_instance}_ "

        elif device_type == "mouse":
            if input_type == "button":
                return f"mouse{input_value}"
            elif input_type == "wheel":
                return f"mwheel_{input_value}"
            elif input_type == "unbound":
                return f"mouse{device_instance}_ "

        return ""

    @classmethod
    def get_input_description(cls, input_code: str) -> str:
        """
        Get a human-readable description of an input code

        Args:
            input_code: Input code to describe

        Returns:
            Human-readable description
        """
        parsed = cls.parse(input_code)
        if not parsed:
            return input_code

        device = parsed["device_type"].capitalize()
        instance = parsed["device_instance"]
        input_type = parsed["input_type"]
        value = parsed["input_value"]
        detail = parsed["input_detail"]

        if input_type == "button":
            # Special handling for mouse buttons with friendly names
            if device == "Mouse":
                mouse_button_names = {
                    1: "Left Click",
                    2: "Right Click",
                    3: "Middle Click",
                    4: "Button 4 (Side)",
                    5: "Button 5 (Side)",
                }
                friendly_name = mouse_button_names.get(value, f"Button {value}")
                return f"Mouse {friendly_name}"
            else:
                return f"{device} {instance} Button {value}"
        elif input_type == "axis":
            return f"{device} {instance} {value.upper()} Axis"
        elif input_type == "hat":
            return f"{device} {instance} Hat {value} {detail.upper()}"
        elif input_type == "key":
            # Format modifier key names for display
            modifier_map = {
                "lctrl": "Left Ctrl",
                "rctrl": "Right Ctrl",
                "lalt": "Left Alt",
                "ralt": "Right Alt",
                "lshift": "Left Shift",
                "rshift": "Right Shift",
            }
            if detail and detail in modifier_map:
                return f"Keyboard {modifier_map[detail]}+{value.upper()}"
            else:
                return f"Keyboard {value.upper()}"
        elif input_type == "wheel":
            return f"Mouse Wheel {value.upper()}"
        elif input_type == "unbound":
            return f"Unbound ({device} {instance})"

        return input_code

    @classmethod
    def is_unbound(cls, input_code: str) -> bool:
        """Check if an input code represents an unbound input"""
        return bool(cls.UNBOUND_PATTERN.match(input_code.strip()))

    @classmethod
    def get_device_prefix(cls, input_code: str) -> Optional[str]:
        """
        Get the device prefix from an input code (e.g., "js1", "kb1")

        Args:
            input_code: Input code to parse

        Returns:
            Device prefix string or None
        """
        parsed = cls.parse(input_code)
        if not parsed:
            return None

        device_type = parsed["device_type"]
        instance = parsed["device_instance"]

        if device_type == "joystick":
            return f"js{instance}"
        elif device_type == "keyboard":
            return f"kb{instance}"
        elif device_type == "mouse":
            return "mouse"

        return None

    @classmethod
    def validate_activation_mode(cls, mode: Optional[str]) -> bool:
        """Validate if an activation mode is valid"""
        return mode in cls.ACTIVATION_MODES

    @classmethod
    def get_available_axes(cls) -> List[str]:
        """Get list of available axis names"""
        return ["x", "y", "z", "rotx", "roty", "rotz", "slider1", "slider2"]

    @classmethod
    def get_available_hat_directions(cls) -> List[str]:
        """Get list of available hat directions"""
        return ["up", "down", "left", "right"]
