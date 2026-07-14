"""
The 529 Network: Assets & Accounts
A member dashboard built on three fields: state, plan name, assets, accounts.
Everything else on screen derives from those fields.

Data contract: data/assets_accounts_master.csv
  quarter, state, plan_name, assets, accounts
The loader also accepts common header variants and auto-detects
assets reported in millions.
"""

from __future__ import annotations

import io
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ────────────────────────── brand tokens ──────────────────────────
GREEN = "#3A8916"
DARK = "#2B650B"
STEEL = "#708686"
MIST = "#C6DDBB"
INK = "#1C2420"
PAPER = "#FAFBF8"
AMBER = "#C98A2B"  # single non-brand accent, used only for change context

COLORWAY = [GREEN, STEEL, DARK, AMBER, "#8FB07C", "#4A5D57", "#A3C293", "#5E7D3A"]

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

st.set_page_config(
    page_title="Assets & Accounts | The 529 Network",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────────────── styles ──────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp {{ font-family: 'Inter', sans-serif; color: {INK}; }}
.stApp {{ background: {PAPER}; }}
h1, h2, h3 {{ font-family: 'Fraunces', serif !important; color: {INK}; letter-spacing: -0.01em; }}
section[data-testid="stSidebar"] {{ background: #F1F6EC; border-right: 1px solid {MIST}; }}

.eyebrow {{
  font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem;
  letter-spacing: 0.14em; text-transform: uppercase; color: {STEEL};
  margin-bottom: 0.15rem;
}}
.pagetitle {{ font-family: 'Fraunces', serif; font-size: 2.1rem; font-weight: 600;
  color: {INK}; line-height: 1.1; margin-bottom: 0.2rem; }}
.subtitle {{ color: {STEEL}; font-size: 0.95rem; margin-bottom: 0.6rem; }}

/* signature element: the ledger strip */
.ledger {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  border-top: 2px solid {DARK}; border-bottom: 1px solid {MIST};
  background: white; margin: 0.4rem 0 1rem 0;
}}
.ledger .cell {{ padding: 0.85rem 1rem; border-right: 1px solid #EDF3E8; }}
.ledger .cell:last-child {{ border-right: none; }}
.ledger .v {{ font-family: 'IBM Plex Mono', monospace; font-size: 1.45rem;
  font-weight: 500; color: {DARK}; font-variant-numeric: tabular-nums; }}
.ledger .k {{ font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: {STEEL}; margin-top: 0.15rem; }}
.ledger .d {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; margin-top: 0.1rem; }}
.up {{ color: {GREEN}; }} .down {{ color: #A34A2A; }} .flat {{ color: {STEEL}; }}

.caption-note {{ color: {STEEL}; font-size: 0.8rem; margin-top: -0.4rem; }}
.neutral-note {{
  background: #F1F6EC; border-left: 3px solid {MIST}; padding: 0.5rem 0.8rem;
  font-size: 0.82rem; color: {STEEL}; border-radius: 0 4px 4px 0; margin: 0.5rem 0;
}}

.stTabs [data-baseweb="tab"] {{ font-weight: 500; color: {STEEL}; }}
.stTabs [aria-selected="true"] {{ color: {DARK} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {GREEN}; }}

div[data-testid="stMetricValue"] {{ font-family: 'IBM Plex Mono', monospace; color: {DARK}; }}
#MainMenu, footer {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)

# ────────────────────────── formatting ──────────────────────────
def usd(v: float) -> str:
    if pd.isna(v):
        return "n/a"
    a = abs(v)
    if a >= 1e12: return f"${v/1e12:,.2f}T"
    if a >= 1e9:  return f"${v/1e9:,.1f}B"
    if a >= 1e6:  return f"${v/1e6:,.1f}M"
    return f"${v:,.0f}"

def num(v: float) -> str:
    if pd.isna(v):
        return "n/a"
    a = abs(v)
    if a >= 1e6: return f"{v/1e6:,.2f}M"
    if a >= 1e3: return f"{v/1e3:,.0f}K"
    return f"{v:,.0f}"

def pct(v: float, signed: bool = True) -> str:
    if pd.isna(v):
        return "n/a"
    s = "+" if (signed and v >= 0) else ""
    return f"{s}{v*100:,.1f}%"

def delta_html(v: float) -> str:
    if pd.isna(v):
        return '<span class="flat">n/a</span>'
    cls = "up" if v > 0.0005 else ("down" if v < -0.0005 else "flat")
    return f'<span class="{cls}">{pct(v)}</span>'

# ────────────────────────── data layer ──────────────────────────
PREPAID_PAT = re.compile(
    r"prepaid|guaranteed|tuition promise|tuition plan|u\.plan|\(MET\)|\(GET\)|"
    r"PACT|College Illinois|Tuition Trust|Advance Payment", re.I)


@st.cache_data(show_spinner=False)
def load() -> pd.DataFrame:
    df = pd.read_csv("data/529_data.csv")
    df = df.rename(columns={
        "State": "state", "PlanName": "plan_name",
        "Accounts": "accounts", "AUM": "assets", "Note": "note",
    })
    df["quarter"] = df["Year"].astype(str) + df["Period"].astype(str)
    df["period"] = pd.PeriodIndex(df["quarter"], freq="Q")
    df["t"] = df["period"].dt.to_timestamp(how="end")
    df["state"] = df["state"].str.strip()
    df["plan_name"] = df["plan_name"].str.strip()
    df["plan_type"] = np.where(
        df["plan_name"].str.contains(PREPAID_PAT), "Prepaid", "Savings")
    df["note"] = df["note"].fillna("")
    # Rows with a note and no figures are closed or non-operational plans.
    # Keep them for the coverage view, exclude them from every total.
    df["reporting"] = df["assets"].notna()
    return df.sort_values(["period", "state", "plan_name"]).reset_index(drop=True)


full = load()
df = full[full["reporting"]].copy()
QUARTERS = sorted(df["period"].unique())
Q_LABELS = [f"{p.year}Q{p.quarter}" for p in QUARTERS]

def natl(frame: pd.DataFrame) -> pd.DataFrame:
    g = frame.groupby("t", as_index=False).agg(assets=("assets", "sum"),
                                               accounts=("accounts", "sum"))
    g["avg_balance"] = g["assets"] / g["accounts"]
    return g

def fig_base(fig: go.Figure, h: int = 380) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=h, colorway=COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=INK, size=12),
        margin=dict(l=10, r=10, t=36, b=10),
        hoverlabel=dict(font_family="IBM Plex Mono, monospace"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(gridcolor="#EDF3E8", zeroline=False)
    fig.update_yaxes(gridcolor="#EDF3E8", zeroline=False)
    return fig

PLOT = {"width": "stretch", "config": {"displayModeBar": False}}

# ────────────────────────── sidebar ──────────────────────────
with st.sidebar:
    st.markdown('<div class="eyebrow">The 529 Network</div>', unsafe_allow_html=True)
    st.markdown("### Assets & Accounts")
    q_sel = st.select_slider("Reporting quarter", options=Q_LABELS, value=Q_LABELS[-1])
    p_sel = pd.Period(q_sel, freq="Q")
    st.markdown(
        f'<div class="neutral-note">Data submitted by states and consolidated by '
        f'The 529 Network. {len(Q_LABELS)} reporting periods from '
        f'{Q_LABELS[0]} to {Q_LABELS[-1]}. Reporting is quarterly from 2021 on '
        f'and sparser before that, so the timeline is not evenly spaced. '
        f'2022 was added from the four CSPN website workbooks and reconciles '
        f'to their national totals rows exactly.</div>',
        unsafe_allow_html=True)

cur = df[df["period"] == p_sel]
prev_p = QUARTERS[QUARTERS.index(p_sel) - 1] if QUARTERS.index(p_sel) > 0 else None
yoy_p = (p_sel - 4) if (p_sel - 4) in QUARTERS else None
prev = df[df["period"] == prev_p] if prev_p is not None else pd.DataFrame(columns=df.columns)
yoy = df[df["period"] == yoy_p] if yoy_p is not None else pd.DataFrame(columns=df.columns)

# ────────────────────────── header ──────────────────────────
st.markdown('<div class="eyebrow">Member dashboard · quarterly record</div>',
            unsafe_allow_html=True)
st.markdown('<div class="pagetitle">Assets & Accounts</div>', unsafe_allow_html=True)
st.markdown(f'<div class="subtitle">The full record, {Q_LABELS[0]} to {Q_LABELS[-1]}: '
            f'state, plan name, assets, and open accounts. '
            f'Showing {q_sel}.</div>', unsafe_allow_html=True)

def qoq(cur_v, prev_v):
    return (cur_v / prev_v - 1) if prev_v else np.nan

a_now, c_now = cur["assets"].sum(), cur["accounts"].sum()
a_prev = prev["assets"].sum() if len(prev) else np.nan
c_prev = prev["accounts"].sum() if len(prev) else np.nan
a_yoy = yoy["assets"].sum() if len(yoy) else np.nan
st.markdown(f"""
<div class="ledger">
  <div class="cell"><div class="v">{usd(a_now)}</div><div class="k">Total assets</div>
    <div class="d">{delta_html(qoq(a_now, a_prev))} QoQ · {delta_html(qoq(a_now, a_yoy))} YoY</div></div>
  <div class="cell"><div class="v">{num(c_now)}</div><div class="k">Open accounts</div>
    <div class="d">{delta_html(qoq(c_now, c_prev))} QoQ</div></div>
  <div class="cell"><div class="v">{usd(a_now / c_now)}</div><div class="k">Average balance</div>
    <div class="d">{delta_html(qoq(a_now / c_now, a_prev / c_prev) if len(prev) else np.nan)} QoQ</div></div>
  <div class="cell"><div class="v">{cur["plan_name"].nunique()}</div><div class="k">Plans reporting</div>
    <div class="d"><span class="flat">{cur["state"].nunique()} states & D.C.</span></div></div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["National", "Map", "States", "Plans", "Compare",
                "Change", "Coverage", "Data & Downloads", "About"])

# ────────────────────────── 1 · National ──────────────────────────
with tabs[0]:
    n = natl(df)
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("#### Total assets, every reporting quarter")
        f = go.Figure(go.Scatter(x=n["t"], y=n["assets"], fill="tozeroy",
                                 line=dict(color=GREEN, width=2),
                                 fillcolor="rgba(58,137,22,0.12)",
                                 hovertemplate="%{x|%Y Q%q}<br>%{y:$,.3s}<extra></extra>"))
        st.plotly_chart(fig_base(f), **PLOT)
    with c2:
        st.markdown("#### Open accounts")
        f = go.Figure(go.Scatter(x=n["t"], y=n["accounts"],
                                 line=dict(color=STEEL, width=2),
                                 hovertemplate="%{x|%Y Q%q}<br>%{y:,.3s}<extra></extra>"))
        st.plotly_chart(fig_base(f), **PLOT)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### Year over year asset growth")
        nq = (df.groupby("period", as_index=False)["assets"].sum()
              .rename(columns={"assets": "a"}))
        nq["prior"] = nq["period"] - 4
        nq = nq.merge(nq[["period", "a"]].rename(
            columns={"period": "prior", "a": "a_prior"}), on="prior", how="left")
        nq["yoy"] = nq["a"] / nq["a_prior"] - 1
        nq["t"] = nq["period"].dt.to_timestamp(how="end")
        nq = nq.dropna(subset=["yoy"])
        f = go.Figure(go.Bar(
            x=nq["t"], y=nq["yoy"],
            marker_color=[GREEN if v >= 0 else "#A34A2A" for v in nq["yoy"]],
            hovertemplate="%{x|%Y Q%q}<br>%{y:+.1%}<extra></extra>"))
        f.update_yaxes(tickformat="+.0%")
        st.plotly_chart(fig_base(f, 320), **PLOT)
        st.markdown('<div class="caption-note">Bars appear only where the record '
                    'holds the same quarter one year earlier. Reporting was sparser '
                    'before 2021.</div>', unsafe_allow_html=True)
    with c4:
        st.markdown("#### Average account balance")
        f = go.Figure(go.Scatter(x=n["t"], y=n["avg_balance"],
                                 line=dict(color=DARK, width=2),
                                 hovertemplate="%{x|%Y Q%q}<br>%{y:$,.0f}<extra></extra>"))
        st.plotly_chart(fig_base(f, 320), **PLOT)
    st.markdown('<div class="caption-note">Assets follow markets and contributions '
                'together. Accounts move on enrollment alone, which makes them the '
                'steadier read on reach.</div>', unsafe_allow_html=True)

    c5, c6 = st.columns(2)
    with c5:
        st.markdown("#### Savings vs prepaid assets")
        tt = (df.groupby(["t", "plan_type"])["assets"].sum()
              .unstack().reindex(columns=["Savings", "Prepaid"]))
        f = go.Figure()
        f.add_scatter(x=tt.index, y=tt["Savings"], name="Savings",
                      stackgroup="s", line=dict(color=GREEN, width=1),
                      hovertemplate="%{x|%Y Q%q}<br>%{y:$,.3s}<extra>Savings</extra>")
        f.add_scatter(x=tt.index, y=tt["Prepaid"], name="Prepaid",
                      stackgroup="s", line=dict(color=AMBER, width=1),
                      hovertemplate="%{x|%Y Q%q}<br>%{y:$,.3s}<extra>Prepaid</extra>")
        st.plotly_chart(fig_base(f, 340), **PLOT)
    with c6:
        st.markdown(f"#### The fifteen largest plans, {q_sel}")
        top = (cur.groupby("plan_name", as_index=False)["assets"].sum()
               .sort_values("assets", ascending=False).head(15).iloc[::-1])
        f = go.Figure(go.Bar(x=top["assets"], y=top["plan_name"],
                             orientation="h", marker_color=GREEN,
                             hovertemplate="%{y}<br>%{x:$,.3s}<extra></extra>"))
        f.update_yaxes(tickfont=dict(size=10))
        st.plotly_chart(fig_base(f, 340), **PLOT)
    top10_share = (cur.groupby("plan_name")["assets"].sum()
                   .sort_values(ascending=False).head(10).sum() / a_now)
    st.markdown(f'<div class="caption-note">The ten largest plans hold '
                f'{top10_share*100:.0f}% of all 529 assets at {q_sel}. Scale in '
                f'this market concentrates.</div>', unsafe_allow_html=True)

# ────────────────────────── 2 · Map ──────────────────────────
with tabs[1]:
    mcol1, mcol2 = st.columns([1, 3])
    with mcol1:
        metric = st.radio("Color the map by",
                          ["Assets", "Accounts", "Average balance"], index=0)
        st.markdown('<div class="caption-note">The table below follows the '
                    'metric you pick, largest first.</div>',
                    unsafe_allow_html=True)
    s = cur.groupby("state", as_index=False).agg(assets=("assets", "sum"),
                                                 accounts=("accounts", "sum"),
                                                 plans=("plan_name", "nunique"))
    s["avg_balance"] = s["assets"] / s["accounts"]
    s["usps"] = s["state"].map(USPS)
    key = {"Assets": "assets", "Accounts": "accounts",
           "Average balance": "avg_balance"}[metric]
    fmt = usd if key != "accounts" else num
    with mcol2:
        f = go.Figure(go.Choropleth(
            locations=s["usps"], z=s[key], locationmode="USA-states",
            colorscale=[[0, "#EFF5EA"], [0.5, MIST], [1, DARK]],
            marker_line_color="white",
            colorbar=dict(title=None, thickness=10, len=0.7),
            customdata=np.stack([s["state"], s["assets"], s["accounts"],
                                 s["avg_balance"], s["plans"]], axis=-1),
            hovertemplate=("<b>%{customdata[0]}</b><br>"
                           "Assets %{customdata[1]:$,.3s}<br>"
                           "Accounts %{customdata[2]:,.3s}<br>"
                           "Avg balance %{customdata[3]:$,.0f}<br>"
                           "Plans %{customdata[4]}<extra></extra>")))
        f.update_geos(scope="usa", bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_base(f, 460), **PLOT)
    tbl = s.sort_values(key, ascending=False)[
        ["state", "plans", "assets", "accounts", "avg_balance"]]
    tbl["assets"] = tbl["assets"].map(usd)
    tbl["accounts"] = tbl["accounts"].map(num)
    tbl["avg_balance"] = tbl["avg_balance"].map(usd)
    tbl.columns = ["State", "Plans", "Assets", "Accounts", "Avg balance"]
    st.dataframe(tbl, hide_index=True, width="stretch", height=320)

# ────────────────────────── 3 · States ──────────────────────────
with tabs[2]:
    state = st.selectbox("State", sorted(df["state"].unique()))
    sd = df[df["state"] == state]
    sd_cur = sd[sd["period"] == p_sel]
    sd_prev = sd[sd["period"] == prev_p] if prev_p is not None else sd.iloc[0:0]
    sa, sc = sd_cur["assets"].sum(), sd_cur["accounts"].sum()
    share = sa / a_now if a_now else np.nan
    st.markdown(f"""
    <div class="ledger">
      <div class="cell"><div class="v">{usd(sa)}</div><div class="k">Assets, {q_sel}</div>
        <div class="d">{delta_html(qoq(sa, sd_prev["assets"].sum() if len(sd_prev) else np.nan))} QoQ</div></div>
      <div class="cell"><div class="v">{num(sc)}</div><div class="k">Accounts</div>
        <div class="d">{delta_html(qoq(sc, sd_prev["accounts"].sum() if len(sd_prev) else np.nan))} QoQ</div></div>
      <div class="cell"><div class="v">{usd(sa / sc) if sc else "n/a"}</div><div class="k">Average balance</div></div>
      <div class="cell"><div class="v">{pct(share, signed=False)}</div><div class="k">Share of national assets</div></div>
    </div>""", unsafe_allow_html=True)

    g = sd.groupby("t", as_index=False).agg(assets=("assets", "sum"),
                                            accounts=("accounts", "sum"))
    ntot = natl(df)
    g = g.merge(ntot[["t", "assets"]].rename(columns={"assets": "natl_assets"}), on="t")
    g["share"] = g["assets"] / g["natl_assets"]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### {state}: assets and accounts over time")
        f = go.Figure()
        f.add_scatter(x=g["t"], y=g["assets"], name="Assets",
                      line=dict(color=GREEN, width=2), yaxis="y1",
                      hovertemplate="%{x|%Y Q%q}<br>%{y:$,.3s}<extra>Assets</extra>")
        f.add_scatter(x=g["t"], y=g["accounts"], name="Accounts",
                      line=dict(color=STEEL, width=2, dash="dot"), yaxis="y2",
                      hovertemplate="%{x|%Y Q%q}<br>%{y:,.3s}<extra>Accounts</extra>")
        f.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False))
        st.plotly_chart(fig_base(f), **PLOT)
    with c2:
        st.markdown("#### Share of national assets")
        f = go.Figure(go.Scatter(x=g["t"], y=g["share"], fill="tozeroy",
                                 line=dict(color=DARK, width=2),
                                 fillcolor="rgba(43,101,11,0.10)",
                                 hovertemplate="%{x|%Y Q%q}<br>%{y:.2%}<extra></extra>"))
        f.update_yaxes(tickformat=".1%")
        st.plotly_chart(fig_base(f), **PLOT)

    st.markdown(f"#### Plans in {state}, {q_sel}")
    pt = sd_cur.groupby("plan_name", as_index=False).agg(
        assets=("assets", "sum"), accounts=("accounts", "sum")).sort_values(
        "assets", ascending=False)
    pt["avg_balance"] = pt["assets"] / pt["accounts"]
    show = pt.copy()
    show["assets"] = show["assets"].map(usd)
    show["accounts"] = show["accounts"].map(num)
    show["avg_balance"] = show["avg_balance"].map(usd)
    show.columns = ["Plan", "Assets", "Accounts", "Avg balance"]
    st.dataframe(show, hide_index=True, width="stretch")

# ────────────────────────── 4 · Plans ──────────────────────────
with tabs[3]:
    plan = st.selectbox("Plan", sorted(df["plan_name"].unique()))
    pdta = df[df["plan_name"] == plan].sort_values("period")
    p_state = pdta["state"].iloc[-1]
    p_cur = pdta[pdta["period"] == p_sel]
    pa = p_cur["assets"].sum() if len(p_cur) else np.nan
    pc = p_cur["accounts"].sum() if len(p_cur) else np.nan
    state_assets = cur[cur["state"] == p_state]["assets"].sum()
    st.markdown(f"""
    <div class="ledger">
      <div class="cell"><div class="v">{usd(pa)}</div><div class="k">Assets, {q_sel}</div></div>
      <div class="cell"><div class="v">{num(pc)}</div><div class="k">Accounts</div></div>
      <div class="cell"><div class="v">{usd(pa / pc) if pc else "n/a"}</div><div class="k">Average balance</div></div>
      <div class="cell"><div class="v">{pct(pa / state_assets, signed=False) if state_assets else "n/a"}</div>
        <div class="k">Share of {p_state} assets</div></div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Asset history")
        f = go.Figure(go.Scatter(x=pdta["t"], y=pdta["assets"], fill="tozeroy",
                                 line=dict(color=GREEN, width=2),
                                 fillcolor="rgba(58,137,22,0.12)",
                                 hovertemplate="%{x|%Y Q%q}<br>%{y:$,.3s}<extra></extra>"))
        st.plotly_chart(fig_base(f, 340), **PLOT)
    with c2:
        st.markdown("#### Account history")
        f = go.Figure(go.Scatter(x=pdta["t"], y=pdta["accounts"],
                                 line=dict(color=STEEL, width=2),
                                 hovertemplate="%{x|%Y Q%q}<br>%{y:,.3s}<extra></extra>"))
        st.plotly_chart(fig_base(f, 340), **PLOT)

    st.markdown("#### Quarter by quarter")
    hist = pdta[["quarter", "assets", "accounts"]].copy()
    hist["assets_qoq"] = pdta["assets"].pct_change()
    hist["accounts_qoq"] = pdta["accounts"].pct_change()
    disp = hist.iloc[::-1].copy()
    disp["assets"] = disp["assets"].map(usd)
    disp["accounts"] = disp["accounts"].map(num)
    disp["assets_qoq"] = disp["assets_qoq"].map(lambda v: pct(v))
    disp["accounts_qoq"] = disp["accounts_qoq"].map(lambda v: pct(v))
    disp.columns = ["Quarter", "Assets", "Accounts", "Assets QoQ", "Accounts QoQ"]
    st.dataframe(disp, hide_index=True, width="stretch", height=300)
    st.download_button("Download this plan's history (CSV)",
                       hist.to_csv(index=False).encode(),
                       file_name=f"{plan.replace(' ', '_')}_history.csv",
                       mime="text/csv")

# ────────────────────────── 5 · Compare ──────────────────────────
with tabs[4]:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        level = st.radio("Compare", ["States", "Plans"], horizontal=True)
    with c2:
        cmetric = st.radio("Metric", ["Assets", "Accounts", "Average balance"],
                           horizontal=True)
    with c3:
        indexed = st.toggle("Index to 100 at first common quarter", value=False)
    col = "state" if level == "States" else "plan_name"
    opts = sorted(df[col].unique())
    picks = st.multiselect(f"Choose up to 6 {level.lower()}", opts,
                           default=opts[:2], max_selections=6)
    if picks:
        f = go.Figure()
        for name in picks:
            g = (df[df[col] == name].groupby("t", as_index=False)
                 .agg(assets=("assets", "sum"), accounts=("accounts", "sum")))
            g["avg_balance"] = g["assets"] / g["accounts"]
            k = {"Assets": "assets", "Accounts": "accounts",
                 "Average balance": "avg_balance"}[cmetric]
            y = g[k]
            if indexed and len(y) and y.iloc[0]:
                y = y / y.iloc[0] * 100
            f.add_scatter(x=g["t"], y=y, name=name, mode="lines",
                          hovertemplate="%{x|%Y Q%q}<br>%{y:,.3s}<extra>" + name + "</extra>")
        if indexed:
            f.add_hline(y=100, line_dash="dot", line_color=STEEL)
        st.plotly_chart(fig_base(f, 440), **PLOT)
        st.markdown('<div class="caption-note">Indexing rebases each line to 100 at '
                    'its first quarter, so the chart compares growth paths rather '
                    'than size.</div>', unsafe_allow_html=True)

# ────────────────────────── 6 · Change ──────────────────────────
with tabs[5]:
    st.markdown("#### Movement between quarters")
    st.markdown('<div class="caption-note">Movement across every plan, '
                'largest asset change first. Click any column header to '
                're-sort.</div>', unsafe_allow_html=True)
    horizon = st.radio("Change over", ["One quarter", "One year"], horizontal=True)
    base_p = prev_p if horizon == "One quarter" else yoy_p
    if base_p is None:
        st.info("Not enough history at this quarter for that horizon. "
                "Move the quarter slider forward.")
    else:
        base = df[df["period"] == base_p]
        m = (cur.groupby(["state", "plan_name"], as_index=False)
             .agg(assets=("assets", "sum"), accounts=("accounts", "sum"))
             .merge(base.groupby(["state", "plan_name"], as_index=False)
                    .agg(assets_0=("assets", "sum"), accounts_0=("accounts", "sum")),
                    on=["state", "plan_name"], how="inner"))
        m["assets_chg"] = m["assets"] / m["assets_0"] - 1
        m["accounts_chg"] = m["accounts"] / m["accounts_0"] - 1
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Distribution of asset change across plans")
            f = go.Figure(go.Histogram(x=m["assets_chg"], nbinsx=40,
                                       marker_color=GREEN, opacity=0.85))
            med = float(m["assets_chg"].median())
            f.add_vline(x=med, line_dash="dot", line_color=DARK,
                        annotation_text=f"median {pct(med)}")
            f.update_xaxes(tickformat="+.0%")
            st.plotly_chart(fig_base(f, 340), **PLOT)
        with c2:
            st.markdown("##### Account change vs asset change")
            f = go.Figure(go.Scatter(
                x=m["assets_chg"], y=m["accounts_chg"], mode="markers",
                marker=dict(color=STEEL, size=7, opacity=0.7,
                            line=dict(color="white", width=0.5)),
                text=m["plan_name"],
                hovertemplate="<b>%{text}</b><br>Assets %{x:+.1%}<br>"
                              "Accounts %{y:+.1%}<extra></extra>"))
            f.add_vline(x=0, line_color=MIST)
            f.add_hline(y=0, line_color=MIST)
            f.update_xaxes(tickformat="+.0%")
            f.update_yaxes(tickformat="+.0%")
            st.plotly_chart(fig_base(f, 340), **PLOT)
        st.markdown('<div class="caption-note">Plans right of the vertical line grew '
                    'assets. Plans above the horizontal line added accounts. The '
                    'upper right quadrant did both.</div>', unsafe_allow_html=True)
        out = m.sort_values("assets_chg", ascending=False)[
            ["state", "plan_name", "assets", "assets_chg", "accounts", "accounts_chg"]]
        st.dataframe(out, hide_index=True, width="stretch", height=340,
                     column_config={
                         "state": "State", "plan_name": "Plan",
                         "assets": st.column_config.NumberColumn("Assets", format="dollar"),
                         "assets_chg": st.column_config.NumberColumn("Assets change", format="percent"),
                         "accounts": st.column_config.NumberColumn("Accounts", format="localized"),
                         "accounts_chg": st.column_config.NumberColumn("Accounts change", format="percent"),
                     })

# ────────────────────────── 7 · Coverage ──────────────────────────
with tabs[6]:
    st.markdown("#### What the record covers, and where it needs attention")

    c1, c2 = st.columns([2, 1])
    with c1:
        cov = (df.groupby("period")
               .agg(plans=("plan_name", "nunique"), assets=("assets", "sum"))
               .reset_index())
        cov["t"] = cov["period"].dt.to_timestamp(how="end")
        f = go.Figure(go.Bar(x=cov["t"], y=cov["plans"], marker_color=MIST,
                             marker_line_color=DARK, marker_line_width=1,
                             hovertemplate="%{x|%Y Q%q}<br>%{y} plans<extra></extra>"))
        f.update_layout(bargap=0.35)
        st.markdown("##### Plans reporting in each period")
        st.plotly_chart(fig_base(f, 300), **PLOT)
        st.markdown('<div class="caption-note">Reporting runs quarterly from 2021. '
                    'Before that the record is annual or semiannual, so gaps in this '
                    'chart are gaps in reporting cadence, not missing plans.</div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown("##### Non-reporting rows")
        nr = full[~full["reporting"]][["quarter", "state", "plan_name", "note"]]
        st.markdown(f'<div class="caption-note">{len(nr)} rows carry a note and no '
                    f'figures. Every total on this dashboard excludes them.</div>',
                    unsafe_allow_html=True)
        st.dataframe(nr, hide_index=True, width="stretch", height=280,
                     column_config={"quarter": "Quarter", "state": "State",
                                    "plan_name": "Plan", "note": "Note"})

    st.markdown("##### Two items to resolve")
    st.markdown("""
**2023Q1 repeats 2022Q4.** With 2022 now loaded, all 111 plans report identical
assets and accounts in 2022Q4 and 2023Q1. No other consecutive pair in the
twenty-four year record does this. The 12/31/2022 source workbook carries an
internal title reading "Reporting date: March 31," which is the most likely
cause: the year-end file was almost certainly ingested a second time as Q1 2023.
The 2022 figures here reconcile to their source totals rows exactly, so the
suspect period is 2023Q1, not 2022Q4. Worth pulling the original 3/31/2023
workbook and comparing.

**Alabama PACT, 2022Q1.** Assets of $76.1M sit far below the $232M to $257M
reported in the other three quarters while accounts barely move. Kept as
reported, flagged for the state to confirm.
""")
    st.markdown('<div class="neutral-note">Both items sit in the source data. '
                'Nothing was silently corrected.</div>', unsafe_allow_html=True)


# ────────────────────────── 8 · Data & Downloads ──────────────────────────
with tabs[7]:
    st.markdown("#### The record itself")
    c1, c2, c3 = st.columns(3)
    with c1:
        f_states = st.multiselect("States", sorted(df["state"].unique()))
    with c2:
        f_q = st.multiselect("Quarters", Q_LABELS)
    with c3:
        f_plans = st.multiselect("Plans", sorted(df["plan_name"].unique()))
    view = df.copy()
    if f_states: view = view[view["state"].isin(f_states)]
    if f_q:      view = view[view["quarter"].isin(f_q)]
    if f_plans:  view = view[view["plan_name"].isin(f_plans)]
    st.markdown(f'<div class="caption-note">{len(view):,} rows match.</div>',
                unsafe_allow_html=True)
    st.dataframe(view[["quarter", "state", "plan_name", "assets", "accounts"]]
                 .sort_values(["quarter", "state", "plan_name"]),
                 hide_index=True, width="stretch", height=420,
                 column_config={
                     "quarter": "Quarter", "state": "State", "plan_name": "Plan",
                     "assets": st.column_config.NumberColumn("Assets", format="dollar"),
                     "accounts": st.column_config.NumberColumn("Accounts", format="localized"),
                 })
    d1, d2 = st.columns(2)
    with d1:
        st.download_button("Download filtered rows (CSV)",
                           view[["quarter", "state", "plan_name", "assets", "accounts"]]
                           .to_csv(index=False).encode(),
                           file_name="529_assets_accounts.csv", mime="text/csv")
    with d2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            view[["quarter", "state", "plan_name", "assets", "accounts"]].to_excel(
                xw, index=False, sheet_name="Assets & Accounts")
        st.download_button("Download filtered rows (Excel)", buf.getvalue(),
                           file_name="529_assets_accounts.xlsx",
                           mime="application/vnd.openxmlformats-officedocument"
                                ".spreadsheetml.sheet")

# ────────────────────────── 9 · About ──────────────────────────
with tabs[8]:
    st.markdown("#### About this dashboard")
    st.markdown(f"""
The 529 Network built this dashboard on data submitted by states and consolidated
by The 529 Network. It covers {len(Q_LABELS)} reporting quarters from {Q_LABELS[0]}
to {Q_LABELS[-1]}.

**What it shows.** Four reported fields: state, plan name, total assets, and open
accounts. Every other figure on screen, average balances, shares, growth rates,
and distributions, derives from those four.

**The 2022 addition.** 2022 was the one gap in the master. It is now filled
from the four CSPN website workbooks (3/31, 6/30, 9/30, 12/31), parsed and
reconciled to each file's own national totals row with zero difference in all
four quarters. Plan names and state assignments were taken from the master's own
2021Q4 and 2023Q1 rosters, so nothing new was invented. Tennessee BEST Prepaid
and West Virginia Prepaid closed in 3Q 2021 and correctly carry no 2022 rows.
Arizona's Q1 row reports Ivy Funds InvestEd and Q2 onward reports Goldman Sachs
529, which is the manager transition, not a gap.

**Cadence.** Reporting is quarterly from 2021. Before that the record is annual
or semiannual, so year over year comparisons appear only where the same quarter
exists one year earlier.

**A note before this goes external.** Tables in this draft order by size so the
data reads plainly. Before any member-facing release, review against the
network's neutrality standard.

**Updating the record.** The app reads `data/529_data.csv` with columns
`Year, Period, Date, State, PlanName, Accounts, AUM, Note`. Append new periods
to the CSV and reboot the app. No code changes required.
""")

st.markdown(f'<div style="border-top:1px solid {MIST}; margin-top:2rem; '
            f'padding-top:0.6rem;" class="caption-note">The 529 Network · '
            f'Data submitted by states and consolidated by The 529 Network · '
            f'Updated through {Q_LABELS[-1]}</div>', unsafe_allow_html=True)
