"""
Infographic generator, wired to the live record.

Two halves:

  derive_spec(df, year)  builds the data spec straight out of the master
                         dataframe, so the infographic can never disagree with
                         the dashboard it sits inside.

  render(spec)           renders that spec to a print-ready PDF and a PNG.

The chart drawing functions are the originals from the delivered generator,
kept as they were so the output matches the published Q4 2025 graphic. Only the
data plumbing changed: the spec is derived rather than hand-entered in JSON.

Average balance is never entered. It is assets divided by accounts, and it is
labelled as derived wherever it appears.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

import qrcode
from jinja2 import Template

ROOT = pathlib.Path(__file__).parent
ASSETS = ROOT / "assets"

PLOT_X0, PLOT_X1 = 34, 420
HERO_X = 452
GRIDLAB_DX = 13      # left axis labels sit clear of the first bar
RGRIDLAB_DX = 12     # clears the last bar, which is centred on PLOT_X1
                     # and so reaches PLOT_X1 + bw/2


def x_for(i, n):
    return PLOT_X0 + i * (PLOT_X1 - PLOT_X0) / (n - 1)


# ─────────────────────────── charts (unchanged) ───────────────────────────

def nice_ceiling(v, step):
    """Round up to a clean multiple of step, leaving a little headroom."""
    import math
    return max(step, math.ceil(v * 1.06 / step) * step)


def area_chart(cfg, as_of_short, label_years):
    pts = cfg["series"]
    n = len(pts)
    y0, y1 = 250.0, 40.0
    # 640 keeps the published look while the series fits under it. Beyond
    # that the axis grows in clean 200s so a future edition cannot overflow.
    peak = max(p["value"] for p in pts)
    ymax = 640.0 if peak <= 604 else float(nice_ceiling(peak, 200))
    ann = {a["year"] for a in cfg["annotations"]}

    def y_for(v):
        return y0 - (v / ymax) * (y0 - y1)

    co = [(x_for(i, n), y_for(p["value"])) for i, p in enumerate(pts)]
    line = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(co))
    area = f"{line} L{co[-1][0]:.1f},{y0} L{co[0][0]:.1f},{y0} Z"

    o = []
    for gv in range(200, int(ymax) + 1, 200):
        gy = y_for(gv)
        o.append(f'<line x1="{PLOT_X0}" y1="{gy:.1f}" x2="{PLOT_X1}" y2="{gy:.1f}" class="grid"/>'
                 f'<text x="{PLOT_X0 - GRIDLAB_DX}" y="{gy + 2.6:.1f}" class="gridlab">{gv}</text>')

    o.append(f'<path d="{area}" fill="url(#leafgrad)"/>')
    o.append(f'<path d="{line}" class="curve"/>')

    for i, p in enumerate(pts):
        if p["year"] in ann:
            x, y = co[i]
            o.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y0}" class="drop"/>'
                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.8" class="dropdot"/>')

    # Every point carries its value, matching the published sheet. Annotated
    # years and the endpoint are emphasised; the rest sit back so the shape
    # still reads first.
    for i, p in enumerate(pts):
        x, y = co[i]
        strong = p["year"] in label_years
        o.append(f'<text x="{x:.1f}" y="{y - 8:.1f}" '
                 f'class="vlab{" hi" if strong else ""}">{p["value"]:.0f}</text>')
        o.append(f'<text x="{x_for(i, n):.1f}" y="266" class="ylab">{p["year"]}</text>')

    ex, ey = co[-1]
    o.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4" class="enddot"/>')
    o.append(f'<line x1="{ex + 5:.1f}" y1="{ey:.1f}" x2="{HERO_X - 6}" y2="{ey:.1f}" class="leader"/>')
    o.append(f'<text x="{HERO_X}" y="{ey + 9:.1f}" class="hero">{cfg["hero_label"]}</text>'
             f'<text x="{HERO_X}" y="{ey + 24:.1f}" class="herocap">total assets</text>'
             f'<text x="{HERO_X}" y="{ey + 35:.1f}" class="herocap">{as_of_short}</text>')
    o.append(f'<line x1="{PLOT_X0}" y1="{y0}" x2="{PLOT_X1}" y2="{y0}" class="axis"/>')

    return ('<svg viewBox="0 0 560 278" class="chart">'
            '<defs><linearGradient id="leafgrad" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#3A8916"/>'
            '<stop offset="100%" stop-color="#2B650B"/></linearGradient></defs>'
            + "".join(o) + "</svg>")


# --------------------------------------------------- decomposition chart


def decomposition_chart(acc_cfg, avg_series, as_of_short, avg_hero):
    """
    Accounts as columns against the left axis, average balance as a line against
    the right axis. Together these are the two factors whose product is total
    assets, so this explains the chart above instead of repeating it.
    """
    pts = acc_cfg["series"]
    n = len(pts)
    y0, y1 = 168.0, 26.0
    # Both axes hold their published scale while the data fits, then grow.
    n_peak = max(p["value"] for p in pts)
    a_peak = max(avg_series)
    n_max = 20.0 if n_peak <= 19.0 else float(nice_ceiling(n_peak, 5))
    a_max = 40000.0 if a_peak <= 38000 else float(nice_ceiling(a_peak, 10000))
    bw = 19.0

    def yn(v):
        return y0 - (v / n_max) * (y0 - y1)

    def ya(v):
        return y0 - (v / a_max) * (y0 - y1)

    o = []
    for gv in range(5, int(n_max) + 1, 5):
        gy = yn(gv)
        o.append(f'<line x1="{PLOT_X0}" y1="{gy:.1f}" x2="{PLOT_X1}" y2="{gy:.1f}" class="grid"/>'
                 f'<text x="{PLOT_X0 - GRIDLAB_DX}" y="{gy + 2.6:.1f}" class="gridlab">{gv}</text>')
    for gv in range(10000, int(a_max) + 1, 10000):
        o.append(f'<text x="{PLOT_X1 + RGRIDLAB_DX}" y="{ya(gv) + 2.6:.1f}" class="gridlab r">'
                 f'{gv // 1000}k</text>')

    for i, p in enumerate(pts):
        x, y = x_for(i, n), yn(p["value"])
        last = i == n - 1
        o.append(f'<rect x="{x - bw / 2:.1f}" y="{y:.1f}" width="{bw}" '
                 f'height="{y0 - y:.1f}" class="{"bar last" if last else "bar"}"/>')
        o.append(f'<text x="{x:.1f}" y="{y - 4:.1f}" '
                 f'class="barlab{" hi" if last else ""}">{p["value"]:.1f}</text>')
        o.append(f'<text x="{x:.1f}" y="184" class="ylab">{p["year"]}</text>')

    o.append(f'<text x="0" y="{y1 - 6:.1f}" class="axlab">accounts, M</text>')
    o.append(f'<text x="{PLOT_X1 + RGRIDLAB_DX}" y="{y1 - 6:.1f}" class="axlab r">avg balance</text>')

    path = " ".join(f"{'M' if i == 0 else 'L'}{x_for(i, n):.1f},{ya(v):.1f}"
                    for i, v in enumerate(avg_series))
    o.append(f'<path d="{path}" class="avgline"/>')
    for i, v in enumerate(avg_series):
        o.append(f'<circle cx="{x_for(i, n):.1f}" cy="{ya(v):.1f}" r="1.9" class="avgdot"/>')

    ey = yn(pts[-1]["value"])
    o.append(f'<line x1="{PLOT_X1 + 24}" y1="{ey:.1f}" x2="{HERO_X - 6}" y2="{ey:.1f}" class="leader"/>')
    o.append(f'<text x="{HERO_X}" y="{ey + 8:.1f}" class="hero">{acc_cfg["hero_label"]}</text>'
             f'<text x="{HERO_X}" y="{ey + 22:.1f}" class="herocap">open accounts</text>'
             f'<text x="{HERO_X}" y="{ey + 40:.1f}" class="hero sm">{avg_hero}</text>'
             f'<text x="{HERO_X}" y="{ey + 53:.1f}" class="herocap">average balance</text>'
             f'<text x="{HERO_X}" y="{ey + 64:.1f}" class="herocap">{as_of_short}</text>')
    o.append(f'<line x1="{PLOT_X0}" y1="{y0}" x2="{PLOT_X1}" y2="{y0}" class="axis"/>')

    return '<svg viewBox="0 0 560 196" class="chart">' + "".join(o) + "</svg>"


# ---------------------------------------------------------------------- QR


def qr_svg(url):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                      box_size=1, border=0)
    q.add_data(url)
    q.make(fit=True)
    m = q.get_matrix()
    size = len(m)
    rects = "".join(f'<rect x="{c}" y="{r}" width="1" height="1"/>'
                    for r, row in enumerate(m) for c, v in enumerate(row) if v)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
            f'shape-rendering="crispEdges"><g fill="currentColor">{rects}</g></svg>')


# ─────────────────────── derive the spec from the record ───────────────────
MONTH = {1: "March 31", 2: "June 30", 3: "September 30", 4: "December 31"}
SHORT = {1: "Mar 31", 2: "Jun 30", 3: "Sep 30", 4: "Dec 31"}


def derive_spec(df, period, first_year=2012, url="https://529network.org"):
    """Build the infographic spec from the dashboard's own dataframe.

    df      the reporting rows of the master, with columns
            period, Year, Period, assets, accounts, plan
    period  a pandas Period, the edition being published
    """
    q = period.quarter
    year = period.year

    # Annual points use the same quarter as the edition, so a Q2 edition
    # compares against prior Q2s rather than mixing quarter ends.
    ann = (df[df["Period"] == f"Q{q}"]
           .groupby("Year")
           .agg(assets=("assets", "sum"), accounts=("accounts", "sum")))
    ann = ann[(ann.index >= first_year) & (ann.index <= year)]
    ann = ann[ann["accounts"] > 0]

    years = [int(y) for y in ann.index]
    if len(years) < 2:
        raise ValueError(
            f"only {len(years)} matching Q{q} year(s) at or before {year}, "
            f"so there is no series to chart. Pick a later edition or an "
            f"earlier start year.")
    assets_b = [round(v / 1e9, 1) for v in ann["assets"]]
    accounts_m = [round(v / 1e6, 2) for v in ann["accounts"]]
    avg = [a / c for a, c in zip(ann["assets"], ann["accounts"])]

    cur = df[df["period"] == period]
    A = cur["assets"].sum()
    C = cur["accounts"].sum()
    avg_now = A / C if C else 0

    # Mark the worst single-year fall, if there is one, rather than hard-coding
    # a year that may not exist in a future edition.
    annotations = []
    if len(assets_b) > 1:
        drops = [(years[i], assets_b[i] / assets_b[i - 1] - 1)
                 for i in range(1, len(assets_b))]
        worst_y, worst_d = min(drops, key=lambda t: t[1])
        if worst_d < -0.02:
            annotations.append({"year": worst_y,
                                "text": f"{worst_y} market decline"})

    # The caption has to match what is actually drawn. The delivered template
    # hard-coded "the two periods ... in both cases", which is wrong for any
    # edition with one dip or none, so it is derived here instead.
    if not annotations:
        caption = (f"Assets rose in every {'year' if q == 4 else f'Q{q}'} "
                   f"on this chart.")
    else:
        names = " and ".join(a["text"] for a in annotations)
        one = len(annotations) == 1
        recovered = []
        for a in annotations:
            i = years.index(a["year"])
            prior = max(assets_b[:i]) if i else assets_b[0]
            recovered.append(any(v >= prior for v in assets_b[i + 1:]))
        if all(recovered) and any(recovered):
            tail = (" Assets regained the prior peak afterwards."
                    if one else
                    " Assets regained the prior peak after each.")
        else:
            tail = ""
        caption = (f"The dotted marker shows the period when assets fell: "
                   f"{names}.{tail}" if one else
                   f"Dotted markers show the {len(annotations)} periods when "
                   f"assets fell: {names}.{tail}")

    # Label the ends and any annotated year. Keeping this short is deliberate.
    label_years = {years[0], years[-1]} | {a["year"] for a in annotations}

    first_avg, last_avg = avg[0], avg[-1]
    delta = last_avg / first_avg - 1

    return {
        "period_label": ("End-of-year data" if q == 4
                         else f"Q{q} {year} data"),
        "year": str(year),
        "as_of": f"{MONTH[q]}, {year}",
        "as_of_short": f"{SHORT[q]}, {year}",
        "file_stem": f"Q{q}-{year}-Graphic",
        "headline": f"Total assets in 529 plans reached ${A/1e9:,.0f} billion",
        "headline_highlight": f"${A/1e9:,.0f} billion",
        "deck": (f"Families held {C/1e6:.2f} million accounts as of "
                 f"{MONTH[q]}, {year}, with an average balance of "
                 f"${avg_now:,.0f}. Account numbers have risen in every year "
                 f"on record. Average balance moves with the market."),
        "assets": {
            "unit": "Total assets, $ billions",
            "series": [{"year": y, "value": v} for y, v in zip(years, assets_b)],
            "hero_label": f"${A/1e9:,.0f}B",
            "annotations": annotations,
            "label_years": sorted(label_years),
            "caption": caption,
        },
        "accounts": {
            "unit": "Open accounts, millions",
            "series": [{"year": y, "value": v} for y, v in zip(years, accounts_m)],
            "hero_label": f"{C/1e6:.2f}M",
            "growth_note": (
                f"Accounts grew {accounts_m[-1]/accounts_m[0]-1:+.0%} from "
                f"{years[0]} to {years[-1]}. Average balance grew "
                f"{delta:+.0%} over the same period. Average balance is "
                f"derived, assets divided by accounts."),
        },
        "average_account": {
            "title": "Average account size",
            "from_year": str(years[0]),
            "from_value": f"${first_avg:,.0f}",
            "to_label": f"{SHORT[q]}, {year}",
            "to_value": f"${last_avg:,.0f}",
            "delta": f"{delta:+.0%}",
            "note": (f"Compares {years[0]} with {years[-1]}. Derived figure, "
                     f"assets divided by accounts."),
        },
        "automatic": {
            "title": "Plans reporting",
            "value": f"{cur['plan'].nunique()}",
            "body": (f"529 plans reported for {MONTH[q]}, {year}, across "
                     f"{cur[cur['state'] != 'PRIVATE']['state'].nunique()} "
                     f"states and jurisdictions."),
        },
        "footer": {
            "source": ("Source: The 529 Network quarterly data collection from "
                       "state 529 program administrators."),
            "scope": ("Total assets cover 529 savings and prepaid tuition "
                      "plans. ABLE accounts are excluded. Average balance is "
                      "derived, assets divided by accounts."),
            "reporting": f"{cur['plan'].nunique()} plans reporting",
            "url": "529network.org",
            "url_href": url,
        },
        "label_precision": "rounded",
        "cta": {
            "title": "Compare plans",
            "body": "Every state plan, side by side, with your home state shown first.",
            "url": url,
            "url_label": "529network.org",
        },
        "_avg_series": avg,
    }


# ───────────────────────────── rendering ─────────────────────────────
def build_html(spec):
    A = {p["year"]: p["value"] for p in spec["assets"]["series"]}
    N = {p["year"]: p["value"] for p in spec["accounts"]["series"]}
    years = [p["year"] for p in spec["accounts"]["series"]]
    avg = spec.get("_avg_series") or [A[y] * 1e9 / (N[y] * 1e6) for y in years]

    hl = spec.get("headline_highlight", "")
    head = spec["headline"]
    head_html = (head.replace(hl, f'<span class="hl">{hl}</span>')
                 if hl and hl in head else head)

    return Template((ROOT / "template.html").read_text()).render(
        d=spec,
        mark_529=(ASSETS / "mark-529.svg").read_text(),
        mark_nast=(ASSETS / "nast.svg").read_text(),
        headline_html=head_html,
        assets_svg=area_chart(spec["assets"], spec["as_of_short"],
                              set(spec["assets"]["label_years"])),
        decomp_svg=decomposition_chart(spec["accounts"], avg,
                                       spec["as_of_short"],
                                       spec["average_account"]["to_value"]),
        qr=qr_svg(spec["cta"]["url"]),
    )


def chromium_available() -> bool:
    """True when a browser capable of rendering the PDF can be launched."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            b.close()
        return True
    except Exception:
        return False


def ensure_chromium() -> tuple[bool, str]:
    """Install the Playwright browser if it is missing. Safe to call twice."""
    if chromium_available():
        return True, "ready"
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install",
                        "chromium", "--with-deps"],
                       capture_output=True, timeout=600)
    except Exception:
        pass
    if chromium_available():
        return True, "installed"
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install",
                        "chromium"], capture_output=True, timeout=600)
    except Exception as e:
        return False, str(e)[:200]
    return (chromium_available(),
            "installed" if chromium_available() else "unavailable")


def render(spec) -> dict:
    """Render the spec. Returns {'html', 'pdf', 'png'}; pdf/png may be None."""
    html = build_html(spec)
    out = {"html": html.encode("utf-8"), "pdf": None, "png": None}

    if not chromium_available():
        return out

    from playwright.sync_api import sync_playwright
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        # The template pulls its marks from a relative path, so render from a
        # copy of the package directory to keep those references resolvable.
        work = tmp / "pkg"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns("__pycache__"))
        page_path = work / "page.html"
        page_path.write_text(html)

        pdf_path, png_path = tmp / "out.pdf", tmp / "out.png"
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page(viewport={"width": 816, "height": 1056},
                             device_scale_factor=3)
            pg.goto(page_path.as_uri())
            pg.wait_for_timeout(400)
            pg.pdf(path=str(pdf_path), width="8.5in", height="11in",
                   print_background=True,
                   margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            pg.screenshot(path=str(png_path), full_page=True)
            br.close()
        out["pdf"] = pdf_path.read_bytes()
        out["png"] = png_path.read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out
