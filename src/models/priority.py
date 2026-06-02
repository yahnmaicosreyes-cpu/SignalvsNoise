# ============================================================
# priority.py
#
# The priority system. Each event can be tagged with two
# independent boolean fields:
#   - important (True/False/None)
#   - urgent    (True/False/None)
#
# These two booleans resolve into a Quadrant — one of five
# named buckets — which the engine uses to sort output.
#
# The user's chosen ordering (most → least important):
#   1. SIGNAL       (important=True,  urgent=False)
#   2. URGENT       (important=True,  urgent=True)
#   3. INTERRUPTION (important=False, urgent=True)
#   4. NOISE        (important=False, urgent=False)
#   5. UNSPECIFIED  (either or both fields are None)
#
# This ordering is deliberate and reflects the user's philosophy:
# "I want to live in important-not-urgent (prevention)." See the
# project README for the full reasoning.
# ============================================================

from enum import Enum


class Quadrant(Enum):
    """
    The five priority buckets. Members are ordered by their `value`
    field (lower number = higher priority).

    Why an Enum instead of strings?
      Strings make typos invisible: quadrant == "SIGNALL" would
      silently fail forever. Enums force the caller to use
      Quadrant.SIGNAL, which IDEs and linters can verify.

    Why integers as values instead of just names?
      The integer IS the sort rank. We can sort issues directly
      by their quadrant's value — no separate lookup table needed.
      Lower number sorts first, matching "highest priority first."
    """
    SIGNAL = 1        # important=True,  urgent=False  → highest priority
    URGENT = 2        # important=True,  urgent=True
    INTERRUPTION = 3  # important=False, urgent=True
    NOISE = 4         # important=False, urgent=False
    UNSPECIFIED = 5   # any field is None              → lowest priority


def resolve_quadrant(important, urgent):
    """
    Map two booleans (each True/False/None) to a Quadrant.

    Args:
        important: True, False, or None (not specified).
        urgent:    True, False, or None (not specified).

    Returns:
        A Quadrant value. UNSPECIFIED if either input is None
        (we deliberately do NOT guess defaults — see project
        decision in Section 1 of Path B).

    Why a separate function instead of a method on Event?
      Keeps the rule in one place. If we ever change how the
      booleans map to quadrants, we change ONE function and
      every caller updates automatically.

    Note: we accept only True, False, or None. Anything else
    (e.g. 1, "yes", []) is a programmer error — Event's own
    validation will catch this before we ever see it here.
    """

    # UNSPECIFIED wins immediately if EITHER field is missing.
    # No silent default-filling: we don't know what the user meant.
    if important is None or urgent is None:
        return Quadrant.UNSPECIFIED

    # All four real combinations, mapped by the user's ordering.
    if important and not urgent:
        return Quadrant.SIGNAL
    if important and urgent:
        return Quadrant.URGENT
    if not important and urgent:
        return Quadrant.INTERRUPTION
    # Last case: both False
    return Quadrant.NOISE
