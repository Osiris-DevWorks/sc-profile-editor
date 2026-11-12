"""
Joystick backends: where device lists and raw joystick events come from.

The rest of the app never talks to pygame directly. It asks the active
backend for two things:

* ``list_joysticks()`` — the connected sticks, in SC instance order
  (index 0 is js1). Each entry is a ``JoystickInfo``.
* ``open()`` / ``poll()`` / ``close()`` — a stream of normalized
  ``JoyEvent`` objects while the Remap Dialog is listening.

Two implementations ship:

``PygameBackend``
    The real thing (SDL via pygame). Default.

``MockBackend``
    Virtual sticks described in a JSON file, so the app and the tests run
    on a machine with no joysticks attached. Events come from three
    places: ``inject()`` (the Virtual Joystick panel and tests use it), a
    ``script`` list in the JSON file (timed replays of a recorded
    session), or both.

Select the mock with either:

* ``python src/main.py --mock-joysticks [devices.json]``
* ``SCPE_MOCK_JOYSTICKS=devices.json`` (or ``=1`` for the default preset)

Translating a ``JoyEvent`` into an SC input code (``js1_button5``,
``js2_hat1_up``, ``js1_rotz``) lives in ``translate_event()`` here, so it
is shared by both backends and covered by plain unit tests.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

ENV_VAR = "SCPE_MOCK_JOYSTICKS"
CLI_FLAG = "--mock-joysticks"

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_MOCK_DEVICES = os.path.join(_REPO_ROOT, "tests", "fixtures", "mock_devices", "vkb_gladiator_twcs.json")

# pygame axis index -> SC axis name (unchanged from the original detector).
AXIS_NAMES = {
    0: "x",
    1: "y",
    2: "z",
    3: "rotz",
    4: "rotx",
    5: "roty",
    6: "slider1",
    7: "slider2",
}
AXIS_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class JoyEvent:
    """One raw joystick event, 0-based like pygame.

    kind:  "button" (value 1 = pressed, 0 = released),
           "hat"    (value (x, y) with each in -1/0/1),
           "axis"   (value float in -1.0..1.0)
    joy:   0-based joystick index (0 -> js1)
    index: 0-based button / hat / axis number
    """
    kind: str
    joy: int
    index: int
    value: object = 1


@dataclass
class JoystickInfo:
    name: str
    vid_pid: Optional[Tuple[int, int]] = None
    buttons: int = 32
    hats: int = 1
    axes: int = 8


# ---------------------------------------------------------------------------
# Event -> SC input code
# ---------------------------------------------------------------------------

def translate_event(
    event: JoyEvent,
    axis_state: Optional[Dict[Tuple[int, str], float]] = None,
    ignored: Optional[Set[str]] = None,
) -> Optional[Tuple[str, str]]:
    """Turn a ``JoyEvent`` into ``(input_code, description)``.

    Returns None for events that do not count as an input (button
    release, hat centered, axis below threshold, ignored inputs).
    ``axis_state`` is caller-owned and lets an axis fire once per crossing
    of the threshold rather than on every motion event.
    """
    ignored = ignored or set()
    js_num = event.joy + 1

    if event.kind == "button":
        if not event.value:
            return None
        button_num = event.index + 1
        if button_num < 1 or button_num > 100:
            logger.warning(f"Suspicious button number: {event.index} (raw) for js{js_num}")
        code = f"js{js_num}_button{button_num}"
        desc = f"Joystick {js_num} Button {button_num}"

    elif event.kind == "hat":
        x, y = event.value
        if y == 1:
            direction = "up"
        elif y == -1:
            direction = "down"
        elif x == 1:
            direction = "right"
        elif x == -1:
            direction = "left"
        else:
            return None
        hat_num = event.index + 1
        code = f"js{js_num}_hat{hat_num}_{direction}"
        desc = f"Joystick {js_num} Hat {hat_num} {direction.upper()}"

    elif event.kind == "axis":
        value = float(event.value)
        axis_name = AXIS_NAMES.get(event.index, f"axis{event.index}")
        state = axis_state if axis_state is not None else {}
        key = (js_num, axis_name)
        previous = state.get(key)
        state[key] = value
        if abs(value) <= AXIS_THRESHOLD:
            return None
        if previous is not None and abs(previous) > AXIS_THRESHOLD:
            return None  # still past the threshold from an earlier event
        code = f"js{js_num}_{axis_name}"
        desc = f"Joystick {js_num} {axis_name.upper()} ({'+' if value > 0 else '-'})"

    else:
        return None

    if code in ignored:
        logger.debug(f"Ignoring filtered input: {code}")
        return None
    return code, desc


def joystick_infos_to_devices(infos: List[JoystickInfo]) -> List[dict]:
    """The device-dict shape ``InputDetector.get_available_devices()`` returns."""
    return [
        {"type": "joystick", "instance": i + 1, "name": info.name, "vid_pid": info.vid_pid}
        for i, info in enumerate(infos)
    ]


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

class JoystickBackend:
    name = "base"
    is_mock = False

    def list_joysticks(self) -> List[JoystickInfo]:
        raise NotImplementedError

    def open(self) -> int:
        """Start an event session. Returns how many sticks are listening."""
        raise NotImplementedError

    def poll(self) -> List[JoyEvent]:
        raise NotImplementedError

    def close(self) -> None:
        pass


class PygameBackend(JoystickBackend):
    """SDL joysticks via pygame. This is the code path that used to live
    inline in ``input_detector.py``; behavior is unchanged."""

    name = "pygame"

    def __init__(self):
        self._joysticks = []

    def list_joysticks(self) -> List[JoystickInfo]:
        infos: List[JoystickInfo] = []
        try:
            import pygame
        except ImportError:
            logger.warning("pygame not available, joystick detection skipped")
            return infos

        pygame.init()
        # Quit and reinitialize to pick up hot-swapped devices.
        pygame.joystick.quit()
        pygame.joystick.init()

        from utils.directinput_guid import parse_sdl_joystick_guid

        for i in range(pygame.joystick.get_count()):
            try:
                joy = pygame.joystick.Joystick(i)
                joy.init()
            except Exception as e:
                logger.debug(f"Could not initialize joystick {i}: {e}")
                continue
            vid_pid = None
            try:
                sdl_guid = joy.get_guid()
                vid_pid = parse_sdl_joystick_guid(sdl_guid)
                if vid_pid:
                    logger.debug(
                        f"Joystick {len(infos) + 1} ({joy.get_name()}): "
                        f"VID=0x{vid_pid[0]:04X} PID=0x{vid_pid[1]:04X} (SDL GUID: {sdl_guid})"
                    )
            except Exception as e:
                logger.debug(f"Could not extract VID/PID for joystick {i}: {e}")
            infos.append(JoystickInfo(
                name=joy.get_name(),
                vid_pid=vid_pid,
                buttons=joy.get_numbuttons(),
                hats=joy.get_numhats(),
                axes=joy.get_numaxes(),
            ))
        return infos

    def open(self) -> int:
        import pygame

        pygame.init()
        pygame.joystick.init()

        # Windows needs an active display context for joystick events.
        try:
            pygame.display.set_mode((1, 1))
            if sys.platform == "win32":
                try:
                    import ctypes
                    hwnd = ctypes.windll.user32.FindWindowW(None, "pygame window")
                    if hwnd:
                        ctypes.windll.user32.SetWindowPos(hwnd, 0, -10000, -10000, 1, 1, 0x0001)
                        logger.debug("Moved pygame window off-screen")
                except Exception as e:
                    logger.debug(f"Could not move window off-screen: {e}")
            logger.info("Created pygame display window for joystick event handling")
        except Exception as e:
            logger.error(f"Could not create pygame display: {e}", exc_info=True)
            logger.warning("Continuing without pygame display - joystick events may not be detected")

        self._joysticks = []
        for i in range(pygame.joystick.get_count()):
            try:
                joy = pygame.joystick.Joystick(i)
                joy.init()
                self._joysticks.append(joy)
                logger.info(f"Initialized joystick {i + 1}: {joy.get_name()}")
            except Exception as e:
                logger.warning(f"Could not initialize joystick {i}: {e}")
        return len(self._joysticks)

    def poll(self) -> List[JoyEvent]:
        import pygame

        pygame.event.pump()
        events: List[JoyEvent] = []
        for ev in pygame.event.get():
            try:
                if ev.type == pygame.JOYBUTTONDOWN:
                    events.append(JoyEvent("button", ev.joy, ev.button, 1))
                elif ev.type == pygame.JOYHATMOTION:
                    events.append(JoyEvent("hat", ev.joy, ev.hat, tuple(ev.value)))
                elif ev.type == pygame.JOYAXISMOTION:
                    events.append(JoyEvent("axis", ev.joy, ev.axis, ev.value))
            except AttributeError as e:
                logger.error(f"Malformed pygame joystick event {ev}: {e}")
        return events


class MockBackend(JoystickBackend):
    """Virtual joysticks for machines with no hardware.

    JSON format (see tests/fixtures/mock_devices/)::

        {
          "devices": [
            {"name": "VKBsim Gladiator EVO R", "vid": "0x231D", "pid": "0x0200",
             "buttons": 34, "hats": 1, "axes": 6}
          ],
          "script": [
            {"after_ms": 500, "kind": "button", "js": 1, "button": 5}
          ]
        }

    Device identity can also be given as ``"product"`` with a DirectInput
    GUID copied straight from an SC profile, e.g.
    ``"{0200231D-0000-0000-0000-504944564944}"``.

    Script entries use SC's 1-based numbering (``js``, ``button``, ``hat``)
    so a fixture reads like the input codes it produces. Axis entries take
    ``"axis": "rotz"`` (or a 0-based number) and a ``"value"``.
    """

    name = "mock"
    is_mock = True

    def __init__(self, devices: List[JoystickInfo], script: Optional[List[dict]] = None, source: str = ""):
        self.devices = list(devices)
        self.script = list(script or [])
        self.source = source
        self._queue: "queue.Queue[JoyEvent]" = queue.Queue()
        self._pending_script: List[Tuple[float, JoyEvent]] = []
        self._lock = threading.Lock()
        self._listening = False

    # -- construction -----------------------------------------------------

    @classmethod
    def from_file(cls, path: str) -> "MockBackend":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data, source=path)

    @classmethod
    def from_path(cls, path: str) -> "MockBackend":
        """A devices JSON file, or an SC profile XML to mirror."""
        if path.lower().endswith(".xml"):
            return cls(devices_from_profile(path), source=path)
        return cls.from_file(path)

    def set_devices(self, devices: List[JoystickInfo], source: str = "") -> None:
        """Swap the virtual sticks (e.g. to match a newly opened profile)."""
        with self._lock:
            self.devices = list(devices)
            self.source = source
            self._drain()

    @classmethod
    def from_dict(cls, data: dict, source: str = "") -> "MockBackend":
        from utils.directinput_guid import parse_di_product_guid

        devices = []
        for d in data.get("devices", []):
            vid_pid = None
            if "vid" in d and "pid" in d:
                vid_pid = (_as_int(d["vid"]), _as_int(d["pid"]))
            elif "product" in d:
                vid_pid = parse_di_product_guid(d["product"])
            devices.append(JoystickInfo(
                name=d["name"],
                vid_pid=vid_pid,
                buttons=int(d.get("buttons", 32)),
                hats=int(d.get("hats", 1)),
                axes=int(d.get("axes", 8)),
            ))
        return cls(devices, data.get("script"), source)

    # -- backend API ------------------------------------------------------

    def list_joysticks(self) -> List[JoystickInfo]:
        return list(self.devices)

    def open(self) -> int:
        with self._lock:
            # Drop anything clicked while nobody was listening.
            self._drain()
            start = time.monotonic()
            self._pending_script = sorted(
                ((start + entry.get("after_ms", 0) / 1000.0, script_entry_to_event(entry))
                 for entry in self.script),
                key=lambda pair: pair[0],
            )
            self._listening = True
        return len(self.devices)

    def poll(self) -> List[JoyEvent]:
        events = self._drain()
        now = time.monotonic()
        with self._lock:
            while self._pending_script and self._pending_script[0][0] <= now:
                events.append(self._pending_script.pop(0)[1])
        return events

    def close(self) -> None:
        with self._lock:
            self._listening = False
            self._pending_script = []

    # -- simulation -------------------------------------------------------

    @property
    def listening(self) -> bool:
        return self._listening

    def inject(self, event: JoyEvent) -> None:
        """Queue an event as if the virtual stick produced it."""
        if not 0 <= event.joy < len(self.devices):
            raise ValueError(f"No mock joystick at index {event.joy} (have {len(self.devices)})")
        self._queue.put(event)

    def _drain(self) -> List[JoyEvent]:
        out = []
        while True:
            try:
                out.append(self._queue.get_nowait())
            except queue.Empty:
                return out


_INPUT_RE = re.compile(r"\bjs(\d+)_(button|hat)(\d+)", re.IGNORECASE)
_ANY_JS_RE = re.compile(r"\bjs(\d+)_", re.IGNORECASE)


def devices_from_profile(path: str) -> List[JoystickInfo]:
    """Build virtual sticks that mirror the joysticks in an SC profile XML.

    Names and VID/PID come from ``<options type="joystick" instance="N"
    Product="Name {GUID}">``. Button and hat counts are the highest ones
    the profile binds, with a floor of 32 buttons and 1 hat, so
    every binding in the profile has a control to click. Instance gaps
    get a placeholder so js numbering stays aligned with the profile.
    """
    import xml.etree.ElementTree as ET
    from utils.directinput_guid import parse_di_product_guid

    root = ET.parse(path).getroot()

    products: Dict[int, str] = {}
    for opt in root.iter("options"):
        if (opt.get("type") or "").lower() != "joystick":
            continue
        try:
            instance = int(opt.get("instance", "1"))
        except ValueError:
            continue
        products.setdefault(instance, opt.get("Product", "") or "")

    max_button: Dict[int, int] = {}
    max_hat: Dict[int, int] = {}
    seen: Set[int] = set(products)
    for elem in root.iter():
        value = elem.get("input")
        if not value:
            continue
        for m in _ANY_JS_RE.finditer(value):
            seen.add(int(m.group(1)))
        for m in _INPUT_RE.finditer(value):
            js, kind, num = int(m.group(1)), m.group(2).lower(), int(m.group(3))
            table = max_button if kind == "button" else max_hat
            table[js] = max(table.get(js, 0), num)

    seen.discard(0)
    if not seen:
        return []

    devices = []
    for js in range(1, max(seen) + 1):
        product = products.get(js, "")
        name = product.split("{")[0].strip() if product else ""
        devices.append(JoystickInfo(
            name=name or f"Virtual stick js{js}",
            vid_pid=parse_di_product_guid(product) if product else None,
            buttons=max(max_button.get(js, 0), 32),
            hats=max(max_hat.get(js, 0), 1),
            axes=8,
        ))
    return devices


def script_entry_to_event(entry: dict) -> JoyEvent:
    """Convert a fixture/script entry (1-based, SC-style) to a ``JoyEvent``."""
    kind = entry["kind"]
    joy = int(entry.get("js", 1)) - 1
    if kind == "button":
        return JoyEvent("button", joy, int(entry["button"]) - 1, int(entry.get("value", 1)))
    if kind == "hat":
        directions = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0), "center": (0, 0)}
        value = entry.get("value", "up")
        value = directions[value] if isinstance(value, str) else tuple(value)
        return JoyEvent("hat", joy, int(entry.get("hat", 1)) - 1, value)
    if kind == "axis":
        axis = entry["axis"]
        if isinstance(axis, str):
            by_name = {v: k for k, v in AXIS_NAMES.items()}
            axis = by_name[axis]
        return JoyEvent("axis", joy, int(axis), float(entry.get("value", 1.0)))
    raise ValueError(f"Unknown script event kind: {kind!r}")


def _as_int(v) -> int:
    return int(v, 0) if isinstance(v, str) else int(v)


# ---------------------------------------------------------------------------
# Active backend
# ---------------------------------------------------------------------------

# The app imports this package both as ``utils.*`` and ``src.utils.*``,
# which gives two copies of this module. Keep the active backend in one
# holder both copies share, so every caller sees the same (mock) sticks.
_STATE_KEY = "_scpe_joystick_backend_state"
if _STATE_KEY not in sys.modules:
    import types
    sys.modules[_STATE_KEY] = types.SimpleNamespace(active=None, lock=threading.Lock())
_state = sys.modules[_STATE_KEY]


def configure_from_argv(argv: List[str]) -> Optional[str]:
    """Strip ``--mock-joysticks [path]`` from argv and record it in the
    environment so the choice also reaches anything that reads the env.
    Returns the devices file path if the flag was present."""
    if CLI_FLAG not in argv:
        for i, arg in enumerate(argv):
            if arg.startswith(CLI_FLAG + "="):
                path = arg.split("=", 1)[1] or DEFAULT_MOCK_DEVICES
                del argv[i]
                os.environ[ENV_VAR] = path
                return path
        return None
    i = argv.index(CLI_FLAG)
    path = DEFAULT_MOCK_DEVICES
    if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
        path = argv[i + 1]
        del argv[i + 1]
    del argv[i]
    os.environ[ENV_VAR] = path
    return path


def _backend_from_env() -> JoystickBackend:
    value = os.environ.get(ENV_VAR, "").strip()
    if not value or value.lower() in ("0", "false", "no", "off"):
        return PygameBackend()
    path = DEFAULT_MOCK_DEVICES if value.lower() in ("1", "true", "yes", "on") else value
    try:
        backend = MockBackend.from_path(path)
    except (OSError, ValueError, KeyError, SyntaxError) as e:
        logger.error(f"Could not load mock joysticks from {path!r} ({e}); using real joysticks")
        return PygameBackend()
    logger.warning(f"Using MOCK joysticks from {path}: {[d.name for d in backend.devices]}")
    return backend


def get_backend() -> JoystickBackend:
    with _state.lock:
        if _state.active is None:
            _state.active = _backend_from_env()
        return _state.active


def set_backend(backend: Optional[JoystickBackend]) -> None:
    """Install a backend (tests), or None to re-read the environment next time."""
    with _state.lock:
        _state.active = backend
