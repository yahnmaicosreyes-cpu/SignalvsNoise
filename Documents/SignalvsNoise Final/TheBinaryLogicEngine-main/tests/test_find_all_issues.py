# ============================================================
# test_find_all_issues.py
#
# Tests for find_all_issues() in conflict_checker.py.
#
# Test groups:
#   1. No-issue cases — events that should produce zero issues
#   2. OVERLAP detection
#   3. HARD_BUFFER detection (with default and override)
#   4. SOFT_BUFFER detection (with default and override)
#   5. Severity precedence (most-severe-wins)
#   6. Multi-event scenarios (the realistic week)
#   7. Edge cases
#   8. Type validation
#
# These cover defaults of 15 (hard) and 30 (soft) — confirm in
# buffer_defaults.py if those numbers ever change.
# ============================================================

from src.models.event import Event
from src.models.issue import Issue, IssueType
from src.engine.conflict_checker import find_all_issues


# Convenience: all tests use these defaults
HARD = 15
SOFT = 30


def _make(title, day, start, end, hard=None, soft=None):
    """Tiny helper — keeps test setup readable."""
    return Event(
        title=title, day=day, start=start, end=end,
        hard_buffer_minutes=hard, soft_buffer_minutes=soft,
    )


# =================================================================
# GROUP 1: No issues expected
# =================================================================

def run_no_issues():
    print("=== find_all_issues — NO ISSUE CASES ===")

    tests = []

    # 1: empty list
    tests.append(("Empty list", [], 0))

    # 2: single event
    tests.append(("Single event", [_make("A", 0, 1600, 1700)], 0))

    # 3: cross-day (no buffer issue across days)
    tests.append((
        "Same times on different days",
        [_make("A", 0, 1600, 1700), _make("B", 1, 1600, 1700)],
        0,
    ))

    # 4: same day, gap >= soft default (30 min)
    tests.append((
        "Same day, gap of 30 min meets soft default",
        [_make("A", 0, 1600, 1700), _make("B", 0, 1730, 1830)],
        0,
    ))

    # 5: same day, gap WAY more than soft default
    tests.append((
        "Same day, gap of 2 hours — way more than needed",
        [_make("A", 0, 900, 1000), _make("B", 0, 1200, 1300)],
        0,
    ))

    # 6: per-event override that allows zero gap
    tests.append((
        "Override hard=0, soft=0 makes touching events fine",
        [_make("A", 0, 1600, 1700, hard=0, soft=0),
         _make("B", 0, 1700, 1800)],
        0,
    ))

    passed = 0
    for i, (desc, events, expected_count) in enumerate(tests, 1):
        issues = find_all_issues(events)
        status = "PASS" if len(issues) == expected_count else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"Test {i}: {status} | {desc} | expected {expected_count}, got {len(issues)}")
    print(f"{passed}/{len(tests)} no-issue tests passed\n")
    return passed, len(tests)


# =================================================================
# GROUP 2: OVERLAP detection
# =================================================================

def run_overlap():
    print("=== find_all_issues — OVERLAP DETECTION ===")

    tests = []

    # 1: clear overlap
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1630, 1730)
    tests.append(("Clear 30-min overlap", [a, b], IssueType.OVERLAP, -30))

    # 2: full containment
    # A 9-5pm, B noon-1pm. Sorted by start, A is "earlier" (starts first).
    # Gap = minutes_between(A.end=1700, B.start=1200) = -300 (B starts 5 hours before A ends).
    # This is the engine's consistent definition of gap; an overlap shows up as a negative number.
    a = _make("A", 0, 900, 1700)
    b = _make("B", 0, 1200, 1300)
    tests.append(("B fully inside A", [a, b], IssueType.OVERLAP, -300))

    # 3: identical times
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1600, 1700)
    tests.append(("Identical times", [a, b], IssueType.OVERLAP, -60))

    # 4: input order doesn't affect output ordering
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1630, 1730)
    tests.append(("Reversed input still produces overlap", [b, a], IssueType.OVERLAP, -30))

    passed = 0
    for i, (desc, events, expected_type, expected_gap) in enumerate(tests, 1):
        issues = find_all_issues(events)
        if (len(issues) == 1
            and issues[0].type == expected_type
            and issues[0].gap_minutes == expected_gap):
            status = "PASS"
            detail = f"{expected_type.value}, gap={expected_gap}"
            passed += 1
        else:
            status = "FAIL"
            detail = f"got {[(i.type.value, i.gap_minutes) for i in issues]}"
        print(f"Test {i}: {status} | {desc} | {detail}")
    print(f"{passed}/{len(tests)} overlap tests passed\n")
    return passed, len(tests)


# =================================================================
# GROUP 3: HARD_BUFFER detection
# =================================================================

def run_hard_buffer():
    print("=== find_all_issues — HARD_BUFFER DETECTION ===")

    tests = []

    # 1: zero gap, default hard (15) → HARD_BUFFER
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1700, 1800)
    tests.append(("Zero gap with default hard=15 → HARD_BUFFER",
        [a, b], IssueType.HARD_BUFFER, 0, 15))

    # 2: 10-min gap, default hard (15) → HARD_BUFFER
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1710, 1810)
    tests.append(("10-min gap with default hard=15 → HARD_BUFFER",
        [a, b], IssueType.HARD_BUFFER, 10, 15))

    # 3: 14-min gap, default hard (15) → HARD_BUFFER (just under)
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1714, 1814)
    tests.append(("14-min gap with default hard=15 → HARD_BUFFER",
        [a, b], IssueType.HARD_BUFFER, 14, 15))

    # 4: per-event override raises hard requirement
    a = _make("A", 0, 1600, 1700, hard=45)
    b = _make("B", 0, 1730, 1830)
    tests.append(("30-min gap with hard=45 override → HARD_BUFFER",
        [a, b], IssueType.HARD_BUFFER, 30, 45))

    # 5: per-event override hard=0 means zero gap is fine for hard,
    #    but default soft=30 still applies → SOFT_BUFFER expected
    a = _make("A", 0, 1600, 1700, hard=0)
    b = _make("B", 0, 1700, 1800)
    tests.append(("Override hard=0, default soft=30, 0-min gap → SOFT_BUFFER",
        [a, b], IssueType.SOFT_BUFFER, 0, 30))

    passed = 0
    for i, (desc, events, expected_type, expected_gap, expected_required) in enumerate(tests, 1):
        issues = find_all_issues(events)
        if (len(issues) == 1
            and issues[0].type == expected_type
            and issues[0].gap_minutes == expected_gap
            and issues[0].required_minutes == expected_required):
            status = "PASS"
            detail = f"{expected_type.value}, gap={expected_gap}, required={expected_required}"
            passed += 1
        else:
            status = "FAIL"
            detail = f"got {[(i.type.value, i.gap_minutes, i.required_minutes) for i in issues]}"
        print(f"Test {i}: {status} | {desc} | {detail}")
    print(f"{passed}/{len(tests)} hard buffer tests passed\n")
    return passed, len(tests)


# =================================================================
# GROUP 4: SOFT_BUFFER detection
# =================================================================

def run_soft_buffer():
    print("=== find_all_issues — SOFT_BUFFER DETECTION ===")

    tests = []

    # 1: 15-min gap (meets hard, fails soft)
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1715, 1815)
    tests.append(("15-min gap (= hard) but < soft default 30 → SOFT_BUFFER",
        [a, b], IssueType.SOFT_BUFFER, 15, 30))

    # 2: 29-min gap (just under soft)
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1729, 1829)
    tests.append(("29-min gap < soft default 30 → SOFT_BUFFER",
        [a, b], IssueType.SOFT_BUFFER, 29, 30))

    # 3: exactly 30-min gap = no issue (boundary)
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1730, 1830)
    tests.append(("30-min gap exactly = no issue", [a, b], None, None, None))

    # 4: per-event override raises soft requirement
    a = _make("A", 0, 1600, 1700, soft=60)
    b = _make("B", 0, 1730, 1830)
    tests.append(("30-min gap with soft=60 override → SOFT_BUFFER",
        [a, b], IssueType.SOFT_BUFFER, 30, 60))

    passed = 0
    for i, (desc, events, expected_type, expected_gap, expected_required) in enumerate(tests, 1):
        issues = find_all_issues(events)
        if expected_type is None:
            # Expecting NO issue
            if len(issues) == 0:
                status = "PASS"
                detail = "no issues as expected"
                passed += 1
            else:
                status = "FAIL"
                detail = f"expected no issues, got {[(i.type.value, i.gap_minutes) for i in issues]}"
        else:
            if (len(issues) == 1
                and issues[0].type == expected_type
                and issues[0].gap_minutes == expected_gap
                and issues[0].required_minutes == expected_required):
                status = "PASS"
                detail = f"{expected_type.value}, gap={expected_gap}, required={expected_required}"
                passed += 1
            else:
                status = "FAIL"
                detail = f"got {[(i.type.value, i.gap_minutes, i.required_minutes) for i in issues]}"
        print(f"Test {i}: {status} | {desc} | {detail}")
    print(f"{passed}/{len(tests)} soft buffer tests passed\n")
    return passed, len(tests)


# =================================================================
# GROUP 5: Severity precedence
# =================================================================

def run_severity():
    print("=== find_all_issues — SEVERITY PRECEDENCE ===")

    # When a pair could trigger multiple thresholds, the most severe wins.
    # Each pair produces AT MOST one issue.

    tests = []

    # 1: overlap also "violates" buffers — should report just OVERLAP
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1630, 1730)
    tests.append(("Overlap reported as OVERLAP only (not also a buffer)",
        [a, b], 1, IssueType.OVERLAP))

    # 2: hard violation also fails soft — should report just HARD_BUFFER
    a = _make("A", 0, 1600, 1700)
    b = _make("B", 0, 1705, 1805)
    tests.append(("5-min gap reported as HARD_BUFFER (not SOFT_BUFFER)",
        [a, b], 1, IssueType.HARD_BUFFER))

    passed = 0
    for i, (desc, events, expected_count, expected_type) in enumerate(tests, 1):
        issues = find_all_issues(events)
        if len(issues) == expected_count and issues[0].type == expected_type:
            status = "PASS"
            detail = f"got {expected_type.value} only, count={expected_count}"
            passed += 1
        else:
            status = "FAIL"
            detail = f"got {[i.type.value for i in issues]}"
        print(f"Test {i}: {status} | {desc} | {detail}")
    print(f"{passed}/{len(tests)} severity tests passed\n")
    return passed, len(tests)


# =================================================================
# GROUP 6: Realistic multi-event scenarios
# =================================================================

def run_realistic():
    print("=== find_all_issues — REALISTIC SCENARIOS ===")

    passed = 0
    total = 0

    # --- Scenario A: the example from earlier ---
    # Therapy 4-5pm → Commute 5-5:30pm → Class 5:30-7pm
    # Both transitions are 0-min gaps, default hard=15 → 2 HARD_BUFFER issues
    therapy = _make("Therapy", 0, 1600, 1700)
    commute = _make("Commute", 0, 1700, 1730)
    class_ = _make("Class",   0, 1730, 1900)
    issues = find_all_issues([therapy, commute, class_])

    total += 1
    hard_count = sum(1 for i in issues if i.type == IssueType.HARD_BUFFER)
    if hard_count == 2 and len(issues) == 2:
        passed += 1
        print(f"Test {total}: PASS | Therapy→Commute→Class chain finds 2 HARD_BUFFER issues")
    else:
        print(f"Test {total}: FAIL | got {[i.type.value for i in issues]}")

    # --- Scenario B: realistic week from earlier demo ---
    # Should now find OVERLAPS (3) AND any buffer issues between non-overlapping pairs.
    week = [
        _make("Study session", 0, 1600, 1700),  # Mon 4-5
        _make("Commute",       0, 1700, 1900),  # Mon 5-7  (back-to-back with Study)
        _make("School",        0, 1900, 2200),  # Mon 7-10 (back-to-back with Commute)
        _make("Therapy",       0, 1630, 1730),  # Mon 4:30-5:30 — OVERLAPS Study & Commute
        _make("Yoga",          1, 900, 1000),   # Tue
        _make("Team meeting",  2, 1400, 1500),  # Wed 2-3
        _make("Doctor appt",   2, 1430, 1530),  # Wed 2:30-3:30 — OVERLAPS Team meeting
        _make("Gym",           4, 600, 700),    # Fri morning
    ]
    issues = find_all_issues(week)

    total += 1
    overlap_count = sum(1 for i in issues if i.type == IssueType.OVERLAP)
    if overlap_count == 3:
        passed += 1
        print(f"Test {total}: PASS | Realistic week finds 3 OVERLAPS as expected")
    else:
        print(f"Test {total}: FAIL | expected 3 overlaps, got {overlap_count}")

    # --- Scenario C: total issue count for realistic week ---
    # Mon non-overlapping pairs: (Study, Commute) [0 gap → HARD], (Commute, School) [0 gap → HARD]
    # Mon overlapping pairs: (Study, Therapy), (Commute, Therapy), (Therapy, School pair?)
    #   Actually: Study 4-5, Therapy 4:30-5:30 → overlap
    #             Commute 5-7, Therapy 4:30-5:30 → overlap
    #             School 7-10, Therapy 4:30-5:30 → no overlap, gap=90 min, fine
    # Wed: (Team meeting, Doctor appt) overlap
    # Total: 3 OVERLAPS + 2 HARD_BUFFERs = 5 issues
    total += 1
    if len(issues) == 5:
        passed += 1
        print(f"Test {total}: PASS | Realistic week finds exactly 5 total issues (3 overlap + 2 hard buffer)")
    else:
        print(f"Test {total}: FAIL | expected 5 total issues, got {len(issues)}")
        for it in issues:
            print(f"           - {it.type.value}: {it.event_a.title} + {it.event_b.title}")

    print(f"{passed}/{total} realistic scenario tests passed\n")
    return passed, total


# =================================================================
# GROUP 7: Type validation
# =================================================================

def run_validation():
    print("=== find_all_issues — VALIDATION TESTS ===")

    real = _make("Real", 0, 1600, 1700)

    tests = [
        ("Non-list input rejected",
            lambda: find_all_issues("not a list"), TypeError),
        ("None rejected",
            lambda: find_all_issues(None), TypeError),
        ("Tuple rejected (must be a list)",
            lambda: find_all_issues((real, real)), TypeError),
        ("List with non-Event item rejected",
            lambda: find_all_issues([real, "not an event"]), TypeError),
        ("List with None item rejected",
            lambda: find_all_issues([real, None]), TypeError),
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
    """Run all find_all_issues tests."""
    p1, t1 = run_no_issues()
    p2, t2 = run_overlap()
    p3, t3 = run_hard_buffer()
    p4, t4 = run_soft_buffer()
    p5, t5 = run_severity()
    p6, t6 = run_realistic()
    p7, t7 = run_validation()
    return p1+p2+p3+p4+p5+p6+p7, t1+t2+t3+t4+t5+t6+t7


if __name__ == "__main__":
    run()
