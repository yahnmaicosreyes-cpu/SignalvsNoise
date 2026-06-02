# ============================================================
# time_math.py
#
# Time arithmetic helpers. Lives in the engine package because
# the engine is what does math on already-clean numbers.
#
# Why this file exists:
#   Military-format times (1700, 1530, etc.) are NOT regular numbers.
#   1730 - 1700 = 30 happens to be right, but
#   1800 - 1530 = 270 is WRONG (real answer: 150 minutes).
#
#   Mistakes here would silently miscalculate every buffer in the
#   app. Better to do the math in one place, test it once, and
#   never think about it again.
# ============================================================


def to_total_minutes(military_time):
    """
    Convert a military-format time into total minutes since midnight.

    Examples:
        to_total_minutes(0)    →    0   (midnight)
        to_total_minutes(900)  →  540   (9:00 AM = 9 * 60)
        to_total_minutes(1530) →  930   (15:30 = 15*60 + 30)
        to_total_minutes(2359) → 1439   (23:59 = 23*60 + 59)

    Why this works:
        Military format packs hours and minutes into one number:
        the LAST TWO digits are minutes, everything else is hours.
        So 1530 → hours=15, minutes=30. We split, then convert.

    Args:
        military_time (int): A time in military format (0 to 2359).

    Returns:
        int: Total minutes since midnight.
    """

    # Last two digits = minutes. Everything else = hours.
    # We use integer division (//) and modulo (%) instead of string
    # parsing because integer math is faster and can't be tricked
    # by accidental string-typed inputs.
    hours = military_time // 100
    minutes = military_time % 100

    return hours * 60 + minutes


def minutes_between(earlier_time, later_time):
    """
    Return the number of minutes between two military-format times
    on the same day.

    Examples:
        minutes_between(1700, 1730) →  30   (5:00 PM to 5:30 PM)
        minutes_between(1530, 1800) → 150   (3:30 PM to 6:00 PM)
        minutes_between(1700, 1700) →   0   (touching, no gap)
        minutes_between(1730, 1700) → -30   (negative = later before earlier)

    A negative result means the "later" time is actually earlier
    than the "earlier" time. Calling code can use this to detect
    out-of-order sequences if needed.

    Args:
        earlier_time (int): The first time (e.g. when an event ends).
        later_time   (int): The second time (e.g. when the next event starts).

    Returns:
        int: Minutes between the two times. May be negative.
    """

    # Convert both to total-minutes-since-midnight, then subtract.
    # This is the correct way — direct subtraction of military
    # format would give wrong answers across the hour boundary.
    return to_total_minutes(later_time) - to_total_minutes(earlier_time)
