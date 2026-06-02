# ============================================================
# test_timesheet_formatter.py
#
# Tests for src/engine/timesheet_formatter.py.
#
# Test groups:
#   1. Structure -- the seven-day banner shape is always present
#   2. Empty days -- "Open Availability" rendering
#   3. Event rendering -- titles, times, quadrants
#   4. Issue rendering -- sub-lines, phrasing for both events
#   5. Title column alignment -- adaptive width
#   6. Edge cases -- empty input, all-empty week, long titles
#   7. Type safety -- bad input gets rejected
# ============================================================

from src.models.event import Event
from src.models.issue import Issue, IssueType
from src.engine.conflict_checker import find_all_issues
from src.engine.timesheet_formatter import (
    render_timesheet,
    BANNER_WIDTH,
    DAY_NAMES,
)


def _make(title, day, start, end, important=None, urgent=None, hard=None, soft=None):
    """Helper to keep test events concise."""
    return Event(
        title=title, day=day, start=start, end=end,
        important=important, urgent=urgent,
        hard_buffer_minutes=hard, soft_buffer_minutes=soft,
    )


# =================================================================
# GROUP 1: STRUCTURE -- the seven-day shape is always present
# =================================================================

def run_structure():
    print("=== STRUCTURE TESTS ===")
    passed = 0
    total = 0

    # ---- Title appears at the top ----
    total += 1
    output = render_timesheet([], [])
    if output.startswith("Weekly Timesheet"):
        passed += 1
        print(f"Test {total}: PASS | Output starts with 'Weekly Timesheet'")
    else:
        print(f"Test {total}: FAIL | output starts with: {output[:30]!r}")

    # ---- All seven day names appear, in order ----
    total += 1
    output = render_timesheet([], [])
    positions = [output.find(name) for name in DAY_NAMES]
    # Each position must be > -1 (found) and in ascending order
    if all(p > -1 for p in positions) and positions == sorted(positions):
        passed += 1
        print(f"Test {total}: PASS | All 7 days appear in Mon->Sun order")
    else:
        print(f"Test {total}: FAIL | day positions: {positions}")

    # ---- Banners are BANNER_WIDTH equals signs ----
    total += 1
    output = render_timesheet([], [])
    banner_line = "=" * BANNER_WIDTH
    if output.count(banner_line) >= 14:  # 2 per day x 7 days
        passed += 1
        print(f"Test {total}: PASS | Banner line ({BANNER_WIDTH} '=' chars) appears at least 14 times")
    else:
        print(f"Test {total}: FAIL | only {output.count(banner_line)} banners found")

    print(f"{passed}/{total} structure tests passed\n")
    return passed, total


# =================================================================
# GROUP 2: EMPTY DAYS -- "Open Availability"
# =================================================================

def run_empty_days():
    print("=== EMPTY-DAY TESTS ===")
    passed = 0
    total = 0

    # ---- Fully empty week shows "Open Availability" 7 times ----
    total += 1
    output = render_timesheet([], [])
    if output.count("Open Availability") == 7:
        passed += 1
        print(f"Test {total}: PASS | Empty week shows 'Open Availability' 7 times")
    else:
        print(f"Test {total}: FAIL | got {output.count('Open Availability')} occurrences")

    # ---- One event on Monday means 6 'Open Availability' lines ----
    total += 1
    events = [_make("Solo", 0, 900, 1000)]
    output = render_timesheet(events, [])
    if output.count("Open Availability") == 6:
        passed += 1
        print(f"Test {total}: PASS | One Mon event -> 6 'Open Availability' lines")
    else:
        print(f"Test {total}: FAIL | got {output.count('Open Availability')}")

    # ---- "Open Availability" appears under correct banner ----
    # (Specifically: under WEDNESDAY when only Mon has events)
    total += 1
    events = [_make("Mon thing", 0, 900, 1000)]
    output = render_timesheet(events, [])
    # Find the WEDNESDAY banner section
    wed_index = output.find("WEDNESDAY")
    thu_index = output.find("THURSDAY")
    wed_section = output[wed_index:thu_index]
    if "Open Availability" in wed_section:
        passed += 1
        print(f"Test {total}: PASS | 'Open Availability' appears under WEDNESDAY")
    else:
        print(f"Test {total}: FAIL")

    print(f"{passed}/{total} empty-day tests passed\n")
    return passed, total


# =================================================================
# GROUP 3: EVENT RENDERING -- times, titles, quadrants
# =================================================================

def run_event_rendering():
    print("=== EVENT RENDERING TESTS ===")
    passed = 0
    total = 0

    # ---- Military time format with leading zeros ----
    total += 1
    e = _make("Early", 0, 900, 1030)
    output = render_timesheet([e], [])
    if "09:00 - 10:30" in output:
        passed += 1
        print(f"Test {total}: PASS | 900 -> '09:00' (leading zero)")
    else:
        print(f"Test {total}: FAIL")

    # ---- Midnight renders as 00:00 ----
    total += 1
    e = _make("Midnight start", 0, 0, 100)
    output = render_timesheet([e], [])
    if "00:00 - 01:00" in output:
        passed += 1
        print(f"Test {total}: PASS | Midnight start -> '00:00 - 01:00'")
    else:
        print(f"Test {total}: FAIL")

    # ---- 23:59 renders correctly ----
    total += 1
    e = _make("Late", 5, 2300, 2359)
    output = render_timesheet([e], [])
    if "23:00 - 23:59" in output:
        passed += 1
        print(f"Test {total}: PASS | 2359 -> '23:59'")
    else:
        print(f"Test {total}: FAIL")

    # ---- Event title appears in output ----
    total += 1
    e = _make("Therapy session", 0, 1600, 1700)
    output = render_timesheet([e], [])
    if "Therapy session" in output:
        passed += 1
        print(f"Test {total}: PASS | Title appears in output")
    else:
        print(f"Test {total}: FAIL")

    # ---- Quadrant tag appears for each quadrant ----
    quadrants_to_test = [
        (True, False, "[SIGNAL]"),
        (True, True, "[URGENT]"),
        (False, True, "[INTERRUPTION]"),
        (False, False, "[NOISE]"),
        (None, None, "[UNSPECIFIED]"),
    ]
    for important, urgent, expected_tag in quadrants_to_test:
        total += 1
        e = _make("X", 0, 900, 1000, important=important, urgent=urgent)
        output = render_timesheet([e], [])
        if expected_tag in output:
            passed += 1
            print(f"Test {total}: PASS | Quadrant tag {expected_tag} appears")
        else:
            print(f"Test {total}: FAIL | {expected_tag} missing")

    # ---- Events render in chronological order within a day ----
    total += 1
    # Add in scrambled order; output should be 9am then 1pm then 5pm
    morning = _make("morning", 0, 900, 1000)
    afternoon = _make("afternoon", 0, 1300, 1400)
    evening = _make("evening", 0, 1700, 1800)
    output = render_timesheet([evening, morning, afternoon], [])
    pos_morning = output.find("morning")
    pos_afternoon = output.find("afternoon")
    pos_evening = output.find("evening")
    if pos_morning < pos_afternoon < pos_evening:
        passed += 1
        print(f"Test {total}: PASS | Events sorted chronologically within Monday")
    else:
        print(f"Test {total}: FAIL | order positions: morning={pos_morning}, afternoon={pos_afternoon}, evening={pos_evening}")

    print(f"{passed}/{total} event rendering tests passed\n")
    return passed, total


# =================================================================
# GROUP 4: ISSUE RENDERING -- sub-lines, phrasing
# =================================================================

def run_issue_rendering():
    print("=== ISSUE RENDERING TESTS ===")
    passed = 0
    total = 0

    # ---- HARD_BUFFER appears as a sub-line ----
    total += 1
    a = _make("Therapy", 0, 1600, 1700)
    b = _make("Commute", 0, 1700, 1800)
    issues = find_all_issues([a, b])
    output = render_timesheet([a, b], issues)
    if "! HARD_BUFFER" in output:
        passed += 1
        print(f"Test {total}: PASS | HARD_BUFFER issue appears with '!' prefix")
    else:
        print(f"Test {total}: FAIL")

    # ---- "before" phrasing on earlier event, "after" on later event ----
    total += 1
    output = render_timesheet([a, b], issues)
    # Therapy is event_a (earlier), so its line says "before Commute"
    # Commute is event_b (later), so its line says "after Therapy"
    has_before = "before Commute" in output
    has_after = "after Therapy" in output
    if has_before and has_after:
        passed += 1
        print(f"Test {total}: PASS | Both 'before' (event_a side) and 'after' (event_b side) phrasing present")
    else:
        print(f"Test {total}: FAIL | before={has_before}, after={has_after}")

    # ---- OVERLAP phrasing ----
    total += 1
    standup = _make("Standup", 0, 1000, 1030)
    one_on_one = _make("1:1", 0, 1015, 1100)
    issues = find_all_issues([standup, one_on_one])
    output = render_timesheet([standup, one_on_one], issues)
    if "OVERLAP: overlaps" in output and "by 15 min" in output:
        passed += 1
        print(f"Test {total}: PASS | OVERLAP shows 'overlaps X by N min'")
    else:
        print(f"Test {total}: FAIL")

    # ---- SOFT_BUFFER appears with gap and required ----
    total += 1
    e1 = _make("First", 0, 900, 1000)
    e2 = _make("Second", 0, 1020, 1120)  # 20-min gap < 30 default soft
    issues = find_all_issues([e1, e2])
    output = render_timesheet([e1, e2], issues)
    if "! SOFT_BUFFER" in output and "20 min" in output and "need 30" in output:
        passed += 1
        print(f"Test {total}: PASS | SOFT_BUFFER shows gap (20) and required (30)")
    else:
        print(f"Test {total}: FAIL")

    # ---- One event can have multiple sub-lines (middle event in chain) ----
    total += 1
    therapy = _make("Therapy", 0, 1600, 1700)
    commute = _make("Commute", 0, 1700, 1730)
    cls = _make("Class", 0, 1730, 1900)
    issues = find_all_issues([therapy, commute, cls])
    output = render_timesheet([therapy, commute, cls], issues)
    # Commute should have 2 sub-lines (one from therapy, one before class).
    # Count '!' characters in the section between Commute and Class.
    commute_pos = output.find("Commute")
    class_pos = output.find("Class")
    commute_section = output[commute_pos:class_pos]
    sub_line_count = commute_section.count("! HARD_BUFFER")
    if sub_line_count == 2:
        passed += 1
        print(f"Test {total}: PASS | Middle event (Commute) shows 2 sub-lines")
    else:
        print(f"Test {total}: FAIL | got {sub_line_count} sub-lines on Commute")

    # ---- No issues -> no '!' characters in output ----
    total += 1
    clean_a = _make("a", 0, 900, 1000)
    clean_b = _make("b", 0, 1200, 1300)  # 2 hour gap, no issue
    output = render_timesheet([clean_a, clean_b], [])
    if "!" not in output:
        passed += 1
        print(f"Test {total}: PASS | Clean week has no '!' sub-lines")
    else:
        print(f"Test {total}: FAIL | unexpected '!' in output")

    print(f"{passed}/{total} issue rendering tests passed\n")
    return passed, total


# =================================================================
# GROUP 5: TITLE COLUMN ALIGNMENT
# =================================================================

def run_title_alignment():
    print("=== TITLE COLUMN ALIGNMENT TESTS ===")
    passed = 0
    total = 0

    # ---- All event lines share the same column for the [QUADRANT] tag ----
    total += 1
    e1 = _make("a", 0, 900, 1000)         # short title
    e2 = _make("longer name", 0, 1100, 1200)
    e3 = _make("xx", 1, 900, 1000)
    output = render_timesheet([e1, e2, e3], [])

    # Find every event line (those that start with "  HH:MM").
    # The [QUADRANT] tag should appear at the same column on each.
    event_lines = [line for line in output.split("\n")
                   if len(line) > 6 and line.startswith("  ") and line[2].isdigit()]
    bracket_positions = [line.find("[") for line in event_lines]
    if len(set(bracket_positions)) == 1 and -1 not in bracket_positions:
        passed += 1
        print(f"Test {total}: PASS | All event [QUADRANT] tags aligned at column {bracket_positions[0]}")
    else:
        print(f"Test {total}: FAIL | bracket positions: {bracket_positions}")

    # ---- A very long title widens the column for the whole week ----
    total += 1
    long_title = "This is an unusually long event title for testing"
    long_e = _make(long_title, 0, 900, 1000)
    short_e = _make("X", 4, 1500, 1600)
    output = render_timesheet([long_e, short_e], [])

    # The short event's [X] tag should still be at the same column
    # as the long event's. The padding adapts to the longest title.
    event_lines = [line for line in output.split("\n")
                   if len(line) > 6 and line.startswith("  ") and line[2].isdigit()]
    bracket_positions = [line.find("[") for line in event_lines]
    if len(set(bracket_positions)) == 1:
        passed += 1
        print(f"Test {total}: PASS | Long title widens column, all tags still aligned")
    else:
        print(f"Test {total}: FAIL | positions: {bracket_positions}")

    print(f"{passed}/{total} title alignment tests passed\n")
    return passed, total


# =================================================================
# GROUP 6: EDGE CASES
# =================================================================

def run_edge_cases():
    print("=== EDGE CASE TESTS ===")
    passed = 0
    total = 0

    # ---- Empty events + empty issues works ----
    total += 1
    try:
        output = render_timesheet([], [])
        if "Weekly Timesheet" in output and output.count("Open Availability") == 7:
            passed += 1
            print(f"Test {total}: PASS | Empty week renders without crashing")
        else:
            print(f"Test {total}: FAIL")
    except Exception as e:
        print(f"Test {total}: FAIL | {type(e).__name__}: {e}")

    # ---- Events but no issues ----
    total += 1
    e1 = _make("a", 0, 900, 1000)
    e2 = _make("b", 0, 1100, 1200)
    output = render_timesheet([e1, e2], [])
    if "Weekly Timesheet" in output and "!" not in output:
        passed += 1
        print(f"Test {total}: PASS | Events without issues render cleanly")
    else:
        print(f"Test {total}: FAIL")

    # ---- Issues but no events (degenerate case -- shouldn't happen
    #      in practice, but the formatter shouldn't crash) ----
    # We construct an Issue manually using fake events that aren't in
    # the events list. The formatter should silently ignore issues whose
    # events aren't in the list (since _issues_for_event won't match).
    total += 1
    fake_a = _make("phantom_a", 0, 900, 1000)
    fake_b = _make("phantom_b", 0, 930, 1030)
    fake_issue = Issue(
        type=IssueType.OVERLAP,
        event_a=fake_a, event_b=fake_b,
        gap_minutes=-30, required_minutes=0,
    )
    try:
        output = render_timesheet([], [fake_issue])
        # All 7 days should still be empty since events list is empty.
        if output.count("Open Availability") == 7:
            passed += 1
            print(f"Test {total}: PASS | Orphan issues don't crash empty rendering")
        else:
            print(f"Test {total}: FAIL")
    except Exception as e:
        print(f"Test {total}: FAIL | {type(e).__name__}: {e}")

    # ---- Output is a single string, not a list ----
    total += 1
    output = render_timesheet([_make("a", 0, 900, 1000)], [])
    if isinstance(output, str):
        passed += 1
        print(f"Test {total}: PASS | Output is a string")
    else:
        print(f"Test {total}: FAIL | got {type(output).__name__}")

    # ---- Output ends without trailing blank line ----
    total += 1
    output = render_timesheet([], [])
    if not output.endswith("\n\n") and not output.endswith("\n"):
        passed += 1
        print(f"Test {total}: PASS | Output doesn't end with stray blank lines")
    else:
        # Allow exactly one final newline character at most? Actually our
        # formatter strips the trailing blank line entirely. Confirm.
        # Last character should NOT be a newline.
        if not output.endswith("\n"):
            passed += 1
            print(f"Test {total}: PASS | Output doesn't end with newline")
        else:
            print(f"Test {total}: FAIL | output ends with newline(s)")

    print(f"{passed}/{total} edge case tests passed\n")
    return passed, total


# =================================================================
# GROUP 7: TYPE SAFETY
# =================================================================

def run_type_safety():
    print("=== TYPE SAFETY TESTS ===")
    passed = 0
    total = 0

    real_event = _make("Real", 0, 900, 1000)

    bad_inputs = [
        ("events as None",         None, [], TypeError),
        ("events as string",       "not a list", [], TypeError),
        ("issues as None",         [real_event], None, TypeError),
        ("issues as dict",         [real_event], {}, TypeError),
        ("events list with junk",  [real_event, "not an event"], [], TypeError),
        ("issues list with junk",  [real_event], ["not an issue"], TypeError),
    ]

    for desc, events_arg, issues_arg, expected_error in bad_inputs:
        total += 1
        try:
            render_timesheet(events_arg, issues_arg)
            print(f"Test {total}: FAIL | {desc} -- expected {expected_error.__name__}, no error raised")
        except expected_error:
            passed += 1
            print(f"Test {total}: PASS | {desc} rejected with {expected_error.__name__}")
        except Exception as e:
            print(f"Test {total}: FAIL | {desc} got {type(e).__name__}: {e}")

    print(f"{passed}/{total} type safety tests passed\n")
    return passed, total


# =================================================================
# Main runner
# =================================================================

def run():
    """Run all timesheet formatter tests."""
    p1, t1 = run_structure()
    p2, t2 = run_empty_days()
    p3, t3 = run_event_rendering()
    p4, t4 = run_issue_rendering()
    p5, t5 = run_title_alignment()
    p6, t6 = run_edge_cases()
    p7, t7 = run_type_safety()
    return (
        p1 + p2 + p3 + p4 + p5 + p6 + p7,
        t1 + t2 + t3 + t4 + t5 + t6 + t7,
    )


if __name__ == "__main__":
    run()
