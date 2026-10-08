#!/usr/bin/env python3
"""Fetch and normalise Microsoft documentation for any Azure workload.

Two fetch strategies, because Azure documentation lives in several repositories
and not all of them are reachable as raw Markdown from every environment:

  raw    - the Learn article source on GitHub. Preferred: the Markdown states
           SKU names explicitly and the tables are trivially parsed.
  learn  - the rendered Learn page. Used where the source repository is not
           publicly mirrored (the Azure databases docs, for one). Tables are
           extracted from the HTML into the same normalised shape.

Both strategies yield the same structure, so providers never care which was
used:

    Doc(key, url, sections=[Section(heading, level, tables=[Table(rows)])])
"""

from __future__ import annotations

import html as htmllib
import os
import re
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120 Safari/537.36")


@dataclass
class Table:
    rows: list[list[str]] = field(default_factory=list)

    @property
    def header(self) -> list[str]:
        return self.rows[0] if self.rows else []

    @property
    def body(self) -> list[list[str]]:
        return self.rows[1:]

    def column(self, name: str) -> int:
        """Index of the first header cell containing `name` (case-insensitive)."""
        low = name.lower()
        for i, h in enumerate(self.header):
            if low in h.lower():
                return i
        return -1


@dataclass
class Section:
    heading: str
    level: int
    tables: list[Table] = field(default_factory=list)
    text: str = ""


@dataclass
class Doc:
    key: str
    url: str
    sections: list[Section] = field(default_factory=list)
    raw: str = ""

    def section(self, *needles: str) -> Section | None:
        """First section whose heading contains every needle."""
        for s in self.sections:
            low = s.heading.lower()
            if all(n.lower() in low for n in needles):
                return s
        return None

    def tables(self) -> list[Table]:
        return [t for s in self.sections for t in s.tables]

    def find_table(self, *header_needles: str) -> Table | None:
        """First table whose header row contains all the given needles."""
        for t in self.tables():
            joined = " | ".join(t.header).lower()
            if all(n.lower() in joined for n in header_needles):
                return t
        return None


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------

def http_get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def cache_path(cache: str, key: str, strategy: str) -> str:
    return os.path.join(cache, f"{key}.{'md' if strategy == 'raw' else 'html'}")


def fetch(spec: dict, cache: str, offline: bool = False) -> str:
    """Download one source, or read it from cache. Returns the raw payload."""
    path = cache_path(cache, spec["key"], spec["strategy"])
    if offline or os.path.exists(path) and spec.get("_reuse"):
        if not os.path.exists(path):
            raise FileNotFoundError(f"{spec['key']} not cached")
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    payload = http_get(spec["fetch_url"])
    os.makedirs(cache, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(payload)
    return payload


def load(spec: dict, cache: str) -> Doc:
    path = cache_path(cache, spec["key"], spec["strategy"])
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"source '{spec['key']}' is not cached - run scripts/fetch_docs.py")
    with open(path, encoding="utf-8") as fh:
        payload = fh.read()
    parse = parse_markdown if spec["strategy"] == "raw" else parse_learn_html
    doc = parse(payload)
    doc.key, doc.url, doc.raw = spec["key"], spec["live_url"], payload
    return doc


# --------------------------------------------------------------------------
# markdown strategy
# --------------------------------------------------------------------------

CLEAN_MD = re.compile(r"<sup>.*?</sup>|\^\d+\^|<a id=\"[^\"]*\"></a>|<br\s*/?>")
LINK_MD = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _md_cell(cell: str) -> str:
    cell = CLEAN_MD.sub(" ", cell)
    cell = LINK_MD.sub(r"\1", cell)
    return cell.replace("**", "").replace("`", "").strip()


def parse_markdown(text: str) -> Doc:
    doc, current = Doc(key="", url=""), Section(heading="(front matter)", level=0)
    doc.sections.append(current)
    table: Table | None = None
    buf: list[str] = []

    for line in text.split("\n"):
        if line.startswith("#"):
            current.text = "\n".join(buf).strip()
            buf, table = [], None
            level = len(line) - len(line.lstrip("#"))
            current = Section(heading=_md_cell(line.lstrip("#").strip()), level=level)
            doc.sections.append(current)
            continue
        if line.lstrip().startswith("|"):
            cells = [_md_cell(c) for c in line.strip().strip("|").split("|")]
            if cells and set("".join(cells)) <= set("-: "):
                continue                                   # separator row
            if table is None:
                table = Table()
                current.tables.append(table)
            table.rows.append(cells)
            continue
        table = None
        buf.append(line)
    current.text = "\n".join(buf).strip()
    return doc


# --------------------------------------------------------------------------
# rendered-Learn strategy
# --------------------------------------------------------------------------

class _LearnParser(HTMLParser):
    """Pull headings and tables out of a rendered Learn article."""

    SKIP = {"script", "style", "nav", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.doc = Doc(key="", url="")
        self.current = Section(heading="(intro)", level=0)
        self.doc.sections.append(self.current)
        self._skip = 0
        self._in_heading = 0
        self._heading: list[str] = []
        self._table: Table | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
            return
        if self._skip:
            return
        if tag in ("h1", "h2", "h3", "h4"):
            self._in_heading = int(tag[1])
            self._heading = []
        elif tag == "table":
            self._table = Table()
            self.current.tables.append(self._table)
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag in ("h1", "h2", "h3", "h4") and self._in_heading:
            self.current.text = " ".join(self._text).strip()
            self._text = []
            self.current = Section(heading=" ".join(self._heading).strip(),
                                   level=self._in_heading)
            self.doc.sections.append(self.current)
            self._in_heading = 0
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._table is not None and self._row:
                self._table.rows.append(self._row)
            self._row = None
        elif tag == "table":
            self._table = None

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_heading:
            self._heading.append(data)
        elif self._cell is not None:
            self._cell.append(data)
        else:
            self._text.append(data)


def parse_learn_html(payload: str) -> Doc:
    p = _LearnParser()
    p.feed(htmllib.unescape(payload) if "&lt;table" in payload else payload)
    return p.doc
