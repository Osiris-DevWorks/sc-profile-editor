# Release Process

**Version:** 0.7.5
**Date:** 2026-01-06
**For:** Release managers - Creating and publishing new versions

This document outlines the standard process for creating a new release of SC Profile Editor. This process was used successfully for v0.7.5 release.

## Pre-Release Checklist

- [ ] All features for the release are complete and merged
- [ ] Tests pass (if applicable)
- [ ] Documentation is updated (README.md, docs/DEVELOPMENT.md)
- [ ] docs/CHANGELOG.md has entries for all changes

## Release Steps

### 1. Prepare Release Branch

If working on a feature branch:
```bash
# Ensure branch is up to date
git checkout <feature-branch>
git pull origin <feature-branch>
```

### 2. Update Version Files

Update the following files with the new version number:

- `VERSION.TXT` - Update to new version (e.g., `0.2.0`)
- `docs/CHANGELOG.md` - Move unreleased items to new version section with date
- `installer.iss` - Update `#define MyAppVersion "X.Y.Z"`

### 3. Clean Up Repository

- Remove temporary/scratch files and directories
- Update `.gitignore` if needed
- Stage documentation and utility files for commit

### 4. Build the Executable

```bash
.venv\Scripts\python.exe scripts/build/build_exe.py
```

Verify the build:
```bash
# Check that dist/SCProfileViewer.exe exists
dir dist\SCProfileViewer.exe
```

### 5. Create Release Commit

On the feature branch, commit all version updates:
```bash
git add VERSION.TXT docs/CHANGELOG.md installer.iss [other-files]
git commit -m "Release vX.Y.Z - <Brief Description>"
```

### 6. Merge to Main

**Option A: Pull Request (Recommended)**
```bash
git push origin <feature-branch>
# Create PR on GitHub to merge into main
# After PR is approved and merged, proceed to step 7
```

**Option B: Direct Merge**
```bash
git checkout main
git merge <feature-branch>
git push origin main
```

### 7. Create Version Commit on Main

After merging, ensure version files are correct on main:
```bash
git checkout main
git pull origin main

# Verify VERSION.TXT, docs/CHANGELOG.md, installer.iss are at correct version
# If not, update them and commit:
git add VERSION.TXT docs/CHANGELOG.md installer.iss
git commit -m "Update version to X.Y.Z"
git push origin main
```

### 8. Create Git Tag

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z - <Brief Description>"
git push origin vX.Y.Z
```

### 9. Build Installer

```bash
cmd /c build_all.bat
```

This creates: `installer_output/SCProfileEditor-vX.Y.Z-Setup.exe`

**⚠️ IMPORTANT:** The installer is a required release artifact and must be built and included in all releases.

### 10. Create GitHub Release

**⚠️ IMPORTANT:** You must COMPLETE this step (including publishing the release) BEFORE running the Discord notification in step 11. The Discord notification includes a link to the release, which must exist for users.

1. **Go to GitHub Release Page:**
   ```
   https://github.com/Osiris-RK/sc-profile-editor/releases/new?tag=vX.Y.Z
   ```

2. **Fill in Release Information:**
   - **Tag:** vX.Y.Z (should be auto-selected)
   - **Release Title:** `SC Profile Editor vX.Y.Z - <Brief Description>`
   - **Description:** Use the docs/CHANGELOG.md content for this version (see template below)

3. **Attach Build Artifacts:**
   - Upload `installer_output/SCProfileEditor-vX.Y.Z-Setup.exe`
   - Upload `dist/SCProfileEditor.exe` (optional, as standalone)

4. **Publish Release**
      - Look at previous release notes to make sure you're including sections included before
      - Before officially publishing the release, review the release notes with the user. 
      - Ask the user what the testing focus should be for the release.
      - Publish the release when user gives approval

5. **Verify Release is Live:**
   - Visit the release URL to confirm it's accessible
   - Verify download links work
   - Only proceed to step 11 after confirmation

### 11. Post Release to Discord

**⚠️ PREREQUISITE:** The GitHub release from step 10 MUST be published and live before running this step.

**Prerequisites:**
- Set up Discord webhook URL in `.env` file (copy from `.env.example`)
- Create webhook: Discord Server → Server Settings → Integrations → Webhooks → New Webhook

**Post the release:**
```bash
.venv\Scripts\python.exe scripts/discord_notify.py vX.Y.Z https://github.com/Osiris-RK/sc-profile-editor/releases/tag/vX.Y.Z
```

Example:
```bash
.venv\Scripts\python.exe scripts/discord_notify.py v0.4.0 https://github.com/Osiris-RK/sc-profile-editor/releases/tag/v0.4.0
```

The script will:
- Parse docs/CHANGELOG.md for the version's changes
- Create a formatted Discord embed with release info
- Post to the configured Discord channel
- Skip gracefully if webhook URL is not configured

## GitHub Release Notes Template

```markdown
# SC Profile Editor vX.Y.Z - <Brief Description>

[1-2 sentence summary of the release]

## 🆕 What's New

### Added
- Feature 1
- Feature 2

### Changed
- Change 1
- Change 2

### Fixed
- Fix 1
- Fix 2

## 📥 Downloads

- **Installer:** [SCProfileEditor-vX.Y.Z-Setup.exe](link) - Recommended for most users
- **Standalone:** [SCProfileEditor.exe](link) - Portable version (no installation required)

## 📋 System Requirements

- Windows 10 or later (64-bit)
- No additional dependencies required

## 🎮 Devices Supported

[List all supported device types and specific models]

**Examples:**
- VKB Gladiator (EVO, SCG variants)
- VKB Gunfighter (MCG, SCG variants)
- VKB Space Sim Module (SEM)
- VPC MongoosT-50CM3
- Thrustmaster TWCS Throttle
- Keyboard, Mouse, Joystick

## 🐛 Known Issues

[List any known issues, limitations, or workarounds]

## 🧪 Testing Focus

[Areas the community should focus testing on for this release]

## 📝 Full Changelog

See [CHANGELOG.md](https://github.com/Osiris-RK/sc-profile-editor/blob/main/docs/CHANGELOG.md) for complete version history.

---

**First time using SC Profile Editor?** Check out the [User Guide](https://github.com/Osiris-RK/sc-profile-editor/blob/main/README.md) to get started!

**Need help?** Join our [Discord community](https://discord.gg/BNzRegKZ7k) for support and discussions.

**Support this project:** [PayPal](https://paypal.me/RighteousKill) | [Venmo](https://venmo.com/u/Amr-Abouelleil)
```

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0) - Incompatible API changes or major feature overhauls
- **MINOR** (0.X.0) - New functionality in a backward-compatible manner
- **PATCH** (0.0.X) - Backward-compatible bug fixes

## Post-Release

- [ ] Verify GitHub release is published
- [ ] Test installer download and installation
- [ ] **Post to Discord** (see step 11 - this is REQUIRED, not optional):
  ```bash
  .venv\Scripts\python.exe scripts/discord_notify.py vX.Y.Z https://github.com/Osiris-RK/sc-profile-editor/releases/tag/vX.Y.Z
  ```
- [ ] Create new development branch for next version (if needed)
- [ ] Update docs/CHANGELOG.md with new `[Unreleased]` section

## Troubleshooting

### Tag Already Exists
```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push --delete origin vX.Y.Z

# Recreate tag
git tag -a vX.Y.Z -m "Release vX.Y.Z - <Description>"
git push origin vX.Y.Z
```

### Version Mismatch
If version files don't match after merge, update them on main and create a new commit before tagging.

### Build Fails
Check `build\SCProfileViewer\warn-SCProfileViewer.txt` for warnings and errors.
