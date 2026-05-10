from conflict_checker import has_conflict, parse_time

# --- ORIGINAL 10 TESTS (unchanged) ---
tests = [
    (1300, 1400, 1330, 1430, True),
    (900, 1000, 1100, 1200, False),
    (900, 1000, 1000, 1100, False),
    (1300, 1400, 1300, 1400, True),
    (900, 1700, 1200, 1300, True),
    (1200, 1300, 900, 1700, True),
    (1300, 1400, 1359, 1500, True),
    (1400, 1500, 1500, 1600, False),
    (1500, 1600, 1300, 1400, False),
    (2200, 2359, 2300, 2400, True),
]

print("=== CONFLICT LOGIC TESTS ===")
passed = 0
for i, (s1, e1, s2, e2, expected) in enumerate(tests, 1):
    result = has_conflict(s1, e1, s2, e2)
    status = "PASS" if result == expected else "FAIL"
    if status == "PASS":
        passed += 1
    print(f"Test {i}: {status} | ({s1}-{e1}) vs ({s2}-{e2}) | Expected: {expected}, Got: {result}")
print(f"{passed}/10 logic tests passed\n")

# --- NEW: 10 PARSER TESTS ---
parser_tests = [
    ("4:00PM", 1600),
    ("4pm", 1600),
    ("4:30pm", 1630),
    ("12:00PM", 1200),
    ("12:00AM", 0),
    ("7:00PM", 1900),
    ("16:00", 1600),
    ("9:00AM", 900),
    ("11:59PM", 2359),
    ("1:00am", 100),
]

print("=== PARSER TESTS ===")
p_passed = 0
for i, (time_str, expected) in enumerate(parser_tests, 1):
    result = parse_time(time_str)
    status = "PASS" if result == expected else "FAIL"
    if status == "PASS":
        p_passed += 1
    print(f"Test {i}: {status} | \"{time_str}\" | Expected: {expected}, Got: {result}")
print(f"{p_passed}/10 parser tests passed\n")

# --- BONUS: FULL FLOW TEST (your real-world scenario) ---
print("=== FULL FLOW: Your Study + Commute Scenario ===")
study_start = parse_time("4:00PM")
study_end = parse_time("5:00PM")
commute_end = study_end + 200  # 2 hours after studying ends
school_start = parse_time("7:00PM")
school_end = parse_time("10:00PM")

print(f"Study:   {study_start}-{study_end}")
print(f"Commute: {study_end}-{commute_end}")
print(f"School:  {school_start}-{school_end}")
print(f"Study vs School conflict: {has_conflict(study_start, study_end, school_start, school_end)}")
print(f"Commute vs School conflict: {has_conflict(study_end, commute_end, school_start, school_end)}")