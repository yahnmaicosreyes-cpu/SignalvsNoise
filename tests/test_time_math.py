# ============================================================
# test_time_math.py
#
# Tests for src/engine/time_math.py.
#
# These functions are tiny but critical — every buffer calculation
# in the app depends on them. Bugs here would silently miscalculate
# every transition gap. Better to over-test these.
# ============================================================

from src.engine.time_math import to_total_minutes, minutes_between


def run_to_total_minutes():
    """Test to_total_minutes. Returns (passed, total)."""
    print("=== to_total_minutes TESTS ===")

    # Each tuple: (input military time, expected total minutes, description)
    tests = [
        (0,    0,    "Midnight = 0 minutes"),
        (100,  60,   "1:00 AM = 60 minutes"),
        (900,  540,  "9:00 AM = 540 minutes"),
        (1200, 720,  "Noon = 720 minutes"),
        (1530, 930,  "3:30 PM = 930 minutes"),
        (1700, 1020, "5:00 PM = 1020 minutes"),
        (1800, 1080, "6:00 PM = 1080 minutes"),
        (2359, 1439, "11:59 PM = 1439 minutes (last minute of day)"),
    ]

    passed = 0
    for i, (input_time, expected, desc) in enumerate(tests, 1):
        result = to_total_minutes(input_time)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"Test {i}: {status} | {desc} | Got: {result}, Expected: {expected}")
    print(f"{passed}/{len(tests)} to_total_minutes tests passed\n")
    return passed, len(tests)


def run_minutes_between():
    """Test minutes_between. Returns (passed, total)."""
    print("=== minutes_between TESTS ===")

    # Each tuple: (earlier, later, expected, description)
    tests = [
        # --- Within-hour cases (the easy ones) ---
        (1700, 1730, 30,
            "5:00 PM to 5:30 PM = 30 min"),
        (900, 930, 30,
            "9:00 AM to 9:30 AM = 30 min"),

        # --- Across-hour cases (where naive subtraction fails) ---
        # If we naively did 1800 - 1530 we'd get 270. Real answer: 150.
        (1530, 1800, 150,
            "3:30 PM to 6:00 PM = 150 min (NOT 270 — would be naive bug)"),
        (1700, 1800, 60,
            "5:00 PM to 6:00 PM = 60 min (NOT 100 — would be naive bug)"),

        # --- Zero gap (touching events) ---
        (1700, 1700, 0,
            "Same time = 0 min"),

        # --- Negative gap (out-of-order) ---
        (1730, 1700, -30,
            "5:30 PM to 5:00 PM = -30 (out of order)"),

        # --- Edge cases ---
        (0, 2359, 1439,
            "Midnight to 11:59 PM = 1439 min (full day minus 1)"),
        (0, 60, 60,
            "Midnight to 1:00 AM = 60 min"),
        (1159, 1200, 1,
            "11:59 AM to noon = 1 min"),
    ]

    passed = 0
    for i, (earlier, later, expected, desc) in enumerate(tests, 1):
        result = minutes_between(earlier, later)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"Test {i}: {status} | {desc} | Got: {result}")
    print(f"{passed}/{len(tests)} minutes_between tests passed\n")
    return passed, len(tests)


def run():
    """Run all time math tests. Returns (passed, total)."""
    p1, t1 = run_to_total_minutes()
    p2, t2 = run_minutes_between()
    return p1 + p2, t1 + t2


if __name__ == "__main__":
    run()
