"""
Input detection module for capturing joystick, keyboard, and mouse inputs

This module uses python-dinput for joystick/gamepad detection and pynput
for keyboard and mouse input detection.
"""

import logging
from typing import Optional, Tuple, Dict
from PyQt6.QtCore import QThread, pyqtSignal
import threading
import time

logger = logging.getLogger(__name__)


class InputDetectorThread(QThread):
    """Thread-safe input detector that listens for controller inputs"""

    # Signal emitted when input is detected: (input_code, input_description)
    input_detected = pyqtSignal(str, str)

    # Signal emitted when detection times out or is cancelled
    detection_cancelled = pyqtSignal()

    def __init__(self, timeout_ms: int = 10000):
        super().__init__()
        self.timeout_ms = timeout_ms
        self.running = False
        self.joystick_state: Dict[int, Dict] = {}  # Track joystick axis state for threshold detection
        self.active_modifiers: Dict[str, bool] = {  # Track which modifier keys are pressed
            "lctrl": False,
            "rctrl": False,
            "lalt": False,
            "ralt": False,
            "lshift": False,
            "rshift": False,
        }

    def run(self):
        """Run the input detection loop"""
        try:
            self.running = True
            start_time = time.time()
            elapsed_ms = 0
            last_detected_joystick = None
            last_detected_keyboard_listener = None
            last_detected_mouse_listener = None

            # Start joystick detection thread
            joystick_detected = threading.Event()
            joystick_result = {"code": None, "description": None}

            joystick_thread = threading.Thread(
                target=self._detect_joystick,
                args=(joystick_detected, joystick_result),
                daemon=True
            )
            joystick_thread.start()

            # Start keyboard detection listener
            keyboard_detected = threading.Event()
            keyboard_result = {"code": None, "description": None}

            try:
                from pynput import keyboard
                keyboard_listener = keyboard.Listener(
                    on_press=lambda key: self._on_keyboard_press(key, keyboard_detected, keyboard_result),
                    on_release=lambda key: self._on_keyboard_release(key)
                )
                keyboard_listener.start()
            except Exception as e:
                logger.warning(f"Could not start keyboard listener: {e}")
                keyboard_listener = None

            # Start mouse detection listener
            mouse_detected = threading.Event()
            mouse_result = {"code": None, "description": None}

            try:
                from pynput import mouse
                mouse_listener = mouse.Listener(
                    on_click=lambda x, y, button, pressed: self._on_mouse_click(button, pressed, mouse_detected, mouse_result)
                )
                mouse_listener.start()
            except Exception as e:
                logger.warning(f"Could not start mouse listener: {e}")
                mouse_listener = None

            # Detection loop
            while self.running and elapsed_ms < self.timeout_ms:
                # Check for joystick input
                if joystick_detected.is_set():
                    if joystick_result["code"]:
                        logger.info(f"Detected joystick input: {joystick_result['code']} - {joystick_result['description']}")
                        self.input_detected.emit(joystick_result["code"], joystick_result["description"])
                        self.running = False
                        break

                # Check for keyboard input
                if keyboard_detected.is_set():
                    if keyboard_result["code"]:
                        logger.info(f"Detected keyboard input: {keyboard_result['code']} - {keyboard_result['description']}")
                        self.input_detected.emit(keyboard_result["code"], keyboard_result["description"])
                        self.running = False
                        break

                # Check for mouse input
                if mouse_detected.is_set():
                    if mouse_result["code"]:
                        logger.info(f"Detected mouse input: {mouse_result['code']} - {mouse_result['description']}")
                        self.input_detected.emit(mouse_result["code"], mouse_result["description"])
                        self.running = False
                        break

                # Update elapsed time and sleep
                time.sleep(0.05)  # 50ms polling interval
                elapsed_ms = (time.time() - start_time) * 1000

            # Clean up listeners
            if keyboard_listener:
                try:
                    keyboard_listener.stop()
                except:
                    pass

            if mouse_listener:
                try:
                    mouse_listener.stop()
                except:
                    pass

            # Timeout
            if self.running:
                logger.info("Input detection timed out")
                self.detection_cancelled.emit()

        except Exception as e:
            logger.error(f"Error in input detection: {e}", exc_info=True)
            self.detection_cancelled.emit()

        finally:
            self.running = False

    def _detect_joystick(self, detected_event, result_dict):
        """Detect joystick input in a separate thread"""
        try:
            import dinput

            # Get list of devices
            devices = dinput.get_joysticks()

            if not devices:
                logger.warning("No joysticks detected")
                return

            logger.info(f"Found {len(devices)} joystick(s)")

            # Create joystick objects
            joysticks = []
            for i, device_guid in enumerate(devices):
                try:
                    joystick = dinput.Joystick(device_guid)
                    joystick.open()
                    joysticks.append((i + 1, joystick))  # 1-indexed for SC
                    logger.info(f"Initialized joystick {i + 1}")
                except Exception as e:
                    logger.warning(f"Could not initialize joystick {i}: {e}")

            if not joysticks:
                return

            # Joystick detection loop
            start_time = time.time()
            axis_state = {}  # Track previous axis values to detect significant changes

            while self.running and (time.time() - start_time) * 1000 < self.timeout_ms:
                try:
                    for js_num, joystick in joysticks:
                        try:
                            # Update state
                            joystick.update()
                            state = joystick.state

                            # Check buttons
                            if hasattr(state, 'buttons') and state.buttons:
                                for button_idx, button_pressed in enumerate(state.buttons):
                                    if button_pressed:
                                        input_code = f"js{js_num}_button{button_idx + 1}"
                                        result_dict["code"] = input_code
                                        result_dict["description"] = f"Joystick {js_num} Button {button_idx + 1}"
                                        detected_event.set()
                                        return

                            # Check POV/hat switches
                            if hasattr(state, 'pov') and state.pov is not None and state.pov >= 0:
                                # POV is in degrees: 0=up, 9000=right, 18000=down, 27000=left
                                # -1 or 65535 means not pressed
                                if state.pov < 36000:  # Valid POV value
                                    if state.pov == 0:
                                        direction = "up"
                                    elif state.pov == 9000:
                                        direction = "right"
                                    elif state.pov == 18000:
                                        direction = "down"
                                    elif state.pov == 27000:
                                        direction = "left"
                                    else:
                                        # Diagonal - use closest direction
                                        if state.pov < 4500:
                                            direction = "up"
                                        elif state.pov < 13500:
                                            direction = "right"
                                        elif state.pov < 22500:
                                            direction = "down"
                                        else:
                                            direction = "left"

                                    input_code = f"js{js_num}_hat1_{direction}"
                                    result_dict["code"] = input_code
                                    result_dict["description"] = f"Joystick {js_num} Hat 1 {direction.upper()}"
                                    detected_event.set()
                                    return

                            # Check axes (with threshold for analog sticks)
                            axis_names = {
                                0: "x",       # X axis (left stick horizontal)
                                1: "y",       # Y axis (left stick vertical)
                                2: "z",       # Z axis (right stick horizontal, or throttle)
                                3: "rotz",    # Rotation Z (right stick vertical)
                                4: "rotx",    # Rotation X (twist)
                                5: "roty",    # Rotation Y
                                6: "slider1", # Slider 1
                                7: "slider2", # Slider 2
                            }

                            if hasattr(state, 'lX'):
                                axes = [
                                    state.lX if hasattr(state, 'lX') else 0,
                                    state.lY if hasattr(state, 'lY') else 0,
                                    state.lZ if hasattr(state, 'lZ') else 0,
                                    state.lRz if hasattr(state, 'lRz') else 0,
                                    state.lRx if hasattr(state, 'lRx') else 0,
                                    state.lRy if hasattr(state, 'lRy') else 0,
                                ]

                                # Normalize axes from -32768 to 32767 to -1.0 to 1.0
                                threshold = 0.5
                                for axis_idx, raw_value in enumerate(axes):
                                    # Normalize
                                    if raw_value > 0:
                                        normalized_value = raw_value / 32767.0
                                    else:
                                        normalized_value = raw_value / 32768.0

                                    # Check if significant movement
                                    if abs(normalized_value) > threshold:
                                        axis_name = axis_names.get(axis_idx, f"axis{axis_idx}")
                                        direction = "+" if normalized_value > 0 else "-"
                                        input_code = f"js{js_num}_{axis_name}"
                                        result_dict["code"] = input_code
                                        result_dict["description"] = f"Joystick {js_num} {axis_name.upper()} ({direction})"
                                        detected_event.set()
                                        return

                        except Exception as e:
                            logger.debug(f"Error checking joystick {js_num}: {e}")
                            continue

                    time.sleep(0.05)  # 50ms polling interval

                except Exception as e:
                    logger.debug(f"Error in joystick detection loop: {e}")
                    time.sleep(0.05)

        except ImportError:
            logger.error("python-dinput not installed. Joystick detection unavailable.")
        except Exception as e:
            logger.error(f"Error in joystick detection: {e}", exc_info=True)

    def _on_keyboard_press(self, key, detected_event, result_dict):
        """Handle keyboard key press (callback from pynput)"""
        try:
            from pynput.keyboard import Key

            if not self.running:
                return False  # Stop listener

            # Track modifier keys
            modifier_key_map = {
                Key.ctrl_l: "lctrl",
                Key.ctrl_r: "rctrl",
                Key.alt_l: "lalt",
                Key.alt_r: "ralt",
                Key.shift_l: "lshift",
                Key.shift_r: "rshift",
            }

            # If this is a modifier key being pressed, track it and continue listening
            if key in modifier_key_map:
                self.active_modifiers[modifier_key_map[key]] = True
                return True  # Continue listening

            # Get the currently active modifier (if any)
            modifier = self._get_active_modifier_from_state()

            # Get key name
            key_name = self._get_key_name_from_pynput_key(key, modifier)

            # Skip if we couldn't determine a key name
            if not key_name:
                return True  # Continue listening

            # Map to Star Citizen format
            if modifier:
                input_code = f"kb1_{modifier}+{key_name}"
                result_dict["code"] = input_code
                result_dict["description"] = f"Keyboard {self._format_modifier_description(modifier)}+{key_name.upper()}"
            else:
                input_code = f"kb1_{key_name}"
                result_dict["code"] = input_code
                result_dict["description"] = f"Keyboard {key_name.upper()}"

            detected_event.set()
            return False  # Stop listener

        except Exception as e:
            logger.debug(f"Error handling keyboard press: {e}")
            return True  # Continue listening

    def _get_key_name_from_pynput_key(self, key, active_modifier: Optional[str] = None) -> Optional[str]:
        """
        Extract key name from pynput key object.
        Handles special cases like Ctrl+letter combinations which pynput reports as control characters.

        Args:
            key: pynput key object
            active_modifier: The active modifier (if any), used to map control characters back to letters

        Returns:
            Key name string or None if unable to determine
        """
        try:
            from pynput.keyboard import Key

            # Handle special Key enums
            if isinstance(key, Key):
                key_name = key.name
                # Skip pure modifier-like keys
                if key_name in ("ctrl", "alt", "shift", "cmd"):
                    return None
                return key_name

            # Handle regular character keys
            if hasattr(key, 'char'):
                char = key.char

                # When Ctrl is pressed, pynput reports control characters (ASCII 0x00-0x1F)
                # We need to map them back to the original letters
                if active_modifier and active_modifier in ("lctrl", "rctrl"):
                    # Map control characters back to letters
                    # Ctrl+A = 0x01, Ctrl+B = 0x02, ..., Ctrl+Z = 0x1A
                    ctrl_char_map = {
                        '\x01': 'a', '\x02': 'b', '\x03': 'c', '\x04': 'd', '\x05': 'e',
                        '\x06': 'f', '\x07': 'g', '\x08': 'h', '\x09': 'i', '\x0a': 'j',
                        '\x0b': 'k', '\x0c': 'l', '\x0d': 'm', '\x0e': 'n', '\x0f': 'o',
                        '\x10': 'p', '\x11': 'q', '\x12': 'r', '\x13': 's', '\x14': 't',
                        '\x15': 'u', '\x16': 'v', '\x17': 'w', '\x18': 'x', '\x19': 'y',
                        '\x1a': 'z',
                    }

                    if char in ctrl_char_map:
                        return ctrl_char_map[char]

                return char

            return str(key) if key else None

        except Exception as e:
            logger.debug(f"Error getting key name from pynput key: {e}")
            return None

    def _on_keyboard_release(self, key):
        """Handle keyboard key release (callback from pynput)"""
        try:
            from pynput.keyboard import Key

            if not self.running:
                return False  # Stop listener

            # Track modifier keys being released
            modifier_key_map = {
                Key.ctrl_l: "lctrl",
                Key.ctrl_r: "rctrl",
                Key.alt_l: "lalt",
                Key.alt_r: "ralt",
                Key.shift_l: "lshift",
                Key.shift_r: "rshift",
            }

            if key in modifier_key_map:
                self.active_modifiers[modifier_key_map[key]] = False

            return True  # Continue listening

        except Exception as e:
            logger.debug(f"Error handling keyboard release: {e}")
            return True  # Continue listening

    def _get_active_modifier_from_state(self) -> Optional[str]:
        """
        Get the first active modifier from the tracked state.
        Returns the modifier code (lctrl, rctrl, lalt, ralt, lshift, rshift) or None.
        Only one modifier is returned (the first active one found).
        """
        # Check modifiers in order: ctrl, alt, shift (with left preference)
        for modifier in ["lctrl", "rctrl", "lalt", "ralt", "lshift", "rshift"]:
            if self.active_modifiers.get(modifier, False):
                return modifier
        return None

    def _format_modifier_description(self, modifier: str) -> str:
        """Format modifier code to human-readable description"""
        modifier_map = {
            "lctrl": "Left Ctrl",
            "rctrl": "Right Ctrl",
            "lalt": "Left Alt",
            "ralt": "Right Alt",
            "lshift": "Left Shift",
            "rshift": "Right Shift",
        }
        return modifier_map.get(modifier, modifier)

    def _on_mouse_click(self, button, pressed, detected_event, result_dict):
        """Handle mouse button click (callback from pynput)"""
        try:
            from pynput.mouse import Button

            if not self.running or not pressed:
                return True  # Continue listening

            # Get button name
            # Standard mouse button mapping: left=1, right=2, middle=3, x1=4, x2=5
            button_names = {
                Button.left: ("mouse1", "Mouse Left"),
                Button.right: ("mouse2", "Mouse Right"),
                Button.middle: ("mouse3", "Mouse Middle"),
                Button.x1: ("mouse4", "Mouse Button 4 (Side)"),
                Button.x2: ("mouse5", "Mouse Button 5 (Side)"),
            }

            if button in button_names:
                input_code, description = button_names[button]
                result_dict["code"] = input_code
                result_dict["description"] = description
                detected_event.set()
                return False  # Stop listener

            return True  # Continue listening

        except Exception as e:
            logger.debug(f"Error handling mouse click: {e}")
            return True  # Continue listening

    def stop(self):
        """Stop the detection loop"""
        self.running = False


class InputDetector:
    """Main input detector class - wrapper around the thread"""

    def __init__(self):
        self.thread = None

    def start_detection(self, timeout_ms: int = 10000) -> InputDetectorThread:
        """
        Start listening for input

        Args:
            timeout_ms: How long to wait for input before timing out

        Returns:
            InputDetectorThread object with signals to connect to
        """
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.thread.wait()

        self.thread = InputDetectorThread(timeout_ms)
        self.thread.start()
        return self.thread

    def stop_detection(self):
        """Stop listening for input"""
        if self.thread:
            self.thread.stop()
            self.thread.wait()

    @staticmethod
    def get_available_devices() -> list:
        """Get list of available input devices"""
        devices = []

        try:
            # Keyboard and mouse are always available
            devices.append({"type": "keyboard", "instance": 1, "name": "Keyboard"})
            devices.append({"type": "mouse", "instance": 1, "name": "Mouse"})

            # Add joysticks
            try:
                import dinput
                joystick_guids = dinput.get_joysticks()

                for i, guid in enumerate(joystick_guids):
                    try:
                        joystick = dinput.Joystick(guid)
                        joystick.open()
                        devices.append({
                            "type": "joystick",
                            "instance": i + 1,
                            "name": f"Joystick {i + 1}"
                        })
                        joystick.close()
                    except Exception as e:
                        logger.debug(f"Could not open joystick {i}: {e}")
                        devices.append({
                            "type": "joystick",
                            "instance": i + 1,
                            "name": f"Joystick {i + 1} (unavailable)"
                        })

            except ImportError:
                logger.warning("python-dinput not available, joystick detection skipped")
            except Exception as e:
                logger.error(f"Error detecting joysticks: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error getting devices: {e}", exc_info=True)

        return devices
