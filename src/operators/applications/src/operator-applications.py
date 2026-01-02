import kopf
import kubernetes.client
from kubernetes.client.rest import ApiException

# Constants
GROUP = "cnap.platforms.howlabs.io"
VERSION = "v1alpha1"
PLURAL = "applications"

@kopf.on.create(GROUP, VERSION, PLURAL)
@kopf.on.update(GROUP, VERSION, PLURAL)
def reconcile_ingress_policy(spec, name, namespace, logger, **kwargs):
    
    # --- CONFIGURATION ---
    # 1. Expected Domain
    final_domain = spec.get("global", {}).get("baseDomain", "example.com")
    
    # 2. Plugin String (e.g., "key-auth")
    gateway_config = spec.get("gateway", {})
    plugin_map = gateway_config.get("plugins", {})
    api_token_plugin_name = plugin_map.get("apiToken", "key-auth")
    
    # 3. Auth Status
    auth_config = spec.get("global", {}).get("authentication", {})
    is_apitoken_active = False
    if auth_config.get("enabled"):
        if auth_config.get("methods", {}).get("apiToken"):
            is_apitoken_active = True

    api = kubernetes.client.NetworkingV1Api()
    
    # Fetch ALL Ingresses belonging to this App (regardless of component)
    # We use the label 'cnap.io/app' which you must apply to your Ingress manifests.
    try:
        all_app_ingresses = api.list_namespaced_ingress(
            namespace, 
            label_selector=f"cnap.io/app={name}"
        ).items
    except ApiException as e:
        raise kopf.TemporaryError(f"Could not list ingresses: {e}")

    logger.info(f"Found {len(all_app_ingresses)} Ingresses for App '{name}'. Starting Validation.")

    # --- PHASE 1: STRICT HOSTNAME VALIDATION ---
    # We check ALL ingresses first. If ANY fails, we abort the entire operation.
    
    validation_errors = []
    
    for ing in all_app_ingresses:
        ing_name = ing.metadata.name
        # Grab the first rule's host. If no rules, default to empty string.
        current_host = ing.spec.rules[0].host if ing.spec.rules else ""
        
        if current_host != final_domain:
            validation_errors.append(
                f"Ingress '{ing_name}' has host '{current_host}' but requires '{final_domain}'."
            )

    if validation_errors:
        # Stop everything. Do not patch anything.
        error_summary = "; ".join(validation_errors)
        logger.error(f"Compliance Check Failed: {error_summary}")
        raise kopf.PermanentError(f"Hostname Mismatch detected. No patches applied. Fix these Ingresses: {error_summary}")

    logger.info("Validation Passed: All Ingresses have the correct hostname. Proceeding to Patching.")

    # --- PHASE 2: EXECUTION (PATCH PLUGINS) ---
    # Since validation passed, we iterate again to apply Auth Logic.
    
    for ing in all_app_ingresses:
        process_ingress_patch(
            api, 
            ing, 
            namespace, 
            is_apitoken_active, 
            api_token_plugin_name, 
            logger
        )

def process_ingress_patch(api, ing, namespace, is_globally_active, plugin_name, logger):
    """
    Determines if the specific Ingress needs the plugin added or removed
    based on its own 'protection' label.
    """
    labels = ing.metadata.labels or {}
    protection_status = labels.get("cnap.io/protection", "disabled")
    
    patch_needed = False
    patch_body = {"metadata": {"annotations": {}}}
    
    current_anns = ing.metadata.annotations or {}
    current_plugins = current_anns.get("konghq.com/plugins", "")
    plugins_list = [p.strip() for p in current_plugins.split(',')] if current_plugins else []

    # DECISION MATRIX:
    # 1. Protection=Enabled AND GlobalAuth=Active -> ENFORCE Plugin
    # 2. Protection=Enabled AND GlobalAuth=Inactive -> REMOVE Plugin
    # 3. Protection=Disabled -> REMOVE Plugin (Always)
    
    should_have_plugin = (protection_status == "enabled" and is_globally_active)

    if should_have_plugin:
        # ENFORCE: Add if missing
        if plugin_name not in plugins_list:
            plugins_list.append(plugin_name)
            new_val = ", ".join(plugins_list)
            patch_body["metadata"]["annotations"]["konghq.com/plugins"] = new_val
            patch_needed = True
    else:
        # REMOVE: Delete if present
        if plugin_name in plugins_list:
            plugins_list.remove(plugin_name)
            new_val = ", ".join(plugins_list) if plugins_list else None
            patch_body["metadata"]["annotations"]["konghq.com/plugins"] = new_val
            patch_needed = True

    # Apply Patch
    if patch_needed:
        try:
            api.patch_namespaced_ingress(ing.metadata.name, namespace, patch_body)
            action = "Added" if should_have_plugin else "Removed"
            logger.info(f"Patched '{ing.metadata.name}': {action} plugin '{plugin_name}'")
        except ApiException as e:
            logger.error(f"Failed to patch {ing.metadata.name}: {e}")