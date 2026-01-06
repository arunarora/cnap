import kopf
import kubernetes.config
import kubernetes.client
import hashlib
from kubernetes.client.rest import ApiException
from gateways.base_gateway import BaseGatewayHandler

class GatewayHandler(BaseGatewayHandler):
    def __init__(self):
        # specific initialization for this handler
        # We try to load configuration here to ensure the client is ready
        try:
            kubernetes.config.load_incluster_config()
        except kubernetes.config.ConfigException:
            try:
                kubernetes.config.load_kube_config()
            except kubernetes.config.ConfigException:
                # Fallback or let it fail later if no config found
                pass

    def process_application(self, spec, name, namespace, logger, **kwargs):
        logger.info("Initializing Kong Ingress Controller logic...")

        # 1. Parse Global Configuration
        global_config = spec.get('global', {})
        global_base_domain = global_config.get('baseDomain', 'example.com')
        env_prefixes = global_config.get('envPrefix', [])
        
        # Parse Authentication Configuration
        auth_config = global_config.get('authentication', {})
        # Note: Top-level 'enabled' field has been removed from CRD.
        # We now rely solely on specific method enablement.
        
        methods = auth_config.get('methods', {})
        api_token = methods.get('apiToken', {})
        
        api_token_enabled = False
        auth_plugin_name = None

        if isinstance(api_token, dict):
            api_token_enabled = api_token.get('enabled', False)
            ref = api_token.get('addonResourceref', {})
            
            # Check if the target resource is 'ingress'
            target_resource = ref.get('resourceName')
            if target_resource == 'ingress':
                raw_name = ref.get('addonResourceName')
                if raw_name:
                    auth_plugin_name = str(raw_name).strip()
                    logger.info(f"Identified Auth Plugin for Ingress: {auth_plugin_name} (Enabled: {api_token_enabled})")
            elif target_resource:
                logger.info(f"Auth Plugin targets '{target_resource}', skipping for Ingress.")
        elif isinstance(api_token, bool):
            api_token_enabled = api_token

        # 2. Parse Integration Addons (Common Plugins)
        integrations = spec.get('integrations', {}).get('gateway', {})
        addons = integrations.get('addons', [])
        
        # Extract plugins specifically for Ingress resources (Common to all routes)
        common_plugins = []
        for addon in addons:
            # We look for resources attaching to 'ingress'
            resources = addon.get('resources', [])
            for res in resources:
                if res.get('resourceName') == 'ingress':
                    val = res.get('addonResourceName', [])
                    # Robust parsing: Handle string vs list to avoid character splitting
                    if isinstance(val, list):
                        common_plugins.extend([str(p).strip() for p in val])
                    elif isinstance(val, str):
                        common_plugins.append(val.strip())
        
        if common_plugins:
            logger.info(f"Identified Common Kong Plugins: {', '.join(common_plugins)}")

        # Initialize Networking API
        networking_v1 = kubernetes.client.NetworkingV1Api()

        # 3. Process Components (Microservices)
        components = spec.get('components', [])
        generated_resources = []

        for component in components:
            comp_name = component.get('name')
            routes = component.get('routes', [])

            for route in routes:
                # Extract Route-specific Service Info
                service_config = route.get('service', {})
                # Use route service name, fallback to component name if not specified
                service_name = service_config.get('name', comp_name)
                
                # Extract port information from route service config
                ports_config = service_config.get('ports', {})
                service_port = ports_config.get('port', 80) # Default to 80 if not specified

                # Extract Route-specific Base Domain
                route_base_domain = route.get('baseDomain')

                # Calculate Plugins for this specific route
                # Start with common plugins (Copy to avoid modifying the original list)
                current_route_plugins = common_plugins.copy()
                
                # Check if route is exposed
                exposed_api = route.get('exposedAPI', False)
                
                if auth_plugin_name:
                    # Apply auth only if: API Token is ON, and Route is Exposed
                    # Removed 'global_auth_enabled' check as the field was removed from CRD
                    should_apply_auth = api_token_enabled and exposed_api

                    if should_apply_auth:
                        # Add auth plugin if not already present
                        if auth_plugin_name not in current_route_plugins:
                            current_route_plugins.append(auth_plugin_name)
                    else:
                        # Explicitly remove the auth plugin if it exists (e.g. from common_plugins)
                        # This covers cases where apiToken is disabled or exposedAPI is false.
                        # Using a while loop ensures we remove ALL instances (handling potential duplicates)
                        removed_count = 0
                        while auth_plugin_name in current_route_plugins:
                            current_route_plugins.remove(auth_plugin_name)
                            removed_count += 1
                        
                        if removed_count > 0:
                            logger.debug(f"Removed {removed_count} instances of {auth_plugin_name} from route {route.get('path')}")
                
                plugin_annotation_str = ", ".join(current_route_plugins)

                # Logic to generate Ingress for every environment defined in global config
                for env_entry in env_prefixes:
                    env_name = env_entry.get('env')
                    prefix = env_entry.get('prefix')

                    # Determine effective base domain: route override > global default
                    effective_base_domain = route_base_domain if route_base_domain else global_base_domain

                    # Construct full hostname
                    if prefix:
                        host = f"{prefix}.{effective_base_domain}"
                    else:
                        host = effective_base_domain

                    # Generate the Ingress definition
                    ingress_manifest = self._generate_ingress_manifest(
                        app_name=name,
                        service_name=service_name,
                        service_port=service_port,
                        namespace=namespace,
                        host=host,
                        route=route,
                        base_plugins=plugin_annotation_str
                    )

                    # CRITICAL: Adopt the resource. 
                    # This adds ownerReferences pointing to the 'Application' CR.
                    # When the Application CR is deleted, K8s will automatically delete this Ingress.
                    kopf.adopt(ingress_manifest)

                    # Apply to Kubernetes
                    try:
                        networking_v1.create_namespaced_ingress(
                            namespace=namespace,
                            body=ingress_manifest
                        )
                        logger.info(f"Created Ingress: {ingress_manifest['metadata']['name']}")
                    except ApiException as e:
                        if e.status == 409: # Conflict / Already Exists
                            # Logic to update existing resource
                            logger.info(f"Ingress {ingress_manifest['metadata']['name']} exists. Updating...")
                            
                            # Fetch the current version of the resource to avoid 409 Conflict during Replace
                            existing_ingress = networking_v1.read_namespaced_ingress(
                                name=ingress_manifest['metadata']['name'],
                                namespace=namespace
                            )
                            # Set the resourceVersion in the manifest to match the server's version
                            ingress_manifest['metadata']['resourceVersion'] = existing_ingress.metadata.resource_version
                            
                            networking_v1.replace_namespaced_ingress(
                                name=ingress_manifest['metadata']['name'],
                                namespace=namespace,
                                body=ingress_manifest
                            )
                        else:
                            # Re-raise other errors
                            raise kopf.PermanentError(f"Failed to manage Ingress: {e}")
                    
                    generated_resources.append(ingress_manifest['metadata']['name'])

        # Cleanup Orphaned Ingresses
        # This handles cases where an environment was removed or a route was deleted
        self._cleanup_orphaned_ingresses(networking_v1, namespace, name, generated_resources, logger)

        return {"generated_ingress_count": len(generated_resources), "resources": generated_resources}

    def _cleanup_orphaned_ingresses(self, api, namespace, app_name, active_ingress_names, logger):
        """
        Deletes Ingress resources that are managed by this application (identified by label)
        but are no longer present in the active_ingress_names list.
        """
        # Label selector to find all ingresses managed by this app
        label_selector = f"cnap.platforms.howlabs.io/application={app_name}"
        
        try:
            existing_ingresses = api.list_namespaced_ingress(namespace, label_selector=label_selector)
            for ingress in existing_ingresses.items:
                if ingress.metadata.name not in active_ingress_names:
                    logger.info(f"Deleting orphaned Ingress: {ingress.metadata.name}")
                    try:
                        api.delete_namespaced_ingress(ingress.metadata.name, namespace)
                    except ApiException as e:
                        # If it's already gone (404), that's fine
                        if e.status != 404:
                            logger.warning(f"Failed to delete orphaned Ingress {ingress.metadata.name}: {e}")
        except ApiException as e:
            logger.error(f"Failed to list Ingresses for cleanup: {e}")

    def _generate_ingress_manifest(self, app_name, service_name, service_port, namespace, host, route, base_plugins):
        """
        Helper to construct a K8s Ingress manifest dictionary.
        Generates a unique Ingress name per route using a hash of the host+path.
        """
        path = route.get('path')
        # https_enabled = route.get('httpsEnabled', False) # Ignored for now
        # whitelist_ips = route.get('whitelistIPs', [])    # Ignored for now

        # 1. Create Deterministic Unique Identifier
        # We hash the combination of Host + Path. 
        # This ensures that 'dev.example.com/api' and 'prod.example.com/api' 
        # get different Ingress names, even though the hostname is not in the string.
        unique_key = f"{host}:{path}"
        path_hash = hashlib.md5(unique_key.encode('utf-8')).hexdigest()[:6]
        
        # Name format: app-service-hash
        prefix = f"{app_name}-{service_name}"
        
        # Ensure name fits in 63 chars (limit for K8s names)
        # 63 - 1 (hyphen) - 6 (hash) = 56 chars available for prefix
        if len(prefix) > 56:
            prefix = prefix[:56]
            
        name = f"{prefix}-{path_hash}"

        # 2. Prepare Annotations
        annotations = {
            "kubernetes.io/ingress.class": "kong"
        }
        
        # Handle Plugins
        plugins = base_plugins
        
        if plugins:
            annotations["konghq.com/plugins"] = plugins

        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": {
                    "cnap.platforms.howlabs.io/application": app_name
                },
                "annotations": annotations
            },
            "spec": {
                "ingressClassName": "kong",
                "rules": [
                    {
                        "host": host,
                        "http": {
                            "paths": [
                                {
                                    "path": path,
                                    "pathType": "ImplementationSpecific",
                                    "backend": {
                                        "service": {
                                            "name": service_name,
                                            "port": {"number": service_port}
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }