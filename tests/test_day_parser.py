# ============================================================
# test_day_parser.py
#
# Tests for src/parsers/day_parser.py
# 8 tests proving case-insensitivity and whitespace tolerance.
# ============================================================

from src.parsers.day_parser import parse_day


# Each tuple: (input_string, expected_output)
# These tests prove the parser ignores case and surrounding whitespace.
case_tests = [
    ("monday", 0),
    ("Monday", 0),
    ("MONDAY", 0),
    ("MoNdAy", 0),
    ("mON", 0),
    ("  Monday  ", 0),    # whitespace tolerance
    ("FRI", 4),
    ("sUn", 6),
]


def run():
    """Run all day parser tests and return (passed, total)."""
    print("=== DAY PARSER TESTS (case-insensitivity) ===")
    passed = 0
    for i, (day_str, expected) in enumerate(case_tests, 1):
        result = parse_day(day_str)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"Test {i}: {status} | \"{day_str}\" | Expected: {expected}, Got: {result}")
    print(f"{passed}/{len(case_tests)} day parser tests passed\n")
    return passed, len(case_tests)


if __name__ == "__main__":
    run()
