# ============================================================
# test_event_conflict.py
#
# Tests for the Event-aware functions in conflict_checker.py:
#   - has_event_conflict(a, b)
#   - find_all_conflicts(events)
#
# The numeric has_conflict() is tested in test_conflict_checker.py;
# this file focuses on the Event-aware layer.
# ============================================================

from src.models.event import Event
from src.engine.conflict_checker import (
    has_event_conflict,
    find_all_conflicts,
)


# =================================================================
# GROUP 1: has_event_conflict — pairwise checks
# =================================================================

def run_pairwise():
    """Test has_event_conflict on pairs. Returns (passed, total)."""
    print("=== has_event_conflict TESTS ===")

    # Build a small set of reusable events so each test reads cleanly.
    study_mon_4to5   = Event(title="Study",   day=0, start=1600, end=1700)
    school_mon_7to10 = Event(title="School",  day=0, start=1900, end=2200)
    study_tue_4to5   = Event(title="Study",   day=1, start=1600, end=1700)
    overlap_mon      = Event(title="Overlap", day=0, start=1630, end=1730)
    touch_mon        = Event(title="Touch",   day=0, start=1700, end=1800)
    same_mon         = Event(title="Same",    day=0, start=1600, end=1700)

    # Each tuple: (description, event_a, event_b, expected)
    tests = [
        ("Same day, no overlap → no conflict",
            study_mon_4to5, school_mon_7to10, False),
        ("Different days, same times → no conflict",
            study_mon_4to5, study_tue_4to5, False),
        ("Same day, overlapping → conflict",
            study_mon_4to5, overlap_mon, True),
        ("Same day, touching at boundary → no conflict",
            study_mon_4to5, touch_mon, False),
        ("Same day, identical times → conflict",
            study_mon_4to5, same_mon, True),
        ("Order doesn't matter — A vs B same as B vs A",
            overlap_mon, study_mon_4to5, True),
    ]

    passed = 0
    for i, (desc, a, b, expected) in enumerate(tests, 1):
        result = has_event_conflict(a, b)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"Test {i}: {status} | {desc} | Expected: {expected}, Got: {result}")
    print(f"{passed}/{len(tests)} pairwise tests passed\n")
    return passed, len(tests)


# =================================================================
# GROUP 2: has_event_conflict — type errors
# =================================================================

def run_pairwise_validation():
    """Test that has_event_conflict rejects non-Events. Returns (passed, total)."""
    print("=== has_event_conflict VALIDATION TESTS ===")

    real_event = Event(title="Real", day=0, start=1600, end=1700)

    # Each tuple: (description, builder-lambda, expected_error)
    tests = [
        ("Non-Event in first slot rejected",
            lambda: has_event_conflict("not an event", real_event), TypeError),
        ("Non-Event in second slot rejected",
            lambda: has_event_conflict(real_event, {"day": 0}), TypeError),
        ("None in first slot rejected",
            lambda: has_event_conflict(None, real_event), TypeError),
        ("Tuple in second slot rejected",
            lambda: has_event_conflict(real_event, (0, 1600, 1700)), TypeError),
    ]

    passed = 0
    for i, (desc, builder, expected_error) in enumerate(tests, 1):
        try:
            result = builder()
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, got result: {result}"
        except expected_error:
            status = "PASS"
            detail = f"raised {expected_error.__name__}"
            passed += 1
        except Exception as e:
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, got {type(e).__name__}"
        print(f"Test {i}: {status} | {desc} | {detail}")
    print(f"{passed}/{len(tests)} validation tests passed\n")
    return passed, len(tests)


# =================================================================
# GROUP 3: find_all_conflicts — happy paths
# =================================================================

def run_find_all():
    """Test find_all_conflicts on various event lists. Returns (passed, total)."""
    print("=== find_all_conflicts TESTS ===")

    # Reusable events
    a = Event(title="A", day=0, start=1600, end=1700)  # Mon 4-5pm
    b = Event(title="B", day=0, start=1630, end=1730)  # Mon 4:30-5:30 (overlaps A)
    c = Event(title="C", day=0, start=1900, end=2000)  # Mon 7-8 (no overlap with A or B)
    d = Event(title="D", day=1, start=1600, end=1700)  # Tue 4-5pm (different day)
    e = Event(title="E", day=0, start=1645, end=1715)  # Mon 4:45-5:15 (overlaps both A and B)

    passed = 0
    total = 0

    # --- Test: empty list returns empty list ---
    total += 1
    result = find_all_conflicts([])
    if result == []:
        passed += 1
        print(f"Test {total}: PASS | Empty list → no conflicts")
    else:
        print(f"Test {total}: FAIL | Empty list → expected [], got {result}")

    # --- Test: single event returns empty list ---
    total += 1
    result = find_all_conflicts([a])
    if result == []:
        passed += 1
        print(f"Test {total}: PASS | Single event → no conflicts (nothing to compare against)")
    else:
        print(f"Test {total}: FAIL | Single event → expected [], got {result}")

    # --- Test: two non-conflicting events ---
    total += 1
    result = find_all_conflicts([a, c])
    if result == []:
        passed += 1
        print(f"Test {total}: PASS | Two non-overlapping events → no conflicts")
    else:
        print(f"Test {total}: FAIL | Expected [], got {len(result)} conflicts")

    # --- Test: two conflicting events return one pair ---
    total += 1
    result = find_all_conflicts([a, b])
    if len(result) == 1 and result[0] == (a, b):
        passed += 1
        print(f"Test {total}: PASS | A overlaps B → 1 conflict pair (A, B)")
    else:
        print(f"Test {total}: FAIL | Expected [(A, B)], got {result}")

    # --- Test: order of input is preserved in output ---
    total += 1
    result = find_all_conflicts([b, a])  # reversed input
    if len(result) == 1 and result[0] == (b, a):
        passed += 1
        print(f"Test {total}: PASS | Reversed input → conflict reported as (B, A)")
    else:
        print(f"Test {total}: FAIL | Expected [(B, A)], got {result}")

    # --- Test: each pair reported only once (not twice) ---
    total += 1
    result = find_all_conflicts([a, b])
    if len(result) == 1:
        passed += 1
        print(f"Test {total}: PASS | Conflict pair reported once, not twice")
    else:
        print(f"Test {total}: FAIL | Expected 1 pair, got {len(result)}")

    # --- Test: different days never conflict ---
    total += 1
    result = find_all_conflicts([a, d])  # same time, different days
    if result == []:
        passed += 1
        print(f"Test {total}: PASS | Different days, same times → no conflicts")
    else:
        print(f"Test {total}: FAIL | Expected [], got {len(result)} conflicts")

    # --- Test: one event overlapping multiple others ---
    # E (4:45-5:15) overlaps both A (4-5) and B (4:30-5:30).
    # A and B also overlap each other.
    # So we expect 3 conflict pairs total: (A,B), (A,E), (B,E).
    total += 1
    result = find_all_conflicts([a, b, e])
    expected = [(a, b), (a, e), (b, e)]
    if result == expected:
        passed += 1
        print(f"Test {total}: PASS | 3-way overlap → 3 distinct conflict pairs")
    else:
        print(f"Test {total}: FAIL | Expected {len(expected)} pairs, got {len(result)}")

    # --- Test: bigger mixed list (the realistic week scenario) ---
    # [a Mon 4-5, b Mon 4:30-5:30, c Mon 7-8, d Tue 4-5, e Mon 4:45-5:15]
    # Mon overlaps: (a,b), (a,e), (b,e). c is alone on Mon. d is on Tue.
    # Expected: 3 pairs.
    total += 1
    result = find_all_conflicts([a, b, c, d, e])
    if len(result) == 3 and (a, b) in result and (a, e) in result and (b, e) in result:
        passed += 1
        print(f"Test {total}: PASS | Mixed week list → finds exactly 3 real conflicts")
    else:
        print(f"Test {total}: FAIL | Expected 3 specific pairs, got {result}")

    # --- Test: duplicate events DO conflict with each other ---
    # If a user accidentally enters the same event twice, that's a real
    # conflict (it's double-booking themselves) — flag it.
    total += 1
    a_copy = Event(title="A", day=0, start=1600, end=1700)
    result = find_all_conflicts([a, a_copy])
    if len(result) == 1:
        passed += 1
        print(f"Test {total}: PASS | Duplicate events → flagged as conflict")
    else:
        print(f"Test {total}: FAIL | Expected duplicate to be a conflict, got {result}")

    print(f"{passed}/{total} find_all_conflicts tests passed\n")
    return passed, total


# =================================================================
# GROUP 4: find_all_conflicts — type errors
# =================================================================

def run_find_all_validation():
    """Test that find_all_conflicts rejects bad input. Returns (passed, total)."""
    print("=== find_all_conflicts VALIDATION TESTS ===")

    real_event = Event(title="Real", day=0, start=1600, end=1700)

    tests = [
        ("Non-list input rejected",
            lambda: find_all_conflicts("not a list"), TypeError),
        ("None rejected",
            lambda: find_all_conflicts(None), TypeError),
        ("Tuple rejected (must be a list)",
            lambda: find_all_conflicts((real_event, real_event)), TypeError),
        ("List with non-Event item rejected",
            lambda: find_all_conflicts([real_event, "not an event"]), TypeError),
        ("List with None item rejected",
            lambda: find_all_conflicts([real_event, None]), TypeError),
    ]

    passed = 0
    for i, (desc, builder, expected_error) in enumerate(tests, 1):
        try:
            result = builder()
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, got result: {result}"
        except expected_error:
            status = "PASS"
            detail = f"raised {expected_error.__name__}"
            passed += 1
        except Exception as e:
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, got {type(e).__name__}"
        print(f"Test {i}: {status} | {desc} | {detail}")
    print(f"{passed}/{len(tests)} validation tests passed\n")
    return passed, len(tests)


def run():
    """Run all event conflict tests. Returns (passed, total)."""
    p1, t1 = run_pairwise()
    p2, t2 = run_pairwise_validation()
    p3, t3 = run_find_all()
    p4, t4 = run_find_all_validation()
    return p1 + p2 + p3 + p4, t1 + t2 + t3 + t4


if __name__ == "__main__":
    run()
