# ============================================================
# dump_parser.py
#
# Parses a freeform text "data dump" of weekly events into a list
# of Event objects.
#
# Input format (strict, pipe-separated):
#   Title | Day | StartTime-EndTime | [optional tags]
#
# Example lines:
#   Therapy | Monday | 4:00PM-5:00PM | [signal]
#   Sync A  | Friday | 2:00PM-2:30PM | [noise] [hard:0] [soft:0]
#   Yoga    | Wed    | 7:00AM-8:00AM
#
# Tags (all optional, all case-insensitive, order doesn't matter):
#   [signal]        Set priority to important=True,  urgent=False
#   [urgent]        Set priority to important=True,  urgent=True
#   [interruption]  Set priority to important=False, urgent=True
#   [noise]         Set priority to important=False, urgent=False
#   [hard:30]       Override hard buffer to 30 minutes
#   [soft:60]       Override soft buffer to 60 minutes
#   (Whitespace inside tags is allowed: [hard: 30] works the same.)
#
# Error handling philosophy ("parse what you can"):
#   - Lines that fail parsing don't kill the whole dump.
#   - Successful lines are returned as Events.
#   - Failed lines are returned in a separate list, each with
#     a clear reason explaining what went wrong.
#   - The caller decides what to do with failures.
#
# Security caps (rejected with a single clear error if exceeded):
#   - Total input length:  MAX_TOTAL_INPUT_LENGTH characters
#   - Total number of lines: MAX_LINE_COUNT
#   - Per-line length: MAX_LINE_LENGTH characters
# ============================================================

from dataclasses import dataclass, field
from typing import List

from src.models.event import Event


# ----------------------------------------------------------------
# Security caps.
#
# These are calibrated to 1.5x of typical real-world usage. They're
# deliberately tight to keep the attack surface small. If real users
# hit them, the user shouldn't suffer in silence — they'll see a
# clear error, and we can raise the cap (these are just constants).
#
# Typical-week assumptions used to set these:
#   - 60 events per week (heavy)  → 60 lines minimum
#   - 100 characters per line (longest realistic line)
#   - 60 * 100 = 6,000 chars typical total
#
# 1.5x multiplier on each:
# ----------------------------------------------------------------

# 9,000 characters: 1.5x of a heavy-week dump (~6,000 chars).
# Anything larger is probably an accidental paste or an attack.
MAX_TOTAL_INPUT_LENGTH = 9_000

# 90 lines: 1.5x of a 60-event week. Includes room for blank
# lines and # comments that the parser skips.
MAX_LINE_COUNT = 90

# 150 characters per line: 1.5x of a typical fully-tagged line
# (~100 chars). Unusually long titles will hit this first; if they
# do, the fix is to shorten the title (or raise this constant).
MAX_LINE_LENGTH = 150


# ----------------------------------------------------------------
# Tag vocabulary. The keys are exactly what users type (lowercase).
# The values are (important, urgent) tuples that get applied to
# the Event when the tag is present.
# ----------------------------------------------------------------
PRIORITY_TAGS = {
    "signal":       (True,  False),
    "urgent":       (True,  True),
    "interruption": (False, True),
    "noise":        (False, False),
}


# ----------------------------------------------------------------
# Result structures
# ----------------------------------------------------------------

@dataclass
class DumpFailure:
    """
    A single line that couldn't be parsed.

    Attributes:
        line_number: 1-based line number in the original input
                     (so users can find it in their text).
        line_content: The actual text of the bad line, TRUNCATED to
                      MAX_LINE_LENGTH characters in case the line
                      itself is huge. (We never echo unbounded input.)
        reason: Human-readable explanation of what went wrong.
    """
    line_number: int
    line_content: str
    reason: str


@dataclass
class DumpResult:
    """
    The complete result of parsing a dump.

    Attributes:
        events: List of Event objects for lines that parsed successfully.
        failures: List of DumpFailure objects for lines that didn't.
        global_error: If the entire dump was rejected (e.g. too long),
                      this is set to the error message and events/failures
                      will be empty. Normally None.

    Why a single result object instead of (events, failures)?
        Tuples are easy to misuse — easy to forget which position is
        which. A named result makes calling code self-documenting:
        result.events, result.failures, result.global_error.
    """
    events: List[Event] = field(default_factory=list)
    failures: List[DumpFailure] = field(default_factory=list)
    global_error: str = None


# ----------------------------------------------------------------
# Internal helpers (prefixed with _ to mark them as private)
# ----------------------------------------------------------------

def _truncate_for_echo(text, max_len=MAX_LINE_LENGTH):
    """
    Make a string safe to put inside an error message.

    Why this exists:
        Error messages echo back the bad input so the user can see
        what went wrong. But if the bad input is 10MB, the error
        message would also be 10MB — which is its own problem.
        This helper bounds the size of anything we echo back.

    Args:
        text: The string to truncate.
        max_len: Maximum length before truncation kicks in.

    Returns:
        The original string if it's short enough.
        Otherwise the first max_len characters, with "..." appended.
    """
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _parse_time_range(time_range_str):
    """
    Parse a "StartTime-EndTime" string into two military integers.

    Examples:
        _parse_time_range("4:00PM-5:00PM") returns (1600, 1700)
        _parse_time_range("9:00AM - 10:30AM") returns (900, 1030)
                                                      (whitespace OK)

    Args:
        time_range_str: A string with two times separated by "-".

    Returns:
        A tuple (start_int, end_int) in military format.

    Raises:
        ValueError if the input doesn't contain exactly one "-",
        or if either side fails to parse as a valid time.
    """
    # Import inside the function to avoid a circular import
    # (time_parser imports nothing from us, but we use it here).
    from src.parsers.time_parser import parse_time

    # Must contain exactly one "-" separating start and end.
    if time_range_str.count("-") != 1:
        raise ValueError(
            f"time range '{_truncate_for_echo(time_range_str)}' must contain "
            f"exactly one '-' between start and end times"
        )

    start_str, end_str = time_range_str.split("-")

    # parse_time handles its own validation (strict hours, minutes,
    # AM/PM rules). Any errors here propagate up with their own
    # clear messages.
    start = parse_time(start_str)
    end = parse_time(end_str)

    return start, end


def _parse_tag(tag_content):
    """
    Parse the contents of a single [tag] (the part inside the brackets).

    Args:
        tag_content: The string between [ and ], e.g. "signal" or "hard:30"
                     or "hard: 30" (with optional whitespace around the colon).

    Returns:
        A tuple (kind, value) where:
          - kind is one of: "priority", "hard_buffer", "soft_buffer"
          - value is:
              for "priority"     → (important_bool, urgent_bool) tuple
              for "hard_buffer"  → integer minutes
              for "soft_buffer"  → integer minutes

    Raises:
        ValueError if the tag isn't recognized or its value is invalid.
    """
    # Normalize: strip outer whitespace, lowercase for case-insensitive
    # matching. Inner spaces (like "hard: 30") are handled below.
    tag = tag_content.strip().lower()

    # Priority tags are single words with no colon.
    # Check this first since they're the most common.
    if tag in PRIORITY_TAGS:
        return ("priority", PRIORITY_TAGS[tag])

    # Buffer tags have the form "hard:30" or "soft: 60".
    # Both "hard" and "soft" require a colon followed by a number.
    if ":" in tag:
        kind_part, value_part = tag.split(":", 1)
        kind_part = kind_part.strip()
        value_part = value_part.strip()

        # Map the kind to a result type.
        if kind_part == "hard":
            result_kind = "hard_buffer"
        elif kind_part == "soft":
            result_kind = "soft_buffer"
        else:
            raise ValueError(
                f"unknown tag '{_truncate_for_echo(tag_content)}' "
                f"(expected one of: signal, urgent, interruption, noise, "
                f"hard:N, soft:N)"
            )

        # Value must be a non-negative integer.
        # Negative buffers and decimals are rejected by Event's own
        # validation later, but catching obvious garbage here gives
        # a better error message.
        if not value_part.isdigit():
            raise ValueError(
                f"tag '{_truncate_for_echo(tag_content)}' requires a "
                f"non-negative integer after the colon "
                f"(e.g. [hard:30], [soft:60])"
            )

        return (result_kind, int(value_part))

    # Tag didn't match any recognized form.
    raise ValueError(
        f"unknown tag '{_truncate_for_echo(tag_content)}' "
        f"(expected one of: signal, urgent, interruption, noise, "
        f"hard:N, soft:N)"
    )


def _extract_tags(tags_section):
    """
    Pull every [tag] out of a string and parse each one.

    Args:
        tags_section: The portion of a line after the time range,
                      e.g. "[signal] [hard:30]" or "" (no tags).

    Returns:
        A dict with the resolved values. Keys present only when
        the corresponding tag was found:
          - "important" → bool (if a priority tag was present)
          - "urgent"    → bool (if a priority tag was present)
          - "hard_buffer_minutes" → int (if [hard:N] was present)
          - "soft_buffer_minutes" → int (if [soft:N] was present)

    Raises:
        ValueError if any tag is malformed or unknown, OR if the
        same kind of tag appears more than once (e.g. two priority
        tags). Duplicates are rejected because they're almost
        certainly a user mistake we want to surface.
    """
    result = {}
    seen_priority = False

    # Find each [tag] one at a time. We use string scanning rather
    # than regex to keep the parser simple and predictable.
    cursor = 0
    while cursor < len(tags_section):
        # Find the next '['
        open_pos = tags_section.find("[", cursor)
        if open_pos == -1:
            # No more tags. Whatever's left should be only whitespace.
            remainder = tags_section[cursor:].strip()
            if remainder:
                raise ValueError(
                    f"unexpected text after tags: "
                    f"'{_truncate_for_echo(remainder)}'"
                )
            break

        # Anything between cursor and open_pos should be whitespace.
        between = tags_section[cursor:open_pos].strip()
        if between:
            raise ValueError(
                f"unexpected text before tag: "
                f"'{_truncate_for_echo(between)}'"
            )

        # Find the matching ']'
        close_pos = tags_section.find("]", open_pos)
        if close_pos == -1:
            raise ValueError(
                f"unclosed tag starting at '['"
            )

        # Pull out the contents between [ and ]
        tag_content = tags_section[open_pos + 1:close_pos]
        kind, value = _parse_tag(tag_content)

        # Apply the parsed tag to the result dict.
        if kind == "priority":
            if seen_priority:
                raise ValueError(
                    "more than one priority tag on the same line "
                    "(use only one of: [signal], [urgent], "
                    "[interruption], [noise])"
                )
            important, urgent = value
            result["important"] = important
            result["urgent"] = urgent
            seen_priority = True

        elif kind == "hard_buffer":
            if "hard_buffer_minutes" in result:
                raise ValueError("more than one [hard:N] tag on the same line")
            result["hard_buffer_minutes"] = value

        elif kind == "soft_buffer":
            if "soft_buffer_minutes" in result:
                raise ValueError("more than one [soft:N] tag on the same line")
            result["soft_buffer_minutes"] = value

        # Move cursor past this tag
        cursor = close_pos + 1

    return result


def _parse_line(line):
    """
    Parse a single line of dump input into an Event.

    Expected format:
        Title | Day | StartTime-EndTime
        Title | Day | StartTime-EndTime | [tags]

    Args:
        line: The raw line of input (without trailing newline).

    Returns:
        An Event object built from the line's fields.

    Raises:
        ValueError if the line doesn't have the expected structure,
        or if any field fails to parse, or if any tag is malformed.
    """
    # Import here to avoid any circular import surprises.
    from src.parsers.day_parser import parse_day

    # Split on '|'. Strict format requires at least 3 sections
    # (title, day, time range) and at most 4 (with tags).
    parts = line.split("|")
    if len(parts) < 3 or len(parts) > 4:
        raise ValueError(
            f"line must have 3 or 4 sections separated by '|' "
            f"(got {len(parts)} sections)"
        )

    # Strip whitespace from each section.
    parts = [p.strip() for p in parts]
    title, day_str, time_range_str = parts[0], parts[1], parts[2]
    tags_section = parts[3] if len(parts) == 4 else ""

    # Empty fields are not allowed for the three required sections.
    # (Empty tags section is fine — it means no tags.)
    if not title:
        raise ValueError("title is empty")
    if not day_str:
        raise ValueError("day is empty")
    if not time_range_str:
        raise ValueError("time range is empty")

    # Each helper validates its own input and raises a clear error
    # if anything is wrong.
    day = parse_day(day_str)
    start, end = _parse_time_range(time_range_str)
    tag_values = _extract_tags(tags_section)

    # Build the Event. Event's own validation will catch any
    # remaining problems (negative buffer, end before start, etc.)
    # via its __post_init__ method.
    return Event(
        title=title,
        day=day,
        start=start,
        end=end,
        important=tag_values.get("important"),
        urgent=tag_values.get("urgent"),
        hard_buffer_minutes=tag_values.get("hard_buffer_minutes"),
        soft_buffer_minutes=tag_values.get("soft_buffer_minutes"),
    )


# ----------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------

def parse_dump(text):
    """
    Parse a freeform text dump of weekly events.

    Args:
        text: The raw input string.

    Returns:
        A DumpResult object with three pieces of information:
          - result.events: list of successfully-parsed Event objects
          - result.failures: list of DumpFailure entries for lines
            that couldn't be parsed (each with line number and reason)
          - result.global_error: set if the entire dump was rejected
            (input too large, wrong type, etc.). If set, events and
            failures will be empty.

    The parser is intentionally lenient about *which* lines fail:
    a malformed line doesn't kill the whole dump. The caller decides
    what to do with failed lines.

    Raises:
        Nothing. All errors are reported through DumpResult fields,
        not exceptions. (Other code may need to react to parse
        failures in various ways; making them all data instead of
        exceptions keeps that easy.)
    """
    result = DumpResult()

    # ---- TYPE CHECK ----
    # Reject non-string input loudly. A None or integer here is a
    # programmer mistake, not a user-input mistake.
    if not isinstance(text, str):
        result.global_error = (
            f"input must be a string, got {type(text).__name__}"
        )
        return result

    # ---- TOTAL LENGTH CAP ----
    # Bounded BEFORE any further processing. A 100MB string can't
    # even reach the line-splitting step.
    if len(text) > MAX_TOTAL_INPUT_LENGTH:
        result.global_error = (
            f"input is too long ({len(text)} characters, "
            f"maximum is {MAX_TOTAL_INPUT_LENGTH})"
        )
        return result

    # ---- SPLIT INTO LINES ----
    # splitlines() handles "\n", "\r\n", and "\r" all the same way,
    # which protects against Windows/Mac/Unix paste differences.
    lines = text.splitlines()

    # ---- LINE COUNT CAP ----
    if len(lines) > MAX_LINE_COUNT:
        result.global_error = (
            f"too many lines ({len(lines)}, maximum is {MAX_LINE_COUNT})"
        )
        return result

    # ---- PROCESS EACH LINE ----
    for index, raw_line in enumerate(lines):
        # 1-based line number for human-readable error messages.
        line_number = index + 1

        # ---- PER-LINE LENGTH CAP ----
        if len(raw_line) > MAX_LINE_LENGTH:
            result.failures.append(DumpFailure(
                line_number=line_number,
                line_content=_truncate_for_echo(raw_line),
                reason=(
                    f"line is too long ({len(raw_line)} characters, "
                    f"maximum is {MAX_LINE_LENGTH})"
                ),
            ))
            continue

        # ---- SKIP BLANK LINES ----
        # Blank lines and pure-whitespace lines are not errors — they
        # let users space out their dump for readability.
        stripped = raw_line.strip()
        if not stripped:
            continue

        # ---- SKIP COMMENT LINES ----
        # Lines starting with '#' are comments. Convenient for users
        # who want to label sections of their dump ("# Monday block").
        if stripped.startswith("#"):
            continue

        # ---- PARSE THE LINE ----
        # _parse_line raises ValueError on any problem; we catch and
        # convert to a DumpFailure so the rest of the dump keeps going.
        try:
            event = _parse_line(stripped)
            result.events.append(event)
        except (ValueError, TypeError) as e:
            # ValueError covers most parse failures. TypeError covers
            # the rare case of Event construction failing on a bad
            # buffer value (e.g. someone slipping a string in somehow).
            result.failures.append(DumpFailure(
                line_number=line_number,
                line_content=_truncate_for_echo(stripped),
                reason=str(e),
            ))

    return result
