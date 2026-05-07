"""DirectInput product-GUID resolution.

Star Citizen profile XML stores HOTAS / joystick devices as:

    <options type="joystick" instance="1"
             Product="VKB-Sim Space Gunfighter  {0126231D-0000-0000-0000-504944564944}"/>

The GUID is the DirectInput **product** GUID (model-level — every unit of the
same model produces the same GUID). The format is fully specified:

    {(PID:u16) (VID:u16)-0000-0000-0000-504944564944}

where the trailing constant `504944564944` is "PIDVID" in ASCII (0x50='P',
0x49='I', 0x44='D', 0x56='V', 0x49='I', 0x44='D'). The first 8 hex chars
of the first group encode (PID << 16) | VID.

Because the GUID is a pure function of VID/PID, we can match a connected
device against a profile entry without ever calling DirectInput. We just
need VID/PID, which `pygame.joystick.Joystick.get_guid()` already exposes
in SDL's joystick-GUID format.

This module has zero runtime dependencies — it's pure parsing.
"""
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# Trailing constant of every DirectInput product GUID — "PIDVID" as bytes.
_PIDVID_TAIL = "504944564944"


# Matches "{HHHHHHHH-0000-0000-0000-504944564944}" anywhere in a string,
# case-insensitive. Intentionally tolerant: SC profile attributes embed
# the GUID inside a wider string like "VKB-Sim Space Gunfighter {GUID}".
_DI_PRODUCT_GUID_RE = re.compile(
    r"\{([0-9A-Fa-f]{8})-0{4}-0{4}-0{4}-" + _PIDVID_TAIL + r"\}",
    re.IGNORECASE,
)


def parse_di_product_guid(text: str) -> Optional[Tuple[int, int]]:
    """Extract (vid, pid) from a DirectInput product GUID.

    Accepts any string that contains a DI product GUID — the bare GUID,
    the full SC profile Product string ("Name {GUID}"), or with extra
    whitespace. Returns None if the input doesn't contain a recognizable
    DI product GUID, including for keyboard/mouse class GUIDs which use
    a different signature (e.g. `6F1D2B61-D5A0-11CF-BFC7-444553540000`).
    """
    if not text:
        return None
    match = _DI_PRODUCT_GUID_RE.search(text)
    if not match:
        return None
    data1 = int(match.group(1), 16)
    pid = (data1 >> 16) & 0xFFFF
    vid = data1 & 0xFFFF
    return (vid, pid)


def make_di_product_guid(vid: int, pid: int) -> str:
    """Construct the canonical DirectInput product GUID from VID/PID.

    Output is always uppercase and braced, matching the format SC writes
    to profile XML. Round-trips with parse_di_product_guid().
    """
    if not (0 <= vid <= 0xFFFF and 0 <= pid <= 0xFFFF):
        raise ValueError(f"VID/PID out of u16 range: vid={vid}, pid={pid}")
    data1 = ((pid & 0xFFFF) << 16) | (vid & 0xFFFF)
    return f"{{{data1:08X}-0000-0000-0000-{_PIDVID_TAIL.upper()}}}"


def parse_sdl_joystick_guid(guid_hex: str) -> Optional[Tuple[int, int]]:
    """Extract (vid, pid) from an SDL joystick GUID string.

    SDL's joystick GUID is a 16-byte struct serialized as 32 lowercase hex
    chars. On Windows the layout is:

        Offset  Field
        ------  -----
        0-1     bus type (LE u16; 0x0003 = USB)
        2-3     CRC16 of name (LE u16; often 0)
        4-5     vendor ID (LE u16)
        6-7     padding
        8-9     product ID (LE u16)
        10-11   padding
        12-13   version (LE u16)
        14-15   driver signature/data

    pygame's `Joystick.get_guid()` returns this string. Some pygame
    builds/platforms may produce a different layout (e.g. XInput devices
    produce a synthetic GUID with VID/PID elsewhere) — we return None for
    anything we can't confidently parse rather than guess.
    """
    if not guid_hex:
        return None
    g = guid_hex.replace("-", "").strip().lower()
    if len(g) != 32 or not all(c in "0123456789abcdef" for c in g):
        return None

    # Bus type tells us whether the layout above applies. USB (0x03) and
    # Bluetooth (0x05) both follow the standard HID layout. XInput and
    # other synthetic GUIDs use bus = 0x00 and don't carry VID/PID at the
    # standard offsets — bail out so the caller falls back to name match.
    bus = int(g[0:2], 16) | (int(g[2:4], 16) << 8)
    if bus not in (0x03, 0x05):
        logger.debug(f"SDL GUID {guid_hex!r} has bus 0x{bus:04x} — skipping VID/PID extraction")
        return None

    vid = int(g[8:10], 16) | (int(g[10:12], 16) << 8)
    pid = int(g[16:18], 16) | (int(g[18:20], 16) << 8)
    if vid == 0 and pid == 0:
        return None
    return (vid, pid)


def vid_pid_from_any(text: str) -> Optional[Tuple[int, int]]:
    """Best-effort VID/PID extraction from either a DI product GUID
    (SC profile format) or an SDL joystick GUID. Tries DI first since
    that's the format with an unambiguous signature."""
    return parse_di_product_guid(text) or parse_sdl_joystick_guid(text)
