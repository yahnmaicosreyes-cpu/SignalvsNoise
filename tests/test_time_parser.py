# ============================================================
# test_time_parser.py
#
# Tests for src/parsers/time_parser.py
# 10 tests covering normal cases and the AM/PM edge cases.
# ============================================================

# This import path works because we run tests from the project root.
# The 'src.parsers.time_parser' path mirrors the folder structure.
from src.parsers.time_parser import parse_time


# Each tuple: (input_string, expected_output)
parser_tests = [
    ("4:00PM", 1600),
    ("4pm", 1600),
    ("4:30pm", 1630),
    ("12:00PM", 1200),    # noon edge case
    ("12:00AM", 0),       # midnight edge case
    ("7:00PM", 1900),
    ("16:00", 1600),      # already in 24-hour format
    ("9:00AM", 900),
    ("11:59PM", 2359),    # last minute of the day
    ("1:00am", 100),
]


def run():
    """Run all time parser tests and return (passed, total)."""
    print("=== TIME PARSER TESTS ===")
    passed = 0
    for i, (time_str, expected) in enumerate(parser_tests, 1):
        result = parse_time(time_str)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"Test {i}: {status} | \"{time_str}\" | Expected: {expected}, Got: {result}")
    print(f"{passed}/{len(parser_tests)} time parser tests passed\n")
    return passed, len(parser_tests)


# Allow this file to be run on its own OR imported by a master runner.
if __name__ == "__main__":
    run()
