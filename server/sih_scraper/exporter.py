"""Export and formatting utilities for scraped SIH problem statements."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List, Union
from .models import ProblemStatement

# Type alias for path
Union_Path_or_Str = Union[str, Path]


def export_csv(statements: List[ProblemStatement], filepath: Union_Path_or_Str) -> Path:
    """Export problem statements to a CSV file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "numeric_id",
        "sno",
        "title",
        "organization",
        "department",
        "category",
        "theme",
        "submitted_count",
        "capacity",
        "percentage_filled",
        "slots_remaining",
        "is_full",
        "status",
        "deadline",
        "youtube_link",
        "dataset_link",
        "contact_info",
        "description",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ps in statements:
            writer.writerow(ps.to_dict())

    return path


def export_json(
    statements: List[ProblemStatement],
    filepath: Union_Path_or_Str,
    indent: int = 2
) -> Path:
    """Export problem statements to a JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = [ps.to_dict() for ps in statements]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)

    return path


def export_markdown(statements: List[ProblemStatement], filepath: Union_Path_or_Str) -> Path:
    """Export problem statements as a formatted Markdown summary table."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Smart India Hackathon - Problem Statements Submission Report",
        "",
        f"**Total Selected Statements:** {len(statements)}",
        "",
        "| ID | Title | Category | Theme | Submissions | % Filled | Status | Deadline |",
        "| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |",
    ]

    for ps in statements:
        # Truncate title for markdown table
        title = ps.title.replace("|", "-")
        theme = ps.theme.replace("|", "-")
        lines.append(
            f"| `{ps.id}` | {title} | {ps.category} | {theme} | {ps.submitted_count}/{ps.capacity} | {ps.percentage_filled:.1f}% | {ps.status} | {ps.deadline} |"
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return path


def format_terminal_table(statements: List[ProblemStatement], max_title_len: int = 38) -> str:
    """Generate a clean aligned table string suitable for terminal display."""
    if not statements:
        return "No problem statements found matching criteria."

    headers = ["PS ID", "Category", "Submissions", "Filled", "Status", "Theme", "Title"]
    col_widths = [10, 10, 13, 8, 16, 22, max_title_len]

    def truncate(text: str, length: int) -> str:
        text = str(text)
        return text[: length - 2] + ".." if len(text) > length else text

    row_fmt = " | ".join([f"{{:<{w}}}" for w in col_widths])
    sep = "-+-".join(["-" * w for w in col_widths])

    lines = [
        row_fmt.format(*headers),
        sep,
    ]

    for ps in statements:
        sub_str = f"{ps.submitted_count}/{ps.capacity}"
        pct_str = f"{ps.percentage_filled:.1f}%"
        lines.append(
            row_fmt.format(
                ps.id,
                ps.category,
                sub_str,
                pct_str,
                ps.status,
                truncate(ps.theme, col_widths[5]),
                truncate(ps.title, col_widths[6]),
            )
        )

    return "\n".join(lines)
