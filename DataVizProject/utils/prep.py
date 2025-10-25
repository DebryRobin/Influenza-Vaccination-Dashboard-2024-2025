import pandas as pd
import numpy as np


def make_time_series(df):
    full_dates = pd.date_range(df["date"].min(), df["date"].max())
    ts = (
        df.groupby("date")[["valeur", "jour"]]
        .sum()
        .reindex(full_dates)
        .ffill()
    )
    ts.index.name = "date"
    ts = ts.rename(columns={"valeur": "dose", "jour": "day_count"})
    ts["rolling_7d_doses"] = ts["dose"].rolling(7, min_periods=1).mean()
    ts["cum_doses"] = ts["dose"].cumsum()
    return ts


def make_region_data(df_cov, regions, population=1_000_000):
    df = df_cov[df_cov["variable"].str.contains("DOSES")].copy()
    df["code"] = df["code"].astype(str)
    agg = df.groupby("code")["valeur"].sum().reset_index()
    agg = agg.rename(columns={"code": "region_code", "valeur": "total_doses"})
    agg["population"] = population
    agg["doses_per_10k"] = agg["total_doses"] / agg["population"] * 10000
    regions = regions.copy()
    regions["code"] = regions["code"].astype(str)
    merged = regions.merge(agg, left_on="code", right_on="region_code", how="left")
    return merged


def run_sir(N, I0, R0, gamma, days):
    beta = R0 * gamma
    S, I, R = N - I0, I0, 0
    data = []
    for t in range(days):
        new_inf = beta * S * I / N
        new_rec = gamma * I
        S, I, R = S - new_inf, I + new_inf - new_rec, R + new_rec
        data.append({"day": t, "S": S, "I": I, "R": R})
    return pd.DataFrame(data)


def hosp_avoidance(baseline_cov, boosted_cov, R0, gamma, days=120):
    N_total = 67_000_000
    I0 = 5000
    base_N = int(N_total * (1 - baseline_cov))
    boost_N = int(N_total * (1 - boosted_cov))
    df_base = run_sir(base_N, I0, R0, gamma, days)
    df_boost = run_sir(boost_N, I0, R0, gamma, days)
    df_hosp = pd.DataFrame(
        {
            "day": df_base["day"],
            "Hosp_Base": df_base["I"] * 0.05,
            "Hosp_Boost": df_boost["I"] * 0.05,
        }
    )
    df_hosp["avoided"] = df_hosp["Hosp_Base"] - df_hosp["Hosp_Boost"]
    return df_hosp

def compute_region_timeseries(df_doses):
    df = df_doses.copy()
    if "valeur" in df.columns and "dose" not in df.columns:
        df = df.rename(columns={"valeur": "dose"})
    if "date" not in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    df["date"] = pd.to_datetime(df["date"])
    if "region_code" not in df.columns and "code" in df.columns:
        df = df.rename(columns={"code": "region_code"})

    out = []
    if "region_code" in df.columns:
        for region, grp in df.groupby("region_code"):
            grp = grp.groupby("date")["dose"].sum().reset_index()
            idx = pd.date_range(grp["date"].min(), grp["date"].max())
            grp2 = grp.set_index("date").reindex(idx, fill_value=0).rename_axis("date").reset_index()
            grp2["region_code"] = region
            grp2["rolling_7d_doses"] = grp2["dose"].rolling(7, min_periods=1).mean()
            out.append(grp2[["date", "region_code", "dose", "rolling_7d_doses"]])
    if out:
        return pd.concat(out, ignore_index=True)
    return pd.DataFrame(columns=["date", "region_code", "dose", "rolling_7d_doses"])


def compute_scenarios(ts, boosts=[0, 5, 10, 15, 20], target_pct=75, population=67_000_000):
    results = []
    last_cum = ts["cum_doses"].iloc[-1]
    for b in sorted(set(boosts)):
        boosted_daily = ts["rolling_7d_doses"] * (1 + b / 100)
        cum_bo = boosted_daily.cumsum()
        target = population * target_pct / 100
        if cum_bo.iloc[-1] < target:
            mean_recent = boosted_daily.tail(14).mean()
            days_needed = int(np.ceil((target - cum_bo.iloc[-1]) / mean_recent)) if mean_recent > 0 else np.nan
            date_hit = ts.index[-1] + pd.Timedelta(days=days_needed) if not np.isnan(days_needed) else pd.NaT
        else:
            idx = cum_bo[cum_bo >= target].index.min()
            date_hit = idx
        extra_vax = cum_bo.iloc[-1] - last_cum
        avoided = int(max(0, extra_vax) * 0.0005)  # placeholder conversion, adjust with source
        results.append(
            {
                "boost_pct": b,
                "date_hit": pd.to_datetime(date_hit).date() if pd.notnull(date_hit) else "Not reached",
                "extra_vaccinated": int(max(0, extra_vax)),
                "avoided_est": avoided,
            }
        )
    return pd.DataFrame(results)


def sir_avoided_for_params(baseline_cov, boosted_cov, R0, gamma, days):
    N_total = 67_000_000
    I0 = 5000
    base_N = int(N_total * (1 - baseline_cov))
    boost_N = int(N_total * (1 - boosted_cov))
    df_b = run_sir(base_N, I0, R0, gamma, days)
    df_bo = run_sir(boost_N, I0, R0, gamma, days)
    hosp_b = df_b["I"] * 0.05
    hosp_bo = df_bo["I"] * 0.05
    avoided = hosp_b - hosp_bo
    return pd.DataFrame({"day": df_b["day"], "Hosp_Base": hosp_b, "Hosp_Boost": hosp_bo, "avoided": avoided})


def sir_sensitivity(baseline_cov, boosted_cov, R0_center=1.3, gamma_center=1 / 7, days=120, runs=20):
    rng = np.random.default_rng(42)
    R0_samples = rng.normal(R0_center, 0.2, runs)
    gamma_samples = rng.normal(gamma_center, gamma_center * 0.15, runs)
    all_runs = []
    for r0, g in zip(R0_samples, gamma_samples):
        df = sir_avoided_for_params(baseline_cov, boosted_cov, max(0.1, r0), max(0.01, g), days)
        all_runs.append(df[["day", "avoided"]].set_index("day"))
    big = pd.concat(all_runs, axis=1)
    big.columns = range(big.shape[1])
    avoided_p10 = big.quantile(0.10, axis=1)
    avoided_p50 = big.quantile(0.50, axis=1)
    avoided_p90 = big.quantile(0.90, axis=1)
    out = pd.DataFrame(
        {
            "day": avoided_p10.index,
            "avoided_p10": avoided_p10.values,
            "avoided_median": avoided_p50.values,
            "avoided_p90": avoided_p90.values,
        }
    )
    return out