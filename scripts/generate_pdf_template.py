"""Generate a visual-template PDF from a device image with pre-drawn label rectangles.

Two-phase workflow:

  1. detect:   image + (optional) hints  ->  manifest.json (rectangles + placeholder names)
                 user edits manifest.json to fill in real field names
  2. generate: manifest.json + image     ->  device.pdf + field_mapping.json

The detector uses OpenCV's contour-finding to locate axis-aligned rectangles in
the source image. The generator uses PyMuPDF to embed the image into a PDF
sized to the image dimensions and place a text-field widget at each rectangle.

Usage
-----

    python scripts/generate_pdf_template.py detect path/to/device.png \\
        [--output manifest.json] [--min-area 200] [--max-aspect 30]

    # ...edit manifest.json to fill in field names...

    python scripts/generate_pdf_template.py generate manifest.json \\
        [--image path/to/device.png] [--output-dir visual-templates/my_device]

Manifest format
---------------

    {
      "image": "path/to/device.png",
      "page_size": [width_pt, height_pt],
      "rectangles": [
        {"name": "TODO_1", "x": 60, "y": 90.9, "w": 22, "h": 16},
        ...
      ]
    }

Coordinates are in PDF points (= image pixels at 72 DPI), origin at top-left.
Field names default to TODO_<scan_order>; edit them before running `generate`.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("generate_pdf_template")


# ----------------------------------------------------------------------------
# Detector
# ----------------------------------------------------------------------------


@dataclass
class DetectedRect:
    """One detected label rectangle, in image-pixel coordinates (origin top-left)."""
    name: str
    x: float
    y: float
    w: float
    h: float


def detect_rectangles(
    image_path: str,
    min_area: int = 200,
    max_aspect: float = 30.0,
    canny_low: int = 30,
    canny_high: int = 100,
    epsilon_ratio: float = 0.02,
    drop_outer_groups: bool = True,
) -> List[DetectedRect]:
    """Find axis-aligned rectangle outlines in an image.

    Pipeline: grayscale -> Canny edges -> findContours (with hierarchy) ->
    approxPolyDP -> filter to 4-vertex contours with reasonable aspect ratio +
    minimum area -> dedupe nested/overlapping rectangles, preferring the
    innermost (the actual label cell, not its containing group frame).

    Returns rectangles in scan order with placeholder names TODO_1...TODO_N.

    Args:
        image_path: PNG/JPG file with label rectangles drawn on it.
        min_area: Reject rectangles smaller than this (in px^2). Filters noise.
        max_aspect: Reject rectangles whose long/short ratio exceeds this.
        canny_low, canny_high: Canny hysteresis thresholds. Defaults tuned for
            screenshots / authoring-tool exports where strokes are thin and
            the higher 50/150 default missed light-color cell borders.
        epsilon_ratio: Polygon-approximation tolerance as a fraction of the
            contour's perimeter. 0.02 = tight, only accepts well-formed rects.
        drop_outer_groups: When a detected rectangle fully contains other
            detected rectangles, drop the outer one (it's the group frame,
            not an actual label cell). Set False if you want both.
    """
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "Rectangle detection requires opencv-python and numpy.\n"
            "Install with: pip install opencv-python\n"
            f"(original error: {e})"
        )

    img = cv2.imread(image_path)
    if img is None:
        raise SystemExit(f"Could not read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, canny_low, canny_high)
    # Note: no dilation. Dilation closes thin gaps but also bridges the thin
    # separator lines between adjacent cells in a group, which causes the
    # detector to see the whole group as one rectangle instead of N cells.

    # RETR_LIST returns all contours (including nested), which is what we
    # want — we'll prune outer group frames in post-processing rather than
    # missing inner cells entirely.
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    rects: List[DetectedRect] = []
    for c in contours:
        peri = cv2.arcLength(c, True)
        if peri < 30:
            continue
        approx = cv2.approxPolyDP(c, epsilon_ratio * peri, True)
        if len(approx) != 4:
            continue
        x, y, w, h = cv2.boundingRect(approx)
        if w * h < min_area:
            continue
        long_side = max(w, h)
        short_side = max(1, min(w, h))
        if long_side / short_side > max_aspect:
            continue
        rects.append(DetectedRect(name="", x=float(x), y=float(y), w=float(w), h=float(h)))

    rects = _deduplicate(rects)
    if drop_outer_groups:
        rects = _drop_outer_groups(rects)
    rects = _sort_scan_order(rects)
    for i, r in enumerate(rects, start=1):
        r.name = f"TODO_{i}"
    return rects


def _deduplicate(rects: List[DetectedRect]) -> List[DetectedRect]:
    """Drop near-duplicate rectangles (inner + outer edge of the same stroke).

    Two flavors of duplicate get caught here:

    1. Same-size: centers within 5px AND dimensions within 10% — direct
       restate of one detection in another scan pass.
    2. Concentric nested: one rectangle fully contains another with similar
       center and a size delta of <30%. This is the inner+outer edge of a
       drawn stroke where the contour finder picked up both sides; we keep
       the inner one (the actual cell interior)."""
    kept: List[DetectedRect] = []
    for r in rects:
        cx, cy = r.x + r.w / 2, r.y + r.h / 2
        is_dup = False
        for k in kept:
            kcx, kcy = k.x + k.w / 2, k.y + k.h / 2
            # Variant 1: near-identical
            if (abs(cx - kcx) < 5 and abs(cy - kcy) < 5
                    and abs(r.w - k.w) / max(k.w, 1) < 0.1
                    and abs(r.h - k.h) / max(k.h, 1) < 0.1):
                is_dup = True
                break
            # Variant 2: concentric nested with up to 30% size mismatch.
            # If the new rect is the OUTER one (larger), drop it — keep the
            # smaller one already in `kept`. If it's the inner one (smaller),
            # replace `kept` entry with this one.
            center_close = abs(cx - kcx) < max(r.w, k.w) * 0.2 and abs(cy - kcy) < max(r.h, k.h) * 0.2
            size_close = (abs(r.w - k.w) / max(k.w, 1) < 0.3
                          and abs(r.h - k.h) / max(k.h, 1) < 0.3)
            if center_close and size_close:
                # Prefer the smaller one (inner stroke edge)
                if r.w * r.h < k.w * k.h:
                    kept.remove(k)
                    kept.append(r)
                is_dup = True
                break
        if not is_dup:
            kept.append(r)
    return kept


def detect_rectangles_by_color(
    image_path: str,
    fill_hsv: Tuple[int, int, int],
    hue_tolerance: int = 15,
    sat_tolerance: int = 40,
    val_tolerance: int = 60,
    min_area: int = 100,
    min_dim: int = 15,
    max_aspect: float = 30.0,
    erode_iters: int = 0,
) -> List[DetectedRect]:
    """Detect rectangles by masking pixels of a specific fill color.

    Far more precise than edge-based detection when the form-field cells are
    drawn with a known fill color (e.g. the X56 layout's pale-blue cells).
    Background, photos, headers, and identifier cells are filtered out by
    color rather than by shape, so the result is just the actual form-field
    locations.

    Pipeline:
        1. Convert to HSV; mask pixels within tolerance of `fill_hsv`.
        2. Morphological close to bridge anti-aliased borders.
        3. findContours (RETR_EXTERNAL — color regions don't nest).
        4. Bounding-rect of each contour, filter by area and aspect.

    Args:
        fill_hsv: (H, S, V) of the fill color. H in 0-179 (OpenCV),
            S in 0-255, V in 0-255. For pale cyan: ~(115, 33, 255).
        hue_tolerance: Half-width of the hue range. Pale colors compress in
            the hue space, so a wider tolerance is OK.
        sat_tolerance, val_tolerance: Same for saturation/value.
    """
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "Color-based rectangle detection requires opencv-python and numpy.\n"
            "Install with: pip install opencv-python\n"
            f"(original error: {e})"
        )

    img = cv2.imread(image_path)
    if img is None:
        raise SystemExit(f"Could not read image: {image_path}")

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = fill_hsv
    lower = np.array([
        max(0, h - hue_tolerance),
        max(0, s - sat_tolerance),
        max(0, v - val_tolerance),
    ])
    upper = np.array([
        min(179, h + hue_tolerance),
        min(255, s + sat_tolerance),
        min(255, v + val_tolerance),
    ])
    mask = cv2.inRange(hsv, lower, upper)
    # Optional light erosion to break 1-px anti-aliasing bridges between
    # adjacent cells. Helps when cells share a fully-colored row (JPEG
    # smoothing on vertical stacks of blue cells) but hurts when the mask
    # is already thin (gray cells with a narrow value window can disappear).
    # Erosion shrinks bounds slightly — we compensate when computing the
    # bounding rect by widening it by the same amount.
    if erode_iters > 0:
        mask = cv2.erode(mask, np.ones((2, 2), np.uint8), iterations=erode_iters)

    # Use connected components rather than findContours — direct stats avoid
    # any contour-walking that could miss interior holes or merge through
    # diagonal adjacency.
    n_blobs, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)

    rects: List[DetectedRect] = []
    for i in range(1, n_blobs):  # 0 = background
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area:
            continue
        # Reject blobs with either dimension below min_dim — noise blobs
        # (residual mask fragments around device photos, leader-line
        # crossings, anti-aliasing artifacts) tend to have one tiny side
        # even when their area passes min_area.
        if min(w, bh) < min_dim:
            continue
        long_side = max(w, bh)
        short_side = max(1, min(w, bh))
        if long_side / short_side > max_aspect:
            continue
        # Compensate for erosion so rect aligns with original cell border.
        pad = erode_iters
        rects.append(DetectedRect(
            name="",
            x=float(max(0, x - pad)),
            y=float(max(0, y - pad)),
            w=float(w + 2 * pad),
            h=float(bh + 2 * pad),
        ))

    rects = _split_tall_blobs(rects)
    rects = _sort_scan_order(rects)
    for i, r in enumerate(rects, start=1):
        r.name = f"TODO_{i}"
    return rects


def _split_tall_blobs(rects: List[DetectedRect], split_threshold: float = 1.5) -> List[DetectedRect]:
    """Split blobs whose height is clearly N cells worth instead of 1.

    When a separator line between two vertically-stacked cells is too weak
    to register in the color mask (anti-aliasing or low contrast), the two
    cells fuse into one blob of double height. Detect that by comparing
    each rectangle's height to the median row height for its column: any
    blob with h >= split_threshold * median_h is treated as N=round(h / median)
    stacked cells and split evenly.

    Bucketed by column (x within tolerance) so a tall single cell that's
    deliberately larger than its column-mates doesn't get falsely split
    based on heights from unrelated parts of the image.
    """
    if not rects:
        return rects
    # Bucket by approximate column (x within tolerance)
    sorted_by_x = sorted(rects, key=lambda r: r.x)
    columns: List[List[DetectedRect]] = []
    col_tol = 20.0
    for r in sorted_by_x:
        if columns and abs(r.x - columns[-1][0].x) <= col_tol:
            columns[-1].append(r)
        else:
            columns.append([r])

    out: List[DetectedRect] = []
    for col in columns:
        if len(col) < 2:
            out.extend(col)
            continue
        heights = sorted(r.h for r in col)
        median_h = heights[len(heights) // 2]
        for r in col:
            if r.h >= median_h * split_threshold:
                n = max(2, round(r.h / median_h))
                slice_h = r.h / n
                for i in range(n):
                    out.append(DetectedRect(
                        name="",
                        x=r.x,
                        y=r.y + i * slice_h,
                        w=r.w,
                        h=slice_h,
                    ))
            else:
                out.append(r)
    return out


# Named fill colors: (H, S, V, hue_tol, sat_tol, val_tol, erode_iters).
# Tolerances are per-color because grays cluster very close to whites in HSV
# space (only V differs) and need a tight value window. Erosion is per-color
# because tightly-masked colors (gray) shrink to nothing if eroded, while
# wider masks (blue) benefit from erosion separating vertically-stacked
# adjacent cells that JPEG smoothing has bridged.
def detect_white_bordered_cells(
    image_path: str,
    excluded_rects: Optional[List[DetectedRect]] = None,
    min_area: int = 200,
    min_dim: int = 15,
    max_aspect: float = 30.0,
    interior_v_min: int = 240,
) -> List[DetectedRect]:
    """Detect rectangles with white interior bounded by a visible border.

    Edge-based detection (Canny + findContours + 4-vertex polygon approx)
    finds all bordered rectangles. We then keep only those whose interior
    sample pixels are nearly white (V >= interior_v_min in HSV), filtering
    out gray-filled cells, dark device-photo regions, and the white page
    background (which has no enclosing border).

    `excluded_rects` is the gray-cell set; rectangles that overlap heavily
    with any of those are dropped to avoid double-counting cells that the
    color detector already found.
    """
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as e:
        raise SystemExit(f"Detection requires opencv-python and numpy: {e}")

    img = cv2.imread(image_path)
    if img is None:
        raise SystemExit(f"Could not read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    excluded = excluded_rects or []

    rects: List[DetectedRect] = []
    for c in contours:
        peri = cv2.arcLength(c, True)
        if peri < 30:
            continue
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        x, y, w, h = cv2.boundingRect(approx)
        if w * h < min_area or min(w, h) < min_dim:
            continue
        long_side = max(w, h)
        short_side = max(1, min(w, h))
        if long_side / short_side > max_aspect:
            continue

        # Sample a 5x5 window in the rectangle's interior. Using mean V from
        # multiple points dodges the case where a single sample lands on a
        # text glyph that's darker than the cell fill.
        cx, cy = x + w // 2, y + h // 2
        s = 2
        patch = hsv[max(0, cy - s):cy + s + 1, max(0, cx - s):cx + s + 1]
        if patch.size == 0:
            continue
        mean_v = float(patch[..., 2].mean())
        mean_s = float(patch[..., 1].mean())
        if mean_v < interior_v_min or mean_s > 30:
            # Not near-white interior — likely gray cell, photo, or chrome
            continue

        candidate = DetectedRect(name="", x=float(x), y=float(y), w=float(w), h=float(h))
        if _overlaps_any(candidate, excluded):
            continue
        rects.append(candidate)

    rects = _deduplicate(rects)
    rects = _drop_outer_groups(rects)
    return rects


def _overlaps_any(rect: DetectedRect, others: List[DetectedRect],
                  threshold: float = 0.3) -> bool:
    """True if `rect` overlaps any rectangle in `others` by >= threshold of
    EITHER's area. Used to drop cells the gray-color detector already claimed.

    Bidirectional area check matters because anti-aliased borders inside a
    gray cell often produce small inner contours — those overlap the gray
    fully (rect inside gray = overlap == rect_area), but their threshold
    relative to the larger gray rect alone wouldn't trip a one-sided check."""
    rx0, ry0, rx1, ry1 = rect.x, rect.y, rect.x + rect.w, rect.y + rect.h
    rect_area = max(1, rect.w * rect.h)
    for o in others:
        ox0, oy0, ox1, oy1 = o.x, o.y, o.x + o.w, o.y + o.h
        ix0, iy0 = max(rx0, ox0), max(ry0, oy0)
        ix1, iy1 = min(rx1, ox1), min(ry1, oy1)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        overlap = (ix1 - ix0) * (iy1 - iy0)
        other_area = max(1, o.w * o.h)
        if overlap / rect_area >= threshold or overlap / other_area >= threshold:
            return True
    return False


def ocr_label_strips(
    image_path: str,
    rectangles: List[DetectedRect],
    strip_width_max: float = 1.5,
    expand_height: float = 0.0,
) -> dict:
    """OCR the white identifier cell to the left of each detected blue cell.

    The X56-style layout puts a white-background cell with text like `JOY_25`,
    `POV1_UP`, or `JOY_RZ+` immediately to the left of each blue label cell.
    This function locates that white cell by stepping left from each blue
    rectangle and uses Tesseract to read the text.

    Returns a dict mapping rectangle name -> raw OCR text (str), with empty
    strings for cells where no readable text was found. The caller is
    responsible for parsing the OCR text into SC input codes.

    Args:
        strip_width_max: Maximum width of the identifier cell as a multiple
            of the blue cell's width. The white cells in the X56 are smaller
            than the blue ones, so 1.5x is plenty of headroom.
        expand_height: Vertical padding around each strip (fraction of cell
            height). Zero is usually fine; bump if OCR misses tops/bottoms.
    """
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as e:
        raise SystemExit(f"OCR requires opencv-python and numpy: {e}")

    try:
        import pytesseract  # type: ignore
    except ImportError:
        raise SystemExit(
            "OCR requires pytesseract. Install with: pip install pytesseract\n"
            "You also need the Tesseract binary on PATH or at "
            "C:\\Program Files\\Tesseract-OCR\\tesseract.exe.\n"
            "Windows installer: https://github.com/UB-Mannheim/tesseract/wiki"
        )

    # Probe known Windows install locations when the binary isn't on PATH.
    # Fresh winget/UB-Mannheim installs land in Program Files but the running
    # shell often inherits the pre-install PATH, so we'd otherwise error
    # despite the install being valid.
    _ensure_tesseract_on_path(pytesseract)

    try:
        pytesseract.get_tesseract_version()
    except (pytesseract.TesseractNotFoundError, FileNotFoundError):
        raise SystemExit(
            "Tesseract binary not found. pytesseract needs the Tesseract OCR "
            "engine itself, not just the Python wrapper.\n"
            "Windows: install from https://github.com/UB-Mannheim/tesseract/wiki "
            "(default location works), or set the path explicitly:\n"
            "  pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'"
        )

    img = cv2.imread(image_path)
    if img is None:
        raise SystemExit(f"Could not read image: {image_path}")
    img_h, img_w = img.shape[:2]

    results: dict = {}
    for rect in rectangles:
        # Search left of the blue cell for the white identifier cell. The
        # X56 layout always puts the identifier immediately adjacent.
        strip_w = int(rect.w * strip_width_max)
        strip_x0 = max(0, int(rect.x) - strip_w)
        strip_x1 = max(0, int(rect.x))
        strip_y0 = max(0, int(rect.y - rect.h * expand_height))
        strip_y1 = min(img_h, int(rect.y + rect.h * (1 + expand_height)))
        if strip_x1 - strip_x0 < 5 or strip_y1 - strip_y0 < 5:
            results[rect.name] = ""
            continue

        crop = img[strip_y0:strip_y1, strip_x0:strip_x1]
        # The X56 identifier strips have TWO lines:
        #   line 1 (big, bold):   position label — UP / DOWN / FWD / AFT / RIGHT / LEFT / PUSH
        #   line 2 (small, italic): SC binding   — JOY_7 / POV1_UP / JOY_RZ+ / JOY_SLIDER1
        # We OCR the whole strip with PSM 6 (block of text), then return all
        # extracted tokens joined by newline so the caller can pick the JOY_X
        # / POV1_X line. Cropping to just the bottom half before OCR loses
        # context Tesseract uses for line segmentation, so we leave the full
        # strip and filter afterward.
        crop = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        config = (
            "--psm 6 "
            "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_+-/"
        )
        text = pytesseract.image_to_string(binary, config=config).strip()
        results[rect.name] = text

    return results


_JOY_TOKEN_RE = re.compile(
    # Match any JOY_X / POV1_X / POVI_X token embedded in OCR-noisy text.
    # Tesseract often prepends/appends garbage characters (`_`, `m`, `i`)
    # around the real label; this finds the token regardless.
    #
    # POV1 / POVI: Tesseract often misreads the digit '1' as letter 'I' in
    # italic text, so accept both.
    r"(?:JOY_(?:[A-Z]+\d*|\d+)[+-]?"
    r"|POV[1I]?_(?:UP|DOWN|LEFT|RIGHT|U|D|L|R))",
    re.IGNORECASE,
)


def _pick_joy_line(ocr_text: str) -> str:
    """Extract a JOY_X / POV1_X token from possibly-noisy OCR output.

    The X56 identifier strips OCR as two lines: a position label (UP, DOWN,
    FWD, AFT, RIGHT, LEFT, PUSH) and a binding identifier (JOY_7, POV1_UP,
    JOY_RZ+). Tesseract frequently inserts stray characters around the
    binding token (`_ JOY_10`, `wJOY_8`, `mumsPOVI_D`), so we regex-search
    for the token rather than expecting a clean line start.

    Normalizes POVI -> POV1 since italic 1 frequently OCRs as I."""
    if not ocr_text:
        return ""
    match = _JOY_TOKEN_RE.search(ocr_text)
    if not match:
        return ""
    token = match.group(0).upper()
    # POVI_X -> POV1_X (italic-1-as-I correction)
    token = re.sub(r"^POVI", "POV1", token)
    return token


def _ensure_tesseract_on_path(pytesseract_module) -> None:
    """If the Tesseract binary isn't on the inherited PATH, fall back to the
    standard Windows install locations. Sets ``pytesseract.tesseract_cmd``
    when a binary is found at a known path."""
    import shutil
    if shutil.which("tesseract"):
        return  # Already on PATH, pytesseract will find it
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\UB-Mannheim.TesseractOCR_Microsoft.Winget.Source_8wekyb3d8bbwe\tesseract.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            pytesseract_module.pytesseract.tesseract_cmd = path
            return


def parse_joy_label(text: str) -> Optional[Tuple[str, "Any"]]:
    """Parse a Logitech-style joystick label into (kind, value).

    Recognized formats:

        JOY_25         -> ("button", 25)
        JOY_5          -> ("button", 5)
        JOY_X+ / JOY_X- / JOY_X    -> ("axis", "x")
        JOY_RZ+ / JOY_RZ-          -> ("axis", "rotz")
        JOY_SLIDER1                -> ("axis", "slider1")
        JOY_33+ / JOY_33-          -> ("axis", "slider2") [non-standard; best-effort]
        POV1_UP / POV1_U           -> ("hat",  "hat1_up")
        POV1_LEFT / POV1_L         -> ("hat",  "hat1_left")
        POV1_RIGHT / POV1_R        -> ("hat",  "hat1_right")
        POV1_DOWN / POV1_D         -> ("hat",  "hat1_down")

    Returns None when the label doesn't match any recognized pattern, leaving
    the caller to surface it as TODO_NEEDS_REVIEW for human inspection.
    """
    if not text:
        return None
    s = text.strip().upper()
    s = s.replace(" ", "")  # OCR sometimes inserts a space

    # POV1_<DIR>
    pov_match = re.match(r"^POV1?_([UDLR]|UP|DOWN|LEFT|RIGHT)$", s)
    if pov_match:
        d = pov_match.group(1)
        d_map = {"U": "up", "D": "down", "L": "left", "R": "right",
                 "UP": "up", "DOWN": "down", "LEFT": "left", "RIGHT": "right"}
        return ("hat", f"hat1_{d_map[d]}")

    # JOY_<axis>+/- or JOY_<axis>
    axis_match = re.match(r"^JOY_(X|Y|Z|RX|RY|RZ)[+-]?$", s)
    if axis_match:
        ax = axis_match.group(1).lower()
        if ax in {"x", "y", "z"}:
            return ("axis", ax)
        # RX/RY/RZ -> rotx/roty/rotz
        return ("axis", "rot" + ax[1])

    # JOY_SLIDER<N>
    slider_match = re.match(r"^JOY_SLIDER(\d+)$", s)
    if slider_match:
        return ("axis", f"slider{slider_match.group(1)}")

    # JOY_33+/- (non-standard sliders) — direction sign is REQUIRED here so
    # this doesn't shadow plain JOY_NN button matches below.
    slider33_match = re.match(r"^JOY_(\d{2,})[+-]$", s)
    if slider33_match:
        # Two-digit JOY_NN labels with +/- direction are sliders, not buttons
        # — Logitech firmware exposes some axes with these high indices.
        # Map to slider2 as a best-effort default; user can override.
        return ("axis", "slider2")

    # Plain JOY_<digit>... is a button
    btn_match = re.match(r"^JOY_(\d+)$", s)
    if btn_match:
        return ("button", int(btn_match.group(1)))

    return None


_NAMED_FILL_COLORS_HSV = {
    # Pale cyan, X56 style — well-separated from white by hue and sat.
    # Tolerances widened from the original (15/40/60) to (20/60/80) after
    # round-tripping the X56 image — narrower windows missed cells that
    # JPEG compression had pushed to a slightly different blue. No erosion:
    # empirically cells are already well-separated by their white borders,
    # and erosion eats narrow cells without recovering any merged ones.
    "blue": (115, 33, 255, 20, 60, 80, 0),
    # Light gray, X52 style — V=220 vs white V=254, narrow window; no
    # erosion or cells disappear.
    "gray": (0, 0, 220, 180, 30, 18, 0),
    "grey": (0, 0, 220, 180, 30, 18, 0),
}


def _drop_outer_groups(rects: List[DetectedRect]) -> List[DetectedRect]:
    """Drop rectangles that fully contain >=2 other detected rectangles.

    Group frames (e.g. the box around HAT 1 / UP / RIGHT / LEFT / DOWN cells)
    are usually drawn as their own rectangle in the image. They satisfy the
    same shape filters as the inner cells, so they get detected too. We
    don't want them in the output: the user wants form fields on the
    actual label cells, not a redundant field over the whole group.

    Heuristic: if a rectangle contains 2+ other detected rectangles
    (>80% of those rects' areas inside it), it's a group frame, drop it.
    A rectangle that contains exactly 1 other rectangle is more likely a
    near-duplicate of that inner one (handled by _deduplicate)."""
    def _contains(outer: DetectedRect, inner: DetectedRect) -> bool:
        if outer is inner:
            return False
        ox0, oy0, ox1, oy1 = outer.x, outer.y, outer.x + outer.w, outer.y + outer.h
        ix0, iy0, ix1, iy1 = inner.x, inner.y, inner.x + inner.w, inner.y + inner.h
        # Inner-area-overlap test: how much of the inner rect lies within outer
        sx0 = max(ox0, ix0)
        sy0 = max(oy0, iy0)
        sx1 = min(ox1, ix1)
        sy1 = min(oy1, iy1)
        if sx1 <= sx0 or sy1 <= sy0:
            return False
        overlap = (sx1 - sx0) * (sy1 - sy0)
        inner_area = inner.w * inner.h
        return overlap / max(inner_area, 1) > 0.8 and (outer.w * outer.h) > inner_area * 1.2

    kept: List[DetectedRect] = []
    for r in rects:
        contained_count = sum(1 for other in rects if _contains(r, other))
        if contained_count >= 2:
            continue  # Group frame
        kept.append(r)
    return kept


def _sort_scan_order(rects: List[DetectedRect]) -> List[DetectedRect]:
    """Sort top-to-bottom, then left-to-right.

    Group rectangles into rows by y-coordinate (within a tolerance of half the
    median height) so that visually-aligned rectangles end up in the same row
    even if their tops differ by a pixel or two. Within each row, sort by x."""
    if not rects:
        return rects
    median_h = sorted(r.h for r in rects)[len(rects) // 2]
    row_tol = max(median_h * 0.5, 5.0)
    by_y = sorted(rects, key=lambda r: r.y)
    rows: List[List[DetectedRect]] = []
    for r in by_y:
        if rows and abs(r.y - rows[-1][0].y) <= row_tol:
            rows[-1].append(r)
        else:
            rows.append([r])
    out: List[DetectedRect] = []
    for row in rows:
        out.extend(sorted(row, key=lambda r: r.x))
    return out


# ----------------------------------------------------------------------------
# Manifest
# ----------------------------------------------------------------------------


def write_manifest(
    image_path: str,
    rectangles: List[DetectedRect],
    page_size: Tuple[float, float],
    output_path: str,
) -> None:
    """Serialize manifest as readable JSON. The manifest is meant to be hand-edited."""
    payload = {
        "image": os.path.relpath(image_path, os.path.dirname(output_path) or "."),
        "page_size": list(page_size),
        "rectangles": [asdict(r) for r in rectangles],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    logger.info(f"Wrote {len(rectangles)} rectangles to {output_path}")


def render_key_image(
    image_path: str,
    rectangles: List[DetectedRect],
    output_path: str,
) -> None:
    """Render a "key" PNG showing each detected rectangle with its field name.

    Reads the source image, draws each rectangle in red, and overlays the
    field name (or just the trailing number from `TODO_N`) inside the cell.
    Lets the user visually map each rectangle to its name in the manifest
    so they can do meaningful renames (e.g., TODO_42 -> HAT2_UP_2) without
    eyeballing coordinates.

    Font scales with cell height so small cells get readable small labels
    and big cells get bigger ones. Text is drawn with a white halo outline
    so it stays readable on any background color.
    """
    try:
        import cv2  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "Key-image rendering requires opencv-python.\n"
            "Install with: pip install opencv-python\n"
            f"(original error: {e})"
        )

    img = cv2.imread(image_path)
    if img is None:
        raise SystemExit(f"Could not read image: {image_path}")

    for r in rectangles:
        x, y, w, h = int(r.x), int(r.y), int(r.w), int(r.h)
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # Show just the trailing token of TODO_N or the full name otherwise.
        # Keeps labels short enough to fit inside the cell.
        label = r.name.rsplit("_", 1)[-1] if r.name.startswith("TODO_") else r.name
        font = cv2.FONT_HERSHEY_SIMPLEX
        # Scale font to fit cell — heuristic: ~50% of cell height, capped.
        font_scale = max(0.35, min(0.9, h / 40.0))
        thickness = 1 if font_scale < 0.5 else 2
        (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)
        # Center horizontally; vertically position from the cell top-left
        # rather than center, so when scan-order numbers cluster the eye
        # finds them in the same relative position per cell.
        tx = x + max(2, (w - tw) // 2)
        ty = y + th + 2 if th + 4 < h else y - 2  # spill above if cell is too short

        # White halo for contrast, then red foreground.
        cv2.putText(img, label, (tx, ty), font, font_scale, (255, 255, 255), thickness + 2)
        cv2.putText(img, label, (tx, ty), font, font_scale, (0, 0, 255), thickness)

    cv2.imwrite(output_path, img)
    logger.info(f"Wrote key image -> {output_path}")


def read_manifest(manifest_path: str) -> Tuple[str, Tuple[float, float], List[DetectedRect]]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    rects = [DetectedRect(**r) for r in payload["rectangles"]]
    page = tuple(payload["page_size"])
    image = payload["image"]
    if not os.path.isabs(image):
        image = os.path.join(os.path.dirname(manifest_path), image)
    return image, page, rects


# ----------------------------------------------------------------------------
# PDF generator
# ----------------------------------------------------------------------------


def generate_pdf(
    image_path: str,
    page_size: Tuple[float, float],
    rectangles: List[DetectedRect],
    output_pdf: str,
    include_todos: bool = False,
) -> None:
    """Build the template PDF.

    Strategy: page is sized identically to the source image (1pt = 1px), so
    coordinates from the manifest map 1:1 onto the page. The image is embedded
    full-bleed; each rectangle becomes a text-field widget with its `name` as
    the field name. Field rendering uses PyMuPDF's default text-field defaults
    (Helvetica, 8pt) — InDesign-authored templates use similar settings.

    Args:
        include_todos: If True, generate fields for TODO_N-named rectangles
            too (preserves their placeholder names). Useful for getting a
            complete starter PDF before iterating on names.
    """
    import fitz  # PyMuPDF

    width, height = page_size
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)

    # Embed source image as full-page background.
    page.insert_image(fitz.Rect(0, 0, width, height), filename=image_path)

    seen_names = set()
    skipped = 0
    for rect in rectangles:
        if not rect.name:
            skipped += 1
            continue
        if rect.name.startswith("TODO_") and not include_todos:
            skipped += 1
            continue
        if rect.name in seen_names:
            raise SystemExit(
                f"Duplicate field name in manifest: {rect.name!r}. "
                "Each rectangle must have a unique name."
            )
        seen_names.add(rect.name)

        widget = fitz.Widget()
        widget.field_name = rect.name
        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        widget.rect = fitz.Rect(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)
        widget.text_font = "Helv"
        widget.text_fontsize = 8
        widget.field_value = ""
        page.add_widget(widget)

    doc.save(output_pdf)
    doc.close()
    logger.info(
        f"Wrote PDF with {len(seen_names)} form fields"
        + (f" ({skipped} skipped)" if skipped else "")
        + f" to {output_pdf}"
    )


# ----------------------------------------------------------------------------
# field_mapping.json skeleton
# ----------------------------------------------------------------------------


_AXIS_TOKENS = ("AX_", "_AXIS", "TWIST", "THROTTLE", "RUDDER", "SLIDER")
_AXIS_NAMES = {"x", "y", "z", "rotx", "roty", "rotz", "twist", "throttle"}


def _classify_field(name: str) -> str:
    """Heuristic: is this PDF field name an axis or a button?

    Mirrors generate_field_mapping_templates.py's existing heuristic so that
    the inverse direction (PDF -> mapping) and forward direction (image ->
    PDF -> mapping) produce mappings with the same shape.
    """
    upper = name.upper()
    if any(tok in upper for tok in _AXIS_TOKENS):
        return "axis"
    return "button"


def write_field_mapping_skeleton(
    rectangles: List[DetectedRect],
    output_path: str,
    device_id: str,
    include_todos: bool = False,
) -> None:
    """Write a starter field_mapping.json with TODO values, ready for hand-fill.

    The bridge from PDF field names to SC inputs is done in this file; the
    generator produces a skeleton with the right keys but placeholder values
    so the human author can fill them in without retyping every name.
    """
    button_map = {}
    axis_map = {}

    for rect in rectangles:
        if not rect.name:
            continue
        if rect.name.startswith("TODO_") and not include_todos:
            continue
        kind = _classify_field(rect.name)
        if kind == "axis":
            # Try to guess axis name from the field name's tail
            tail = rect.name.lower().split("_")[-1]
            axis_map[rect.name] = tail if tail in _AXIS_NAMES else "TODO_AXIS"
        else:
            button_map[rect.name] = "TODO_BUTTON"

    payload = {
        "comment": f"Button and axis mapping for {device_id} (generated; fill TODOs)",
        "device_columns": {
            "_1": "First device (left column or single device)",
            "_2": "Second device (right column or dual setup)",
        },
        "button_mapping": button_map,
        "axis_mapping": axis_map,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    logger.info(
        f"Wrote field_mapping skeleton: {len(button_map)} buttons, "
        f"{len(axis_map)} axes -> {output_path}"
    )


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def cmd_detect(args: argparse.Namespace) -> None:
    image_path = os.path.abspath(args.image)
    if not os.path.exists(image_path):
        raise SystemExit(f"Image not found: {image_path}")

    if args.fill_color:
        fill_hsv, tols, erode_iters = _resolve_fill_color(args.fill_color)
        logger.info(
            f"Using color-based detection (HSV target {fill_hsv}, "
            f"tolerances {tols}, erode={erode_iters})"
        )
        rects = detect_rectangles_by_color(
            image_path,
            fill_hsv=fill_hsv,
            hue_tolerance=tols[0],
            sat_tolerance=tols[1],
            val_tolerance=tols[2],
            min_area=args.min_area,
            max_aspect=args.max_aspect,
            erode_iters=erode_iters,
        )
    else:
        rects = detect_rectangles(
            image_path,
            min_area=args.min_area,
            max_aspect=args.max_aspect,
        )
    if not rects:
        raise SystemExit(
            "No rectangles detected. Try --min-area smaller, --fill-color blue|gray "
            "(if cells have a distinct fill), or check that the image has visibly "
            "outlined label boxes."
        )

    # PDF page size = image size at 72 DPI (1pt = 1px). Read with cv2 was done
    # inside detect; re-read dims here without re-importing cv2 by using PIL.
    from PIL import Image
    with Image.open(image_path) as im:
        width_px, height_px = im.size
    page_size = (float(width_px), float(height_px))

    output = args.output or _default_manifest_path(image_path)
    write_manifest(image_path, rects, page_size, output)

    # Always emit a key PNG next to the manifest so the user can visually
    # map each detected rectangle to its TODO_N name without re-running
    # the script.
    key_path = os.path.splitext(output)[0]
    if key_path.endswith(".manifest"):
        key_path = key_path[: -len(".manifest")]
    key_path += ".key.png"
    render_key_image(image_path, rects, key_path)

    print(f"Detected {len(rects)} rectangles.")
    print(f"  Manifest: {output}")
    print(f"  Key:      {key_path}  (open this to see which TODO_N is which cell)")
    print(f"Edit the manifest to rename TODO_N to real field names, then:")
    print(f"  python {sys.argv[0]} generate {output}")


def cmd_detect_paired(args: argparse.Namespace) -> None:
    """Detect cells of two types in one pass: a colored "label" cell and a
    white-bordered "mapping" cell. Each detected rectangle gets its base
    TODO_N name plus a suffix indicating which type it is.

    Designed for layouts like the X52 where each input has a paired
    gray label cell + white mapping cell."""
    image_path = os.path.abspath(args.image)
    if not os.path.exists(image_path):
        raise SystemExit(f"Image not found: {image_path}")

    fill_hsv, tols, erode_iters = _resolve_fill_color(args.label_color)
    label_rects = detect_rectangles_by_color(
        image_path,
        fill_hsv=fill_hsv,
        hue_tolerance=tols[0], sat_tolerance=tols[1], val_tolerance=tols[2],
        min_area=args.min_area, max_aspect=args.max_aspect,
        erode_iters=erode_iters,
    )
    logger.info(f"Detected {len(label_rects)} {args.label_color} (label) cells")

    mapping_rects = detect_white_bordered_cells(
        image_path,
        excluded_rects=label_rects,
        min_area=args.min_area, max_aspect=args.max_aspect,
    )
    logger.info(f"Detected {len(mapping_rects)} white-bordered (mapping) cells")

    # Stamp suffixes and merge. Each subset retains its scan order; we then
    # re-sort the combined list so the manifest reads top-to-bottom for a
    # human reviewer scanning by position.
    combined: List[DetectedRect] = []
    for i, r in enumerate(label_rects, 1):
        combined.append(DetectedRect(
            name=f"TODO_{i}{args.label_suffix}",
            x=r.x, y=r.y, w=r.w, h=r.h,
        ))
    for i, r in enumerate(mapping_rects, 1):
        combined.append(DetectedRect(
            name=f"TODO_{i}{args.mapping_suffix}",
            x=r.x, y=r.y, w=r.w, h=r.h,
        ))

    combined = _sort_scan_order(combined)
    if not combined:
        raise SystemExit("No rectangles detected for either type.")

    from PIL import Image
    with Image.open(image_path) as im:
        width_px, height_px = im.size
    page_size = (float(width_px), float(height_px))

    output = args.output or _default_manifest_path(image_path)
    write_manifest(image_path, combined, page_size, output)

    key_path = os.path.splitext(output)[0]
    if key_path.endswith(".manifest"):
        key_path = key_path[: -len(".manifest")]
    key_path += ".key.png"
    render_key_image(image_path, combined, key_path)

    n_label = sum(1 for r in combined if r.name.endswith(args.label_suffix))
    n_map = sum(1 for r in combined if r.name.endswith(args.mapping_suffix))
    print(f"Detected {len(combined)} cells total ({n_label} label, {n_map} mapping)")
    print(f"  Manifest: {output}")
    print(f"  Key:      {key_path}")
    print(f"\nGenerate PDF: python {sys.argv[0]} generate {output}")


def cmd_auto_map(args: argparse.Namespace) -> None:
    """OCR the identifier strips next to each detected cell and auto-rename
    the manifest, then emit a populated field_mapping.json.

    For images like the X56 where each blue cell has a sibling white cell
    with text like JOY_25, this turns 75 manual lookups into one command."""
    manifest_path = os.path.abspath(args.manifest)
    if not os.path.exists(manifest_path):
        raise SystemExit(f"Manifest not found: {manifest_path}")
    image, page_size, rects = read_manifest(manifest_path)
    if args.image:
        image = os.path.abspath(args.image)
    if not os.path.exists(image):
        raise SystemExit(f"Image not found: {image}")

    logger.info(f"OCR'ing {len(rects)} identifier strips from {image}")
    raw_text = ocr_label_strips(image, rects)

    # Diagnostic: how many cells got readable text?
    readable = sum(1 for v in raw_text.values() if v)
    logger.info(f"OCR returned text for {readable}/{len(rects)} cells")

    button_map = {}
    axis_map = {}
    hat_map = {}
    todo_count = 0
    new_rects: List[DetectedRect] = []
    for rect in rects:
        text = _pick_joy_line(raw_text.get(rect.name, ""))
        parsed = parse_joy_label(text) if text else None
        if parsed is None:
            # Couldn't parse — keep TODO name and add a TODO mapping entry
            new_name = rect.name if rect.name.startswith("TODO_") else rect.name
            new_rects.append(DetectedRect(name=new_name, x=rect.x, y=rect.y, w=rect.w, h=rect.h))
            button_map[new_name] = "TODO_BUTTON"
            todo_count += 1
            continue

        kind, value = parsed
        # Field name derives from the parsed text: e.g. JOY_25 -> button_25,
        # POV1_UP -> hat_1_up, JOY_Z+ -> axis_z. Matches the t16000 naming
        # convention (button_N, hat_X_dir, axis_X).
        if kind == "button":
            new_name = f"button_{value}"
            button_map[new_name] = value
        elif kind == "axis":
            new_name = f"axis_{value}"
            axis_map[new_name] = value
        elif kind == "hat":
            # value is "hat1_up" -> name "hat_1_up"
            short = value.replace("hat1_", "hat_1_")
            new_name = short
            hat_map[new_name] = value
        else:
            new_name = rect.name
            button_map[new_name] = "TODO_BUTTON"
            todo_count += 1

        # Disambiguate duplicate names by appending the cell's scan-order suffix.
        # Multiple cells can map to the same SC code (e.g. ROTARY 1 FWD and AFT
        # both refer to axis Z; A button JOY_2 and ROTARY 1 PUSH JOY_2 both
        # refer to button 2). Suffix with the original TODO_N so each PDF
        # form-field stays uniquely named while the value-side resolves to the
        # same SC input. The user can rename later if they want.
        existing_names = {r.name for r in new_rects}
        if new_name in existing_names:
            todo_n = rect.name.split("_")[-1] if rect.name.startswith("TODO_") else "x"
            new_name = f"{new_name}_at_{todo_n}"
            # Move the mapping value to the disambiguated name
            for m in (button_map, axis_map, hat_map):
                if rect.name in m:
                    m[new_name] = m.pop(rect.name)
            if kind == "button":
                button_map[new_name] = value
            elif kind == "axis":
                axis_map[new_name] = value
            elif kind == "hat":
                hat_map[new_name] = value

        new_rects.append(DetectedRect(name=new_name, x=rect.x, y=rect.y, w=rect.w, h=rect.h))

    # Save the renamed manifest
    write_manifest(image, new_rects, page_size, manifest_path)

    # Emit the field_mapping.json next to the manifest
    out_dir = os.path.dirname(manifest_path)
    device_id = args.device_id or _device_id_from_manifest(manifest_path)
    mapping_path = os.path.join(out_dir, "field_mapping.json")
    payload = {
        "comment": f"Mapping for {device_id} (OCR-generated; review TODOs)",
        "button_mapping": button_map,
        "hat_mapping": hat_map,
        "axis_mapping": axis_map,
    }
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    print(f"Auto-mapped {len(rects) - todo_count} cells via OCR")
    print(f"  {len(button_map)} buttons, {len(hat_map)} hats, {len(axis_map)} axes")
    if todo_count:
        print(f"  {todo_count} cells unreadable -> kept as TODO_*; review manifest + mapping")
    print(f"  Manifest: {manifest_path}")
    print(f"  Mapping:  {mapping_path}")
    print(f"\nNow re-render the key to verify names: {sys.argv[0]} key {manifest_path}")


def cmd_key(args: argparse.Namespace) -> None:
    manifest_path = os.path.abspath(args.manifest)
    if not os.path.exists(manifest_path):
        raise SystemExit(f"Manifest not found: {manifest_path}")
    image, _, rects = read_manifest(manifest_path)
    if args.image:
        image = os.path.abspath(args.image)
    if not os.path.exists(image):
        raise SystemExit(f"Image not found: {image}")
    if args.output:
        output = os.path.abspath(args.output)
    else:
        base = os.path.splitext(manifest_path)[0]
        if base.endswith(".manifest"):
            base = base[: -len(".manifest")]
        output = base + ".key.png"
    render_key_image(image, rects, output)
    print(f"Wrote key image: {output}")


def cmd_generate(args: argparse.Namespace) -> None:
    manifest_path = os.path.abspath(args.manifest)
    if not os.path.exists(manifest_path):
        raise SystemExit(f"Manifest not found: {manifest_path}")

    image, page_size, rects = read_manifest(manifest_path)
    if args.image:
        image = os.path.abspath(args.image)
    if not os.path.exists(image):
        raise SystemExit(f"Image not found: {image}")

    todo_count = sum(1 for r in rects if not r.name or r.name.startswith("TODO_"))
    if todo_count and not args.allow_todos:
        raise SystemExit(
            f"{todo_count} rectangles still have TODO_* names. Edit the manifest "
            f"to rename them, or pass --allow-todos to generate a starter PDF "
            f"with the placeholder names (you can rename later by editing the "
            f"manifest and re-running)."
        )

    device_id = args.device_id or _device_id_from_manifest(manifest_path)
    output_dir = args.output_dir or os.path.join("visual-templates", device_id)
    os.makedirs(output_dir, exist_ok=True)

    pdf_path = os.path.join(output_dir, f"{device_id}.pdf")
    mapping_path = os.path.join(output_dir, "field_mapping.json")

    generate_pdf(image, page_size, rects, pdf_path, include_todos=args.allow_todos)

    # Only write the skeleton if no field_mapping.json exists yet — running
    # `generate` after `auto_map` (or after manual editing) used to clobber
    # the populated mapping with placeholders. The skeleton is a starting
    # point, not a runtime override.
    if os.path.exists(mapping_path):
        logger.info(f"Leaving existing {mapping_path} in place (use auto_map or hand-edit)")
    else:
        write_field_mapping_skeleton(rects, mapping_path, device_id, include_todos=args.allow_todos)

    print(f"\nGenerated template at {output_dir}/")
    print(f"  - {os.path.basename(pdf_path)}: PDF with form fields")
    print(f"  - {os.path.basename(mapping_path)}: starter field mapping (fill TODOs)")
    print(f"\nNext: add a registry entry to visual-templates/template_registry.json:")
    _print_registry_snippet(device_id, pdf_path, len(rects))


def _resolve_fill_color(spec: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], int]:
    """Parse a --fill-color argument into (HSV, tolerances, erode_iters)."""
    s = spec.strip().lower()
    if s in _NAMED_FILL_COLORS_HSV:
        h, sa, v, ht, st, vt, ei = _NAMED_FILL_COLORS_HSV[s]
        return (h, sa, v), (ht, st, vt), ei
    parts = [p.strip() for p in s.split(",")]
    if len(parts) == 3:
        try:
            return (int(parts[0]), int(parts[1]), int(parts[2])), (15, 40, 60), 0
        except ValueError:
            pass
    raise SystemExit(
        f"Unrecognized --fill-color {spec!r}. Use a named color "
        f"({'/'.join(_NAMED_FILL_COLORS_HSV)}) or H,S,V (e.g. 115,33,255)."
    )


def _default_manifest_path(image_path: str) -> str:
    base = os.path.splitext(os.path.basename(image_path))[0]
    return os.path.join(os.path.dirname(image_path) or ".", f"{base}.manifest.json")


def _device_id_from_manifest(manifest_path: str) -> str:
    base = os.path.basename(manifest_path)
    base = re.sub(r"\.manifest\.json$", "", base)
    base = re.sub(r"\.json$", "", base)
    return base or "new_device"


def _print_registry_snippet(device_id: str, pdf_path: str, field_count: int) -> None:
    rel = os.path.relpath(pdf_path, "visual-templates").replace("\\", "/")
    snippet = {
        "id": device_id,
        "name": device_id.replace("_", " ").title(),
        "pdf": rel,
        "device_match_patterns": ["TODO_PATTERN"],
        "type": "joystick",
        "manufacturer": "TODO",
        "button_count": field_count,
    }
    print()
    print(json.dumps(snippet, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_detect = sub.add_parser("detect", help="Detect rectangles in an image and write a manifest")
    p_detect.add_argument("image", help="Path to the device image (PNG/JPG)")
    p_detect.add_argument("--output", "-o", help="Manifest output path (default: <image>.manifest.json)")
    p_detect.add_argument("--min-area", type=int, default=200, help="Minimum rectangle area in px^2 (default 200)")
    p_detect.add_argument("--max-aspect", type=float, default=30.0, help="Reject rectangles thinner than this aspect ratio (default 30)")
    p_detect.add_argument("--fill-color", help="Find cells by fill color instead of edges. "
                          "Named: blue (X56-style pale cyan), gray (X52-style). Or H,S,V tuple "
                          "(OpenCV ranges: H 0-179, S/V 0-255).")
    p_detect.set_defaults(func=cmd_detect)

    p_paired = sub.add_parser("detect_paired",
                              help="Detect two cell types in one pass: a colored 'label' cell and a "
                                   "white-bordered 'mapping' cell. Each rect gets a type suffix in its name. "
                                   "Designed for X52-style layouts.")
    p_paired.add_argument("image", help="Path to the device image")
    p_paired.add_argument("--output", "-o", help="Manifest output path (default: <image>.manifest.json)")
    p_paired.add_argument("--label-color", default="gray",
                          help="Fill color for label cells (named color or H,S,V). Default: gray.")
    p_paired.add_argument("--label-suffix", default="_label",
                          help="Suffix appended to label-cell field names (default _label)")
    p_paired.add_argument("--mapping-suffix", default="_mapping",
                          help="Suffix appended to white-bordered mapping-cell field names (default _mapping)")
    p_paired.add_argument("--min-area", type=int, default=200)
    p_paired.add_argument("--max-aspect", type=float, default=30.0)
    p_paired.set_defaults(func=cmd_detect_paired)

    p_auto = sub.add_parser("auto_map",
                             help="OCR the identifier strips next to each cell and auto-populate field_mapping.json. "
                                  "Requires Tesseract OCR engine installed.")
    p_auto.add_argument("manifest", help="Path to a manifest JSON")
    p_auto.add_argument("--image", help="Override the image path in the manifest")
    p_auto.add_argument("--device-id", help="Device id (default: derived from manifest filename)")
    p_auto.set_defaults(func=cmd_auto_map)

    p_key = sub.add_parser("key", help="Re-render the key image from a manifest (after renaming TODO_N entries)")
    p_key.add_argument("manifest", help="Path to a manifest JSON")
    p_key.add_argument("--image", help="Override the image path in the manifest")
    p_key.add_argument("--output", "-o", help="Key image output path (default: <manifest>.key.png)")
    p_key.set_defaults(func=cmd_key)

    p_gen = sub.add_parser("generate", help="Generate PDF + field_mapping.json from a manifest")
    p_gen.add_argument("manifest", help="Path to a manifest JSON")
    p_gen.add_argument("--image", help="Override the image path in the manifest")
    p_gen.add_argument("--output-dir", help="Directory to write PDF + mapping (default: visual-templates/<device_id>)")
    p_gen.add_argument("--device-id", help="Device id (default: derived from manifest filename)")
    p_gen.add_argument("--allow-todos", action="store_true", help="Generate even with TODO_* names (those rectangles are skipped)")
    p_gen.set_defaults(func=cmd_generate)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
