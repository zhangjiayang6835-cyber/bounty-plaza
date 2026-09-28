#!/bin/bash

# Run tests with coverage instrumentation
gcov -o . -b -c -d .

# Generate coverage report
lcov --capture --directory . --output-file coverage.info

# Filter out system and test files
lcov --remove coverage.info '/usr/*' '*/tests/*' --output-file coverage_filtered.info

# Generate HTML report
genhtml coverage_filtered.info --output-directory coverage_report
