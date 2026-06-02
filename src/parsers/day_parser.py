# ============================================================
# day_parser.py
#
# Translates human-friendly day strings into integers where
# Monday = 0 and Sunday = 6 (matching Python's datetime.weekday()).
#
# Now hardened with input validation:
#   - Type check (must be a string)
#   - Length check (max 50 characters)
#   - Emptiness check (rejects "" and whitespace-only)
#   - The day-name check that was already here stays as-is.
# ============================================================

from src.parsers._validators import validate_string_input


def parse_day(day_str):
    """
    Convert a human day string into a number (Monday=0 ... Sunday=6).

    Behavior:
        - Case-insensitive  ("Monday" == "MONDAY" == "mOnDaY")
        - Whitespace-tolerant ("  monday  " works)
        - Accepts common abbreviations (mon, tue, tues, wed, thu, thur, etc.)
        - Fails LOUDLY on unknown input — raises ValueError.
          We chose this over returning -1 or None because silent failures
          hide bugs. Loud failures force them into the open.

    Examples:
        parse_day("Monday") → 0
        parse_day("FRI")    → 4
        parse_day("Funday") → raises ValueError

    Raises:
        TypeError  if input is not a string
        ValueError if input is empty, too long, or not a recognized day
    """

    # ----- VALIDATION PIPELINE -----
    # Step 1-3: shared checks (type, length, emptiness).
    # Returns the stripped string so we skip re-stripping.
    day_str = validate_string_input(day_str, "Day")

    # Force lowercase so the dictionary lookup matches any capitalization.
    day_str = day_str.lower()

    # ----- DAY-NAME LOOKUP -----
    # Numbers chosen to match Python's built-in datetime.weekday(),
    # which means we won't need a translator when integrating later.
    day_map = {
        "monday": 0,    "mon": 0,
        "tuesday": 1,   "tue": 1,    "tues": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3,  "thu": 3,    "thur": 3,    "thurs": 3,
        "friday": 4,    "fri": 4,
        "saturday": 5,  "sat": 5,
        "sunday": 6,    "sun": 6,
    }

    # If we recognize it, return the matching number.
    if day_str in day_map:
        return day_map[day_str]

    # If not, refuse the input and say why.
    # Including the original string in the error message helps debug —
    # a user sees "Unrecognized day: 'mondya'" and immediately knows
    # they typoed.
    raise ValueError(f"Unrecognized day: '{day_str}'")
