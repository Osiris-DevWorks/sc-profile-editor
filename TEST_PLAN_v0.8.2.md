# v0.8.2 Test Plan

## Setup
- **Devices**: Thrustmaster T16000 + Throttle
- **Branch**: develop-v0.8.2
- **Testing Environment**: Fresh start of application

---

## Test 1: Device Detection in New Profile
**Goal**: Verify that connected joystick devices are automatically detected and shown in the Controls tab when creating a new profile.

**Steps**:
1. Install and start the application
2. Click "Create New Profile"
3. Go to **Controls** tab
4. **Expected Result**:
   - Device count should show "4 devices" (Keyboard, Mouse, T16000, Throttle)
   - Device list in profile summary should include your joysticks by name
   - Device filter dropdown should show: "All Devices", "Keyboard", "Mouse", and both joystick names

**Success Criteria**:
- ✅ Both joysticks appear in device count
- ✅ Device filter dropdown is populated with your devices
- ✅ Device View tab shows your joysticks as available options

---

## Test 2: Device Mapping Configuration
**Goal**: Verify that device-to-joystick mappings from the Config tab are applied to new profiles.

**Steps**:
1. Go to **Config** tab
2. Click "Auto-Populate from Connected Devices"
3. **Check that the layout is readable**:
   - Labels (js1:, js2:) should be clearly visible
   - Dropdowns should show your device names
   - Buttons should be at comfortable size and spacing
4. Click "Save Configuration"
5. Go back to **Controls** tab
6. Check the device filter dropdown
7. **Expected Result**:
   - Both devices should still be visible and properly mapped
   - Device count unchanged
   - Device names in filter dropdown match your mapped devices

**Success Criteria**:
- ✅ UI layout is not cropped or hard to read
- ✅ Device mapping is saved
- ✅ New profiles respect the mapping

---

## Test 3: Device Filtering
**Goal**: Verify that device filter doesn't crash or empty the action table.

**Steps**:
1. In **Controls** tab, look at the device filter dropdown
2. Select "T16000" (or first device name)
3. **Expected Result**:
   - Action table should show only actions for that device
   - Table should NOT be completely empty
   - Status bar shows filtered count (e.g., "Showing X of Y bindings")
4. Select "All Devices"
5. **Expected Result**:
   - All actions return to view

**Success Criteria**:
- ✅ Device filter works without emptying the table
- ✅ Can filter to specific devices
- ✅ Can return to "All Devices" view

---

## Test 4: Device View Tab
**Goal**: Verify that Device View shows your joystick templates.

**Steps**:
1. Go to **Device View** tab
2. Click "Select device" dropdown
3. **Expected Result**:
   - Dropdown should list:
     - Your T16000 (with connection status, e.g., "[CONNECTED]")
     - Your Throttle (with connection status)
   - At least one template should be available for selection
4. Select your T16000
5. **Expected Result**:
   - Device PDF graphic should display
   - Shows which buttons/controls you can map

**Success Criteria**:
- ✅ Device dropdown shows your joysticks
- ✅ PDF templates display correctly
- ✅ No "No devices available" message

---

## Test 5: Button Detection
**Goal**: Verify that joystick buttons are correctly detected when binding inputs.

**Important**: This test requires careful attention to logging. These changes help diagnose the issue but don't fully fix it yet.

**Steps**:
1. In **Controls** tab, select an unmapped action
2. Click the "Edit" button (pencil icon)
3. In RemapDialog, click "Detect Input"
4. Press **different buttons** on your T16000 (try buttons 1, 3, 5, 10)
5. **Check the app's log file** (look in working directory or check console output):
   - Should see messages like: "JOYBUTTONDOWN event: joy=X, button=Y"
   - Button numbers should vary for different presses
   - Should see: "Button detected: jsX_buttonY"

**Expected Results**:
- When you press button 1 → should detect "button1" (not always "button1")
- When you press button 3 → should detect "button3"
- When you press button 5 → should detect "button5"

**Troubleshooting if all buttons show as "button1"**:
- Check the log messages for: "JOYBUTTONDOWN event: joy=X, button=0" (always 0)
- This would indicate a pygame event handling issue
- The comprehensive logging we added will help diagnose this

**Success Criteria** (currently diagnostic):
- ✅ Different button presses produce different button numbers
- ✅ Logging shows varied button values
- ⚠️ If still showing all as button 1, logs will help identify the issue

---

## Test 6: Duplicate Actions Check
**Goal**: Verify that saving and loading profiles doesn't create duplicate actions.

**Steps**:
1. Create a new profile (or load existing)
2. Edit a few bindings to different buttons
3. Click "Save Profile"
4. Reload the saved profile
5. **Expected Result**:
   - No duplicate actions in the XML
   - Each action appears only once
   - All your bindings are preserved

**Success Criteria**:
- ✅ No duplicate actions in saved XML files
- ✅ Bindings preserved after save/reload
- ✅ Profile loads cleanly without errors

---

## Test 7: End-to-End Workflow
**Goal**: Complete workflow with all fixes working together.

**Steps**:
1. Start fresh application
2. Create new profile
3. Verify devices are detected (Test 1)
4. Go to Device View, select T16000 (Test 4)
5. Go to Controls, filter by one device (Test 3)
6. Edit a binding:
   - Click Edit button
   - Detect input (Test 5)
   - Assign to a button
   - Click OK
7. Save profile
8. Reload profile
9. Verify binding still exists (Test 6)

**Success Criteria**:
- ✅ All steps complete without errors
- ✅ Devices properly detected and displayed
- ✅ Bindings saved and loaded correctly
- ✅ UI remains responsive throughout

---

## Reporting Results

Please run through each test and note:
1. ✅ = Test passed
2. ❌ = Test failed (note what went wrong)
3. ⚠️ = Partial/Inconclusive (note details)

For Test 5 (Button Detection), please save your log output if buttons are still showing as button 1 - this will help diagnose the issue further.

---

## Log Location
The application logs to the console and to a log file (if configured). Check:
- Console output during test execution
- Look for messages starting with "JOYBUTTONDOWN event:"
- Look for "Button detected:" messages

These logs will help diagnose the button detection issue if needed.
