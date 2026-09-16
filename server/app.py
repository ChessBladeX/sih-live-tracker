"""FastAPI Web Dashboard for SIH Live Submission Tracker."""

import os
import sys
from pathlib import Path
from typing import Optional, List

# Ensure server package directory is in sys.path
SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from sih_scraper import SIHScraper, normalize_id

app = FastAPI(title="SIH Live Submission Dashboard")

scraper = SIHScraper()

# Resolve client frontend directory
CLIENT_DIR = SERVER_DIR.parent / "client"
if not CLIENT_DIR.exists():
    CLIENT_DIR = SERVER_DIR / "client"


@app.get("/api/statements")
def get_statements(
    ps_ids: Optional[str] = Query(None, description="Comma-separated PS IDs"),
    category: Optional[str] = Query(None),
    theme: Optional[List[str]] = Query(None, description="One or more themes to filter by"),
    themes: Optional[List[str]] = Query(None, description="Alias for theme list"),
    keyword: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    min_submissions: Optional[int] = Query(None),
    max_submissions: Optional[int] = Query(None),
    submission_range: Optional[str] = Query(None, description="Range string like '15-59'"),
    refresh: bool = Query(False),
):
    """Fetch problem statements with live submission metrics and multi-theme filtering."""
    try:
        ps_ids = ps_ids if isinstance(ps_ids, str) else None
        category = category if isinstance(category, str) else None
        keyword = keyword if isinstance(keyword, str) else None
        sort_by = sort_by if isinstance(sort_by, str) else None
        refresh = refresh if isinstance(refresh, bool) else False

        # Gather multiple themes if provided
        selected_themes = []
        raw_list = []
        if isinstance(theme, list):
            raw_list.extend(theme)
        elif isinstance(theme, str):
            raw_list.append(theme)

        if isinstance(themes, list):
            raw_list.extend(themes)
        elif isinstance(themes, str):
            raw_list.append(themes)

        for t in raw_list:
            if t and isinstance(t, str) and t.strip():
                selected_themes.append(t.strip())

        # Parse submission_range if provided (e.g., "15-59", "15 - 59", "<50", ">20")
        min_sub = min_submissions if isinstance(min_submissions, int) else None
        max_sub = max_submissions if isinstance(max_submissions, int) else None
        if submission_range and isinstance(submission_range, str):
            sr = submission_range.strip()
            if "-" in sr:
                parts = sr.split("-", 1)
                if parts[0].strip().isdigit():
                    min_sub = int(parts[0].strip())
                if parts[1].strip().isdigit():
                    max_sub = int(parts[1].strip())
            elif sr.startswith("<"):
                val = sr[1:].strip()
                if val.isdigit():
                    max_sub = int(val)
            elif sr.startswith(">"):
                val = sr[1:].strip()
                if val.isdigit():
                    min_sub = int(val)
            elif sr.isdigit():
                min_sub = int(sr)

        if ps_ids:
            ids = [p.strip() for p in ps_ids.split(",") if p.strip()]
            results = scraper.get_by_ids(ids, force_refresh=refresh)
            if selected_themes:
                results = [
                    r for r in results
                    if r.theme and any(st.lower() in r.theme.lower() for st in selected_themes)
                ]
            if min_sub is not None:
                results = [r for r in results if r.submitted_count >= min_sub]
            if max_sub is not None:
                results = [r for r in results if r.submitted_count <= max_sub]
        else:
            results = scraper.filter_statements(
                category=category,
                theme=selected_themes if selected_themes else None,
                keyword=keyword,
                min_submissions=min_sub,
                max_submissions=max_sub,
                sort_by=sort_by,
                force_refresh=refresh,
            )

        return {
            "count": len(results),
            "data": [ps.to_dict() for ps in results],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/import-all-descriptions")
def import_all_descriptions():
    """Import and save all problem statements as individual Markdown files in descriptions/ folder."""
    try:
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

        return {
            "success": True,
            "message": f"Successfully imported {len(statements)} full problem statement descriptions to {out_dir.resolve()}",
            "count": len(statements),
            "directory": str(out_dir.resolve()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/summary")
def get_summary(refresh: bool = Query(False)):
    """Fetch aggregate statistics across all hackathon statements."""
    try:
        stats = scraper.get_summary(force_refresh=refresh)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/categories-and-themes")
def get_meta():
    """Fetch distinct categories, themes, and theme counts for dropdown filters."""
    from collections import Counter
    all_ps = scraper.fetch_all()
    theme_counts = Counter(ps.theme for ps in all_ps if ps.theme)
    themes = sorted(theme_counts.keys())
    categories = sorted({ps.category for ps in all_ps if ps.category})
    all_ids = [{"id": ps.id, "title": ps.title} for ps in all_ps]
    return {
        "themes": themes,
        "theme_counts": dict(theme_counts),
        "categories": categories,
        "all_problem_statements": all_ids,
    }


# Mount frontend assets
app.mount("/static", StaticFiles(directory=CLIENT_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Serve web dashboard index page."""
    index_file = CLIENT_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>SIH Web Dashboard</h1><p>client/index.html not found.</p>")


@app.get("/style.css")
def serve_css():
    """Serve style.css directly from client root."""
    css_file = CLIENT_DIR / "style.css"
    if css_file.exists():
        return FileResponse(css_file)
    raise HTTPException(status_code=404, detail="style.css not found")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SIH Live Dashboard at http://127.0.0.1:8000")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
