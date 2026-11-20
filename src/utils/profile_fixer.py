"""Apply the fixes ``utils.profile_checker`` attaches to its findings.

Works on the profile XML and writes a new file, so the original is never
touched; the app then loads the fixed copy as an unsaved, modified profile
for the user to review and save. Pure ElementTree, no Qt.

Fix kinds (``finding.fix["kind"]``):

clear_activation_mode   drop a forced activationMode from one rebind
restore_hat             bind cleared view actions back onto free hat directions
keep_one                one input fires several actions: keep ``keep``, clear the rest
move_tuning             re-label a <deviceoptions> block with the stick's current ID
unbind                  clear bindings on inputs the stick doesn't have
renumber                jsN -> jsM everywhere so bindings follow their stick
"""
from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, List, Optional

from utils.profile_checker import _profile_root

_JS_PREFIX_RE = re.compile(r"\bjs(\d+)_", re.IGNORECASE)


class FixError(Exception):
    pass


def _blank_for(input_code: str) -> str:
    m = _JS_PREFIX_RE.match(input_code)
    return f"js{m.group(1)}_ " if m else ""


def _action(root: ET.Element, actionmap: str, action: str) -> Optional[ET.Element]:
    for amap in root.iter("actionmap"):
        if amap.get("name") != actionmap:
            continue
        for act in amap.findall("action"):
            if act.get("name") == action:
                return act
    return None


def _rebind(root: ET.Element, actionmap: str, action: str, input_code: str) -> Optional[ET.Element]:
    act = _action(root, actionmap, action)
    if act is None:
        return None
    for rb in act.findall("rebind"):
        if (rb.get("input") or "").strip().lower() == input_code.strip().lower():
            return rb
    return None


def _clear(rb: ET.Element) -> None:
    rb.set("input", _blank_for(rb.get("input") or ""))
    rb.attrib.pop("activationMode", None)


# ---------------------------------------------------------------------------
# Individual fixes. Each returns a one-line description of what changed.
# ---------------------------------------------------------------------------

def _fix_clear_activation_mode(root, fix, choice) -> str:
    rb = _rebind(root, fix["actionmap"], fix["action"], fix["input"])
    if rb is None:
        raise FixError(f"{fix['action']} on {fix['input']} is no longer in the profile")
    rb.attrib.pop("activationMode", None)
    return f"{fix['action']} on {fix['input']}: activation mode set to game default"


def _fix_restore_hat(root, fix, choice) -> str:
    done = []
    for a in fix["assign"]:
        act = _action(root, a["actionmap"], a["action"])
        if act is None:
            continue
        blank = _blank_for(a["input"]).strip()
        target = None
        for rb in act.findall("rebind"):
            if (rb.get("input") or "").strip().lower() == blank.lower():
                target = rb
                break
        if target is None:
            target = ET.SubElement(act, "rebind")
        target.set("input", a["input"])
        target.attrib.pop("activationMode", None)
        done.append(f"{a['action']} → {a['input']}")
    if not done:
        raise FixError("none of those actions are in the profile any more")
    return "Restored " + ", ".join(done)


def _fix_keep_one(root, fix, choice) -> str:
    keep = choice or fix.get("keep")
    if not keep:
        raise FixError("no action chosen to keep the input")
    cleared = []
    for b in fix["bindings"]:
        if b["action"] == keep:
            continue
        rb = _rebind(root, b["actionmap"], b["action"], fix["input"])
        if rb is not None:
            _clear(rb)
            cleared.append(b["action"])
    return f"{fix['input']} now only does {keep} (cleared {', '.join(cleared) or 'nothing'})"


def _fix_move_tuning(root, fix, choice) -> str:
    src = next((d for d in root.findall("deviceoptions") if d.get("name") == fix["from_name"]), None)
    if src is None:
        raise FixError("that tuning block is no longer in the profile")
    dst = next((d for d in root.findall("deviceoptions") if d.get("name") == fix["to_name"]), None)
    if dst is None:
        src.set("name", fix["to_name"])
    else:
        # The stick already has some tuning: keep it, add the old settings
        # it doesn't have yet.
        have = {(o.get("input"), tuple(sorted(k for k in o.attrib if k != "input"))) for o in dst}
        for opt in list(src):
            key = (opt.get("input"), tuple(sorted(k for k in opt.attrib if k != "input")))
            if key not in have:
                dst.append(copy.deepcopy(opt))
        root.remove(src)
    return f"Tuning moved to {' '.join(fix['to_name'].split('{')[0].split())}"


def _fix_unbind(root, fix, choice) -> str:
    n = 0
    for b in fix["bindings"]:
        rb = _rebind(root, b["actionmap"], b["action"], b["input"])
        if rb is not None:
            _clear(rb)
            n += 1
    return f"Removed {n} binding{'s' if n != 1 else ''} on inputs the stick doesn't have"


def _fix_renumber(root, fix, choice) -> str:
    mapping: Dict[int, int] = {int(k): int(v) for k, v in fix["mapping"].items()}
    if not mapping:
        return "Nothing to renumber"

    def sub(value: str) -> str:
        return _JS_PREFIX_RE.sub(lambda m: f"js{mapping.get(int(m.group(1)), int(m.group(1)))}_", value)

    for elem in root.iter():
        for key, value in list(elem.attrib.items()):
            if "js" in value.lower() and _JS_PREFIX_RE.search(value):
                elem.set(key, sub(value))

    # <options type="joystick" instance="N" Product="..."> and the header list.
    joystick_opts = [o for o in root.findall("options") if (o.get("type") or "").lower() == "joystick"]
    for opt in joystick_opts:
        try:
            n = int(opt.get("instance", "0"))
        except ValueError:
            continue
        if n in mapping:
            opt.set("instance", str(mapping[n]))
    # A bare placeholder <options instance="M"/> may now share M with a moved
    # stick; drop the placeholder.
    seen: Dict[str, ET.Element] = {}
    for opt in joystick_opts:
        inst = opt.get("instance")
        if inst in seen:
            bare = opt if not opt.get("Product") else seen[inst]
            root.remove(bare)
            if bare is seen[inst]:
                seen[inst] = opt
        else:
            seen[inst] = opt
    # Keep options in instance order so the file reads naturally.
    _sort_joystick_options(root)

    for devices in root.iter("devices"):
        for js in devices.findall("joystick"):
            try:
                n = int(js.get("instance", "0"))
            except ValueError:
                continue
            if n in mapping:
                js.set("instance", str(mapping[n]))
        insts = set()
        for js in list(devices.findall("joystick")):
            if js.get("instance") in insts:
                devices.remove(js)
            insts.add(js.get("instance"))

    pretty = ", ".join(f"js{o}→js{n}" for o, n in sorted(mapping.items()))
    return f"Renumbered sticks: {pretty}"


def _sort_joystick_options(root: ET.Element) -> None:
    children = list(root)
    idx = [i for i, c in enumerate(children)
           if c.tag == "options" and (c.get("type") or "").lower() == "joystick"]
    if not idx:
        return
    ordered = sorted((children[i] for i in idx), key=lambda o: int(o.get("instance", "0") or 0))
    for i, elem in zip(idx, ordered):
        children[i] = elem
    for c in list(root):
        root.remove(c)
    root.extend(children)


_FIXERS = {
    "clear_activation_mode": _fix_clear_activation_mode,
    "restore_hat": _fix_restore_hat,
    "keep_one": _fix_keep_one,
    "move_tuning": _fix_move_tuning,
    "unbind": _fix_unbind,
    "renumber": _fix_renumber,
}


def apply_fixes(xml_path: str, fixes: Iterable[dict], output_path: str,
                choices: Optional[Dict[int, str]] = None) -> List[str]:
    """Apply ``fixes`` to the profile at ``xml_path`` and write ``output_path``.

    ``choices`` maps a fix's position in ``fixes`` to the user's pick for
    fixes that need one (``keep_one``). The same renumber fix attached to
    several findings is applied once. Returns one line per change made;
    raises FixError if a fix can't be applied (nothing is written then).
    """
    tree = ET.parse(xml_path)
    root = _profile_root(tree.getroot())
    choices = choices or {}
    done: List[str] = []
    applied_renumber = False
    fixes = list(fixes)
    # Renumber last: the other fixes name inputs by the profile's old jsN.
    order = sorted(range(len(fixes)), key=lambda i: fixes[i].get("kind") == "renumber")
    for i in order:
        fix = fixes[i]
        kind = fix.get("kind")
        if kind == "renumber":
            if applied_renumber:
                continue
            applied_renumber = True
        fixer = _FIXERS.get(kind)
        if fixer is None:
            raise FixError(f"unknown fix {kind!r}")
        done.append(fixer(root, fix, choices.get(i)))
    tree.write(output_path, encoding="utf-8")
    return done
