#!/bin/bash
# run_load_test.sh

# Install locust if not present
pip install locust > /dev/null 2>&1

echo "Starting DocuMindAI Load Testing Suite..."
echo "Targeting localhost:8000"

# Run Locust in headless mode for 1 minute with 50 concurrent users
locust -f load_tests/locustfile.py --headless -u 50 -r 10 --run-time 1m --host http://localhost:8000
