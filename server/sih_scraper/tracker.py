"""Live tracker for monitoring submission updates on selected problem statements."""

import time
import datetime
from typing import List, Dict, Optional, Callable, Union
from .scraper import SIHScraper, normalize_id
from .models import ProblemStatement


class LiveTracker:
    """Monitors live changes to submitted idea counts at regular intervals."""

    def __init__(
        self,
        scraper: Optional[SIHScraper] = None,
        target_ids: Optional[List[Union[str, int]]] = None,
        interval_seconds: int = 30,
        on_update_callback: Optional[Callable[[ProblemStatement, int, int], None]] = None,
    ):
        self.scraper = scraper or SIHScraper()
        self.target_ids = target_ids or []
        self.interval = max(5, interval_seconds)
        self.on_update = on_update_callback
        self.history: Dict[str, int] = {}

    def _get_target_statements(self) -> List[ProblemStatement]:
        if self.target_ids:
            return self.scraper.get_by_ids(self.target_ids, force_refresh=True)
        return self.scraper.fetch_all(force_refresh=True)

    def poll_once(self) -> List[Dict]:
        """Perform a single check and return any detected changes."""
        statements = self._get_target_statements()
        changes = []
        now_str = datetime.datetime.now().strftime("%H:%M:%S")

        for ps in statements:
            prev_count = self.history.get(ps.id)
            curr_count = ps.submitted_count

            if prev_count is not None and curr_count != prev_count:
                delta = curr_count - prev_count
                change_info = {
                    "timestamp": now_str,
                    "ps_id": ps.id,
                    "title": ps.title,
                    "previous_count": prev_count,
                    "current_count": curr_count,
                    "delta": delta,
                    "percentage_filled": ps.percentage_filled,
                    "slots_remaining": ps.slots_remaining,
                    "status": ps.status,
                }
                changes.append(change_info)

                if self.on_update:
                    self.on_update(ps, prev_count, curr_count)

            self.history[ps.id] = curr_count

        return changes

    def start_console_watch(self, max_cycles: Optional[int] = None):
        """Run continuous live watching in terminal with clear alerts."""
        print("=" * 75)
        target_desc = ", ".join(self.target_ids) if self.target_ids else "ALL Problem Statements"
        print(f">> SIH LIVE SUBMISSION TRACKER")
        print(f">> Monitoring: {target_desc}")
        print(f">> Refresh Interval: {self.interval}s")
        print("=" * 75)

        # Initial baseline fetch
        print("Fetching initial baseline counts...")
        initial_statements = self._get_target_statements()
        for ps in initial_statements:
            self.history[ps.id] = ps.submitted_count

        print(f"[OK] Baseline established for {len(initial_statements)} problem statement(s):")
        for ps in initial_statements:
            blocks = int(ps.percentage_filled / 5)
            bar = "#" * blocks + "." * (20 - blocks)
            print(f"   [{ps.id}] {ps.submitted_count:>3}/{ps.capacity} [{bar}] {ps.percentage_filled:>5.1f}% | {ps.title[:35]}...")

        print("\n[WATCHING] Actively monitoring live submission changes (Press Ctrl+C to stop)...\n")

        cycle = 0
        try:
            while max_cycles is None or cycle < max_cycles:
                time.sleep(self.interval)
                cycle += 1
                now_str = datetime.datetime.now().strftime("%H:%M:%S")

                try:
                    changes = self.poll_once()
                    if changes:
                        for c in changes:
                            sign = "+" if c["delta"] > 0 else ""
                            print(
                                f"[UPDATE {c['timestamp']}] {c['ps_id']} -> "
                                f"{c['current_count']} ideas ({sign}{c['delta']}) | "
                                f"{c['percentage_filled']}% filled ({c['slots_remaining']} slots left) | "
                                f"'{c['title'][:40]}...'"
                            )
                    else:
                        print(f"[{now_str}] Checked {len(self.history)} statement(s) - No new submissions.")
                except Exception as poll_err:
                    print(f"[WARN {now_str}] Network check error (will retry next cycle): {poll_err}")

        except KeyboardInterrupt:
            print("\n[STOPPED] Watcher stopped by user.")
