# ============================================================
# event.py
#
# The Event data structure. An Event is a single thing on your
# calendar — a class, a meeting, a workout — with everything we
# know about it bundled into one object.
#
# Two ways to make an Event:
#   1. Direct construction (internal/testing — already-parsed numbers)
#         Event(title="Study", day=0, start=1600, end=1700)
#
#   2. From strings (user-facing — handles parsing + validation)
#         Event.from_strings("Study", "Monday", "4:00PM", "5:00PM")
#
# Optional buffer fields:
#   hard_buffer_minutes — minimum physical transition time AFTER this event
#   soft_buffer_minutes — desired breathing room AFTER this event
#
# Optional priority fields (NEW — Path B):
#   important — True/False/None. Whether this event matters strategically.
#   urgent    — True/False/None. Whether this event is time-pressured.
#
# Both default None ("not specified"). When both are set, they resolve
# to one of four Quadrants (SIGNAL / URGENT / INTERRUPTION / NOISE).
# When either is None, the event's quadrant is UNSPECIFIED.
# ============================================================

from dataclasses import dataclass
from typing import Optional

from src.parsers.day_parser import parse_day
from src.parsers.time_parser import parse_time
from src.parsers._validators import validate_string_input
from src.models.priority import Quadrant, resolve_quadrant


# Maximum length for an event title (security: prevent paste-bomb attacks
# and absurd UI breakage from unbounded text input).
MAX_TITLE_LENGTH = 200


# Maximum allowed buffer in minutes. 720 = 12 hours. Catches typos
# (1500 instead of 15) without being restrictive in practice.
MAX_BUFFER_MINUTES = 720


@dataclass
class Event:
    """
    A single calendar event with title, day, time window, optional
    per-event buffer overrides, and optional priority tags.

    Validation runs automatically after construction (see __post_init__).
    Invalid Events cannot exist — if construction succeeds, the data is good.
    """

    title: str
    day: int
    start: int
    end: int
    hard_buffer_minutes: Optional[int] = None
    soft_buffer_minutes: Optional[int] = None
    important: Optional[bool] = None
    urgent: Optional[bool] = None

    def __post_init__(self):
        """
        Runs automatically right after an Event is constructed.
        The 'validate at the edge' checkpoint for direct construction.
        If anything fails, the Event simply doesn't exist — the
        constructor raises and the caller has to handle it.
        """

        # --- TITLE CHECKS ---
        self.title = validate_string_input(self.title, "Title")
        if len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError(
                f"Title is too long "
                f"({len(self.title)} characters, max is {MAX_TITLE_LENGTH})"
            )

        # --- DAY CHECKS ---
        # Bool rejection: in Python, True == 1 and False == 0, so without
        # the bool check, Event(day=True) would silently create a Tuesday event.
        if not isinstance(self.day, int) or isinstance(self.day, bool):
            raise TypeError(
                f"Day must be an integer 0-6, "
                f"got {type(self.day).__name__}"
            )
        if self.day < 0 or self.day > 6:
            raise ValueError(
                f"Day must be 0-6 (Mon=0..Sun=6), got {self.day}"
            )

        # --- TIME CHECKS ---
        for field_name, value in (("start", self.start), ("end", self.end)):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(
                    f"{field_name} must be an integer in military format, "
                    f"got {type(value).__name__}"
                )
            if value < 0 or value > 2359:
                raise ValueError(
                    f"{field_name} must be 0-2359 (military format), got {value}"
                )
            # Sanity: minutes portion must be 0-59. Catches values like
            # 1099 that LOOK in range but aren't valid times.
            if value % 100 > 59:
                raise ValueError(
                    f"{field_name}={value} is not a valid time "
                    f"(minutes must be 0-59)"
                )

        # --- LOGICAL: end must come after start ---
        if self.end <= self.start:
            raise ValueError(
                f"end ({self.end}) must be after start ({self.start})"
            )

        # --- BUFFER CHECKS ---
        for field_name, value in (
            ("hard_buffer_minutes", self.hard_buffer_minutes),
            ("soft_buffer_minutes", self.soft_buffer_minutes),
        ):
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(
                    f"{field_name} must be an integer or None, "
                    f"got {type(value).__name__}"
                )
            if value < 0:
                raise ValueError(
                    f"{field_name} must be >= 0, got {value}"
                )
            if value > MAX_BUFFER_MINUTES:
                raise ValueError(
                    f"{field_name}={value} exceeds maximum of "
                    f"{MAX_BUFFER_MINUTES} minutes (likely a typo?)"
                )

        # --- PRIORITY CHECKS (NEW) ---
        # Each field must be True, False, or None — nothing else.
        # We can't use the usual isinstance(value, bool) check alone
        # because we ALSO need to accept None. So the rule is:
        #   value is None  → OK
        #   value is True  → OK
        #   value is False → OK
        #   anything else  → reject
        for field_name, value in (
            ("important", self.important),
            ("urgent", self.urgent),
        ):
            if value is None:
                continue
            # `isinstance(value, bool)` returns True for True/False only —
            # not for 1 or 0, which is the right check here. Python's
            # boolean type is the only thing we want to accept.
            if not isinstance(value, bool):
                raise TypeError(
                    f"{field_name} must be True, False, or None, "
                    f"got {type(value).__name__}"
                )

    def get_quadrant(self):
        """
        Convenience accessor: returns this event's Quadrant.

        UNSPECIFIED if either important or urgent is None.
        Otherwise one of SIGNAL / URGENT / INTERRUPTION / NOISE.

        Why a method on Event instead of expecting callers to
        call resolve_quadrant themselves? Two reasons:
          1. Most consumers want the quadrant, not the raw booleans.
          2. Centralizes "how do we get the quadrant of an event"
             so it's the same everywhere.
        """
        return resolve_quadrant(self.important, self.urgent)

    @classmethod
    def from_strings(
        cls,
        title,
        day_str,
        start_str,
        end_str,
        hard_buffer_minutes=None,
        soft_buffer_minutes=None,
        important=None,
        urgent=None,
    ):
        """
        Create an Event from human-friendly string inputs.

        Buffer and priority fields are passed through directly — they're
        already typed values (int or bool), no parsing needed.
        """
        day = parse_day(day_str)
        start = parse_time(start_str)
        end = parse_time(end_str)

        return cls(
            title=title,
            day=day,
            start=start,
            end=end,
            hard_buffer_minutes=hard_buffer_minutes,
            soft_buffer_minutes=soft_buffer_minutes,
            important=important,
            urgent=urgent,
        )
