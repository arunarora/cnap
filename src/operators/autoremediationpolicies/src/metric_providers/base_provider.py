from abc import ABC, abstractmethod
from typing import Any, Dict

class MetricProvider(ABC):
    """
    The Contract: All metric tools must implement this.
    """
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]):
        """Establish connection to the data source."""
        pass

    @abstractmethod
    def fetch_metric(self, query: str) -> float:
        """
        Executes a query and returns a single float value.
        If the tool returns a time series, this method should 
        normalize it (e.g., take the last value).
        """
        pass

