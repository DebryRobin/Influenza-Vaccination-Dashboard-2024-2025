import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from utils.io import load_data
from utils.prep import (
    make_time_series,
    make_region_data,
    compute_region_timeseries,
    compute_scenarios,
    sir_sensitivity,
)
from utils.viz import (
    line_chart,
    map_chart,
    plot_sir,
    alt_heatmap,
    plot_sir_band,
)

st.set_page_config(page_title="Flu Vaccination Dashboard", layout="wide")

@st.cache_data(show_spinner=False)
def get_data():
    df_doses, df_cov, regions = load_data()
    if "date" in df_doses.columns:
        df_doses["date"] = pd.to_datetime(df_doses["date"])
    ts = make_time_series(df_doses)
    regional = make_region_data(df_cov, regions)
    regional_ts = compute_region_timeseries(df_doses)
    return df_doses, ts, regional, regional_ts

df_doses, ts, regional, regional_ts = get_data()

st.sidebar.header("Filters & Scenarios")
date_range = st.sidebar.date_input(
    "Date range", [ts.index.min().date(), ts.index.max().date()]
)
date_min, date_max = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])

region_codes = regional["region_code"].dropna().unique().tolist()
regions_sel = st.sidebar.multiselect("Regions", region_codes, default=region_codes)

boost = st.sidebar.slider("Weekly capacity boost (%)", 0, 30, 10, 1)
R0 = st.sidebar.slider("Epidemic R₀", 0.5, 3.0, 1.3, 0.1)
gamma_days = st.sidebar.slider("Recovery period (days)", 5, 14, 7, 1)
gamma = 1.0 / gamma_days

c1, c2, c3 = st.columns(3)
latest = ts.loc[date_max]
c1.metric("Total doses dispensed", f"{int(latest['cum_doses']):,}")
c2.metric("7-day avg per day", f"{latest['rolling_7d_doses']:.0f}")
cov_pct = latest["cum_doses"] / 67_000_000 * 100
c3.metric("National coverage (%)", f"{cov_pct:.1f}%")
st.markdown("---")

st.subheader("Campaign Momentum — 7‑Day Rolling Average of Daily Doses")
st.caption(
    "Shows the 7‑day moving average of doses dispensed per day. "
    "Smoothing highlights sustained increases or declines and reduces weekday noise; use this view to identify campaign peaks and periods where additional outreach is needed."
)
ts_sel = ts[(ts.index >= date_min) & (ts.index <= date_max)]
line_chart(
    ts_sel.reset_index().rename(columns={"index": "date"}),
    x="date",
    y="rolling_7d_doses",
    title="Campaign Momentum — 7‑Day Rolling Average",
)

st.subheader("Regional Coverage — Doses per 10,000 Inhabitants")
st.caption(
    "Choropleth showing doses administered per 10,000 inhabitants by region. "
    "Use this map to locate underperforming regions and target mobile units or communications."
)
map_data = regional[regional["region_code"].isin(regions_sel)]
map_chart(map_data, value_col="doses_per_10k", id_col="region_code", title="Regional Coverage — Doses per 10k")

st.subheader("Weekly Pattern Heatmap — Day of Week × ISO Week")
st.caption(
    "Heatmap of weekly dosing patterns. Bright rows reveal consistent weekday effects, dark streaks can indicate reporting gaps or holiday slowdowns."
)
heat_df = ts_sel.reset_index().rename(columns={"index": "date"})
st.altair_chart(alt_heatmap(heat_df), use_container_width=True)


st.subheader("Cumulative Doses — Actual vs Boosted Scenario")
st.caption(
    "Cumulative doses under current pace versus an accelerated weekly capacity. "
    "The vertical difference indicates additional people vaccinated over the displayed period; the intersection with the target line shows earlier attainment."
)
boosted = ts_sel.copy()
boosted["boosted"] = boosted["rolling_7d_doses"] * (1 + boost / 100)
boosted["cum_boosted"] = boosted["boosted"].cumsum()
plot_df = boosted.reset_index().rename(columns={"index": "date"})
target = 67_000_000 * 0.75

line_actual = alt.Chart(plot_df).mark_line(color="#1f77b4").encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("cum_doses:Q", title="Cumulative doses"),
    tooltip=["date:T", "cum_doses:Q"],
)
line_boost = alt.Chart(plot_df).mark_line(strokeDash=[6, 3], color="#ff7f0e").encode(
    x="date:T", y="cum_boosted:Q", tooltip=["date:T", "cum_boosted:Q"]
)
target_rule = alt.Chart(pd.DataFrame({"y": [target]})).mark_rule(color="green").encode(y="y:Q")
proj_chart = (line_actual + line_boost + target_rule).properties(title="Cumulative Coverage Projection — Target Line", height=300)
st.altair_chart(proj_chart, use_container_width=True)

st.subheader("Scenario Summary — Date to Reach Target and Estimated Avoided Hospitalisations")
st.caption(
    "Tabular summary of alternative weekly-boost scenarios showing projected date to reach the target coverage, rough estimate of additional vaccinated people, and a coarse estimate of hospitalisations avoided."
)
scen_df = compute_scenarios(ts, boosts=[0, 5, 10, 15, 20, boost], target_pct=75, population=67_000_000)
st.table(scen_df)

st.subheader("Estimated Hospitalizations Avoided — Sensitivity Band (10–90%)")
st.caption(
    "Monte‑Carlo style sensitivity on R₀ and recovery rate. The shaded band shows uncertainty (10–90 percentile) and the median line indicates typical expected impact; use this to communicate uncertainty to decision makers."
)
sir_df = sir_sensitivity(
    baseline_cov=cov_pct / 100,
    boosted_cov=min(1.0, cov_pct / 100 + boost / 100),
    R0_center=R0,
    gamma_center=gamma,
    days=120,
    runs=25,
)
plot_sir_band(sir_df, title="Estimated Hospitalizations Avoided — 10–90% band & median")
st.write(f"Estimated hospitalizations avoided (median scenario): {int(sir_df['avoided_median'].sum()):,}")

st.subheader("Hospitalizations: Deterministic Median — Baseline vs Boosted")
st.caption("Median estimated hospitalizations avoided over time (for quick interpretation).")
median_df = pd.DataFrame({"day": sir_df["day"], "avoided_median": sir_df["avoided_median"]})
median_chart = alt.Chart(median_df).mark_line(color="#1f77b4").encode(
    x=alt.X("day:Q", title="Day"),
    y=alt.Y("avoided_median:Q", title="Estimated hospitalizations avoided (median)"),
    tooltip=["day:Q", "avoided_median:Q"],
).properties(height=300, title="Median Estimated Hospitalizations Avoided Over Time")
st.altair_chart(median_chart, use_container_width=True)

st.markdown("---")
st.caption(
    "Notes: placeholder assumptions used for population and avoided-hospitalisation conversions. "
    "Replace placeholders with authoritative demographic and clinical parameters for operational decisions."
)