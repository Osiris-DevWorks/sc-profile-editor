# Star Citizen Profile Editor

A desktop application for editing and exporting Star Citizen control profiles in human-readable formats. Create visual diagrams of your controller layouts and export your bindings to PDF, Word, CSV, and annotated device graphics.

![Version](https://img.shields.io/badge/version-0.6.1-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## Features

- Import and customize Star Citizen control profiles
- **Table-based input editing** - Edit inputs directly from Controls Table
- **Device Configuration** - Map physical devices to joystick slots with hot-swap detection
- **Automatic input detection** - Detect joystick buttons, axes, keyboard keys, and mouse clicks
- **Keyboard modifier support** - Full Ctrl, Alt, Shift support with left/right distinction
- Generate visual controller diagrams with labeled buttons
- Export to multiple formats: PDF, Word, CSV, PNG
- 20+ device templates (VKB, VPC, Thrustmaster)
- Custom label system for cleaner graphics
- Filter and search control bindings
- Interactive PDF-based device viewer

## Download & Installation

You can download SC Profile Editor from the [GitHub Releases page](https://github.com/Osiris-RK/sc-profile-editor/releases). Two options are available:

### Option 1: Installer (Recommended)

**`SCProfileEditor-vX.X.X-Setup.exe`** - Full installer with automatic updates

- Double-click to run the installer
- Choose your installation location
- Creates Start Menu shortcuts
- Easy uninstall via Programs & Features
- Recommended for most users

### Option 2: Standalone Executable

**`SCProfileEditor.exe`** - Portable version (no installation required)

- Download and run directly
- No installation or Admin rights needed
- Perfect for portable storage or USB drives
- All settings stored locally in the executable folder
- Choose this if you prefer minimal system changes

## System Requirements

- Windows 10 or later (64-bit)
- No additional dependencies required

---

## Getting Started

### Importing a Profile

1. **Launch the application**
2. Click the **"Import Profile XML"** button (green button in the top-right)
3. Navigate to your Star Citizen profiles folder (usually `C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\USER\Client\0\Profiles\default`)
4. Select your exported profile XML file
5. Click **Open**

The application will automatically load the last profile you opened when you start it again.

## Main Features

### Three Application Tabs

The application is organized into three main tabs:

1. **Controls Table** - View and edit all your control bindings in a searchable, filterable table
2. **Device View** - See & edit buttons in a visual representations of your controllers with labeled buttons
3. **Config** - Manage connected devices and configure device-to-joystick mappings
4. **About** - Project information and acknowledgements

### Two Viewing Modes

The Controls Table offers two ways to view your control bindings:

#### Default View (Simplified)
- Shows only essential information: **Action Map**, **Action**, and **Device**
- Perfect for quick reference and printing
- Cleaner, more compact display

#### Detailed View (Complete)
- Shows all information including:
  - **Action Map**: The category of the action (e.g., "Spaceship Movement")
  - **Action (Original)**: The auto-generated action name
  - **Action (Override)**: Your custom label (if you've set one)
  - **Input Code**: The raw input code (e.g., "js1_button5")
  - **Input Label**: Human-readable input (e.g., "Joystick 1: Button 5")
  - **Device**: The device name

**To toggle between views:** Check/uncheck the **"Show Detailed"** checkbox in the Filters section.

---

## Device Configuration

The **Config** tab helps you manage your connected devices and ensure consistent control mappings across sessions.

### What's the Config Tab?

The Config tab displays:
- **Connected Devices** - All currently connected devices (keyboard, mouse, joysticks)
- **Device-to-Joystick Mapping** - Configuration for which physical device maps to which SC profile joystick identifier
- **Star Citizen Profiles Directory** - Path to your SC control profiles folder

### Connected Devices

The connected devices section shows:
- **Device Type** - Keyboard, Mouse, or Joystick
- **Product Name** - The actual device name (e.g., "T.16000M", "Keyboard")
- **Instance** - The device instance number

**Refresh Devices button** - Click to detect any newly connected or disconnected devices 

### Device-to-Joystick Mapping

When you have multiple joysticks connected, Star Citizen assigns them joystick slots (js1, js2, js3, etc.) based on connection order. If you unplug and replug devices in different order, the mappings change - breaking your profile bindings.

**Solution: Configure persistent device mappings**

1. Select which physical device maps to which slot (js1, js2, js3)
2. Click **"Save Configuration"** to persist the mapping
3. The app will remember this configuration and apply it to input detection

**Auto-Populate button** - Automatically map all connected joysticks to js1, js2, js3 based on detection order. 

### Star Citizen Profiles Directory

Specify where your Star Citizen control profiles are stored. This helps the app quickly load profiles without browsing.

**Default location:** `C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\USER\Client\0\Controls\Mappings`

---

## Input Detection & Remapping

### Detecting Inputs

When editing a control binding, you can use the **"Detect Input"** button to automatically detect what button/key you press:

1. Click the **Edit** button in the Controls Table for any action
2. In the RemapDialog, click **"Detect Input"** (or in the "Change Input Binding" section)
3. Press the button/key you want to bind
4. The input will be detected automatically (joystick buttons, axes, keyboard keys, mouse clicks)
5. Optionally adjust which device this input maps to using the dropdown
6. Click **"Save Binding"** to apply

### Supported Input Types

**Joystick:**
- Buttons (up to 32 per joystick)
- Analog axes (X, Y, Z, throttle, etc.)
- POV hats (8-direction switches)

**Keyboard:**
- All letter keys, numbers, symbols
- Function keys (F1-F12)
- Modifier combinations (Ctrl+A, Alt+P, Shift+Down, etc.)
- Arrow keys, Enter, Space, Tab, etc.

**Mouse:**
- Left, Right, Middle buttons
- Forward, Back buttons (5-button mice)

### Keyboard Modifiers

Full support for modifier key combinations:
- **Ctrl** (Left and Right)
- **Alt** (Left and Right, including AltGr for non-US keyboards)
- **Shift** (Left and Right)

Just hold the modifier key while pressing another key - the app will detect the combination automatically!

**Examples:**
- Ctrl+A, Alt+P, Shift+Down
- Right Ctrl+Right Shift (both modifier keys together)

### Manual Input Selection

Can't detect your input? Use the searchable dropdown in the "Change Input Binding" section:

1. Click in the input dropdown
2. Type to search (e.g., "button", "ctrl", "axis")
3. Select your input from the list
4. The full list shows all available inputs organized by device type

---

## Control Table Views

### Understanding the Table

The control table displays all your keybindings organized by action map. Each row represents one binding.

**Default Columns:**
- **Action Category**: Category like "Spaceship Movement", "Spaceship Weapons", etc.
- **Label**: Custom or auto-generated short name for the action
- **Input**: Human-readable input description (e.g., "Joystick 1: Button 5") with tooltip showing raw code
- **Device**: Which controller (e.g., "Keyboard", "Joystick 1")
- **Edit**: Pencil icon button to open RemapDialog for editing that specific binding

**Detailed Columns (when "Show Detailed" is checked):**
- All default columns plus:
- **Action**: The original auto-generated action name from Star Citizen

### Editing Inputs

Click the **Edit** button (pencil icon) in any row to open the RemapDialog:
- Change the input binding (use Detect Input or manual dropdown selection)
- Change which device the input maps to
- See whether the binding is applied to a single action or multiple actions
- Confirm changes with Save Binding

This is especially useful when you want to:
- Remap a button to a different input
- Move a binding from one device to another
- Apply device mapping configuration to detected inputs

### Sorting

Click any column header to sort by that column. Click again to reverse the sort order.

---

## Customizing Labels

One of the most powerful features is the ability to create custom, shorter labels for actions to make your graphics more readable.

### How to Edit Labels

1. **Find the action** you want to rename in the Control Table
2. **Double-click** the cell in the "Action" column (or "Action (Override)" if in detailed view)
3. The text will be selected automatically
4. **Type your new label** (e.g., change "Missile Launch" to "ML")
5. Press **Enter** or click outside the cell to save

**Examples:**
- "Fire" → "F"
- "Afterburner" → "AB"
- "Target Cycle All Forward" → "Next Tgt"
- "Shield Raise Level Forward" → "Shld Fwd"

### Reverting Custom Labels

To remove a custom label and return to the auto-generated one:

1. **Double-click** the action label cell
2. **Select all text** (Ctrl+A) and **delete** it (or just press Delete since text is auto-selected)
3. Press **Enter**

The label will revert to either:
- The global default label (if one exists in `label_overrides.json`)
- The auto-generated label

### How Label Overrides Work

The application uses a two-tier label system:

1. **Global Defaults** (`label_overrides.json`)
   - Pre-configured short labels for 72 common Star Citizen actions
   - Shipped with the application
   - Examples: "v_attack1" → "Fire", "v_afterburner" → "Afterburner"

2. **Custom Overrides** (`label_overrides_custom.json`)
   - Your personal customizations
   - Created automatically when you edit your first label
   - Takes priority over global defaults
   - Not tracked in version control (your personal file)

**Priority Order:**
1. Your custom label (if you've edited it)
2. Global default label (if defined)
3. Auto-generated label (from the action name)

---

## Device View

The **Device View** tab shows interactive visual representations of your controllers with your bindings labeled on them.

### Available Device Templates

The application includes PDF templates for 20+ devices:
- **VKB Gladiator** - EVO and SCG variants (Left/Right, OTA variants)
- **VKB Gunfighter** - MCG Ultimate, SCG variants (Left/Right, OTA variants)
- **VKB Space Sim Module (SEM)** - Standard and V variants
- **VKB STECS Throttle System** - Base unit, STEM, ATEM, Space Throttle Grips
- **VKB Throttle Quadrants** - THQ, THQ-V, THQ-WW2, THQ-V-WW2
- **VKB F16 MFD** - Multi-Function Display
- **VPC MongoosT-50CM3** - Right stick
- **Thrustmaster TWCS** - Throttle

### How Graphics Work

1. Switch to the **"Device View"** tab
2. Select your device from the dropdown
3. The interactive PDF will show:
   - Button/axis labels on the device diagram
   - Your custom action labels automatically filled in
   - Easy-to-read layout

**Graphics automatically update** when you edit labels in the Control Table!

### Using the Interactive PDF Viewer

- **Zoom**: Use your mouse wheel or the zoom controls
- **Navigate**: The PDF viewer provides browser-like controls
- **Export**: Click the "Export Graphic" button in the top header to save as PNG or PDF

---

## Exporting Your Profile

You can export your profile in four formats. All export buttons are located in the top header for easy access:

### Export to CSV

**Best for:** Spreadsheets, further data processing

1. Click **"Export CSV"** button
2. Choose a location and filename
3. Click **Save**

The CSV will contain all visible rows from your current view (default or detailed).

**Opens in:** Excel, Google Sheets, LibreOffice Calc

### Export to PDF

**Best for:** Printing, sharing, archiving

1. Click **"Export PDF"** button
2. Choose a location and filename
3. Click **Save**

The PDF includes:
- Profile information
- Device list
- Full table of bindings (formatted for landscape orientation)

**Features:**
- Professional formatting
- Alternating row colors for readability
- Automatic page breaks

### Export to Word Document

**Best for:** Editing, custom formatting, documentation

1. Click **"Export Word"** button
2. Choose a location and filename
3. Click **Save**

The Word document includes:
- Title page with profile name
- Device information
- Formatted table of bindings
- Easy to customize and edit

**Opens in:** Microsoft Word, Google Docs, LibreOffice Writer

### Export Device Graphic

**Best for:** Visual reference, printing controller layouts

1. Switch to the **"Device View"** tab
2. Select your device from the dropdown
3. Click the **"Export Graphic"** button in the top header
4. Choose format (PNG or PDF) and location
5. Click **Save**

The graphic will include:
- Device image with labeled controls
- Your custom action labels
- Clear, print-ready layout

**Note:** The Export Graphic button is only enabled when a device with a template is loaded.

### Export Modes

All table export formats (CSV, PDF, Word) respect the **"Show Detailed"** checkbox:
- **Unchecked**: Exports simplified view (3 columns)
- **Checked**: Exports detailed view (6 columns)

---

## Filters and Search

### Search Box

Type in the **Search** box to filter bindings by any text:
- Action names
- Device names
- Input labels
- Action maps

**Example searches:**
- "fire" - Shows all fire-related actions
- "joystick 1" - Shows all Joystick 1 bindings
- "shield" - Shows all shield controls

### Device Filter

Select a device from the **Device** dropdown to show only bindings for that device:
- All Devices (default)
- Keyboard
- Mouse
- Joystick 1
- Joystick 2
- etc.

### Action Map Filter

Filter by category using the **Action Map** dropdown:
- All Action Maps (default)
- Spaceship Movement
- Spaceship Weapons
- Spaceship Targeting
- Spaceship Mining
- etc.

### Hide Unmapped Keys

Check **"Hide Unmapped Keys"** to hide any inputs that don't have bindings assigned.

### Clear Filters

Click **"Clear Filters"** to reset all filters and show everything.

---

## Tips and Tricks

### Creating a Reference Card

1. **Customize labels** for your most important actions with short names
2. Switch to **Default View** (uncheck "Show Detailed")
3. **Filter** to show only one device (e.g., "Joystick 1")
4. **Export to PDF**
5. Print and keep next to your controller!

### Quick Label Editing

- Labels are **auto-selected** when you double-click, so you can immediately start typing
- Press **Delete** to clear a label completely (reverts to default)
- Press **Escape** while editing to cancel changes

### Understanding Your Setup

Use **Detailed View** to see:
- Which physical buttons are mapped (Input Code + Input Label)
- Original action names vs. your custom labels
- Device assignments at a glance

### Graphics Workflow

1. **First pass**: Use default labels to see what's mapped
2. **Customize**: Edit labels to short versions that fit in graphics
3. **Export graphics**: Switch to Device View tab and export images
4. **Print**: Create a physical reference sheet

### Managing Multiple Profiles

The application remembers your last loaded profile and automatically opens it on startup. To switch profiles:
1. Click **"Import Profile XML"**
2. Select a different profile
3. Your custom labels are **saved globally** and will apply to matching actions in any profile

### Backup Your Custom Labels

Your custom labels are stored in `label_overrides_custom.json` in the application directory. To backup:
1. Locate the file in the application folder
2. Copy it to a safe location
3. To restore, just copy it back

---

## Example Workflow

### Scenario: Creating a HOTAS Reference Card

1. **Import** your Star Citizen profile
2. **Filter** to show only "Joystick 1" in the Device filter
3. **Edit labels** to create short versions:
   - "Target Cycle All Forward" → "Next"
   - "Target Cycle All Back" → "Prev"
   - "Missile Launch" → "MSL"
   - "Shield Raise Level Forward" → "Shld F"
4. **Switch to Device View** tab
5. **Select** your joystick model
6. **Verify** the labels look good on the graphic
7. **Export** the graphic as an image
8. **Return to Control Table** and export to PDF
9. **Print** both the graphic and the PDF for reference

---

## Troubleshooting

### Table doesn't show after importing

- Toggle any checkbox (like "Show Detailed") to refresh the view
- This is a known issue that will be fixed in the next update

### Custom labels not appearing in graphics

- Make sure you pressed Enter after editing the label
- Switch tabs and back to refresh the graphics

### Can't edit a cell

- Make sure you're double-clicking the "Action" or "Action (Override)" column (column 2)
- Other columns are read-only

### Export buttons are disabled

- Make sure you've imported a profile first
- The buttons enable after a successful profile load

---

## Keyboard Shortcuts

Currently, the application uses standard Qt shortcuts:
- **Ctrl+C**: Copy selected text
- **Ctrl+V**: Paste (when editing)
- **Escape**: Cancel editing
- **Enter**: Save edit

---

## Getting Help

For issues, feature requests, or contributions:
- Join the Discord community (link in app footer)
- Report bugs with steps to reproduce
- Request new device templates
- Share your custom label configurations
- Suggest improvements

---

## Developer Documentation

For development setup, building from source, and contributing:
- See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

---

## Version Information

This guide is for Star Citizen Profile Editor v0.6.1

**Major Features in v0.6.1:**
- **Device Configuration Tab** - Manage connected devices and device-to-joystick mappings
- **Device hot-swap detection** - Automatically detect newly connected devices
- **Automatic input detection** - Detect joystick, keyboard, and mouse inputs with one click
- **Keyboard modifier support** - Full Ctrl, Alt, Shift support with left/right distinction
- **Table-based input editing** - Edit inputs directly from Controls Table with Edit button
- **Interactive PDF-based device templates** (20+ devices supported)
- **Expanded VKB device support** (Gladiator, Gunfighter, STECS, THQ variants)
- **Four-tab interface:** Controls Table, Device View, Config, About
- **Custom label override system** with three-tier priority
- **Show Detailed view toggle** (3 or 6 columns)
- **Export to CSV, PDF, Word, and device graphics** (PNG/PDF)
- **Filter by device, action map, search text**
- **Automatic label mapping** to device buttons
- **Version display** in window title and exports

---

## Support the Project

SC Profile Editor is a free, open-source project created to help Star Citizen players manage their control profiles. If you find it useful and would like to support the development, here are ways you can help:

### Donate

Your financial support helps fund development of new features and device templates:

💳 **[PayPal Donation](https://paypal.me/RighteousKill)** - Support via PayPal

💰 **[Venmo Donation](https://venmo.com/u/Amr-Abouelleil)** - Support via Venmo

### Contribute

- **Report bugs** with steps to reproduce
- **Request features** you'd like to see
- **Request device templates** for controllers you own
- **Share configurations** and label sets with the community
- **Submit code contributions** via GitHub

### Join the Community

💬 **[Discord Community](https://discord.gg/BNzRegKZ7k)** - Join for support, discussions, and feature requests

Even if you can't donate, your feedback and bug reports are invaluable!

---

**Happy Flying, Citizen!** o7
