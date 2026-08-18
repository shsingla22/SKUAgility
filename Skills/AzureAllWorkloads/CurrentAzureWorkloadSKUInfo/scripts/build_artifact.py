#!/usr/bin/env python3
"""Render the catalog as the Azure Workload SKU Atlas — a self-contained HTML page.

Reads the azure-workload-skus.json produced by build_catalog.py and writes
azure-workload-skus.html into the same directory. The page is filterable by service,
lifecycle status, hardware and tier, and every row expands to its recommendation
conditions and sources. No external requests: a strict CSP would block them, so
all CSS and JS are inline and there are no webfonts.

    python3 scripts/build_artifact.py [--out-dir DIR]

Guidance text is deduplicated into a lookup table keyed by its own content, so
the rows stay small even though each carries a full numbered condition list.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    "doc-changes-updates-release-notes-whats-new-archive": "What\'s new archive",
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


def build(out_dir: str) -> None:
    src_path = os.path.join(out_dir, "azure-workload-skus.json")
    with open(src_path, encoding="utf-8") as fh:
        src = json.load(fh)

    guidance: dict[str, dict] = {}
    rows = []
    for s in src["skus"]:
        key = hashlib.sha1(
            "\n".join(s["recommend_when"]).encode("utf-8")).hexdigest()[:10]
        if key not in guidance:
            guidance[key] = {
                "when": s["recommend_when"],
                "src": [[u, label_for(u)] for u in s["recommend_sources"]],
            }
        rows.append({
            "n": s["sku"],
            "svc": s["service"],
            "t": s["tier"],
            "hw": s["series"],
            "c": s["capacity"],
            "cu": s["capacity_unit"],
            "m": s["memory_gb"],
            "d": s["release_date"],
            "cf": s["date_confidence"],
            "ls": s["lifecycle_status"],
            "idoc": [s["inventory_doc"], label_for(s["inventory_doc"])],
            "rdoc": [s["release_doc"], label_for(s["release_doc"])],
            "g": key,
            "ms": s["milestone_label"],
        })

    payload = json.dumps(
        {"rows": rows, "guidance": guidance, "asOf": src["generated"]},
        separators=(",", ":"))

    html = TEMPLATE.replace("__DATA__", payload)
    out = os.path.join(out_dir, "azure-workload-skus.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {out} ({len(html) / 1024:.0f} KB, {len(rows)} rows, "
          f"{len(guidance)} guidance sets)")


TEMPLATE = r"""<title>Azure Workload SKU Atlas</title>
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
    <h1>Azure Workload SKU Atlas</h1>
    <p class="sub">
      Compute SKUs across Azure&rsquo;s major workload services — databases, caching, web,
      Kubernetes and virtual machines — with the release that made each one orderable, its
      lifecycle state, and the conditions for recommending it. Open any row for the
      guidance and its sources. Every fact traces to Microsoft documentation.
    </p>
    <div class="stats">
      <div class="stat"><b id="st-total">—</b><span>SKUs documented</span></div>
      <div class="stat"><b id="st-svc">—</b><span>Services covered</span></div>
      <div class="stat is-ga"><b id="st-ga">—</b><span>Generally available</span></div>
      <div class="stat is-dep"><b id="st-dep">—</b><span>Deprecated / retiring</span></div>
      <div class="stat is-prev"><b id="st-prev">—</b><span>Public preview</span></div>
      <div class="stat"><b id="st-span">—</b><span>Dates not sourced</span></div>
    </div>
  </div>
</header>

<div class="controls">
  <div class="controls-in">
    <input id="q" class="search" type="search" placeholder="Search SKU, tier, or hardware…"
           aria-label="Search SKUs">
    <div class="group" id="f-ls" data-facet="ls"><span class="group-label">Status</span></div>
    <button class="theme" id="theme" type="button">Theme</button>
  </div>
</div>

<div class="wrap">
  <div class="group" id="f-svc" data-facet="svc" style="padding-top:16px">
    <span class="group-label">Service</span>
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
          <th>Tier</th>
          <th>Series / family</th>
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
      Azure announces SKUs by family or tier, not per size, so a size inherits its
      family&rsquo;s date unless it was added later. Confidence marks how firmly each date is
      sourced: <strong>low</strong> means reconstructed from context, and
      <strong>unknown</strong> means no date could be sourced at all &mdash; those rows read
      <em>not established</em> rather than carrying a guess. Availability is
      region-dependent; this catalog records what each service offers, not what a given
      region can allocate today.
    </p>
    <p>
      Virtual Machines are recorded at size-family level: Azure documents roughly 800
      individual sizes across more than a hundred pages, and the authoritative per-size
      list is the Resource SKUs API rather than the documentation. Azure SQL is produced by
      the CurrentAzureSQLSKUInfo skill and adopted here rather than re-derived.
    </p>
  </footer>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  var D = JSON.parse(document.getElementById('data').textContent);
  var rows = D.rows, G = D.guidance;
  var tbody = document.getElementById('tbody');
  var empty = document.getElementById('empty');
  var countEl = document.getElementById('count');
  document.getElementById('asof').textContent = D.asOf;

  function statusClass(ls) {
    if (ls.indexOf('preview') > -1) return 'prev';
    if (ls.indexOf('Deprecated') > -1 || ls.indexOf('Retiring') > -1) return 'dep';
    return 'ga';
  }
  function shortStatus(ls) {
    if (ls.indexOf('preview') > -1) return 'Preview';
    if (ls.indexOf('Retiring') > -1) return 'Retiring';
    if (ls.indexOf('Deprecated') > -1) return 'Deprecated';
    return 'GA';
  }

  // ---- stat strip
  var n = { ga: 0, prev: 0, dep: 0 };
  var services = {}, unsourced = 0;
  rows.forEach(function (r) {
    n[statusClass(r.ls)]++;
    services[r.svc] = 1;
    if (r.cf === 'unknown') unsourced++;
  });
  document.getElementById('st-total').textContent = rows.length;
  document.getElementById('st-ga').textContent = n.ga;
  document.getElementById('st-dep').textContent = n.dep;
  document.getElementById('st-prev').textContent = n.prev;
  document.getElementById('st-svc').textContent = Object.keys(services).length;
  document.getElementById('st-span').textContent = unsourced;

  // ---- facets
  var state = { q: '', svc: null, ls: null, t: null };

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
  buildFacet('f-ls', 'ls');
  buildFacet('f-svc', 'svc');
  buildFacet('f-t', 't');

  document.getElementById('q').addEventListener('input', function (e) {
    state.q = e.target.value.toLowerCase().trim();
    render();
  });

  function matches(r) {
    if (state.svc && r.svc !== state.svc) return false;
    if (state.ls && shortStatus(r.ls) !== state.ls) return false;
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
    right.appendChild(el('p', 'milestone', r.ms));
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

      tr.appendChild(el('td', 'tier', r.t));
      tr.appendChild(el('td', 'hw', r.hw === 'n/a (DTU model)' ? '—' : r.hw));

      var size = r.c == null ? '—'
        : r.c + ' ' + r.cu + (r.m != null ? ' · ' + r.m + ' GB' : '');
      tr.appendChild(el('td', 'num', size));

      tr.appendChild(el('td', 'num date', r.d));
      var cf = el('td', 'cf' + (r.cf === 'low' || r.cf === 'unknown' ? ' low' : ''), r.cf);
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(HERE, "output"))
    build(ap.parse_args().out_dir)
