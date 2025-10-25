import altair as alt
import streamlit as st
import plotly.express as px
import pandas as pd
import matplotlib.pyplot as plt


def line_chart(df, x, y, labels=None, title=None):
    if isinstance(y, list):
        df_melt = df.melt(id_vars=[x], value_vars=y, var_name="Series", value_name="Value")
        chart = alt.Chart(df_melt).mark_line().encode(
            x=alt.X(f"{x}:T", title=x),
            y=alt.Y("Value:Q", title=labels.get(y[0], "Value") if labels else "Value"),
            color=alt.Color("Series:N", title=""),
            tooltip=[f"{x}:T", "Value:Q", "Series:N"],
        )
    else:
        chart = alt.Chart(df).mark_line(color="#1f77b4", strokeWidth=2).encode(
            x=alt.X(f"{x}:T", title=x),
            y=alt.Y(f"{y}:Q", title=labels.get(y, y) if labels else y),
            tooltip=[f"{x}:T", f"{y}:Q"],
        )
    chart = chart.properties(width=700, height=300, title=title)
    st.altair_chart(chart, use_container_width=True)


def map_chart(df, value_col, id_col, title):
    geojson = df.__geo_interface__
    cent = {"lat": df.geometry.centroid.y.mean(), "lon": df.geometry.centroid.x.mean()}
    fig = px.choropleth_mapbox(
        df,
        geojson=geojson,
        locations=id_col,
        color=value_col,
        featureidkey=f"properties.{id_col}",
        center=cent,
        mapbox_style="carto-positron",
        zoom=5,
        opacity=0.6,
        labels={value_col: value_col},
    )
    fig.update_layout(margin={"r": 0, "t": 30, "l": 0, "b": 0}, title=title)
    st.plotly_chart(fig, use_container_width=True)


def plot_sir(df, title=None):
    df_melt = df.melt(
        id_vars=["day"],
        value_vars=["Hosp_Base", "Hosp_Boost"],
        var_name="Scenario",
        value_name="Hospitalizations",
    )
    chart = alt.Chart(df_melt).mark_line().encode(
        x=alt.X("day:Q", title="Day"),
        y=alt.Y("Hospitalizations:Q", title="Hospitalizations"),
        color=alt.Color("Scenario:N", scale=alt.Scale(range=["#1f77b4", "#ff7f0e"])),
        tooltip=["day:Q", "Hospitalizations:Q"],
    ).properties(width=700, height=300, title=title)
    st.altair_chart(chart, use_container_width=True)

def alt_heatmap(df):
    d = df.copy()
    if "date" not in d.columns and "index" in d.columns:
        d = d.rename(columns={"index": "date"})
    d["week"] = d["date"].dt.isocalendar().week.astype(str)
    d["weekday"] = d["date"].dt.weekday
    chart = alt.Chart(d).mark_rect().encode(
        x=alt.X("week:O", title="Semaine ISO"),
        y=alt.Y("weekday:O", title="Jour (0=Lun)"),
        color=alt.Color("rolling_7d_doses:Q", title="7d avg doses"),
        tooltip=["date:T", "rolling_7d_doses:Q"],
    ).properties(height=280)
    return chart


def plot_sir_band(df_band, title=None):
    fig, ax = plt.subplots(figsize=(9, 3))
    ax.fill_between(df_band["day"], df_band["avoided_p10"], df_band["avoided_p90"], color="lightblue", label="10-90 pct")
    ax.plot(df_band["day"], df_band["avoided_median"], color="navy", label="median avoided")
    ax.set_xlabel("Days")
    ax.set_ylabel("Estimated hospitalizations avoided")
    ax.set_title(title or "")
    ax.legend()
    st.pyplot(fig)
    plt.close(fig)