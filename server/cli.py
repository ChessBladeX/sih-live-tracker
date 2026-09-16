#!/usr/bin/env python3
"""Command-line interface for SIH Problem Statement Scraper and Live Tracker."""

import argparse
import json
import sys
from pathlib import Path
from typing import List

# Ensure server package directory is in sys.path
SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

# Ensure Windows stdout handles UTF-8 gracefully without crashing
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sih_scraper import (
    SIHScraper,
    LiveTracker,
    export_csv,
    export_json,
    export_markdown,
    format_terminal_table,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Smart India Hackathon (SIH) Live Submission Scraper & Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check live submissions for specific problem statements:
  python cli.py --ps SIH26001,SIH26002,SIH26005

  # Track selected statements live every 20 seconds:
  python cli.py --ps SIH26001,SIH26015 --watch 20

  # Search statements with "AI" in Software category:
  python cli.py --keyword AI --category Software

  # Find statements with lowest submissions (best selection odds):
  python cli.py --sort sub-asc --limit 15

  # Export selected statements to CSV or JSON:
  python cli.py --ps SIH26001,SIH26002 --export my_shortlist.csv

  # View hackathon-wide submission statistics:
  python cli.py --summary
        """,
    )

    parser.add_argument(
        "--ps", "-p",
        help="Comma-separated Problem Statement IDs to fetch (e.g., 'SIH26001,26005')",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Fetch all available problem statements",
    )
    parser.add_argument(
        "--keyword", "-k",
        help="Search keyword in title, description, or ID",
    )
    parser.add_argument(
        "--category", "-c",
        choices=["Software", "Hardware", "software", "hardware"],
        help="Filter by category (Software or Hardware)",
    )
    parser.add_argument(
        "--theme", "-t",
        nargs="*",
        help="Filter by one or more themes/domains (e.g. -t 'Disaster Management' 'Robotics' or -t 'Disaster, Robotics')",
    )
    parser.add_argument(
        "--org", "-o",
        help="Filter by organization name",
    )
    parser.add_argument(
        "--min-submissions",
        type=int,
        help="Filter for statements with at least N submissions",
    )
    parser.add_argument(
        "--max-submissions",
        type=int,
        help="Filter for statements with at most N submissions",
    )
    parser.add_argument(
        "--range", "-r",
        help="Submission range filter (e.g. '15-59', '<20', '>50')",
    )
    parser.add_argument(
        "--import-descriptions",
        action="store_true",
        help="Import full problem statement descriptions from SIH into local descriptions/ directory",
    )
    parser.add_argument(
        "--sort",
        choices=["sub-asc", "sub-desc", "pct-asc", "pct-desc", "id"],
        default="id",
        help="Sort results (e.g., sub-asc for lowest submissions)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Limit number of rows displayed",
    )
    parser.add_argument(
        "--watch", "-w",
        nargs="?",
        const=30,
        type=int,
        help="Live watch mode: polls portal every N seconds (default: 30s) and alerts on changes",
    )
    parser.add_argument(
        "--export", "-e",
        help="Export path (format inferred from .csv, .json, or .md extension)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as raw JSON to stdout",
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Display overall hackathon competition statistics",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Launch interactive terminal menu",
    )

    return parser.parse_args()


def interactive_mode():
    """Interactive wizard for terminal users."""
    scraper = SIHScraper()
    print("=" * 70)
    print("🎯  SMART INDIA HACKATHON - INTERACTIVE SCRAPER")
    print("=" * 70)
    print("1. Query specific Problem Statement IDs (e.g. SIH26001, SIH26005)")
    print("2. Search by Keyword or Theme")
    print("3. Find Lowest Competition Problem Statements (Best odds)")
    print("4. Find Most Competitive Problem Statements (>80% capacity)")
    print("5. Live Watch / Monitor Submissions (Real-time alerts)")
    print("6. Hackathon Overview & Statistics")
    print("0. Exit")
    print("-" * 70)

    try:
        choice = input("Enter your choice (1-6): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        return

    if choice == "1":
        raw_ids = input("\nEnter Problem Statement IDs (comma-separated): ").strip()
        ids = [x.strip() for x in raw_ids.split(",") if x.strip()]
        if not ids:
            print("No IDs provided.")
            return
        print(f"\nFetching live data for {len(ids)} statement(s)...")
        results = scraper.get_by_ids(ids)
        print("\n" + format_terminal_table(results))

    elif choice == "2":
        keyword = input("\nEnter keyword (or press Enter to skip): ").strip() or None
        theme = input("Enter theme(s) (comma-separated or press Enter to skip): ").strip() or None
        cat = input("Enter category (Software/Hardware or press Enter to skip): ").strip() or None
        print("\nSearching problem statements...")
        results = scraper.filter_statements(keyword=keyword, theme=theme, category=cat)
        print(f"Found {len(results)} matches:\n")
        print(format_terminal_table(results[:25]))
        if len(results) > 25:
            print(f"\n... and {len(results) - 25} more results.")

    elif choice == "3":
        print("\nFetching least contested problem statements...")
        results = scraper.filter_statements(sort_by="sub-asc")
        print("\nTop 15 Problem Statements with LOWEST Submissions:\n")
        print(format_terminal_table(results[:15]))

    elif choice == "4":
        print("\nFetching highest contested problem statements...")
        results = scraper.filter_statements(sort_by="sub-desc")
        print("\nTop 15 Problem Statements with HIGHEST Submissions:\n")
        print(format_terminal_table(results[:15]))

    elif choice == "5":
        raw_ids = input("\nEnter Problem Statement IDs to watch live (or press Enter for all): ").strip()
        ids = [x.strip() for x in raw_ids.split(",") if x.strip()]
        interval_input = input("Enter refresh interval in seconds [default: 30]: ").strip()
        interval = int(interval_input) if interval_input.isdigit() else 30
        tracker = LiveTracker(scraper=scraper, target_ids=ids, interval_seconds=interval)
        tracker.start_console_watch()

    elif choice == "6":
        print("\nCalculating live hackathon statistics...")
        stats = scraper.get_summary()
        print("\n" + "=" * 60)
        print("📊 HACKATHON LIVE OVERVIEW")
        print("=" * 60)
        print(f"• Total Problem Statements : {stats.get('total_problem_statements', 0)}")
        print(f"• Total Live Submissions   : {stats.get('total_live_submissions', 0):,}")
        print(f"• Average per Statement    : {stats.get('average_submissions', 0)}")
        print(f"• Frozen (Reached Cap)     : {stats.get('frozen_statements_count', 0)}")
        print(f"• Software Statements      : {stats.get('software_count', 0)}")
        print(f"• Hardware Statements      : {stats.get('hardware_count', 0)}")
        print("=" * 60)

    elif choice == "0":
        print("Goodbye!")
    else:
        print("Invalid choice.")


def main():
    args = parse_args()

    # If no flags passed or interactive requested, enter interactive mode
    if len(sys.argv) == 1 or args.interactive:
        interactive_mode()
        return

    scraper = SIHScraper()

    # Summary report
    if args.summary:
        stats = scraper.get_summary()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("=" * 65)
            print("📊  SMART INDIA HACKATHON - LIVE SUMMARY")
            print("=" * 65)
            print(f"Total Statements     : {stats.get('total_problem_statements')}")
            print(f"Total Submissions    : {stats.get('total_live_submissions'):,}")
            print(f"Average Submissions  : {stats.get('average_submissions')}")
            print(f"Software Category    : {stats.get('software_count')}")
            print(f"Hardware Category    : {stats.get('hardware_count')}")
            print(f"Frozen/Full (at Cap) : {stats.get('frozen_statements_count')}")
            print("=" * 65)
        return

    # Watch Mode
    if args.watch is not None:
        target_ids = []
        if args.ps:
            target_ids = [p.strip() for p in args.ps.split(",") if p.strip()]
        tracker = LiveTracker(
            scraper=scraper,
            target_ids=target_ids,
            interval_seconds=args.watch,
        )
        tracker.start_console_watch()
        return

    # Import All Descriptions Mode
    if args.import_descriptions:
        print("Importing full problem statement descriptions from SIH portal...")
        statements = scraper.fetch_all(force_refresh=True)
        out_dir = SERVER_DIR / "descriptions"
        out_dir.mkdir(parents=True, exist_ok=True)
        for ps in statements:
            md_path = out_dir / f"{ps.id}.md"
            lines = [
                f"# {ps.id}: {ps.title}",
                "",
                f"- **Organization:** {ps.organization}",
                f"- **Department:** {ps.department}",
                f"- **Category:** {ps.category}",
                f"- **Theme / Domain:** {ps.theme}",
                f"- **Live Submissions:** {ps.submitted_count} / {ps.capacity} ({ps.percentage_filled}%)",
                f"- **Slots Remaining:** {ps.slots_remaining}",
                f"- **Status:** {ps.status}",
                f"- **Deadline:** {ps.deadline}",
            ]
            if ps.youtube_link:
                lines.append(f"- **YouTube Video:** {ps.youtube_link}")
            if ps.dataset_link:
                lines.append(f"- **Dataset Link:** {ps.dataset_link}")
            if ps.contact_info:
                lines.append(f"- **Contact Info:** {ps.contact_info}")
            lines.extend([
                "",
                "## Problem Description",
                "",
                ps.description or "No detailed description provided.",
            ])
            md_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[OK] Successfully imported {len(statements)} full descriptions into: {out_dir.resolve()}")
        return

    # Parse range if supplied (e.g. 15-59)
    min_sub = args.min_submissions
    max_sub = args.max_submissions
    if args.range:
        sr = args.range.strip()
        if "-" in sr:
            parts = sr.split("-", 1)
            if parts[0].strip().isdigit():
                min_sub = int(parts[0].strip())
            if parts[1].strip().isdigit():
                max_sub = int(parts[1].strip())
        elif sr.startswith("<") and sr[1:].strip().isdigit():
            max_sub = int(sr[1:].strip())
        elif sr.startswith(">") and sr[1:].strip().isdigit():
            min_sub = int(sr[1:].strip())

    # Regular Query / Filter Mode
    if args.ps:
        target_ids = [p.strip() for p in args.ps.split(",") if p.strip()]
        results = scraper.get_by_ids(target_ids)
        if min_sub is not None:
            results = [r for r in results if r.submitted_count >= min_sub]
        if max_sub is not None:
            results = [r for r in results if r.submitted_count <= max_sub]
    else:
        results = scraper.filter_statements(
            category=args.category,
            theme=args.theme,
            organization=args.org,
            keyword=args.keyword,
            min_submissions=min_sub,
            max_submissions=max_sub,
            sort_by=args.sort,
        )

    if args.limit and args.limit > 0:
        results = results[: args.limit]

    # JSON Output
    if args.json:
        print(json.dumps([ps.to_dict() for ps in results], indent=2, ensure_ascii=False))
        return

    # File Export
    if args.export:
        export_path = args.export.strip()
        lower_path = export_path.lower()
        if lower_path.endswith(".json"):
            saved = export_json(results, export_path)
        elif lower_path.endswith(".md"):
            saved = export_markdown(results, export_path)
        else:
            saved = export_csv(results, export_path)
        print(f"✅ Exported {len(results)} records to: {saved.resolve()}")

    # Terminal Table Display
    print("\n" + format_terminal_table(results) + "\n")
    print(f"Showing {len(results)} problem statement(s).")


if __name__ == "__main__":
    main()
