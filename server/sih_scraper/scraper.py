"""Core web scraper for Smart India Hackathon problem statements."""

import logging
import re
import time
from typing import List, Optional, Dict, Any, Union
import requests
from bs4 import BeautifulSoup

from .config import (
    DEFAULT_SIH_URL,
    DEFAULT_HEADERS,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    MOJIBAKE_FIX,
)
from .models import ProblemStatement

logger = logging.getLogger(__name__)


def clean_text(text: Optional[str]) -> str:
    """Normalize whitespace and fix character encoding glitches."""
    if not text:
        return ""
    for bad, good in MOJIBAKE_FIX.items():
        text = text.replace(bad, good)
    # Collapse irregular whitespace into single space
    return re.sub(r"\s+", " ", text).strip()


def normalize_id(ps_id: Union[str, int]) -> str:
    """Normalize input PS ID (e.g., 'SIH26001', 'sih-26001', '26001' -> '26001')."""
    clean = str(ps_id).strip().upper()
    clean = re.sub(r"^SIH-?", "", clean)
    clean = re.sub(r"^#", "", clean)
    return clean.strip()


def clean_description(element) -> str:
    """Extract and format full rich description with paragraphs and lists preserved."""
    if not element:
        return ""
    
    # Work on a clone or direct element
    desc_div = element.find("div", class_="style-2") or element
    
    # Replace <br> tags with newlines
    for br in desc_div.find_all("br"):
        br.replace_with("\n")
        
    # Highlight bold labels like <b>Background:</b> or <b>Expected Solution:</b>
    for b in desc_div.find_all(["b", "strong"]):
        b_text = b.get_text(strip=True)
        if b_text:
            b.string = f"\n**{b_text}**\n"

    raw_text = desc_div.get_text()
    
    # Fix mojibake
    for bad, good in MOJIBAKE_FIX.items():
        raw_text = raw_text.replace(bad, good)
        
    # Clean up excessive line breaks
    cleaned = re.sub(r"[ \t]+", " ", raw_text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


class SIHScraper:
    """Scraper to fetch and extract problem statement submission counts."""

    def __init__(
        self,
        url: str = DEFAULT_SIH_URL,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = DEFAULT_TIMEOUT,
        cache_ttl: int = 15,
    ):
        self.url = url
        self.headers = headers or DEFAULT_HEADERS
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cached_records: List[ProblemStatement] = self.load_local_data()
        self._last_fetch_time: float = 0.0

    def save_local_cache(self, records: List[ProblemStatement]):
        """Persist fresh records to disk cache."""
        try:
            from pathlib import Path
            import json
            base = Path(__file__).resolve().parent.parent
            cache_file = base / "data" / "cached_statements.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = [r.to_dict() for r in records]
            cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("Saved %d updated problem statements to %s", len(records), cache_file)
        except Exception as e:
            logger.warning("Could not persist cache to file: %s", e)

    def fetch_html(self) -> str:
        """Fetch raw HTML from portal with automatic retries."""
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug("Fetching SIH portal (attempt %d/%d)...", attempt, MAX_RETRIES)
                response = requests.get(
                    self.url,
                    headers=self.headers,
                    timeout=(10, self.timeout),
                )
                response.raise_for_status()
                # Ensure correct UTF-8 decoding
                response.encoding = "utf-8"
                return response.text
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_error = e
                logger.warning("Network/Connection issue reaching SIH portal (attempt %d/%d): %s", attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
            except Exception as e:
                last_error = e
                logger.warning("Attempt %d failed: %s", attempt, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)

        raise RuntimeError(
            f"Failed to fetch data from {self.url} after {MAX_RETRIES} attempts: {last_error}"
        )

    def parse_modal(self, modal_elem) -> Dict[str, str]:
        """Extract detailed metadata and full rich description from the statement's modal popover."""
        details = {
            "department": "",
            "description": "",
            "youtube_link": "",
            "dataset_link": "",
            "contact_info": "",
        }
        if not modal_elem:
            return details

        for row in modal_elem.find_all("tr"):
            cols = row.find_all(["th", "td"])
            if len(cols) >= 2:
                key = clean_text(cols[0].get_text()).lower()

                if "department" in key:
                    details["department"] = clean_text(cols[1].get_text())
                elif "description" in key:
                    details["description"] = clean_description(cols[1])
                elif "youtube" in key:
                    a_tag = cols[1].find("a")
                    val = a_tag["href"] if a_tag and a_tag.has_attr("href") else cols[1].get_text().strip()
                    details["youtube_link"] = val
                elif "dataset" in key:
                    a_tag = cols[1].find("a")
                    val = a_tag["href"] if a_tag and a_tag.has_attr("href") else cols[1].get_text().strip()
                    details["dataset_link"] = val
                elif "contact" in key:
                    details["contact_info"] = clean_text(cols[1].get_text())

        return details

    def parse_html(self, html_content: str) -> List[ProblemStatement]:
        """Parse HTML table into ProblemStatement instances."""
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        if not table:
            raise ValueError("No table found on the SIH problem statements page.")

        tbody = table.find("tbody") or table
        rows = tbody.find_all("tr", recursive=False)
        records: List[ProblemStatement] = []

        for row in rows:
            tds = row.find_all("td", recursive=False)
            if len(tds) < 8:
                continue

            # Column 0: S.No.
            try:
                sno = int(clean_text(tds[0].get_text()))
            except ValueError:
                sno = len(records) + 1

            # Column 1: Organization
            organization = clean_text(tds[1].get_text())

            # Column 2: Title & Details Modal
            td2 = tds[2]
            title_tag = td2.find("a")
            title = clean_text(title_tag.get_text()) if title_tag else clean_text(td2.get_text())
            # Clean up trailing modal trigger markers if present
            title = re.sub(r"\s*Problem Statement Details\s*$", "", title, flags=re.IGNORECASE)

            modal_elem = td2.find("div", class_=re.compile(r"modal|modal-body"))
            modal_details = self.parse_modal(modal_elem)

            # Column 3: Category (Software/Hardware)
            category = clean_text(tds[3].get_text())

            # Column 4: PS Number (e.g. SIH26001)
            ps_id_raw = clean_text(tds[4].get_text())
            numeric_id = normalize_id(ps_id_raw)
            formatted_id = ps_id_raw if ps_id_raw.upper().startswith("SIH") else f"SIH{numeric_id}"

            # Column 5: Submitted Idea(s) Count (e.g. "92/500" or "92")
            sub_count_text = clean_text(tds[5].get_text())
            submitted_count = 0
            capacity = 500
            if "/" in sub_count_text:
                parts = sub_count_text.split("/", 1)
                try:
                    submitted_count = int(parts[0].strip())
                    capacity = int(parts[1].strip())
                except ValueError:
                    pass
            else:
                try:
                    submitted_count = int(sub_count_text)
                except ValueError:
                    pass

            # Column 6: Theme
            theme = clean_text(tds[6].get_text())

            # Column 7: Deadline
            deadline = clean_text(tds[7].get_text())

            ps = ProblemStatement(
                id=formatted_id,
                numeric_id=numeric_id,
                sno=sno,
                title=title,
                organization=organization,
                department=modal_details.get("department") or organization,
                category=category,
                theme=theme,
                submitted_count=submitted_count,
                capacity=capacity,
                deadline=deadline,
                description=modal_details.get("description", ""),
                youtube_link=modal_details.get("youtube_link", ""),
                dataset_link=modal_details.get("dataset_link", ""),
                contact_info=modal_details.get("contact_info", ""),
            )
            records.append(ps)

        return records

    def load_from_descriptions_dir(self) -> List[ProblemStatement]:
        """Fallback loader that parses local descriptions/ markdown files if portal is unreachable."""
        from pathlib import Path
        desc_dir = Path(__file__).resolve().parent.parent / "descriptions"
        if not desc_dir.exists():
            desc_dir = Path(__file__).resolve().parent.parent.parent / "descriptions"
        if not desc_dir.exists():
            return []

        records = []
        md_files = sorted(desc_dir.glob("*.md"))
        for f in md_files:
            try:
                content = f.read_text(encoding="utf-8")
                lines = content.splitlines()
                if not lines:
                    continue
                first_line = lines[0]
                m = re.match(r"^#\s*([A-Za-z0-9_-]+)\s*:\s*(.*)", first_line)
                if not m:
                    continue
                ps_id = m.group(1).strip()
                title = m.group(2).strip()
                numeric_id = normalize_id(ps_id)

                def get_field(pat):
                    match = re.search(pat, content)
                    return match.group(1).strip() if match else ""

                org = get_field(r"\*\*Organization:\*\*\s*(.*)")
                dept = get_field(r"\*\*Department:\*\*\s*(.*)")
                cat = get_field(r"\*\*Category:\*\*\s*(.*)")
                theme = get_field(r"\*\*Theme / Domain:\*\*\s*(.*)")
                deadline = get_field(r"\*\*Deadline:\*\*\s*(.*)")
                youtube = get_field(r"\*\*YouTube Video:\*\*\s*(.*)")
                dataset = get_field(r"\*\*Dataset Link:\*\*\s*(.*)")
                contact = get_field(r"\*\*Contact Info:\*\*\s*(.*)")

                submitted = 0
                cap = 500
                subs_match = re.search(r"\*\*Live Submissions:\*\*\s*(\d+)\s*/\s*(\d+)", content)
                if subs_match:
                    submitted = int(subs_match.group(1))
                    cap = int(subs_match.group(2))

                desc_parts = content.split("## Problem Description", 1)
                desc = desc_parts[1].strip() if len(desc_parts) > 1 else ""

                sno = int(numeric_id) if numeric_id.isdigit() else len(records) + 1

                records.append(ProblemStatement(
                    id=ps_id,
                    numeric_id=numeric_id,
                    sno=sno,
                    title=title,
                    organization=org,
                    department=dept or org,
                    category=cat,
                    theme=theme,
                    submitted_count=submitted,
                    capacity=cap,
                    deadline=deadline,
                    description=desc,
                    youtube_link=youtube,
                    dataset_link=dataset,
                    contact_info=contact,
                ))
            except Exception:
                continue
        return records

    def load_local_data(self) -> List[ProblemStatement]:
        """Load records from pre-compiled JSON cache or local descriptions/ directory."""
        from pathlib import Path
        import json

        base = Path(__file__).resolve().parent.parent
        possible_json_paths = [
            base / "data" / "cached_statements.json",
            base.parent / "server" / "data" / "cached_statements.json",
        ]
        for jp in possible_json_paths:
            if jp.exists():
                try:
                    data = json.loads(jp.read_text(encoding="utf-8"))
                    records = [ProblemStatement.from_dict(d) for d in data]
                    if records:
                        return records
                except Exception as e:
                    logger.debug("Failed loading JSON cache %s: %s", jp, e)

        return self.load_from_descriptions_dir()

    def fetch_all(self, force_refresh: bool = False) -> List[ProblemStatement]:
        """Fetch all problem statements, using local data only as an offline fallback."""
        now = time.time()
        if not force_refresh and self._cached_records and (now - self._last_fetch_time < self.cache_ttl):
            return self._cached_records

        try:
            html = self.fetch_html()
            parsed = self.parse_html(html)
            if not parsed:
                raise ValueError("The SIH portal returned no problem statements.")
            self._cached_records = parsed
            self._last_fetch_time = now
            self.save_local_cache(parsed)
            return self._cached_records
        except Exception as e:
            if force_refresh:
                raise RuntimeError(f"Live SIH refresh failed: {e}") from e
            if self._cached_records:
                logger.warning("SIH portal fetch error (%s); serving last known statements", e)
                return self._cached_records
            fallback = self.load_local_data()
            if fallback:
                logger.info("Loaded %d records from offline data store", len(fallback))
                self._cached_records = fallback
                self._last_fetch_time = now
                return self._cached_records
            raise

    def get_by_ids(self, ps_ids: List[Union[str, int]], force_refresh: bool = False) -> List[ProblemStatement]:
        """Filter problem statements by requested IDs (supports 'SIH26001' or '26001')."""
        all_ps = self.fetch_all(force_refresh=force_refresh)
        normalized_targets = {normalize_id(pid) for pid in ps_ids}
        return [ps for ps in all_ps if ps.numeric_id in normalized_targets or ps.id in ps_ids]

    def filter_statements(
        self,
        category: Optional[str] = None,
        theme: Optional[Union[str, List[str]]] = None,
        themes: Optional[List[str]] = None,
        organization: Optional[str] = None,
        keyword: Optional[str] = None,
        min_submissions: Optional[int] = None,
        max_submissions: Optional[int] = None,
        only_open: bool = False,
        sort_by: Optional[str] = None,
        force_refresh: bool = False,
    ) -> List[ProblemStatement]:
        """Search and filter problem statements with custom criteria.
        Supports single theme string, comma-separated themes, or list of themes."""
        records = self.fetch_all(force_refresh=force_refresh)

        if category:
            records = [r for r in records if r.category.lower() == category.lower()]

        # Combine theme and themes arguments
        raw_themes = []
        if theme:
            if isinstance(theme, str):
                raw_themes.append(theme)
            elif isinstance(theme, (list, tuple, set)):
                raw_themes.extend(theme)
        if themes:
            if isinstance(themes, str):
                raw_themes.append(themes)
            elif isinstance(themes, (list, tuple, set)):
                raw_themes.extend(themes)

        if raw_themes:
            known_themes_lower = {r.theme.strip().lower() for r in records if r.theme}
            target_themes = []
            for t in raw_themes:
                if not t:
                    continue
                t_str = str(t).strip()
                t_lower = t_str.lower()
                if t_lower in known_themes_lower:
                    target_themes.append(t_lower)
                elif "," in t_str:
                    parts = [p.strip().lower() for p in t_str.split(",") if p.strip()]
                    target_themes.extend(parts)
                else:
                    target_themes.append(t_lower)

            if target_themes:
                records = [
                    r for r in records
                    if r.theme and any(tgt in r.theme.lower() for tgt in target_themes)
                ]

        if organization:
            records = [r for r in records if organization.lower() in r.organization.lower()]

        if keyword:
            kw = keyword.lower()
            records = [
                r for r in records
                if kw in r.title.lower() or kw in r.description.lower() or kw in r.id.lower()
            ]

        if min_submissions is not None:
            records = [r for r in records if r.submitted_count >= min_submissions]

        if max_submissions is not None:
            records = [r for r in records if r.submitted_count <= max_submissions]

        if only_open:
            records = [r for r in records if not r.is_full]

        if sort_by:
            if sort_by in ("submissions-asc", "sub-asc"):
                records.sort(key=lambda x: x.submitted_count)
            elif sort_by in ("submissions-desc", "sub-desc"):
                records.sort(key=lambda x: x.submitted_count, reverse=True)
            elif sort_by in ("percentage-asc", "pct-asc"):
                records.sort(key=lambda x: x.percentage_filled)
            elif sort_by in ("percentage-desc", "pct-desc"):
                records.sort(key=lambda x: x.percentage_filled, reverse=True)
            elif sort_by in ("id-asc", "id"):
                records.sort(key=lambda x: x.sno)

        return records

    def get_summary(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Compute aggregate statistics across all problem statements."""
        records = self.fetch_all(force_refresh=force_refresh)
        if not records:
            return {}

        total = len(records)
        total_submissions = sum(r.submitted_count for r in records)
        full_count = sum(1 for r in records if r.is_full)
        software_count = sum(1 for r in records if r.category.lower() == "software")
        hardware_count = sum(1 for r in records if r.category.lower() == "hardware")

        sorted_by_subs = sorted(records, key=lambda x: x.submitted_count)
        least_competitive = [r.to_summary() for r in sorted_by_subs[:5]]
        most_competitive = [r.to_summary() for r in sorted_by_subs[-5:][::-1]]

        return {
            "total_problem_statements": total,
            "total_live_submissions": total_submissions,
            "average_submissions": round(total_submissions / total, 1) if total else 0,
            "frozen_statements_count": full_count,
            "software_count": software_count,
            "hardware_count": hardware_count,
            "least_competitive_top5": least_competitive,
            "most_competitive_top5": most_competitive,
        }
