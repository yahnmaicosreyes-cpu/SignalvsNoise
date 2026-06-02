# ============================================================
# _validators.py
#
# Shared validation helpers used by both parsers.
#
# Naming note: the leading underscore in the filename is a Python
# convention meaning "internal — don't import this from outside
# the parsers package." Other code in src/ should not reach in
# here directly. The parsers wrap these checks and expose them.
#
# Why a shared file?
#   Both parse_time and parse_day need the same first-line checks
#   (type, length, emptiness). Putting them here means:
#     1. One place to update if we change the rules
#     2. Identical behavior across parsers (no drift)
#     3. Each parser file stays focused on its real job
# ============================================================


# Maximum allowed length for any input string, in characters.
# Real time/day strings are well under 15 characters; 50 is a
# generous buffer that still blocks paste-bomb attacks (someone
# pasting a million characters to slow the app down).
MAX_INPUT_LENGTH = 50


def validate_string_input(value, field_name):
    """
    Run the universal first-line checks on any user input.

    Checks, in order:
        1. Is it actually a string? (rejects None, numbers, lists, etc.)
        2. Is it within the length cap? (rejects paste-bombs)
        3. Is there any content after stripping whitespace?
           (rejects "" and "   ")

    Args:
        value: The raw input from the user.
        field_name: Human-readable name of the field for error messages
                    (e.g. "time" or "day"). This is what shows up in
                    the error so the user knows which input was bad.

    Returns:
        The input string, stripped of surrounding whitespace.
        (We strip here once so callers don't have to repeat it.)

    Raises:
        TypeError if the input isn't a string.
        ValueError if the input is too long or empty.
    """

    # Step 1: type check.
    # We use TypeError (not ValueError) here because passing a non-string
    # is a programmer mistake, not a user-input mistake. Different error
    # types let calling code respond differently if it ever needs to.
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string, got {type(value).__name__}"
        )

    # Step 2: length check.
    # Done BEFORE stripping so a 10MB string of spaces still gets blocked
    # immediately — we never want to process huge inputs, even if they're
    # mostly whitespace.
    if len(value) > MAX_INPUT_LENGTH:
        raise ValueError(
            f"{field_name} is too long "
            f"({len(value)} characters, maximum is {MAX_INPUT_LENGTH})"
        )

    # Step 3: emptiness check.
    # Strip first so "   " is treated the same as "".
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} cannot be empty")

    # Hand back the stripped string so callers skip re-stripping.
    return stripped
