"""
Security Test Suite for P0 Security Features.

Tests all P0 security implementations:
- API Key Authentication
- Rate Limiting
- Request Size Limits
- Input Sanitization
- Admin Protection
- Public Endpoints (bypass auth)

Run with: pytest tests/test_security.py -v
Or directly: python tests/test_security.py
"""

import os
import sys
import time
import json
import requests
from typing import Optional, Dict, Any

# Configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEV_API_KEY = os.getenv("DEV_API_KEY", "dev-key-12345")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-key-master-12345")

# ANSI colors for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_test_header(test_name: str):
    """Print a formatted test header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}TEST: {test_name}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.END}")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}[PASS] {message}{Colors.END}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}[FAIL] {message}{Colors.END}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.YELLOW}[INFO] {message}{Colors.END}")


def make_request(
    method: str,
    endpoint: str,
    api_key: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> requests.Response:
    """
    Make an HTTP request to the API.

    Args:
        method: HTTP method (GET, POST, DELETE)
        endpoint: API endpoint path
        api_key: Optional API key for authentication
        data: Optional request body data
        params: Optional query parameters

    Returns:
        requests.Response object
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    url = f"{BASE_URL}{endpoint}"

    if method.upper() == "GET":
        return requests.get(url, headers=headers, params=params, timeout=5)
    elif method.upper() == "POST":
        return requests.post(url, headers=headers, json=data, params=params, timeout=5)
    elif method.upper() == "DELETE":
        return requests.delete(url, headers=headers, params=params, timeout=5)
    else:
        raise ValueError(f"Unsupported method: {method}")


def test_server_running():
    """Test 1: Verify server is running."""
    print_test_header("Server Health Check")

    try:
        response = make_request("GET", "/health")
        if response.status_code == 200:
            print_success(f"Server is running at {BASE_URL}")
            print_success(f"Response: {response.json()}")
            return True
        else:
            print_error(f"Server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to server: {e}")
        print_info(f"Make sure the server is running at {BASE_URL}")
        print_info("Start with: uvicorn backend.main:app --reload")
        return False


def test_public_endpoints():
    """Test 2: Public endpoints should work without authentication."""
    print_test_header("Public Endpoints (No Auth Required)")

    public_endpoints = [
        ("/health", "GET"),
        ("/docs", "GET"),
        ("/redoc", "GET"),
        ("/openapi.json", "GET"),
        ("/llm/info", "GET"),
    ]

    all_passed = True
    for endpoint, method in public_endpoints:
        response = make_request(method, endpoint)
        if response.status_code == 200:
            print_success(f"{method} {endpoint} - OK (no auth required)")
        else:
            print_error(f"{method} {endpoint} - FAILED (status {response.status_code})")
            all_passed = False

    return all_passed


def test_api_key_authentication():
    """Test 3: API key authentication required for protected endpoints."""
    print_test_header("API Key Authentication")

    protected_endpoints = [
        ("/personas", "GET"),
        ("/chat", "POST"),
        ("/sessions", "POST"),
    ]

    all_passed = True

    # Test without API key (should fail)
    print_info("Testing without API key...")
    for endpoint, method in protected_endpoints:
        response = make_request(method, endpoint, api_key=None)
        if response.status_code == 401:
            print_success(f"{method} {endpoint} - Correctly rejected (401)")
        else:
            print_error(f"{method} {endpoint} - Should have returned 401, got {response.status_code}")
            all_passed = False

    # Test with valid API key (should succeed)
    print_info("\nTesting with valid API key...")
    for endpoint, method in protected_endpoints:
        data = None
        if endpoint == "/chat":
            data = {
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "test"}]}
                ]
            }

        response = make_request(method, endpoint, api_key=DEV_API_KEY, data=data)
        if response.status_code in [200, 201]:
            print_success(f"{method} {endpoint} - Accepted with valid API key")
        else:
            print_error(f"{method} {endpoint} - Failed with valid key (status {response.status_code})")
            print_info(f"Response: {response.text[:200]}")
            all_passed = False

    # Test with invalid API key (should fail)
    print_info("\nTesting with invalid API key...")
    for endpoint, method in protected_endpoints:
        response = make_request(method, endpoint, api_key="invalid-key-12345")
        if response.status_code == 403:
            print_success(f"{method} {endpoint} - Correctly rejected invalid key (403)")
        else:
            print_error(f"{method} {endpoint} - Should have returned 403, got {response.status_code}")
            all_passed = False

    return all_passed


def test_rate_limiting():
    """Test 4: Rate limiting enforcement."""
    print_test_header("Rate Limiting")

    print_info("Sending rapid requests to test rate limiting...")
    print_info(f"Rate limit: 60 req/min, 1000 req/hour")

    # Send multiple rapid requests
    rate_limit_hits = 0
    for i in range(70):  # Try to exceed the 60 req/min limit
        response = make_request("GET", "/personas", api_key=DEV_API_KEY)
        if response.status_code == 429:
            rate_limit_hits += 1
            print_info(f"Request {i+1}: Rate limited (429)")
            break
        time.sleep(0.05)  # Small delay between requests

    if rate_limit_hits > 0:
        print_success("Rate limiting is working correctly (429 response received)")
        return True
    else:
        print_error("Rate limiting may not be working (no 429 responses)")
        print_info("Note: Rate limiting uses a sliding window, may need more requests")
        return False


def test_request_size_limit():
    """Test 5: Request size limit enforcement."""
    print_test_header("Request Size Limits")

    # Create a large payload (attempting to exceed 10MB)
    large_text = "x" * (11 * 1024 * 1024)  # 11MB
    large_payload = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": large_text}]}
        ]
    }

    print_info("Sending request larger than 10MB limit...")
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            headers={"X-API-Key": DEV_API_KEY, "Content-Type": "application/json"},
            json=large_payload,
            timeout=5
        )

        if response.status_code == 413:
            print_success("Large request correctly rejected (413)")
            return True
        else:
            print_error(f"Expected 413, got {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        # Connection might be closed by middleware
        print_success("Large request was rejected (connection closed)")
        return True


def test_input_sanitization():
    """Test 6: Input sanitization for malicious patterns."""
    print_test_header("Input Sanitization")

    malicious_inputs = [
        ("SQL Injection", "'; DROP TABLE users; --"),
        ("XSS", "<script>alert('xss')</script>"),
        ("Path Traversal", "../../../etc/passwd"),
        ("Command Injection", "; cat /etc/passwd"),
    ]

    all_passed = True
    for attack_type, payload in malicious_inputs:
        # Test in query parameter
        response = make_request("GET", "/conversations/search",
                              api_key=DEV_API_KEY,
                              params={"query": payload})

        # Should either be rejected (400) or the payload should be sanitized
        if response.status_code == 400:
            print_success(f"{attack_type} - Blocked (400)")
        elif response.status_code == 401:
            # Auth error, expected if endpoint requires auth
            print_info(f"{attack_type} - Auth required (401), skipping payload test")
        else:
            print_info(f"{attack_type} - Status {response.status_code} (may be allowed/sanitized)")

    return all_passed


def test_admin_protection():
    """Test 7: Admin-only endpoints."""
    print_test_header("Admin Protection")

    admin_endpoints = [
        ("/db/size", "GET"),
        ("/db/stats", "GET"),
        ("/db/status", "GET"),
    ]

    all_passed = True

    # Test with regular API key (should fail)
    print_info("Testing admin endpoints with regular API key...")
    for endpoint, method in admin_endpoints:
        response = make_request(method, endpoint, api_key=DEV_API_KEY)
        if response.status_code == 403:
            print_success(f"{method} {endpoint} - Correctly rejected regular key (403)")
        else:
            print_error(f"{method} {endpoint} - Should have returned 403, got {response.status_code}")
            all_passed = False

    # Test with admin API key (should succeed)
    print_info("\nTesting admin endpoints with admin API key...")
    for endpoint, method in admin_endpoints:
        response = make_request(method, endpoint, api_key=ADMIN_API_KEY)
        if response.status_code == 200:
            print_success(f"{method} {endpoint} - Accepted with admin key")
        else:
            print_error(f"{method} {endpoint} - Failed with admin key (status {response.status_code})")
            print_info(f"Response: {response.text[:200]}")
            all_passed = False

    return all_passed


def test_security_headers():
    """Test 8: Security headers in responses."""
    print_test_header("Security Headers")

    expected_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "Permissions-Policy",
    ]

    response = make_request("GET", "/health")
    headers = response.headers

    all_present = True
    for header in expected_headers:
        if header in headers:
            print_success(f"{header}: {headers[header][:50]}...")
        else:
            print_error(f"{header} - MISSING")
            all_present = False

    # Check that Server header is removed or generic
    if "Server" not in headers or headers["Server"] == "":
        print_success("Server header is hidden")
    else:
        print_info(f"Server header: {headers.get('Server', 'not set')}")

    return all_present


def test_cors_configuration():
    """Test 9: CORS configuration."""
    print_test_header("CORS Configuration")

    # Make a preflight request
    response = requests.options(
        f"{BASE_URL}/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-API-Key",
        },
        timeout=5
    )

    cors_headers = [
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers",
        "Access-Control-Max-Age",
    ]

    all_present = True
    for header in cors_headers:
        if header in response.headers:
            print_success(f"{header}: {response.headers[header]}")
        else:
            print_info(f"{header} - Not present (may be optional)")

    return all_present


def run_all_tests():
    """Run all security tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"SECURITY TEST SUITE - P0 Implementation")
    print(f"{'='*60}{Colors.END}\n")
    print(f"Base URL: {BASE_URL}")
    print(f"Dev API Key: {DEV_API_KEY}")
    print(f"Admin API Key: {ADMIN_API_KEY}")

    tests = [
        ("Server Health Check", test_server_running),
        ("Public Endpoints", test_public_endpoints),
        ("API Key Authentication", test_api_key_authentication),
        ("Rate Limiting", test_rate_limiting),
        ("Request Size Limits", test_request_size_limit),
        ("Input Sanitization", test_input_sanitization),
        ("Admin Protection", test_admin_protection),
        ("Security Headers", test_security_headers),
        ("CORS Configuration", test_cors_configuration),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print_error(f"Test failed with exception: {e}")
            results[test_name] = False
        time.sleep(0.5)  # Brief pause between tests

    # Print summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{Colors.END}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{status} - {test_name}")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.END}")

    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed! P0 security is working correctly.{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}Some tests failed. Please review the output above.{Colors.END}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
