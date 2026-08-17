#!/usr/bin/env python3
"""Render the Azure SQL catalog as a self-contained, filterable HTML page.

Reads data/azure-sql.json (produced by build_catalog.py) and writes
docs/azure-sql-skus.html. Guidance text is deduplicated into a lookup table
keyed by guidance key, so the 304 rows stay small.

Run with:  python3 tools/build_artifact.py
"""

from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "azure-sql.json")
OUT = os.path.join(ROOT, "docs", "azure-sql-skus.html")

SHORT_DOC = {
    "resource-limits-vcore-single-databases": "vCore resource limits",
    "resource-limits-dtu-single-databases": "DTU resource limits",
    "resource-limits-dtu-elastic-pools": "DTU elastic pool limits",
    "resource-limits": "Managed Instance resource limits",
    "service-tiers-sql-database-vcore": "vCore purchasing model",
    "service-tiers-managed-instance-vcore": "MI vCore purchasing model",
    "service-tiers-next-gen-general-purpose-use": "Next-gen General Purpose",
    "service-tiers-dtu": "DTU purchasing model",
    "purchasing-models": "Compare purchasing models",
    "serverless-tier-overview": "Serverless compute tier",
    "service-tier-hyperscale": "Hyperscale service tier",
    "elastic-pool-overview": "Elastic pools overview",
    "doc-changes-updates-release-notes-whats-new-archive": "What's new archive",
    "sql-managed-instance-paas-overview": "Managed Instance overview",
}


def label_for(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1].split("?")[0]
    if tail in SHORT_DOC:
        return SHORT_DOC[tail]
    if "aka.ms" in url:
        return "Announcement"
    if "azure.microsoft.com/updates" in url:
        return "Azure update"
    if "azure.microsoft.com" in url and "/blog/" in url:
        return "Azure blog"
    if "techcommunity" in url:
        return "Tech Community"
    return "Microsoft Learn"


def build() -> None:
    src = json.load(open(SRC, encoding="utf-8"))
    skus = src["skus"]

    guidance: dict[str, dict] = {}
    rows = []
    for s in skus:
        key = s["guidance_key"]
        if key not in guidance:
            guidance[key] = {
                "when": s["recommend_when"],
                "src": [[u, label_for(u)] for u in s["recommend_sources"]],
            }
        rows.append({
            "n": s["sku"],
            "svc": "SQL DB" if s["service"].endswith("Database") else "SQL MI",
            "dep": s["deployment_model"],
            "pm": s["purchasing_model"],
            "t": s["service_tier"],
            "ct": s["compute_tier"],
            "hw": s["hardware"],
            "c": s["capacity"],
            "cu": s["capacity_unit"],
            "m": s["memory_gb"],
            "d": s["release_date"],
            "cf": s["date_confidence"],
            "ls": s["lifecycle_status"],
            "idoc": [s["inventory_doc"], label_for(s["inventory_doc"])],
            "rdoc": [s["release_doc"], label_for(s["release_doc"])],
            "g": key,
            "ms": s["milestone"],
        })

    milestones = {m["key"]: m["label"] for m in src["release_milestones"]}

    payload = json.dumps(
        {"rows": rows, "guidance": guidance, "milestones": milestones,
         "asOf": src["catalog_as_of"]},
        separators=(",", ":"),
    )

    html = TEMPLATE.replace("__DATA__", payload).replace("__COUNT__", str(len(rows)))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {OUT} ({len(html) / 1024:.0f} KB, {len(rows)} rows, "
          f"{len(guidance)} guidance sets)")


TEMPLATE = r"""<title>Azure SQL SKU Atlas</title>
<style>
  /* ---- tokens: light is the base, both themes redefine only these ---- */
  :root {
    --ground:    #f2f5f6;
    --surface:   #ffffff;
    --surface-2: #e9eef0;
    --ink:       #0e1519;
    --ink-2:     #56666f;
    --ink-3:     #7d8f99;
    --line:      #d7e0e4;
    --line-2:    #eaf0f2;
    --accent:    #0d6b76;
    --accent-2:  #0a545d;
    --on-accent: #ffffff;
    --ga:        #1c7548;
    --ga-bg:     #e2f1e8;
    --prev:      #8a5a09;
    --prev-bg:   #f8eed8;
    --dep:       #a33a26;
    --dep-bg:    #f8e5e0;
    --shadow:    0 1px 2px rgba(14,21,25,.06), 0 8px 24px -16px rgba(14,21,25,.28);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --ground:    #0b1216;
      --surface:   #111b20;
      --surface-2: #17242b;
      --ink:       #e4ecef;
      --ink-2:     #93a5ae;
      --ink-3:     #6d818b;
      --line:      #22323a;
      --line-2:    #1a272e;
      --accent:    #56c2cd;
      --accent-2:  #7fd6de;
      --on-accent: #07161a;
      --ga:        #57b483;
      --ga-bg:     #14301f;
      --prev:      #d8a84e;
      --prev-bg:   #33270e;
      --dep:       #e08b76;
      --dep-bg:    #351c15;
      --shadow:    0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);
    }
  }
  :root[data-theme="dark"] {
    --ground:    #0b1216;
    --surface:   #111b20;
    --surface-2: #17242b;
    --ink:       #e4ecef;
    --ink-2:     #93a5ae;
    --ink-3:     #6d818b;
    --line:      #22323a;
    --line-2:    #1a272e;
    --accent:    #56c2cd;
    --accent-2:  #7fd6de;
    --on-accent: #07161a;
    --ga:        #57b483;
    --ga-bg:     #14301f;
    --prev:      #d8a84e;
    --prev-bg:   #33270e;
    --dep:       #e08b76;
    --dep-bg:    #351c15;
    --shadow:    0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    background: var(--ground);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    font-size: 15px;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
  }

  .mono {
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
                 "Liberation Mono", monospace;
    font-variant-numeric: tabular-nums;
  }

  .wrap { max-width: 1360px; margin: 0 auto; padding: 0 24px 96px; }

  /* ---- masthead ---- */
  header { border-bottom: 1px solid var(--line); background: var(--surface); }
  .head-in { max-width: 1360px; margin: 0 auto; padding: 34px 24px 26px; }
  .eyebrow {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 11px; letter-spacing: .16em; text-transform: uppercase;
    color: var(--accent); margin: 0 0 10px;
  }
  h1 {
    margin: 0; font-size: clamp(28px, 4vw, 40px); line-height: 1.08;
    letter-spacing: -.025em; font-weight: 700; text-wrap: balance;
  }
  .sub { margin: 12px 0 0; max-width: 66ch; color: var(--ink-2); font-size: 15.5px; }
  .sub a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }

  /* ---- stat strip ---- */
  .stats { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px; }
  .stat {
    flex: 1 1 150px; background: var(--ground); border: 1px solid var(--line);
    border-radius: 3px; padding: 12px 14px; display: flex; flex-direction: column; gap: 2px;
  }
  .stat b {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 24px; font-weight: 600; letter-spacing: -.02em;
    font-variant-numeric: tabular-nums; line-height: 1.1;
  }
  .stat span {
    font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  .stat.is-ga b { color: var(--ga); }
  .stat.is-prev b { color: var(--prev); }
  .stat.is-dep b { color: var(--dep); }

  /* ---- controls ---- */
  .controls {
    position: sticky; top: 0; z-index: 20; background: var(--surface);
    border-bottom: 1px solid var(--line); padding: 12px 0;
    box-shadow: var(--shadow);
  }
  .controls-in {
    max-width: 1360px; margin: 0 auto; padding: 0 24px;
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  }
  .search {
    flex: 1 1 260px; min-width: 200px; background: var(--ground); color: var(--ink);
    border: 1px solid var(--line); border-radius: 3px; padding: 8px 12px;
    font: inherit; font-size: 14px;
  }
  .search::placeholder { color: var(--ink-3); }
  .search:focus-visible, .chip:focus-visible, .row-btn:focus-visible, .theme:focus-visible {
    outline: 2px solid var(--accent); outline-offset: 2px;
  }
  .group { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .group-label {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 10px; letter-spacing: .14em; text-transform: uppercase;
    color: var(--ink-3); margin-right: 2px;
  }
  .chip {
    background: var(--ground); color: var(--ink-2); border: 1px solid var(--line);
    border-radius: 999px; padding: 5px 12px; font: inherit; font-size: 12.5px;
    cursor: pointer; white-space: nowrap; transition: background .12s, color .12s, border-color .12s;
  }
  .chip:hover { border-color: var(--accent); color: var(--ink); }
  .chip[aria-pressed="true"] {
    background: var(--accent); border-color: var(--accent); color: var(--on-accent);
    font-weight: 600;
  }
  .theme {
    margin-left: auto; background: var(--ground); color: var(--ink-2);
    border: 1px solid var(--line); border-radius: 3px; padding: 6px 12px;
    font: inherit; font-size: 12.5px; cursor: pointer;
  }

  .count {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px; color: var(--ink-3); padding: 16px 0 8px;
    letter-spacing: .04em;
  }

  /* ---- table ---- */
  .tablewrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 4px;
               background: var(--surface); }
  table { border-collapse: collapse; width: 100%; min-width: 900px; }
  thead th {
    position: sticky; top: 0; z-index: 5; background: var(--surface-2);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 10.5px; letter-spacing: .12em; text-transform: uppercase;
    color: var(--ink-2); text-align: left; padding: 10px 12px;
    border-bottom: 1px solid var(--line); white-space: nowrap; font-weight: 600;
  }
  tbody tr.sku { border-top: 1px solid var(--line-2); }
  tbody tr.sku:first-child { border-top: 0; }
  tbody tr.sku:hover { background: var(--surface-2); }
  td { padding: 9px 12px; vertical-align: top; }
  td.stripe { padding: 0; width: 3px; }
  td.stripe i { display: block; width: 3px; height: 100%; min-height: 34px; }
  .s-ga i    { background: var(--ga); }
  .s-prev i  { background: var(--prev); }
  .s-dep i   { background: var(--dep); }

  .row-btn {
    background: none; border: 0; padding: 0; font: inherit; cursor: pointer;
    color: var(--ink); text-align: left;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 13px; font-weight: 600; letter-spacing: -.01em;
    display: inline-flex; align-items: baseline; gap: 7px;
  }
  .row-btn:hover { color: var(--accent); }
  .caret { color: var(--ink-3); font-size: 9px; transition: transform .15s; }
  tr.sku[data-open="1"] .caret { transform: rotate(90deg); }
  .tier { font-size: 13.5px; }
  .hw, .dim { color: var(--ink-2); font-size: 13px; }
  .num {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12.5px; font-variant-numeric: tabular-nums; white-space: nowrap;
  }
  .date { font-weight: 600; }
  .cf { font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-3); }
  .cf.low { color: var(--dep); }

  .pill {
    display: inline-block; border-radius: 3px; padding: 2px 8px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 10.5px; letter-spacing: .06em; text-transform: uppercase;
    font-weight: 600; white-space: nowrap;
  }
  .p-ga   { background: var(--ga-bg);   color: var(--ga); }
  .p-prev { background: var(--prev-bg); color: var(--prev); }
  .p-dep  { background: var(--dep-bg);  color: var(--dep); }

  a.doc {
    color: var(--accent); font-size: 12.5px; text-decoration: none;
    border-bottom: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
  }
  a.doc:hover { color: var(--accent-2); border-bottom-color: var(--accent-2); }

  /* ---- expanded guidance ---- */
  tr.detail > td { background: var(--surface-2); padding: 0 12px 20px 18px; }
  .detail-in { display: grid; grid-template-columns: minmax(0,1fr) 260px; gap: 28px;
               padding-top: 4px; max-width: 1180px; }
  @media (max-width: 860px) { .detail-in { grid-template-columns: 1fr; } }
  .detail h4 {
    margin: 14px 0 8px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 10.5px; letter-spacing: .13em; text-transform: uppercase; color: var(--ink-3);
    font-weight: 600;
  }
  ol.when { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 7px; }
  ol.when li { font-size: 14px; line-height: 1.5; max-width: 74ch; }
  ol.when li::marker { color: var(--accent); font-variant-numeric: tabular-nums; }
  ul.srcs { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; }
  .milestone { font-size: 13px; color: var(--ink-2); }

  .empty { padding: 48px 12px; text-align: center; color: var(--ink-3); }

  footer {
    border-top: 1px solid var(--line); margin-top: 48px; padding-top: 20px;
    color: var(--ink-3); font-size: 13px; max-width: 74ch;
  }
  footer a { color: var(--accent); }

  @media (prefers-reduced-motion: reduce) {
    * { transition: none !important; animation: none !important; }
  }
</style>

<header>
  <div class="head-in">
    <p class="eyebrow">SKUAgility · catalog <span id="asof"></span></p>
    <h1>Azure SQL SKU Atlas</h1>
    <p class="sub">
      Every Azure SQL Database and Azure SQL Managed Instance SKU Microsoft currently
      documents — with the release that made it orderable, its lifecycle state, and the
      conditions for recommending it. Open any row for the guidance and its sources.
      Every fact traces to a Microsoft Learn page or a dated Microsoft announcement.
    </p>
    <div class="stats">
      <div class="stat"><b id="st-total">—</b><span>SKUs documented</span></div>
      <div class="stat is-ga"><b id="st-ga">—</b><span>Generally available</span></div>
      <div class="stat is-dep"><b id="st-dep">—</b><span>Deprecated</span></div>
      <div class="stat is-prev"><b id="st-prev">—</b><span>Public preview</span></div>
      <div class="stat"><b id="st-span">—</b><span>Release span</span></div>
    </div>
  </div>
</header>

<div class="controls">
  <div class="controls-in">
    <input id="q" class="search" type="search" placeholder="Search SKU, tier, or hardware…"
           aria-label="Search SKUs">
    <div class="group" id="f-svc" data-facet="svc"><span class="group-label">Service</span></div>
    <div class="group" id="f-ls" data-facet="ls"><span class="group-label">Status</span></div>
    <button class="theme" id="theme" type="button">Theme</button>
  </div>
</div>

<div class="wrap">
  <div class="group" id="f-hw" data-facet="hw" style="padding-top:16px">
    <span class="group-label">Hardware</span>
  </div>
  <div class="group" id="f-t" data-facet="t" style="padding-top:8px">
    <span class="group-label">Tier</span>
  </div>

  <p class="count" id="count"></p>

  <div class="tablewrap">
    <table>
      <thead>
        <tr>
          <th></th>
          <th>SKU</th>
          <th>Service</th>
          <th>Service tier</th>
          <th>Hardware</th>
          <th>Size</th>
          <th>Released</th>
          <th>Conf.</th>
          <th>Lifecycle</th>
          <th>SKU source</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
  <div class="empty" id="empty" hidden>No SKU matches those filters.</div>

  <footer>
    <p>
      Release dates are published by Microsoft per SKU <em>family</em>, not per size, so a
      size added after its family carries its own date. Confidence marks how firmly each
      date is sourced — <strong>low</strong> means reconstructed from context, mostly
      pre-2019 history whose announcement posts are no longer dated. Memory figures are
      Availability
      is region-dependent; this catalog records what the service offers, not what a given
      region can allocate today. Azure SQL Database memory is transcribed from the published
      resource-limit tables; Managed Instance memory is derived from the documented
      per-vCore ratio with published caps applied.
    </p>
    <p>
      Gen4 and M-series hardware are fully retired and no longer enumerable from Microsoft
      docs, so they are not listed as rows here.
    </p>
  </footer>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  var D = JSON.parse(document.getElementById('data').textContent);
  var rows = D.rows, G = D.guidance, MS = D.milestones;
  var tbody = document.getElementById('tbody');
  var empty = document.getElementById('empty');
  var countEl = document.getElementById('count');
  document.getElementById('asof').textContent = D.asOf;

  function statusClass(ls) {
    if (ls.indexOf('preview') > -1) return 'prev';
    if (ls.indexOf('Deprecated') > -1) return 'dep';
    return 'ga';
  }
  function shortStatus(ls) {
    if (ls.indexOf('preview') > -1) return 'Preview';
    if (ls.indexOf('Deprecated') > -1) return 'Deprecated';
    return 'GA';
  }

  // ---- stat strip
  var n = { ga: 0, prev: 0, dep: 0 };
  var years = [];
  rows.forEach(function (r) {
    n[statusClass(r.ls)]++;
    var y = parseInt(r.d.slice(0, 4), 10);
    if (!isNaN(y)) years.push(y);
  });
  document.getElementById('st-total').textContent = rows.length;
  document.getElementById('st-ga').textContent = n.ga;
  document.getElementById('st-dep').textContent = n.dep;
  document.getElementById('st-prev').textContent = n.prev;
  document.getElementById('st-span').textContent =
    Math.min.apply(null, years) + '–' + Math.max.apply(null, years);

  // ---- facets
  var state = { q: '', svc: null, ls: null, hw: null, t: null };

  function uniq(key) {
    var seen = [];
    rows.forEach(function (r) {
      var v = key === 'ls' ? shortStatus(r.ls) : r[key];
      if (seen.indexOf(v) === -1) seen.push(v);
    });
    return seen;
  }

  function buildFacet(id, key) {
    var host = document.getElementById(id);
    uniq(key).forEach(function (v) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip';
      b.textContent = v;
      b.setAttribute('aria-pressed', 'false');
      b.addEventListener('click', function () {
        state[key] = state[key] === v ? null : v;
        Array.prototype.forEach.call(host.querySelectorAll('.chip'), function (c) {
          c.setAttribute('aria-pressed', String(c.textContent === state[key]));
        });
        render();
      });
      host.appendChild(b);
    });
  }
  buildFacet('f-svc', 'svc');
  buildFacet('f-ls', 'ls');
  buildFacet('f-hw', 'hw');
  buildFacet('f-t', 't');

  document.getElementById('q').addEventListener('input', function (e) {
    state.q = e.target.value.toLowerCase().trim();
    render();
  });

  function matches(r) {
    if (state.svc && r.svc !== state.svc) return false;
    if (state.ls && shortStatus(r.ls) !== state.ls) return false;
    if (state.hw && r.hw !== state.hw) return false;
    if (state.t && r.t !== state.t) return false;
    if (state.q) {
      var hay = (r.n + ' ' + r.t + ' ' + r.hw + ' ' + r.ct + ' ' + r.dep + ' ' +
                 r.ls + ' ' + r.d).toLowerCase();
      if (hay.indexOf(state.q) === -1) return false;
    }
    return true;
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function docLink(pair) {
    var a = el('a', 'doc', pair[1]);
    a.href = pair[0];
    a.target = '_blank';
    a.rel = 'noopener';
    return a;
  }

  function detailRow(r) {
    var tr = el('tr', 'detail');
    var td = document.createElement('td');
    td.colSpan = 10;
    var box = el('div', 'detail-in');

    var left = el('div', 'detail');
    left.appendChild(el('h4', null, 'When to recommend ' + r.n));
    var ol = el('ol', 'when');
    G[r.g].when.forEach(function (t) { ol.appendChild(el('li', null, t)); });
    left.appendChild(ol);

    var right = el('div', 'detail');
    right.appendChild(el('h4', null, 'Recommendation sources'));
    var ul = el('ul', 'srcs');
    G[r.g].src.forEach(function (p) {
      var li = document.createElement('li');
      li.appendChild(docLink(p));
      ul.appendChild(li);
    });
    right.appendChild(ul);

    right.appendChild(el('h4', null, 'Release milestone'));
    right.appendChild(el('p', 'milestone', MS[r.ms] || r.ms));
    var ul2 = el('ul', 'srcs');
    var li2 = document.createElement('li');
    li2.appendChild(docLink(r.rdoc));
    ul2.appendChild(li2);
    right.appendChild(ul2);

    box.appendChild(left);
    box.appendChild(right);
    td.appendChild(box);
    tr.appendChild(td);
    return tr;
  }

  function render() {
    var list = rows.filter(matches);
    tbody.textContent = '';
    empty.hidden = list.length > 0;
    countEl.textContent = list.length === rows.length
      ? 'Showing all ' + rows.length + ' SKUs'
      : 'Showing ' + list.length + ' of ' + rows.length + ' SKUs';

    var frag = document.createDocumentFragment();
    list.forEach(function (r) {
      var sc = statusClass(r.ls);
      var tr = el('tr', 'sku s-' + sc);

      var tdS = el('td', 'stripe');
      tdS.appendChild(document.createElement('i'));
      tr.appendChild(tdS);

      var tdN = document.createElement('td');
      var btn = el('button', 'row-btn');
      btn.type = 'button';
      btn.appendChild(el('span', 'caret', '▶'));
      btn.appendChild(el('span', null, r.n));
      tdN.appendChild(btn);
      tr.appendChild(tdN);

      tr.appendChild(el('td', 'dim', r.svc));

      var tier = r.t + (r.ct === 'Provisioned' ? '' : ' · ' + r.ct);
      tr.appendChild(el('td', 'tier', tier));
      tr.appendChild(el('td', 'hw', r.hw === 'n/a (DTU model)' ? '—' : r.hw));

      var size = r.c + ' ' + r.cu + (r.m != null ? ' · ' + r.m + ' GB' : '');
      tr.appendChild(el('td', 'num', size));

      tr.appendChild(el('td', 'num date', r.d));
      var cf = el('td', 'cf' + (r.cf === 'low' ? ' low' : ''), r.cf);
      tr.appendChild(cf);

      var tdL = document.createElement('td');
      var pill = el('span', 'pill p-' + sc, shortStatus(r.ls));
      pill.title = r.ls;
      tdL.appendChild(pill);
      tr.appendChild(tdL);

      var tdD = document.createElement('td');
      tdD.appendChild(docLink(r.idoc));
      tr.appendChild(tdD);

      var det = null;
      btn.addEventListener('click', function () {
        if (tr.getAttribute('data-open') === '1') {
          tr.removeAttribute('data-open');
          if (det) { det.remove(); det = null; }
        } else {
          tr.setAttribute('data-open', '1');
          det = detailRow(r);
          tr.parentNode.insertBefore(det, tr.nextSibling);
        }
      });

      frag.appendChild(tr);
    });
    tbody.appendChild(frag);
  }

  // ---- theme toggle
  var order = ['', 'light', 'dark'];
  var ti = 0;
  document.getElementById('theme').addEventListener('click', function () {
    ti = (ti + 1) % 3;
    if (order[ti]) document.documentElement.setAttribute('data-theme', order[ti]);
    else document.documentElement.removeAttribute('data-theme');
    this.textContent = order[ti] ? 'Theme: ' + order[ti] : 'Theme: system';
  });

  render();
})();
</script>
"""


if __name__ == "__main__":
    build()
