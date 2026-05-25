# ============================================================
# test_priority.py
#
# Tests for src/models/priority.py — the Quadrant enum and the
# resolve_quadrant function that maps (important, urgent) to a Quadrant.
# ============================================================

from src.models.priority import Quadrant, resolve_quadrant


def run_resolve_all_cases():
    """
    Test all 9 input combinations of (important, urgent).
    Each is True, False, or None — 3x3 = 9 cases.
    Returns (passed, total).
    """
    print("=== resolve_quadrant — ALL INPUT CASES ===")

    # Each tuple: (important, urgent, expected_quadrant, description)
    tests = [
        # The four "fully specified" quadrants
        (True,  False, Quadrant.SIGNAL,       "important=T, urgent=F → SIGNAL"),
        (True,  True,  Quadrant.URGENT,       "important=T, urgent=T → URGENT"),
        (False, True,  Quadrant.INTERRUPTION, "important=F, urgent=T → INTERRUPTION"),
        (False, False, Quadrant.NOISE,        "important=F, urgent=F → NOISE"),

        # Partial assignments — should all be UNSPECIFIED
        (True,  None,  Quadrant.UNSPECIFIED, "important=T, urgent=None → UNSPECIFIED"),
        (False, None,  Quadrant.UNSPECIFIED, "important=F, urgent=None → UNSPECIFIED"),
        (None,  True,  Quadrant.UNSPECIFIED, "important=None, urgent=T → UNSPECIFIED"),
        (None,  False, Quadrant.UNSPECIFIED, "important=None, urgent=F → UNSPECIFIED"),

        # No assignment at all
        (None,  None,  Quadrant.UNSPECIFIED, "both None → UNSPECIFIED"),
    ]

    passed = 0
    for i, (important, urgent, expected, desc) in enumerate(tests, 1):
        result = resolve_quadrant(important, urgent)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"Test {i}: {status} | {desc} | Got: {result.name}")
    print(f"{passed}/{len(tests)} resolve_quadrant tests passed\n")
    return passed, len(tests)


def run_quadrant_ordering():
    """
    Test that the Quadrant enum values produce the correct sort order:
    SIGNAL=1 < URGENT=2 < INTERRUPTION=3 < NOISE=4 < UNSPECIFIED=5
    Returns (passed, total).
    """
    print("=== Quadrant — ORDERING (user's custom hierarchy) ===")

    tests = [
        ("SIGNAL value is 1 (highest priority)",
            Quadrant.SIGNAL.value == 1),
        ("URGENT value is 2",
            Quadrant.URGENT.value == 2),
        ("INTERRUPTION value is 3",
            Quadrant.INTERRUPTION.value == 3),
        ("NOISE value is 4",
            Quadrant.NOISE.value == 4),
        ("UNSPECIFIED value is 5 (lowest priority)",
            Quadrant.UNSPECIFIED.value == 5),
        ("Sorting by value puts SIGNAL first",
            sorted([Quadrant.NOISE, Quadrant.SIGNAL, Quadrant.URGENT],
                   key=lambda q: q.value)[0] == Quadrant.SIGNAL),
        ("Sorting puts UNSPECIFIED last",
            sorted([Quadrant.UNSPECIFIED, Quadrant.SIGNAL, Quadrant.NOISE],
                   key=lambda q: q.value)[-1] == Quadrant.UNSPECIFIED),
    ]

    passed = 0
    for i, (desc, condition) in enumerate(tests, 1):
        status = "PASS" if condition else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"Test {i}: {status} | {desc}")
    print(f"{passed}/{len(tests)} quadrant ordering tests passed\n")
    return passed, len(tests)


def run():
    """Run all priority model tests."""
    p1, t1 = run_resolve_all_cases()
    p2, t2 = run_quadrant_ordering()
    return p1 + p2, t1 + t2


if __name__ == "__main__":
    run()
