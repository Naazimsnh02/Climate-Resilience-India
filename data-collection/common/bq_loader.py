"""Shared helper to load a pandas DataFrame into a BigQuery table (create-or-append)."""
from google.cloud import bigquery
from common.config import GCP_PROJECT, BQ_DATASET

_client = None


def client():
    global _client
    if _client is None:
        _client = bigquery.Client(project=GCP_PROJECT)
    return _client


def load_dataframe(df, table_name, write_disposition="WRITE_APPEND"):
    """Loads df into {GCP_PROJECT}.{BQ_DATASET}.{table_name}, auto-detecting schema on first create."""
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=write_disposition,
        autodetect=True,
        source_format=bigquery.SourceFormat.PARQUET,
    )
    job = client().load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()
    print(f"Loaded {len(df)} rows into {table_id}")
