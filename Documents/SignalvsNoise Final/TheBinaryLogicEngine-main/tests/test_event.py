# ============================================================
# test_event.py
#
# Tests for src/models/event.py
#
# Two test groups:
#   1. Happy-path tests — Events that should construct successfully
#   2. Validation tests — bad input that should be rejected
#
# As with the parser validation tests, we check that the right
# TYPE of error is raised, not the exact message text.
# ============================================================

from src.models.event import Event


# =================================================================
# GROUP 1: HAPPY PATH — these constructions should all SUCCEED
# =================================================================

def run_happy_path():
    """
    Construct Events that should work, and verify their fields.
    Returns (passed, total).
    """
    print("=== EVENT HAPPY PATH TESTS ===")

    # Each test is (description, function-that-builds-event, expected fields).
    # Using lambdas so a test failing to construct doesn't crash the whole run.
    tests = [
        (
            "Direct construction with valid numbers",
            lambda: Event(title="Study", day=0, start=1600, end=1700),
            {"title": "Study", "day": 0, "start": 1600, "end": 1700},
        ),
        (
            "from_strings with full names",
            lambda: Event.from_strings("Yoga", "Wednesday", "9:00AM", "10:00AM"),
            {"title": "Yoga", "day": 2, "start": 900, "end": 1000},
        ),
        (
            "from_strings with abbreviations and lowercase",
            lambda: Event.from_strings("Lunch", "fri", "12:00pm", "1:00pm"),
            {"title": "Lunch", "day": 4, "start": 1200, "end": 1300},
        ),
        (
            "from_strings with mixed-case day",
            lambda: Event.from_strings("Class", "MoNdAy", "7:00PM", "10:00PM"),
            {"title": "Class", "day": 0, "start": 1900, "end": 2200},
        ),
        (
            "Title with leading/trailing whitespace gets stripped",
            lambda: Event(title="  Study  ", day=0, start=1600, end=1700),
            {"title": "Study", "day": 0, "start": 1600, "end": 1700},
        ),
        (
            "Edge of day — late evening event",
            lambda: Event(title="Late call", day=5, start=2300, end=2359),
            {"title": "Late call", "day": 5, "start": 2300, "end": 2359},
        ),
        (
            "Edge of day — start of day event",
            lambda: Event(title="Early run", day=1, start=0, end=600),
            {"title": "Early run", "day": 1, "start": 0, "end": 600},
        ),
    ]

    passed = 0
    for i, (desc, builder, expected) in enumerate(tests, 1):
        try:
            event = builder()
            # Compare every expected field against the actual event.
            mismatches = [
                f"{k}={getattr(event, k)!r} (expected {v!r})"
                for k, v in expected.items()
                if getattr(event, k) != v
            ]
            if mismatches:
                status = "FAIL"
                detail = f"field mismatch: {', '.join(mismatches)}"
            else:
                status = "PASS"
                detail = "all fields match"
                passed += 1
        except Exception as e:
            status = "FAIL"
            detail = f"unexpected {type(e).__name__}: {e}"
        print(f"Test {i}: {status} | {desc} | {detail}")

    print(f"{passed}/{len(tests)} happy-path tests passed\n")
    return passed, len(tests)


# =================================================================
# GROUP 2: VALIDATION — these constructions should all FAIL
# =================================================================

def run_validation():
    """
    Try to construct invalid Events. Each should raise the expected error.
    Returns (passed, total).
    """
    print("=== EVENT VALIDATION TESTS ===")

    # Each test is (description, function-that-builds-event, expected_error).
    tests = [
        # --- TITLE failures ---
        (
            "Empty title rejected",
            lambda: Event(title="", day=0, start=1600, end=1700),
            ValueError,
        ),
        (
            "Whitespace-only title rejected",
            lambda: Event(title="   ", day=0, start=1600, end=1700),
            ValueError,
        ),
        (
            "Non-string title rejected",
            lambda: Event(title=123, day=0, start=1600, end=1700),
            TypeError,
        ),
        (
            "Title over 200 chars rejected",
            lambda: Event(title="x" * 201, day=0, start=1600, end=1700),
            ValueError,
        ),

        # --- DAY failures ---
        (
            "Day below range (-1) rejected",
            lambda: Event(title="X", day=-1, start=1600, end=1700),
            ValueError,
        ),
        (
            "Day above range (7) rejected",
            lambda: Event(title="X", day=7, start=1600, end=1700),
            ValueError,
        ),
        (
            "Day as string rejected",
            lambda: Event(title="X", day="Monday", start=1600, end=1700),
            TypeError,
        ),
        (
            "Day as boolean rejected (True == 1 in Python)",
            lambda: Event(title="X", day=True, start=1600, end=1700),
            TypeError,
        ),
        (
            "Day as None rejected",
            lambda: Event(title="X", day=None, start=1600, end=1700),
            TypeError,
        ),

        # --- TIME failures ---
        (
            "Negative start time rejected",
            lambda: Event(title="X", day=0, start=-1, end=1700),
            ValueError,
        ),
        (
            "Start time over 2359 rejected",
            lambda: Event(title="X", day=0, start=2400, end=2500),
            ValueError,
        ),
        (
            "Invalid minutes in start (1099 → minutes=99) rejected",
            lambda: Event(title="X", day=0, start=1099, end=1700),
            ValueError,
        ),
        (
            "Invalid minutes in end (1660 → minutes=60) rejected",
            lambda: Event(title="X", day=0, start=1600, end=1660),
            ValueError,
        ),
        (
            "Start as string rejected",
            lambda: Event(title="X", day=0, start="1600", end=1700),
            TypeError,
        ),

        # --- LOGICAL failures ---
        (
            "End before start rejected",
            lambda: Event(title="X", day=0, start=1700, end=1600),
            ValueError,
        ),
        (
            "End equal to start (zero-length) rejected",
            lambda: Event(title="X", day=0, start=1600, end=1600),
            ValueError,
        ),

        # --- from_strings failures (parser errors propagate) ---
        (
            "from_strings with bad day rejected",
            lambda: Event.from_strings("X", "Funday", "4:00PM", "5:00PM"),
            ValueError,
        ),
        (
            "from_strings with bad time rejected",
            lambda: Event.from_strings("X", "Monday", "25:00", "26:00"),
            ValueError,
        ),
        (
            "from_strings with end before start rejected",
            lambda: Event.from_strings("X", "Monday", "5:00PM", "4:00PM"),
            ValueError,
        ),
    ]

    passed = 0
    for i, (desc, builder, expected_error) in enumerate(tests, 1):
        try:
            event = builder()
            # Construction succeeded — that's a FAIL for a validation test.
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, but Event was created: {event}"
        except expected_error:
            status = "PASS"
            detail = f"raised {expected_error.__name__}"
            passed += 1
        except Exception as e:
            # Wrong type of error — counts as a fail (validation has a hole).
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, got {type(e).__name__}: {e}"
        print(f"Test {i}: {status} | {desc} | {detail}")

    print(f"{passed}/{len(tests)} validation tests passed\n")
    return passed, len(tests)


def run():
    """Run all event tests. Returns (passed, total)."""
    h_passed, h_total = run_happy_path()
    v_passed, v_total = run_validation()
    b_passed, b_total = run_buffer_fields()
    p_passed, p_total = run_priority_fields()
    return (
        h_passed + v_passed + b_passed + p_passed,
        h_total + v_total + b_total + p_total,
    )


def run_buffer_fields():
    """
    Tests for the optional hard_buffer_minutes and soft_buffer_minutes
    fields on Event. Returns (passed, total).
    """
    print("=== EVENT BUFFER FIELD TESTS ===")

    # --- Happy paths: valid buffer values should be accepted ---
    happy_tests = [
        ("Default buffers (None) accepted",
            lambda: Event(title="X", day=0, start=1600, end=1700),
            {"hard_buffer_minutes": None, "soft_buffer_minutes": None}),
        ("Hard buffer set explicitly",
            lambda: Event(title="X", day=0, start=1600, end=1700, hard_buffer_minutes=30),
            {"hard_buffer_minutes": 30, "soft_buffer_minutes": None}),
        ("Soft buffer set explicitly",
            lambda: Event(title="X", day=0, start=1600, end=1700, soft_buffer_minutes=45),
            {"hard_buffer_minutes": None, "soft_buffer_minutes": 45}),
        ("Both buffers set",
            lambda: Event(title="X", day=0, start=1600, end=1700,
                          hard_buffer_minutes=15, soft_buffer_minutes=30),
            {"hard_buffer_minutes": 15, "soft_buffer_minutes": 30}),
        ("Zero buffer explicitly allowed (back-to-back Zoom)",
            lambda: Event(title="X", day=0, start=1600, end=1700, hard_buffer_minutes=0),
            {"hard_buffer_minutes": 0, "soft_buffer_minutes": None}),
        ("from_strings supports buffer fields",
            lambda: Event.from_strings("X", "Mon", "4:00PM", "5:00PM",
                                        hard_buffer_minutes=20, soft_buffer_minutes=40),
            {"hard_buffer_minutes": 20, "soft_buffer_minutes": 40}),
    ]

    passed = 0
    for i, (desc, builder, expected) in enumerate(happy_tests, 1):
        try:
            event = builder()
            mismatches = [
                f"{k}={getattr(event, k)!r} (expected {v!r})"
                for k, v in expected.items()
                if getattr(event, k) != v
            ]
            if mismatches:
                status = "FAIL"
                detail = f"field mismatch: {', '.join(mismatches)}"
            else:
                status = "PASS"
                detail = "fields match"
                passed += 1
        except Exception as e:
            status = "FAIL"
            detail = f"unexpected {type(e).__name__}: {e}"
        print(f"Test {i}: {status} | {desc} | {detail}")

    # --- Validation: bad buffer values should be rejected ---
    bad_tests = [
        ("Negative hard buffer rejected",
            lambda: Event(title="X", day=0, start=1600, end=1700, hard_buffer_minutes=-1),
            ValueError),
        ("Negative soft buffer rejected",
            lambda: Event(title="X", day=0, start=1600, end=1700, soft_buffer_minutes=-5),
            ValueError),
        ("Buffer over 720 (likely typo) rejected",
            lambda: Event(title="X", day=0, start=1600, end=1700, hard_buffer_minutes=1500),
            ValueError),
        ("String buffer rejected",
            lambda: Event(title="X", day=0, start=1600, end=1700, hard_buffer_minutes="15"),
            TypeError),
        ("Boolean buffer rejected (True == 1 trap)",
            lambda: Event(title="X", day=0, start=1600, end=1700, soft_buffer_minutes=True),
            TypeError),
        ("Float buffer rejected",
            lambda: Event(title="X", day=0, start=1600, end=1700, hard_buffer_minutes=15.5),
            TypeError),
    ]

    offset = len(happy_tests)
    for i, (desc, builder, expected_error) in enumerate(bad_tests, 1):
        try:
            event = builder()
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, but Event was created"
        except expected_error:
            status = "PASS"
            detail = f"raised {expected_error.__name__}"
            passed += 1
        except Exception as e:
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, got {type(e).__name__}: {e}"
        print(f"Test {offset + i}: {status} | {desc} | {detail}")

    total = len(happy_tests) + len(bad_tests)
    print(f"{passed}/{total} buffer field tests passed\n")
    return passed, total


def run_priority_fields():
    """
    Tests for the optional important / urgent priority fields on Event.
    Also tests the get_quadrant() convenience accessor.
    Returns (passed, total).
    """
    from src.models.priority import Quadrant

    print("=== EVENT PRIORITY FIELD TESTS ===")

    # --- Happy paths: valid values + get_quadrant() output ---
    happy_tests = [
        ("Default (no priority set) → UNSPECIFIED",
            lambda: Event(title="X", day=0, start=1600, end=1700),
            Quadrant.UNSPECIFIED),
        ("important=T, urgent=F → SIGNAL",
            lambda: Event(title="X", day=0, start=1600, end=1700,
                          important=True, urgent=False),
            Quadrant.SIGNAL),
        ("important=T, urgent=T → URGENT",
            lambda: Event(title="X", day=0, start=1600, end=1700,
                          important=True, urgent=True),
            Quadrant.URGENT),
        ("important=F, urgent=T → INTERRUPTION",
            lambda: Event(title="X", day=0, start=1600, end=1700,
                          important=False, urgent=True),
            Quadrant.INTERRUPTION),
        ("important=F, urgent=F → NOISE",
            lambda: Event(title="X", day=0, start=1600, end=1700,
                          important=False, urgent=False),
            Quadrant.NOISE),
        ("Only important set → UNSPECIFIED",
            lambda: Event(title="X", day=0, start=1600, end=1700,
                          important=True),
            Quadrant.UNSPECIFIED),
        ("Only urgent set → UNSPECIFIED",
            lambda: Event(title="X", day=0, start=1600, end=1700,
                          urgent=False),
            Quadrant.UNSPECIFIED),
        ("from_strings supports priority fields",
            lambda: Event.from_strings("X", "Mon", "4:00PM", "5:00PM",
                                        important=True, urgent=False),
            Quadrant.SIGNAL),
    ]

    passed = 0
    for i, (desc, builder, expected_quadrant) in enumerate(happy_tests, 1):
        try:
            event = builder()
            result = event.get_quadrant()
            if result == expected_quadrant:
                status = "PASS"
                detail = f"get_quadrant() = {result.name}"
                passed += 1
            else:
                status = "FAIL"
                detail = f"expected {expected_quadrant.name}, got {result.name}"
        except Exception as e:
            status = "FAIL"
            detail = f"unexpected {type(e).__name__}: {e}"
        print(f"Test {i}: {status} | {desc} | {detail}")

    # --- Validation: bad values for important/urgent should reject ---
    # Note: integers 1 and 0 are rejected because isinstance(1, bool) is False.
    # This is the right call — Python's int-is-not-bool rule protects us
    # from `important=1` silently becoming SIGNAL.
    bad_tests = [
        ("important as string rejected",
            lambda: Event(title="X", day=0, start=1600, end=1700, important="yes"),
            TypeError),
        ("urgent as string rejected",
            lambda: Event(title="X", day=0, start=1600, end=1700, urgent="no"),
            TypeError),
        ("important as integer rejected (1 is not True)",
            lambda: Event(title="X", day=0, start=1600, end=1700, important=1),
            TypeError),
        ("urgent as integer rejected (0 is not False)",
            lambda: Event(title="X", day=0, start=1600, end=1700, urgent=0),
            TypeError),
        ("important as list rejected",
            lambda: Event(title="X", day=0, start=1600, end=1700, important=[]),
            TypeError),
    ]

    offset = len(happy_tests)
    for i, (desc, builder, expected_error) in enumerate(bad_tests, 1):
        try:
            event = builder()
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, but Event was created"
        except expected_error:
            status = "PASS"
            detail = f"raised {expected_error.__name__}"
            passed += 1
        except Exception as e:
            status = "FAIL"
            detail = f"expected {expected_error.__name__}, got {type(e).__name__}"
        print(f"Test {offset + i}: {status} | {desc} | {detail}")

    total = len(happy_tests) + len(bad_tests)
    print(f"{passed}/{total} priority field tests passed\n")
    return passed, total


if __name__ == "__main__":
    run()
