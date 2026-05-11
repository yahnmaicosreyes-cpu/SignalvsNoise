# Priority Planner

A weekly planner (Monday–Sunday) that takes a freeform text dump of priorities, to-dos, and events and turns them into a clean, conflict-free, prioritized view.

## Mission

**Signal vs. noise.** Flag scheduling problems first, separate signal from noise second.

## Project Status

The MVP detection engine is complete and works end-to-end. You can paste a text dump of your week, and the engine returns a sorted, day-grouped list of every scheduling problem it found.

## Folder Structure

```
priority_planner/
├── src/
│   ├── parsers/        # human input → clean numbers
│   │   ├── time_parser.py
│   │   ├── day_parser.py
│   │   └── dump_parser.py
│   ├── engine/         # decisions + math
│   │   ├── conflict_checker.py
│   │   └── time_math.py
│   └── models/         # data shapes (Event, Issue, Priority)
├── tests/              # 12 test files, 264 tests
└── run_all_tests.py    # one command, all tests
```

## Input Format (Dump Parser)

Pipe-separated, one event per line:

```
Title | Day | StartTime-EndTime
Title | Day | StartTime-EndTime | [optional tags]
```

### Tags

Optional, case-insensitive, in any order:

| Tag | Effect |
|---|---|
| `[signal]` | Important = True, Urgent = False |
| `[urgent]` | Important = True, Urgent = True |
| `[interruption]` | Important = False, Urgent = True |
| `[noise]` | Important = False, Urgent = False |
| `[hard:30]` | Set hard buffer override to 30 minutes |
| `[soft:60]` | Set soft buffer override to 60 minutes |

Whitespace inside tags is allowed: `[hard: 30]` works the same as `[hard:30]`.

### Comments and blank lines

- Lines starting with `#` are skipped (use them as section labels)
- Blank or whitespace-only lines are skipped
- Anything else is treated as an event line

### Security caps

- Maximum 9,000 characters total
- Maximum 90 lines
- Maximum 150 characters per line

Oversized inputs are rejected cleanly with a clear error message.

## Quick Example

```python
from src.parsers.dump_parser import parse_dump
from src.engine.conflict_checker import find_all_issues, group_issues_by_day

text = """
# Monday block
Therapy | Monday | 4:00PM-5:00PM | [signal]
Commute | Monday | 5:00PM-5:30PM | [urgent]

# Friday Zoom-to-Zoom
Sync A | Friday | 2:00PM-2:30PM | [noise] [hard:0] [soft:0]
Sync B | Friday | 2:30PM-3:00PM | [noise]
"""

result = parse_dump(text)
# result.events: list of parsed Event objects
# result.failures: list of lines that didn't parse (each has line number + reason)
# result.global_error: set only if the whole dump was rejected

issues = find_all_issues(result.events)
by_day = group_issues_by_day(issues)
# by_day: dict like {0: [Monday issues], 4: [Friday issues]}
```

## How to Run Tests

```
python3 run_all_tests.py
```

Expected: `GRAND TOTAL: 264/264 tests passed`.

## Priority System (Quadrants)

Each event can be tagged with two independent booleans (`important`, `urgent`), which resolve into one of five quadrants:

| Rank | Quadrant | important | urgent |
|---|---|---|---|
| 1 (highest) | **SIGNAL** | True | False |
| 2 | **URGENT** | True | True |
| 3 | **INTERRUPTION** | False | True |
| 4 | **NOISE** | False | False |
| 5 (lowest) | **UNSPECIFIED** | partial / both None | partial / both None |

The custom ordering reflects a deliberate "prevention over crisis" philosophy: events that are important-but-not-urgent rank highest, because doing them prevents the crises.

## Issue Detection

Three kinds of problems are detected, in this severity order:

| Issue Type | Meaning |
|---|---|
| **OVERLAP** | Events run at the same time (hard conflict) |
| **HARD_BUFFER** | Events don't overlap, but the transition gap is below the hard minimum |
| **SOFT_BUFFER** | Events have enough transition time but not enough breathing room |

Defaults: 15-minute hard buffer, 30-minute soft buffer. Both can be overridden per-event.

## Output Sort Order

`find_all_issues()` returns issues sorted by: **Day → Time → Priority → Severity**.
`group_issues_by_day()` reshapes that flat list into a day-keyed dict.

Days with no issues are absent from the output.

## Roadmap

- [x] Time parser
- [x] Day-of-week awareness
- [x] Conflict detection
- [x] Folder structure + test runner
- [x] Input validation
- [x] Event objects with validation
- [x] Time math helpers
- [x] Buffer logic (hard/soft + per-event overrides)
- [x] Severity-labeled issue detection
- [x] Priority quadrants (Signal / Urgent / Interruption / Noise / Unspecified)
- [x] Sorted output (Day → Time → Priority → Severity)
- [x] Day grouping
- [x] Text dump parser (user-facing input)
- [ ] Sun-Sat timesheet generation (formatted printable view)
- [ ] Print-friendly export
- [ ] Google Calendar export
- [ ] Public-facing security layer (web/API hardening)
