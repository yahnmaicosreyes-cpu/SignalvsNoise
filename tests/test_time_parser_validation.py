# ============================================================
# test_time_parser_validation.py
#
# Tests that bad input to parse_time gets rejected cleanly with
# the right kind of error.
#
# Each test passes when the expected error IS raised. If the
# parser silently accepts bad input, the test fails — that's the
# whole point.
# ============================================================

from src.parsers.time_parser import parse_time


# Each tuple: (input, expected_exception_type, description)
# We don't check exact error messages — only the error TYPE — because
# message text is allowed to evolve without breaking tests.
validation_tests = [
    # --- TYPE errors (TypeError) ---
    (None,    TypeError,  "None is not a string"),
    (12345,   TypeError,  "Integer is not a string"),
    (["4pm"], TypeError,  "List is not a string"),

    # --- EMPTINESS errors (ValueError) ---
    ("",       ValueError, "Empty string rejected"),
    ("   ",    ValueError, "Whitespace-only rejected"),

    # --- LENGTH errors (ValueError) ---
    ("4" * 51, ValueError, "String over 50 chars rejected"),

    # --- FORMAT errors (ValueError) ---
    ("banana",     ValueError, "Non-numeric string rejected"),
    ("4PMAM",      ValueError, "Both AM and PM rejected as ambiguous"),
    ("4:00:00PM",  ValueError, "Seconds rejected"),
    ("4:00:00",    ValueError, "Seconds rejected (24h format)"),
    ("abc:def",    ValueError, "Non-numeric hour/minute rejected"),

    # --- RANGE errors (ValueError) ---
    # These are the silent-success cases from the probe — now they fail loudly.
    ("25:00",  ValueError, "Hour 25 rejected (24h format)"),
    ("99",     ValueError, "Hour 99 rejected"),
    ("4:99PM", ValueError, "Minutes 99 rejected"),
    ("4:60PM", ValueError, "Minutes 60 rejected (must be 0-59)"),
    ("0PM",    ValueError, "Hour 0 with PM rejected (12h format is 1-12)"),
    ("13PM",   ValueError, "Hour 13 with PM rejected (12h format is 1-12)"),
]


def run():
    """Run all time parser validation tests and return (passed, total)."""
    print("=== TIME PARSER VALIDATION TESTS ===")
    passed = 0
    for i, (bad_input, expected_error, desc) in enumerate(validation_tests, 1):
        try:
            result = parse_time(bad_input)
            # If we get here, the parser accepted bad input — that's a FAIL.
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, but got result: {result}"
        except expected_error as e:
            # Got the right kind of error → PASS
            status = "PASS"
            detail = f"raised {expected_error.__name__}"
            passed += 1
        except Exception as e:
            # Got an error, but the WRONG kind → FAIL
            # (This catches cases like a TypeError sneaking through where
            # we expected a ValueError, which would mean validation has a hole.)
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, got {type(e).__name__}: {e}"
        print(f"Test {i}: {status} | {desc} | {detail}")
    print(f"{passed}/{len(validation_tests)} time validation tests passed\n")
    return passed, len(validation_tests)


if __name__ == "__main__":
    run()
