# Influenza Vaccination Dashboard 2024–2025

You can view the live dashboard here: [Streamlit App](https://influenza-vaccination-dashboard-2024-2025.streamlit.app/)

## Overview

This Streamlit app transforms open-data on flu vaccinations into an interactive, narrative-driven dashboard.

Users can explore daily dispensing trends, compare regional coverage, simulate accelerated distribution scenarios, and estimate hospitalizations avoided through improved vaccine uptake.

## Features

- Time-series of 7-day rolling average doses

- Choropleth map of doses per 10,000 inhabitants by region

- “What-If” slider to model weekly capacity boosts

- SIR-based hospital-avoidance estimates with adjustable R₀ and recovery rate

- KPI header showing cumulative doses and national coverage percentage

## Prerequisites

- Python 3.8+

- Git (to clone the repo, optional)

## Installation

1. Clone the repository (or download zip)

git clone https://your-repo-url.git
cd influenza-vaccination-dashboard

2. Create and activate a virtual environment

python -m venv .venv
### for macOS / Linux
source .venv/bin/activate
### for Windows PowerShell
.\.venv\Scripts\Activate.ps1

3. Install Python dependencies

pip install --upgrade pip
pip install -r requirements.txt

4. Place raw data files in data/

- doses-actes-2024.csv

- couverture-2024.csv

- regions.geojson

## Running the App

streamlit run app.py

The dashboard will launch at http://localhost:8501 with hot-reload on file changes.

## Project Structure

.
├── app.py
├── requirements.txt
├── data/
│   ├── doses-actes-2024.csv
│   ├── couverture-2024.csv
│   └── regions.geojson
└── utils/
    ├── io.py
    ├── prep.py
    └── viz.py

- app.py: Defines layout, sidebar controls, KPIs, and ties together analytics & visuals

- utils/io.py: Reads CSV/GeoJSON and caches raw data

- utils/prep.py: Builds continuous time series, computes rolling/cumulative doses, regional aggregates, and SIR hospital-avoidance

- utils/viz.py: Wraps Altair and Plotly charts for consistent styling and interactivity

## Data Sources

- Daily dispensing: French open data doses/acts database

- Regional coverage: Official public-health coverage CSV

- Boundaries: GeoJSON of France’s administrative regions

## Customization

- Adjust the smoothing window by changing the rolling-average window in make_time_series()

- Replace the placeholder population with real regional totals in make_region_data()

- Add additional demographic or geospatial layers by extending utils/prep.py and utils/viz.py

## Next Steps

- Incorporate age-group or risk-group segmentation

- Drill down from regions to départements for finer granularity

- Compare with previous flu seasons for year-over-year analysis

- Deploy on Streamlit Community Cloud or another hosting platform

## License

This project is released under the MIT License.
Data is subject to the original open-data portal licensing—please refer to source metadata for reuse terms.
