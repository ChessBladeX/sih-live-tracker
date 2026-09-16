# Smart India Hackathon (SIH) Live Submission Scraper & Tracker

A Python web scraper and real-time monitoring tool to track **live submission counts**, competition ratios, slots remaining, and metadata for problem statements from the official [Smart India Hackathon portal](https://sih.gov.in/sih2026PS).

---

## 🌟 Key Features

- **Live Submission Tracking**: Scrapes live registered idea counts (e.g. `93/500`) directly from the official portal.
- **Selective Problem Statement Query**: Fetch data for any specific statement by ID (e.g. `SIH26001`, `26005`).
- **Real-Time Watcher**: Polls the portal at configurable intervals and triggers alerts whenever new ideas are submitted.
- **Smart Filtering & Competition Analysis**:
  - Filter by Category (`Software`, `Hardware`), Theme, Keyword, or Organization.
  - Sort by **lowest submissions** to identify less crowded, high-probability problem statements.
- **Multiple Export Formats**: Export selected statements to `CSV`, `JSON`, or `Markdown` with full descriptions and metadata.
- **Modern Web Dashboard**: Visual interface with live capacity progress bars, search, and a persistent browser watchlist.
- **Interactive CLI Wizard**: Terminal menu for interactive queries without remembering command flags.

---

## 📁 Repository Structure

```
SIH webscrapper/
├── client/                     # Frontend UI (HTML, CSS)
│   ├── index.html
│   └── style.css
├── server/                     # Backend application & data
│   ├── app.py                  # FastAPI web server
│   ├── cli.py                  # Command-line interface
│   ├── requirements.txt        # Python dependencies
│   ├── sih_scraper/            # Core scraper Python package
│   ├── descriptions/           # Scraped markdown files for problem statements
│   └── tests/                  # Unit test suite
├── Dockerfile                  # Container definition
├── Procfile                    # Deployment process configuration
└── README.md
```

---

## 🚀 Quick Start

### 1. Check Live Submissions for Selected Statements
Pass problem statement IDs separated by commas (supports both `SIH26001` and short `26001` format):
```bash
python server/cli.py --ps SIH26001,SIH26002,SIH26005
```

Output:
```
PS ID      | Category   | Submissions   | Filled   | Status           | Theme                  | Title                                 
-----------+------------+---------------+----------+------------------+------------------------+---------------------------------------
SIH26001   | Software   | 93/500        | 18.6%    | LOW (<20%)       | Disaster Management    | AI-Based early warning and landslide..
SIH26002   | Software   | 42/500        | 8.4%     | LOW (<20%)       | Transportation & Log.. | Al-Based Smart Logistics and Accessi..
SIH26005   | Hardware   | 41/500        | 8.2%     | LOW (<20%)       | Agriculture, FoodTec.. | Solar-Powered Smart Mini Cold Storag..
```

### 2. Live Monitoring / Watch Mode
Watch selected problem statements in real time with automated alerts when new ideas are submitted:
```bash
python server/cli.py --ps SIH26001,SIH26015 --watch 30
```
*(Polls every 30 seconds and prints live deltas, e.g. `SIH26001 -> 94 ideas (+1) | 18.8% filled`)*.

### 3. Submission Range Filter (e.g. 15-59)
Filter for problem statements that fall within a desired competition range:
```bash
python server/cli.py --range 15-59 --limit 15
```

### 4. Import Full Problem Statement Descriptions
Download and generate individual, richly formatted Markdown files for every single problem statement into a `descriptions/` directory:
```bash
python server/cli.py --import-descriptions
```

### 5. Find Least Competitive Problem Statements (Best Odds)
Sort all statements by lowest number of submissions:
```bash
python server/cli.py --sort sub-asc --limit 15
```

### 4. Search by Keyword & Category
```bash
# Search for statements containing "AI" in Software
python server/cli.py --keyword "AI" --category Software

# Search by Theme/Domain
python server/cli.py --theme "Disaster Management"
```

### 5. Export Selected Data
```bash
# Export to CSV (includes full problem descriptions)
python server/cli.py --ps SIH26001,SIH26002 --export shortlist.csv

# Export to JSON
python server/cli.py --keyword "Blockchain" --export blockchain_ps.json

# Export to Markdown table
python server/cli.py --sort sub-asc --limit 20 --export top_picks.md
```

### 6. Interactive Terminal Wizard
Run with no arguments or `--interactive` for an easy-to-use menu:
```bash
python server/cli.py --interactive
```

### 7. Hackathon Overview & Statistics
```bash
python server/cli.py --summary
```

### 8. Visual Web Dashboard
Launch the local web dashboard:
```bash
python server/app.py
```
Open your browser at **`http://127.0.0.1:8000`** to search, pin statements to your watchlist, view live capacity progress bars, and export data.

---

## 💻 Python Library Usage

You can also import and use the scraper in your own Python projects:

```python
from sih_scraper import SIHScraper, LiveTracker

scraper = SIHScraper()

# 1. Fetch specific problem statements
statements = scraper.get_by_ids(["SIH26001", "26002"])
for ps in statements:
    print(f"ID: {ps.id}")
    print(f"Title: {ps.title}")
    print(f"Submissions: {ps.submitted_count} / {ps.capacity} ({ps.percentage_filled}%)")
    print(f"Slots Remaining: {ps.slots_remaining}")
    print(f"Status: {ps.status}")

# 2. Filter programmatically
ai_software = scraper.filter_statements(
    category="Software",
    keyword="AI",
    max_submissions=50,  # low competition
    sort_by="sub-asc"
)

# 3. Monitor live submission updates with a callback
def on_new_submission(statement, prev_count, new_count):
    print(f"ALERT: {statement.id} received a new submission! {prev_count} -> {new_count}")

tracker = LiveTracker(
    target_ids=["SIH26001"],
    interval_seconds=30,
    on_update_callback=on_new_submission
)
tracker.start_console_watch()
```

---

## 🧪 Running Tests

Run the unit test suite:
```bash
python -m unittest discover server/tests
```
