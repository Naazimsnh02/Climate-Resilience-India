"""Shared BigQuery client for agent tools."""
from google.cloud import bigquery
from .config import GCP_PROJECT

_client = None


def client():
    global _client
    if _client is None:
        _client = bigquery.Client(project=GCP_PROJECT)
    return _client
