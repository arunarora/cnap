import requests
import logging

class OPAClient:
    def __init__(self, url="http://opa.opa.svc.cluster.local:8181/v1/data"):
        self.url = url

    def evaluate_policy(self, input_data, policy_path="cnap/reflex/allow"):
        """
        Sends the input JSON to OPA and returns the decision.
        """
        # OPA expects input wrapped in an "input" key
        payload = {"input": input_data}
        full_url = f"{self.url}/{policy_path}"
        
        try:
            response = requests.post(full_url, json=payload, timeout=5)
            response.raise_for_status()
            result = response.json()
            
            # Return the "result" object from OPA (e.g., {"action": "scale", "replicas": 5})
            return result.get("result", {})
            
        except requests.exceptions.RequestException as e:
            logging.error(f"[OPAClient] Error querying OPA at {full_url}: {e}")
            return {}