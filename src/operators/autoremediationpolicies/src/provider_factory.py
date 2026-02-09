import importlib
import logging

from metric_providers.base_provider import MetricProvider
from metric_providers.prometheus import PrometheusAdapter


class ProviderFactory:
    _providers = {}

    @classmethod
    def register(cls, name, provider_cls):
        cls._providers[name] = provider_cls

    @classmethod
    def get_provider(cls, name, config) -> MetricProvider:
        provider_cls = cls._providers.get(name)
        if not provider_cls:
            raise ValueError(f"Provider '{name}' is not supported. Available: {list(cls._providers.keys())}")
        
        instance = provider_cls()
        instance.connect(config)
        return instance

# Register available tools immediately
ProviderFactory.register("prometheus", PrometheusAdapter)
# ProviderFactory.register("datadog", DatadogAdapter)