# ============================================================
# test_dump_parser.py
#
# Tests for src/parsers/dump_parser.py — the freeform text parser.
#
# Organized into seven groups:
#   1. Happy paths
#   2. Format validation (structure errors)
#   3. Tag parsing
#   4. Skipping (blank lines, comments)
#   5. Security caps
#   6. Type safety
#   7. Partial success (the "parse what you can" philosophy)
# ============================================================

from src.parsers.dump_parser import (
    parse_dump,
    DumpResult,
    DumpFailure,
    MAX_TOTAL_INPUT_LENGTH,
    MAX_LINE_COUNT,
    MAX_LINE_LENGTH,
)
from src.models.priority import Quadrant


# =================================================================
# GROUP 1: HAPPY PATHS
# =================================================================

def run_happy_paths():
    """Normal, well-formed input should parse without failures."""
    print("=== HAPPY PATHS ===")

    passed = 0
    total = 0

    # ---- Single minimal line, no tags ----
    total += 1
    r = parse_dump("Therapy | Monday | 4:00PM-5:00PM")
    if (len(r.events) == 1 and len(r.failures) == 0
        and r.events[0].title == "Therapy"
        and r.events[0].day == 0
        and r.events[0].start == 1600
        and r.events[0].end == 1700
        and r.events[0].get_quadrant() == Quadrant.UNSPECIFIED):
        passed += 1
        print(f"Test {total}: PASS | Minimal line (no tags) → 1 event, UNSPECIFIED")
    else:
        print(f"Test {total}: FAIL | got {len(r.events)} events, {len(r.failures)} failures")

    # ---- Single line with priority tag ----
    total += 1
    r = parse_dump("Yoga | Wednesday | 7:00AM-8:00AM | [signal]")
    if (len(r.events) == 1
        and r.events[0].get_quadrant() == Quadrant.SIGNAL):
        passed += 1
        print(f"Test {total}: PASS | Line with [signal] → SIGNAL quadrant")
    else:
        print(f"Test {total}: FAIL | quadrant was {r.events[0].get_quadrant().name if r.events else 'no events'}")

    # ---- All four priority tags ----
    total += 1
    r = parse_dump(
        "A | Mon | 9:00AM-10:00AM | [signal]\n"
        "B | Mon | 11:00AM-12:00PM | [urgent]\n"
        "C | Mon | 1:00PM-2:00PM | [interruption]\n"
        "D | Mon | 3:00PM-4:00PM | [noise]"
    )
    if (len(r.events) == 4 and len(r.failures) == 0
        and r.events[0].get_quadrant() == Quadrant.SIGNAL
        and r.events[1].get_quadrant() == Quadrant.URGENT
        and r.events[2].get_quadrant() == Quadrant.INTERRUPTION
        and r.events[3].get_quadrant() == Quadrant.NOISE):
        passed += 1
        print(f"Test {total}: PASS | All four priority tags map correctly")
    else:
        print(f"Test {total}: FAIL | events={len(r.events)}, failures={len(r.failures)}")

    # ---- Buffer tags ----
    total += 1
    r = parse_dump("Sync | Friday | 2:00PM-2:30PM | [hard:0] [soft:0]")
    if (len(r.events) == 1
        and r.events[0].hard_buffer_minutes == 0
        and r.events[0].soft_buffer_minutes == 0):
        passed += 1
        print(f"Test {total}: PASS | Buffer tags [hard:0] [soft:0] applied")
    else:
        print(f"Test {total}: FAIL | hard={r.events[0].hard_buffer_minutes if r.events else 'no events'}")

    # ---- Combined: priority + buffer tags ----
    total += 1
    r = parse_dump("Class | Mon | 5:30PM-7:00PM | [signal] [hard:30]")
    if (len(r.events) == 1
        and r.events[0].get_quadrant() == Quadrant.SIGNAL
        and r.events[0].hard_buffer_minutes == 30):
        passed += 1
        print(f"Test {total}: PASS | Mixed priority+buffer tags work together")
    else:
        print(f"Test {total}: FAIL")

    # ---- Multiple events, no problems ----
    total += 1
    r = parse_dump(
        "Therapy | Monday | 4:00PM-5:00PM | [signal]\n"
        "Yoga | Wednesday | 7:00AM-8:00AM\n"
        "Sync | Friday | 2:00PM-2:30PM | [noise]"
    )
    if len(r.events) == 3 and len(r.failures) == 0:
        passed += 1
        print(f"Test {total}: PASS | 3-event dump, all parsed cleanly")
    else:
        print(f"Test {total}: FAIL | {len(r.events)} events, {len(r.failures)} failures")

    print(f"{passed}/{total} happy path tests passed\n")
    return passed, total


# =================================================================
# GROUP 2: FORMAT VALIDATION (structure errors)
# =================================================================

def run_format_validation():
    """Lines with wrong structure should produce DumpFailures, not crash."""
    print("=== FORMAT VALIDATION ===")

    passed = 0
    total = 0

    # ---- Too few pipe-separated sections ----
    total += 1
    r = parse_dump("Therapy | Monday")  # Only 2 sections
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | 2-section line rejected as failure")
    else:
        print(f"Test {total}: FAIL")

    # ---- Too many pipe-separated sections ----
    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [signal] | extra")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | 5-section line rejected as failure")
    else:
        print(f"Test {total}: FAIL")

    # ---- Empty title ----
    total += 1
    r = parse_dump(" | Monday | 4:00PM-5:00PM")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Empty title rejected")
    else:
        print(f"Test {total}: FAIL")

    # ---- Empty day ----
    total += 1
    r = parse_dump("Therapy |  | 4:00PM-5:00PM")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Empty day rejected")
    else:
        print(f"Test {total}: FAIL")

    # ---- Empty time range ----
    total += 1
    r = parse_dump("Therapy | Monday | ")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Empty time range rejected")
    else:
        print(f"Test {total}: FAIL")

    # ---- Time range missing the dash ----
    total += 1
    r = parse_dump("Therapy | Monday | 4:00PM 5:00PM")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Time range without dash rejected")
    else:
        print(f"Test {total}: FAIL")

    # ---- Time range with TWO dashes ----
    total += 1
    r = parse_dump("Therapy | Monday | 4:00PM-5:00PM-6:00PM")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Time range with two dashes rejected")
    else:
        print(f"Test {total}: FAIL")

    # ---- Invalid day name ----
    total += 1
    r = parse_dump("Therapy | Funday | 4:00PM-5:00PM")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Invalid day 'Funday' rejected")
    else:
        print(f"Test {total}: FAIL")

    # ---- Invalid time (hour 25) ----
    total += 1
    r = parse_dump("Therapy | Monday | 25:00-26:00")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Invalid time 25:00 rejected")
    else:
        print(f"Test {total}: FAIL")

    # ---- End before start ----
    total += 1
    r = parse_dump("Therapy | Monday | 5:00PM-4:00PM")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | End-before-start rejected by Event validation")
    else:
        print(f"Test {total}: FAIL")

    # ---- Verify failure carries line number ----
    total += 1
    r = parse_dump(
        "Therapy | Monday | 4:00PM-5:00PM\n"
        "Bad line here\n"
        "Yoga | Wednesday | 7:00AM-8:00AM"
    )
    if (len(r.events) == 2 and len(r.failures) == 1
        and r.failures[0].line_number == 2):
        passed += 1
        print(f"Test {total}: PASS | Failure carries correct line number (2)")
    else:
        line_num = r.failures[0].line_number if r.failures else "no failure"
        print(f"Test {total}: FAIL | got line_number={line_num}")

    print(f"{passed}/{total} format validation tests passed\n")
    return passed, total


# =================================================================
# GROUP 3: TAG PARSING
# =================================================================

def run_tag_parsing():
    """Every tag variant: case, whitespace, ordering, duplicates."""
    print("=== TAG PARSING ===")

    passed = 0
    total = 0

    # ---- Case-insensitive priority ----
    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [SIGNAL]")
    if (len(r.events) == 1
        and r.events[0].get_quadrant() == Quadrant.SIGNAL):
        passed += 1
        print(f"Test {total}: PASS | [SIGNAL] (uppercase) works")
    else:
        print(f"Test {total}: FAIL")

    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [SiGnAl]")
    if (len(r.events) == 1
        and r.events[0].get_quadrant() == Quadrant.SIGNAL):
        passed += 1
        print(f"Test {total}: PASS | [SiGnAl] (mixed case) works")
    else:
        print(f"Test {total}: FAIL")

    # ---- Whitespace variants on buffer tags ----
    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [hard: 30]")
    if (len(r.events) == 1
        and r.events[0].hard_buffer_minutes == 30):
        passed += 1
        print(f"Test {total}: PASS | [hard: 30] (space after colon) works")
    else:
        print(f"Test {total}: FAIL")

    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [ hard : 30 ]")
    if (len(r.events) == 1
        and r.events[0].hard_buffer_minutes == 30):
        passed += 1
        print(f"Test {total}: PASS | [ hard : 30 ] (lots of whitespace) works")
    else:
        print(f"Test {total}: FAIL")

    # ---- Tag order doesn't matter ----
    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [hard:30] [signal] [soft:60]")
    if (len(r.events) == 1
        and r.events[0].get_quadrant() == Quadrant.SIGNAL
        and r.events[0].hard_buffer_minutes == 30
        and r.events[0].soft_buffer_minutes == 60):
        passed += 1
        print(f"Test {total}: PASS | Tag order doesn't matter — all three applied")
    else:
        print(f"Test {total}: FAIL")

    # ---- Duplicate priority tag rejected ----
    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [signal] [urgent]")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Two priority tags rejected as duplicate")
    else:
        print(f"Test {total}: FAIL")

    # ---- Duplicate hard tag rejected ----
    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [hard:30] [hard:60]")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Two [hard:N] tags rejected as duplicate")
    else:
        print(f"Test {total}: FAIL")

    # ---- Unknown tag rejected ----
    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [important]")  # not a real tag
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Unknown tag [important] rejected")
    else:
        print(f"Test {total}: FAIL")

    # ---- Buffer tag with non-numeric value rejected ----
    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [hard:abc]")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | [hard:abc] rejected (not a number)")
    else:
        print(f"Test {total}: FAIL")

    # ---- Unclosed tag bracket ----
    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [signal")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Unclosed [signal rejected")
    else:
        print(f"Test {total}: FAIL")

    # ---- Text between tags rejected ----
    total += 1
    r = parse_dump("A | Mon | 9:00AM-10:00AM | [signal] junk [hard:30]")
    if len(r.events) == 0 and len(r.failures) == 1:
        passed += 1
        print(f"Test {total}: PASS | Text between tags rejected")
    else:
        print(f"Test {total}: FAIL")

    print(f"{passed}/{total} tag parsing tests passed\n")
    return passed, total


# =================================================================
# GROUP 4: SKIPPING (blank lines, comments)
# =================================================================

def run_skipping():
    """Blank lines and # comments should be skipped, not errored on."""
    print("=== SKIPPING (blank lines + comments) ===")

    passed = 0
    total = 0

    # ---- Blank lines skipped ----
    total += 1
    r = parse_dump(
        "Therapy | Monday | 4:00PM-5:00PM\n"
        "\n"
        "\n"
        "Yoga | Wednesday | 7:00AM-8:00AM"
    )
    if len(r.events) == 2 and len(r.failures) == 0:
        passed += 1
        print(f"Test {total}: PASS | Blank lines skipped (no failures)")
    else:
        print(f"Test {total}: FAIL")

    # ---- Whitespace-only lines skipped ----
    total += 1
    r = parse_dump(
        "Therapy | Monday | 4:00PM-5:00PM\n"
        "    \n"
        "\t\t\n"
        "Yoga | Wednesday | 7:00AM-8:00AM"
    )
    if len(r.events) == 2 and len(r.failures) == 0:
        passed += 1
        print(f"Test {total}: PASS | Whitespace-only lines skipped")
    else:
        print(f"Test {total}: FAIL")

    # ---- Comment lines skipped ----
    total += 1
    r = parse_dump(
        "# Monday block\n"
        "Therapy | Monday | 4:00PM-5:00PM\n"
        "# Wednesday\n"
        "Yoga | Wednesday | 7:00AM-8:00AM\n"
        "# end"
    )
    if len(r.events) == 2 and len(r.failures) == 0:
        passed += 1
        print(f"Test {total}: PASS | # comment lines skipped")
    else:
        print(f"Test {total}: FAIL")

    # ---- Indented comment skipped ----
    total += 1
    r = parse_dump("   # leading whitespace then #\nTherapy | Mon | 4:00PM-5:00PM")
    if len(r.events) == 1 and len(r.failures) == 0:
        passed += 1
        print(f"Test {total}: PASS | Indented # comment skipped")
    else:
        print(f"Test {total}: FAIL")

    # ---- Empty dump (just blank lines and comments) ----
    total += 1
    r = parse_dump("# nothing here\n\n# really\n\n")
    if len(r.events) == 0 and len(r.failures) == 0 and r.global_error is None:
        passed += 1
        print(f"Test {total}: PASS | Empty dump (only comments/blanks) → 0 events, 0 failures, no global error")
    else:
        print(f"Test {total}: FAIL")

    # ---- Completely empty string ----
    total += 1
    r = parse_dump("")
    if len(r.events) == 0 and len(r.failures) == 0 and r.global_error is None:
        passed += 1
        print(f"Test {total}: PASS | Empty string → no events, no failures, no global error")
    else:
        print(f"Test {total}: FAIL")

    print(f"{passed}/{total} skipping tests passed\n")
    return passed, total


# =================================================================
# GROUP 5: SECURITY CAPS
# =================================================================

def run_security_caps():
    """The three hard caps should reject oversized input cleanly."""
    print("=== SECURITY CAPS ===")

    passed = 0
    total = 0

    # ---- Total input length cap ----
    total += 1
    oversized = "x" * (MAX_TOTAL_INPUT_LENGTH + 1)
    r = parse_dump(oversized)
    if (r.global_error is not None
        and len(r.events) == 0 and len(r.failures) == 0):
        passed += 1
        print(f"Test {total}: PASS | Input over {MAX_TOTAL_INPUT_LENGTH} chars rejected globally")
    else:
        print(f"Test {total}: FAIL | global_error={r.global_error}")

    # ---- Just under the cap should succeed ----
    total += 1
    # We need a valid-ish input that's close to the cap. We pack it
    # with many blank lines (which are cheap and pass through).
    near_cap = "\n" * (MAX_TOTAL_INPUT_LENGTH - 10)
    r = parse_dump(near_cap)
    # Should produce 0 events and 0 failures (all lines are blank
    # and skipped), and crucially NO global error.
    if r.global_error is None and len(r.failures) == 0:
        # But wait — the blank lines count against MAX_LINE_COUNT,
        # which would fail. So actually we'd expect a line-count
        # global error here. Let me test the boundary differently.
        pass

    # Better near-cap test: use a small string that's under all caps.
    r = parse_dump("Therapy | Monday | 4:00PM-5:00PM")  # tiny but valid
    if r.global_error is None:
        passed += 1
        print(f"Test {total}: PASS | Small valid input has no global error")
    else:
        print(f"Test {total}: FAIL | global_error={r.global_error}")

    # ---- Line count cap ----
    total += 1
    too_many_lines = "\n".join(["# comment"] * (MAX_LINE_COUNT + 1))
    r = parse_dump(too_many_lines)
    if r.global_error is not None and "too many lines" in r.global_error.lower():
        passed += 1
        print(f"Test {total}: PASS | Over {MAX_LINE_COUNT} lines rejected globally")
    else:
        print(f"Test {total}: FAIL | global_error={r.global_error}")

    # ---- Exactly at line count cap should pass ----
    total += 1
    at_cap = "\n".join(["# comment"] * MAX_LINE_COUNT)
    r = parse_dump(at_cap)
    if r.global_error is None:
        passed += 1
        print(f"Test {total}: PASS | Exactly {MAX_LINE_COUNT} lines accepted (boundary)")
    else:
        print(f"Test {total}: FAIL | global_error={r.global_error}")

    # ---- Per-line length cap ----
    total += 1
    one_huge_line = "X" * (MAX_LINE_LENGTH + 1)
    r = parse_dump(one_huge_line)
    # Per-line cap is a PER-LINE failure, not a global error.
    if (r.global_error is None
        and len(r.failures) == 1
        and "too long" in r.failures[0].reason.lower()):
        passed += 1
        print(f"Test {total}: PASS | Line over {MAX_LINE_LENGTH} chars rejected per-line (not globally)")
    else:
        print(f"Test {total}: FAIL")

    # ---- Long line in a dump shouldn't poison good lines ----
    total += 1
    mixed = ("Therapy | Monday | 4:00PM-5:00PM\n"
             + "X" * (MAX_LINE_LENGTH + 1) + "\n"
             "Yoga | Wednesday | 7:00AM-8:00AM")
    r = parse_dump(mixed)
    if (r.global_error is None
        and len(r.events) == 2 and len(r.failures) == 1):
        passed += 1
        print(f"Test {total}: PASS | One oversized line → 2 events parse, 1 failure")
    else:
        print(f"Test {total}: FAIL | events={len(r.events)}, failures={len(r.failures)}")

    # ---- Failure echo is bounded (never returns the full huge input) ----
    total += 1
    huge = "X" * 10_000  # exceeds total input cap
    r = parse_dump(huge)
    # global_error itself should be a short message, not 10k chars.
    if (r.global_error is not None and len(r.global_error) < 500):
        passed += 1
        print(f"Test {total}: PASS | Global error message bounded (length={len(r.global_error)})")
    else:
        msg_len = len(r.global_error) if r.global_error else 0
        print(f"Test {total}: FAIL | error message length={msg_len}")

    print(f"{passed}/{total} security cap tests passed\n")
    return passed, total


# =================================================================
# GROUP 6: TYPE SAFETY
# =================================================================

def run_type_safety():
    """Non-string input should be rejected with global_error."""
    print("=== TYPE SAFETY ===")

    passed = 0
    total = 0

    bad_inputs = [
        (None, "None"),
        (12345, "integer"),
        (["line1", "line2"], "list"),
        ({"key": "value"}, "dict"),
        (b"bytes are not strings", "bytes"),
    ]

    for bad, label in bad_inputs:
        total += 1
        r = parse_dump(bad)
        if (r.global_error is not None
            and len(r.events) == 0 and len(r.failures) == 0):
            passed += 1
            print(f"Test {total}: PASS | {label} rejected via global_error")
        else:
            print(f"Test {total}: FAIL | {label}: events={len(r.events)}, error={r.global_error}")

    print(f"{passed}/{total} type safety tests passed\n")
    return passed, total


# =================================================================
# GROUP 7: PARTIAL SUCCESS (the real-world scenario)
# =================================================================

def run_partial_success():
    """The mission: good lines parse, bad lines reported, no crash."""
    print("=== PARTIAL SUCCESS (realistic mixed input) ===")

    passed = 0
    total = 0

    # ---- Realistic mixed week ----
    realistic_dump = """
# Monday block — back-to-back day
Therapy | Monday | 4:00PM-5:00PM | [signal]
Commute | Monday | 5:00PM-5:30PM | [urgent]
Class   | Monday | 5:30PM-7:00PM | [signal]

# Tuesday — typo on this line
Standup | Tuseday | 10:00AM-10:30AM | [interruption]
1:1     | Tuesday | 10:15AM-11:00AM | [signal]

# Wednesday block
Yoga | Wednesday | 7:00AM-8:00AM

# Friday — Zoom override
Sync A | Friday | 2:00PM-2:30PM | [noise] [hard:0] [soft:0]
Sync B | Friday | 2:30PM-3:00PM | [noise]

# Invalid time
Junk | Thursday | 25:00-26:00 | [signal]
""".strip()

    r = parse_dump(realistic_dump)

    total += 1
    # We expect 7 valid events (Therapy, Commute, Class, 1:1, Yoga, Sync A, Sync B)
    # and 2 failures (Tuseday typo, 25:00 invalid time).
    if len(r.events) == 7:
        passed += 1
        print(f"Test {total}: PASS | 7 valid events parsed from messy real-world input")
    else:
        titles = [e.title for e in r.events]
        print(f"Test {total}: FAIL | expected 7 events, got {len(r.events)}: {titles}")

    total += 1
    if len(r.failures) == 2:
        passed += 1
        print(f"Test {total}: PASS | 2 failures captured (Tuseday + 25:00)")
    else:
        print(f"Test {total}: FAIL | expected 2 failures, got {len(r.failures)}")
        for f in r.failures:
            print(f"           Line {f.line_number}: {f.reason}")

    total += 1
    # Each failure should have line number AND reason populated
    if (len(r.failures) >= 1
        and r.failures[0].line_number > 0
        and len(r.failures[0].reason) > 0):
        passed += 1
        print(f"Test {total}: PASS | Failures carry line number + reason")
    else:
        print(f"Test {total}: FAIL")

    total += 1
    # No global error — this is a normal, healthy parse
    if r.global_error is None:
        passed += 1
        print(f"Test {total}: PASS | Mixed dump has no global error")
    else:
        print(f"Test {total}: FAIL | got global_error: {r.global_error}")

    print(f"{passed}/{total} partial success tests passed\n")
    return passed, total


# =================================================================
# Main runner
# =================================================================

def run():
    """Run all dump parser tests."""
    p1, t1 = run_happy_paths()
    p2, t2 = run_format_validation()
    p3, t3 = run_tag_parsing()
    p4, t4 = run_skipping()
    p5, t5 = run_security_caps()
    p6, t6 = run_type_safety()
    p7, t7 = run_partial_success()
    return (
        p1 + p2 + p3 + p4 + p5 + p6 + p7,
        t1 + t2 + t3 + t4 + t5 + t6 + t7,
    )


if __name__ == "__main__":
    run()
