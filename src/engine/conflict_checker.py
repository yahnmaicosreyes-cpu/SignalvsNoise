# ============================================================
# conflict_checker.py
#
# The decision-making core. Detects three kinds of problems
# between events and returns them in a useful order.
#
# Public functions:
#   1. has_conflict(d1, s1, e1, d2, s2, e2)
#         Original numeric overlap-only check. Unchanged.
#
#   2. has_event_conflict(event_a, event_b)
#         Event-aware overlap-only check. Unchanged.
#
#   3. find_all_conflicts(events)
#         Returns every overlapping pair from a list. Unchanged.
#
#   4. find_all_issues(events)
#         Returns every issue (overlap + buffer violations) labeled
#         by severity. Now sorted: Day → Time → Priority → Severity.
#
#   5. group_issues_by_day(issues)  ← NEW
#         Reshapes a flat list of issues into a dict keyed by day.
#         Days with no issues are absent from the result.
# ============================================================

from src.models.event import Event
from src.models.issue import Issue, IssueType
from src.models.buffer_defaults import (
    DEFAULT_HARD_BUFFER_MINUTES,
    DEFAULT_SOFT_BUFFER_MINUTES,
)
from src.engine.time_math import minutes_between


# Severity ranks for sorting. Lower number = more severe = sorts first.
# Kept here (not on the enum itself) because the engine owns the
# notion of "what's most actionable to see first"; the IssueType
# enum is just labels.
_SEVERITY_RANK = {
    IssueType.OVERLAP: 1,
    IssueType.HARD_BUFFER: 2,
    IssueType.SOFT_BUFFER: 3,
}


# ============================================================
# EXISTING FUNCTIONS — unchanged
# ============================================================

def has_conflict(day1, start1, end1, day2, start2, end2):
    """
    Determine whether two events conflict (overlap on the same day).
    Numeric API. Returns True if events overlap, False otherwise.
    Touching at a boundary (5pm end → 5pm start) is NOT a conflict.
    """
    if day1 != day2:
        return False
    return start1 < end2 and start2 < end1


def has_event_conflict(event_a, event_b):
    """
    Event-aware version of has_conflict. Takes two Events,
    returns True if they overlap on the same day.
    """
    if not isinstance(event_a, Event):
        raise TypeError(
            f"event_a must be an Event, got {type(event_a).__name__}"
        )
    if not isinstance(event_b, Event):
        raise TypeError(
            f"event_b must be an Event, got {type(event_b).__name__}"
        )
    return has_conflict(
        event_a.day, event_a.start, event_a.end,
        event_b.day, event_b.start, event_b.end,
    )


def find_all_conflicts(events):
    """
    Given a list of Events, return every pair that strictly overlaps.
    Buffer violations are NOT included — for those, see find_all_issues.
    """
    if not isinstance(events, list):
        raise TypeError(
            f"events must be a list, got {type(events).__name__}"
        )

    conflicts = []
    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            if has_event_conflict(events[i], events[j]):
                conflicts.append((events[i], events[j]))
    return conflicts


# ============================================================
# DETECTION HELPERS (internal)
# ============================================================

def _resolve_buffer(event_buffer, default):
    """
    Internal. Returns the effective buffer for an event:
    per-event override if set, otherwise the global default.
    """
    return default if event_buffer is None else event_buffer


def _classify_pair(event_a, event_b):
    """
    Internal. Looks at one ordered pair (event_a happens first,
    event_b second on the SAME day) and returns either an Issue
    or None.

    Severity order:
      1. OVERLAP wins over everything.
      2. HARD_BUFFER wins over SOFT_BUFFER.
      3. SOFT_BUFFER is the gentlest flag.
      4. If everything's fine, return None.
    """

    gap = minutes_between(event_a.end, event_b.start)

    hard_required = _resolve_buffer(
        event_a.hard_buffer_minutes, DEFAULT_HARD_BUFFER_MINUTES
    )
    soft_required = _resolve_buffer(
        event_a.soft_buffer_minutes, DEFAULT_SOFT_BUFFER_MINUTES
    )

    if gap < 0:
        return Issue(
            type=IssueType.OVERLAP,
            event_a=event_a, event_b=event_b,
            gap_minutes=gap, required_minutes=0,
        )

    if gap < hard_required:
        return Issue(
            type=IssueType.HARD_BUFFER,
            event_a=event_a, event_b=event_b,
            gap_minutes=gap, required_minutes=hard_required,
        )

    if gap < soft_required:
        return Issue(
            type=IssueType.SOFT_BUFFER,
            event_a=event_a, event_b=event_b,
            gap_minutes=gap, required_minutes=soft_required,
        )

    return None


# ============================================================
# SORTING (NEW)
# ============================================================

def _issue_sort_key(issue):
    """
    Internal. Returns a tuple that drives the sort order:
    Day → Time → Priority → Severity.

    Why a tuple?
        Python sorts tuples lexicographically: it compares the
        first element; if those are equal, it compares the second;
        and so on. So putting fields in the tuple in priority order
        gives us the entire sort hierarchy in one expression.

    The fields, in order:
      1. event_a.day            — which day (Mon=0..Sun=6)
      2. event_a.start          — clock time (military int)
      3. quadrant priority rank — SIGNAL=1..UNSPECIFIED=5 (lower = higher priority)
      4. severity rank          — OVERLAP=1..SOFT_BUFFER=3 (lower = more severe)

    Why use event_a's quadrant?
        Each Issue has TWO events. We pick event_a's quadrant for
        sorting because event_a is always the earlier event (the
        engine already orders pairs chronologically when classifying).
        This is consistent and unambiguous.

        A more sophisticated approach (use the HIGHER-priority of the
        two events) is possible later if needed. For now, simple wins.
    """
    quadrant_rank = issue.event_a.get_quadrant().value
    severity_rank = _SEVERITY_RANK[issue.type]
    return (
        issue.event_a.day,
        issue.event_a.start,
        quadrant_rank,
        severity_rank,
    )


# ============================================================
# find_all_issues — now sorted
# ============================================================

def find_all_issues(events):
    """
    Given a list of Events, return every Issue between them,
    sorted by Day → Time → Priority → Severity.

    Args:
        events (list[Event]): The events to check.

    Returns:
        A flat list of Issue objects in sorted order. Empty if no issues.

    Raises:
        TypeError if 'events' isn't a list, or any item isn't an Event.

    Behavior notes:
        - Cross-day pairs are skipped (no buffer issue across days).
        - Each pair produces AT MOST one issue (most severe wins).
        - Pairs are ordered chronologically inside each Issue
          (event_a is always the earlier of the two).
        - The sorted output makes a printable daily timesheet trivial:
          walk the list in order, line by line.
    """

    if not isinstance(events, list):
        raise TypeError(
            f"events must be a list, got {type(events).__name__}"
        )

    # Type-check every item up front. Doing this BEFORE we start
    # finding issues means the caller gets a clean error pointing
    # at the bad item, instead of a half-built result list plus a
    # crash mid-loop.
    for i, item in enumerate(events):
        if not isinstance(item, Event):
            raise TypeError(
                f"events[{i}] must be an Event, got {type(item).__name__}"
            )

    issues = []

    # Compare each pair exactly once (i < j prevents duplicates and
    # self-comparisons).
    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            ev_i = events[i]
            ev_j = events[j]

            # Skip cross-day pairs immediately.
            if ev_i.day != ev_j.day:
                continue

            # Order the pair so the earlier event comes first.
            # Predictable Issue.event_a / Issue.event_b regardless
            # of input list order.
            if ev_i.start <= ev_j.start:
                earlier, later = ev_i, ev_j
            else:
                earlier, later = ev_j, ev_i

            issue = _classify_pair(earlier, later)
            if issue is not None:
                issues.append(issue)

    # Sort by the four-level hierarchy. Python's sorted() is stable,
    # so issues with identical sort keys keep their relative input order.
    return sorted(issues, key=_issue_sort_key)


# ============================================================
# group_issues_by_day — NEW
# ============================================================

def group_issues_by_day(issues):
    """
    Reshape a flat list of issues into a dict keyed by day number.

    Args:
        issues (list[Issue]): The issues to group. Typically the output
            of find_all_issues(), but any list of Issues works.

    Returns:
        A dict where:
          - keys are day numbers (Mon=0..Sun=6) that have at least one issue
          - values are lists of Issues for that day, in their original order

        Days with no issues are NOT present in the dict.

    Raises:
        TypeError if 'issues' isn't a list, or if any item isn't an Issue.

    Why a dict instead of a list-of-lists?
        Two reasons:
          1. Callers can ask "do I have issues on Wednesday?" with a
             simple `2 in result` check — no looping required.
          2. Days with no issues don't waste space (or attention).
             Printing the result naturally skips quiet days.

    Note on order:
        Iterating the dict's keys gives them in insertion order (Python
        guarantees this since 3.7). Since find_all_issues already returns
        issues sorted by day, the dict's keys come out in day order too.
        Within each day, issues stay in whatever order they appeared in
        the input (chronological, if the input was from find_all_issues).
    """

    if not isinstance(issues, list):
        raise TypeError(
            f"issues must be a list, got {type(issues).__name__}"
        )

    grouped = {}

    for i, item in enumerate(issues):
        if not isinstance(item, Issue):
            raise TypeError(
                f"issues[{i}] must be an Issue, got {type(item).__name__}"
            )

        # event_a.day is the canonical day for an issue. Both events in
        # the pair are on the same day (cross-day pairs were skipped
        # earlier), so it doesn't matter which we use.
        day = item.event_a.day

        # setdefault: returns the existing list if 'day' is already a key,
        # or sets it to [] and returns the new empty list. Either way we
        # get back a list to append to. One line, zero conditionals.
        grouped.setdefault(day, []).append(item)

    return grouped
