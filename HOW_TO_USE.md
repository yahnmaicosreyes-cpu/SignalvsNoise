# How to Use the Priority Planner

A plain-English guide. Keep this open the first few times you use the app.

---

## What this app does

You give it a messy list of your week's events. It gives you back a clean Monday–Sunday timesheet with every scheduling problem flagged. You can read it on screen, save it as a file, or print it.

**Mission:** signal vs. noise. Flag conflicts first, separate signal from noise second.

---

## Section 1 — One-time setup

Do these steps once. After that, you can skip ahead to Section 2 every time.

### 1.1 Make sure Python is installed

Open a terminal and type:

```
python3 --version
```

You should see something like `Python 3.10.x` or higher. If you get an error, install Python from [python.org](https://www.python.org/downloads/).

### 1.2 Unzip the project

Put the project folder somewhere you'll find it again. For example:

```
~/Documents/priority_planner/
```

### 1.3 Open a terminal inside the project folder

Navigate to the folder you just unzipped. On Mac/Linux:

```
cd ~/Documents/priority_planner
```

On Windows (PowerShell):

```
cd C:\Users\YourName\Documents\priority_planner
```

### 1.4 Verify everything works

Run the test suite:

```
python3 run_all_tests.py
```

You should see, at the bottom:

```
GRAND TOTAL: 322/322 tests passed
```

**If the tests don't all pass, stop and tell me what happened.** Don't try to use the app — something is wrong with the install.

---

## Section 2 — Your weekly workflow

Here's what you do every time you want to plan a week.

### 2.1 Open a terminal in the project folder

Same as setup step 1.3.

### 2.2 Run the planner

```
python3 plan_my_week.py
```

You'll see a banner and a prompt asking you to paste your week.

### 2.3 Paste your week

Type or paste your events. Each line is one event. Format:

```
Title | Day | StartTime-EndTime | [optional tags]
```

Real example:

```
Therapy | Monday | 4:00PM-5:00PM | [signal]
Commute | Monday | 5:00PM-5:30PM | [urgent]
Class | Monday | 5:30PM-7:00PM | [signal]
Yoga | Wednesday | 7:00AM-8:00AM | [signal]
Sync A | Friday | 2:00PM-2:30PM | [noise] [hard:0] [soft:0]
```

You can use comments (lines starting with `#`) and blank lines to organize:

```
# Monday — heavy day
Therapy | Monday | 4:00PM-5:00PM | [signal]
Commute | Monday | 5:00PM-5:30PM | [urgent]

# Tuesday
Standup | Tuesday | 10:00AM-10:30AM | [interruption]
```

### 2.4 Signal that you're done

After your last line, press:

- **Mac / Linux:** `Ctrl + D`
- **Windows:** `Ctrl + Z` then `Enter`

### 2.5 Read the output

You'll see:

1. Any **parse warnings** (lines that couldn't be read — typically typos)
2. Your **Monday–Sunday timesheet** with problems flagged inline
3. A **save confirmation** with the file path
4. A **summary line** (events, issues, skipped lines)

The timesheet is also saved as a `.txt` file in the `outputs/` folder.

---

## Section 3 — How to write your dump

This section is a reference for the input format.

### 3.1 The required fields

Every event needs three things, separated by `|`:

```
Title | Day | StartTime-EndTime
```

- **Title:** any text up to 200 characters
- **Day:** Monday, Tuesday, Wednesday, etc. Or abbreviations like Mon, Tue, Wed. Case doesn't matter.
- **Time range:** start and end separated by a dash, e.g. `4:00PM-5:00PM` or `16:00-17:00`. AM/PM or 24-hour format both work.

### 3.2 Optional tags

You can add tags inside square brackets after the time range. All tags are optional. All are case-insensitive.

**Priority tags** (pick one per event):

| Tag | Meaning |
|---|---|
| `[signal]` | Important + not urgent. Highest priority. |
| `[urgent]` | Important + urgent. Second priority. |
| `[interruption]` | Not important + urgent. Loud but not signal. |
| `[noise]` | Not important + not urgent. Drop candidate. |

If you don't set a priority, the event is marked `UNSPECIFIED`.

**Buffer override tags** (use when defaults don't fit):

| Tag | Meaning |
|---|---|
| `[hard:30]` | This event needs at least 30 minutes of transition time after it |
| `[soft:60]` | This event wants at least 60 minutes of breathing room after it |

Whitespace inside tags is allowed: `[hard: 30]` works the same as `[hard:30]`.

### 3.3 Real examples

A morning meeting, no overrides:

```
Standup | Monday | 9:00AM-9:30AM | [interruption]
```

A Zoom-to-Zoom transition where you don't need a buffer:

```
Sync A | Friday | 2:00PM-2:30PM | [noise] [hard:0] [soft:0]
```

A long-term-important event with no urgency:

```
Annual physical | Wednesday | 2:00PM-3:00PM | [signal]
```

A day with everything left UNSPECIFIED (still works, just no priority info):

```
Coffee | Friday | 3:00PM-3:30PM
```

### 3.4 Things that get skipped

These don't cause errors — they're just ignored:

- Blank lines
- Lines that start with `#` (comments)
- Whitespace-only lines

### 3.5 Common mistakes that cause failures

| Mistake | Example | What happens |
|---|---|---|
| Misspelled day | `Tuseday` | That line gets skipped with a warning |
| Invalid time | `25:00-26:00` | That line gets skipped with a warning |
| Missing `\|` separator | `Therapy Monday 4PM-5PM` | That line gets skipped with a warning |
| Two priority tags | `[signal] [urgent]` | Pick one; that line gets skipped |
| Negative buffer | `[hard:-5]` | That line gets skipped |

**Good news:** one bad line doesn't kill the whole dump. The rest of your week still parses. You'll see warnings for any skipped lines so you can fix them next time.

---

## Section 4 — Reading the output

Here's a sample timesheet section, broken down:

```
========================================
MONDAY
========================================
  16:00 - 17:00   Therapy      [SIGNAL]
    ! HARD_BUFFER: only 0 min before Commute (need 15)
  17:00 - 17:30   Commute      [URGENT]
    ! HARD_BUFFER: only 0 min after Therapy (need 15)
```

What each part means:

- **Banner** (`====`) — section header for each day
- **Time range** — 24-hour military format (HH:MM)
- **Title** — what you typed
- **Quadrant tag** — `[SIGNAL]`, `[URGENT]`, `[INTERRUPTION]`, `[NOISE]`, or `[UNSPECIFIED]`
- **Sub-line with `!`** — a flagged problem

### 4.1 The three kinds of problems

| Symbol | What it means |
|---|---|
| `! OVERLAP` | Two events run at the same time. Hard conflict — one has to move. |
| `! HARD_BUFFER` | Events don't overlap but there's not enough physical transition time. Default is 15 minutes. |
| `! SOFT_BUFFER` | Events have enough transition time but not enough breathing room. Default is 30 minutes. |

### 4.2 What "Open Availability" means

A day with no events shows `Open Availability` instead of being skipped. This is intentional — you see the whole week, every time.

---

## Section 5 — Common scenarios

### 5.1 I want to override a default buffer

Add `[hard:N]` or `[soft:N]` tags to the event. `N` is the number of minutes you actually need.

```
Sync A | Friday | 2:00PM-2:30PM | [noise] [hard:0] [soft:0]
```

This tells the engine: "I don't need any transition time after this event." Useful for back-to-back Zoom calls.

### 5.2 I want to save the timesheet

It's automatic. Every time you run `plan_my_week.py`, the timesheet is saved to a file in the `outputs/` folder. Filenames look like `timesheet_2026-05-25.txt`.

If you run it twice on the same day, the second file gets a `-2` suffix, then `-3`, and so on. Your earlier files are never overwritten.

### 5.3 I want to print the timesheet

Find the `.txt` file in the `outputs/` folder and print it like any other file. Plain text prints cleanly on any printer.

### 5.4 I want to share it with someone

The `.txt` file is regular text. Email it as an attachment, copy-paste the content, or whatever you'd do with any other file.

### 5.5 I made a typo and want to re-run

Just run `plan_my_week.py` again. Fix your dump. Re-paste. The new file gets saved alongside the old one (with a `-2` suffix).

### 5.6 I want to clean up old timesheets

Delete files from the `outputs/` folder whenever you want. The app never touches files that already exist — it only creates new ones.

---

## Section 6 — Troubleshooting

### "ImportError: No module named src"

You're running the script from the wrong folder. Open a terminal **inside** the project folder before running:

```
cd /path/to/priority_planner
python3 plan_my_week.py
```

### "Tests failed when I ran run_all_tests.py"

Something is wrong with the install. Don't use the app yet. Tell me what error you saw.

### Parse warnings I don't understand

Read the warning carefully — it includes the line number and the reason. Common causes:

- Misspelled day name (most common)
- Time format the parser can't read (try `4:00PM` instead of `4pm` if you're getting errors)
- Missing or extra `|` separators

### The timesheet is empty / shows only "Open Availability"

Either no lines parsed, or all your events were on a day not in the current week. Check the parse warnings at the top of the output — they'll tell you why.

### Nothing happens when I press Ctrl+D

If you're on Windows, use `Ctrl+Z` then `Enter` instead. Some terminals also need you to be on a new empty line before Ctrl+D works.

### The "save" step failed

Usually means the `outputs/` folder is locked or read-only. Check folder permissions. The timesheet was still shown on screen, so you can copy-paste it from there if needed.

---

## Section 7 — Quick reference card

**To run the planner:**
```
python3 plan_my_week.py
```

**Input format:**
```
Title | Day | StartTime-EndTime | [optional tags]
```

**Priority tags:** `[signal]` `[urgent]` `[interruption]` `[noise]`

**Buffer tags:** `[hard:N]` `[soft:N]` (N is minutes)

**End input:** Ctrl+D (Mac/Linux), Ctrl+Z + Enter (Windows)

**Output location:** `outputs/timesheet_YYYY-MM-DD.txt`

**Run all tests:**
```
python3 run_all_tests.py
```
