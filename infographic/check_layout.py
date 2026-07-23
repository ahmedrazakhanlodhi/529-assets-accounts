#!/usr/bin/env python3
"""
Layout check for the infographic.

Renders a spread of editions and asserts, by measuring real bounding boxes in
the browser rather than by eye, that:

  * no text sits outside its chart's viewBox
  * no axis label is covered by a bar
  * no axis label runs into the hero block
  * the page is exactly 1056px and the footer fits inside it
  * the delta badge in the average-account panel clears both values, which
    matters because its width changes with the number (+14% vs +158%)

Every one of these caught a real bug that a single hand-authored data file
never triggered, so run it after touching the template or the chart geometry.

    python infographic/check_layout.py
"""

from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from infographic import render as R  # noqa: E402

EDITIONS = ["2026Q1", "2025Q4", "2024Q4", "2023Q1", "2022Q4",
            "2021Q4", "2019Q4", "2015Q4", "2013Q4"]

PROBE = """() => {
  const bad = [];
  document.querySelectorAll('svg.chart').forEach(svg => {
    const vb = svg.viewBox.baseVal.width;
    const bars = [...svg.querySelectorAll('rect.bar')].map(b => b.getBBox());
    const hero = svg.querySelector('text.hero');
    const heroBox = hero ? hero.getBBox() : null;
    svg.querySelectorAll('text').forEach(t => {
      const b = t.getBBox();
      if (b.x < -0.5 || b.x + b.width > vb + 0.5)
        bad.push('outside viewBox: ' + t.textContent);
      if (t.classList.contains('gridlab')) {
        bars.forEach(bb => {
          if (b.x < bb.x + bb.width && b.x + b.width > bb.x)
            bad.push('hidden behind a bar: ' + t.textContent);
        });
        if (heroBox && b.x + b.width > heroBox.x)
          bad.push('runs into the hero: ' + t.textContent);
      }
    });
  });
  return [...new Set(bad)];
}"""


PANEL_PROBE = """() => {
  const bad = [];
  const q = s => document.querySelector(s);
  const fv = q('.avg-col.from .v'), tv = q('.avg-col.to .v');
  const badge = q('.avg-arrow span');
  if (fv && tv && badge) {
    const f = fv.getBoundingClientRect(), t = tv.getBoundingClientRect();
    const b = badge.getBoundingClientRect();
    if (b.left < f.right) bad.push('delta badge overlaps the from value');
    if (t.left < b.right) bad.push('delta badge overlaps the to value');
  }
  document.querySelectorAll('.panel, .panel-title, .cta-title, .avg-flow')
    .forEach(e => { if (e.scrollWidth > e.clientWidth + 1)
      bad.push('overflows horizontally: ' + e.className); });
  return bad;
}"""


def load_frame(csv="data/529_data.csv"):
    root = pathlib.Path(__file__).resolve().parent.parent
    d = pd.read_csv(root / csv).rename(columns={
        "State": "state", "PlanName": "plan",
        "Accounts": "accounts", "AUM": "assets"})
    d["quarter"] = d["Year"].astype(str) + d["Period"]
    d["period"] = pd.PeriodIndex(d["quarter"], freq="Q")
    return d[d["assets"].notna()]


def main() -> int:
    from playwright.sync_api import sync_playwright

    df = load_frame()
    tmp = pathlib.Path(tempfile.mkdtemp())
    work = tmp / "pkg"
    shutil.copytree(R.ROOT, work, ignore=shutil.ignore_patterns("__pycache__"))
    failures = 0
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page(viewport={"width": 816, "height": 1056})
            for label in EDITIONS:
                spec = R.derive_spec(df, pd.Period(label, freq="Q"))
                page = work / "p.html"
                page.write_text(R.build_html(spec))
                pg.goto(page.as_uri() + f"?v={label}")
                pg.wait_for_timeout(220)

                bad = pg.evaluate(PROBE)
                bad += pg.evaluate(PANEL_PROBE)
                height = pg.evaluate("document.querySelector('.page').scrollHeight")
                clear = pg.evaluate(
                    "() => {const p=document.querySelector('.page')"
                    ".getBoundingClientRect();"
                    "const f=document.querySelector('.foot')"
                    ".getBoundingClientRect();"
                    "return +(p.bottom-f.bottom).toFixed(1);}")

                ok = not bad and height == 1056 and clear >= 0
                failures += 0 if ok else 1
                status = "ok" if ok else "FAIL"
                print(f"{label}: page={height}px footer_clear={clear}px  {status}")
                for b in bad:
                    print(f"    {b}")
            br.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{len(EDITIONS) - failures}/{len(EDITIONS)} editions clean")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
