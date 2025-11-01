#!/bin/bash
# Comprehensive test runner for aX Agent Studio
# Runs all E2E tests against the dashboard

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🧪 aX Agent Studio - Comprehensive Test Suite${NC}"
echo -e "${BLUE}============================================================${NC}"

# Check if dashboard is running
echo -e "\n${YELLOW}Checking if dashboard is running...${NC}"
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Dashboard is running${NC}"
else
    echo -e "${RED}✗ Dashboard is not running${NC}"
    echo -e "${YELLOW}Starting dashboard...${NC}"

    # Start dashboard in background
    uv run dashboard > /tmp/dashboard.log 2>&1 &
    DASHBOARD_PID=$!

    # Wait for dashboard to be ready
    echo -e "${YELLOW}Waiting for dashboard to start...${NC}"
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Dashboard started (PID: $DASHBOARD_PID)${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done

    # Check if it started successfully
    if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "\n${RED}✗ Dashboard failed to start${NC}"
        echo -e "${YELLOW}Check logs at /tmp/dashboard.log${NC}"
        exit 1
    fi
fi

# Track test results
FAILED_TESTS=()
PASSED_TESTS=()

# Function to run a test
run_test() {
    local test_name=$1
    local test_file=$2

    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}Running: ${test_name}${NC}"
    echo -e "${BLUE}============================================================${NC}"

    if .venv/bin/python "$test_file"; then
        PASSED_TESTS+=("$test_name")
        echo -e "${GREEN}✓ $test_name PASSED${NC}"
    else
        FAILED_TESTS+=("$test_name")
        echo -e "${RED}✗ $test_name FAILED${NC}"
    fi
}

# Run all test suites
run_test "Dashboard UI Tests" "tests/test_dashboard_ui_e2e.py"
run_test "Dashboard API Tests" "tests/test_dashboard_api_e2e.py"
run_test "All Monitors Tests" "tests/test_all_monitors_e2e.py"

# Summary
echo -e "\n${BLUE}============================================================${NC}"
echo -e "${BLUE}📊 Test Results Summary${NC}"
echo -e "${BLUE}============================================================${NC}"

echo -e "\n${GREEN}Passed Tests (${#PASSED_TESTS[@]}):${NC}"
for test in "${PASSED_TESTS[@]}"; do
    echo -e "${GREEN}  ✓ $test${NC}"
done

if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
    echo -e "\n${RED}Failed Tests (${#FAILED_TESTS[@]}):${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "${RED}  ✗ $test${NC}"
    done

    echo -e "\n${YELLOW}Check screenshots at /tmp/*.png${NC}"
    echo -e "${YELLOW}Check dashboard logs at /tmp/dashboard.log${NC}"

    exit 1
else
    echo -e "\n${GREEN}🎉 All tests passed!${NC}"
    echo -e "${BLUE}Screenshots saved to /tmp/${NC}"
    exit 0
fi
