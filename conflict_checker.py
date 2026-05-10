# ============================================================
# conflict_checker.py — Binary Logic Engine (MVP)
#
# Two functions:
#   1. parse_time  — Converts human time strings to military int
#   2. has_conflict — Checks if two time ranges overlap
# ============================================================


# ------------------------------------------------------------
# PARSER
# Input:  A time string (e.g. "4:00PM", "16:00", "4pm")
# Output: An integer in military format (e.g. 1600, 900, 2359)
# ------------------------------------------------------------
def parse_time(time_str):
    # Normalize: strip whitespace, force uppercase
    time_str = time_str.strip().upper()

    # Detect AM/PM before removing the letters
    is_pm = "PM" in time_str
    is_am = "AM" in time_str

    # Remove AM/PM text, leaving only digits and ":"
    time_str = time_str.replace("AM", "").replace("PM", "")

    # Split hours and minutes
    if ":" in time_str:
        hours, minutes = time_str.split(":")
    else:
        # Handles shorthand like "4pm" (no colon, no minutes)
        hours = time_str
        minutes = "0"

    # Convert from text to numbers
    hours = int(hours)
    minutes = int(minutes)

    # PM edge case: add 12 (4pm → 16), but 12pm stays 12 (noon)
    if is_pm and hours != 12:
        hours += 12

    # AM edge case: 12am is midnight → 0
    if is_am and hours == 12:
        hours = 0

    # Combine into military format: 16 hours, 30 min → 1630
    return hours * 100 + minutes


# ------------------------------------------------------------
# CONFLICT CHECKER
# Input:  Four integers (start1, end1, start2, end2)
# Output: True if the two time ranges overlap, False if not
# ------------------------------------------------------------
def has_conflict(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1