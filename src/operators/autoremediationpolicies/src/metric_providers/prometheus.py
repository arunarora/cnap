# --- ADAPTER 1: PROMETHEUS ---
import logging
from typing import Dict, Any
from metric_providers.base_provider import MetricProvider
from prometheus_api_client import PrometheusConnect

class PrometheusAdapter(MetricProvider):
    def connect(self, config: Dict[str, Any]):
        # Default to standard K8s DNS for prometheus if not provided
        url = config.get('url', 'http://cnap-kube-prometheus-stack-prometheus.cnap.svc.cluster.local:9090')
        self.client = PrometheusConnect(url=url, disable_ssl=True)

    def fetch_metric(self, query: str) -> float:
        try:
            # prometheus-api-client returns a list of results
            result = self.client.custom_query(query=query)
            
            if not result:
                return 0.0
            
            # Extract the value. Result format: [{'metric': {...}, 'value': [timestamp, "value"]}]
            value_str = result[0]['value'][1]
            return float(value_str)
        except Exception as e:
            logging.error(f"[PrometheusAdapter] Error fetching query '{query}': {e}")
            return 0.0