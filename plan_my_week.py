#!/usr/bin/env python3
# ============================================================
# plan_my_week.py
#
# The friendly front door to the Priority Planner engine.
#
# What this script does, in plain English:
#   1. Asks you to paste your week (multi-line text dump).
#   2. Reads everything you paste until you press Ctrl+D
#      (Mac/Linux) or Ctrl+Z + Enter (Windows).
#   3. Parses what you typed into events.
#   4. Detects scheduling problems (overlaps + buffer violations).
#   5. Prints your full Monday-through-Sunday timesheet to the screen.
#   6. Saves the same timesheet to a .txt file inside the
#      'outputs/' folder (creates the folder if needed).
#
# How to run it:
#     python3 plan_my_week.py
#
# This wrapper does no fancy logic of its own. It just connects
# the parsers, the engine, and the formatter so you don't have
# to write Python to use them.
# ============================================================

import os
import sys

from src.parsers.dump_parser import parse_dump
from src.engine.conflict_checker import find_all_issues
from src.engine.timesheet_formatter import render_timesheet
from src.engine.timesheet_exporter import export_timesheet


# The folder where saved timesheets go.
# We use a sub-folder (not the project root) so saved files don't
# get mixed up with source code.
OUTPUT_DIRECTORY = "outputs"


def print_banner(text):
    """
    Print a visible banner around a short message.
    Used to break up sections so the output is easy to scan.
    """
    line = "=" * 50
    print()
    print(line)
    print(text)
    print(line)


def collect_user_dump():
    """
    Read multi-line input from the user until they signal end-of-input.

    Returns the full input as a single string.

    How it ends:
      - On Mac/Linux: the user presses Ctrl+D on an empty line
      - On Windows:   the user presses Ctrl+Z then Enter
      Either way, sys.stdin.read() returns at that point.

    Why sys.stdin.read() instead of input() in a loop?
      input() reads one line at a time and requires us to write
      our own "is this the end?" logic. sys.stdin.read() handles
      EOF naturally and matches how every Unix utility works.
    """
    print("Paste your week below.")
    print("When you're done, press:")
    print("  - Ctrl+D  (Mac/Linux)")
    print("  - Ctrl+Z then Enter  (Windows)")
    print()
    print("Format reminder:  Title | Day | StartTime-EndTime | [optional tags]")
    print("Example:          Therapy | Monday | 4:00PM-5:00PM | [signal]")
    print()
    print("--- paste below this line ---")

    # Read everything until EOF.
    # This blocks until the user signals end-of-input.
    raw_input = sys.stdin.read()

    return raw_input


def report_failures(failures):
    """
    Print any parse failures clearly so the user knows what got dropped.

    Each failure includes the line number from the original input
    so the user can find and fix it.
    """
    if not failures:
        return

    print_banner(f"PARSE WARNINGS ({len(failures)} line(s) could not be read)")
    for failure in failures:
        # line_content is already truncated by the parser if it was huge,
        # so we can safely print it.
        print(f"  Line {failure.line_number}: {failure.reason}")
        print(f"    > {failure.line_content!r}")
    print()
    print("(Other lines were parsed normally. See timesheet below.)")


def ensure_output_directory():
    """
    Make sure the outputs/ folder exists.

    Creates it if it's missing. This is the ONE place we create
    a directory automatically -- the export function itself
    deliberately refuses to create directories (per its security
    design), so we handle it here at the user-facing layer where
    we know it's safe.
    """
    if not os.path.exists(OUTPUT_DIRECTORY):
        os.makedirs(OUTPUT_DIRECTORY)


def save_timesheet(rendered):
    """
    Save the rendered timesheet to a date-stamped file.

    Handles the case where today's file already exists by appending
    a suffix (-2, -3, etc.) so we never overwrite an earlier export.

    Returns the path of the file that was actually written.

    Why we add a suffix instead of just calling export_timesheet
    once: export_timesheet refuses to overwrite for safety, raising
    FileExistsError. Here in the user-facing wrapper, we WANT to
    save multiple exports per day (you might tweak your dump and
    re-run). So we try one, and if it collides, we try suffixed
    variants.
    """
    from datetime import date
    from src.engine.timesheet_exporter import (
        _build_filename, FILENAME_PREFIX, FILENAME_EXTENSION
    )

    today = date.today()

    # First attempt: standard date-stamped filename.
    try:
        return export_timesheet(rendered, directory=OUTPUT_DIRECTORY,
                                today=today)
    except FileExistsError:
        pass

    # If today's file already exists, try suffixed variants.
    # We cap at 99 attempts -- if someone re-runs 100 times in one
    # day, something is wrong and we should stop.
    base_name = _build_filename(today)
    base_without_ext = base_name[:-len(FILENAME_EXTENSION)]

    for suffix_num in range(2, 100):
        candidate_filename = f"{base_without_ext}-{suffix_num}{FILENAME_EXTENSION}"
        candidate_path = os.path.join(OUTPUT_DIRECTORY, candidate_filename)
        if not os.path.exists(candidate_path):
            # Write directly here (bypassing the date-based filename).
            # The exporter is built around date-stamped filenames; for
            # the suffix case we write the file ourselves using the
            # same safety patterns (exclusive create mode "x").
            with open(candidate_path, "x", encoding="utf-8") as f:
                f.write(rendered)
            return os.path.realpath(candidate_path)

    # 99 attempts is plenty; if we get here something is off.
    raise RuntimeError(
        "Could not save timesheet: too many existing files for today. "
        "Clean up old files in the outputs/ folder."
    )


def main():
    """
    Run the full pipeline:
      1. Collect input
      2. Parse
      3. Detect issues
      4. Render
      5. Print to screen
      6. Save to file

    Returns 0 on success, 1 on any controlled failure (caught error
    with a clear message), 2 on unexpected crashes.
    """

    # ---- STEP 1: COLLECT INPUT ----
    print_banner("PRIORITY PLANNER -- Plan My Week")

    try:
        raw_input = collect_user_dump()
    except KeyboardInterrupt:
        # User hit Ctrl+C to abort. Exit cleanly, don't show a stack trace.
        print("\n\nCancelled.")
        return 1

    # If the user just pressed Ctrl+D without typing anything, we still
    # have an empty string. Treat that gracefully.
    if not raw_input.strip():
        print("\nNo input received. Exiting.")
        return 0

    # ---- STEP 2: PARSE ----
    parse_result = parse_dump(raw_input)

    # Handle global rejection (input too large, wrong type, etc.).
    # In normal terminal use this shouldn't happen, but we handle it
    # for completeness.
    if parse_result.global_error:
        print()
        print(f"ERROR: {parse_result.global_error}")
        return 1

    # Show any per-line warnings BEFORE the timesheet, so users
    # see them while their attention is fresh.
    report_failures(parse_result.failures)

    # If literally nothing parsed, there's no timesheet to render.
    # Give a helpful message instead of an empty week.
    if not parse_result.events:
        print()
        print("No events were parsed. Check your input format:")
        print("  Title | Day | StartTime-EndTime | [optional tags]")
        return 1

    # ---- STEP 3: DETECT ISSUES ----
    issues = find_all_issues(parse_result.events)

    # ---- STEP 4: RENDER ----
    rendered = render_timesheet(parse_result.events, issues)

    # ---- STEP 5: PRINT TO SCREEN ----
    print_banner("YOUR WEEK")
    print()
    print(rendered)
    print()

    # ---- STEP 6: SAVE TO FILE ----
    ensure_output_directory()

    try:
        saved_path = save_timesheet(rendered)
        print_banner("SAVED")
        print(f"Your timesheet was saved to:")
        print(f"  {saved_path}")
        print()
    except (OSError, RuntimeError) as e:
        # File-writing errors that are recoverable: report and exit
        # with status 1. The user already saw the timesheet on screen,
        # so they haven't lost anything.
        print(f"Could not save timesheet: {e}")
        return 1

    # ---- SUMMARY LINE ----
    issue_count = len(issues)
    event_count = len(parse_result.events)
    failure_count = len(parse_result.failures)
    print(f"Summary: {event_count} event(s), "
          f"{issue_count} issue(s), "
          f"{failure_count} line(s) skipped.")

    return 0


# This is the standard "only run main() when this file is executed
# directly" guard. If someone imports plan_my_week from another file,
# main() does not run automatically.
if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
