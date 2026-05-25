# ============================================================
# issue.py
#
# The Issue data structure. An Issue is one specific problem
# the engine has flagged between two events — an overlap, a
# hard buffer violation, or a soft buffer violation.
#
# Why a separate file from event.py?
#   Events and Issues are different nouns. An Event is something
#   on your calendar; an Issue is something WRONG with your
#   calendar. Keeping them separate makes the codebase easier
#   to navigate as it grows.
# ============================================================

from dataclasses import dataclass
from enum import Enum

from src.models.event import Event


class IssueType(Enum):
    """
    The three kinds of problems the engine can flag.

    Listed in order of severity (highest to lowest):
      OVERLAP      — Events run at the same time. Hard conflict.
      HARD_BUFFER  — Events don't overlap, but there isn't enough
                     time between them for physical transition.
      SOFT_BUFFER  — Events have transition time but not enough
                     breathing room. A warning, not a deal-breaker.

    Why an Enum instead of strings?
      Strings make typos invisible: issue.type == "HARDBUFFER"
      would silently fail forever with no error. Enums force
      the caller to use IssueType.HARD_BUFFER, which IDEs and
      linters can verify. Cheap safety, big win.
    """
    OVERLAP = "OVERLAP"
    HARD_BUFFER = "HARD_BUFFER"
    SOFT_BUFFER = "SOFT_BUFFER"


@dataclass
class Issue:
    """
    A single problem found between two events.

    Attributes:
        type (IssueType): Which kind of problem (OVERLAP, HARD_BUFFER, SOFT_BUFFER).
        event_a (Event): The earlier event (the one being left).
        event_b (Event): The later event (the one being arrived at).
        gap_minutes (int):
            Minutes between event_a's end and event_b's start.
            Negative for overlaps (e.g. -30 means they overlap by 30 min).
            Zero or positive for buffer violations.
        required_minutes (int):
            How many minutes the gap SHOULD have been to avoid this issue.
            For OVERLAP: 0 (any non-negative gap would be fine).
            For HARD_BUFFER: the hard buffer requirement.
            For SOFT_BUFFER: the soft buffer requirement.

    Why both gap_minutes and required_minutes?
        With both, the caller can produce useful messages without
        recomputing anything: "you have X minutes, you need Y."
        Storing the math we already did costs nothing and saves
        every consumer from redoing it.
    """

    type: IssueType
    event_a: Event
    event_b: Event
    gap_minutes: int
    required_minutes: int
