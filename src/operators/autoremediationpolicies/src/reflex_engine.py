import logging
import datetime
from kubernetes import client
from provider_factory import ProviderFactory

class ReflexEngine:
    def __init__(self, k8s_api_client, opa_client):
        self.k8s_apps = client.AppsV1Api(k8s_api_client)
        self.k8s_core = client.CoreV1Api(k8s_api_client)
        self.opa = opa_client

    def run_reflex_loop(self, crd_spec):
        """
        Main entry point for the logic loop.
        """
        # 1. Gather Data (Sensors)
        input_vector = self.build_input_vector(crd_spec)
        logging.info(f"Generated Input Vector: {input_vector}")

        # 2. Ask OPA (Decider)
        decision = self.opa.evaluate_policy(input_vector)
        logging.info(f"OPA Decision: {decision}")

        # 3. Execute Remediation (Executor)
        if decision and decision.get('action') != 'none':
            self.execute_action(decision, crd_spec['targetRef'])
            return f"Executed {decision.get('action')}"
        
        return "No action needed"

    def build_input_vector(self, crd_spec):
        """
        Constructs the JSON Payload for OPA.
        """
        target_ref = crd_spec['targetRef']
        
        payload = {
            "target": self._get_target_info(crd_spec),
            "primary_metrics": {},
            "context_metrics": {},
            "system_state": self._get_system_state(target_ref)
        }

        # Process Primary and Context metrics
        if 'metrics' in crd_spec:
            self._process_section(crd_spec['metrics'].get('primary', []), payload['primary_metrics'])
            self._process_section(crd_spec['metrics'].get('context', []), payload['context_metrics'])

        return payload

    def _process_section(self, metric_definitions, payload_section):
        for metric in metric_definitions:
            key = metric['key']
            provider_name = metric['provider']
            query = metric['query']
            config = metric.get('config', {})

            try:
                tool = ProviderFactory.get_provider(provider_name, config)
                value = tool.fetch_metric(query)
                payload_section[key] = value
            except Exception as e:
                logging.error(f"Failed to fetch metric {key}: {e}")
                payload_section[key] = -1.0

    def _get_target_info(self, crd_spec):
        return {
            "name": crd_spec['targetRef']['name'],
            "namespace": crd_spec['targetRef'].get('namespace', 'default')
        }

    def _get_system_state(self, target_ref):
        """
        Fetches live state from K8s (Replicas, Ready status, etc.)
        """
        try:
            name = target_ref['name']
            namespace = target_ref.get('namespace', 'default')
            
            # Assuming Target is a Deployment
            deployment = self.k8s_apps.read_namespaced_deployment(name, namespace)
            
            return {
                "replicas": deployment.status.replicas or 0,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "available_replicas": deployment.status.available_replicas or 0
            }
        except client.exceptions.ApiException as e:
            logging.error(f"K8s API Error fetching system state: {e}")
            return {"error": "target_not_found"}

    def execute_action(self, decision, target_ref):
        """
        The Executor: Performs Scale or Restart actions.
        """
        action = decision.get('action')
        name = target_ref['name']
        namespace = target_ref.get('namespace', 'default')

        try:
            if action == 'scale':
                replicas = decision.get('params', {}).get('replicas')
                if replicas:
                    logging.info(f"Scaling {name} to {replicas} replicas.")
                    body = {"spec": {"replicas": int(replicas)}}
                    self.k8s_apps.patch_namespaced_deployment_scale(name, namespace, body)
            
            elif action == 'restart':
                logging.info(f"Restarting rollout for {name}.")
                # K8s restart is triggered by updating an annotation (usually timestamp)
                now = datetime.datetime.utcnow().isoformat()
                body = {
                    "spec": {
                        "template": {
                            "metadata": {
                                "annotations": {
                                    "kubectl.kubernetes.io/restartedAt": now
                                }
                            }
                        }
                    }
                }
                self.k8s_apps.patch_namespaced_deployment(name, namespace, body)
                
            else:
                logging.warning(f"Unknown action type: {action}")

        except client.exceptions.ApiException as e:
            logging.error(f"Failed to execute action {action}: {e}")