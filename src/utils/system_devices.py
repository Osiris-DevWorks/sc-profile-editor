"""The joysticks this PC has connected, in the order the game numbers them.

Star Citizen reads joysticks through DirectInput and numbers them js1, js2,
... in the order DirectInput enumerates game controllers. When that order
changes (a stick re-plugged into another USB port, a Windows update, a new
device), every binding written for jsN lands on whichever stick is now Nth.

``list_system_joysticks()`` returns the connected sticks in that order:

- With ``--mock-joysticks`` the virtual sticks are the system, in panel order,
  so the check is testable without hardware.
- On Windows the list comes from DirectInput itself (``dinput8.dll`` via
  ctypes, no extra dependency), which is the order the game uses.
- Otherwise it falls back to the joystick backend (pygame/SDL). SDL can list
  sticks in a different order than DirectInput, so the result is marked as
  approximate.

Button/hat counts come from the joystick backend, matched by VID/PID, since
DirectInput enumeration does not report them.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

from utils.joystick_backend import JoystickInfo, get_backend

logger = logging.getLogger(__name__)

SOURCE_DIRECTINPUT = "directinput"
SOURCE_PYGAME = "pygame"
SOURCE_MOCK = "mock"


@dataclass
class SystemJoysticks:
    devices: List[JoystickInfo]
    source: str            # one of the SOURCE_* constants
    exact_order: bool      # True when the order is the one the game uses

    @property
    def source_label(self) -> str:
        if self.source == SOURCE_MOCK:
            return "virtual joysticks (--mock-joysticks)"
        if self.source == SOURCE_DIRECTINPUT:
            return "Windows DirectInput (the order Star Citizen uses)"
        return "pygame/SDL (order may differ from the game's)"


def list_system_joysticks() -> SystemJoysticks:
    backend = get_backend()
    if getattr(backend, "is_mock", False):
        return SystemJoysticks(list(backend.list_joysticks()), SOURCE_MOCK, True)

    backend_devices: List[JoystickInfo] = []
    try:
        backend_devices = list(backend.list_joysticks())
    except Exception as e:  # pragma: no cover - hardware dependent
        logger.warning(f"Joystick backend could not list devices: {e}")

    if sys.platform == "win32":
        try:
            di = enumerate_directinput_joysticks()
        except Exception as e:  # pragma: no cover - Windows only
            logger.warning(f"DirectInput enumeration failed, using pygame order: {e}")
            di = None
        if di is not None:
            return SystemJoysticks(_merge_capabilities(di, backend_devices), SOURCE_DIRECTINPUT, True)

    return SystemJoysticks(backend_devices, SOURCE_PYGAME, False)


def _merge_capabilities(ordered: List[Tuple[str, Optional[Tuple[int, int]]]],
                        caps: List[JoystickInfo]) -> List[JoystickInfo]:
    """Attach button/hat/axis counts from ``caps`` to DirectInput's list.

    Identical models (same VID/PID) are paired up in order. A device the
    backend could not see keeps generous defaults so it never triggers a
    "this stick has no such button" finding by mistake.
    """
    remaining = list(caps)
    out: List[JoystickInfo] = []
    for name, vid_pid in ordered:
        match = None
        for i, info in enumerate(remaining):
            if vid_pid is not None and info.vid_pid == vid_pid:
                match = remaining.pop(i)
                break
        if match is not None:
            out.append(JoystickInfo(name=name, vid_pid=vid_pid, buttons=match.buttons,
                                    hats=match.hats, axes=match.axes))
        else:
            out.append(JoystickInfo(name=name, vid_pid=vid_pid, buttons=128, hats=4, axes=8))
    return out


def _looks_like_xinput_pad(name: str) -> bool:
    n = (name or "").lower()
    return "xbox" in n or n.startswith("controller (")


def enumerate_directinput_joysticks() ->List[Tuple[str, Optional[Tuple[int, int]]]]:  # pragma: no cover - Windows only
    """Attached game controllers in DirectInput enumeration order.

    Returns ``[(product_name, (vid, pid) or None), ...]``.
    """
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                    ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]

    class DIDEVICEINSTANCEW(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD),
                    ("guidInstance", GUID),
                    ("guidProduct", GUID),
                    ("dwDevType", wintypes.DWORD),
                    ("tszInstanceName", ctypes.c_wchar * 260),
                    ("tszProductName", ctypes.c_wchar * 260),
                    ("guidFFDriver", GUID),
                    ("wUsagePage", wintypes.WORD),
                    ("wUsage", wintypes.WORD)]

    DIRECTINPUT_VERSION = 0x0800
    DI8DEVCLASS_GAMECTRL = 4
    DIEDFL_ATTACHEDONLY = 1
    DIENUM_CONTINUE = 1
    PIDVID = bytes(b"\x00\x00PIDVID")  # Data4 of a DirectInput product GUID

    iid = GUID(0xBF798031, 0x483A, 0x4DA2,
               (ctypes.c_ubyte * 8)(0xAA, 0x99, 0x5D, 0x64, 0xED, 0x36, 0x97, 0x00))

    dinput8 = ctypes.WinDLL("dinput8")
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    dinput8.DirectInput8Create.restype = ctypes.c_long
    dinput8.DirectInput8Create.argtypes = [wintypes.HINSTANCE, wintypes.DWORD, ctypes.POINTER(GUID),
                                           ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]

    di = ctypes.c_void_p()
    hr = dinput8.DirectInput8Create(kernel32.GetModuleHandleW(None), DIRECTINPUT_VERSION,
                                    ctypes.byref(iid), ctypes.byref(di), None)
    if hr != 0 or not di.value:
        raise OSError(f"DirectInput8Create failed (HRESULT 0x{hr & 0xFFFFFFFF:08X})")

    vtbl = ctypes.cast(di, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, ctypes.POINTER(DIDEVICEINSTANCEW), ctypes.c_void_p)
    EnumDevices = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.DWORD, CALLBACK,
                                     ctypes.c_void_p, wintypes.DWORD)(vtbl[4])
    Release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])

    found: List[Tuple[str, Optional[Tuple[int, int]]]] = []

    def on_device(inst_ptr, _ref):
        inst = inst_ptr.contents
        prod = inst.guidProduct
        vid_pid = None
        if bytes(prod.Data4) == PIDVID and prod.Data2 == 0 and prod.Data3 == 0:
            vid_pid = (prod.Data1 & 0xFFFF, (prod.Data1 >> 16) & 0xFFFF)
        name = inst.tszProductName or inst.tszInstanceName
        # Xbox-style pads are XInput "gamepad" devices to the game, not jsN.
        if not _looks_like_xinput_pad(name):
            found.append((name, vid_pid))
        return DIENUM_CONTINUE

    callback = CALLBACK(on_device)
    try:
        hr = EnumDevices(di, DI8DEVCLASS_GAMECTRL, callback, None, DIEDFL_ATTACHEDONLY)
        if hr != 0:
            raise OSError(f"EnumDevices failed (HRESULT 0x{hr & 0xFFFFFFFF:08X})")
    finally:
        Release(di)
    return found
