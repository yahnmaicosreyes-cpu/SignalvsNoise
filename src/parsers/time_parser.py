# ============================================================
# time_parser.py
#
# Translates human-friendly time strings into machine-friendly
# military-format integers (e.g. "4:30PM" → 1630).
#
# Now hardened with input validation:
#   - Type check (must be a string)
#   - Length check (max 50 characters)
#   - Emptiness check (rejects "" and whitespace-only)
#   - Format check (rejects ambiguous AM+PM, multiple colons)
#   - Range check (hours 0-23, minutes 0-59)
# ============================================================

from src.parsers._validators import validate_string_input


def parse_time(time_str):
    """
    Convert a human time string into a military-format integer.

    Accepts: "4:00PM", "4pm", "16:00", "9:00AM", "12:00AM", etc.
    Returns: An integer where the hundreds digits are hours and
             the tens/ones digits are minutes (e.g. 1630 = 16:30).

    Examples:
        parse_time("4:30PM")  → 1630
        parse_time("12:00AM") → 0     (midnight)
        parse_time("12:00PM") → 1200  (noon)

    Raises:
        TypeError  if input is not a string
        ValueError if input is empty, too long, malformed, or out of range
    """

    # ----- VALIDATION PIPELINE -----
    # Each step rejects a class of bad input before we try to parse.
    # If anything fails, we raise immediately ("fail fast") with a
    # message that names what went wrong.

    # Step 1-3: shared checks (type, length, emptiness).
    # Returns the stripped string so we don't strip again below.
    time_str = validate_string_input(time_str, "Time")

    # Force uppercase so "pm", "PM", and "Pm" all match.
    time_str = time_str.upper()

    # Step 4: format check — AM/PM must not both appear.
    # "4PMAM" is ambiguous; reject rather than silently picking one.
    is_pm = "PM" in time_str
    is_am = "AM" in time_str
    if is_pm and is_am:
        raise ValueError(
            f"Couldn't read time '{time_str}' — "
            f"can't contain both AM and PM"
        )

    # Strip the AM/PM letters out, leaving only digits and ":"
    digits_only = time_str.replace("AM", "").replace("PM", "")

    # Step 5: format check — at most one colon allowed.
    # "4:00:00PM" (with seconds) gets rejected here per design choice:
    # the engine works at minute precision, so accepting seconds would
    # falsely imply the app cares about them.
    if digits_only.count(":") > 1:
        raise ValueError(
            f"Couldn't read time '{time_str}' — "
            f"too many ':' characters (seconds are not supported)"
        )

    # Split into hours and minutes.
    if ":" in digits_only:
        hours_str, minutes_str = digits_only.split(":")
    else:
        # Shorthand like "4pm" — no colon, no minutes
        hours_str = digits_only
        minutes_str = "0"

    # Step 6: format check — both parts must be pure digits.
    # int() would raise its own error here, but we wrap it with a
    # clearer message that includes the original input.
    if not hours_str.isdigit() or not minutes_str.isdigit():
        raise ValueError(
            f"Couldn't read time '{time_str}' — "
            f"hours and minutes must be numbers"
        )

    hours = int(hours_str)
    minutes = int(minutes_str)

    # Step 7: range check — minutes must be 0-59.
    # This is the check that catches "4:99PM" silently producing 1699.
    if minutes < 0 or minutes > 59:
        raise ValueError(
            f"Couldn't read time '{time_str}' — "
            f"minutes must be between 0 and 59 (got {minutes})"
        )

    # Step 8: range check — hours must be reasonable.
    # If AM/PM was specified, hours must be 1-12 (12-hour clock).
    # If no AM/PM, hours must be 0-23 (24-hour clock).
    if is_am or is_pm:
        if hours < 1 or hours > 12:
            raise ValueError(
                f"Couldn't read time '{time_str}' — "
                f"with AM/PM, hour must be 1-12 (got {hours})"
            )
    else:
        if hours < 0 or hours > 23:
            raise ValueError(
                f"Couldn't read time '{time_str}' — "
                f"hour must be 0-23 (got {hours})"
            )

    # ----- VALIDATION COMPLETE — original parsing logic below -----

    # PM rule: add 12 to convert to 24-hour format.
    # Exception: 12pm is already noon (12), so we DON'T add 12 to it.
    if is_pm and hours != 12:
        hours += 12

    # AM rule: 12am is midnight, which is 0 in 24-hour format.
    # All other AM hours stay as-is (1am stays 1, 9am stays 9).
    if is_am and hours == 12:
        hours = 0

    # Combine into military format.
    # Example: 16 hours, 30 minutes → 16 * 100 + 30 = 1630
    return hours * 100 + minutes
