"""
Assets & Accounts | The 529 Network
Four reported fields: state, plan name, assets, open accounts.
Everything on screen derives from those four. No fund manager names.

Data: data/529_data.csv
  Year, Period, Date, State, PlanName, Accounts, AUM, Note
"""

from __future__ import annotations

import io
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ────────────────────────── brand ──────────────────────────
GREEN, DARK, STEEL, MIST = "#3A8916", "#2B650B", "#708686", "#C6DDBB"
INK, PAPER, AMBER, RED = "#1C2420", "#FAFBF8", "#C98A2B", "#A34A2A"

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
                   page_icon="assets/logo.png", layout="wide")

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
    d["t"] = d["period"].dt.to_timestamp(how="end")
    d["state"] = d["state"].str.strip()
    d["plan"] = d["plan"].str.strip()
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
    d["note"] = d["note"].fillna("")
    d["reporting"] = d["assets"].notna()
    # Before 2009Q4 the record is one aggregate row per state, labelled with the
    # state name rather than the plan name. From 2009Q4 it names real plans.
    # National and state totals hold across the whole record; plan-level views
    # only mean anything after the split.
    d["plan_level"] = d["period"] >= pd.Period("2009Q4", freq="Q")
    return d.sort_values(["period", "state", "plan"]).reset_index(drop=True)


PLAN_ERA = pd.Period("2009Q4", freq="Q")


full = load()
df = full[full["reporting"]].copy()
QS = sorted(df["period"].unique())
LABELS = [f"{p.year}Q{p.quarter}" for p in QS]

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
    return f


# ────────────────────────── sidebar ──────────────────────────
with st.sidebar:
    st.image("assets/logo.png", width="stretch")
    st.markdown("### Assets & Accounts")
    with st.expander("New to 529 data? Start here"):
        st.markdown("""
A **529 plan** is a state-sponsored account that helps families save for
education. This dashboard tracks two numbers for every plan in the country:

**Assets** are the total dollars families hold in a plan. This rises when
families add money or markets go up, and falls when they withdraw for school
or markets go down.

**Open accounts** count how many accounts exist. This only moves when families
open or close accounts, so it is the cleaner read on participation.

**Average balance** is simply assets divided by accounts.

**Savings vs prepaid**: savings plans invest contributions in markets. Prepaid
plans let families lock in tuition at today's prices.

Pick any reporting period with the slider below. Every chart updates.
""")
    q_sel = st.select_slider("Reporting period", options=LABELS, value=LABELS[-1])
    p_sel = pd.Period(q_sel, freq="Q")
    st.markdown(
        f'<div class="note">Data submitted by states and consolidated by '
        f'The 529 Network. {len(LABELS)} reporting periods, {LABELS[0]} to '
        f'{LABELS[-1]}. Reporting runs quarterly from 2021 and is sparser before '
        f'that, so the timeline is not evenly spaced.</div>',
        unsafe_allow_html=True)

cur = df[df["period"] == p_sel]
i = QS.index(p_sel)
prev_p = QS[i - 1] if i else None
yoy_p = (p_sel - 4) if (p_sel - 4) in QS else None
prev = df[df["period"] == prev_p] if prev_p is not None else df.iloc[:0]
yoy = df[df["period"] == yoy_p] if yoy_p is not None else df.iloc[:0]
prior_lbl = f"{prev_p.year}Q{prev_p.quarter}" if prev_p is not None else "n/a"

# ────────────────────────── header ──────────────────────────
st.markdown('<div class="eyebrow">Member dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="pagetitle">Assets & Accounts</div>', unsafe_allow_html=True)
st.markdown(f'<div class="subtitle">Total assets and open accounts for every '
            f'529 plan on record. Showing {q_sel}.</div>', unsafe_allow_html=True)

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
  <div class="cell"><div class="v">{usd(A)}</div><div class="k">Total assets</div>
    <div class="d">{dlt(growth(A, A0))} vs {prior_lbl} &nbsp;·&nbsp; {dlt(growth(A, AY))} YoY</div></div>
  <div class="cell"><div class="v">{num(C)}</div><div class="k">Open accounts</div>
    <div class="d">{dlt(growth(C, C0))} vs {prior_lbl}</div></div>
  <div class="cell"><div class="v">{usd(ratio(A, C))}</div><div class="k">Average balance</div>
    <div class="d">{dlt(growth(ratio(A, C), ratio(A0, C0)))} vs {prior_lbl}</div></div>
  <div class="cell"><div class="v">{cur["plan"].nunique()}</div><div class="k">Plans reporting</div>
    <div class="d"><span class="flat">{n_states} states{dc_txt}</span></div></div>
</div>
""", unsafe_allow_html=True)

def tell_the_story() -> str:
    """One accurate paragraph about the selected period, written from the data."""
    parts = [f"At the end of {q_sel}, families held {usd(A)} across "
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
    big = cur.groupby("state")["assets"].sum()
    top_state = big.idxmax()
    parts.append(f"{top_state} holds the most, {usd(big.max())}, about "
                 f"{pct(ratio(big.max(), A), signed=False)} of the national "
                 f"total.")
    return " ".join(parts)


st.markdown(f'<div class="callout">{tell_the_story()}</div>',
            unsafe_allow_html=True)

tabs = st.tabs(["National", "States", "Plans", "Compare", "Movement",
                "Data & Notes"])


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
        st.markdown("#### Total assets")
        f = go.Figure(go.Scatter(x=n["t"], y=n["assets"], fill="tozeroy",
                                 line=dict(color=GREEN, width=2),
                                 fillcolor="rgba(58,137,22,.12)",
                                 hovertemplate="%{x|%Y Q%q}<br>%{customdata}<extra></extra>",
                                 customdata=[usd(v) for v in n["assets"]]))
        money_ticks(f, "yaxis", n["assets"])
        st.plotly_chart(fig(f), **PLOT)
    with c2:
        st.markdown("#### Open accounts")
        f = go.Figure(go.Scatter(x=n["t"], y=n["accounts"],
                                 line=dict(color=STEEL, width=2),
                                 hovertemplate="%{x|%Y Q%q}<br>%{y:,.0f}<extra></extra>"))
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
        g["t"] = g["period"].dt.to_timestamp(how="end")
        f = go.Figure(go.Bar(x=g["t"], y=g["yoy"],
                             marker_color=[GREEN if v >= 0 else RED for v in g["yoy"]],
                             hovertemplate="%{x|%Y Q%q}<br>%{y:+.1%}<extra></extra>"))
        f.update_yaxes(tickformat="+.0%")
        st.plotly_chart(fig(f, 300), **PLOT)
        st.markdown('<div class="note">Green bars mean savings grew compared with '
                    'the same quarter a year earlier. Red bars mean they shrank. '
                    'Bars appear only where the record holds that earlier '
                    'quarter.</div>', unsafe_allow_html=True)
    with c4:
        st.markdown("#### Average account balance")
        f = go.Figure(go.Scatter(x=n["t"], y=n["avg"], line=dict(color=DARK, width=2),
                                 hovertemplate="%{x|%Y Q%q}<br>%{y:$,.0f}<extra></extra>"))
        st.plotly_chart(fig(f, 300), **PLOT)
        st.markdown('<div class="note">What the typical dollar amount per account '
                    'looks like: total assets divided by total accounts.</div>',
                    unsafe_allow_html=True)

    c5, c6 = st.columns(2)
    with c5:
        st.markdown("#### Savings and prepaid assets")
        tt = (df[df["Year"] >= 2003].groupby(["t", "type"])["assets"].sum()
              .unstack().reindex(columns=["Savings", "Prepaid"]).fillna(0))
        f = go.Figure()
        f.add_scatter(x=tt.index, y=tt["Savings"], name="Savings", stackgroup="a",
                      line=dict(color=GREEN, width=1),
                      customdata=[usd(v) for v in tt["Savings"]],
                      hovertemplate="%{x|%Y Q%q}<br>%{customdata}<extra>Savings</extra>")
        f.add_scatter(x=tt.index, y=tt["Prepaid"], name="Prepaid", stackgroup="a",
                      line=dict(color=AMBER, width=1),
                      customdata=[usd(v) for v in tt["Prepaid"]],
                      hovertemplate="%{x|%Y Q%q}<br>%{customdata}<extra>Prepaid</extra>")
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
        share = ratio(cur.groupby("plan")["assets"].sum().nlargest(10).sum(), A)
        st.markdown(f'<div class="note">The ten largest plans hold '
                    f'{pct(share, signed=False)} of all assets. Amber marks '
                    f'prepaid.</div>', unsafe_allow_html=True)

# ────────────────────────── States ──────────────────────────
with tabs[1]:
    st.markdown('<div class="note">Darker green means more. Hover any state for '
                'its numbers, or scroll down to look at one state closely.</div>',
                unsafe_allow_html=True)
    st.write("")
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
            colorscale=[[0, "#EFF5EA"], [.5, MIST], [1, DARK]],
            marker_line_color="white", colorbar=dict(thickness=10, len=.7),
            customdata=np.stack([mapped["state"], mapped["assets"],
                                 mapped["accounts"], mapped["avg"],
                                 mapped["plans"]], axis=-1),
            hovertemplate=("<b>%{customdata[0]}</b><br>Assets %{customdata[1]:$,.0f}"
                           "<br>Accounts %{customdata[2]:,.0f}"
                           "<br>Avg balance %{customdata[3]:$,.0f}"
                           "<br>Plans %{customdata[4]}<extra></extra>")))
        f.update_geos(scope="usa", bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig(f, 420), **PLOT)

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
    state = st.selectbox("Look at one state", sorted(df["state"].unique()))
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
      <div class="cell"><div class="v">{pct(ratio(sa, A), signed=False)}</div>
        <div class="k">Share of national assets</div></div>
    </div>""", unsafe_allow_html=True)

    g = (sd.groupby("t", as_index=False)
         .agg(assets=("assets", "sum"), accounts=("accounts", "sum")))
    st.markdown(f"#### {state}: assets and accounts")
    f = go.Figure()
    f.add_scatter(x=g["t"], y=g["assets"], name="Assets",
                  line=dict(color=GREEN, width=2),
                  customdata=[usd(v) for v in g["assets"]],
                  hovertemplate="%{x|%Y Q%q}<br>%{customdata}<extra>Assets</extra>")
    f.add_scatter(x=g["t"], y=g["accounts"], name="Accounts", yaxis="y2",
                  line=dict(color=STEEL, width=2, dash="dot"),
                  hovertemplate="%{x|%Y Q%q}<br>%{y:,.0f}<extra>Accounts</extra>")
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

    show_retired = st.toggle(
        f"Include the {len(retired)} plans that no longer report",
        help="Plans that closed, merged, or were renamed. Their history stops "
             "on their last reporting period.")
    universe = sorted(current) + (retired if show_retired else [])
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
            f'record runs from {p0.year}Q{p0.quarter} to '
            f'{last_p.year}Q{last_p.quarter}, and the figures below are its '
            f'final reported quarter.</div>', unsafe_allow_html=True)
        pc = pf[pf["period"] == last_p]
        shown = f"{last_p.year}Q{last_p.quarter}"
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
      <div class="cell"><div class="v">{p0.year}Q{p0.quarter}</div>
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
                                 hovertemplate="%{x|%Y Q%q}<br>%{customdata}<extra></extra>"))
        money_ticks(f, "yaxis", pf["assets"])
        st.plotly_chart(fig(f, 300), **PLOT)
    with c2:
        st.markdown("#### Accounts")
        f = go.Figure(go.Scatter(x=pf["t"], y=pf["accounts"],
                                 mode="lines+markers" if len(pf) < 6 else "lines",
                                 line=dict(color=STEEL, width=2),
                                 hovertemplate="%{x|%Y Q%q}<br>%{y:,.0f}<extra></extra>"))
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
                          hovertemplate="%{x|%Y Q%q}<br>%{y:,.0f}<extra>"
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
        blbl = f"{base_p.year}Q{base_p.quarter}"
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

# ────────────────────────── Data & Notes ──────────────────────────
with tabs[5]:
    st.markdown('<div class="note">The record itself. Filter it, read it, take it '
                'with you as a CSV or Excel file.</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        f_s = st.multiselect("States", sorted(df["state"].unique()))
    with c2:
        f_q = st.multiselect("Periods", LABELS)
    with c3:
        f_p = st.multiselect("Plans", sorted(df["plan"].unique()))
    v = df.copy()
    if f_s: v = v[v["state"].isin(f_s)]
    if f_q: v = v[v["quarter"].isin(f_q)]
    if f_p: v = v[v["plan"].isin(f_p)]
    out = v[["quarter", "state", "plan", "type", "assets", "accounts"]]

    st.markdown(f'<div class="note">{len(out):,} rows match.</div>',
                unsafe_allow_html=True)
    st.dataframe(out, hide_index=True, width="stretch", height=330,
                 column_config={
                     "quarter": "Period", "state": "State", "plan": "Plan",
                     "type": "Type",
                     "assets": st.column_config.NumberColumn("Assets", format="dollar"),
                     "accounts": st.column_config.NumberColumn("Accounts", format="localized")})

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

st.markdown(f'<div style="border-top:1px solid {MIST};margin-top:1.6rem;'
            f'padding-top:.6rem" class="note">The 529 Network · Data submitted by '
            f'states and consolidated by The 529 Network · Record through '
            f'{LABELS[-1]}</div>', unsafe_allow_html=True)
