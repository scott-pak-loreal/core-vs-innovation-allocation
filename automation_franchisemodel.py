# app.py
import math
import random
from datetime import date

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Core vs Innovation Allocation", layout="wide")

# ---- SIDEBAR INPUTS ----
st.sidebar.header("Inputs")
total_budget = st.sidebar.number_input("Total Budget ($)", min_value=0, value=40_000_000, step=1_000_000)
core_pct   = st.sidebar.slider("Core % of Budget", 0, 100, 85)
innov_pct  = 100 - core_pct

n_core  = st.sidebar.number_input("Number of Core franchises", min_value=1, value=8, step=1)
n_innov = st.sidebar.number_input("Number of Innovation franchises", min_value=1, value=2, step=1)
seed    = st.sidebar.number_input("Random seed", min_value=0, value=42, step=1)

# ---- DUMMY DATA (repeatable) ----
random.seed(seed)
np.random.seed(seed)

core_names  = [f"Core_{i+1}" for i in range(n_core)]
innov_names = [f"Innov_{i+1}" for i in range(n_innov)]
franchises  = core_names + innov_names

# Simple ROI curve params (a diminishing-returns toy model)
# Core is steadier (lower responsiveness), Innovation is spikier (higher responsiveness)
a_core, b_core = 1.0, 0.55
a_inn,  b_inn  = 1.3, 0.75

df = pd.DataFrame({
    "Franchise": franchises,
    "Type": ["Core"] * n_core + ["Innovation"] * n_innov,
})

# ---- BUDGET SPLIT ----
core_budget  = total_budget * (core_pct / 100)
innov_budget = total_budget - core_budget

# Split within each group by equal share (you can swap in your weights later)
df["budget_share"] = df.groupby("Type")["Franchise"].transform(lambda s: 1.0 / len(s))
df.loc[df["Type"] == "Core", "Spend"]       = df["budget_share"] * core_budget
df.loc[df["Type"] == "Innovation", "Spend"] = df["budget_share"] * innov_budget

# ---- TOY RESPONSE CURVE (per franchise) ----
def response_curve(spend, kind):
    # Diminishing returns: sales = a * spend^b, with different (a,b) by type
    if kind == "Core":
        return a_core * (spend ** b_core)
    return a_inn * (spend ** b_inn)

df["Sales_Forecast"] = df.apply(lambda r: response_curve(r["Spend"], r["Type"]), axis=1)
df["Media_to_Sales_%"] = (df["Spend"] / df["Sales_Forecast"]).replace([np.inf, -np.inf], np.nan) * 100

# ---- LAYOUT ----
left, right = st.columns([1, 1])

with left:
    st.title("Core vs Innovation Allocation")
    st.subheader("Summary")
    st.metric("Total Budget", f"${total_budget:,.0f}")
    st.write(
        f"**Split:** Core {core_pct}% (${core_budget:,.0f})  |  "
        f"Innovation {innov_pct}% (${innov_budget:,.0f})"
    )

    st.subheader("Allocation Table")
    st.dataframe(
        df[["Franchise", "Type", "Spend", "Sales_Forecast", "Media_to_Sales_%"]]
          .sort_values(["Type", "Franchise"])
          .style.format({"Spend": "${:,.0f}", "Sales_Forecast": "${:,.0f}", "Media_to_Sales_%": "{:,.1f}%"}),
        use_container_width=True
    )

with right:
    st.subheader("Spend by Type")
    spend_by_type = df.groupby("Type", as_index=False)["Spend"].sum()

    fig1, ax1 = plt.subplots()
    ax1.bar(spend_by_type["Type"], spend_by_type["Spend"])
    ax1.set_xlabel("Type")
    ax1.set_ylabel("Spend ($)")
    ax1.set_title("Spend by Type")
    st.pyplot(fig1)

    st.subheader("Toy Response Curve (illustrative)")
    # Plot response curve for a representative franchise in each group
    x_spend = np.linspace(0, max(core_budget, innov_budget) / max(n_core, 1), 50)
    y_core  = [response_curve(x, "Core") for x in x_spend]
    y_inn   = [response_curve(x, "Innovation") for x in x_spend]

    fig2, ax2 = plt.subplots()
    ax2.plot(x_spend, y_core, label="Core")
    ax2.plot(x_spend, y_inn,  label="Innovation")
    ax2.set_xlabel("Spend ($)")
    ax2.set_ylabel("Sales (toy units)")
    ax2.set_title("Diminishing Returns (toy curves)")
    ax2.legend()
    st.pyplot(fig2)

st.caption(f"Run date: {date.today().isoformat()} • This is a toy scaffold. Replace the curve with your real MMM/elasticities.")
