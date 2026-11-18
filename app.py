"""
Assets & Accounts | The 529 Network
Four reported fields: state, plan name, assets, open accounts.
Everything on screen derives from those four. No fund manager names.

Data: data/529_data.csv
  Year, Period, Date, State, PlanName, Accounts, AUM, Note
"""

from __future__ import annotations

import io
import os
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from infographic import render as ig_render

# ────────────────────────── brand ──────────────────────────
GREEN, DARK, STEEL, MIST = "#3A8916", "#2B650B", "#708686", "#C6DDBB"

# The 529 Network logo, embedded as a data URI so the sidebar never
# depends on a file being present on the deploy. A committed PNG that
# arrives corrupt or missing on the server was showing a broken icon;
# inlining it removes that failure mode entirely.
LOGO_DATA_URI = "data:image/jpeg;base64,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"
# RED is the "decline" color, paired with GREEN for gains. It is a dark burnt
# brown rather than a true red: against GREEN it has ~1.9:1 luminance contrast
# (vs ~1.3:1 for a mid red), which red-green colorblind viewers can tell apart,
# and 8:1 against the paper background. Direction is also shown by the bar's
# sign, so color is never the only cue. (ADA review requested by testers.)
INK, PAPER, AMBER, RED = "#1C2420", "#FAFBF8", "#C98A2B", "#7A3B0E"

USPS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN",
    "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

st.set_page_config(page_title="Assets & Accounts | The 529 Network",
                   page_icon=("assets/logo.png"
                              if os.path.exists("assets/logo.png") else "🎓"),
                   layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
html, body, [class*="css"], .stApp {{ font-family:'Inter',sans-serif; color:{INK}; }}
.stApp {{ background:{PAPER}; }}
h1,h2,h3,h4 {{ font-family:'Fraunces',serif !important; letter-spacing:-0.01em; }}
section[data-testid="stSidebar"] {{ background:#F1F6EC; border-right:1px solid {MIST}; }}
.eyebrow {{ font-family:'IBM Plex Mono',monospace; font-size:.72rem; letter-spacing:.14em;
  text-transform:uppercase; color:{STEEL}; }}
.pagetitle {{ font-family:'Fraunces',serif; font-size:2rem; font-weight:600;
  line-height:1.1; margin:.15rem 0 .2rem; }}
.subtitle {{ color:{STEEL}; font-size:.92rem; margin-bottom:.5rem; }}
.ledger {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(165px,1fr));
  border-top:2px solid {DARK}; border-bottom:1px solid {MIST}; background:#fff;
  margin:.4rem 0 1.1rem; }}
.ledger .cell {{ padding:.8rem 1rem; border-right:1px solid #EDF3E8; }}
.ledger .cell:last-child {{ border-right:none; }}
.ledger .v {{ font-family:'IBM Plex Mono',monospace; font-size:1.4rem; color:{DARK};
  font-variant-numeric:tabular-nums; }}
.ledger .k {{ font-size:.7rem; letter-spacing:.08em; text-transform:uppercase;
  color:{STEEL}; margin-top:.12rem; }}
.ledger .d {{ font-family:'IBM Plex Mono',monospace; font-size:.76rem; margin-top:.08rem; }}
.up {{ color:{GREEN}; }} .down {{ color:{RED}; }} .flat {{ color:{STEEL}; }}
.note {{ color:{STEEL}; font-size:.8rem; margin-top:-.35rem; }}
.callout {{ background:#F1F6EC; border-left:3px solid {GREEN}; padding:.55rem .85rem;
  font-size:.84rem; color:#3c4a44; border-radius:0 4px 4px 0; margin:.5rem 0; }}
.stTabs [aria-selected="true"] {{ color:{DARK} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color:{GREEN}; }}
#MainMenu, footer {{ visibility:hidden; }}
/* Hide the Streamlit Community Cloud "Created by / Hosted by" viewer badge in
   the corner. It links to the developer profile and other apps, which the
   Network does not want surfaced on a member-facing embed. These selectors
   cover the several class names Streamlit has used for it. */
[data-testid="stAppViewerBadge"],
[data-testid="viewerBadge"],
.viewerBadge_container__1QSob,
.viewerBadge_link__qRIco,
.styles_viewerBadge__CvC9N,
a[href*="streamlit.io/cloud"],
a[href*="share.streamlit.io"] {{ display:none !important; }}
</style>
""", unsafe_allow_html=True)


# ────────────────────────── format ──────────────────────────
def usd(v) -> str:
    if v is None or pd.isna(v) or np.isinf(v):
        return "n/a"
    a = abs(v)
    if a >= 1e12: return f"${v/1e12:,.2f}T"
    if a >= 1e9:  return f"${v/1e9:,.1f}B"
    if a >= 1e6:  return f"${v/1e6:,.1f}M"
    return f"${v:,.0f}"


def num(v) -> str:
    if v is None or pd.isna(v) or np.isinf(v):
        return "n/a"
    a = abs(v)
    if a >= 1e6: return f"{v/1e6:,.2f}M"
    if a >= 1e3: return f"{v/1e3:,.0f}K"
    return f"{v:,.0f}"


def pct(v, signed=True) -> str:
    if v is None or pd.isna(v) or np.isinf(v):
        return "n/a"
    return f"{'+' if signed and v >= 0 else ''}{v*100:,.1f}%"


def dlt(v) -> str:
    if v is None or pd.isna(v) or np.isinf(v):
        return '<span class="flat">n/a</span>'
    c = "up" if v > 5e-4 else ("down" if v < -5e-4 else "flat")
    return f'<span class="{c}">{pct(v)}</span>'


def ratio(a, b):
    """Safe division. Guards the zero-account rows the record contains."""
    if a is None or b is None or pd.isna(a) or pd.isna(b) or b == 0:
        return np.nan
    return a / b


def growth(now, before):
    r = ratio(now, before)
    return np.nan if pd.isna(r) else r - 1


def money_ticks(fig_obj, axis="yaxis", series=None):
    """Relabel a money axis in $B/$M so it never shows Plotly's SI 'G'.

    series: the values plotted on that axis, used to size the ticks.
    Handles axes that span negative to positive (e.g. dollar change).
    """
    clean = [] if series is None else [
        v for v in list(series) if v is not None and not pd.isna(v)]
    if not clean:
        return fig_obj
    lo, hi = min(clean + [0]), max(clean + [0])
    span = max(abs(lo), abs(hi))
    if span == 0:
        return fig_obj
    if span >= 1e9:
        unit, suf = 1e9, "B"
        step = 1e11 if span >= 5e11 else 1e10 if span >= 5e10 else 1e9
    elif span >= 1e6:
        unit, suf = 1e6, "M"
        step = 1e8 if span >= 5e8 else 1e7 if span >= 5e7 else 1e6
    else:
        unit, suf, step = 1e3, "K", 1e3
    start = int(lo / step) - 1 if lo < 0 else 0
    end = int(hi / step) + 2
    ticks = [i * step for i in range(start, end)]
    ticks = [t for t in ticks if lo - step / 2 <= t <= hi + step / 2 or t == 0]

    def lab(t):
        if t == 0:
            return "$0"
        s = "-" if t < 0 else ""
        return f"{s}${abs(t)/unit:,.0f}{suf}"

    text = [lab(t) for t in ticks]
    fig_obj.update_layout(**{axis: dict(tickvals=ticks, ticktext=text)})
    return fig_obj


# ────────────────────────── data ──────────────────────────
PREPAID = re.compile(
    r"prepaid|guaranteed|tuition promise|tuition plan|u\.plan|\(MET\)|\(GET\)|"
    r"PACT|College Illinois|Advance Payment", re.I)


@st.cache_data(show_spinner=False)
def load():
    d = pd.read_csv("data/529_data.csv").rename(columns={
        "State": "state", "PlanName": "plan", "Accounts": "accounts",
        "AUM": "assets", "Note": "note"})
    d["quarter"] = d["Year"].astype(str) + d["Period"]
    d["period"] = pd.PeriodIndex(d["quarter"], freq="Q")
    d["t"] = d["period"].dt.to_timestamp(how="start")
    d["state"] = d["state"].str.strip()
    d["plan"] = d["plan"].str.strip()

    # Explicit plan-name corrections, applied before the punctuation-blind merge
    # below. Some plans were reported under names that differ by a whole word,
    # so the automatic key cannot join them, and some early aggregate rows were
    # labelled with just the state name. Each entry maps an old exact name to
    # the plan's current name so its history reads as one continuous series.
    # Washington was reported by its administrator (WA529) as the trigger for
    # these; the same pattern is corrected wherever it is unambiguous.
    NAME_FIXES = {
        # Washington GET (prepaid) carried three names over the years, and the
        # 2003-2004 rows were labelled only "Washington". All are the one GET
        # plan that has existed since 2001. DreamAhead (savings) began in 2018.
        ("Washington", "Washington"):
            "Washington Guaranteed Education Tuition (GET)",
        ("Washington", "Washington Prepaid"):
            "Washington Guaranteed Education Tuition (GET)",
        ("Washington", "Washington Guaranteed Education Tuition"):
            "Washington Guaranteed Education Tuition (GET)",
        ("Washington", "Guaranteed Education Tuition (GET)"):
            "Washington Guaranteed Education Tuition (GET)",
        ("Washington", "DreamAhead (Washington College Investment Program)"):
            "Washington DreamAhead College Investment Plan",
        # Illinois Bright Start, per the Illinois Treasurer's office: the Direct
        # line is the continuous Bright Start plan, reported as "Bright Start
        # Direct" through 2016, then "Bright Start" in 2017-2018, then the
        # current name. Join all three so its history runs unbroken from 2009.
        # The separate Advisor line was merged into Bright Directions in 2017
        # and is left as a plan that no longer reports.
        ("Illinois", "Illinois - Bright Start Direct"): "Illinois Bright Start",
        ("Illinois", "Bright Start"): "Illinois Bright Start",
    }
    key = list(zip(d["state"], d["plan"]))
    d["plan"] = [NAME_FIXES.get(k, p) for k, p in zip(key, d["plan"])]
    # The source spells 15 plans two ways, changing punctuation or casing
    # partway through (Virginia CollegeAmerica became Virginia - CollegeAmerica
    # and back). Left alone, one plan reads as two and its history breaks in
    # half. Merge on a punctuation-blind key and adopt the most recent spelling.
    # No two spellings ever report in the same period, so nothing double counts,
    # and the assertion below keeps it that way.
    d["alias"] = d["plan"]
    d["_k"] = (d["plan"].str.normalize("NFKC").str.lower()
               .str.replace(r"[^a-z0-9]", "", regex=True))
    newest = (d.sort_values(["Year", "Period"])
              .groupby("_k")["plan"].last())
    d["plan"] = d["_k"].map(newest)
    clash = d[d["assets"].notna()].groupby(["_k", "Year", "Period"]).size()
    assert (clash <= 1).all(), "two spellings report in the same period"
    d = d.drop(columns="_k")

    d["type"] = np.where(d["plan"].str.contains(PREPAID), "Prepaid", "Savings")

    # Distribution channel: Direct or Advisor. A later data revision will carry
    # an explicit Channel column; until then, read it where present and fall
    # back to the plan name, which labels the channel for most plans that have
    # both. A plan that names neither is treated as Direct, the common case.
    if "Channel" in d.columns:
        ch = d["Channel"].astype(str).str.strip().str.title()
        d["channel"] = np.where(ch.isin(["Direct", "Advisor"]), ch, np.nan)
    else:
        d["channel"] = np.nan
    name_adv = d["plan"].str.contains(r"advisor|advisory", case=False, regex=True)
    name_dir = d["plan"].str.contains(r"direct", case=False, regex=True)
    d["channel"] = d["channel"].where(
        d["channel"].notna(),
        np.select([name_adv, name_dir], ["Advisor", "Direct"], default="Direct"))

    d["note"] = d["note"].fillna("")
    d["reporting"] = d["assets"].notna()
    # Before 2009Q4 the record is one aggregate row per state, labelled with the
    # state name rather than the plan name. From 2009Q4 it names real plans.
    # National and state totals hold across the whole record; plan-level views
    # only mean anything after the split.
    d["plan_level"] = d["period"] >= pd.Period("2009Q4", freq="Q")

    # Display name in "State - Name" form, so the plan list sorts by state and
    # every plan sits in its state's block. The full reported name is kept after
    # the dash; where the name already begins with the state (or the state is
    # already present, as in "College Illinois"), it is not duplicated. Requested
    # by DOT Committee testers. The pre-2009 aggregate rows keep the state name.
    def _display(state, plan, is_plan_level):
        if not is_plan_level or plan == state:
            return plan
        p = plan
        # strip a leading "State - " / "State " the source already added
        for pre in (f"{state} - ", f"{state}- ", f"{state} ", f"{state}-"):
            if p.startswith(pre):
                p = p[len(pre):]
                break
        return f"{state} - {p}"
    d["plan"] = [
        _display(s, p, lvl)
        for s, p, lvl in zip(d["state"], d["plan"], d["plan_level"])]

    return d.sort_values(["period", "state", "plan"]).reset_index(drop=True)


PLAN_ERA = pd.Period("2009Q4", freq="Q")


full = load()
df = full[full["reporting"]].copy()
QS = sorted(df["period"].unique())


def qlabel(p) -> str:
    """Display a quarter as '2026 - Q3' (DOT Committee's requested format)."""
    p = pd.Period(str(p).replace(" - Q", "Q").replace(" ", ""), freq="Q") \
        if not isinstance(p, pd.Period) else p
    return f"{p.year} - Q{p.quarter}"


def qparse(label: str):
    """Parse a '2026 - Q3' label (or a bare '2026Q3') back to a Period."""
    return pd.Period(str(label).replace(" - Q", "Q").replace(" ", ""), freq="Q")


LABELS = [qlabel(p) for p in QS]

PLOT = {"width": "stretch", "config": {"displayModeBar": False}}


COLORWAY = [GREEN, STEEL, AMBER, DARK, "#8FB07C", "#4A5D57"]


def fig(f, h=340):
    f.update_layout(template="plotly_white", height=h, colorway=COLORWAY,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter,sans-serif", size=12, color=INK),
                    margin=dict(l=10, r=10, t=30, b=10),
                    hoverlabel=dict(font_family="IBM Plex Mono"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    f.update_xaxes(gridcolor="#EDF3E8", zeroline=False)
    f.update_yaxes(gridcolor="#EDF3E8", zeroline=False)
    # Any chart whose x-axis is time gets an explicit tick on the newest year,
    # so a series running into 2026 never reads as though it stopped at 2025.
    xs = []
    for tr in f.data:
        if getattr(tr, "x", None) is not None:
            xs.extend(list(tr.x))
    if xs:
        xt = pd.to_datetime(pd.Series(xs), errors="coerce")
        if xt.notna().mean() > 0.9 and xt.dt.year.nunique() > 1:
            year_ticks(f, xt.dropna())
    return f


def year_ticks(f, times, every=5):
    """Label the x-axis every `every` years and always include the latest year.

    Plotly's automatic ticks stop at the last round multiple, so a chart that
    runs into 2026 still reads "2025" at the right edge. This anchors an
    explicit tick on the final year so the newest data is unmistakable.
    """
    t = pd.to_datetime(pd.Series(times))
    if t.empty:
        return f
    y0, y1 = int(t.dt.year.min()), int(t.dt.year.max())
    first_tick = y0 - (y0 % every)
    yrs = [y for y in range(first_tick, y1 + 1, every) if y >= y0]
    if y1 not in yrs:
        yrs.append(y1)                      # always show the newest year
    # drop a labelled year if it would collide with the final one
    yrs = [y for y in yrs if y == y1 or y1 - y >= 2]
    # Anchor each tick on Jan 1, matching the start-of-quarter timestamps the
    # charts use. A range end of Q2 still shows its year because the axis is
    # extended just past the last point below.
    vals = [pd.Timestamp(year=y, month=1, day=1) for y in yrs]
    f.update_xaxes(tickmode="array", tickvals=vals,
                   ticktext=[str(y) for y in yrs])
    # Give the axis a little room past the final point so a mid-year end (like
    # Q2) still sits inside the plotted range and its year tick stays visible.
    last = t.max()
    f.update_xaxes(range=[t.min() - pd.Timedelta(days=120),
                          last + pd.Timedelta(days=120)])
    return f


# ────────────────────────── sidebar ──────────────────────────
with st.sidebar:
    # Logo is embedded (LOGO_DATA_URI), so it always renders regardless of
    # what is on the deploy.
    st.markdown(
        f'<img src="{LOGO_DATA_URI}" alt="The 529 Network" '
        f'style="width:100%;height:auto;margin:.1rem 0 .3rem">',
        unsafe_allow_html=True)
    st.markdown("### Assets & Accounts")
    with st.expander("New to 529 data? Start here"):
        st.markdown("""
A **529 plan** is a state-sponsored account that helps families save for
education. This dashboard tracks two numbers for every plan in the country:

**Volume of Assets** is the total dollars families hold in a plan. This rises
when families add money or markets go up, and falls when they withdraw for
school or markets go down.

**Number of Accounts** counts how many accounts exist. This only moves when
families open or close accounts, so it is the cleaner read on participation.

**Average balance** is simply assets divided by accounts.

**Savings vs prepaid**: savings plans invest contributions in markets. Prepaid
plans let families lock in tuition at today's prices.

**Direct vs advisor**: direct plans are opened by families on their own;
advisor plans are sold through a financial advisor. Some states run both.

Pick any reporting period with the slider below, and choose whether to view
savings plans, prepaid plans, or the total of both. Every figure and chart on
the page follows both choices.
""")
    q_sel = st.select_slider("Reporting period", options=LABELS, value=LABELS[-1])
    p_sel = qparse(q_sel)
    type_sel = st.radio(
        "Plan type", ["Total", "Savings", "Prepaid"], index=0,
        help="Total covers every plan. Savings plans invest in markets. "
             "Prepaid plans lock in tuition prices. Every figure and chart "
             "on the page follows this choice.")
    chan_sel = st.radio(
        "Distribution channel", ["All", "Direct", "Advisor"], index=0,
        help="Direct plans are opened by families on their own. Advisor plans "
             "are sold through a financial advisor. Some states run both. "
             "Choose All to combine them.")
    st.markdown(
        f'<div class="note">Data submitted by states and consolidated by '
        f'The 529 Network. {len(LABELS)} reporting periods, {LABELS[0]} to '
        f'{LABELS[-1]}. Reporting runs quarterly from 2021 and is sparser before '
        f'that, so the timeline is not evenly spaced.</div>',
        unsafe_allow_html=True)
    st.markdown(
        '<div class="note" style="margin-top:.5rem"><strong>Note:</strong> '
        'These figures are self-reported by the states and have not been '
        'audited or verified by a third party.</div>',
        unsafe_allow_html=True)

# The type and channel filters are dashboard wide. Everything below reads the
# filtered frame, so headline figures, charts, tables, and downloads all agree.
if type_sel != "Total":
    df = df[df["type"] == type_sel]
if chan_sel != "All":
    df = df[df["channel"] == chan_sel]

cur = df[df["period"] == p_sel]
i = QS.index(p_sel)
prev_p = QS[i - 1] if i else None
yoy_p = (p_sel - 4) if (p_sel - 4) in QS else None
prev = df[df["period"] == prev_p] if prev_p is not None else df.iloc[:0]
yoy = df[df["period"] == yoy_p] if yoy_p is not None else df.iloc[:0]
prior_lbl = qlabel(prev_p) if prev_p is not None else "n/a"

# ────────────────────────── header ──────────────────────────
st.markdown('<div class="eyebrow">Member dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="pagetitle">Assets & Accounts</div>', unsafe_allow_html=True)
scope_txt = {"Total": "every 529 plan on record",
             "Savings": "savings plans only",
             "Prepaid": "prepaid plans only"}[type_sel]
st.markdown(f'<div class="subtitle">Volume of assets and number of accounts for '
            f'{scope_txt}. Showing {q_sel}.</div>', unsafe_allow_html=True)

# Count real jurisdictions. PRIVATE is the multistate plan, not a state.
geo = cur[cur["state"] != "PRIVATE"]["state"].unique()
has_dc = "District of Columbia" in geo
n_states = len([g for g in geo if g != "District of Columbia"])
dc_txt = " and D.C." if has_dc else ""

A, C = cur["assets"].sum(), cur["accounts"].sum()
A0 = prev["assets"].sum() if len(prev) else np.nan
C0 = prev["accounts"].sum() if len(prev) else np.nan
AY = yoy["assets"].sum() if len(yoy) else np.nan

st.markdown(f"""
<div class="ledger">
  <div class="cell"><div class="v">{usd(A)}</div><div class="k">Volume of Assets</div>
    <div class="d">{dlt(growth(A, A0))} vs {prior_lbl} &nbsp;·&nbsp; {dlt(growth(A, AY))} YoY</div></div>
  <div class="cell"><div class="v">{num(C)}</div><div class="k">Number of Accounts</div>
    <div class="d">{dlt(growth(C, C0))} vs {prior_lbl}</div></div>
  <div class="cell"><div class="v">{usd(ratio(A, C))}</div><div class="k">Average balance</div>
    <div class="d">{dlt(growth(ratio(A, C), ratio(A0, C0)))} vs {prior_lbl}</div></div>
  <div class="cell"><div class="v">{cur["plan"].nunique()}</div><div class="k">Plans reporting</div>
    <div class="d"><span class="flat">{n_states} states{dc_txt}</span></div></div>
</div>
""", unsafe_allow_html=True)

def tell_the_story() -> str:
    """One accurate paragraph about the selected period, written from the data."""
    lead = {"Total": "families held",
            "Savings": "families held, in savings plans,",
            "Prepaid": "families held, in prepaid plans,"}[type_sel]
    parts = [f"At the end of {q_sel}, {lead} {usd(A)} across "
             f"{cur['plan'].nunique()} plans in {num(C)} open accounts."]
    ga, gc = growth(A, A0), growth(C, C0)
    if not pd.isna(ga) and not pd.isna(gc):
        a_dir = "grew" if ga > 0 else "fell"
        c_dir = "rose" if gc > 0 else ("fell" if gc < 0 else "held steady")
        parts.append(f"Since {prior_lbl}, total savings {a_dir} "
                     f"{pct(abs(ga), signed=False)} and the number of accounts "
                     f"{c_dir} {pct(abs(gc), signed=False)}.")
        if ga < 0 and gc > 0:
            parts.append("Balances fell while families kept opening accounts, "
                         "which usually means markets dropped, not that savers "
                         "left.")
    # The "largest state holds X%" line was dropped at the Illinois Treasurer's
    # request: the leader rarely changes, so a standing note added little.
    return " ".join(parts)


st.markdown(f'<div class="callout">{tell_the_story()}</div>',
            unsafe_allow_html=True)

tabs = st.tabs(["National", "States", "Plans", "Data", "Infographic"])


# ────────────────────────── National ──────────────────────────
with tabs[0]:
    n = (df.groupby("t", as_index=False)
         .agg(assets=("assets", "sum"), accounts=("accounts", "sum")))
    n["avg"] = n["assets"] / n["accounts"]

    st.markdown('<div class="note">The left chart is the money. The right chart '
                'is the people. Reading them together tells you whether a change '
                'came from markets or from families. National totals cover the '
                'whole record, 2001 to today.</div>', unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Volume of Assets")
        f = go.Figure(go.Scatter(x=n["t"], y=n["assets"], fill="tozeroy",
                                 line=dict(color=GREEN, width=2),
                                 fillcolor="rgba(58,137,22,.12)",
                                 hovertemplate="%{x|%Y - Q%q}<br>%{customdata}<extra></extra>",
                                 customdata=[usd(v) for v in n["assets"]]))
        money_ticks(f, "yaxis", n["assets"])
        st.plotly_chart(fig(f), **PLOT)
    with c2:
        st.markdown("#### Number of Accounts")
        f = go.Figure(go.Scatter(x=n["t"], y=n["accounts"],
                                 line=dict(color=STEEL, width=2),
                                 hovertemplate="%{x|%Y - Q%q}<br>%{y:,.0f}<extra></extra>"))
        st.plotly_chart(fig(f), **PLOT)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### Year over year asset growth")
        g = df.groupby("period", as_index=False)["assets"].sum()
        g["prior"] = g["period"] - 4
        g = g.merge(g[["period", "assets"]].rename(
            columns={"period": "prior", "assets": "a0"}), on="prior", how="left")
        g["yoy"] = g["assets"] / g["a0"] - 1
        g = g.dropna(subset=["yoy"])
        # Start at 2010. Before then the record is sparse, so most quarters have
        # no same-quarter-prior-year to compare against and the bars are gappy;
        # the early swings also run past +30%, which forces the axis wide and
        # flattens the recent quarters. From 2010 the data is quarterly and the
        # range sits within roughly +/-25%, which is what matters to read.
        g = g[g["period"] >= pd.Period("2010Q1", freq="Q")]
        g["t"] = g["period"].dt.to_timestamp(how="start")
        f = go.Figure(go.Bar(x=g["t"], y=g["yoy"],
                             marker_color=[GREEN if v >= 0 else RED for v in g["yoy"]],
                             hovertemplate="%{x|%Y - Q%q}<br>%{y:+.1%}<extra></extra>"))
        f.update_yaxes(tickformat="+.0%")
        st.plotly_chart(fig(f, 300), **PLOT)
        st.markdown('<div class="note">Change in total assets from the same '
                    'quarter a year earlier. Green is growth, red a decline. '
                    'Shown from 2010, when reporting became quarterly.</div>',
                    unsafe_allow_html=True)
    with c4:
        st.markdown("#### Average account balance")
        f = go.Figure(go.Scatter(x=n["t"], y=n["avg"], line=dict(color=DARK, width=2),
                                 hovertemplate="%{x|%Y - Q%q}<br>%{y:$,.0f}<extra></extra>"))
        st.plotly_chart(fig(f, 300), **PLOT)
        st.markdown('<div class="note">What the typical dollar amount per account '
                    'looks like: total assets divided by total accounts.</div>',
                    unsafe_allow_html=True)

    # The savings vs prepaid split only says something when both are in scope.
    # Under a type filter it collapses to one series, so it steps aside and the
    # largest-plans chart takes the full width.
    if type_sel == "Total":
        c5, c6 = st.columns(2)
    else:
        c5, c6 = None, st.container()

    if c5 is not None:
        with c5:
            st.markdown("#### Savings and prepaid assets")
            tt = (df[df["Year"] >= 2003].groupby(["t", "type"])["assets"].sum()
                  .unstack().reindex(columns=["Savings", "Prepaid"]).fillna(0))
            f = go.Figure()
            f.add_scatter(x=tt.index, y=tt["Savings"], name="Savings", stackgroup="a",
                          line=dict(color=GREEN, width=1),
                          customdata=[usd(v) for v in tt["Savings"]],
                          hovertemplate="%{x|%Y - Q%q}<br>%{customdata}<extra>Savings</extra>")
            f.add_scatter(x=tt.index, y=tt["Prepaid"], name="Prepaid", stackgroup="a",
                          line=dict(color=AMBER, width=1),
                          customdata=[usd(v) for v in tt["Prepaid"]],
                          hovertemplate="%{x|%Y - Q%q}<br>%{customdata}<extra>Prepaid</extra>")
            money_ticks(f, "yaxis", (tt["Savings"] + tt["Prepaid"]))
            st.plotly_chart(fig(f, 300), **PLOT)
            st.markdown('<div class="note">Savings plans invest in markets. Prepaid '
                        'plans lock in tuition prices. Type is read from the plan '
                        'name, and the chart starts in 2003, the first year the '
                        'record separates the two.</div>', unsafe_allow_html=True)
    with c6:
        st.markdown(f"#### The fifteen largest plans, {q_sel}")
        top = (cur.groupby(["plan", "type"], as_index=False)["assets"].sum()
               .sort_values("assets", ascending=False).head(15).iloc[::-1])
        f = go.Figure(go.Bar(
            x=top["assets"], y=top["plan"].str.slice(0, 38), orientation="h",
            marker_color=[AMBER if t == "Prepaid" else GREEN for t in top["type"]],
            customdata=[usd(v) for v in top["assets"]],
            hovertemplate="%{y}<br>%{customdata}<extra></extra>"))
        f.update_yaxes(tickfont=dict(size=10))
        money_ticks(f, "xaxis", top["assets"])
        st.plotly_chart(fig(f, 300), **PLOT)
        if type_sel != "Savings":
            st.markdown('<div class="note">Amber marks prepaid.</div>',
                        unsafe_allow_html=True)

# ────────────────────────── States ──────────────────────────
with tabs[1]:
    st.markdown('<div class="note">Darker green means more. Hover any state for '
                'its numbers, click a state to open its detail, or scroll down '
                'to look at one state closely.</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="note" style="margin-top:.3rem">A plan is shown '
                'under the state that administers it. Its assets and accounts '
                'are not necessarily held entirely by residents of that state, '
                'since families can open many plans from anywhere.</div>',
                unsafe_allow_html=True)
    st.write("")
    # Shared state list and default for both the map click handler and the
    # detail selectbox below. Uses the full plan-level roster so a state the
    # current filter empties is still selectable.
    _states = sorted(full[full["plan_level"]]["state"].unique())
    st.session_state.setdefault("state_pick", _states[0])
    s = (cur.groupby("state", as_index=False)
         .agg(assets=("assets", "sum"), accounts=("accounts", "sum"),
              plans=("plan", "nunique")))
    s["avg"] = [ratio(a, c) for a, c in zip(s["assets"], s["accounts"])]
    s["avg"] = s["avg"].round(0)
    s["usps"] = s["state"].map(USPS)
    mapped = s.dropna(subset=["usps"])
    offmap = s[s["usps"].isna()]

    c1, c2 = st.columns([1, 3])
    with c1:
        metric = st.radio("Color the map by",
                          ["Assets", "Accounts", "Average balance"])
        k = {"Assets": "assets", "Accounts": "accounts",
             "Average balance": "avg"}[metric]
        missing = sorted(set(USPS) - set(mapped["state"]))
        bits = []
        if missing:
            bits.append(f"{', '.join(missing)} runs no 529 plan, so it is "
                        f"uncolored.")
        if len(offmap):
            bits.append(f"{', '.join(offmap['state'])} is the multistate plan. "
                        f"It has no geography and sits off the map, but it is in "
                        f"the table below.")
        if bits:
            st.markdown(f'<div class="callout">{" ".join(bits)}</div>',
                        unsafe_allow_html=True)
    with c2:
        f = go.Figure(go.Choropleth(
            locations=mapped["usps"], z=mapped[k], locationmode="USA-states",
            # Darker gradient (requested by testers): deeper mid and end stops so
            # higher-value states read clearly rather than washing out pale.
            colorscale=[[0, "#DCE8D2"], [.35, "#7CA85C"],
                        [.7, GREEN], [1, "#1E4A07"]],
            marker_line_color="white", colorbar=dict(thickness=10, len=.7),
            customdata=np.stack([mapped["state"], mapped["assets"],
                                 mapped["accounts"], mapped["avg"],
                                 mapped["plans"]], axis=-1),
            hovertemplate=("<b>%{customdata[0]}</b>"
                           "<br>Volume of Assets %{customdata[1]:$,.0f}"
                           "<br>Number of Accounts %{customdata[2]:,.0f}"
                           "<br>Avg balance %{customdata[3]:$,.0f}"
                           "<br>Plans %{customdata[4]}<extra></extra>")))
        f.update_geos(scope="usa", bgcolor="rgba(0,0,0,0)")
        # Clicking a state selects it in the detail view below, without changing
        # anything else on the page. The click returns the USPS code; we map it
        # back to the state name and stash it for the selectbox default.
        ev = st.plotly_chart(fig(f, 420), on_select="rerun",
                             selection_mode="points", key="statemap",
                             config={"displayModeBar": False},
                             width="stretch")
        pts = (ev.get("selection", {}) or {}).get("points", []) if ev else []
        if pts:
            code = pts[0].get("location")
            back = {v: kk for kk, v in USPS.items()}
            if code in back:
                # Write the selectbox's key directly (the map renders before the
                # selectbox this run), so the click lands in the dropdown.
                st.session_state["state_pick"] = back[code]
        st.markdown('<div class="note">Tip: click a state on the map to see its '
                    'detail below.</div>', unsafe_allow_html=True)

    st.dataframe(
        s.sort_values(k, ascending=False)[
            ["state", "plans", "assets", "accounts", "avg"]],
        hide_index=True, width="stretch", height=280,
        column_config={
            "state": "State", "plans": "Plans",
            "assets": st.column_config.NumberColumn("Assets", format="dollar"),
            "accounts": st.column_config.NumberColumn("Accounts", format="localized"),
            "avg": st.column_config.NumberColumn("Avg balance ($)", format="localized")})

    st.divider()
    # The selectbox keeps its own choice across reruns via its key, so changing
    # the plan type or channel in the sidebar does not reset the chosen state.
    # A map click writes the same key (above), so map and dropdown stay in sync.
    state = st.selectbox("Look at one state", _states, key="state_pick")
    sd = df[df["state"] == state]
    sc = sd[sd["period"] == p_sel]
    sp = sd[sd["period"] == prev_p] if prev_p is not None else sd.iloc[:0]
    sa, sac = sc["assets"].sum(), sc["accounts"].sum()

    st.markdown(f"""
    <div class="ledger">
      <div class="cell"><div class="v">{usd(sa)}</div><div class="k">Assets, {q_sel}</div>
        <div class="d">{dlt(growth(sa, sp["assets"].sum() if len(sp) else np.nan))} vs {prior_lbl}</div></div>
      <div class="cell"><div class="v">{num(sac)}</div><div class="k">Accounts</div>
        <div class="d">{dlt(growth(sac, sp["accounts"].sum() if len(sp) else np.nan))} vs {prior_lbl}</div></div>
      <div class="cell"><div class="v">{usd(ratio(sa, sac))}</div><div class="k">Average balance</div></div>
    </div>""", unsafe_allow_html=True)

    g = (sd.groupby("t", as_index=False)
         .agg(assets=("assets", "sum"), accounts=("accounts", "sum")))
    st.markdown(f"#### {state}: assets and accounts")
    f = go.Figure()
    f.add_scatter(x=g["t"], y=g["assets"], name="Assets",
                  line=dict(color=GREEN, width=2),
                  customdata=[usd(v) for v in g["assets"]],
                  hovertemplate="%{x|%Y - Q%q}<br>%{customdata}<extra>Assets</extra>")
    f.add_scatter(x=g["t"], y=g["accounts"], name="Accounts", yaxis="y2",
                  line=dict(color=STEEL, width=2, dash="dot"),
                  hovertemplate="%{x|%Y - Q%q}<br>%{y:,.0f}<extra>Accounts</extra>")
    f.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False))
    money_ticks(f, "yaxis", g["assets"])
    st.plotly_chart(fig(f, 340), **PLOT)

    st.markdown(f"#### Plans in {state}, {q_sel}")
    pt = (sc.groupby(["plan", "type"], as_index=False)
          .agg(assets=("assets", "sum"), accounts=("accounts", "sum"))
          .sort_values("assets", ascending=False))
    pt["avg"] = pd.Series(
        [ratio(a, c) for a, c in zip(pt["assets"], pt["accounts"])],
        index=pt.index).round(0)
    st.dataframe(
        pt, hide_index=True, width="stretch",
        column_config={
            "plan": st.column_config.TextColumn("Plan", width="large"),
            "type": "Type",
            "assets": st.column_config.NumberColumn("Assets", format="dollar"),
            "accounts": st.column_config.NumberColumn("Accounts", format="localized"),
            "avg": st.column_config.NumberColumn("Avg balance ($)", format="localized")})

# ────────────────────────── Plans ──────────────────────────
with tabs[2]:
    plan_era = df[df["plan_level"]]
    latest = df[df["period"] == QS[-1]]
    current = set(latest["plan"])
    retired = sorted(set(plan_era["plan"]) - current)

    # A filter combination can legitimately be empty (for example Prepaid plans
    # sold through an Advisor, which do not exist). Say so plainly rather than
    # letting the plan picker fail on an empty set.
    if plan_era.empty or (not current and not retired):
        st.markdown(
            f'<div class="callout">No plans match the current filters'
            f'{" (" + type_sel + ", " + chan_sel + ")" if (type_sel != "Total" or chan_sel != "All") else ""}. '
            f'Widen the plan type or channel in the sidebar to see plans here.'
            f'</div>', unsafe_allow_html=True)
    else:

        show_retired = st.toggle(
            f"Include the {len(retired)} plans that no longer report",
            help="Plans that closed, merged, or were renamed. Their history stops "
                 "on their last reporting period.")
        # Order plans by their state, then by plan name, so every plan sits in its
        # state's block in the list rather than by the first letter of a name that
        # might start with "College", "The", or a ticker. Requested by the Illinois
        # Treasurer's office. The displayed names are left exactly as reported.
        plan_state = plan_era.groupby("plan")["state"].last()
        by_state = lambda names: sorted(
            names, key=lambda p: (plan_state.get(p, ""), p))
        universe = by_state(current) + (by_state(retired) if show_retired else [])
        biggest = latest.groupby("plan")["assets"].sum().idxmax()
        plan = st.selectbox("Plan", universe, index=universe.index(biggest))

        pf = plan_era[plan_era["plan"] == plan].sort_values("period")
        pc = pf[pf["period"] == p_sel]
        active = len(pc) > 0
        pstate = pf["state"].iloc[-1]
        last_p = pf["period"].iloc[-1]
        p0 = pf["period"].iloc[0]

        if not active:
            st.markdown(
                f'<div class="callout">This plan does not report in {q_sel}. Its '
                f'record runs from {qlabel(p0)} to '
                f'{qlabel(last_p)}, and the figures below are its '
                f'final reported quarter.</div>', unsafe_allow_html=True)
            pc = pf[pf["period"] == last_p]
            shown = qlabel(last_p)
        else:
            shown = q_sel

        pa = pc["assets"].sum()
        pac = pc["accounts"].sum()
        st_assets = df[(df["period"] == pc["period"].iloc[0])
                       & (df["state"] == pstate)]["assets"].sum()

        st.markdown(f"""
        <div class="ledger">
          <div class="cell"><div class="v">{usd(pa)}</div><div class="k">Assets, {shown}</div></div>
          <div class="cell"><div class="v">{num(pac)}</div><div class="k">Accounts</div></div>
          <div class="cell"><div class="v">{usd(ratio(pa, pac))}</div><div class="k">Average balance</div></div>
          <div class="cell"><div class="v">{pct(ratio(pa, st_assets), signed=False)}</div>
            <div class="k">Share of {pstate}</div></div>
          <div class="cell"><div class="v">{qlabel(p0)}</div>
            <div class="k">First on record</div></div>
        </div>""", unsafe_allow_html=True)

        aliases = sorted(set(pf["alias"]) - {plan})
        if aliases:
            st.markdown(f'<div class="note">The record also spells this plan '
                        f'{", ".join(chr(34) + a + chr(34) for a in aliases)}. '
                        f'Both spellings are the same plan, and its history below '
                        f'is joined.</div>', unsafe_allow_html=True)
        if len(pf) < 3:
            st.markdown(f'<div class="note">This plan reports in only {len(pf)} '
                        f'period(s), so its charts show a short line.</div>',
                        unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Assets")
            f = go.Figure(go.Scatter(x=pf["t"], y=pf["assets"], fill="tozeroy",
                                     mode="lines+markers" if len(pf) < 6 else "lines",
                                     line=dict(color=GREEN, width=2),
                                     fillcolor="rgba(58,137,22,.12)",
                                     customdata=[usd(v) for v in pf["assets"]],
                                     hovertemplate="%{x|%Y - Q%q}<br>%{customdata}<extra></extra>"))
            money_ticks(f, "yaxis", pf["assets"])
            st.plotly_chart(fig(f, 300), **PLOT)
        with c2:
            st.markdown("#### Accounts")
            f = go.Figure(go.Scatter(x=pf["t"], y=pf["accounts"],
                                     mode="lines+markers" if len(pf) < 6 else "lines",
                                     line=dict(color=STEEL, width=2),
                                     hovertemplate="%{x|%Y - Q%q}<br>%{y:,.0f}<extra></extra>"))
            st.plotly_chart(fig(f, 300), **PLOT)

        hist = pf[["quarter", "assets", "accounts"]].copy()
        hist["avg"] = pd.Series(
            [ratio(a, c) for a, c in zip(hist["assets"], hist["accounts"])],
            index=hist.index).round(0)
        st.dataframe(hist.iloc[::-1], hide_index=True, width="stretch", height=280,
                     column_config={
                         "quarter": "Period",
                         "assets": st.column_config.NumberColumn("Assets", format="dollar"),
                         "accounts": st.column_config.NumberColumn("Accounts", format="localized"),
                         "avg": st.column_config.NumberColumn("Avg balance ($)", format="localized")})
        st.download_button("Download this plan's history",
                           hist.to_csv(index=False).encode(),
                           file_name=f"{re.sub(r'[^A-Za-z0-9]+', '_', plan)}.csv",
                           mime="text/csv")

        st.markdown('<div class="note">Plan-level views start at 2009Q4. Before that '
                    'the record reports one combined line per state instead of '
                    'naming individual plans.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# WITHHELD FROM THE PORTAL
#
# The Compare and Movement tabs are held back for now. The working code is
# kept verbatim below so it can be restored without being rebuilt. To bring
# either one back: add its label to the st.tabs([...]) list, unindent the
# block out of this string, and renumber its tabs[n] index. Nothing else
# about it needs to change.
# ══════════════════════════════════════════════════════════════════════════
WITHHELD_COMPARE_AND_MOVEMENT = '''
# ────────────────────────── Compare ──────────────────────────
with tabs[3]:
    c1, c2, c3 = st.columns(3)
    with c1:
        level = st.radio("Compare", ["States", "Plans"], horizontal=True)
    with c2:
        cm = st.radio("Metric", ["Assets", "Accounts", "Average balance"],
                      horizontal=True)
    with c3:
        idx = st.toggle("Index each line to 100 at its first period")
    col = "state" if level == "States" else "plan"
    src_df = df if level == "States" else df[df["plan_level"]]
    opts = sorted(src_df[col].unique())
    default = ([o for o in opts if o in set(cur[col])][:2]) or opts[:2]
    picks = st.multiselect(f"Choose up to 6 {level.lower()}", opts,
                           default=default, max_selections=6)
    if level == "Plans":
        st.markdown('<div class="note">Plans are comparable from 2009Q4, the '
                    'point where the record starts naming them individually.</div>',
                    unsafe_allow_html=True)
    if picks:
        f = go.Figure()
        for name in picks:
            g = (src_df[src_df[col] == name].groupby("t", as_index=False)
                 .agg(assets=("assets", "sum"), accounts=("accounts", "sum")))
            g["avg"] = g["assets"] / g["accounts"].replace(0, np.nan)
            y = g[{"Assets": "assets", "Accounts": "accounts",
                   "Average balance": "avg"}[cm]]
            if idx and len(y) and y.iloc[0]:
                y = y / y.iloc[0] * 100
            f.add_scatter(x=g["t"], y=y, name=name, mode="lines",
                          hovertemplate="%{x|%Y - Q%q}<br>%{y:,.0f}<extra>"
                                        + name + "</extra>")
        if idx:
            f.add_hline(y=100, line_dash="dot", line_color=STEEL)
        st.plotly_chart(fig(f, 440), **PLOT)
        if idx:
            st.markdown('<div class="note">Every line now starts at 100 at its own '
                        'first period, so this compares growth paths, not size. A '
                        'line at 200 has doubled.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="note">These are raw totals, so bigger plans '
                        'sit higher. Turn on indexing above to compare how fast '
                        'each one grew instead.</div>', unsafe_allow_html=True)

# ────────────────────────── Movement ──────────────────────────
with tabs[4]:
    st.markdown('<div class="note">Where the money actually moved between two '
                'points in time.</div>', unsafe_allow_html=True)
    horizon = st.radio("Change over", ["One period", "One year"], horizontal=True)
    base_p = prev_p if horizon == "One period" else yoy_p

    if base_p is None:
        st.info("The record holds no comparison period here. Move the slider "
                "forward.")
    else:
        b = df[df["period"] == base_p]
        blbl = qlabel(base_p)
        m = (cur.groupby(["state", "plan"], as_index=False)
             .agg(assets=("assets", "sum"), accounts=("accounts", "sum"))
             .merge(b.groupby(["state", "plan"], as_index=False)
                    .agg(a0=("assets", "sum"), c0=("accounts", "sum")),
                    on=["state", "plan"]))
        # Dollar change is the honest unit at network scale. A percentage is
        # only meaningful next to the size it applies to.
        m["d_assets"] = m["assets"] - m["a0"]
        m["d_accounts"] = m["accounts"] - m["c0"]
        m["assets_chg"] = [growth(a, x) for a, x in zip(m["assets"], m["a0"])]
        m["accounts_chg"] = [growth(c, x) for c, x in zip(m["accounts"], m["c0"])]
        m = m.dropna(subset=["assets_chg"])

        net = m["d_assets"].sum()
        net_acct = m["d_accounts"].sum()
        gain, lose = m[m["d_assets"] > 0], m[m["d_assets"] < 0]
        top5 = m.nlargest(5, "d_assets")["d_assets"].sum()
        conc = ratio(top5, net)

        verb = "added" if net >= 0 else "lost"
        line = (f"From {blbl} to {q_sel} the network {verb} "
                f"<b>{usd(abs(net))}</b> in assets and "
                f"<b>{num(abs(net_acct))}</b> accounts. "
                f"{len(gain)} plans gained and {len(lose)} lost ground.")
        if net > 0 and not pd.isna(conc) and conc > 0:
            line += (f" The five biggest movers account for "
                     f"{pct(conc, signed=False)} of the change.")
        st.markdown(f'<div class="callout">{line}</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### The twelve biggest movers, in dollars")
            mv = m.reindex(m["d_assets"].abs().sort_values().index).tail(12)
            f = go.Figure(go.Bar(
                x=mv["d_assets"], y=mv["plan"].str.slice(0, 34), orientation="h",
                marker_color=[GREEN if v >= 0 else RED for v in mv["d_assets"]],
                customdata=np.stack([mv["assets"], mv["assets_chg"]], axis=-1),
                hovertemplate=("%{y}<br>Change %{x:$,.0f}"
                               "<br>Now holds %{customdata[0]:$,.0f}"
                               "<br>That is %{customdata[1]:+.1%}<extra></extra>")))
            f.add_vline(x=0, line_color=STEEL, line_width=1)
            f.update_yaxes(tickfont=dict(size=10))
            money_ticks(f, "xaxis", list(mv["d_assets"]) + [-x for x in mv["d_assets"]])
            st.plotly_chart(fig(f, 380), **PLOT)
            st.markdown('<div class="note">Green added assets, red lost them. '
                        'This is the chart that answers where the money went.</div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown("#### Every plan, sized by what it holds")
            size = (m["assets"] / m["assets"].max()) ** 0.5 * 38 + 5
            f = go.Figure(go.Scatter(
                x=m["assets_chg"], y=m["accounts_chg"], mode="markers",
                text=m["plan"],
                marker=dict(size=size, color=STEEL, opacity=.55,
                            line=dict(color="white", width=.5)),
                customdata=np.stack([m["assets"], m["d_assets"]], axis=-1),
                hovertemplate=("<b>%{text}</b><br>Assets %{x:+.1%}"
                               "<br>Accounts %{y:+.1%}"
                               "<br>Holds %{customdata[0]:$,.0f}"
                               "<br>Change %{customdata[1]:$,.0f}<extra></extra>")))
            f.add_vline(x=0, line_color=MIST)
            f.add_hline(y=0, line_color=MIST)
            f.update_xaxes(tickformat="+.0%", title="Asset change")
            f.update_yaxes(tickformat="+.0%", title="Account change")
            st.plotly_chart(fig(f, 380), **PLOT)
            st.markdown('<div class="note">Each bubble is a plan, sized by the '
                        'assets it holds. Big percentage swings sit on the small '
                        'bubbles, which is why percentages alone mislead.</div>',
                        unsafe_allow_html=True)

        st.markdown("#### Every plan, ordered by dollars gained or lost")
        show = m.sort_values("d_assets", ascending=False)[
            ["state", "plan", "assets", "d_assets", "assets_chg",
             "accounts", "d_accounts"]].copy()
        show["assets_chg"] *= 100
        st.dataframe(
            show, hide_index=True, width="stretch", height=340,
            column_config={
                "state": "State", "plan": "Plan",
                "assets": st.column_config.NumberColumn("Assets", format="dollar"),
                "d_assets": st.column_config.NumberColumn("Change", format="dollar"),
                "assets_chg": st.column_config.NumberColumn("Change (%)", format="%.1f%%"),
                "accounts": st.column_config.NumberColumn("Accounts", format="localized"),
                "d_accounts": st.column_config.NumberColumn("Accounts change", format="localized")})
        st.markdown('<div class="note">Sorted by dollars, not percent. A small '
                    'plan can post a large percentage on very little money, so '
                    'read the two columns together.</div>', unsafe_allow_html=True)
'''

# ────────────────────────── Data ──────────────────────────
with tabs[3]:
    st.markdown('<div class="note">The record itself. Filter it, read it, take it '
                'with you as a CSV or Excel file.</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        f_s = st.multiselect("States", sorted(df["state"].unique()))
    with c2:
        f_q = st.multiselect("Periods", LABELS)
    with c3:
        # Only offer real plan names here, not the pre-2009 aggregate rows that
        # carry the state name, so a state cannot appear as a plan. Order by
        # state so plans group under their state rather than by first letter.
        _pe = df[df["plan_level"]]
        _ps = _pe.groupby("plan")["state"].last()
        f_p = st.multiselect(
            "Plans",
            sorted(_pe["plan"].unique(), key=lambda p: (_ps.get(p, ""), p)))
    v = df.copy()
    if f_s: v = v[v["state"].isin(f_s)]
    if f_q: v = v[v["period"].isin([qparse(q) for q in f_q])]
    if f_p: v = v[v["plan"].isin(f_p)]
    v = v.copy()
    v["Period"] = v["period"].map(qlabel)
    out = v[["Period", "state", "plan", "type", "channel", "accounts", "assets"]]

    st.markdown(f'<div class="note">{len(out):,} rows match.</div>',
                unsafe_allow_html=True)
    st.dataframe(out, hide_index=True, width="stretch", height=330,
                 column_config={
                     "Period": "Period", "state": "State", "plan": "Plan",
                     "type": "Type", "channel": "Channel",
                     "assets": st.column_config.NumberColumn(
                         "Volume of Assets", format="dollar"),
                     "accounts": st.column_config.NumberColumn(
                         "Number of Accounts", format="localized")})

    d1, d2 = st.columns(2)
    with d1:
        st.download_button("Download CSV", out.to_csv(index=False).encode(),
                           file_name="529_assets_accounts.csv", mime="text/csv")
    with d2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            out.to_excel(w, index=False, sheet_name="Assets & Accounts")
        st.download_button("Download Excel", buf.getvalue(),
                           file_name="529_assets_accounts.xlsx",
                           mime="application/vnd.openxmlformats-officedocument"
                                ".spreadsheetml.sheet")

# ══════════════════════════════════════════════════════════════════════════
# WITHHELD FROM THE PORTAL
#
# The notes section of the Data tab is held back for now. Kept verbatim so
# the provenance write-up and the non-reporting-rows table can be restored
# without being rewritten. To bring it back, unindent this block out of the
# string and place it at the end of the Data tab.
# ══════════════════════════════════════════════════════════════════════════
WITHHELD_DATA_NOTES = '''
    st.divider()
    st.markdown("#### Notes on the record")
    nr = full[~full["reporting"]][["quarter", "state", "plan", "note"]]
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f"""
**Coverage.** {len(LABELS)} reporting periods, {LABELS[0]} to {LABELS[-1]}.
Reporting runs quarterly from 2021 and is annual or semiannual before that, so
year over year views appear only where the same quarter exists a year earlier.

**2022.** 2022 was the one gap in the record. It is now filled from the four
quarterly workbooks and reconciles to their national totals rows exactly, in
both assets and accounts, in all four quarters. Plan names and states came from
the 2021Q4 and 2023Q1 rosters, so no new naming was introduced.

**Two items to resolve.** All 111 plans report identical figures in 2022Q4 and
2023Q1, the only such pair anywhere in the record. The 12/31/2022 workbook
carries an internal title reading "Reporting date: March 31," so the year end
file was likely loaded a second time as Q1 2023. Separately, Alabama PACT
reports $76.1M in 2022Q1 against $232M to $257M in the other three quarters
while accounts barely move. Both are kept as reported. Nothing was silently
corrected.

**2026Q1 and the transposed rows.** The published website file for 3/31/2026
prints ten rows under the wrong plan names: Nevada (Vanguard and Wealthfront),
South Carolina (Future Scholar Advisor and Direct), Virginia (Invest529 and
Prepaid529), and Texas (a four way rotation across all four plans). The survey
submissions and the prior quarter agree with each other in every case, so this
dashboard loads the survey figures. Each corrected row carries a note. National
totals are unaffected, since every swap sits inside one state, and 2026Q1 still
reconciles to the published totals row: accounts to the unit, assets to three
cents of the source's own rounding.

**One plan, two spellings.** The source spells 15 plans two ways, changing
punctuation or casing partway through. Virginia CollegeAmerica also appears as
"Virginia - CollegeAmerica." Left alone, one plan reads as two and its history
breaks in half. This dashboard merges them on a punctuation-blind key and shows
the most recent spelling, naming the alias on the Plans tab. No two spellings
ever report in the same period, so nothing double counts, and the loader asserts
that on every run.

**Two eras in one record.** Through 2008Q4 the data arrives as one combined
line per state, labelled with the state name rather than a plan name. From
2009Q4 it names individual plans. National and state totals are sound across
the whole record, because a sum is a sum. Plan-level views start at 2009Q4,
and the Plans and Compare tabs enforce that. This also means a single plan can
appear under more than one name over the years: Kansas's Schwab plan, for
instance, is recorded under three.

**Plan type** is inferred from the plan name, not reported. Treat it as a
convenience, not a field of record.
""")
    with c2:
        st.markdown("##### Rows with no figures")
        st.markdown(f'<div class="note">{len(nr)} rows carry a note instead of '
                    f'numbers. Every total here excludes them.</div>',
                    unsafe_allow_html=True)
        st.dataframe(nr, hide_index=True, width="stretch", height=300,
                     column_config={"quarter": "Period", "state": "State",
                                    "plan": "Plan", "note": "Note"})
'''

# ────────────────────────── Infographic ──────────────────────────
with tabs[4]:
    st.markdown('<div class="note">Generates the print-ready period '
                'infographic straight from this record, so the published sheet '
                'and the dashboard can never disagree.</div>',
                unsafe_allow_html=True)

    # The infographic is a national publication covering savings and prepaid
    # together, so it always reads the unfiltered record regardless of the
    # sidebar plan type. Anything else would publish a partial total.
    ig_src = full[full["reporting"]].copy()

    c1, c2 = st.columns([1, 2])
    with c1:
        ed = st.selectbox("Edition", LABELS[::-1], index=0,
                          help="Which reporting period the sheet is for.")
        ed_p = qparse(ed)
        earliest = int(min(p.year for p in QS))
        if ed_p.year <= earliest:
            st.markdown('<div class="note">This edition is the earliest on '
                        'record, so there is no prior year to chart against. '
                        'Pick a later edition.</div>', unsafe_allow_html=True)
            first_year = earliest
        else:
            first_year = st.number_input(
                "Chart starts in", min_value=earliest,
                max_value=ed_p.year - 1,
                value=min(2012, ed_p.year - 1), step=1,
                help="The published series starts in 2012, the first year "
                     "with a complete account count.")
    if type_sel != "Total":
        with c2:
            st.markdown(f'<div class="callout">The sidebar is filtered to '
                        f'{type_sel}, but the infographic always uses the '
                        f'total of savings and prepaid, matching its own '
                        f'footnote.</div>', unsafe_allow_html=True)

    try:
        spec = ig_render.derive_spec(ig_src, ed_p, first_year=int(first_year))
    except Exception as exc:
        st.error(f"Could not build the sheet for {ed}: {exc}")
        spec = None

    if spec:
        a_now = ig_src[ig_src["period"] == ed_p]["assets"].sum()
        c_now = ig_src[ig_src["period"] == ed_p]["accounts"].sum()
        st.markdown(f"""
        <div class="ledger">
          <div class="cell"><div class="v">{usd(a_now)}</div><div class="k">Total assets</div></div>
          <div class="cell"><div class="v">{num(c_now)}</div><div class="k">Open accounts</div></div>
          <div class="cell"><div class="v">{spec['average_account']['to_value']}</div>
            <div class="k">Average balance (derived)</div></div>
          <div class="cell"><div class="v">{spec['footer']['reporting'].split()[0]}</div>
            <div class="k">Plans reporting</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("##### Wording")
        headline = st.text_input("Headline", spec["headline"])
        hl = st.text_input(
            "Phrase set in gold", spec["headline_highlight"],
            help="Must appear in the headline word for word, or it is ignored.")
        deck = st.text_area("Deck", spec["deck"], height=90)
        spec["headline"], spec["headline_highlight"], spec["deck"] = headline, hl, deck
        if hl and hl not in headline:
            st.markdown('<div class="note">That phrase is not in the headline, '
                        'so nothing will be highlighted.</div>',
                        unsafe_allow_html=True)

        with st.expander("What goes on the sheet"):
            st.markdown(
                f"**Series** {spec['assets']['series'][0]['year']} to "
                f"{spec['assets']['series'][-1]['year']}, "
                f"{len(spec['assets']['series'])} points, taken from "
                f"Q{ed_p.quarter} of each year so the comparison stays like "
                f"for like.\n\n"
                f"**Average balance** is derived, assets divided by accounts, "
                f"and is labelled that way on the sheet. It is never entered "
                f"by hand.\n\n"
                f"**Marked on the chart**: "
                + (", ".join(a["text"] for a in spec["assets"]["annotations"])
                   or "no single-year fall large enough to mark") + ".")
            st.json({k: v for k, v in spec.items() if not k.startswith("_")},
                    expanded=False)

        if st.button("Generate the sheet", type="primary"):
            with st.spinner("Rendering..."):
                try:
                    ok, note = ig_render.ensure_chromium()
                    out = ig_render.render(spec)
                except Exception as exc:
                    ok, note, out = False, str(exc)[:300], None

            if out and out["pdf"]:
                st.session_state["ig_out"] = out
                st.session_state["ig_stem"] = spec["file_stem"]
            elif out:
                st.session_state["ig_out"] = out
                st.session_state["ig_stem"] = spec["file_stem"]
                st.warning(
                    "The PDF needs a headless browser, which is not available "
                    "here, so only the HTML was produced. Open the HTML and "
                    "print to PDF, or see the deployment note in the README to "
                    "enable rendering on the server. "
                    f"({note})")

        out = st.session_state.get("ig_out")
        if out:
            stem = st.session_state.get("ig_stem", "529-Graphic")
            d1, d2, d3 = st.columns(3)
            with d1:
                st.download_button(
                    "Download PDF", out["pdf"] or b"", f"{stem}.pdf",
                    "application/pdf", disabled=out["pdf"] is None)
            with d2:
                st.download_button(
                    "Download PNG", out["png"] or b"", f"{stem}.png",
                    "image/png", disabled=out["png"] is None)
            with d3:
                st.download_button("Download HTML", out["html"],
                                   f"{stem}.html", "text/html")
            if out["png"]:
                st.image(out["png"], caption=f"{stem} preview",
                         width="stretch")

        st.markdown('<div class="note">Both brand marks are traced from the '
                    'official logos: the 529 Network cap at 96.6% pixel overlap '
                    'and the NAST mark at 94.4%. Each inherits currentColor so '
                    'the rail renders them correctly.</div>',
                    unsafe_allow_html=True)


st.markdown(f'<div style="border-top:1px solid {MIST};margin-top:1.6rem;'
            f'padding-top:.6rem" class="note">The 529 Network · Data submitted by '
            f'states and consolidated by The 529 Network · Record through '
            f'{LABELS[-1]}</div>', unsafe_allow_html=True)
