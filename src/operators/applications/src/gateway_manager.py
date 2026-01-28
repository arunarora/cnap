import importlib
import logging

class GatewayManager:
    def __init__(self):
        # Map YAML gateway names to module filenames
        # You can expand this registry as you add more gateways
        self.registry = {
            "kong-ingress-controller": "gateways.kong_ingress_controller"
        }

    def get_handler(self, gateway_name):
        """
        Dynamically imports the module for the given gateway name 
        and returns an instance of the GatewayHandler class.
        """
        module_path = self.registry.get(gateway_name)
        
        if not module_path:
            logging.error(f"Gateway '{gateway_name}' is not registered in GatewayManager.")
            return None

        try:
            # Dynamic import
            module = importlib.import_module(module_path)
            
            # Assume every gateway file has a class named 'GatewayHandler'
            handler_class = getattr(module, 'GatewayHandler')
            return handler_class()
        
        except (ImportError, AttributeError) as e:
            logging.error(f"Failed to load handler for {gateway_name}: {e}")
            return None