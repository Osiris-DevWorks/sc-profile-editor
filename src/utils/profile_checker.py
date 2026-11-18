"""Check a Star Citizen profile for problems the game won't tell you about.

Pure logic: reads the profile XML (either an exported ``layout_*.xml`` or the
live ``actionmaps.xml``) and, optionally, the list of joysticks this PC has
connected, and returns a list of findings. No Qt, no hardware access, so it
is fully unit-testable and works the same with ``--mock-joysticks``.

Checks
------
device_order        The profile's js1/js2/... devices vs the order this PC
                    numbers its sticks. A mismatch means bindings land on the
                    wrong stick in game.
device_missing      A profile stick that isn't connected, or a connected
                    stick the profile doesn't know about.
device_unknown      Bindings on a jsN the profile has no device for.
no_such_input       A binding on a button/hat the connected stick doesn't have.
forced_press        ``activationMode="press"`` on a view/look action (or a
                    ``*_hold`` action): the camera can stay stuck.
partial_hat         A hat with some directions bound and the rest free.
mode_switch_clash   One input bound to two or more mode switches.
stale_tuning        Deadzone/saturation/curve tuning stored under a device ID
                    that no stick in the profile has, so the game ignores it.
js1_defaults        js1 was never cleared, so the game's default joystick
                    bindings still apply on it alongside yours.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from utils.directinput_guid import parse_di_product_guid

ERROR = "error"
WARNING = "warning"
INFO = "info"
SEVERITY_ORDER = {ERROR: 0, WARNING: 1, INFO: 2}

HAT_DIRECTIONS = ("up", "down", "left", "right")

_JS_INPUT_RE = re.compile(r"^js(\d+)_(.*)$", re.IGNORECASE)
_BUTTON_RE = re.compile(r"^button(\d+)$", re.IGNORECASE)
_HAT_RE = re.compile(r"^hat(\d+)_(up|down|left|right)$", re.IGNORECASE)
_MODE_SWITCH_RE = re.compile(r"^v_(set|toggle)_[a-z]+_mode$|^v_master_mode_set_[a-z]+$")
_VIEW_ACTION_RE = re.compile(r"(^v_view_|look_behind|freelook|_look_(left|right|up|down)$)")


@dataclass
class Finding:
    check: str
    severity: str
    title: str
    detail: str
    inputs: List[str] = field(default_factory=list)


@dataclass
class DeviceRow:
    """One line of the device-order table: profile slot vs this PC."""
    slot: str                          # "js1"
    profile_name: str                  # "" when the profile has none
    profile_vid_pid: Optional[Tuple[int, int]]
    system_name: str                   # "" when nothing is in that slot
    system_vid_pid: Optional[Tuple[int, int]]
    status: str                        # "ok" | "swapped" | "missing" | "extra" | "unknown"


@dataclass
class CheckReport:
    findings: List[Finding]
    devices: List[DeviceRow]
    profile_name: str = ""
    system_checked: bool = False

    def count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    @property
    def ok(self) -> bool:
        return not self.findings


@dataclass
class _Binding:
    actionmap: str
    action: str
    input: str
    activation_mode: Optional[str]


@dataclass
class _ProfileDevice:
    instance: int
    name: str
    vid_pid: Optional[Tuple[int, int]]


# ---------------------------------------------------------------------------
# Reading the XML
# ---------------------------------------------------------------------------

def _profile_root(root: ET.Element) -> ET.Element:
    """Live actionmaps.xml wraps everything in <ActionProfiles>; exported
    layouts don't. Prefer the profile named "default" when there are several."""
    profiles = root.findall("ActionProfiles")
    if not profiles:
        return root
    for p in profiles:
        if p.get("profileName") == "default":
            return p
    return profiles[0]


def _clean_name(product: str) -> str:
    return " ".join(product.split("{")[0].split())


def _read_devices(root: ET.Element) -> Dict[int, _ProfileDevice]:
    devices: Dict[int, _ProfileDevice] = {}
    for opt in root.findall("options"):
        if (opt.get("type") or "").lower() != "joystick":
            continue
        try:
            instance = int(opt.get("instance", "0"))
        except ValueError:
            continue
        product = opt.get("Product") or ""
        if not product.strip():
            continue
        devices[instance] = _ProfileDevice(instance, _clean_name(product), parse_di_product_guid(product))
    return devices


def _read_bindings(root: ET.Element) -> List[_Binding]:
    out: List[_Binding] = []
    for amap in root.iter("actionmap"):
        map_name = amap.get("name", "")
        for action in amap.findall("action"):
            action_name = action.get("name", "")
            for rebind in action.findall("rebind"):
                value = rebind.get("input")
                if value is None:
                    continue
                out.append(_Binding(map_name, action_name, value.strip(), rebind.get("activationMode")))
    return out


def _js_parts(input_code: str) -> Optional[Tuple[int, str]]:
    m = _JS_INPUT_RE.match(input_code)
    if not m:
        return None
    return int(m.group(1)), m.group(2)


def _is_blank(input_code: str) -> bool:
    parts = _js_parts(input_code)
    return parts is not None and parts[1] == ""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _fmt_vid_pid(vid_pid: Optional[Tuple[int, int]]) -> str:
    return f"{vid_pid[0]:04X}:{vid_pid[1]:04X}" if vid_pid else "unknown ID"


def _check_forced_press(bindings: List[_Binding]) -> List[Finding]:
    view, hold = [], []
    for b in bindings:
        if (b.activation_mode or "").lower() != "press" or _is_blank(b.input):
            continue
        if _VIEW_ACTION_RE.search(b.action):
            view.append(b)
        elif b.action.endswith("_hold"):
            hold.append(b)
    findings = []
    for b in view:
        findings.append(Finding(
            "forced_press", WARNING,
            f"{b.action} on {b.input} is forced to \"press\"",
            "View and look actions are hold actions in the game. Forcing \"press\" overrides that, "
            "so the camera can stay turned after you let go. Set the activation mode back to "
            "(Game default).",
            [b.input]))
    for b in hold:
        findings.append(Finding(
            "forced_press", INFO,
            f"{b.action} on {b.input} is forced to \"press\"",
            "This action is meant to be held. If it behaves oddly, set its activation mode back to "
            "(Game default).",
            [b.input]))
    return findings


def _check_partial_hats(bindings: List[_Binding], devices: Dict[int, _ProfileDevice]) -> List[Finding]:
    bound: Dict[Tuple[int, int], set] = defaultdict(set)
    # Actions cleared to "jsN_ " that still carry an activation mode: a
    # binding that used to be there and was deleted.
    cleared: Dict[int, List[str]] = defaultdict(list)
    for b in bindings:
        parts = _js_parts(b.input)
        if not parts:
            continue
        if not parts[1]:
            if b.activation_mode and _VIEW_ACTION_RE.search(b.action):
                cleared[parts[0]].append(b.action)
            continue
        m = _HAT_RE.match(parts[1])
        if m:
            bound[(parts[0], int(m.group(1)))].add(m.group(2).lower())
    findings = []
    for (js, hat), dirs in sorted(bound.items()):
        free = [d for d in HAT_DIRECTIONS if d not in dirs]
        if not free:
            continue
        dev = devices.get(js)
        where = f"js{js}" + (f" ({dev.name})" if dev else "")
        detail = f"Only {', '.join(d for d in HAT_DIRECTIONS if d in dirs)} is bound on this hat."
        lost = sorted(set(cleared.get(js, [])))
        if lost:
            detail += (f" These view actions were cleared on js{js} but kept their activation mode, "
                       f"which suggests they used to be on this hat: {', '.join(lost)}.")
        else:
            detail += " If the other directions used to do something, they were cleared."
        findings.append(Finding(
            "partial_hat", WARNING if lost else INFO,
            f"Hat {hat} on {where}: {', '.join(free)} unbound",
            detail,
            [f"js{js}_hat{hat}_{d}" for d in free]))
    return findings


def _check_mode_switch_clash(bindings: List[_Binding]) -> List[Finding]:
    by_input: Dict[str, List[_Binding]] = defaultdict(list)
    for b in bindings:
        if b.input and not _is_blank(b.input) and _MODE_SWITCH_RE.match(b.action):
            by_input[b.input.lower()].append(b)
    findings = []
    for code, group in sorted(by_input.items()):
        modes = {}
        for b in group:
            key = (b.activation_mode or "").lower()
            modes.setdefault(key, []).append(b.action)
        for mode, actions in modes.items():
            actions = sorted(set(actions))
            # set_scan_mode + toggle_scan_mode on one button is the same mode.
            if len({_mode_word(a) for a in actions}) < 2:
                continue
            findings.append(Finding(
                "mode_switch_clash", WARNING,
                f"{group[0].input} switches {len(actions)} modes at once",
                f"{', '.join(actions)} are all on {group[0].input}"
                + (f" ({mode})" if mode else "")
                + ". One press fires all of them, so you end up in whichever mode the game applies "
                  "last. Move all but one to a free button.",
                [group[0].input]))
    return findings


def _mode_word(action: str) -> str:
    m = re.match(r"^v_(?:set|toggle)_([a-z]+)_mode$", action)
    return m.group(1) if m else action


def _check_stale_tuning(root: ET.Element, devices: Dict[int, _ProfileDevice]) -> List[Finding]:
    present = {d.vid_pid for d in devices.values() if d.vid_pid}
    findings = []
    for opts in root.findall("deviceoptions"):
        name_attr = opts.get("name") or ""
        vid_pid = parse_di_product_guid(name_attr)
        if vid_pid is None or vid_pid in present:
            continue
        name = _clean_name(name_attr)
        similar = [d for d in devices.values()
                   if d.vid_pid and d.vid_pid[0] == vid_pid[0] and _names_related(d.name, name)]
        if similar:
            target = similar[0]
            findings.append(Finding(
                "stale_tuning", WARNING,
                f"Tuning for \"{name}\" ({_fmt_vid_pid(vid_pid)}) isn't applied",
                f"The deadzone/saturation settings are stored under device ID {_fmt_vid_pid(vid_pid)}, "
                f"but your stick now reports as \"{target.name}\" ({_fmt_vid_pid(target.vid_pid)}, "
                f"js{target.instance}). The game ignores tuning for IDs that aren't present. "
                "Move the settings to the new ID or set them again in game.",
                []))
        else:
            findings.append(Finding(
                "stale_tuning", INFO,
                f"Tuning for \"{name}\" belongs to a device not in this profile",
                "Harmless: the game ignores it. It only matters if you plug that device back in.",
                []))
    return findings


def _names_related(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    return a.startswith(b) or b.startswith(a)


def _check_js1_defaults(bindings: List[_Binding], devices: Dict[int, _ProfileDevice]) -> List[Finding]:
    blanks: Dict[int, int] = defaultdict(int)
    for b in bindings:
        if _is_blank(b.input):
            blanks[_js_parts(b.input)[0]] += 1
    if 1 not in devices or blanks.get(1) or not blanks:
        return []
    cleared = ", ".join(f"js{js} ({n})" for js, n in sorted(blanks.items()))
    return [Finding(
        "js1_defaults", INFO,
        f"js1 ({devices[1].name}) was never cleared",
        f"Cleared entries exist for {cleared} but none for js1. The game's default joystick "
        "bindings sit on js1, so they still apply alongside yours. If a button on this stick "
        "does an extra, unexpected thing, this is why.",
        [])]


def _check_unknown_slots(bindings: List[_Binding], devices: Dict[int, _ProfileDevice]) -> List[Finding]:
    used: Dict[int, int] = defaultdict(int)
    for b in bindings:
        parts = _js_parts(b.input)
        if parts and parts[1]:
            used[parts[0]] += 1
    findings = []
    for js, n in sorted(used.items()):
        if js not in devices:
            findings.append(Finding(
                "device_unknown", WARNING,
                f"{n} binding{'s' if n != 1 else ''} on js{js}, but the profile doesn't say which stick that is",
                "Without a device recorded for this slot, nothing ties these bindings to a particular "
                "stick. They will go to whatever the game numbers js" + str(js) + ".",
                []))
    return findings


def _check_system(bindings: List[_Binding], devices: Dict[int, _ProfileDevice],
                  system: Sequence) -> Tuple[List[Finding], List[DeviceRow]]:
    """Compare profile slots with the connected sticks, in system order."""
    findings: List[Finding] = []
    rows: List[DeviceRow] = []

    sys_by_slot = {i + 1: dev for i, dev in enumerate(system)}
    sys_slots_by_id: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for slot, dev in sys_by_slot.items():
        if dev.vid_pid:
            sys_slots_by_id[dev.vid_pid].append(slot)

    used_slots = {p[0] for p in (_js_parts(b.input) for b in bindings) if p and p[1]}
    max_slot = max([0, len(system), *devices.keys(), *used_slots])

    for slot in range(1, max_slot + 1):
        pdev = devices.get(slot)
        sdev = sys_by_slot.get(slot)
        if pdev is None and sdev is None:
            continue
        if pdev is None and sdev.vid_pid is None and slot not in used_slots:
            continue  # unidentified extra (e.g. a virtual placeholder) with nothing bound
        if pdev is None:
            status = "extra"
        elif sdev is None:
            status = "missing"
        elif pdev.vid_pid is None or sdev.vid_pid is None:
            status = "ok" if _names_related(pdev.name, (sdev.name or "").strip()) else "unknown"
        else:
            status = "ok" if pdev.vid_pid == sdev.vid_pid else "swapped"
        rows.append(DeviceRow(f"js{slot}", pdev.name if pdev else "",
                              pdev.vid_pid if pdev else None,
                              (sdev.name or "").strip() if sdev else "",
                              sdev.vid_pid if sdev else None, status))

    # One finding per profile stick that won't be where the profile expects it.
    for slot, pdev in sorted(devices.items()):
        sdev = sys_by_slot.get(slot)
        if pdev.vid_pid is None:
            continue
        if sdev is not None and sdev.vid_pid == pdev.vid_pid:
            continue
        now = sys_slots_by_id.get(pdev.vid_pid, [])
        n_bind = sum(1 for b in bindings if (_js_parts(b.input) or (0, ""))[0] == slot
                     and (_js_parts(b.input) or (0, ""))[1])
        if now:
            other = (sdev.name or "").strip() if sdev else "nothing"
            findings.append(Finding(
                "device_order", ERROR,
                f"{pdev.name} is js{slot} in the profile but js{now[0]} on this PC",
                f"This PC currently numbers its sticks differently from the profile. In game, "
                f"the {n_bind} js{slot} binding{'s' if n_bind != 1 else ''} meant for {pdev.name} will go to "
                f"{other} instead. Before you play, get the PC to list the sticks in the profile's order "
                f"(usually by re-plugging them, or using the same USB ports as when the profile was made), "
                f"then press Check again.",
                []))
        else:
            findings.append(Finding(
                "device_missing", WARNING,
                f"{pdev.name} (js{slot}) isn't connected",
                f"Its {n_bind} binding{'s' if n_bind != 1 else ''} won't work, and with it missing the game "
                "may number the sticks after it differently.",
                []))

    profile_ids = {d.vid_pid for d in devices.values() if d.vid_pid}
    for slot, sdev in sys_by_slot.items():
        if sdev.vid_pid and sdev.vid_pid not in profile_ids:
            findings.append(Finding(
                "device_missing", INFO,
                f"{(sdev.name or '').strip() or 'A stick'} (js{slot} on this PC) isn't in the profile",
                "The profile has no bindings recorded for this device. If it sits before your other "
                "sticks in the order, it can push them to higher js numbers.",
                []))

    dup = [vp for vp, slots in sys_slots_by_id.items() if len(slots) > 1]
    for vp in dup:
        findings.append(Finding(
            "device_order", INFO,
            f"{len(sys_slots_by_id[vp])} identical sticks connected ({_fmt_vid_pid(vp)})",
            "Identical models report the same ID, so this check can't tell them apart. If their "
            "bindings feel swapped, swap the USB ports.",
            []))

    # Bindings on buttons/hats the connected stick in that slot doesn't have.
    for slot, sdev in sys_by_slot.items():
        pdev = devices.get(slot)
        if pdev and pdev.vid_pid and sdev.vid_pid and pdev.vid_pid != sdev.vid_pid:
            continue  # already reported as a swap
        too_high = []
        for b in bindings:
            parts = _js_parts(b.input)
            if not parts or parts[0] != slot:
                continue
            mb, mh = _BUTTON_RE.match(parts[1]), _HAT_RE.match(parts[1])
            if (mb and int(mb.group(1)) > sdev.buttons) or (mh and int(mh.group(1)) > sdev.hats):
                too_high.append(b)
        if too_high:
            codes = sorted({b.input for b in too_high})
            name = (sdev.name or "").strip()
            findings.append(Finding(
                "no_such_input", WARNING,
                f"{len(too_high)} binding{'s' if len(too_high) != 1 else ''} on js{slot} ({name}) use inputs it doesn't have",
                f"{name} has {sdev.buttons} button{'s' if sdev.buttons != 1 else ''} and "
                f"{sdev.hats} hat{'s' if sdev.hats != 1 else ''}, so these bindings never fire: "
                f"{', '.join(codes[:12])}{' …' if len(codes) > 12 else ''}.",
                codes))
    return findings, rows


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def check_profile(xml_path: str, system_devices: Optional[Sequence] = None) -> CheckReport:
    """Run every check on the profile at ``xml_path``.

    ``system_devices`` is the list of connected joysticks in the order the
    game numbers them (objects with ``name``, ``vid_pid``, ``buttons`` and
    ``hats``, e.g. ``JoystickInfo``). Pass None to skip the checks that need
    the PC's devices.
    """
    tree_root = ET.parse(xml_path).getroot()
    root = _profile_root(tree_root)
    devices = _read_devices(root)
    bindings = _read_bindings(root)

    findings: List[Finding] = []
    rows: List[DeviceRow] = []
    if system_devices is not None:
        sys_findings, rows = _check_system(bindings, devices, system_devices)
        findings += sys_findings
    else:
        rows = [DeviceRow(f"js{i}", d.name, d.vid_pid, "", None, "unknown")
                for i, d in sorted(devices.items())]
    findings += _check_unknown_slots(bindings, devices)
    findings += _check_forced_press(bindings)
    findings += _check_mode_switch_clash(bindings)
    findings += _check_stale_tuning(root, devices)
    findings += _check_partial_hats(bindings, devices)
    findings += _check_js1_defaults(bindings, devices)

    findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 9))
    name = root.get("profileName") or tree_root.get("profileName") or ""
    return CheckReport(findings, rows, name, system_devices is not None)
