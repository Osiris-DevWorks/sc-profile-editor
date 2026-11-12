---
description: Audit the current branch's source changes for matching test coverage in tests/
---

# /test_coverage_check

For every source file modified on the current branch, decide whether it should have a unit test and whether that test exists or was updated. Surface gaps; don't auto-write tests.

## Severities

- **Critical** — non-exempt code (per the table below) with no matching test. Blocks the release.
- **Major** — an existing test covers an old branch of changed logic but does not exercise the new branch.
- **Minor** — exempt code (GUI wiring, input detection, scripts) flagged for manual attention so the user remembers to smoke-test.

## Scoping the diff

```bash
git diff --name-only $(git merge-base HEAD origin/main)...HEAD
```

On a `release/X.Y.Z` integration branch that is the right baseline. On a feature PR, use the release branch instead of `origin/main`.

## Coverage rules

| Area | Coverage requirement |
|---|---|
| `src/parser/`, `src/models/`, `src/registry/`, `src/exporters/xml_exporter.py` | **Required.** New public functions, new classes, changed branching logic need new or updated tests in `tests/`. The XML round-trip is the product; a parser/exporter change without a test is Critical. |
| `src/utils/` pure helpers: `directinput_guid.py`, `input_validator.py`, `label_overrides.py`, `device_splitter.py`, `device_joystick_mapper.py`, `version.py` | **Required** — no Qt or hardware needed, so they are testable. |
| `src/graphics/pdf_template_manager.py` (template matching, `find_template`) | **Required** for matching logic; PDF rendering itself is exempt. |
| `src/utils/input_detector.py`, `src/utils/single_instance.py` | **Exempt.** Needs real hardware / Windows mutex. Manual test with a joystick plugged in. Flag for human attention. |
| `src/gui/*.py` (widgets, signals, MainWindow wiring, dialogs) | **Exempt.** Manual GUI testing only (there is no pytest-qt). Surface for review. |
| `src/exporters/{csv,pdf,word,graphic}_exporter.py` | **Exempt** unless a pure formatting helper was added. Manual export check. |
| `scripts/` | **Exempt**, except `scripts/generate_pdf_template.py::parse_joy_label` which has `tests/test_parse_joy_label.py` and stays covered. |

## Procedure

1. Run the diff. Group the file list by area per the table above.
2. For each non-exempt file, identify the new or changed callable. Check `tests/` for a matching test (`tests/test_<module>.py`, `test_<callable>_<scenario>`).
3. For changed branching logic in existing code, read the existing test to confirm it covers the new branch; don't trust the filename alone.
4. Run `python -m pytest tests/ -q` and report pass/fail with the count.

## Output

```
**Critical** (non-exempt code without tests):
  src/parser/xml_parser.py::ProfileParser._parse_rebind — new activationMode branch, no test

**Major** (stale tests — changed branches not exercised):
  src/utils/directinput_guid.py::parse_sc_product_guid — test covers PIDVID form only; new XInput path uncovered

**Minor** (exempt — flagged for manual attention):
  src/gui/remap_dialog.py — activation-mode dropdown changed, manual exercise needed

python -m pytest tests/: PASS (41 passed)  |  FAIL — see output above
```

End with a one-line **verdict**: **Clean** (no Critical/Major, pytest passes), **Minor issues** (only Minor; pytest passes), or **Needs attention** (any Critical/Major or pytest failures).

After the verdict, **CHECKPOINT — pause and ask whether to draft tests for the Critical findings, or move on.** Wait for the answer before doing anything else.
