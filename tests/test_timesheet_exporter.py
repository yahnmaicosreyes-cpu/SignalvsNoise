# ============================================================
# test_timesheet_exporter.py
#
# Tests for src/engine/timesheet_exporter.py.
#
# Test groups:
#   1. Happy path -- file gets written with correct content
#   2. Filename generation -- date-stamped format
#   3. Overwrite refusal -- existing files are protected
#   4. Directory validation -- bad directories rejected
#   5. Type safety -- bad input types rejected
#   6. Round-trip -- writing then reading produces identical content
#
# Tests use tempfile.TemporaryDirectory() throughout so no test
# litters the filesystem. The directory is cleaned up automatically.
# ============================================================

import os
import tempfile
from datetime import date

from src.engine.timesheet_exporter import (
    export_timesheet,
    _build_filename,
    FILENAME_PREFIX,
    FILENAME_EXTENSION,
)


# =================================================================
# GROUP 1: HAPPY PATH
# =================================================================

def run_happy_path():
    print("=== HAPPY PATH ===")
    passed = 0
    total = 0

    # ---- File gets written and exists on disk ----
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        path = export_timesheet("hello world", directory=tmp,
                                today=date(2026, 5, 25))
        if os.path.exists(path):
            passed += 1
            print(f"Test {total}: PASS | File written and exists at {os.path.basename(path)}")
        else:
            print(f"Test {total}: FAIL | file does not exist")

    # ---- Returned path is absolute ----
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        path = export_timesheet("hello", directory=tmp,
                                today=date(2026, 1, 1))
        if os.path.isabs(path):
            passed += 1
            print(f"Test {total}: PASS | Returned path is absolute")
        else:
            print(f"Test {total}: FAIL | returned path: {path}")

    # ---- File contents match input exactly ----
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        content = "Weekly Timesheet\n\nMONDAY\n  09:00 - 10:00   Yoga"
        path = export_timesheet(content, directory=tmp,
                                today=date(2026, 5, 25))
        with open(path, encoding="utf-8") as f:
            read_back = f.read()
        if read_back == content:
            passed += 1
            print(f"Test {total}: PASS | File contents match input exactly")
        else:
            print(f"Test {total}: FAIL | content mismatch")

    # ---- Empty string can be exported (edge case but valid) ----
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        path = export_timesheet("", directory=tmp,
                                today=date(2026, 5, 25))
        with open(path, encoding="utf-8") as f:
            read_back = f.read()
        if read_back == "":
            passed += 1
            print(f"Test {total}: PASS | Empty string exported as empty file")
        else:
            print(f"Test {total}: FAIL")

    # ---- Default directory is current working directory ----
    # We can verify this by changing into a temp dir, calling export
    # with no directory arg, and confirming the file landed there.
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp)
            path = export_timesheet("test", today=date(2026, 5, 25))
            # The written file should be in tmp (now the cwd).
            if os.path.dirname(os.path.realpath(path)) == os.path.realpath(tmp):
                passed += 1
                print(f"Test {total}: PASS | Default directory is cwd")
            else:
                print(f"Test {total}: FAIL | wrote to {path} but cwd is {tmp}")
        finally:
            os.chdir(original_cwd)

    print(f"{passed}/{total} happy path tests passed\n")
    return passed, total


# =================================================================
# GROUP 2: FILENAME GENERATION
# =================================================================

def run_filename_generation():
    print("=== FILENAME GENERATION ===")
    passed = 0
    total = 0

    # ---- Filename uses the right prefix and extension ----
    total += 1
    name = _build_filename(today=date(2026, 5, 25))
    if name.startswith(FILENAME_PREFIX) and name.endswith(FILENAME_EXTENSION):
        passed += 1
        print(f"Test {total}: PASS | Filename '{name}' uses prefix and extension")
    else:
        print(f"Test {total}: FAIL | got '{name}'")

    # ---- Filename uses ISO date format ----
    total += 1
    name = _build_filename(today=date(2026, 5, 25))
    if "2026-05-25" in name:
        passed += 1
        print(f"Test {total}: PASS | Filename includes ISO date '2026-05-25'")
    else:
        print(f"Test {total}: FAIL | got '{name}'")

    # ---- Different dates produce different filenames ----
    total += 1
    name1 = _build_filename(today=date(2026, 5, 25))
    name2 = _build_filename(today=date(2026, 5, 26))
    if name1 != name2:
        passed += 1
        print(f"Test {total}: PASS | Different dates -> different filenames")
    else:
        print(f"Test {total}: FAIL")

    # ---- Default (no date arg) uses today's actual date ----
    total += 1
    name_default = _build_filename()
    name_today = _build_filename(today=date.today())
    if name_default == name_today:
        passed += 1
        print(f"Test {total}: PASS | Default uses today's date")
    else:
        print(f"Test {total}: FAIL | default={name_default}, today={name_today}")

    print(f"{passed}/{total} filename generation tests passed\n")
    return passed, total


# =================================================================
# GROUP 3: OVERWRITE REFUSAL (security: prevent data loss)
# =================================================================

def run_overwrite_refusal():
    print("=== OVERWRITE REFUSAL ===")
    passed = 0
    total = 0

    # ---- Exporting twice on the same date raises FileExistsError ----
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        export_timesheet("first", directory=tmp, today=date(2026, 5, 25))
        try:
            export_timesheet("second", directory=tmp, today=date(2026, 5, 25))
            print(f"Test {total}: FAIL | expected FileExistsError")
        except FileExistsError:
            passed += 1
            print(f"Test {total}: PASS | Second export refused with FileExistsError")

    # ---- After refusal, original file content is UNCHANGED ----
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        path = export_timesheet("original content",
                                directory=tmp, today=date(2026, 5, 25))
        try:
            export_timesheet("would-be replacement",
                             directory=tmp, today=date(2026, 5, 25))
        except FileExistsError:
            pass
        with open(path) as f:
            read_back = f.read()
        if read_back == "original content":
            passed += 1
            print(f"Test {total}: PASS | Original file content survived refused overwrite")
        else:
            print(f"Test {total}: FAIL | content was: {read_back!r}")

    # ---- Different dates -> two separate files coexist ----
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        path1 = export_timesheet("monday version",
                                 directory=tmp, today=date(2026, 5, 25))
        path2 = export_timesheet("tuesday version",
                                 directory=tmp, today=date(2026, 5, 26))
        if (os.path.exists(path1) and os.path.exists(path2)
            and path1 != path2):
            passed += 1
            print(f"Test {total}: PASS | Different dates -> separate files, both exist")
        else:
            print(f"Test {total}: FAIL")

    print(f"{passed}/{total} overwrite refusal tests passed\n")
    return passed, total


# =================================================================
# GROUP 4: DIRECTORY VALIDATION
# =================================================================

def run_directory_validation():
    print("=== DIRECTORY VALIDATION ===")
    passed = 0
    total = 0

    # ---- Nonexistent directory rejected ----
    total += 1
    try:
        export_timesheet("test",
                         directory="/this/path/does/not/exist/xyzzy",
                         today=date(2026, 5, 25))
        print(f"Test {total}: FAIL | expected ValueError")
    except ValueError as e:
        if "does not exist" in str(e).lower():
            passed += 1
            print(f"Test {total}: PASS | Nonexistent directory rejected with clear message")
        else:
            print(f"Test {total}: FAIL | wrong message: {e}")

    # ---- Path that's a file, not a directory, rejected ----
    total += 1
    with tempfile.NamedTemporaryFile(suffix=".txt") as f:
        try:
            export_timesheet("test", directory=f.name,
                             today=date(2026, 5, 25))
            print(f"Test {total}: FAIL | expected ValueError")
        except ValueError as e:
            if "not a directory" in str(e).lower():
                passed += 1
                print(f"Test {total}: PASS | File-as-directory rejected with clear message")
            else:
                print(f"Test {total}: FAIL | wrong message: {e}")

    print(f"{passed}/{total} directory validation tests passed\n")
    return passed, total


# =================================================================
# GROUP 5: TYPE SAFETY
# =================================================================

def run_type_safety():
    print("=== TYPE SAFETY ===")
    passed = 0
    total = 0

    with tempfile.TemporaryDirectory() as tmp:

        # ---- Content as None ----
        total += 1
        try:
            export_timesheet(None, directory=tmp, today=date(2026, 5, 25))
            print(f"Test {total}: FAIL")
        except TypeError:
            passed += 1
            print(f"Test {total}: PASS | None content rejected")

        # ---- Content as integer ----
        total += 1
        try:
            export_timesheet(12345, directory=tmp, today=date(2026, 5, 25))
            print(f"Test {total}: FAIL")
        except TypeError:
            passed += 1
            print(f"Test {total}: PASS | Integer content rejected")

        # ---- Content as list ----
        total += 1
        try:
            export_timesheet(["line1", "line2"],
                             directory=tmp, today=date(2026, 5, 25))
            print(f"Test {total}: FAIL")
        except TypeError:
            passed += 1
            print(f"Test {total}: PASS | List content rejected")

        # ---- Content as bytes ----
        total += 1
        try:
            export_timesheet(b"bytes are not strings",
                             directory=tmp, today=date(2026, 5, 25))
            print(f"Test {total}: FAIL")
        except TypeError:
            passed += 1
            print(f"Test {total}: PASS | Bytes content rejected")

        # ---- Directory as None ----
        total += 1
        try:
            export_timesheet("content", directory=None,
                             today=date(2026, 5, 25))
            print(f"Test {total}: FAIL")
        except TypeError:
            passed += 1
            print(f"Test {total}: PASS | None directory rejected")

        # ---- Directory as integer ----
        total += 1
        try:
            export_timesheet("content", directory=42,
                             today=date(2026, 5, 25))
            print(f"Test {total}: FAIL")
        except TypeError:
            passed += 1
            print(f"Test {total}: PASS | Integer directory rejected")

    print(f"{passed}/{total} type safety tests passed\n")
    return passed, total


# =================================================================
# GROUP 6: ROUND-TRIP WITH FULL PIPELINE
# =================================================================

def run_round_trip():
    """End-to-end: parse text -> find issues -> render -> export -> read back."""
    print("=== ROUND-TRIP (full pipeline through export) ===")
    passed = 0
    total = 0

    from src.parsers.dump_parser import parse_dump
    from src.engine.conflict_checker import find_all_issues
    from src.engine.timesheet_formatter import render_timesheet

    text = (
        "Therapy | Monday | 4:00PM-5:00PM | [signal]\n"
        "Commute | Monday | 5:00PM-5:30PM | [urgent]"
    )

    parsed = parse_dump(text)
    issues = find_all_issues(parsed.events)
    rendered = render_timesheet(parsed.events, issues)

    # ---- The rendered timesheet exports successfully ----
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        path = export_timesheet(rendered, directory=tmp,
                                today=date(2026, 5, 25))
        if os.path.exists(path):
            passed += 1
            print(f"Test {total}: PASS | Full-pipeline timesheet exported successfully")
        else:
            print(f"Test {total}: FAIL")

    # ---- Exported file content matches the rendered string exactly ----
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        path = export_timesheet(rendered, directory=tmp,
                                today=date(2026, 5, 25))
        with open(path, encoding="utf-8") as f:
            read_back = f.read()
        if read_back == rendered:
            passed += 1
            print(f"Test {total}: PASS | Round-trip preserves rendered content exactly")
        else:
            print(f"Test {total}: FAIL")

    # ---- Banner lines made it through unchanged ----
    total += 1
    with tempfile.TemporaryDirectory() as tmp:
        path = export_timesheet(rendered, directory=tmp,
                                today=date(2026, 5, 25))
        with open(path, encoding="utf-8") as f:
            read_back = f.read()
        if "MONDAY" in read_back and "=" * 40 in read_back:
            passed += 1
            print(f"Test {total}: PASS | MONDAY banner present in exported file")
        else:
            print(f"Test {total}: FAIL")

    print(f"{passed}/{total} round-trip tests passed\n")
    return passed, total


# =================================================================
# Main runner
# =================================================================

def run():
    """Run all timesheet exporter tests."""
    p1, t1 = run_happy_path()
    p2, t2 = run_filename_generation()
    p3, t3 = run_overwrite_refusal()
    p4, t4 = run_directory_validation()
    p5, t5 = run_type_safety()
    p6, t6 = run_round_trip()
    return (
        p1 + p2 + p3 + p4 + p5 + p6,
        t1 + t2 + t3 + t4 + t5 + t6,
    )


if __name__ == "__main__":
    run()
