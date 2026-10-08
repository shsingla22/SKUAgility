"""Shared record shape and helpers for every workload provider.

A provider's job is to turn Microsoft documentation into `Sku` records. It owns
its own parsing, because every service documents its SKUs differently, but the
record it returns is identical across workloads so the catalog, table and Atlas
never special-case a service.

Contract — each provider module exposes:

    WORKLOAD   str        stable identifier, matches sources.json
    SERVICE    str        display name
    SOURCES    list[str]  source keys it needs from sources.json
    collect(docs) -> list[Sku]

`docs` is {source_key: Doc}. A provider that cannot find its expected table must
raise, not return a short list: a silently shrinking catalog is the failure mode
worth guarding hardest against.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, asdict

sys.path.insert(0, __file__.rsplit("/providers/", 1)[0] + "/references")

from milestones import MILESTONES, NOT_ESTABLISHED, release_date_for   # noqa: E402

GA = "Generally available"
PREVIEW = "Public preview"


def retiring(date: str) -> str:
    return f"Retiring - {date}"


@dataclass
class Sku:
    workload: str
    service: str
    sku: str
    tier: str
    series: str
    capacity: float | None
    capacity_unit: str
    memory_gb: float | None
    lifecycle_status: str
    milestone: str
    inventory_doc: str
    recommend_when: list[str] = field(default_factory=list)
    recommend_sources: list[str] = field(default_factory=list)
    release_date: str = ""
    date_confidence: str = ""
    milestone_label: str = ""
    release_doc: str = ""
    notes: str = ""

    def resolve(self) -> "Sku":
        m = MILESTONES[self.milestone]
        self.release_date, self.date_confidence = release_date_for(
            self.milestone, self.lifecycle_status)
        self.milestone_label = m.label
        self.release_doc = m.source
        if m.note and not self.notes:
            self.notes = m.note
        return self

    def dict(self) -> dict:
        return asdict(self)


def num(text: str) -> float | None:
    """First number in a cell, tolerating '1,024 GiB', '4 vCores', '~8'."""
    import re
    m = re.search(r"(\d[\d,]*\.?\d*)", text.replace(" ", " "))
    return float(m.group(1).replace(",", "")) if m else None


def sentences(text: str, limit: int = 8) -> list[str]:
    """Split documentation prose into clean, numbered-list-ready conditions.

    HTML entities are decoded before splitting. Without that, "Intel&reg; Xeon"
    splits on the entity's semicolon and yields the fragment "This new processor
    features Intel&reg." instead of a usable sentence.
    """
    import html
    import re
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.;])\s+(?=[A-Z(])", text)
    out = []
    for p in parts:
        p = p.strip().rstrip(";").strip()
        if len(p) < 25:                 # drop stubs left by lists and headings
            continue
        if len(p.split()) < 5:          # and anything that is not a real sentence
            continue
        if not p.endswith("."):
            p += "."
        out.append(p)
        if len(out) >= limit:
            break
    return out
