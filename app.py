# ============================================================
# app.py
#
# The web entry point for the Priority Planner.
#
# What this file does, in plain English:
#   - Creates the Flask application object
#   - Configures security defaults (session cookies, size limits)
#   - Provides CSRF protection for all forms
#   - Stores entered events in the user's session as they move
#     through the four-quadrant flow
#   - Registers the routes
#
# How to run it:
#     python3 app.py                  # for local development
#     gunicorn app:app                # for Railway / production
#
# Build progress:
#   Session 1 -- skeleton + security baseline (done)
#   Session 2 -- welcome page + Signal quadrant form (THIS SESSION)
#   Session 3 -- remaining quadrants (Urgent, Interruption, Noise)
#   Session 4 -- review/edit screen
#   Session 5 -- final timesheet + download
#   Session 6 -- Railway deploy + security audit
#
# The engine code (src/) is NOT touched by the web layer.
# ============================================================

import os
import secrets

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    abort,
    Response,
)

from src.parsers.day_parser import parse_day
from src.parsers.time_parser import parse_time
from src.models.event import Event
from src.engine.conflict_checker import find_all_issues
from src.engine.timesheet_formatter import render_timesheet


# ---- Request-size cap (outer security boundary) ----
# Our engine caps input at 9,000 chars; this rejects oversized
# HTTP requests before any application code runs. 64 KB is far
# above the engine cap but still tiny -- defense in depth.
MAX_REQUEST_BYTES = 64 * 1024  # 64 KB


# ---- The four quadrants, in the order the user enters them ----
# Each quadrant maps to a fixed (important, urgent) pair. The user
# never sets these booleans directly -- the SCREEN they're on
# determines the priority. This is the priority-first philosophy
# made concrete: you decide importance by choosing which screen
# you're entering events on.
#
# Order matters: signal first (prevention), then urgent, then the
# less-important buckets. Each dict entry drives one form screen.
QUADRANTS = {
    "signal": {
        "name": "Signal",
        "subtitle": "Important, not urgent. Your foundation work.",
        "important": True,
        "urgent": False,
        "next": "urgent",      # which quadrant comes after this one
        "step_number": 1,      # for the "Step X of 4" progress indicator
    },
    "urgent": {
        "name": "Urgent",
        "subtitle": "Important AND urgent. Today's fires.",
        "important": True,
        "urgent": True,
        "next": "interruption",
        "step_number": 2,
    },
    "interruption": {
        "name": "Interruption",
        "subtitle": "Urgent but not really important. Looks loud, isn't signal.",
        "important": False,
        "urgent": True,
        "next": "noise",
        "step_number": 3,
    },
    "noise": {
        "name": "Noise",
        "subtitle": "Neither important nor urgent. Drop candidates.",
        "important": False,
        "urgent": False,
        "next": None,          # last quadrant -- nothing after it (yet)
        "step_number": 4,
    },
}

# Total number of quadrant steps. Derived from the dict so it can
# never drift out of sync with the actual number of quadrants.
TOTAL_QUADRANT_STEPS = len(QUADRANTS)


# ============================================================
# CSRF protection
#
# Cross-Site Request Forgery: an attacker tricks a logged-in user's
# browser into submitting a form to our app without the user's
# intent. We defend by putting a secret token in every form. A
# forged request from another site won't have the token, so we
# reject it.
#
# We implement this ourselves (rather than adding flask-wtf) to keep
# dependencies minimal. The pattern is standard and well understood.
# ============================================================

def _get_or_create_csrf_token():
    """
    Return the CSRF token for the current session, creating one if
    it doesn't exist yet.

    The token lives in the session (a signed cookie). Because the
    cookie is signed with our SECRET_KEY, an attacker can't forge
    or read it. Each form embeds this token; each POST must echo it
    back; we compare. A cross-site forgery won't know the token.
    """
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def _check_csrf():
    """
    Verify the CSRF token on an incoming POST request.

    Aborts with HTTP 400 if the token is missing or doesn't match
    the one in the session. We use secrets.compare_digest for the
    comparison -- it's constant-time, which avoids timing attacks
    that could otherwise leak whether a guess was "close."
    """
    session_token = session.get("csrf_token")
    form_token = request.form.get("csrf_token", "")

    # If there's no session token at all, the request is invalid.
    if not session_token:
        abort(400, "Missing CSRF session token")

    # Constant-time comparison. Both must be strings.
    if not secrets.compare_digest(str(session_token), str(form_token)):
        abort(400, "CSRF token mismatch")


# ============================================================
# Session-based event storage
#
# We have no database (stateless app). Events entered on each
# quadrant screen are stored in the Flask session (signed cookie)
# so they survive the trip from one screen to the next.
#
# Each event gets a unique ID when stored. IDs are needed so the
# review screen can reliably identify a specific event for editing
# or deleting -- positions in the list shift when you delete, so
# index-based identification is fragile.
#
# Structure stored in session["events"]:
#   A list of dicts, each with keys:
#     id, title, day, start, end, important, urgent
#   (Already-parsed values -- the parsing happens at submit time.)
#
# Structure stored in session["next_event_id"]:
#   An integer counter. Incremented each time we assign an ID. We
#   never reuse IDs -- even after deletion -- so a stale link can
#   never accidentally hit a different event.
# ============================================================

def _get_stored_events():
    """Return the list of events stored in the session (empty if none)."""
    return session.get("events", [])


def _store_events(events):
    """Replace the session's stored events with the given list."""
    session["events"] = events
    # Mark the session modified so Flask re-signs and re-sends the cookie.
    session.modified = True


def _next_event_id():
    """
    Return a fresh unique event ID and advance the counter.

    Counter starts at 1 (not 0) so missing/zero IDs are obviously
    invalid. Never reuses IDs, even when events are deleted.
    """
    current = session.get("next_event_id", 1)
    session["next_event_id"] = current + 1
    session.modified = True
    return current


def _add_events(new_events):
    """
    Append new events to whatever's already stored, assigning each
    a fresh unique ID.

    Mutates each event dict to add an "id" key.
    """
    existing = _get_stored_events()
    for event in new_events:
        event["id"] = _next_event_id()
    existing.extend(new_events)
    _store_events(existing)


def _find_event_by_id(event_id):
    """
    Return (index, event) for the event with the given ID, or
    (None, None) if no such event exists.

    The index is useful for delete/replace operations; the event
    dict itself is useful for rendering and editing.
    """
    for i, event in enumerate(_get_stored_events()):
        if event.get("id") == event_id:
            return i, event
    return None, None


def _delete_event_by_id(event_id):
    """
    Remove the event with the given ID. Returns True if found and
    deleted, False if no such event existed.
    """
    index, _ = _find_event_by_id(event_id)
    if index is None:
        return False
    events = _get_stored_events()
    del events[index]
    _store_events(events)
    return True


def _replace_event_by_id(event_id, new_event_data):
    """
    Replace the event with the given ID. Preserves the ID itself
    so subsequent edit/delete links remain valid.

    Returns True on success, False if no such event existed.
    """
    index, _ = _find_event_by_id(event_id)
    if index is None:
        return False
    # Preserve the ID -- never let an edit change the identifier.
    new_event_data["id"] = event_id
    events = _get_stored_events()
    events[index] = new_event_data
    _store_events(events)
    return True


def _quadrant_key_for_event(event):
    """
    Return the quadrant key ("signal", "urgent", etc.) that matches
    an event's important/urgent booleans.

    Used by the review screen to group events by quadrant.
    """
    for key, info in QUADRANTS.items():
        if (info["important"] == event.get("important")
            and info["urgent"] == event.get("urgent")):
            return key
    # Defensive: any event we stored should match one of the four
    # quadrants. If somehow not, treat it as a generic "other".
    return None


def _events_grouped_by_quadrant():
    """
    Return a dict mapping each quadrant key to its list of events.
    Quadrants with no events still appear with an empty list, so
    the template can render every section even when empty.
    """
    grouped = {key: [] for key in QUADRANTS}
    for event in _get_stored_events():
        key = _quadrant_key_for_event(event)
        if key in grouped:
            grouped[key].append(event)
    return grouped


def _parse_event_id_from_url(event_id_str):
    """
    Convert a URL path component to a positive integer event ID.

    Returns the integer if valid, or None if the string isn't a
    valid positive integer. The route handler treats None as 404.

    Why this exists: the URL contains a user-supplied value. Even
    though Flask's <int:event_id> converter would reject non-digits,
    we layer in an explicit check to make the validation visible
    and to handle the conversion uniformly.
    """
    try:
        value = int(event_id_str)
    except (TypeError, ValueError):
        return None
    if value < 1:
        return None
    return value


# ============================================================
# Parsing form submissions into event dicts
# ============================================================

def _stored_events_to_event_objects():
    """
    Convert the session's event dicts into Event objects for the engine.

    The session stores events as plain dicts (because Flask sessions are
    JSON-serializable cookies, and Event objects aren't). When we need to
    feed them through the engine (issue detection, timesheet rendering),
    we reconstruct them as proper Event objects.

    Why not just store Event objects? Because:
      1. Flask sessions serialize to JSON in the signed cookie
      2. Event objects contain validation logic; storing them as dicts
         keeps the session lean and the validation is re-applied here
         when we reconstruct

    Returns:
        A list of Event objects, one per stored event.

    Raises:
        ValueError / TypeError if any stored event somehow has invalid
        data (e.g. a corrupted session). The route handler should
        catch this and show an error.
    """
    events = []
    for stored in _get_stored_events():
        events.append(Event(
            title=stored["title"],
            day=stored["day"],
            start=stored["start"],
            end=stored["end"],
            important=stored.get("important"),
            urgent=stored.get("urgent"),
        ))
    return events


def _build_download_filename():
    """
    Build a date-stamped filename for the timesheet download.

    Uses the same convention as the CLI exporter so files from the web
    and the CLI look interchangeable. Built server-side from a date --
    no user input touches the filename, so injection is impossible.
    """
    from datetime import date
    return f"timesheet_{date.today().isoformat()}.txt"


def _parse_quadrant_submission(form, quadrant_key):
    """
    Turn a submitted quadrant form into a list of event dicts.

    The form contains parallel arrays: title[], day[], start[], end[]
    -- one entry per row the user filled in. We zip them together,
    skip fully-blank rows, validate each non-blank row through the
    engine's parsers, and build event dicts.

    Args:
        form: the request.form object (a MultiDict).
        quadrant_key: which quadrant we're on ("signal", etc.).
            Determines the important/urgent booleans applied to
            every event in this submission.

    Returns:
        A tuple (events, errors):
          events -- list of valid event dicts ready to store
          errors -- list of human-readable error strings for rows
                    that failed validation (with row numbers)

    Why return errors instead of raising? Same "parse what you can"
    philosophy as the dump parser: one bad row shouldn't discard the
    user's other good rows. We collect errors and show them.
    """
    quadrant = QUADRANTS[quadrant_key]

    # getlist returns all values for a repeated field name.
    titles = form.getlist("title")
    days = form.getlist("day")
    starts = form.getlist("start")
    ends = form.getlist("end")

    events = []
    errors = []

    # All four arrays should be the same length (one per row). Use the
    # longest to be safe, treating missing entries as blank.
    row_count = max(len(titles), len(days), len(starts), len(ends), 0)

    for i in range(row_count):
        # Safely pull each field for this row, defaulting to "".
        title = titles[i].strip() if i < len(titles) else ""
        day_str = days[i].strip() if i < len(days) else ""
        start_str = starts[i].strip() if i < len(starts) else ""
        end_str = ends[i].strip() if i < len(ends) else ""

        # Skip fully-blank rows silently -- they're just unused form
        # slots, not errors.
        if not title and not day_str and not start_str and not end_str:
            continue

        # A partially-filled row IS an error -- the user started a row
        # but didn't finish it. Tell them which row.
        if not (title and day_str and start_str and end_str):
            errors.append(
                f"Row {i + 1}: all fields (title, day, start, end) are "
                f"required. Skipped."
            )
            continue

        # Validate through the engine's parsers. Any failure becomes a
        # per-row error, not a crash.
        try:
            day = parse_day(day_str)
            start = parse_time(start_str)
            end = parse_time(end_str)
            if end <= start:
                errors.append(
                    f"Row {i + 1} ('{title}'): end time must be after "
                    f"start time. Skipped."
                )
                continue
        except (ValueError, TypeError) as e:
            errors.append(f"Row {i + 1} ('{title}'): {e}. Skipped.")
            continue

        # Build the event dict. The important/urgent booleans come from
        # the QUADRANT, not from user input.
        events.append({
            "title": title,
            "day": day,
            "start": start,
            "end": end,
            "important": quadrant["important"],
            "urgent": quadrant["urgent"],
        })

    return events, errors


# ============================================================
# App factory
# ============================================================

def create_app(testing=False):
    """
    Build and configure a Flask application instance.

    Args:
        testing (bool): True for unit tests (predictable config,
            no HTTPS-only cookies). False for real use.

    Returns:
        A configured Flask application.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ---- SECRET_KEY (signs session cookies AND CSRF tokens) ----
    secret_key_from_env = os.environ.get("FLASK_SECRET_KEY")
    if secret_key_from_env:
        app.config["SECRET_KEY"] = secret_key_from_env
    else:
        app.config["SECRET_KEY"] = secrets.token_hex(32)

    # ---- Cookie security flags ----
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = not testing

    # ---- Request size cap ----
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES

    if testing:
        app.config["TESTING"] = True
        # In tests we keep CSRF ON (we want to test it) but the test
        # client can read the token from the session, so it still works.

    # ---- Make the CSRF token available to every template ----
    # This injects csrf_token() into the Jinja environment so any
    # template can call it without the route passing it explicitly.
    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": _get_or_create_csrf_token}

    register_routes(app)

    return app


def register_routes(app):
    """Attach all URL routes to the given app."""

    @app.route("/")
    def index():
        """The welcome / landing page."""
        return render_template("index.html")

    @app.route("/plan/<quadrant_key>", methods=["GET", "POST"])
    def quadrant(quadrant_key):
        """
        Show and process one quadrant's event-entry form.

        GET  -> render the empty form for this quadrant.
        POST -> validate the submitted events, store the good ones,
                show any per-row errors, and (on success) move to the
                next quadrant.

        The <quadrant_key> URL part picks which quadrant. We validate
        it against our known QUADRANTS dict -- an unknown key is a 404.
        """
        # Reject unknown quadrant keys. Never trust the URL.
        if quadrant_key not in QUADRANTS:
            abort(404)

        quadrant_info = QUADRANTS[quadrant_key]

        if request.method == "POST":
            # CSRF check FIRST, before processing anything.
            _check_csrf()

            events, errors = _parse_quadrant_submission(
                request.form, quadrant_key
            )

            # Store whatever validated successfully.
            if events:
                _add_events(events)

            # If there were row errors, re-show THIS form with the
            # errors so the user can fix them. We don't advance.
            if errors:
                return render_template(
                    "quadrant_form.html",
                    quadrant_key=quadrant_key,
                    quadrant=quadrant_info,
                    errors=errors,
                    saved_count=len(events),
                    total_steps=TOTAL_QUADRANT_STEPS,
                )

            # Success: move to the next quadrant, or (if we're on the
            # last one) to the review screen where the user can edit
            # or delete any event before generating the timesheet.
            next_key = quadrant_info["next"]
            if next_key:
                return redirect(url_for("quadrant", quadrant_key=next_key))
            else:
                # Last quadrant -- proceed to the review screen.
                return redirect(url_for("review"))

        # GET: render the empty form.
        return render_template(
            "quadrant_form.html",
            quadrant_key=quadrant_key,
            quadrant=quadrant_info,
            errors=[],
            saved_count=0,
            total_steps=TOTAL_QUADRANT_STEPS,
        )

    @app.route("/review")
    def review():
        """
        The review screen. Shows all entered events grouped by
        quadrant, with edit and delete options for each.

        Reached after the user submits the last quadrant (Noise),
        or any time during the flow if they navigate to /review
        directly (e.g. via a link we may add later).
        """
        grouped = _events_grouped_by_quadrant()
        total_count = sum(len(events) for events in grouped.values())
        return render_template(
            "review.html",
            grouped=grouped,
            total_count=total_count,
            quadrants=QUADRANTS,
        )

    @app.route("/delete/<event_id>", methods=["POST"])
    def delete_event(event_id):
        """
        Delete a single event by ID.

        Why POST (not GET): deletion is a state-changing action.
        GET-based delete links are a CSRF risk -- any page that
        loads a URL (even as an image) could trigger the action
        without the user's intent. POST + CSRF token blocks this.
        """
        _check_csrf()

        parsed_id = _parse_event_id_from_url(event_id)
        if parsed_id is None:
            abort(400, "Invalid event ID")

        _delete_event_by_id(parsed_id)
        # Whether the event existed or not, return to the review
        # screen. We don't tell the caller "no such event" because
        # the only way to get here is from a review screen link --
        # if the ID is gone, the desired end state (event not
        # present) is already achieved.
        return redirect(url_for("review"))

    @app.route("/edit/<event_id>", methods=["GET", "POST"])
    def edit_event(event_id):
        """
        Edit a single event by ID.

        GET  -> render the edit form pre-filled with the event's
                current values.
        POST -> validate the new values; if good, replace the event
                and return to review. If bad, re-render with errors.
        """
        parsed_id = _parse_event_id_from_url(event_id)
        if parsed_id is None:
            abort(404)

        _, event = _find_event_by_id(parsed_id)
        if event is None:
            abort(404)

        # Determine which quadrant this event belongs to, so the edit
        # form can show the user what priority it has.
        quadrant_key = _quadrant_key_for_event(event)
        quadrant_info = QUADRANTS.get(quadrant_key)

        if request.method == "POST":
            _check_csrf()

            # Validate the submitted fields the same way new events
            # are validated. We re-use the engine's parsers.
            title = request.form.get("title", "").strip()
            day_str = request.form.get("day", "").strip()
            start_str = request.form.get("start", "").strip()
            end_str = request.form.get("end", "").strip()

            errors = []
            day = start = end = None

            if not title:
                errors.append("Title is required.")
            if not day_str:
                errors.append("Day is required.")
            if not start_str:
                errors.append("Start time is required.")
            if not end_str:
                errors.append("End time is required.")

            # If basic-presence checks passed, try parsing.
            if not errors:
                try:
                    day = parse_day(day_str)
                except (ValueError, TypeError) as e:
                    errors.append(f"Day: {e}")
                try:
                    start = parse_time(start_str)
                except (ValueError, TypeError) as e:
                    errors.append(f"Start time: {e}")
                try:
                    end = parse_time(end_str)
                except (ValueError, TypeError) as e:
                    errors.append(f"End time: {e}")
                if (start is not None and end is not None and end <= start):
                    errors.append("End time must be after start time.")

            if errors:
                # Re-render the edit form with the user's submitted
                # values (so they don't have to retype) and the errors.
                return render_template(
                    "edit_event.html",
                    event={
                        "id": parsed_id,
                        "title": title,
                        "day": day_str,
                        "start": start_str,
                        "end": end_str,
                    },
                    quadrant=quadrant_info,
                    errors=errors,
                    submitted=True,
                )

            # All clean -- replace the event. Preserve the ID and the
            # priority booleans (priority can't change via edit; the
            # user would delete and re-add in a different quadrant).
            new_event_data = {
                "title": title,
                "day": day,
                "start": start,
                "end": end,
                "important": event["important"],
                "urgent": event["urgent"],
            }
            _replace_event_by_id(parsed_id, new_event_data)
            return redirect(url_for("review"))

        # GET: render the form pre-filled. We pass the stored event
        # but convert its internal numeric fields back to user-friendly
        # display strings so the form is editable as text.
        from src.engine.time_math import to_total_minutes  # avoid top-level import; just for display
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                     "Friday", "Saturday", "Sunday"]
        display_event = {
            "id": parsed_id,
            "title": event["title"],
            "day": day_names[event["day"]],
            # Render military int back to HH:MM for the form.
            "start": f"{event['start'] // 100:02d}:{event['start'] % 100:02d}",
            "end": f"{event['end'] // 100:02d}:{event['end'] % 100:02d}",
        }
        return render_template(
            "edit_event.html",
            event=display_event,
            quadrant=quadrant_info,
            errors=[],
            submitted=False,
        )
    @app.route("/timesheet")
    def show_timesheet():
        """
        Show the rendered weekly timesheet.

        Pulls the user's events out of the session, converts them
        into Event objects, runs them through the engine to find
        issues, then renders them through the timesheet formatter.
        Displays the result in a <pre> block so whitespace and
        alignment are preserved exactly as the engine emits them.

        If no events have been entered yet, shows a friendly message
        with a link to start, rather than an empty 7-day "Open
        Availability" timesheet.
        """
        stored = _get_stored_events()

        if not stored:
            # Empty case: no events. Show a friendly empty-state page.
            return render_template("timesheet_empty.html")

        # Convert stored dicts to Event objects and run the engine.
        # We're defensive about errors here -- a corrupted session
        # could in theory produce invalid event data. If that happens,
        # tell the user clearly instead of crashing with a 500.
        try:
            event_objects = _stored_events_to_event_objects()
            issues = find_all_issues(event_objects)
            rendered = render_timesheet(event_objects, issues)
        except (ValueError, TypeError) as e:
            return render_template(
                "timesheet_error.html",
                error_message=str(e),
            ), 500

        # Counts for the page header summary.
        return render_template(
            "timesheet.html",
            rendered_timesheet=rendered,
            event_count=len(event_objects),
            issue_count=len(issues),
        )

    @app.route("/timesheet/download")
    def download_timesheet():
        """
        Send the rendered timesheet to the browser as a downloadable
        .txt file.

        Why a separate route instead of a button on /timesheet?
        Downloads need different HTTP headers (Content-Disposition,
        Content-Type: text/plain) than HTML pages. Cleaner to have
        a dedicated endpoint than to switch behavior based on a query
        parameter.

        Security:
          - Content comes from the user's own session, never user-
            controlled file paths. No path traversal possible.
          - Filename is built server-side from today's date. No user
            input touches it.
          - Content-Type explicitly set to text/plain so browsers
            don't try to interpret the response as HTML.
        """
        stored = _get_stored_events()

        if not stored:
            # Nothing to download. Bounce back to the timesheet page
            # which will show the empty-state message.
            return redirect(url_for("show_timesheet"))

        try:
            event_objects = _stored_events_to_event_objects()
            issues = find_all_issues(event_objects)
            rendered = render_timesheet(event_objects, issues)
        except (ValueError, TypeError):
            # Corrupted session; redirect to the timesheet page which
            # will surface the error properly.
            return redirect(url_for("show_timesheet"))

        filename = _build_download_filename()

        response = Response(
            rendered,
            mimetype="text/plain",
        )
        # Content-Disposition: attachment triggers a download instead
        # of inline display. The filename here ends up as the default
        # save-as name in the browser's download dialog.
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{filename}"'
        )
        # Explicit Content-Type with charset so encoding is unambiguous.
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        return response

    @app.route("/reset")
    def reset():
        """
        Clear all stored events and start over.

        Useful during the flow if the user wants a fresh start.
        Clears the events AND the next_event_id counter so a fresh
        session starts numbering from 1 again. Keeps the CSRF token
        (no need to rotate it just because the user reset).
        """
        session.pop("events", None)
        session.pop("next_event_id", None)
        return redirect(url_for("index"))

    @app.route("/health")
    def health():
        """
        Health check endpoint for Railway (and any other monitoring).

        Returns a plain "OK" with HTTP 200 if the application process
        is alive and serving requests. Deliberately minimal: a health
        check should be CHEAP so it can be hit frequently without
        adding load.

        We do NOT check deeper things here (DB connections, etc.)
        because we don't have a DB, and because a slow health check
        defeats the purpose -- a hung deep check causes false alarms.

        Why this matters for Railway:
            Railway can detect when an app crashes by polling this
            endpoint. If it stops responding, Railway can restart the
            container automatically.
        """
        return "OK", 200, {"Content-Type": "text/plain"}

    # ---- Error handlers ----
    # Custom pages for the two errors a real user is most likely to
    # see. Other errors (400, 403, 405) keep Flask's defaults --
    # they're mostly developer/attacker-facing and the defaults are
    # adequate.

    @app.errorhandler(404)
    def not_found(error):
        """Friendly 404 page. Returns 404 status so caches behave correctly."""
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """
        Friendly 500 page.

        Important: we do NOT include the actual exception message
        in the response. Stack traces and exception details could
        leak sensitive information (file paths, internal structure,
        what threw). Users get a generic apology; details go to
        server logs only.
        """
        return render_template("500.html"), 500


# ---- Module-level app for production (gunicorn / Railway) ----
app = create_app(testing=False)


# ---- Local development entry point ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # debug=False always -- debug mode is a remote-code-execution risk.
    app.run(host="0.0.0.0", port=port, debug=False)
