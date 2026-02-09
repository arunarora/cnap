# --- ADAPTER 2: DATADOG ---
import logging
import datadog_api_client
from typing import Dict, Any
from metric_providers.base_provider import MetricProvider

class DatadogAdapter(MetricProvider):
    def connect(self, config: Dict[str, Any]):
        # Mocking connection setup
        self.api_key = config.get('api_key')
        self.app_key = config.get('app_key')

    def fetch_metric(self, query: str) -> float:
        # Datadog specific logic (Mock)
        print(f"[Datadog] Executing query: {query}")
        # In reality, you would call api_client.query_metrics(query)
        return 95.5 # Mock return