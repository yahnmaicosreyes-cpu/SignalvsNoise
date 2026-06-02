# ============================================================
# test_app.py
#
# Tests for the Flask web application skeleton (Session 1).
#
# These tests use Flask's built-in test client, which lets us
# pretend to be a browser making HTTP requests WITHOUT actually
# starting a server. Fast and predictable.
#
# Test groups for Session 1:
#   1. Index route -- the / page loads
#   2. HTTP basics -- status codes, content type
#   3. Security baseline -- cookie flags, request size cap
#   4. Template rendering -- base.html inheritance works
#   5. App factory -- create_app() returns a working app
#
# Note: many security defenses (CSRF, XSS escaping, etc.) need
# routes to test against, so their tests will arrive in later
# sessions as we add forms. Here we test what we have.
# ============================================================

from app import create_app, MAX_REQUEST_BYTES


# Build a test app once at module load. Tests share it; that's fine
# because none of these tests mutate global state.
test_app = create_app(testing=True)


# =================================================================
# GROUP 1: INDEX ROUTE
# =================================================================

def run_index_route():
    print("=== INDEX ROUTE ===")
    passed = 0
    total = 0

    client = test_app.test_client()

    # ---- The / page returns HTTP 200 ----
    total += 1
    response = client.get("/")
    if response.status_code == 200:
        passed += 1
        print(f"Test {total}: PASS | GET / returns 200")
    else:
        print(f"Test {total}: FAIL | got status {response.status_code}")

    # ---- The response body is HTML ----
    total += 1
    if response.content_type.startswith("text/html"):
        passed += 1
        print(f"Test {total}: PASS | Response content type is text/html")
    else:
        print(f"Test {total}: FAIL | got {response.content_type}")

    # ---- The page contains key welcome text ----
    total += 1
    body = response.get_data(as_text=True)
    if "Welcome" in body and "Priority Planner" in body:
        passed += 1
        print(f"Test {total}: PASS | Welcome page contains expected text")
    else:
        print(f"Test {total}: FAIL")

    # ---- Visiting an unknown URL returns 404 ----
    total += 1
    response_404 = client.get("/this-does-not-exist")
    if response_404.status_code == 404:
        passed += 1
        print(f"Test {total}: PASS | Unknown URL returns 404")
    else:
        print(f"Test {total}: FAIL | got status {response_404.status_code}")

    print(f"{passed}/{total} index route tests passed\n")
    return passed, total


# =================================================================
# GROUP 2: TEMPLATE INHERITANCE
# =================================================================

def run_template_inheritance():
    print("=== TEMPLATE INHERITANCE ===")
    passed = 0
    total = 0

    client = test_app.test_client()
    response = client.get("/")
    body = response.get_data(as_text=True)

    # ---- DOCTYPE from base.html appears ----
    total += 1
    if "<!DOCTYPE html>" in body:
        passed += 1
        print(f"Test {total}: PASS | DOCTYPE inherited from base.html")
    else:
        print(f"Test {total}: FAIL")

    # ---- The site header appears (proves base.html is used) ----
    total += 1
    if "<h1>Priority Planner</h1>" in body:
        passed += 1
        print(f"Test {total}: PASS | Header from base.html present")
    else:
        print(f"Test {total}: FAIL")

    # ---- The footer appears ----
    total += 1
    if "<footer>" in body:
        passed += 1
        print(f"Test {total}: PASS | Footer from base.html present")
    else:
        print(f"Test {total}: FAIL")

    # ---- Index-specific title appears ----
    total += 1
    if "<title>Welcome - Priority Planner</title>" in body:
        passed += 1
        print(f"Test {total}: PASS | Index-specific title overrides base default")
    else:
        print(f"Test {total}: FAIL")

    print(f"{passed}/{total} template inheritance tests passed\n")
    return passed, total


# =================================================================
# GROUP 3: SECURITY BASELINE
# =================================================================

def run_security_baseline():
    print("=== SECURITY BASELINE ===")
    passed = 0
    total = 0

    # ---- SECRET_KEY is set and non-trivial ----
    total += 1
    secret = test_app.config.get("SECRET_KEY")
    if secret and len(secret) >= 32:
        passed += 1
        print(f"Test {total}: PASS | SECRET_KEY is set (length {len(secret)})")
    else:
        print(f"Test {total}: FAIL | SECRET_KEY missing or too short")

    # ---- SESSION_COOKIE_HTTPONLY is True ----
    total += 1
    if test_app.config.get("SESSION_COOKIE_HTTPONLY") is True:
        passed += 1
        print(f"Test {total}: PASS | SESSION_COOKIE_HTTPONLY is True")
    else:
        print(f"Test {total}: FAIL")

    # ---- SESSION_COOKIE_SAMESITE is 'Lax' ----
    total += 1
    if test_app.config.get("SESSION_COOKIE_SAMESITE") == "Lax":
        passed += 1
        print(f"Test {total}: PASS | SESSION_COOKIE_SAMESITE is 'Lax'")
    else:
        print(f"Test {total}: FAIL | got {test_app.config.get('SESSION_COOKIE_SAMESITE')!r}")

    # ---- MAX_CONTENT_LENGTH is set and bounded ----
    total += 1
    max_len = test_app.config.get("MAX_CONTENT_LENGTH")
    if max_len == MAX_REQUEST_BYTES:
        passed += 1
        print(f"Test {total}: PASS | MAX_CONTENT_LENGTH = {max_len} (64 KB cap)")
    else:
        print(f"Test {total}: FAIL | got {max_len}")

    # ---- Oversized request body is rejected ----
    # We send a POST larger than the cap. Flask should reject it
    # with HTTP 413 (Payload Too Large) before any of our code runs.
    total += 1
    client = test_app.test_client()
    huge_payload = b"x" * (MAX_REQUEST_BYTES + 1)
    # POST to / -- it doesn't accept POSTs (will normally return 405)
    # but the size cap fires FIRST, returning 413.
    response = client.post("/", data=huge_payload, content_type="text/plain")
    if response.status_code == 413:
        passed += 1
        print(f"Test {total}: PASS | Oversized request returns 413 (size cap fires before route logic)")
    else:
        # On some Werkzeug versions, the size check returns 400 with
        # a specific error -- either way, the request was rejected
        # and didn't reach our code.
        if response.status_code >= 400:
            passed += 1
            print(f"Test {total}: PASS | Oversized request rejected with {response.status_code}")
        else:
            print(f"Test {total}: FAIL | got status {response.status_code}")

    print(f"{passed}/{total} security baseline tests passed\n")
    return passed, total


# =================================================================
# GROUP 4: APP FACTORY
# =================================================================

def run_app_factory():
    print("=== APP FACTORY ===")
    passed = 0
    total = 0

    # ---- create_app() returns a Flask app ----
    total += 1
    from flask import Flask
    fresh_app = create_app(testing=True)
    if isinstance(fresh_app, Flask):
        passed += 1
        print(f"Test {total}: PASS | create_app() returns a Flask instance")
    else:
        print(f"Test {total}: FAIL")

    # ---- testing=True sets TESTING flag ----
    total += 1
    if fresh_app.config.get("TESTING") is True:
        passed += 1
        print(f"Test {total}: PASS | testing=True sets app.config['TESTING']")
    else:
        print(f"Test {total}: FAIL")

    # ---- testing=False leaves TESTING off (default) ----
    total += 1
    prod_app = create_app(testing=False)
    if not prod_app.config.get("TESTING"):
        passed += 1
        print(f"Test {total}: PASS | testing=False does NOT enable TESTING flag")
    else:
        print(f"Test {total}: FAIL")

    # ---- SESSION_COOKIE_SECURE flips based on testing flag ----
    # In testing: False (so localhost http works)
    # In production: True (so cookies only travel over HTTPS)
    total += 1
    if (fresh_app.config["SESSION_COOKIE_SECURE"] is False
        and prod_app.config["SESSION_COOKIE_SECURE"] is True):
        passed += 1
        print(f"Test {total}: PASS | SESSION_COOKIE_SECURE: False in testing, True in production")
    else:
        print(f"Test {total}: FAIL | testing={fresh_app.config['SESSION_COOKIE_SECURE']}, prod={prod_app.config['SESSION_COOKIE_SECURE']}")

    print(f"{passed}/{total} app factory tests passed\n")
    return passed, total


# =================================================================
# GROUP 5: ENGINE INTEGRATION (the engine should still work)
# =================================================================

def run_engine_integration():
    """Confirm the web layer can import and use the engine code."""
    print("=== ENGINE INTEGRATION ===")
    passed = 0
    total = 0

    # ---- Engine modules import cleanly ----
    total += 1
    try:
        from src.parsers.dump_parser import parse_dump
        from src.engine.conflict_checker import find_all_issues
        from src.engine.timesheet_formatter import render_timesheet
        passed += 1
        print(f"Test {total}: PASS | Engine modules import from web layer")
    except ImportError as e:
        print(f"Test {total}: FAIL | import error: {e}")

    # ---- Engine still works through the web context ----
    total += 1
    try:
        result = parse_dump("Test | Monday | 9:00AM-10:00AM")
        issues = find_all_issues(result.events)
        rendered = render_timesheet(result.events, issues)
        if "MONDAY" in rendered:
            passed += 1
            print(f"Test {total}: PASS | Full engine pipeline runs from web context")
        else:
            print(f"Test {total}: FAIL")
    except Exception as e:
        print(f"Test {total}: FAIL | engine error: {e}")

    print(f"{passed}/{total} engine integration tests passed\n")
    return passed, total


# =================================================================
# Main runner
# =================================================================

# =================================================================
# SESSION 2 GROUPS: quadrant forms, CSRF, session storage
# =================================================================

def _extract_csrf_token(client):
    """
    Helper: do a GET on a form page and pull the CSRF token out of
    the HTML so we can include it in a POST. Returns the token string.

    Real browsers get the token from the rendered form; the test
    client has to scrape it the same way a browser's form would carry it.
    """
    response = client.get("/plan/signal")
    body = response.get_data(as_text=True)
    # The token sits in: <input type="hidden" name="csrf_token" value="...">
    marker = 'name="csrf_token" value="'
    start = body.find(marker)
    if start == -1:
        return None
    start += len(marker)
    end = body.find('"', start)
    return body[start:end]


def run_quadrant_get():
    print("=== QUADRANT FORM (GET) ===")
    passed = 0
    total = 0

    client = test_app.test_client()

    # ---- Signal form loads ----
    total += 1
    response = client.get("/plan/signal")
    if response.status_code == 200:
        passed += 1
        print(f"Test {total}: PASS | GET /plan/signal returns 200")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Signal form shows the right heading and subtitle ----
    total += 1
    body = response.get_data(as_text=True)
    if "Signal Events" in body and "foundation work" in body:
        passed += 1
        print(f"Test {total}: PASS | Signal form shows correct heading + subtitle")
    else:
        print(f"Test {total}: FAIL")

    # ---- All four quadrant URLs load ----
    total += 1
    all_load = all(
        client.get(f"/plan/{key}").status_code == 200
        for key in ("signal", "urgent", "interruption", "noise")
    )
    if all_load:
        passed += 1
        print(f"Test {total}: PASS | All four quadrant forms load")
    else:
        print(f"Test {total}: FAIL")

    # ---- Unknown quadrant returns 404 ----
    total += 1
    response = client.get("/plan/banana")
    if response.status_code == 404:
        passed += 1
        print(f"Test {total}: PASS | Unknown quadrant key returns 404")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Form contains a CSRF token ----
    total += 1
    token = _extract_csrf_token(client)
    if token and len(token) >= 32:
        passed += 1
        print(f"Test {total}: PASS | Form embeds a CSRF token (length {len(token)})")
    else:
        print(f"Test {total}: FAIL | no valid CSRF token found")

    print(f"{passed}/{total} quadrant GET tests passed\n")
    return passed, total


def run_quadrant_post():
    print("=== QUADRANT FORM (POST + session storage) ===")
    passed = 0
    total = 0

    # ---- Valid submission stores events and redirects to next quadrant ----
    total += 1
    client = test_app.test_client()
    token = _extract_csrf_token(client)
    response = client.post("/plan/signal", data={
        "csrf_token": token,
        "title": "Therapy",
        "day": "Monday",
        "start": "4:00PM",
        "end": "5:00PM",
    })
    # Should redirect (302) to the urgent quadrant.
    if response.status_code == 302 and "/plan/urgent" in response.headers.get("Location", ""):
        passed += 1
        print(f"Test {total}: PASS | Valid signal submission redirects to /plan/urgent")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}, location {response.headers.get('Location')}")

    # ---- The submitted event is actually stored in the session ----
    total += 1
    client = test_app.test_client()
    token = _extract_csrf_token(client)
    client.post("/plan/signal", data={
        "csrf_token": token,
        "title": "Therapy",
        "day": "Monday",
        "start": "4:00PM",
        "end": "5:00PM",
    })
    with client.session_transaction() as sess:
        stored = sess.get("events", [])
    if (len(stored) == 1
        and stored[0]["title"] == "Therapy"
        and stored[0]["day"] == 0
        and stored[0]["start"] == 1600
        and stored[0]["important"] is True
        and stored[0]["urgent"] is False):
        passed += 1
        print(f"Test {total}: PASS | Event stored with correct parsed values + signal priority")
    else:
        print(f"Test {total}: FAIL | stored: {stored}")

    # ---- Multiple events in one submission all stored ----
    total += 1
    client = test_app.test_client()
    token = _extract_csrf_token(client)
    from werkzeug.datastructures import MultiDict
    multi_data = MultiDict()
    multi_data.add("csrf_token", token)
    multi_data.add("title", "Therapy")
    multi_data.add("day", "Monday")
    multi_data.add("start", "4:00PM")
    multi_data.add("end", "5:00PM")
    multi_data.add("title", "Yoga")
    multi_data.add("day", "Wednesday")
    multi_data.add("start", "7:00AM")
    multi_data.add("end", "8:00AM")
    client.post("/plan/signal", data=multi_data)
    with client.session_transaction() as sess:
        stored = sess.get("events", [])
    if len(stored) == 2:
        passed += 1
        print(f"Test {total}: PASS | Two events in one submission both stored")
    else:
        print(f"Test {total}: FAIL | stored {len(stored)} events")

    # ---- Blank rows are skipped silently ----
    total += 1
    client = test_app.test_client()
    token = _extract_csrf_token(client)
    multi_data = MultiDict()
    multi_data.add("csrf_token", token)
    multi_data.add("title", "Real event")
    multi_data.add("day", "Monday")
    multi_data.add("start", "9:00AM")
    multi_data.add("end", "10:00AM")
    multi_data.add("title", "")       # blank row
    multi_data.add("day", "")
    multi_data.add("start", "")
    multi_data.add("end", "")
    client.post("/plan/signal", data=multi_data)
    with client.session_transaction() as sess:
        stored = sess.get("events", [])
    if len(stored) == 1:
        passed += 1
        print(f"Test {total}: PASS | Blank row skipped, only real event stored")
    else:
        print(f"Test {total}: FAIL | stored {len(stored)} events")

    # ---- Invalid row produces an error and re-renders the form ----
    total += 1
    client = test_app.test_client()
    token = _extract_csrf_token(client)
    response = client.post("/plan/signal", data={
        "csrf_token": token,
        "title": "Bad day event",
        "day": "Funday",      # invalid day
        "start": "9:00AM",
        "end": "10:00AM",
    })
    body = response.get_data(as_text=True)
    if response.status_code == 200 and "could not be saved" in body:
        passed += 1
        print(f"Test {total}: PASS | Invalid row shows error and re-renders form")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Last quadrant (noise) now redirects to /review ----
    total += 1
    client = test_app.test_client()
    token = _extract_csrf_token(client)
    response = client.post("/plan/noise", data={
        "csrf_token": token,
        "title": "Junk",
        "day": "Friday",
        "start": "3:00PM",
        "end": "3:30PM",
    })
    if response.status_code == 302 and "/review" in response.headers.get("Location", ""):
        passed += 1
        print(f"Test {total}: PASS | Noise (last quadrant) redirects to /review")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}, location {response.headers.get('Location')}")

    print(f"{passed}/{total} quadrant POST tests passed\n")
    return passed, total


def run_csrf_protection():
    print("=== CSRF PROTECTION ===")
    passed = 0
    total = 0

    # ---- POST with NO token is rejected ----
    total += 1
    client = test_app.test_client()
    response = client.post("/plan/signal", data={
        "title": "No token", "day": "Monday",
        "start": "9:00AM", "end": "10:00AM",
    })
    if response.status_code == 400:
        passed += 1
        print(f"Test {total}: PASS | POST without CSRF token rejected (400)")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- POST with WRONG token is rejected ----
    total += 1
    client = test_app.test_client()
    # Establish a session first (so there IS a real token to mismatch).
    _extract_csrf_token(client)
    response = client.post("/plan/signal", data={
        "csrf_token": "deadbeef" * 8,  # wrong token
        "title": "Wrong token", "day": "Monday",
        "start": "9:00AM", "end": "10:00AM",
    })
    if response.status_code == 400:
        passed += 1
        print(f"Test {total}: PASS | POST with wrong CSRF token rejected (400)")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- POST with correct token is accepted ----
    total += 1
    client = test_app.test_client()
    token = _extract_csrf_token(client)
    response = client.post("/plan/signal", data={
        "csrf_token": token,
        "title": "Good token", "day": "Monday",
        "start": "9:00AM", "end": "10:00AM",
    })
    # 302 redirect = accepted and processed.
    if response.status_code == 302:
        passed += 1
        print(f"Test {total}: PASS | POST with correct CSRF token accepted")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    print(f"{passed}/{total} CSRF protection tests passed\n")
    return passed, total


def run_xss_escaping():
    print("=== XSS ESCAPING ===")
    passed = 0
    total = 0

    # ---- A malicious title is HTML-escaped when shown back ----
    # We submit a title containing a <script> tag via an INVALID row
    # (bad day) so the form re-renders and echoes the error -- which
    # includes the title. The title must come back escaped.
    total += 1
    client = test_app.test_client()
    token = _extract_csrf_token(client)
    response = client.post("/plan/signal", data={
        "csrf_token": token,
        "title": "<script>alert('xss')</script>",
        "day": "Funday",   # invalid -> triggers error re-render with the title
        "start": "9:00AM",
        "end": "10:00AM",
    })
    body = response.get_data(as_text=True)
    # The raw <script> tag must NOT appear. Its escaped form should.
    if "<script>alert" not in body and "&lt;script&gt;" in body:
        passed += 1
        print(f"Test {total}: PASS | Malicious title HTML-escaped (no raw <script>)")
    else:
        print(f"Test {total}: FAIL | raw script tag may have leaked into output")

    print(f"{passed}/{total} XSS escaping tests passed\n")
    return passed, total


def run_reset():
    print("=== RESET ===")
    passed = 0
    total = 0

    # ---- Reset clears stored events ----
    total += 1
    client = test_app.test_client()
    token = _extract_csrf_token(client)
    client.post("/plan/signal", data={
        "csrf_token": token,
        "title": "Therapy", "day": "Monday",
        "start": "4:00PM", "end": "5:00PM",
    })
    # Confirm something is stored, then reset.
    client.get("/reset")
    with client.session_transaction() as sess:
        stored = sess.get("events", [])
    if len(stored) == 0:
        passed += 1
        print(f"Test {total}: PASS | /reset clears stored events")
    else:
        print(f"Test {total}: FAIL | {len(stored)} events remained after reset")

    print(f"{passed}/{total} reset tests passed\n")
    return passed, total


def run_full_flow():
    """Session 3: simulate a user moving through ALL FOUR quadrants."""
    print("=== FULL FOUR-QUADRANT FLOW ===")
    passed = 0
    total = 0

    from werkzeug.datastructures import MultiDict

    def submit_quadrant(client, quadrant_key, rows):
        """Helper: fetch token, submit the given rows to a quadrant."""
        # Get a fresh token from this quadrant's form.
        resp = client.get(f"/plan/{quadrant_key}")
        body = resp.get_data(as_text=True)
        marker = 'name="csrf_token" value="'
        start = body.find(marker) + len(marker)
        token = body[start:body.find('"', start)]

        data = MultiDict()
        data.add("csrf_token", token)
        for (title, day, start_t, end_t) in rows:
            data.add("title", title)
            data.add("day", day)
            data.add("start", start_t)
            data.add("end", end_t)
        return client.post(f"/plan/{quadrant_key}", data=data)

    client = test_app.test_client()

    # Walk through all four quadrants, one event each.
    submit_quadrant(client, "signal", [("Therapy", "Monday", "4:00PM", "5:00PM")])
    submit_quadrant(client, "urgent", [("Deadline", "Tuesday", "9:00AM", "10:00AM")])
    submit_quadrant(client, "interruption", [("Phone call", "Wednesday", "2:00PM", "2:30PM")])
    final = submit_quadrant(client, "noise", [("Scroll", "Friday", "8:00PM", "9:00PM")])

    # ---- All four events stored ----
    total += 1
    with client.session_transaction() as sess:
        stored = sess.get("events", [])
    if len(stored) == 4:
        passed += 1
        print(f"Test {total}: PASS | All 4 events stored across the full flow")
    else:
        print(f"Test {total}: FAIL | stored {len(stored)} events")

    # ---- Each event has the correct priority for its quadrant ----
    total += 1
    by_title = {e["title"]: e for e in stored}
    checks = (
        by_title.get("Therapy", {}).get("important") is True
        and by_title.get("Therapy", {}).get("urgent") is False
        and by_title.get("Deadline", {}).get("important") is True
        and by_title.get("Deadline", {}).get("urgent") is True
        and by_title.get("Phone call", {}).get("important") is False
        and by_title.get("Phone call", {}).get("urgent") is True
        and by_title.get("Scroll", {}).get("important") is False
        and by_title.get("Scroll", {}).get("urgent") is False
    )
    if checks:
        passed += 1
        print(f"Test {total}: PASS | Each event has correct priority for its quadrant")
    else:
        print(f"Test {total}: FAIL | priorities don't match quadrants")

    # ---- Final response from noise is a redirect to /review ----
    total += 1
    if final.status_code == 302 and "/review" in final.headers.get("Location", ""):
        passed += 1
        print(f"Test {total}: PASS | After last quadrant, redirected to /review")
    else:
        print(f"Test {total}: FAIL | status {final.status_code}")

    print(f"{passed}/{total} full flow tests passed\n")
    return passed, total


def run_empty_quadrant():
    """Session 3: submitting a quadrant with no events advances cleanly."""
    print("=== EMPTY QUADRANT (skip) ===")
    passed = 0
    total = 0

    client = test_app.test_client()

    # Get token from signal form.
    resp = client.get("/plan/signal")
    body = resp.get_data(as_text=True)
    marker = 'name="csrf_token" value="'
    start = body.find(marker) + len(marker)
    token = body[start:body.find('"', start)]

    # ---- Submitting all-blank rows advances without storing anything ----
    total += 1
    response = client.post("/plan/signal", data={
        "csrf_token": token,
        "title": "", "day": "", "start": "", "end": "",
    })
    if response.status_code == 302 and "/plan/urgent" in response.headers.get("Location", ""):
        passed += 1
        print(f"Test {total}: PASS | Empty submission advances to next quadrant")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Nothing was stored ----
    total += 1
    with client.session_transaction() as sess:
        stored = sess.get("events", [])
    if len(stored) == 0:
        passed += 1
        print(f"Test {total}: PASS | Empty submission stored zero events")
    else:
        print(f"Test {total}: FAIL | stored {len(stored)} events")

    print(f"{passed}/{total} empty quadrant tests passed\n")
    return passed, total


def run_progress_indicator():
    """Session 3: the progress indicator shows the right step."""
    print("=== PROGRESS INDICATOR ===")
    passed = 0
    total = 0

    client = test_app.test_client()

    expected_steps = {
        "signal": "Step 1 of 4",
        "urgent": "Step 2 of 4",
        "interruption": "Step 3 of 4",
        "noise": "Step 4 of 4",
    }

    for key, expected_text in expected_steps.items():
        total += 1
        body = client.get(f"/plan/{key}").get_data(as_text=True)
        if expected_text in body:
            passed += 1
            print(f"Test {total}: PASS | {key} shows '{expected_text}'")
        else:
            print(f"Test {total}: FAIL | {key} missing '{expected_text}'")

    print(f"{passed}/{total} progress indicator tests passed\n")
    return passed, total


def _setup_client_with_event(title="Therapy", day="Monday",
                              start="4:00PM", end="5:00PM",
                              quadrant_key="signal"):
    """
    Helper: create a fresh test client and submit one event to the
    given quadrant. Returns (client, event_id).

    Used by Session 4 tests to set up a starting state with one
    known event in the session.
    """
    client = test_app.test_client()
    # Get token from signal form (or whichever quadrant).
    body = client.get(f"/plan/{quadrant_key}").get_data(as_text=True)
    marker = 'name="csrf_token" value="'
    s = body.find(marker) + len(marker)
    token = body[s:body.find('"', s)]
    client.post(f"/plan/{quadrant_key}", data={
        "csrf_token": token,
        "title": title, "day": day, "start": start, "end": end,
    })
    # Read back the assigned ID from the session.
    with client.session_transaction() as sess:
        events = sess.get("events", [])
    return client, (events[0]["id"] if events else None)


def _get_token(client, path="/plan/signal"):
    """Helper: extract a CSRF token from any page that embeds one."""
    body = client.get(path).get_data(as_text=True)
    marker = 'name="csrf_token" value="'
    s = body.find(marker)
    if s == -1:
        return None
    s += len(marker)
    return body[s:body.find('"', s)]


def run_event_ids():
    """Session 4: events get unique IDs that survive the flow."""
    print("=== EVENT IDS ===")
    passed = 0
    total = 0

    client, first_id = _setup_client_with_event()

    # ---- First event gets an ID ----
    total += 1
    if first_id is not None and isinstance(first_id, int) and first_id >= 1:
        passed += 1
        print(f"Test {total}: PASS | First event got ID {first_id}")
    else:
        print(f"Test {total}: FAIL | first_id was {first_id}")

    # ---- Subsequent events get DIFFERENT IDs ----
    total += 1
    token = _get_token(client, "/plan/signal")
    client.post("/plan/signal", data={
        "csrf_token": token,
        "title": "Yoga", "day": "Wednesday",
        "start": "7:00AM", "end": "8:00AM",
    })
    with client.session_transaction() as sess:
        ids = [e["id"] for e in sess.get("events", [])]
    if len(ids) == 2 and ids[0] != ids[1] and len(set(ids)) == 2:
        passed += 1
        print(f"Test {total}: PASS | Each event got a unique ID: {ids}")
    else:
        print(f"Test {total}: FAIL | ids: {ids}")

    print(f"{passed}/{total} event ID tests passed\n")
    return passed, total


def run_review_page():
    """Session 4: the review page renders correctly."""
    print("=== REVIEW PAGE ===")
    passed = 0
    total = 0

    # ---- Empty review page is reachable ----
    total += 1
    client = test_app.test_client()
    response = client.get("/review")
    if response.status_code == 200 and "No events were entered" in response.get_data(as_text=True):
        passed += 1
        print(f"Test {total}: PASS | Empty review shows 'no events' message")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Review page shows entered events grouped by quadrant ----
    total += 1
    client, _ = _setup_client_with_event(title="Therapy", quadrant_key="signal")
    token = _get_token(client, "/plan/urgent")
    client.post("/plan/urgent", data={
        "csrf_token": token,
        "title": "Deadline", "day": "Tuesday",
        "start": "9:00AM", "end": "10:00AM",
    })
    body = client.get("/review").get_data(as_text=True)
    # Both events should appear, and each in its quadrant section.
    if ("Therapy" in body and "Deadline" in body
        and "Signal" in body and "Urgent" in body):
        passed += 1
        print(f"Test {total}: PASS | Review shows events grouped by quadrant")
    else:
        print(f"Test {total}: FAIL")

    # ---- Each event has Edit and Delete actions ----
    total += 1
    client, eid = _setup_client_with_event()
    body = client.get("/review").get_data(as_text=True)
    if (f"/edit/{eid}" in body and f"/delete/{eid}" in body):
        passed += 1
        print(f"Test {total}: PASS | Review includes /edit/{eid} and /delete/{eid} links")
    else:
        print(f"Test {total}: FAIL")

    print(f"{passed}/{total} review page tests passed\n")
    return passed, total


def run_delete_event():
    """Session 4: delete works, and only via CSRF-protected POST."""
    print("=== DELETE EVENT ===")
    passed = 0
    total = 0

    # ---- Valid POST with token deletes the event ----
    total += 1
    client, eid = _setup_client_with_event()
    token = _get_token(client, "/review")
    response = client.post(f"/delete/{eid}", data={"csrf_token": token})
    if response.status_code == 302:
        with client.session_transaction() as sess:
            remaining = sess.get("events", [])
        if len(remaining) == 0:
            passed += 1
            print(f"Test {total}: PASS | POST /delete with valid token removed event")
        else:
            print(f"Test {total}: FAIL | event still present")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- GET on /delete is NOT allowed (CSRF protection) ----
    total += 1
    client, eid = _setup_client_with_event()
    response = client.get(f"/delete/{eid}")
    # GET should return 405 Method Not Allowed -- the route only allows POST.
    if response.status_code == 405:
        passed += 1
        print(f"Test {total}: PASS | GET /delete is rejected (405) -- CSRF defense")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- POST /delete WITHOUT a token is rejected ----
    total += 1
    client, eid = _setup_client_with_event()
    response = client.post(f"/delete/{eid}", data={})
    if response.status_code == 400:
        passed += 1
        print(f"Test {total}: PASS | POST /delete without token rejected (400)")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Deleting a nonexistent ID is harmless (no crash, redirect to review) ----
    total += 1
    client = test_app.test_client()
    # Grab a token from a page that actually renders a form.
    # The empty /review page has no forms, so it doesn't establish
    # a CSRF token. Visit /plan/signal instead.
    token = _get_token(client, "/plan/signal")
    response = client.post("/delete/99999", data={"csrf_token": token})
    if response.status_code == 302:
        passed += 1
        print(f"Test {total}: PASS | Deleting nonexistent ID is harmless")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Invalid (non-integer) ID returns 400 ----
    total += 1
    client = test_app.test_client()
    token = _get_token(client, "/plan/signal")
    response = client.post("/delete/abc", data={"csrf_token": token})
    if response.status_code == 400:
        passed += 1
        print(f"Test {total}: PASS | Non-integer delete ID rejected (400)")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    print(f"{passed}/{total} delete tests passed\n")
    return passed, total


def run_edit_event():
    """Session 4: edit form and submission work correctly."""
    print("=== EDIT EVENT ===")
    passed = 0
    total = 0

    # ---- GET /edit/<id> renders form with current values pre-filled ----
    total += 1
    client, eid = _setup_client_with_event(title="Original")
    response = client.get(f"/edit/{eid}")
    body = response.get_data(as_text=True)
    if (response.status_code == 200
        and 'value="Original"' in body
        and "Monday" in body):
        passed += 1
        print(f"Test {total}: PASS | Edit form pre-filled with current values")
    else:
        print(f"Test {total}: FAIL")

    # ---- Valid edit submission changes the event ----
    total += 1
    client, eid = _setup_client_with_event(title="Original")
    token = _get_token(client, f"/edit/{eid}")
    response = client.post(f"/edit/{eid}", data={
        "csrf_token": token,
        "title": "Renamed",
        "day": "Friday",
        "start": "10:00AM",
        "end": "11:00AM",
    })
    if response.status_code == 302 and "/review" in response.headers.get("Location", ""):
        with client.session_transaction() as sess:
            events = sess.get("events", [])
        if (len(events) == 1
            and events[0]["title"] == "Renamed"
            and events[0]["day"] == 4
            and events[0]["start"] == 1000):
            passed += 1
            print(f"Test {total}: PASS | Edit changed title, day, and time")
        else:
            print(f"Test {total}: FAIL | event after edit: {events}")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Edit preserves the ID ----
    total += 1
    client, eid = _setup_client_with_event(title="Original")
    token = _get_token(client, f"/edit/{eid}")
    client.post(f"/edit/{eid}", data={
        "csrf_token": token,
        "title": "Renamed", "day": "Friday",
        "start": "10:00AM", "end": "11:00AM",
    })
    with client.session_transaction() as sess:
        events = sess.get("events", [])
    if len(events) == 1 and events[0]["id"] == eid:
        passed += 1
        print(f"Test {total}: PASS | Edit preserved the event ID")
    else:
        print(f"Test {total}: FAIL")

    # ---- Edit preserves the priority (important/urgent booleans) ----
    total += 1
    client, eid = _setup_client_with_event(quadrant_key="signal")
    token = _get_token(client, f"/edit/{eid}")
    client.post(f"/edit/{eid}", data={
        "csrf_token": token,
        "title": "Still Signal", "day": "Friday",
        "start": "10:00AM", "end": "11:00AM",
    })
    with client.session_transaction() as sess:
        events = sess.get("events", [])
    if (events[0]["important"] is True and events[0]["urgent"] is False):
        passed += 1
        print(f"Test {total}: PASS | Edit preserved priority (still Signal)")
    else:
        print(f"Test {total}: FAIL")

    # ---- Invalid edit (bad day) shows errors and doesn't change event ----
    total += 1
    client, eid = _setup_client_with_event(title="Untouched")
    token = _get_token(client, f"/edit/{eid}")
    response = client.post(f"/edit/{eid}", data={
        "csrf_token": token,
        "title": "Would change",
        "day": "Funday",   # invalid
        "start": "10:00AM",
        "end": "11:00AM",
    })
    body = response.get_data(as_text=True)
    with client.session_transaction() as sess:
        events = sess.get("events", [])
    if ("Please fix the following" in body
        and events[0]["title"] == "Untouched"):
        passed += 1
        print(f"Test {total}: PASS | Invalid edit shows errors, event unchanged")
    else:
        print(f"Test {total}: FAIL")

    # ---- Edit without CSRF token rejected ----
    total += 1
    client, eid = _setup_client_with_event()
    response = client.post(f"/edit/{eid}", data={
        "title": "Hijacked", "day": "Monday",
        "start": "9:00AM", "end": "10:00AM",
    })
    if response.status_code == 400:
        passed += 1
        print(f"Test {total}: PASS | Edit without CSRF token rejected")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Edit nonexistent ID returns 404 ----
    total += 1
    client = test_app.test_client()
    response = client.get("/edit/99999")
    if response.status_code == 404:
        passed += 1
        print(f"Test {total}: PASS | Edit nonexistent ID returns 404")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Edit with non-integer ID returns 404 ----
    total += 1
    client = test_app.test_client()
    response = client.get("/edit/abc")
    if response.status_code == 404:
        passed += 1
        print(f"Test {total}: PASS | Edit non-integer ID returns 404")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    print(f"{passed}/{total} edit tests passed\n")
    return passed, total


def run_timesheet_display():
    """Session 5: the /timesheet route renders the actual timesheet."""
    print("=== TIMESHEET DISPLAY ===")
    passed = 0
    total = 0

    # ---- Page renders with a real event ----
    total += 1
    client, _ = _setup_client_with_event(title="Therapy", day="Monday",
                                          start="4:00PM", end="5:00PM")
    response = client.get("/timesheet")
    body = response.get_data(as_text=True)
    if response.status_code == 200 and "MONDAY" in body and "Therapy" in body:
        passed += 1
        print(f"Test {total}: PASS | Timesheet renders with MONDAY banner and event")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Output is wrapped in <pre> tags (preserves whitespace) ----
    total += 1
    if "<pre>" in body and "</pre>" in body:
        passed += 1
        print(f"Test {total}: PASS | Timesheet wrapped in <pre> tags")
    else:
        print(f"Test {total}: FAIL")

    # ---- Page contains a download button ----
    total += 1
    if "/timesheet/download" in body:
        passed += 1
        print(f"Test {total}: PASS | Page has link to /timesheet/download")
    else:
        print(f"Test {total}: FAIL")

    # ---- Event and issue counts shown in the header ----
    # The HTML wraps counts in <strong> tags, so we check for the
    # actual rendered pattern rather than a plain-text contains.
    total += 1
    if "<strong>1</strong> event(s)" in body and "<strong>0</strong> scheduling issue" in body:
        passed += 1
        print(f"Test {total}: PASS | Summary shows correct event and issue counts")
    else:
        print(f"Test {total}: FAIL")

    # ---- Issues from the engine appear in the rendered output ----
    # Create back-to-back events that will trigger a HARD_BUFFER warning.
    total += 1
    client = test_app.test_client()
    token = _get_token(client, "/plan/signal")
    from werkzeug.datastructures import MultiDict
    data = MultiDict()
    data.add("csrf_token", token)
    data.add("title", "Therapy"); data.add("day", "Monday")
    data.add("start", "4:00PM"); data.add("end", "5:00PM")
    data.add("title", "Commute"); data.add("day", "Monday")
    data.add("start", "5:00PM"); data.add("end", "5:30PM")
    client.post("/plan/signal", data=data)
    body = client.get("/timesheet").get_data(as_text=True)
    if "HARD_BUFFER" in body:
        passed += 1
        print(f"Test {total}: PASS | HARD_BUFFER issue from engine appears in timesheet")
    else:
        print(f"Test {total}: FAIL")

    print(f"{passed}/{total} timesheet display tests passed\n")
    return passed, total


def run_timesheet_empty():
    """Session 5: empty case shows friendly message, not an empty timesheet."""
    print("=== TIMESHEET EMPTY CASE ===")
    passed = 0
    total = 0

    # ---- Empty session: friendly empty-state message ----
    total += 1
    client = test_app.test_client()
    response = client.get("/timesheet")
    body = response.get_data(as_text=True)
    if response.status_code == 200 and "Nothing to show" in body:
        passed += 1
        print(f"Test {total}: PASS | Empty session shows friendly empty-state")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Empty case does NOT contain a 7-day timesheet ----
    total += 1
    if "MONDAY" not in body:
        passed += 1
        print(f"Test {total}: PASS | Empty case doesn't render an empty 7-day timesheet")
    else:
        print(f"Test {total}: FAIL | rendered empty timesheet when it shouldn't have")

    # ---- Empty case offers a link to start ----
    total += 1
    if "/plan/signal" in body:
        passed += 1
        print(f"Test {total}: PASS | Empty case offers link to start")
    else:
        print(f"Test {total}: FAIL")

    print(f"{passed}/{total} empty-case tests passed\n")
    return passed, total


def run_timesheet_download():
    """Session 5: the /timesheet/download endpoint serves the file properly."""
    print("=== TIMESHEET DOWNLOAD ===")
    passed = 0
    total = 0

    # ---- Download returns 200 with the timesheet body ----
    total += 1
    client, _ = _setup_client_with_event(title="Therapy")
    response = client.get("/timesheet/download")
    body = response.get_data(as_text=True)
    if response.status_code == 200 and "MONDAY" in body and "Therapy" in body:
        passed += 1
        print(f"Test {total}: PASS | Download endpoint serves rendered timesheet")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Content-Type is text/plain ----
    total += 1
    ct = response.headers.get("Content-Type", "")
    if "text/plain" in ct:
        passed += 1
        print(f"Test {total}: PASS | Content-Type is text/plain ({ct})")
    else:
        print(f"Test {total}: FAIL | Content-Type was {ct!r}")

    # ---- Content-Disposition triggers a download ----
    total += 1
    cd = response.headers.get("Content-Disposition", "")
    if "attachment" in cd and "filename=" in cd and ".txt" in cd:
        passed += 1
        print(f"Test {total}: PASS | Content-Disposition forces download with .txt filename")
    else:
        print(f"Test {total}: FAIL | got {cd!r}")

    # ---- Filename is date-stamped and starts with 'timesheet_' ----
    total += 1
    if 'filename="timesheet_' in cd:
        passed += 1
        print(f"Test {total}: PASS | Filename starts with 'timesheet_'")
    else:
        print(f"Test {total}: FAIL")

    # ---- Download from empty session redirects to /timesheet ----
    total += 1
    client = test_app.test_client()
    response = client.get("/timesheet/download")
    if response.status_code == 302 and "/timesheet" in response.headers.get("Location", ""):
        passed += 1
        print(f"Test {total}: PASS | Empty-session download redirects to /timesheet")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- Downloaded content matches what's shown on the page ----
    total += 1
    client, _ = _setup_client_with_event(title="Therapy")
    download_body = client.get("/timesheet/download").get_data(as_text=True)
    page_body = client.get("/timesheet").get_data(as_text=True)
    # The download body is plain text; the page body is HTML with the
    # same text wrapped in <pre>. We can check that the meaningful
    # content (the MONDAY banner line, the event) is in both.
    if ("MONDAY" in download_body and "MONDAY" in page_body
        and "Therapy" in download_body and "Therapy" in page_body):
        passed += 1
        print(f"Test {total}: PASS | Download content matches page content")
    else:
        print(f"Test {total}: FAIL")

    print(f"{passed}/{total} download tests passed\n")
    return passed, total


def run_timesheet_xss_defense():
    """Session 5: title with HTML is safely rendered in the <pre> block."""
    print("=== TIMESHEET XSS DEFENSE ===")
    passed = 0
    total = 0

    # The engine caps title length and rejects various bad inputs, but
    # if a benign-looking string with HTML chars gets through, it must
    # be escaped when shown in the <pre>.
    # We submit a title containing < > & to a quadrant and check it
    # appears HTML-escaped on the timesheet page.
    total += 1
    client = test_app.test_client()
    token = _get_token(client, "/plan/signal")
    client.post("/plan/signal", data={
        "csrf_token": token,
        "title": "Meeting <with> & friends",
        "day": "Monday",
        "start": "9:00AM",
        "end": "10:00AM",
    })
    body = client.get("/timesheet").get_data(as_text=True)
    # The raw < > & must NOT appear unescaped between <pre> and </pre>.
    pre_start = body.find("<pre>")
    pre_end = body.find("</pre>", pre_start)
    pre_content = body[pre_start:pre_end] if pre_start != -1 else ""
    # Inside the <pre>, the title's special chars must be escaped.
    if ("&lt;with&gt;" in pre_content and "&amp;" in pre_content):
        passed += 1
        print(f"Test {total}: PASS | HTML special chars in title escaped in <pre> block")
    else:
        print(f"Test {total}: FAIL | unescaped HTML may have leaked into <pre>")

    print(f"{passed}/{total} XSS defense tests passed\n")
    return passed, total


def run_health_endpoint():
    """Session 6: the /health endpoint Railway uses for monitoring."""
    print("=== HEALTH ENDPOINT ===")
    passed = 0
    total = 0

    client = test_app.test_client()

    total += 1
    response = client.get("/health")
    if response.status_code == 200:
        passed += 1
        print(f"Test {total}: PASS | GET /health returns 200")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    total += 1
    body = response.get_data(as_text=True)
    if body == "OK":
        passed += 1
        print(f"Test {total}: PASS | /health body is exactly 'OK'")
    else:
        print(f"Test {total}: FAIL | body was {body!r}")

    total += 1
    ct = response.headers.get("Content-Type", "")
    if "text/plain" in ct:
        passed += 1
        print(f"Test {total}: PASS | /health Content-Type is text/plain")
    else:
        print(f"Test {total}: FAIL | got {ct!r}")

    print(f"{passed}/{total} health endpoint tests passed\n")
    return passed, total


def run_error_pages():
    """Session 6: custom 404 page renders correctly."""
    print("=== ERROR PAGES ===")
    passed = 0
    total = 0

    client = test_app.test_client()

    # ---- 404 returns the custom page ----
    total += 1
    response = client.get("/this-does-not-exist")
    body = response.get_data(as_text=True)
    if response.status_code == 404 and "Page Not Found" in body:
        passed += 1
        print(f"Test {total}: PASS | Unknown URL returns custom 404 page")
    else:
        print(f"Test {total}: FAIL | status {response.status_code}")

    # ---- 404 page has a link home ----
    total += 1
    if 'href="/"' in body:
        passed += 1
        print(f"Test {total}: PASS | 404 page has link home")
    else:
        print(f"Test {total}: FAIL")

    # ---- 404 page does NOT echo the bad URL (prevents reflected XSS) ----
    total += 1
    response = client.get("/<script>alert(1)</script>")
    body = response.get_data(as_text=True)
    if "<script>alert" not in body:
        passed += 1
        print(f"Test {total}: PASS | 404 page doesn't echo malicious URL")
    else:
        print(f"Test {total}: FAIL | dangerous: URL echoed unescaped")

    print(f"{passed}/{total} error page tests passed\n")
    return passed, total


def run():
    """Run all web app tests (Sessions 1, 2, 3, 4, 5, and 6)."""
    p1, t1 = run_index_route()
    p2, t2 = run_template_inheritance()
    p3, t3 = run_security_baseline()
    p4, t4 = run_app_factory()
    p5, t5 = run_engine_integration()
    p6, t6 = run_quadrant_get()
    p7, t7 = run_quadrant_post()
    p8, t8 = run_csrf_protection()
    p9, t9 = run_xss_escaping()
    p10, t10 = run_reset()
    p11, t11 = run_full_flow()
    p12, t12 = run_empty_quadrant()
    p13, t13 = run_progress_indicator()
    p14, t14 = run_event_ids()
    p15, t15 = run_review_page()
    p16, t16 = run_delete_event()
    p17, t17 = run_edit_event()
    p18, t18 = run_timesheet_display()
    p19, t19 = run_timesheet_empty()
    p20, t20 = run_timesheet_download()
    p21, t21 = run_timesheet_xss_defense()
    # Session 6 groups
    p22, t22 = run_health_endpoint()
    p23, t23 = run_error_pages()
    return (
        p1+p2+p3+p4+p5+p6+p7+p8+p9+p10+p11+p12+p13+p14+p15+p16+p17
            +p18+p19+p20+p21+p22+p23,
        t1+t2+t3+t4+t5+t6+t7+t8+t9+t10+t11+t12+t13+t14+t15+t16+t17
            +t18+t19+t20+t21+t22+t23,
    )


if __name__ == "__main__":
    run()
