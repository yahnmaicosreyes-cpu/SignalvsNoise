# ============================================================
# test_sort_and_group.py
#
# Tests for:
#   - The Day → Time → Priority → Severity sort order in find_all_issues
#   - The group_issues_by_day helper
# ============================================================

from src.models.event import Event
from src.models.issue import Issue, IssueType
from src.models.priority import Quadrant
from src.engine.conflict_checker import (
    find_all_issues,
    group_issues_by_day,
    _issue_sort_key,
)


def _make(title, day, start, end, important=None, urgent=None,
          hard=None, soft=None):
    """Helper to keep test events concise."""
    return Event(
        title=title, day=day, start=start, end=end,
        important=important, urgent=urgent,
        hard_buffer_minutes=hard, soft_buffer_minutes=soft,
    )


# =================================================================
# GROUP 1: SORT ORDER — verified using _issue_sort_key directly
#
# Why test the sort KEY rather than just the output order?
#   The output order is determined by the sort key. By testing the
#   key directly, we can isolate each level of the hierarchy
#   (day, time, priority, severity) and prove each one works.
#   Testing the output order alone makes it hard to know which
#   level is "doing the work" when things go right.
# =================================================================

def run_sort_key_levels():
    """Test each level of the sort key in isolation."""
    print("=== SORT KEY — EACH LEVEL ISOLATED ===")

    passed = 0
    total = 0

    # ----- Day is the primary sort -----
    # Two issues identical in every way EXCEPT day.
    # Day 0 (Mon) should sort before day 4 (Fri).
    mon_a = _make("a", 0, 900, 1000)
    mon_b = _make("b", 0, 930, 1030)
    fri_a = _make("a", 4, 900, 1000)
    fri_b = _make("b", 4, 930, 1030)
    mon_issue = find_all_issues([mon_a, mon_b])[0]
    fri_issue = find_all_issues([fri_a, fri_b])[0]

    total += 1
    if _issue_sort_key(mon_issue) < _issue_sort_key(fri_issue):
        passed += 1
        print(f"Test {total}: PASS | Day primary: Mon issue key < Fri issue key")
    else:
        print(f"Test {total}: FAIL | Mon key {_issue_sort_key(mon_issue)} >= Fri key {_issue_sort_key(fri_issue)}")

    # ----- Time is secondary (within same day) -----
    # Two issues same day, different start times.
    early_a = _make("a", 0, 900, 1000)
    early_b = _make("b", 0, 930, 1030)
    late_a = _make("a", 0, 1400, 1500)
    late_b = _make("b", 0, 1430, 1530)
    early_issue = find_all_issues([early_a, early_b])[0]
    late_issue = find_all_issues([late_a, late_b])[0]

    total += 1
    if _issue_sort_key(early_issue) < _issue_sort_key(late_issue):
        passed += 1
        print(f"Test {total}: PASS | Time secondary: 9am issue key < 2pm issue key (same day)")
    else:
        print(f"Test {total}: FAIL | early key {_issue_sort_key(early_issue)} >= late key {_issue_sort_key(late_issue)}")

    # ----- Priority is tertiary (within same day + time) -----
    # Two issues same day + same time, different priority.
    # SIGNAL (rank 1) should sort before NOISE (rank 4).
    sig_a = _make("a", 0, 900, 1000, important=True, urgent=False)
    sig_b = _make("b", 0, 900, 1000, important=True, urgent=False)
    noise_a = _make("a", 0, 900, 1000, important=False, urgent=False)
    noise_b = _make("b", 0, 900, 1000, important=False, urgent=False)
    sig_issue = find_all_issues([sig_a, sig_b])[0]
    noise_issue = find_all_issues([noise_a, noise_b])[0]

    total += 1
    if _issue_sort_key(sig_issue) < _issue_sort_key(noise_issue):
        passed += 1
        print(f"Test {total}: PASS | Priority tertiary: SIGNAL issue key < NOISE issue key (same day+time)")
    else:
        print(f"Test {total}: FAIL | sig key {_issue_sort_key(sig_issue)} >= noise key {_issue_sort_key(noise_issue)}")

    # ----- Severity is quaternary (within same day + time + priority) -----
    # Three issues same day, same start time, same priority (all UNSPECIFIED).
    # OVERLAP severity should sort before HARD_BUFFER before SOFT_BUFFER.
    ov_a = _make("a", 0, 900, 1000)
    ov_b = _make("b", 0, 930, 1030)        # overlap
    hb_a = _make("a", 0, 900, 1000)
    hb_b = _make("b", 0, 1005, 1100)       # 5 min gap → hard buffer violation
    sb_a = _make("a", 0, 900, 1000)
    sb_b = _make("b", 0, 1020, 1120)       # 20 min gap → soft buffer violation
    ov_issue = find_all_issues([ov_a, ov_b])[0]
    hb_issue = find_all_issues([hb_a, hb_b])[0]
    sb_issue = find_all_issues([sb_a, sb_b])[0]

    total += 1
    k_ov = _issue_sort_key(ov_issue)
    k_hb = _issue_sort_key(hb_issue)
    k_sb = _issue_sort_key(sb_issue)
    if k_ov < k_hb < k_sb:
        passed += 1
        print(f"Test {total}: PASS | Severity quaternary: OVERLAP < HARD_BUFFER < SOFT_BUFFER")
    else:
        print(f"Test {total}: FAIL | keys: overlap={k_ov}, hard={k_hb}, soft={k_sb}")

    print(f"{passed}/{total} sort-key-level tests passed\n")
    return passed, total


def run_sort_output_order():
    """End-to-end: build a scrambled input, verify find_all_issues output order."""
    print("=== SORT — END-TO-END OUTPUT ORDER ===")

    passed = 0
    total = 0

    # ----- Days come out in order despite scrambled input -----
    # Build one overlap pair per day, on Wed, Fri, Mon — in that order.
    # Expect Mon (0), Wed (2), Fri (4) in the output.
    wed_a = _make("wed-a", 2, 1000, 1100)
    wed_b = _make("wed-b", 2, 1030, 1130)
    fri_a = _make("fri-a", 4, 900, 1000)
    fri_b = _make("fri-b", 4, 930, 1030)
    mon_a = _make("mon-a", 0, 1600, 1700)
    mon_b = _make("mon-b", 0, 1630, 1730)
    issues = find_all_issues([wed_a, wed_b, fri_a, fri_b, mon_a, mon_b])
    days = [i.event_a.day for i in issues]

    total += 1
    if days == [0, 2, 4]:
        passed += 1
        print(f"Test {total}: PASS | Days output in order [0, 2, 4]")
    else:
        print(f"Test {total}: FAIL | got {days}")

    # ----- Within a day, times come out in order -----
    # Three overlap pairs on Monday at 5pm, 9am, 1pm. Expect 9am, 1pm, 5pm.
    evening_a = _make("ev-a", 0, 1700, 1800)
    evening_b = _make("ev-b", 0, 1730, 1830)
    morning_a = _make("mo-a", 0, 900, 1000)
    morning_b = _make("mo-b", 0, 930, 1030)
    afternoon_a = _make("af-a", 0, 1300, 1400)
    afternoon_b = _make("af-b", 0, 1330, 1430)
    issues = find_all_issues([
        evening_a, evening_b,
        morning_a, morning_b,
        afternoon_a, afternoon_b,
    ])
    starts = [i.event_a.start for i in issues]

    total += 1
    if starts == [900, 1300, 1700]:
        passed += 1
        print(f"Test {total}: PASS | Times within day output in order {starts}")
    else:
        print(f"Test {total}: FAIL | got {starts}")

    print(f"{passed}/{total} output-order tests passed\n")
    return passed, total


# =================================================================
# GROUP 2: group_issues_by_day
# =================================================================

def run_group_by_day():
    """Test the day-grouping helper."""
    print("=== group_issues_by_day TESTS ===")

    passed = 0
    total = 0

    # ----- Empty input → empty dict -----
    total += 1
    if group_issues_by_day([]) == {}:
        passed += 1
        print(f"Test {total}: PASS | Empty list → empty dict")
    else:
        print(f"Test {total}: FAIL | Empty list didn't produce empty dict")

    # ----- Single issue → one-key dict -----
    a = _make("A", 2, 1400, 1500)  # Wednesday
    b = _make("B", 2, 1430, 1530)
    issues = find_all_issues([a, b])
    grouped = group_issues_by_day(issues)

    total += 1
    if list(grouped.keys()) == [2] and len(grouped[2]) == 1:
        passed += 1
        print(f"Test {total}: PASS | Single Wed issue → dict with key 2 only")
    else:
        print(f"Test {total}: FAIL | got {dict((k, len(v)) for k, v in grouped.items())}")

    # ----- Multiple days → keys for those days only, others absent -----
    mon_a = _make("mon-A", 0, 900, 1000)
    mon_b = _make("mon-B", 0, 930, 1030)
    thu_a = _make("thu-A", 3, 1400, 1500)
    thu_b = _make("thu-B", 3, 1430, 1530)
    grouped = group_issues_by_day(find_all_issues([mon_a, mon_b, thu_a, thu_b]))

    total += 1
    if (set(grouped.keys()) == {0, 3}
        and len(grouped[0]) == 1
        and len(grouped[3]) == 1):
        passed += 1
        print(f"Test {total}: PASS | Mon+Thu only — quiet days absent from dict")
    else:
        print(f"Test {total}: FAIL | got keys {sorted(grouped.keys())}")

    # ----- Multiple issues per day → all collected, in time order -----
    e1 = _make("e1", 0, 900, 1000)
    e2 = _make("e2", 0, 930, 1030)
    e3 = _make("e3", 0, 1300, 1400)
    e4 = _make("e4", 0, 1330, 1430)
    e5 = _make("e5", 0, 1700, 1800)
    e6 = _make("e6", 0, 1730, 1830)
    grouped = group_issues_by_day(find_all_issues([e1, e2, e3, e4, e5, e6]))

    total += 1
    if list(grouped.keys()) == [0] and len(grouped[0]) == 3:
        passed += 1
        print(f"Test {total}: PASS | 3 issues on Monday → all in grouped[0]")
    else:
        print(f"Test {total}: FAIL | got {dict((k, len(v)) for k, v in grouped.items())}")

    total += 1
    if list(grouped.keys()) == [0]:
        start_times = [issue.event_a.start for issue in grouped[0]]
        if start_times == sorted(start_times):
            passed += 1
            print(f"Test {total}: PASS | Within-day issues in chronological order {start_times}")
        else:
            print(f"Test {total}: FAIL | not chronological: {start_times}")
    else:
        print(f"Test {total}: FAIL | setup invalid for time-order check")

    # ----- Validation: non-list input rejected -----
    total += 1
    try:
        group_issues_by_day("not a list")
        print(f"Test {total}: FAIL | expected TypeError")
    except TypeError:
        passed += 1
        print(f"Test {total}: PASS | Non-list input rejected")

    # ----- Validation: list with non-Issue item rejected -----
    total += 1
    try:
        group_issues_by_day([issues[0], "not an issue"])
        print(f"Test {total}: FAIL | expected TypeError")
    except TypeError:
        passed += 1
        print(f"Test {total}: PASS | Non-Issue item rejected")

    print(f"{passed}/{total} group_issues_by_day tests passed\n")
    return passed, total


def run():
    """Run all sort and group tests."""
    p1, t1 = run_sort_key_levels()
    p2, t2 = run_sort_output_order()
    p3, t3 = run_group_by_day()
    return p1 + p2 + p3, t1 + t2 + t3


if __name__ == "__main__":
    run()
