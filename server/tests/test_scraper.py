"""Unit tests for SIH Problem Statement Scraper."""

import sys
import unittest
from pathlib import Path
import tempfile

# Ensure server package directory is in sys.path
SERVER_DIR = Path(__file__).resolve().parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from sih_scraper.models import ProblemStatement
from sih_scraper.scraper import SIHScraper, clean_text, normalize_id
from sih_scraper.exporter import export_csv, export_json, format_terminal_table


class TestSIHScraper(unittest.TestCase):

    def test_normalize_id(self):
        self.assertEqual(normalize_id("SIH26001"), "26001")
        self.assertEqual(normalize_id("sih26001"), "26001")
        self.assertEqual(normalize_id("sih-26001"), "26001")
        self.assertEqual(normalize_id("#26001"), "26001")
        self.assertEqual(normalize_id("26001"), "26001")

    def test_clean_text_mojibake(self):
        raw = "AI\u00e2\u20ac\u201cBased early warning   system\u00e2\u20ac\u2122s"
        cleaned = clean_text(raw)
        self.assertEqual(cleaned, "AI-Based early warning system's")

    def test_problem_statement_metrics(self):
        ps = ProblemStatement(
            id="SIH26001",
            numeric_id="26001",
            sno=1,
            title="Early Warning System",
            organization="Org A",
            department="Dept A",
            category="Software",
            theme="Disaster Management",
            submitted_count=100,
            capacity=500,
            deadline="30 Sept 2026",
        )
        self.assertEqual(ps.percentage_filled, 20.0)
        self.assertEqual(ps.slots_remaining, 400)
        self.assertFalse(ps.is_full)
        self.assertEqual(ps.status, "MODERATE")

        # Full test
        ps_full = ProblemStatement(
            id="SIH26002",
            numeric_id="26002",
            sno=2,
            title="Full Challenge",
            organization="Org B",
            department="Dept B",
            category="Hardware",
            theme="Robotics",
            submitted_count=500,
            capacity=500,
            deadline="30 Sept 2026",
        )
        self.assertEqual(ps_full.percentage_filled, 100.0)
        self.assertEqual(ps_full.slots_remaining, 0)
        self.assertTrue(ps_full.is_full)
        self.assertEqual(ps_full.status, "FROZEN (FULL)")

    def test_parse_html(self):
        sample_html = """
        <html>
          <body>
            <table class="dataTablePS">
              <thead>
                <tr>
                  <th>S.No.</th><th>Organization</th><th>Problem Statement Title</th>
                  <th>Category</th><th>PS Number</th><th>Submitted Idea(s) Count</th>
                  <th>Theme</th><th>Deadline for Idea Submission</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>1</td>
                  <td>Ministry of AI</td>
                  <td>
                    <a href="#">AI Traffic Controller</a>
                    <div class="modal-body">
                      <table>
                        <tr><th>Description</th><td>Smart camera feed analyzer</td></tr>
                        <tr><th>Department</th><td>Smart Cities Division</td></tr>
                      </table>
                    </div>
                  </td>
                  <td>Software</td>
                  <td>SIH26099</td>
                  <td>25/500</td>
                  <td>Smart Automation</td>
                  <td>30 September 2026</td>
                </tr>
              </tbody>
            </table>
          </body>
        </html>
        """
        scraper = SIHScraper()
        records = scraper.parse_html(sample_html)
        self.assertEqual(len(records), 1)
        item = records[0]
        self.assertEqual(item.id, "SIH26099")
        self.assertEqual(item.numeric_id, "26099")
        self.assertEqual(item.title, "AI Traffic Controller")
        self.assertEqual(item.category, "Software")
        self.assertEqual(item.submitted_count, 25)
        self.assertEqual(item.capacity, 500)
        self.assertEqual(item.percentage_filled, 5.0)
        self.assertEqual(item.slots_remaining, 475)
        self.assertEqual(item.department, "Smart Cities Division")
        self.assertEqual(item.description, "Smart camera feed analyzer")

    def test_export_csv_and_json(self):
        ps = ProblemStatement(
            id="SIH26001",
            numeric_id="26001",
            sno=1,
            title="Test Statement",
            organization="Gov Dept",
            department="Gov Dept",
            category="Software",
            theme="Smart Cities",
            submitted_count=50,
            capacity=500,
            deadline="30 Sept 2026",
        )
        tmp_dir = Path(__file__).parent / "_tmp_test"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            csv_path = tmp_dir / "test.csv"
            json_path = tmp_dir / "test.json"

            export_csv([ps], csv_path)
            export_json([ps], json_path)

            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("SIH26001", csv_path.read_text(encoding="utf-8"))
            self.assertIn("SIH26001", json_path.read_text(encoding="utf-8"))
        finally:
            import shutil
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_filter_by_range(self):
        scraper = SIHScraper()
        # Mock records
        r1 = ProblemStatement("SIH1", "1", 1, "T1", "O", "D", "Software", "Th", 10, 500, "30 Sept")
        r2 = ProblemStatement("SIH2", "2", 2, "T2", "O", "D", "Software", "Th", 25, 500, "30 Sept")
        r3 = ProblemStatement("SIH3", "3", 3, "T3", "O", "D", "Software", "Th", 60, 500, "30 Sept")
        scraper._cached_records = [r1, r2, r3]
        scraper._last_fetch_time = 9999999999.0

        filtered = scraper.filter_statements(min_submissions=15, max_submissions=59)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, "SIH2")

    def test_terminal_table_formatting(self):
        ps = ProblemStatement(
            id="SIH26001",
            numeric_id="26001",
            sno=1,
            title="Testing Table Formatting",
            organization="Gov Dept",
            department="Gov Dept",
            category="Software",
            theme="Smart Cities",
            submitted_count=10,
            capacity=500,
            deadline="30 Sept 2026",
        )
        table_str = format_terminal_table([ps])
        self.assertIn("SIH26001", table_str)
        self.assertIn("10/500", table_str)
        self.assertIn("Software", table_str)

    def test_filter_by_multiple_themes(self):
        scraper = SIHScraper()
        r1 = ProblemStatement("SIH1", "1", 1, "T1", "Org", "Dept", "Software", "Disaster Management", 10, 500, "30 Sept")
        r2 = ProblemStatement("SIH2", "2", 2, "T2", "Org", "Dept", "Hardware", "Robotics and Drones", 20, 500, "30 Sept")
        r3 = ProblemStatement("SIH3", "3", 3, "T3", "Org", "Dept", "Software", "Clean & Green Technology", 30, 500, "30 Sept")
        r4 = ProblemStatement("SIH4", "4", 4, "T4", "Org", "Dept", "Software", "Agriculture, FoodTech & Rural Development", 40, 500, "30 Sept")
        scraper._cached_records = [r1, r2, r3, r4]
        scraper._last_fetch_time = 9999999999.0

        # 1. Single theme (str)
        res1 = scraper.filter_statements(theme="Disaster Management")
        self.assertEqual([r.id for r in res1], ["SIH1"])

        # 2. Multiple themes as list
        res2 = scraper.filter_statements(theme=["Disaster Management", "Robotics and Drones"])
        self.assertEqual([r.id for r in res2], ["SIH1", "SIH2"])

        # 3. Multiple themes as themes argument
        res3 = scraper.filter_statements(themes=["Robotics and Drones", "Clean & Green Technology"])
        self.assertEqual([r.id for r in res3], ["SIH2", "SIH3"])

        # 4. Comma-separated string
        res4 = scraper.filter_statements(theme="Disaster, Robotics")
        self.assertEqual([r.id for r in res4], ["SIH1", "SIH2"])

        # 5. Theme with embedded comma (Agriculture, FoodTech & Rural Development)
        res5 = scraper.filter_statements(theme="Agriculture, FoodTech & Rural Development")
        self.assertEqual([r.id for r in res5], ["SIH4"])

        # 6. Embedded comma theme alongside another theme in a list
        res6 = scraper.filter_statements(theme=["Agriculture, FoodTech & Rural Development", "Clean & Green Technology"])
        self.assertEqual([r.id for r in res6], ["SIH3", "SIH4"])

        # 7. Multi-theme combined with category filter
        res7 = scraper.filter_statements(theme=["Disaster Management", "Robotics and Drones"], category="Software")
        self.assertEqual([r.id for r in res7], ["SIH1"])


if __name__ == "__main__":
    unittest.main()

