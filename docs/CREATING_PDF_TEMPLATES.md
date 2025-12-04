# Creating PDF Device Templates

**Version:** v0.6.1
**Date:** 2025-12-04
**For:** SC Profile Editor PDF-based templates

## Overview

This guide provides step-by-step instructions for creating PDF device templates in Adobe InDesign. These templates are used by SC Profile Editor to display visual representations of HOTAS devices with button labels.

**Prerequisites:**
- Adobe InDesign CC 2020 or later
- Device photograph or image (high quality)
- Knowledge of device button layout
- List of device inputs (see manufacturer documentation)

---

## Quick Start

1. **Prepare device image** (PNG, 1500-2500px wide)
2. **Create InDesign document** (size based on image)
3. **Import image as background** (locked layer)
4. **Add text fields** over each button
5. **Name fields** using SC convention (`js1_button1`, etc.)
6. **Export as Interactive PDF**
7. **Validate** using validation script
8. **Create field_mapping.json** (optional, documents button layout)
9. **Add .build-ignore** (if incomplete) or **update template_registry.json** (if complete)
10. **Test** in SC Profile Viewer

---

## Detailed Workflow

### Step 1: Prepare Device Image

#### Image Requirements

**Resolution:**
- Minimum: 1500px on longest side
- Recommended: 2000-2500px
- Maximum: 3000px (larger = slower rendering)

**Format:**
- PNG (preferred, supports transparency)
- JPG (acceptable if no transparency needed)

**Quality:**
- Clear, well-lit photograph
- Buttons clearly visible
- Minimal background clutter
- Consistent white balance

#### Image Preparation

1. **Crop to device only**
   - Remove excess background
   - Keep small border (10-20px)

2. **Adjust brightness/contrast**
   - Buttons should be clearly visible
   - Labels readable (if present)

3. **Remove background (optional)**
   - Use Photoshop or similar
   - Transparent background looks cleaner
   - Save as PNG to preserve transparency

4. **Save for InDesign**
   - Filename: `{device_id}.png`
   - Example: `vkb_gladiator_evo_right.png`
   - Save in template folder

---

### Step 2: Create InDesign Document

#### Document Setup

**File → New → Document**

**Settings:**
- Intent: Print (or Web)
- Number of Pages: 1
- Facing Pages: Unchecked
- Width: Match image width (px → inches)
  - Example: 2000px = 27.78 inches at 72 DPI
- Height: Match image height
- Orientation: Landscape (usually)
- Margins: 0 (no margins needed)
- Bleed: 0

**Units:**
- Set units to Pixels: Preferences → Units & Increments → Ruler Units → Pixels

**Color Mode:**
- RGB (for screen display)

#### Example Document Sizes

| Device | Image Size | Document Size (inches @ 72 DPI) |
|--------|-----------|----------------------------------|
| VKB Gladiator EVO | 2000x1500 | 27.78 x 20.83 |
| VKB F16 MFD | 1650x1275 | 22.92 x 17.71 |
| VKB THQ | 1800x1400 | 25.00 x 19.44 |

---

### Step 3: Import Device Image

#### Create Layers

**Window → Layers**

Create two layers:
1. **Background** (bottom)
   - For device image
   - Will be locked
2. **Fields** (top)
   - For text fields
   - Active layer for editing

#### Import Image

1. **Select Background layer**
2. **File → Place** (or Ctrl+D)
3. **Select device image** (`{device_id}.png`)
4. **Click on document** to place at full size
5. **Position image**
   - Drag to align with document edges
   - Should fill entire page
6. **Lock Background layer** (click lock icon in Layers panel)

---

### Step 4: Research Device Inputs

Before creating fields, you need to know:
- Number of buttons
- Button locations
- Hat switches (if any)
- Axes (if labeling analog controls)

#### Information Sources

**Manufacturer Documentation:**
- User manuals (PDF)
- Specification sheets
- Official diagrams

**Star Citizen Profile:**
- Open your profile XML
- Search for device name
- Count `js1_button1`, `js1_button2`, etc.

**Community Resources:**
- Reddit r/hotas
- Star Citizen Discord
- Device-specific forums

#### Create Input List

Example for VKB Gladiator EVO:
```
Buttons: 1-34
Axes: x, y, z, rotx, roty, rotz
Hat: hat1 (up, down, left, right)
```

Generate field names:
```
js1_button1
js1_button2
...
js1_button34
js1_x
js1_y
js1_z
js1_rotx
js1_roty
js1_rotz
js1_hat1_up
js1_hat1_down
js1_hat1_left
js1_hat1_right
```

**Tip:** Use the field name generator in PDF_FIELD_NAMING.md

---

### Step 5: Create Text Fields

#### Select Fields Layer

- **Switch to Fields layer** (click in Layers panel)
- Background layer should remain locked

#### Create First Text Field

**Method 1: Using Buttons and Forms Panel**

1. **Window → Interactive → Buttons and Forms**
2. **Select Text Field tool** (from panel)
3. **Draw field** over first button on device image
   - Click and drag to create rectangle
   - Should cover button area
   - Leave small margin

**Method 2: Using Rectangle Tool + Convert**

1. **Draw rectangle** with Rectangle Tool (M)
2. **Right-click → Interactive → Convert to Text Field**

#### Field Properties

**Select field** → Buttons and Forms panel:

**Name:**
- Enter field name exactly: `js1_button1`
- Case-sensitive (use lowercase)
- **This is critical!**

**Appearance:**
- Font: Arial or Helvetica
- Size: 8-12pt (adjust for button size)
- Alignment: Center (both H and V)
- Border: None (or very subtle)
- Fill: None or White (semi-transparent)

**Options:**
- Read Only: Unchecked
- Required: Unchecked
- Multiline: Unchecked
- Scrollable: Unchecked

**PDF Options (will appear on export):**
- Printable: Checked
- Visible: Checked

#### Styling Text Fields

**Text Appearance:**
- Font Color: Black or dark gray
- Font Size: Match button size
  - Small buttons: 7-8pt
  - Medium buttons: 9-10pt
  - Large buttons: 11-12pt
- Font Style: Regular (not bold)

**Field Background:**
- Fill: None (transparent) OR
- Fill: White at 50-70% opacity
- Stroke: None OR
- Stroke: Light gray, 0.5pt

**Recommendation:**
- Transparent background looks cleanest
- White background helps readability on busy images
- Test both and see what works for your device

---

### Step 6: Duplicate and Position Fields

#### Create All Button Fields

**Efficient Workflow:**

1. **Create first field perfectly**
   - Correct size, font, styling
   - Name it `js1_button1`

2. **Duplicate for next button**
   - **Select field** (Selection Tool, V)
   - **Alt+Drag** to duplicate OR
   - **Edit → Copy** (Ctrl+C), **Edit → Paste** (Ctrl+V)

3. **Position over next button**
   - Drag to correct location
   - Align with button center

4. **Rename field**
   - Buttons and Forms panel → Name: `js1_button2`

5. **Repeat** for all buttons

**Tips:**
- Work systematically (top to bottom, left to right)
- Keep a checklist of field names
- Use guides (View → Grids & Guides) for alignment
- Zoom in (Ctrl+Plus) for precision

#### Create Hat Switch Fields

Hat switches need 4 fields (up, down, left, right):

**Layout:**
```
         [hat1_up]
[hat1_left]  ⊕  [hat1_right]
       [hat1_down]
```

**Field Sizes:**
- Smaller than buttons (hats are compact)
- Position around hat center point
- Leave space between fields

**Field Names:**
```
js1_hat1_up
js1_hat1_down
js1_hat1_left
js1_hat1_right
```

#### Create Axis Fields (Optional)

For analog controls (stick axes, throttle):

**Placement:**
- Near the physical control
- Use arrows or labels to indicate direction

**Field Names:**
```
js1_x       (left/right movement)
js1_y       (forward/back movement)
js1_z       (throttle or twist)
js1_rotx    (rotation X)
js1_roty    (rotation Y)
js1_rotz    (rotation Z)
```

**Note:** Axes are less common in visual templates (they're analog, not discrete buttons).

---

### Step 7: Verify Field Names

**Critical Step: Double-Check All Names**

#### Manual Verification

1. **Open Buttons and Forms panel**
2. **Click each field one by one**
3. **Check Name field** in panel
4. **Verify spelling, case, format**

**Common Mistakes:**
- ❌ `JS1_button1` (uppercase)
- ❌ `js1_Button1` (mixed case)
- ❌ `js1-button1` (hyphen)
- ❌ `js1button1` (missing underscore)
- ❌ `js1_btn1` (abbreviated)
- ✅ `js1_button1` (correct!)

#### Use Checklist

Create a text file with all field names:
```
js1_button1
js1_button2
js1_button3
...
```

Check off each one as you verify in InDesign.

#### Export Test PDF Early

- Export a test PDF (see Step 8)
- Run validation script (see Step 9)
- Fix any errors before continuing

---

### Step 8: Export as Interactive PDF

#### Export Settings

**File → Export** (Ctrl+E)

**Save As:**
- Filename: `{device_id}.pdf`
- Example: `vkb_gladiator_evo_right.pdf`
- Location: `visual-templates/{device_id}/`

**Format:**
- Adobe PDF (Interactive)

**Settings (Export to Interactive PDF dialog):**

**General Tab:**
- View: Page Only
- Layout: Single Page
- Presentation: Open in Full Screen Mode: Unchecked

**Forms and Media:**
- **Include All** (critical!)
- Appearance: Visible

**Advanced:**
- Create Tagged PDF: Checked
- Include Structure for Tab Order: Checked

**Compression Tab:**
- Color Images: JPEG, High Quality (300 PPI)
- Grayscale Images: JPEG, High Quality (300 PPI)
- Monochrome Images: CCITT Group 4

**Export**

#### Post-Export Check

**Open PDF in Adobe Acrobat Reader:**
- Fields should be visible (if highlighted)
- Click fields to verify they're interactive
- Names should match InDesign

**If fields aren't working:**
- Re-export with "Include All" under Forms and Media
- Check that fields layer wasn't locked during export
- Verify fields are actually text fields (not just rectangles)

---

### Step 9: Validate PDF

#### Run Validation Script

```bash
python scripts/validation/validate_pdf_fields.py visual-templates/vkb_gladiator_evo_right/vkb_gladiator_evo_right.pdf
```

**Expected Output (if all correct):**
```
======================================================================
PDF Form Field Validation Results
======================================================================
PDF File: visual-templates/vkb_gladiator_evo_right/vkb_gladiator_evo_right.pdf
Total Fields: 44
Valid Fields: 44
Invalid Fields: 0

Valid Fields:
----------------------------------------------------------------------
  [OK] js1_button1
  [OK] js1_button2
  ...
  [OK] js1_x
  [OK] js1_y
  ...

======================================================================
Status: [OK] All field names are valid!
======================================================================
```

#### Fix Validation Errors

**If you see invalid fields:**

1. **Note the field names** that failed
2. **Open InDesign file**
3. **Find those fields** (use Buttons and Forms panel)
4. **Correct the names**
5. **Re-export PDF**
6. **Re-validate**

**Repeat until 0 invalid fields.**

---

### Step 10: Test in SC Profile Viewer

#### Integration Test

1. **Copy PDF to correct location:**
   ```
   visual-templates/{device_id}/{device_id}.pdf
   ```

2. **Update template_registry.json** (see Step 11)

3. **Run SC Profile Viewer** (once Phase 3 is complete)

4. **Load a profile** with this device

5. **Verify:**
   - PDF renders correctly
   - Button labels appear in fields
   - Labels update when edited
   - Export PDF works

---

### Step 11: Create Field Mapping File (Optional but Recommended)

#### When to Create field_mapping.json

Field mapping files are **optional** but highly recommended for templates where:
- PDF field names don't directly match the device's button numbering (e.g., complex devices with named buttons)
- You need to document the mapping between PDF field names and button numbers
- The device has multiple instances or columns (e.g., dual-setup joysticks, MFD panels)
- Button numbering is non-sequential or uses custom names

#### Field Mapping Structure

```json
{
  "comment": "Brief description of the mapping",
  "device_columns": {
    "_1": "Description of first device/column",
    "_2": "Description of second device/column (optional)"
  },
  "button_mapping": {
    "PDF_FIELD_NAME_1": "[BUTTON_NUMBER]",
    "PDF_FIELD_NAME_2": "BUTTON_NUMBER or custom label",
    "PDF_FIELD_NAME_3": ""
  },
  "axis_mapping": {
    "AXIS_FIELD_NAME": "x|y|z|rotx|roty|rotz"
  },
  "hat_mapping": {
    "HAT_FIELD_NAME_UP": "hat1_up|hat2_up|etc",
    "HAT_FIELD_NAME_DOWN": "hat1_down"
  }
}
```

#### Mapping Format Details

**Button Mapping:**
- PDF field name as key (must match exactly)
- Value can be:
  - `"[N]"` (in brackets): Button number for column _1
  - `N` (number only): Button number for column _2 (dual-setup) or primary value
  - `""` (empty string): Field is not mapped to a button (e.g., mode switch indicator)
  - Custom text: Any descriptive label (e.g., `"[ANALOG MODE SWITCH]"`)

**Axis Mapping:**
- Maps axis field names to joystick axis names
- Valid values: `x`, `y`, `z`, `rotx`, `roty`, `rotz`

**Hat Mapping:**
- Maps hat switch field names to hat directions
- Format: `hat[N]_[direction]` where direction is `up`, `down`, `left`, `right`

#### Example: VKB Gladiator SCG Right

```json
{
  "comment": "Button and axis mapping for vkb_gladiator_scg_rh",
  "device_columns": {
    "_1": "First device (left column or single device)",
    "_2": "Second device (right column or dual setup)"
  },
  "button_mapping": {
    "MT_A_1": "[1]",
    "MT_A_2": 1,
    "MT_B_1": "[2]",
    "MT_B_2": 2,
    "A2_A_1": "[3]",
    "A2_A_2": 3
  },
  "axis_mapping": {
    "A1_X": "x",
    "A1_Y": "y",
    "AX_THROTTLE": "z"
  },
  "hat_mapping": {
    "A1_B_2": "hat1_up",
    "A1_C_2": "hat1_down",
    "A1_D_2": "hat1_left",
    "A1_E_2": "hat1_right"
  }
}
```

#### File Location

Save the field mapping file in the same directory as the PDF:

```
visual-templates/{device_id}/
├── {device_id}.pdf
└── field_mapping.json
```

---

### Step 12: Update Template Registry

#### Add Entry to template_registry.json

```json
{
  "id": "vkb_gladiator_evo_right",
  "name": "VKB Gladiator EVO (Right)",
  "pdf": "vkb_gladiator_evo_right/vkb_gladiator_evo_right.pdf",
  "joystick_index": 1,
  "device_match_patterns": [
    "VKBsim Gladiator EVO R",
    "Gladiator EVO R"
  ],
  "type": "joystick"
}
```

**Fields:**
- `id`: Unique identifier (lowercase, underscores)
- `name`: Human-readable name
- `pdf`: Path to PDF file (relative to visual-templates/)
- `joystick_index`: Default JS index (optional, for single-device profiles)
- `device_match_patterns`: List of strings to match device names
- `type`: Device type (joystick, throttle, mfd, pedals)

---

### Step 13: Mark Incomplete Templates with .build-ignore (If Needed)

#### When to Use .build-ignore

If your template is **incomplete** or **not ready for production**, you should mark it with a `.build-ignore` file to prevent it from being included in builds and installers. This is useful for:
- Templates with incomplete PDF fields
- Templates that haven't been validated yet
- Templates still being tested or refined
- Templates with known issues
- Experimental device support

#### How to Use .build-ignore

1. **Create empty file in template directory:**
   ```
   visual-templates/{device_id}/.build-ignore
   ```

2. **File contents:** Leave the file empty (it's just a marker)

3. **Example structure:**
   ```
   visual-templates/vkb_thq/
   ├── vkb_thq.pdf
   ├── field_mapping.json
   └── .build-ignore    ← Prevents this template from building
   ```

#### Build Process with .build-ignore

**During Development (before marking complete):**
1. Create template directory and files
2. Add `.build-ignore` file
3. Test locally: Application still loads and displays templates from `visual-templates/`
4. Validate and refine the template

**When Ready for Release:**
1. **Remove** the `.build-ignore` file
2. Run build: `python scripts/build/build_exe.py --increment patch`
   - Build script scans for `.build-ignore` files
   - Excludes marked templates from the build output
   - Creates `dist/visual-templates/` with only complete templates
   - Packages executable with complete templates only
3. Build installer: `cmd //c scripts\build\build_installer.bat`
   - Installer copies from `dist/` (not `visual-templates/`)
   - Only complete templates are included

**User Distribution:**
- Users receive executable and installer with only complete, validated templates
- Incomplete templates never reach end users
- Development templates remain in your git repository for future completion

#### Example: Marking a Template Complete

```bash
# When template is ready
rm visual-templates/vkb_thq/.build-ignore

# Build for distribution
python scripts/build/build_exe.py --increment patch
```

#### Current Incomplete Templates

The following templates currently have `.build-ignore` files:

- `vkb_stecs` - STECS throttle (incomplete)
- `vkb_stecs_atem` - STECS with ATEM module (incomplete)
- `vkb_stecs_spacethrottlegrip_lh` - STECS with Space Throttle Grip left (incomplete)
- `vkb_stecs_spacethrottlegrip_rh` - STECS with Space Throttle Grip right (incomplete)
- `vkb_stecs_stem` - STECS with STEM module (incomplete)
- `vkb_thq_v` - VKB Throttle Quadrant V (incomplete)
- `vkb_thq_v_ww2` - VKB Throttle Quadrant V WW2 (incomplete)
- `vpc_mt50cm3_left` - VPC MongoosT-50CM3 left (incomplete)
- `vpc_mt50cm3_right` - VPC MongoosT-50CM3 right (incomplete)
- `thrustmaster_t16000` - Thrustmaster T16000 (incomplete)
- `thrustmaster_twcs_throttle` - Thrustmaster TWCS Throttle (incomplete)

---

## Advanced Topics

### Multi-Page Templates

**If device has front and back views:**

1. **Create 2-page InDesign document**
2. **Page 1:** Front view with front buttons
3. **Page 2:** Back view with back buttons
4. **Export:** Will create multi-page PDF
5. **Application:** Will display pages as tabs or side-by-side

### Templates for Multiple Joystick Instances

**Problem:** User has two of the same device (e.g., left and right sticks)

**Option 1: Separate Templates**
- Create `vkb_gladiator_evo_right.pdf` (js1_* fields)
- Create `vkb_gladiator_evo_left.pdf` (js2_* fields if it's the second device)

**Option 2: Dynamic Field Names**
- Future feature: Application renames fields on the fly
- Not implemented in v0.4.0

### High-DPI / Retina Displays

**For sharper rendering:**
- Use higher resolution images (2500-3000px)
- Export PDF at high quality (300 PPI)
- Application renders at user's DPI setting

### Accessibility

**For users with vision impairments:**
- Use high-contrast field styling
- Larger font sizes (10-12pt minimum)
- Clear field borders
- Test with screen readers (future feature)

---

## Troubleshooting

### Fields Don't Appear in PDF

**Cause:** Export settings incorrect

**Fix:**
- Re-export with "Forms and Media: Include All"
- Verify fields are text fields (not just rectangles)
- Ensure Fields layer is unlocked and visible

### Field Names Wrong in Exported PDF

**Cause:** Names changed after export or typo in InDesign

**Fix:**
- Re-check names in InDesign (Buttons and Forms panel)
- Re-export PDF
- Validate again

### PDF Too Large (File Size)

**Cause:** High-resolution image, no compression

**Fix:**
- Reduce image resolution (2000px is usually enough)
- Use JPEG compression in export (High Quality, 300 PPI)
- Consider reducing color depth (24-bit → 8-bit if grayscale)

### Fields Misaligned with Buttons

**Cause:** Image moved or fields positioned incorrectly

**Fix:**
- Lock Background layer before creating fields
- Use guides and grids for precision alignment
- Zoom in (400-800%) for fine positioning

### Validation Script Errors

**"PDF has no form fields"**
- Export settings missing "Include All" for forms
- Fields weren't actually created (just shapes)

**"Invalid field name: JS1_button1"**
- Uppercase letters used (must be lowercase)
- Fix in InDesign, re-export

**"Button numbering gap"**
- Warning only (not an error)
- Some buttons skipped (e.g., button1, button3, but no button2)
- Verify device actually has those buttons

---

## Tips and Best Practices

### Efficiency

1. **Create first field perfectly**, then duplicate
2. **Use keyboard shortcuts**:
   - V = Selection Tool
   - Alt+Drag = Duplicate
   - Ctrl+Shift+> = Increase font size
   - Ctrl+Shift+< = Decrease font size
3. **Work in batches** (all buttons, then all hats, then axes)
4. **Save frequently** (Ctrl+S)

### Quality

1. **Use high-quality device images**
2. **Test field visibility** with different label lengths
3. **Ensure font is readable** at final size
4. **Check PDF in Acrobat** before validating

### Organization

1. **Save InDesign source file** (`.indd`) in template folder
2. **Keep field name checklist** as text file
3. **Document special cases** (non-standard buttons)
4. **Version control** (commit to git after validation passes)

---

## Example: VKB Gladiator EVO Right

### Device Specs

- **Buttons:** 34 (button1 - button34)
- **Axes:** 6 (x, y, z, rotx, roty, rotz)
- **Hat:** 1 (hat1: up, down, left, right)
- **Total Fields:** 44

### Field Layout

**Stick Buttons (on grip):**
- Trigger: button1
- Top button: button2
- Side buttons: button3-button6
- Thumb buttons: button7-button12
- etc.

**Base Buttons:**
- button13-button34 (various switches and buttons)

**Hat Switch:**
- POV hat on thumb: hat1 (4 directions)

**Axes:**
- Pitch/Roll: x, y
- Twist: rotz
- Throttle: z (if equipped)

### Template File Structure

**Minimal (Complete Template):**
```
visual-templates/vkb_gladiator_evo_right/
├── vkb_gladiator_evo_right.pdf          # Exported PDF template (REQUIRED)
├── vkb_gladiator_evo_right.png          # Device image (optional, for reference)
└── vkb_gladiator_evo_right.indd         # InDesign source file (optional, for future edits)
```

**With Field Mapping (Recommended for complex devices):**
```
visual-templates/vkb_gladiator_evo_right/
├── vkb_gladiator_evo_right.pdf          # Exported PDF template (REQUIRED)
├── field_mapping.json                   # Button to field name mapping (RECOMMENDED)
├── vkb_gladiator_evo_right.png          # Device image (optional)
└── vkb_gladiator_evo_right.indd         # InDesign source file (optional)
```

**Incomplete Template (During Development):**
```
visual-templates/vkb_thq/
├── vkb_thq.pdf                          # Exported PDF template
├── field_mapping.json                   # Button to field name mapping
├── .build-ignore                        # Marker: excludes from build
├── vkb_thq.png                          # Device image
└── vkb_thq.indd                         # InDesign source file
```

---

## Appendix

### Recommended Tools

**Adobe InDesign:**
- Version: CC 2020 or later
- Alternative: Affinity Publisher (may work, not tested)

**Image Editing:**
- Adobe Photoshop (crop, adjust, remove background)
- GIMP (free alternative)
- Paint.NET (Windows, simple edits)

**PDF Viewing:**
- Adobe Acrobat Reader DC (verify form fields)
- Browser built-in PDF viewer (quick check)

### Keyboard Shortcuts (InDesign)

| Action | Shortcut |
|--------|----------|
| Place Image | Ctrl+D |
| Selection Tool | V |
| Text Tool | T |
| Duplicate (drag) | Alt+Drag |
| Copy | Ctrl+C |
| Paste | Ctrl+V |
| Export | Ctrl+E |
| Zoom In | Ctrl+Plus |
| Zoom Out | Ctrl+Minus |
| Fit Page in Window | Ctrl+0 |
| Show/Hide Rulers | Ctrl+R |
| Show/Hide Guides | Ctrl+; |

### Resources

**Documentation:**
- `docs/PDF_FIELD_NAMING.md` - Field naming specification
- `docs/PDF_MIGRATION_PLAN.md` - Overall v0.4.0 plan
- `scripts/validation/validate_pdf_fields.py` - Validation script

**Community:**
- GitHub Issues: Report problems or ask questions
- Discord: #sc-profile-viewer channel

---

## Version History

- **v0.6.1 (2025-12-04):** Enhanced guide with field mapping and build configuration
  - Added Step 11: Field mapping file documentation (field_mapping.json)
  - Added Step 12: Updated template registry instructions
  - Added Step 13: Build-ignore file usage for incomplete templates
  - Updated Quick Start with new steps
  - Expanded template file structure examples
  - Added current incomplete templates list
  - Updated version and application name references

- **v0.4.0 (2025-01-08):** Initial guide for PDF template creation
  - Complete InDesign workflow
  - Field naming integration
  - Validation process
  - Troubleshooting guide
