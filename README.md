# Star Citizen Profile Editor

A desktop application for editing and exporting Star Citizen control profiles in human-readable formats. Create visual diagrams of your controller layouts and export your bindings to PDF, Word, CSV, and annotated device graphics.

![Version](https://img.shields.io/badge/version-0.7.5-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

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

### System Requirements

- Windows 10 or later (64-bit)
- No additional dependencies required

---

## Quick Start

### Launching the Application

1. **Launch the application**
2. The app will automatically load the last profile you used (or start with an empty workspace)

### Importing Your First Profile

1. Click the **"Import Profile XML"** button (green button in the top-right)
2. Navigate to your Star Citizen profiles folder (usually `C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\USER\Client\0\Profiles\default`)
3. Select your exported profile XML file
4. Click **Open**

Your profile will load into the **Controls Table** tab, showing all your current key bindings.

### Understanding the Four Tabs

- **Controls Table** - View and edit all your control bindings in a searchable, filterable table
- **Device View** - Visual representations of your controllers with labeled buttons
- **Config** - Manage connected devices and configure device-to-joystick mappings
- **About** - Project information and acknowledgements

---

## Common Tasks

### Loading a Preset Profile to Get Started

Start with a pre-configured profile for your controller setup, then customize it:

1. Click the **"Load Preset Profile"** button (purple button in the top menu)
2. Select a preset that matches your hardware (T.16000M, Warthog, VKB Gladiator, etc.)
3. The profile loads as a starting point
4. Customize the bindings for your preferences
5. Save your customized profile

**Tip:** After loading a preset, customize the labels for better readability.

### Configuring Your Devices

If you have multiple joysticks, use the **Config** tab to ensure consistent mappings:

1. Go to the **Config** tab
2. Review the **Connected Devices** section (shows keyboard, mouse, and joysticks)
3. Click **Refresh Devices** if you've recently plugged/unplugged devices
4. In the **Device-to-Joystick Mapping** section, select which physical device maps to which joystick slot (js1, js2, js3)
5. Click **"Save Configuration"** to persist the mapping
6. (Optional) Click **Auto-Populate** to automatically assign connected joysticks

**Why this matters:** When you unplug and replug joysticks in different order, Star Citizen assigns them different slots. Persistent mappings ensure your profile bindings stay consistent.

### Viewing Your Bindings

The **Controls Table** offers two viewing modes:

**Default View (Simplified)** - Shows: Action Category, Label, Input, Device
- Perfect for quick reference and printing
- Cleaner, more compact display

**Detailed View (Complete)** - Shows: All columns plus Input Code and full Action name
- Use this to understand the raw input codes (e.g., "js1_button5")
- See both original action names and your custom labels

**To toggle:** Check/uncheck the **"Show Detailed"** checkbox in the Filters section.

### Editing Control Bindings

#### Using Input Detection (Fastest)

1. Click the **Edit** button (pencil icon) in any row of the Controls Table
2. In the RemapDialog, click **"Detect Input"**
3. Press the button/key you want to bind (joystick button, keyboard key, mouse button, or combinations)
4. The app detects it automatically
5. (Optional) Adjust which device this input maps to using the dropdown
6. Click **"Save Binding"** to apply

**Supported inputs:**
- **Joystick:** Buttons (up to 32), analog axes (X, Y, Z, throttle, etc.), POV hats
- **Keyboard:** Letter keys, numbers, function keys, modifier combinations (Ctrl+A, Alt+P, Shift+Down)
- **Mouse:** Left, Right, Middle, Forward, Back buttons

**Full modifier support:** Ctrl, Alt, Shift (left and right variants). Just hold the modifier while pressing another key!

#### Manual Selection (If Detection Doesn't Work)

1. Click **Edit** for the binding you want to change
2. Click the dropdown in the "Change Input Binding" section
3. Type to search (e.g., "button5", "ctrl", "axis_x")
4. Select your input from the list

### Customizing Labels for Better Readability

You can create and display shorter labels for actions to make the graphical view more readable:

1. In the **Controls Table**, find the action you want to rename
2. **Double-click** the cell in the "Label" or "Action (Override)" column
3. The text will be selected automatically
4. **Type your new label** (e.g., change "Missile Launch" to "ML" or "Fire")
5. Press **Enter** or click outside the cell to save

**Examples:**
- "Target Cycle All Forward" → "Next Tgt"
- "Afterburner" → "AB"
- "Shield Raise Level Forward" → "Shld Fwd"

**To revert a custom label:**
1. Double-click the label cell
2. Press **Delete** to clear it (or Ctrl+A then Delete)
3. Press **Enter** - it will revert to the global default or auto-generated label

### Creating Visual Controller Diagrams

The **Device View** tab shows interactive visual representations of your controllers with your bindings labeled:

1. Switch to the **"Device View"** tab
2. Select your device from the dropdown (VKB Gladiator, T.16000M, etc.)
3. The PDF will display with your labels automatically filled in
4. Labels automatically update when you edit them in the Control Table!

**To export the diagram as an image:**
1. Switch to **Device View** tab
2. Select your device
3. Click **"Export Graphic"** button
4. Choose format (PNG or PDF) and location
5. Use for reference or printing

### Exporting Your Profile

All export buttons are in the top header. Exports respect your current view (default or detailed):

**Export to CSV**
- Best for: Spreadsheets and data processing
- Opens in: Excel, Google Sheets, LibreOffice Calc

**Export to PDF**
- Best for: Printing and sharing
- Includes: Profile info, device list, formatted table with landscape orientation

**Export to Word Document**
- Best for: Editing and custom formatting
- Includes: Title page, device information, formatted table

All exports use the **"Show Detailed"** setting - uncheck it for simplified exports, check it for complete details.

### Filtering and Searching Bindings

The **Controls Table** has multiple ways to find and organize what you're looking for:

- **Search Box:** Type any text (action name, device, input label, etc.)
  - Example: "fire" → shows all fire-related actions
- **Device Filter:** Show only bindings for a specific device
- **Action Map Filter:** Show only specific categories (Spaceship Movement, Weapons, etc.)
- **Key Filter:** Show only bindings for a specific button, key, or axis
  - Use the dropdown to manually select a key
  - **Or use "Detect Key"** button to automatically filter by pressing a button/key (no need to remember names!)
- **Show Detailed:** Toggle between simplified (3 columns) and complete (6 columns) view
- **Sorting:** Click any column header to sort by that column (click again to reverse order)
- **Hide Unmapped Keys:** Hide inputs without bindings
- **Clear Filters:** Reset all filters and view options with one click

---

## Reference

### Application Structure

The application is built around four main tabs:

#### Controls Table Tab
- Displays all your control bindings in an editable, filterable, sortable table
- Column headers can be clicked to sort
- Rows can be edited with the pencil icon button
- Supports two viewing modes (Default/Detailed)

#### Device View Tab
- Shows interactive PDF representations of your controllers
- Populated with your custom action labels
- Updates in real-time when labels change
- Supports export to PNG or PDF

#### Config Tab
- **Connected Devices:** Lists all currently connected input devices
- **Device-to-Joystick Mapping:** Configure which physical device maps to which joystick slot
- **SC Profiles Directory:** Specify location of your Star Citizen profiles folder
- **Merge Default Bindings:** Optionally populate unmapped actions with SC defaults

#### About Tab
- Project information and acknowledgements

### Label Override System

The application uses a three-tier label priority system:

1. **Your Custom Labels** (highest priority)
   - Created when you double-click and edit a label
   - Stored in `label_overrides_custom.json`
   - Persists across sessions

2. **Global Default Labels**
   - Pre-configured short labels for 72 common Star Citizen actions
   - Shipped with the application
   - Examples: "v_attack1" → "Fire", "v_afterburner" → "Afterburner"

3. **Auto-generated Labels** (lowest priority)
   - Generated from the action name if no override exists

### Keyboard Shortcuts

- **Ctrl+C**: Copy selected text
- **Ctrl+V**: Paste (when editing)
- **Escape**: Cancel editing
- **Enter**: Save edit
- **Double-click:** Edit label in Controls Table

### Device Templates

The application includes PDF templates for 20+ devices:
- **VKB:** Gladiator (EVO/SCG variants), Gunfighter (MCG/SCG), Space Sim Module, STECS Throttle, Throttle Quadrants, F16 MFD
- **VPC:** MongoosT-50CM3
- **Thrustmaster:** T.16000M, TWCS Throttle

For devices without templates, you can still use the Controls Table, CSV, PDF, and Word exports.

---

## Tips & Tricks

### Creating a Reference Card for Your Joystick

1. Customize labels for your most important actions with short names
2. Switch to **Default View** (uncheck "Show Detailed")
3. Filter to show only one device (e.g., "Joystick 1")
4. Export to PDF
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

### Managing Multiple Profiles

The application remembers your last loaded profile and automatically opens it on startup:
1. Click **"Import Profile XML"** to switch profiles
2. Your custom labels are **saved globally** and apply to matching actions in any profile

### Backup Your Custom Labels

Your custom labels are stored in `label_overrides_custom.json`:
1. Locate the file in the application directory
2. Copy it to a safe location
3. To restore, copy it back to the app folder

### Example Workflow: Creating a HOTAS Reference Card

1. **Import** your Star Citizen profile
2. **Filter** to show only "Joystick 1"
3. **Edit labels** to create short versions (Next, Prev, Fire, etc.)
4. **Switch to Device View** and select your joystick model
5. **Verify** labels look good on the graphic
6. **Export** the graphic as PNG or PDF
7. **Return to Control Table** and export to PDF
8. **Print** both the graphic and the PDF for reference

---

## Troubleshooting

### Table doesn't show after importing

- Toggle any checkbox (like "Show Detailed") to refresh the view
- This is a known issue that will be fixed in the next update

### Custom labels not appearing in graphics

- Make sure you pressed **Enter** after editing the label
- Switch tabs and back to refresh the graphics

### Can't edit a cell

- Make sure you're double-clicking the "Label" or "Action (Override)" column
- Other columns are read-only

### Export buttons are disabled

- Make sure you've imported a profile first
- Buttons enable after a successful profile load

### Can't detect my input with "Detect Input"

- Try manual selection using the dropdown in the "Change Input Binding" section
- Some specialized devices may not be automatically detectable
- Make sure your device is connected and working in Windows

---

## Support & Community

### Getting Help

For issues, feature requests, or contributions:
- **Join the Discord community** (link in app footer) - Ask questions and get support
- **Report bugs** with steps to reproduce on the GitHub issues page
- **Request device templates** for controllers you own
- **Share your custom label configurations** with the community
- **Suggest improvements** via GitHub discussions

### Developer Documentation

For development setup, building from source, and contributing:
- See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

### Support the Project

SC Profile Editor is a free, open-source project created to help Star Citizen players manage their control profiles. If you find it useful and would like to support the development:

**Donate:**
- 💳 **[PayPal Donation](https://paypal.me/RighteousKill)** - Support via PayPal
- 💰 **[Venmo Donation](https://venmo.com/u/Amr-Abouelleil)** - Support via Venmo

**Contribute:**
- Report bugs with steps to reproduce
- Request features you'd like to see
- Request device templates for controllers you own
- Share configurations and label sets with the community
- Submit code contributions via GitHub

**Join the Community:**
- 💬 **[Discord Community](https://discord.gg/BNzRegKZ7k)** - Support, discussions, and feature requests

Even if you can't donate, your feedback and bug reports are invaluable!

---

**Happy Flying, Citizen!** o7
