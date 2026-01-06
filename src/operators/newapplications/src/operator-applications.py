import kopf
import logging
from gateway_manager import GatewayManager

# Initialize the gateway manager to handle routing to specific implementations
gateway_manager = GatewayManager()

@kopf.on.create('cnap.platforms.howlabs.io', 'v1alpha1', 'applications')
@kopf.on.update('cnap.platforms.howlabs.io', 'v1alpha1', 'applications')
def manage_application(spec, name, namespace, logger, **kwargs):
    """
    Main entry point for the Application CRD.
    It parses the gateway name and delegates processing to the specific gateway handler.
    """
    try:
        # 1. Extract Gateway Name
        integrations = spec.get('integrations', {})
        gateway_config = integrations.get('gateway', {})
        gateway_name = gateway_config.get('name')

        if not gateway_name:
            raise kopf.PermanentError("Gateway name is missing in spec.integrations.gateway")

        logger.info(f"Processing Application '{name}' for Gateway: {gateway_name}")

        # 2. Get the specific handler for this gateway
        # This allows us to keep gateway-specific logic in separate files
        handler = gateway_manager.get_handler(gateway_name)

        if not handler:
            raise kopf.PermanentError(f"No handler implementation found for gateway: {gateway_name}")

        # 3. Process the application using the specific handler
        result = handler.process_application(
            spec=spec,
            name=name,
            namespace=namespace,
            logger=logger,
            **kwargs
        )

        return {"status": "Processed", "gateway": gateway_name, "details": result}

    except Exception as e:
        logger.error(f"Failed to process application: {str(e)}")
        raise kopf.TemporaryError(f"Error processing application: {str(e)}", delay=30)