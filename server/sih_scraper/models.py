"""Data models for SIH problem statements."""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class ProblemStatement:
    id: str  # e.g. "SIH26001"
    numeric_id: str  # e.g. "26001"
    sno: int
    title: str
    organization: str
    department: str
    category: str  # "Software" or "Hardware"
    theme: str
    submitted_count: int
    capacity: int
    deadline: str
    description: str = ""
    youtube_link: str = ""
    dataset_link: str = ""
    contact_info: str = ""

    @property
    def percentage_filled(self) -> float:
        """Percentage of maximum submissions reached."""
        if self.capacity <= 0:
            return 0.0
        return round((self.submitted_count / self.capacity) * 100, 2)

    @property
    def slots_remaining(self) -> int:
        """Slots left before idea submissions freeze."""
        return max(0, self.capacity - self.submitted_count)

    @property
    def is_full(self) -> bool:
        """Whether submissions have reached full capacity."""
        return self.slots_remaining == 0

    @property
    def status(self) -> str:
        """Current competition and availability status."""
        if self.is_full:
            return "FROZEN (FULL)"
        pct = self.percentage_filled
        if pct >= 80.0:
            return "CRITICAL (>80%)"
        if pct >= 50.0:
            return "HIGH (>50%)"
        if pct >= 20.0:
            return "MODERATE"
        return "LOW (<20%)"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary including calculated metrics."""
        data = asdict(self)
        data["percentage_filled"] = self.percentage_filled
        data["slots_remaining"] = self.slots_remaining
        data["is_full"] = self.is_full
        data["status"] = self.status
        return data

    def to_summary(self) -> Dict[str, Any]:
        """Concise dictionary for tabular displays."""
        return {
            "ID": self.id,
            "Title": self.title,
            "Category": self.category,
            "Theme": self.theme,
            "Submissions": f"{self.submitted_count}/{self.capacity}",
            "Filled": f"{self.percentage_filled:.1f}%",
            "Status": self.status,
            "Organization": self.organization,
            "Deadline": self.deadline,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProblemStatement":
        """Create ProblemStatement from dictionary, safely filtering computed fields."""
        valid_fields = {
            "id", "numeric_id", "sno", "title", "organization",
            "department", "category", "theme", "submitted_count",
            "capacity", "deadline", "description", "youtube_link",
            "dataset_link", "contact_info"
        }
        kwargs = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**kwargs)
