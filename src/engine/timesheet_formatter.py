# ============================================================
# timesheet_formatter.py
#
# Renders a list of events plus a list of issues into a printable
# plain-text weekly timesheet (Monday through Sunday).
#
# Lives in src/engine/ because it operates on already-clean data
# (validated Event objects and Issue objects). It is a pure
# transformation -- no I/O, no file writing, no network calls.
#
# Design rules locked in during Path C / timesheet planning:
#   1. Plain text only (no markdown, no styled output).
#   2. Show all events in chronological order within each day.
#   3. Issues appear as indented sub-lines beneath their related event.
#   4. Show all seven days, Monday through Sunday, even if empty.
#      Empty days display "Open Availability".
#   5. Time format: 24-hour military "HH:MM".
#   6. Banner-style day headers (40 equals signs).
#   7. Simple "Weekly Timesheet" title at the top.
#   8. Event title column adapts to the longest title in the week.
#
# Security:
#   - Input is already validated (Events have title <= 200 chars).
#   - All string interpolation uses f-strings, not .format() with
#     user-controlled format codes. No format-string injection.
#   - Output size is bounded by Event title cap + dump parser caps
#     upstream, so the formatter cannot produce unbounded output.
# ============================================================

from src.models.event import Event
from src.models.issue import Issue, IssueType


# ---- Visual constants ----

# Width of the banner divider lines (===). 40 was chosen for
# readability on standard terminals and printed pages.
BANNER_WIDTH = 40

# Day names indexed by Event.day (Mon=0..Sun=6). Used for headers
# and for the fixed Monday-through-Sunday output order.
DAY_NAMES = [
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
]

# Minimum width for the event-title column. Even if every event in
# the week has a 3-character title, we won't squeeze the column
# below this -- otherwise titles and the [QUADRANT] tag end up
# uncomfortably close on the same line.
MIN_TITLE_COLUMN_WIDTH = 10


# ---- Helpers (internal, prefixed with _) ----

def _format_time(military_int):
    """
    Convert a military-format integer to "HH:MM" display string.

    Examples:
        _format_time(900)  -> "09:00"
        _format_time(1700) -> "17:00"
        _format_time(2359) -> "23:59"
        _format_time(0)    -> "00:00"

    Note: this assumes the input is already a valid military time
    (0 to 2359 with minutes <= 59). Event's validation guarantees that.
    """
    hours = military_int // 100
    minutes = military_int % 100
    # Pad with leading zeros so the result is always 5 chars wide
    # (HH:MM). Predictable width is what enables clean alignment.
    return f"{hours:02d}:{minutes:02d}"


def _events_for_day(events, day_number):
    """
    Return all events for a given day, sorted chronologically by
    start time. Used to render each day's section.

    Note: stable sort means events with the same start time keep
    their input order.
    """
    same_day = [e for e in events if e.day == day_number]
    return sorted(same_day, key=lambda e: e.start)


def _issues_for_event(issue_list, event):
    """
    Return all issues where the given event is event_a OR event_b.

    Why both positions?
        An Issue is reported once per pair (event_a, event_b). When
        rendering Tuesday's standup that overlaps with the 1:1, the
        issue is attached to whichever appears first chronologically.
        But when showing Tuesday's schedule, BOTH events deserve to
        see the warning -- so we check both positions and attach the
        issue to either event's line during rendering.

    Note: a given Issue can therefore be returned for two different
    events. The caller is responsible for the display logic that
    decides how to phrase it.
    """
    matching = []
    for issue in issue_list:
        if issue.event_a is event or issue.event_b is event:
            matching.append(issue)
    return matching


def _compute_title_column_width(events):
    """
    Find the longest title in the events list. The title column
    will be this wide so every row aligns cleanly.

    Returns MIN_TITLE_COLUMN_WIDTH if all titles are short, so
    we never collapse the column to nothing.

    Empty list -> minimum width (so we still produce sensible
    empty-week output).
    """
    if not events:
        return MIN_TITLE_COLUMN_WIDTH

    longest = max(len(e.title) for e in events)
    return max(longest, MIN_TITLE_COLUMN_WIDTH)


def _format_quadrant_label(event):
    """
    Return the bracketed quadrant tag for an event.

    Examples:
        SIGNAL event       -> "[SIGNAL]"
        UNSPECIFIED event  -> "[UNSPECIFIED]"
    """
    return f"[{event.get_quadrant().name}]"


def _format_issue_line(issue, current_event):
    """
    Render one issue as a sub-line beneath an event.

    The wording adapts based on which event we're rendering -- when
    looking at event_a (the earlier one), we phrase the gap looking
    forward to event_b. When looking at event_b (the later one), we
    phrase it as the gap coming FROM event_a.

    Format examples:
        For event_a:  "! HARD_BUFFER: only 0 min before Commute (need 15)"
        For event_b:  "! HARD_BUFFER: only 0 min after Therapy (need 15)"
        Overlap:      "! OVERLAP: overlaps Commute by 30 min"
    """
    type_name = issue.type.value  # e.g. "HARD_BUFFER"

    if issue.type == IssueType.OVERLAP:
        # Overlaps are symmetric -- the other event in the pair is the
        # one we mention regardless of which side we're rendering.
        other = issue.event_b if current_event is issue.event_a else issue.event_a
        # gap_minutes is negative for overlaps; use absolute value.
        return (
            f"    ! {type_name}: overlaps {other.title} "
            f"by {abs(issue.gap_minutes)} min"
        )

    # Buffer issues (HARD_BUFFER or SOFT_BUFFER) -- direction matters.
    if current_event is issue.event_a:
        # We're rendering the earlier event; the problem is heading
        # FORWARD to event_b.
        return (
            f"    ! {type_name}: only {issue.gap_minutes} min "
            f"before {issue.event_b.title} "
            f"(need {issue.required_minutes})"
        )
    else:
        # We're rendering the later event; the problem is the gap
        # coming BACKWARD from event_a.
        return (
            f"    ! {type_name}: only {issue.gap_minutes} min "
            f"after {issue.event_a.title} "
            f"(need {issue.required_minutes})"
        )


# ---- Public entry point ----

def render_timesheet(events, issues):
    """
    Produce a printable plain-text weekly timesheet.

    Args:
        events: List of Event objects. Order does not matter; the
                formatter sorts events chronologically within each day.
        issues: List of Issue objects. Typically produced by
                find_all_issues(events) but any list of valid Issues
                will work.

    Returns:
        A single string containing the rendered timesheet. Includes
        newlines for separation between days. The caller is responsible
        for printing or saving.

    Raises:
        TypeError if events isn't a list, issues isn't a list, or any
        item in either list is the wrong type. We validate up front
        so the caller gets a clean error rather than a partial render.
    """

    # ---- Input validation at the door ----
    if not isinstance(events, list):
        raise TypeError(
            f"events must be a list, got {type(events).__name__}"
        )
    if not isinstance(issues, list):
        raise TypeError(
            f"issues must be a list, got {type(issues).__name__}"
        )
    for i, e in enumerate(events):
        if not isinstance(e, Event):
            raise TypeError(
                f"events[{i}] must be an Event, got {type(e).__name__}"
            )
    for i, item in enumerate(issues):
        if not isinstance(item, Issue):
            raise TypeError(
                f"issues[{i}] must be an Issue, got {type(item).__name__}"
            )

    # ---- Compute the title column width once for the whole week ----
    # This makes every row line up regardless of which day it's in.
    title_col_width = _compute_title_column_width(events)

    # ---- Build the output as a list of lines, joined at the end ----
    # Using a list + join is the cheap, predictable way to build
    # multi-line text. We never let user input shape control codes.
    lines = []

    # Top-of-document title (Decision 5b: simple title line).
    lines.append("Weekly Timesheet")
    lines.append("")  # blank line after the title

    # Iterate through all seven days in fixed order, Mon -> Sun.
    # This is what gives us a predictable shape every week (Decision 2
    # confirmed by user: show all 7 days, even empty ones).
    for day_number in range(7):
        # Banner header for this day.
        lines.append("=" * BANNER_WIDTH)
        lines.append(DAY_NAMES[day_number])
        lines.append("=" * BANNER_WIDTH)

        day_events = _events_for_day(events, day_number)

        if not day_events:
            # Empty day rendering (locked in: "Open Availability").
            lines.append("  Open Availability")
        else:
            for event in day_events:
                # Build one event line.
                # Format: "  HH:MM - HH:MM   <title padded>   [QUADRANT]"
                time_range = f"{_format_time(event.start)} - {_format_time(event.end)}"
                padded_title = event.title.ljust(title_col_width)
                quadrant_label = _format_quadrant_label(event)
                lines.append(
                    f"  {time_range}   {padded_title}   {quadrant_label}"
                )

                # Append any issue sub-lines for this event.
                event_issues = _issues_for_event(issues, event)
                for issue in event_issues:
                    lines.append(_format_issue_line(issue, event))

        # Blank line between days for readability.
        lines.append("")

    # Strip the trailing blank line so the output ends cleanly.
    if lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)
