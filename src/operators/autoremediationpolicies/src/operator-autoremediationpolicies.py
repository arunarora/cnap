import kopf
import logging
from kubernetes import client, config
from reflex_engine import ReflexEngine
from opa_client import OPAClient

# Configure Logging
logging.basicConfig(level=logging.INFO)

# Global clients (initialized on startup)
k8s_api_client = None
opa_client = None

@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    global k8s_api_client, opa_client
    
    # 1. Load K8s Config
    try:
        config.load_incluster_config()
        logging.info("Loaded in-cluster config.")
    except config.ConfigException:
        config.load_kube_config()
        logging.info("Loaded local kubeconfig.")
    
    # Initialize shared API client
    k8s_api_client = client.ApiClient()
    
    # 2. Initialize OPA Client
    # In production, get URL from env var
    opa_client = OPAClient(url="https://cnap-opa:443/v1/data")

@kopf.on.timer('cnap.platforms.howlabs.io', 'v1alpha1', 'autoremediationpolicies', interval=30.0)
def reflex_loop(spec, **kwargs):
    """
    This function runs every 30 seconds for every AutoRemediationPolicy CR.
    It acts as the heartbeat of the Reflex Loop.
    """
    if not k8s_api_client or not opa_client:
        raise kopf.TemporaryError("Clients not initialized", delay=5)

    engine = ReflexEngine(k8s_api_client, opa_client)
    
    try:
        result = engine.run_reflex_loop(spec)
        return {"status": "success", "last_action": result}
    except Exception as e:
        logging.error(f"Error in reflex loop: {e}")
        raise kopf.TemporaryError(f"Reflex failed: {e}", delay=10)