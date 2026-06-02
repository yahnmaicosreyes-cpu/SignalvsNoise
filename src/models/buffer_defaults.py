# ============================================================
# buffer_defaults.py
#
# Global default buffer values. Lives in models/ because they
# describe a property of "what an Event is" by default.
#
# These are the values used when an Event doesn't specify its own.
# Per-event overrides are supported — see Event.hard_buffer_minutes
# and Event.soft_buffer_minutes.
#
# Why a separate file?
#   Defaults change. If we ever decide 15 minutes was wrong, we
#   change it in ONE place and the whole app updates.
# ============================================================


# Hard buffer: the minimum time you PHYSICALLY need between events.
# Default 15 minutes — covers brief transitions (Zoom → Zoom + bathroom,
# walking between rooms, etc.). Override per-event for things that need
# more (commute) or less (back-to-back virtual meetings).
DEFAULT_HARD_BUFFER_MINUTES = 15


# Soft buffer: the breathing room you WANT between events.
# Default 30 minutes — gives mental decompression time, not just
# physical transition. Override per-event when you want more or less.
DEFAULT_SOFT_BUFFER_MINUTES = 30
