# ============================================================
# test_conflict_checker.py
#
# Tests for src/engine/conflict_checker.py
# 18 tests total: 10 original same-day + 8 day-aware.
# ============================================================

from src.engine.conflict_checker import has_conflict


# --- ORIGINAL 10 SAME-DAY TESTS ---
# Format: (day1, start1, end1, day2, start2, end2, expected)
# We pass day=0 for both events to preserve the original test intent
# (these tests existed before day-awareness was added).
same_day_tests = [
    (0, 1300, 1400, 0, 1330, 1430, True),
    (0, 900,  1000, 0, 1100, 1200, False),
    (0, 900,  1000, 0, 1000, 1100, False),   # touching at boundary, not overlapping
    (0, 1300, 1400, 0, 1300, 1400, True),
    (0, 900,  1700, 0, 1200, 1300, True),    # one event fully inside another
    (0, 1200, 1300, 0, 900,  1700, True),    # same as above, reversed order
    (0, 1300, 1400, 0, 1359, 1500, True),    # 1-minute overlap
    (0, 1400, 1500, 0, 1500, 1600, False),
    (0, 1500, 1600, 0, 1300, 1400, False),
    (0, 2200, 2359, 0, 2300, 2400, True),    # late-night overlap
]


# --- 8 DAY-AWARE TESTS ---
# Format: (day1, start1, end1, day2, start2, end2, expected, description)
# These prove the engine treats different days as never-conflicting.
day_aware_tests = [
    (0, 1300, 1400, 0, 1330, 1430, True,  "Mon: overlapping → conflict"),
    (0, 1300, 1400, 1, 1300, 1400, False, "Mon vs Tue, same times → no conflict"),
    (0, 900,  1000, 0, 1100, 1200, False, "Mon: no overlap → no conflict"),
    (2, 1400, 1500, 2, 1500, 1600, False, "Wed: touching → no conflict"),
    (5, 2200, 2359, 5, 2300, 2400, True,  "Sat late-night overlap → conflict"),
    (0, 900,  1700, 6, 900,  1700, False, "Mon vs Sun, identical times → no conflict"),
    (3, 1300, 1400, 3, 1300, 1400, True,  "Thu: identical times → conflict"),
    (1, 900,  1000, 2, 959,  1100, False, "Tue 9-10 vs Wed 9:59-11 → no conflict"),
]


def run():
    """Run all conflict checker tests and return (passed, total)."""
    total_passed = 0
    total_tests = 0

    print("=== CONFLICT LOGIC TESTS (same-day) ===")
    for i, (d1, s1, e1, d2, s2, e2, expected) in enumerate(same_day_tests, 1):
        result = has_conflict(d1, s1, e1, d2, s2, e2)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            total_passed += 1
        print(f"Test {i}: {status} | ({s1}-{e1}) vs ({s2}-{e2}) | Expected: {expected}, Got: {result}")
    total_tests += len(same_day_tests)
    print(f"{total_passed}/{len(same_day_tests)} same-day tests passed\n")

    print("=== DAY-AWARE CONFLICT TESTS ===")
    section_passed = 0
    for i, (d1, s1, e1, d2, s2, e2, expected, desc) in enumerate(day_aware_tests, 1):
        result = has_conflict(d1, s1, e1, d2, s2, e2)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            section_passed += 1
        print(f"Test {i}: {status} | {desc} | Expected: {expected}, Got: {result}")
    total_passed += section_passed
    total_tests += len(day_aware_tests)
    print(f"{section_passed}/{len(day_aware_tests)} day-aware tests passed\n")

    return total_passed, total_tests


if __name__ == "__main__":
    run()
