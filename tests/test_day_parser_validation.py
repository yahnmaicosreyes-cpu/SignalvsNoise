# ============================================================
# test_day_parser_validation.py
#
# Tests that bad input to parse_day gets rejected cleanly.
# ============================================================

from src.parsers.day_parser import parse_day


# Each tuple: (input, expected_exception_type, description)
validation_tests = [
    # --- TYPE errors ---
    (None,        TypeError,  "None is not a string"),
    (5,           TypeError,  "Integer is not a string"),
    (["Monday"],  TypeError,  "List is not a string"),

    # --- EMPTINESS errors ---
    ("",     ValueError, "Empty string rejected"),
    ("   ",  ValueError, "Whitespace-only rejected"),

    # --- LENGTH errors ---
    ("M" * 51, ValueError, "String over 50 chars rejected"),

    # --- UNRECOGNIZED-DAY errors ---
    ("Funday",    ValueError, "Made-up day rejected"),
    ("mondya",    ValueError, "Typo rejected"),
    ("Mon Tue",   ValueError, "Two days in one string rejected"),
    ("mon\nday",  ValueError, "Newline injection rejected"),
]


def run():
    """Run all day parser validation tests and return (passed, total)."""
    print("=== DAY PARSER VALIDATION TESTS ===")
    passed = 0
    for i, (bad_input, expected_error, desc) in enumerate(validation_tests, 1):
        try:
            result = parse_day(bad_input)
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, but got result: {result}"
        except expected_error:
            status = "PASS"
            detail = f"raised {expected_error.__name__}"
            passed += 1
        except Exception as e:
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, got {type(e).__name__}: {e}"
        print(f"Test {i}: {status} | {desc} | {detail}")
    print(f"{passed}/{len(validation_tests)} day validation tests passed\n")
    return passed, len(validation_tests)


if __name__ == "__main__":
    run()
