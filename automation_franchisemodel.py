# automation_franchisemodel_test.py
import math
import random
from datetime import datetime
import os

import numpy as np
import pandas as pd
from google.cloud import bigquery

# Define BigQuery main function
def get_table_from_query(query, project_id):
    """
    Executes a query in BigQuery and returns the result as a Pandas DataFrame.
    """
    try:
        client = bigquery.Client(project=project_id)
        query_job = client.query(query)
        result = query_job.result()
        df = result.to_dataframe()
        return df
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

# Main execution
if __name__ == "__main__":
    project_id = "amer-mediadata-us-amer-pd"

    query = """
        SELECT * FROM `amer-mediadata-us-amer-pd.Pubco.BCL_PUBCO_data_v2` 
        LIMIT 1000
    """

    print("Executing BigQuery...")

    df = get_table_from_query(query, project_id)

    if df is not None:
        print("✅ Query executed successfully!")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")

        print("\n" + "="*60)
        print("First 5 rows:")
        print("="*60)
        print(df.head().to_string(index=False))

        print("\n" + "="*60)
        print("Data types:")
        print("="*60)
        print(df.dtypes)

        print("\n" + "="*60)
        print("Basic statistics:")
        print("="*60)
        print(df.describe(include='all'))

        # Note: CSV saving removed for testing
        print("\n(No CSV file saved — preview only.)")

    else:
        print("❌ Failed to retrieve data from BigQuery.")
