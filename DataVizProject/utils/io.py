import pandas as pd
import geopandas as gpd

def load_data():
    df_doses = pd.read_csv("data/doses-actes-2024.csv", parse_dates=["date"])
    df_cov   = pd.read_csv("data/couverture-2024.csv")
    regions  = gpd.read_file("data/regions.geojson").to_crs(epsg=4326)
    return df_doses, df_cov, regions