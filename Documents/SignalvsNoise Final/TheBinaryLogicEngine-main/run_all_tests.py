# ============================================================
# run_all_tests.py
#
# Master test runner. Executes every test file and prints a
# grand total. Run from the project root:
#
#     python3 run_all_tests.py
#
# Why this file exists:
#   As we add more test files, running them one by one becomes
#   tedious AND error-prone (it's easy to forget one). A single
#   entry point means there's only one command to remember and
#   one place to check whether everything is green.
# ============================================================

from tests import (
    test_time_parser,
    test_time_parser_validation,
    test_day_parser,
    test_day_parser_validation,
    test_conflict_checker,
    test_event,
    test_event_conflict,
    test_time_math,
    test_find_all_issues,
    test_priority,
    test_sort_and_group,
    test_dump_parser,
    test_timesheet_formatter,
    test_timesheet_exporter,
)


def main():
    grand_passed = 0
    grand_total = 0

    # Each test module exposes a run() that returns (passed, total).
    # Adding a new test file? Add one line here.
    test_modules = (
        test_time_parser,
        test_time_parser_validation,
        test_day_parser,
        test_day_parser_validation,
        test_conflict_checker,
        test_event,
        test_event_conflict,
        test_time_math,
        test_find_all_issues,
        test_priority,
        test_sort_and_group,
        test_dump_parser,
        test_timesheet_formatter,
        test_timesheet_exporter,
    )

    for module in test_modules:
        passed, total = module.run()
        grand_passed += passed
        grand_total += total

    print("=" * 50)
    print(f"GRAND TOTAL: {grand_passed}/{grand_total} tests passed")
    print("=" * 50)

    # Exit code 0 = success, 1 = failure.
    # This matters when we eventually wire up automated testing
    # (CI pipelines read the exit code to know if the build passed).
    return 0 if grand_passed == grand_total else 1


if __name__ == "__main__":
    exit(main())
