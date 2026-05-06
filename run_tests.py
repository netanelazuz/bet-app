"""Run all tests in the tests/ folder and print a summary."""

import sys

import pytest


class TestSummaryReporter:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []

    def pytest_runtest_logreport(self, report):
        if report.when != "call":
            return

        if report.passed:
            self.passed.append(report.nodeid)
        elif report.failed:
            self.failed.append(report.nodeid)
        elif report.skipped:
            self.skipped.append(report.nodeid)


def run_tests():
    reporter = TestSummaryReporter()
    exit_code = pytest.main(["-q", "tests"], plugins=[reporter])

    print("\n=== TEST SUMMARY ===")
    print(f"Passed: {len(reporter.passed)}")
    print(f"Failed: {len(reporter.failed)}")
    print(f"Skipped: {len(reporter.skipped)}")

    if reporter.failed:
        print("\nFailed tests:")
        for nodeid in reporter.failed:
            print(f"- {nodeid}")

    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests())
