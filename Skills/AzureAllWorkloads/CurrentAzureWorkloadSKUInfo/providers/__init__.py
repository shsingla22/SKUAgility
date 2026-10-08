"""Provider registry, driven by references/config.json.

Which services get built is a configuration choice, not a code change: the
config file lists every implemented service with an `enabled` flag, and a run
can override it with `--services`.

Adding a service that is not listed at all is three edits — a source in
references/sources.json, milestones in references/milestones.py, and a provider
module here — then an entry in config.json.
"""

from __future__ import annotations

import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(os.path.dirname(HERE), "references", "config.json")

sys.path.insert(0, HERE)


def load_config() -> list[dict]:
    with open(CONFIG, encoding="utf-8") as fh:
        return json.load(fh)["services"]


def known_keys() -> list[str]:
    return [s["key"] for s in load_config()]


def selected(services: str | None = None) -> list[dict]:
    """Resolve the service list for this run.

    `services` is the --services override: a comma-separated list of keys, or
    "all". When absent, the enabled flags in config.json decide.
    """
    config = load_config()
    by_key = {s["key"]: s for s in config}

    if services:
        wanted = [s.strip() for s in services.split(",") if s.strip()]
        if wanted == ["all"]:
            chosen = list(config)
        else:
            unknown = [w for w in wanted if w not in by_key]
            if unknown:
                raise SystemExit(
                    f"unknown service(s): {', '.join(unknown)}\n"
                    f"known services: {', '.join(by_key)}\n"
                    "Add one to references/config.json, or check the spelling.")
            chosen = [by_key[w] for w in wanted]
    else:
        chosen = [s for s in config if s.get("enabled")]

    if not chosen:
        raise SystemExit(
            "no services selected. Enable at least one in references/config.json "
            "or pass --services.")
    return chosen


def providers_for(services: str | None = None) -> list:
    """Imported provider modules for the selected services, in config order."""
    mods = []
    for svc in selected(services):
        module = importlib.import_module(svc["provider"])
        module.DISPLAY = svc["display"]
        mods.append(module)
    return mods


def applied_errata(modules: list) -> list[dict]:
    """Corrections the given providers made to typos in the source docs."""
    out = []
    for p in modules:
        out += list(getattr(p, "APPLIED_ERRATA", []))
    return out
