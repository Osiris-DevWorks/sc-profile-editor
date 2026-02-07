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
        self.stop_listeners_flag = False  # Flag to forcefully stop listeners
        self.joystick_state: Dict[int, Dict] = {}  # Track joystick axis state for threshold detection
        self.active_modifiers: Dict[str, bool] = {  # Track which modifier keys are pressed
            "lctrl": False,
            "rctrl": False,
            "lalt": False,
            "ralt": False,
            "lshift": False,
            "rshift": False,
        }
        self.modifier_press_time: Dict[str, float] = {}  # Track when each modifier was pressed
        self.other_key_pressed = False  # Flag: was a non-modifier key pressed after a modifier?

        # Load ignored inputs from settings for filtering
        from src.utils.settings import AppSettings
        settings = AppSettings()
        self.ignored_inputs = set(settings.get_ignored_inputs())
        if self.ignored_inputs:
            logger.info(f"Loaded {len(self.ignored_inputs)} ignored inputs for filtering")

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
            keyboard_listener = None  # Will be set below

            try:
                from pynput import keyboard
                keyboard_listener = keyboard.Listener(
                    on_press=lambda key: self._on_keyboard_press(key, keyboard_detected, keyboard_result, keyboard_listener),
                    on_release=lambda key: self._on_keyboard_release(key, keyboard_detected, keyboard_result, keyboard_listener)
                )
                keyboard_listener.start()
            except Exception as e:
                logger.warning(f"Could not start keyboard listener: {e}")
                keyboard_listener = None

            # Start mouse detection listener
            mouse_detected = threading.Event()
            mouse_result = {"code": None, "description": None}
            mouse_listener = None  # Will be set below

            try:
                from pynput import mouse
                mouse_listener = mouse.Listener(
                    on_click=lambda x, y, button, pressed: self._on_mouse_click(button, pressed, mouse_detected, mouse_result, mouse_listener)
                )
                mouse_listener.start()
            except Exception as e:
                logger.warning(f"Could not start mouse listener: {e}")
                mouse_listener = None

            # Detection loop
            while self.running and elapsed_ms < self.timeout_ms:
                # Check if any listener set the stop flag
                if self.stop_listeners_flag:
                    logger.debug("Stop listeners flag set, stopping all listeners")
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

                    # Give listeners a moment to actually stop
                    time.sleep(0.1)

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
        """Detect joystick input in a separate thread using pygame"""
        try:
            import pygame

            # Initialize pygame and joystick module
            pygame.init()
            pygame.joystick.init()

            # Create a display window for proper event handling
            # Windows requires an active display context for joystick events
            try:
                # Create a small visible window (hidden windows don't work reliably on Windows)
                pygame.display.set_mode((100, 100))
                pygame.display.set_caption("Input Detection")
                logger.info("Created pygame display window for joystick event handling")
            except Exception as e:
                logger.error(f"Could not create pygame display: {e}", exc_info=True)
                # Continue anyway, but events might not be detected
                logger.warning("Continuing without pygame display - joystick events may not be detected")

            # Get list of joysticks
            joystick_count = pygame.joystick.get_count()

            if joystick_count == 0:
                logger.warning("No joysticks detected")
                return

            logger.info(f"Found {joystick_count} joystick(s)")

            # Initialize all joysticks
            joysticks = []
            for i in range(joystick_count):
                try:
                    joy = pygame.joystick.Joystick(i)
                    joy.init()
                    joysticks.append((i + 1, joy))  # 1-indexed for SC
                    logger.info(f"Initialized joystick {i + 1}: {joy.get_name()}")
                except Exception as e:
                    logger.warning(f"Could not initialize joystick {i}: {e}")

            if not joysticks:
                logger.warning("No joysticks could be initialized")
                return

            # Track previous axis values to avoid duplicates
            previous_axis_state = {}

            # Joystick detection loop
            start_time = time.time()

            while self.running and (time.time() - start_time) * 1000 < self.timeout_ms:
                try:
                    # Pump events on Windows - required for joystick events to be detected
                    pygame.event.pump()

                    # Process pygame events for button presses
                    for event in pygame.event.get():
                        if event.type == pygame.JOYBUTTONDOWN:
                            # Debug: log raw event attributes
                            logger.debug(f"JOYBUTTONDOWN event: joy={getattr(event, 'joy', 'MISSING')}, button={getattr(event, 'button', 'MISSING')}")

                            # Safely get joystick and button numbers with validation
                            try:
                                js_num = event.joy + 1  # Convert to 1-indexed
                                button_num = event.button + 1  # pygame uses 0-indexed buttons

                                # Validate button_num is reasonable (should be 1-32 typically)
                                if button_num < 1 or button_num > 100:
                                    logger.warning(f"Suspicious button number detected: {button_num - 1} (raw) -> {button_num} (1-indexed) for js{js_num}")

                                input_code = f"js{js_num}_button{button_num}"
                                # Filter ignored inputs
                                if input_code in self.ignored_inputs:
                                    logger.debug(f"Ignoring filtered button input: {input_code}")
                                    continue
                                result_dict["code"] = input_code
                                result_dict["description"] = f"Joystick {js_num} Button {button_num}"
                                logger.info(f"Button detected: {input_code} - {result_dict['description']}")
                                detected_event.set()
                                return
                            except AttributeError as e:
                                logger.error(f"Error accessing event.button or event.joy: {e}", exc_info=True)
                                continue

                        elif event.type == pygame.JOYHATMOTION:
                            # Hat/POV switch
                            js_num = event.joy + 1  # Convert to 1-indexed
                            hat_num = event.hat + 1
                            x, y = event.value

                            # Map hat motion to directions
                            if y == 1:
                                direction = "up"
                            elif y == -1:
                                direction = "down"
                            elif x == 1:
                                direction = "right"
                            elif x == -1:
                                direction = "left"
                            else:
                                continue  # No motion

                            input_code = f"js{js_num}_hat{hat_num}_{direction}"
                            # Filter ignored inputs
                            if input_code in self.ignored_inputs:
                                logger.debug(f"Ignoring filtered hat input: {input_code}")
                                continue
                            result_dict["code"] = input_code
                            result_dict["description"] = f"Joystick {js_num} Hat {hat_num} {direction.upper()}"
                            detected_event.set()
                            return

                        elif event.type == pygame.JOYAXISMOTION:
                            # Analog axis/stick movement
                            js_num = event.joy + 1  # Convert to 1-indexed
                            axis_num = event.axis
                            value = event.value

                            # Map axis number to name
                            axis_names = {
                                0: "x",       # X axis (left stick horizontal)
                                1: "y",       # Y axis (left stick vertical)
                                2: "z",       # Z axis (right stick horizontal or throttle)
                                3: "rotz",    # Rotation Z (right stick vertical)
                                4: "rotx",    # Rotation X (twist)
                                5: "roty",    # Rotation Y
                                6: "slider1", # Slider 1
                                7: "slider2", # Slider 2
                            }

                            axis_name = axis_names.get(axis_num, f"axis{axis_num}")

                            # Only detect significant movements (threshold: 0.5)
                            threshold = 0.5
                            if abs(value) > threshold:
                                # Track state to avoid duplicates
                                state_key = (js_num, axis_name)
                                if state_key not in previous_axis_state or abs(previous_axis_state[state_key]) <= threshold:
                                    previous_axis_state[state_key] = value
                                    direction = "+" if value > 0 else "-"
                                    input_code = f"js{js_num}_{axis_name}"
                                    # Filter ignored inputs
                                    if input_code in self.ignored_inputs:
                                        logger.debug(f"Ignoring filtered axis input: {input_code}")
                                    else:
                                        result_dict["code"] = input_code
                                        result_dict["description"] = f"Joystick {js_num} {axis_name.upper()} ({direction})"
                                        detected_event.set()
                                        return
                            else:
                                # Reset state when axis returns below threshold
                                state_key = (js_num, axis_name)
                                if state_key in previous_axis_state:
                                    previous_axis_state[state_key] = value

                    time.sleep(0.01)  # 10ms polling for pygame events

                except Exception as e:
                    logger.debug(f"Error in joystick detection loop: {e}")
                    time.sleep(0.01)

        except ImportError:
            logger.error("pygame not installed. Joystick detection unavailable. Install with: pip install pygame")
        except Exception as e:
            logger.error(f"Error in joystick detection: {e}", exc_info=True)

    def _on_keyboard_press(self, key, detected_event, result_dict, listener=None):
        """Handle keyboard key press (callback from pynput)"""
        try:
            from pynput.keyboard import Key

            if not self.running:
                return False  # Stop listener

            # If input already detected, stop processing further events
            if detected_event.is_set():
                return False

            # Track modifier keys - build map safely to handle missing Key attributes
            modifier_key_map = {
                Key.ctrl_l: "lctrl",
                Key.ctrl_r: "rctrl",
                Key.alt_l: "lalt",
                Key.shift_l: "lshift",
                Key.shift_r: "rshift",
            }

            # Add alt_r if it exists on this system
            if hasattr(Key, 'alt_r'):
                try:
                    modifier_key_map[Key.alt_r] = "ralt"
                except AttributeError:
                    pass  # Key.alt_r not available on this system

            # Handle AltGr (Right Alt on non-US keyboards) - treat it as ralt
            # pynput reports it as Key.alt_gr on some systems
            alt_gr_key = None
            try:
                alt_gr_key = Key.alt_gr
            except AttributeError:
                pass  # Key.alt_gr not available on this system

            if alt_gr_key and key == alt_gr_key:
                # Detect AltGr as RALT key if pressed alone (for non-US keyboards)
                # Check if we should emit it as a standalone key or continue listening
                self.active_modifiers["ralt"] = True
                self.modifier_press_time["ralt"] = time.time()
                self.other_key_pressed = False  # Reset flag for this modifier press
                return True  # Continue listening to see if another key follows

            # If this is a modifier key being pressed, track it and continue listening
            # This allows detection of modifiers alone (Shift, Ctrl, Alt) or in combinations
            if key in modifier_key_map and modifier_key_map[key] in ["lctrl", "rctrl", "lalt", "ralt", "lshift", "rshift"]:
                modifier_name = modifier_key_map[key]
                self.active_modifiers[modifier_name] = True
                self.modifier_press_time[modifier_name] = time.time()  # Record when pressed
                self.other_key_pressed = False  # Reset flag for this modifier press
                # Continue listening to see if another key follows
                return True

            # Get the currently active modifier (if any)
            modifier = self._get_active_modifier_from_state()

            # Get key name
            key_name = self._get_key_name_from_pynput_key(key, modifier)

            # Skip if we couldn't determine a key name
            if not key_name:
                return True  # Continue listening

            # Mark that a non-modifier key was pressed (for tracking if we should emit modifier alone)
            self.other_key_pressed = True

            # Special handling for space key - normalize it
            if key_name == ' ':
                key_name = 'space'

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
            logger.info(f"Keyboard input detected: {input_code} - {result_dict['description']}")

            # Set flag to stop all listeners
            self.stop_listeners_flag = True

            return False  # Stop listener

        except Exception as e:
            logger.error(f"Error handling keyboard press: {e}", exc_info=True)
            return True  # Continue listening

    def _get_key_name_from_pynput_key(self, key, active_modifier: Optional[str] = None) -> Optional[str]:
        """
        Extract key name from pynput key object.
        Handles special cases like Ctrl+letter combinations which pynput reports as control characters.
        Also handles numpad keys and RALT detection.

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

                # Map numpad Key names to Star Citizen numpad format
                # pynput may report numpad keys with different names depending on platform
                numpad_key_map = {
                    # Standard pynput numpad names
                    'num_lock': 'num_lock',
                    'numlock': 'num_lock',
                    'np_0': 'np_0', 'np_1': 'np_1', 'np_2': 'np_2', 'np_3': 'np_3',
                    'np_4': 'np_4', 'np_5': 'np_5', 'np_6': 'np_6', 'np_7': 'np_7',
                    'np_8': 'np_8', 'np_9': 'np_9',
                    'np_multiply': 'np_multiply', 'multiply': 'np_multiply',
                    'np_add': 'np_add', 'add': 'np_add',
                    'np_subtract': 'np_subtract', 'subtract': 'np_subtract',
                    'np_divide': 'np_divide', 'divide': 'np_divide',
                    'np_decimal': 'np_period', 'decimal': 'np_period',
                    'np_enter': 'np_enter',
                }

                # Check if this is a mapped numpad key
                if key_name in numpad_key_map:
                    return numpad_key_map[key_name]

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

                # When Shift is pressed, pynput reports the shifted character instead of the base key
                # We need to map shifted characters back to their base key names
                if active_modifier and active_modifier in ("lshift", "rshift"):
                    # Map shifted characters back to their base keys
                    # These map to Star Citizen's key names (kb1_equals not kb1_equal, etc.)
                    shift_char_map = {
                        '!': '1',
                        '@': '2',
                        '#': '3',
                        '$': '4',
                        '%': '5',
                        '^': '6',
                        '&': '7',
                        '*': '8',
                        '(': '9',
                        ')': '0',
                        '_': 'minus',
                        '+': 'equals',
                        '{': 'bracketleft',
                        '}': 'bracketright',
                        '|': 'backslash',
                        ':': 'semicolon',
                        '"': 'apostrophe',
                        '<': 'comma',
                        '>': 'period',
                        '?': 'slash',
                        '~': 'grave',
                    }

                    if char in shift_char_map:
                        return shift_char_map[char]

                # Handle numpad character keys that pynput reports as characters
                # Note: pynput doesn't always distinguish between numpad and regular keyboard for numbers
                # We assume these characters come from the numpad when no other modifier is active
                if not active_modifier:
                    numpad_char_map = {
                        '0': 'np_0', '1': 'np_1', '2': 'np_2', '3': 'np_3', '4': 'np_4',
                        '5': 'np_5', '6': 'np_6', '7': 'np_7', '8': 'np_8', '9': 'np_9',
                        '.': 'np_period',
                        '\r': 'np_enter',  # Numpad enter reports as carriage return
                    }

                    if char in numpad_char_map:
                        return numpad_char_map[char]

                return char

            return str(key) if key else None

        except Exception as e:
            logger.debug(f"Error getting key name from pynput key: {e}")
            return None

    def _on_keyboard_release(self, key, detected_event, result_dict, listener=None):
        """Handle keyboard key release (callback from pynput)"""
        try:
            from pynput.keyboard import Key

            if not self.running:
                return False  # Stop listener

            # If input already detected, stop processing further events
            if detected_event.is_set():
                if listener:
                    try:
                        listener.stop()
                    except:
                        pass
                return False

            # Track modifier keys being released - build map safely to handle missing Key attributes
            modifier_key_map = {
                Key.ctrl_l: "lctrl",
                Key.ctrl_r: "rctrl",
                Key.alt_l: "lalt",
                Key.shift_l: "lshift",
                Key.shift_r: "rshift",
            }

            # Add alt_r if it exists on this system
            if hasattr(Key, 'alt_r'):
                try:
                    modifier_key_map[Key.alt_r] = "ralt"
                except AttributeError:
                    pass  # Key.alt_r not available on this system

            # Handle AltGr (Right Alt on non-US keyboards) - treat it as ralt
            alt_gr_key = None
            try:
                alt_gr_key = Key.alt_gr
            except AttributeError:
                pass  # Key.alt_gr not available on this system

            if alt_gr_key and key == alt_gr_key:
                # Check if AltGr/RALT was pressed alone (no other key pressed after it)
                if self.active_modifiers["ralt"] and not self.other_key_pressed:
                    # Emit the RALT key alone
                    input_code = "kb1_ralt"
                    result_dict["code"] = input_code
                    result_dict["description"] = "Keyboard Right Alt"
                    detected_event.set()
                    logger.info(f"Detected AltGr/RALT key alone: {input_code}")

                    # Set flag to stop all listeners
                    self.stop_listeners_flag = True
                    return False  # Stop listener

                self.active_modifiers["ralt"] = False
                return True  # Continue listening

            if key in modifier_key_map:
                modifier_name = modifier_key_map[key]

                # Check if this modifier was pressed alone (no other key pressed after it)
                if self.active_modifiers[modifier_name] and not self.other_key_pressed:
                    # Emit the modifier key alone
                    modifier_description_map = {
                        "lctrl": "Left Ctrl",
                        "rctrl": "Right Ctrl",
                        "lalt": "Left Alt",
                        "ralt": "Right Alt",
                        "lshift": "Left Shift",
                        "rshift": "Right Shift",
                    }

                    input_code = f"kb1_{modifier_name}"
                    result_dict["code"] = input_code
                    result_dict["description"] = f"Keyboard {modifier_description_map.get(modifier_name, modifier_name)}"
                    detected_event.set()
                    logger.info(f"Detected modifier key alone: {input_code} - {result_dict['description']}")

                    # Set flag to stop all listeners
                    self.stop_listeners_flag = True

                    return False  # Stop listener

                self.active_modifiers[modifier_name] = False

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

    def _on_mouse_click(self, button, pressed, detected_event, result_dict, listener=None):
        """Handle mouse button click (callback from pynput)"""
        try:
            from pynput.mouse import Button

            if not self.running or not pressed:
                return True  # Continue listening

            # If input already detected, stop processing further events
            if detected_event.is_set():
                if listener:
                    try:
                        listener.stop()
                    except:
                        pass
                return False

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
                logger.info(f"Mouse input detected: {input_code} - {description}")

                # Set flag to stop all listeners
                self.stop_listeners_flag = True

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

            # Add joysticks using pygame
            try:
                import pygame
                pygame.init()

                # Quit and reinitialize joystick module to detect hot-swapped devices
                pygame.joystick.quit()
                pygame.joystick.init()

                joystick_count = pygame.joystick.get_count()
                instance_counter = 0

                for i in range(joystick_count):
                    try:
                        joy = pygame.joystick.Joystick(i)
                        joy.init()
                        instance_counter += 1
                        devices.append({
                            "type": "joystick",
                            "instance": instance_counter,
                            "name": joy.get_name()
                        })
                    except Exception as e:
                        logger.debug(f"Could not initialize joystick {i}: {e}")
                        # Skip unavailable joysticks instead of adding them to the list

            except ImportError:
                logger.warning("pygame not available, joystick detection skipped")
            except Exception as e:
                logger.error(f"Error detecting joysticks: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error getting devices: {e}", exc_info=True)

        return devices
