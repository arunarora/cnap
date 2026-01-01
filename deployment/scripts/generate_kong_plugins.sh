#!/usr/bin/env bash
set -euo pipefail

# --- Usage & Help ---
usage() {
  cat <<EOF
Usage: $0 [--dry-run] <KONG_DIR> <DEST_DIR>

Arguments:
  --dry-run      Print actions without writing to disk.
  KONG_DIR       Path to kong-ingress-controller directory.
  DEST_DIR       Path where generated manifests will be saved.

Description:
  Generates per-plugin Kong manifests.
  Requires 'handler.lua' and 'schema.lua' in plugin subdirectories.
EOF
}

# --- 1. Argument Parsing ---

DRY_RUN=false
ARGS=()

# Loop through all arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift # Remove --dry-run from processing
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      ARGS+=("$1") # Save regular arguments
      shift
      ;;
  esac
done

# Restore positional arguments (KONG_DIR, DEST_DIR)
set -- "${ARGS[@]}"

if [ "$#" -ne 2 ]; then
  echo "Error: Missing mandatory arguments." >&2
  usage
  exit 1
fi

# Function to execute or print commands
run_cmd() {
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] $*"
  else
    eval "$@"
  fi
}

# Check for yq (skip check if dry-run, but safer to check anyway)
if ! command -v yq &> /dev/null; then
  echo "Error: 'yq' is required but not installed." >&2
  exit 1
fi

KONG_DIR=$(readlink -f "$1")
DEST_DIR=$(readlink -f "$2")

TEMPLATES_DIR="$KONG_DIR/templates"
KONG_TEMPLATE="$TEMPLATES_DIR/kongPlugin.yaml"
CONFIGMAP_TEMPLATE="$TEMPLATES_DIR/configmap-plugin.yaml"

# Validation
if [ ! -d "$KONG_DIR" ]; then
  echo "Error: Kong directory not found at $KONG_DIR" >&2
  exit 1
fi

if [ "$DRY_RUN" = false ]; then
  if [ ! -d "$TEMPLATES_DIR" ]; then
    echo "Error: Templates directory not found at $TEMPLATES_DIR" >&2
    exit 1
  fi
  # Create Destination Directory
  mkdir -p "$DEST_DIR"
else
  echo "[DRY-RUN] Would create directory: $DEST_DIR"
fi

echo "Source:      $KONG_DIR"
echo "Destination: $DEST_DIR"
echo "Mode:        $( [ "$DRY_RUN" = true ] && echo "DRY RUN" || echo "EXECUTE" )"
echo "--------------------------------------------------"

# --- 2. Processing Loop ---

shopt -s nullglob
plugins_found=0

for plugin_path in "$KONG_DIR"/*; do
  if [ ! -d "$plugin_path" ]; then continue; fi

  plugin_name=$(basename "$plugin_path")
  echo "Plugin Path: $plugin_path"
  echo "Plugin Name: $plugin_name"

  # Validation: Plugin MUST have handler.lua and schema.lua
  if [[ ! -f "$plugin_path/handler.lua" || ! -f "$plugin_path/schema.lua" ]]; then
    continue
  fi

  echo "Processing plugin: $plugin_name"
  plugins_found=$((plugins_found+1))

  out_kong="$DEST_DIR/kongPlugin-$plugin_name.yaml"
  out_cm="$DEST_DIR/configmap-plugin-$plugin_name.yaml"

  if [ "$DRY_RUN" = true ]; then
    echo "  -> Would generate: $out_kong (from template)"
    echo "  -> Would generate: $out_cm (from template + handler.lua/schema.lua)"
  else
    # 1. Generate KongPlugin YAML
    sed "s/<VarPluginName>/$plugin_name/g" "$KONG_TEMPLATE" > "$out_kong"

    # 2. Generate ConfigMap YAML
    sed "s/<VarPluginName>/$plugin_name/g" "$CONFIGMAP_TEMPLATE" > "$out_cm"

    # 3. Inject Data
    for file_name in "handler.lua" "schema.lua"; do
      full_file_path="$plugin_path/$file_name"
      yq -i ".data[\"$file_name\"] = load_str(\"$full_file_path\")" "$out_cm"
    done
  fi
done

echo "--------------------------------------------------"
if [ "$plugins_found" -eq 0 ]; then
  echo "Warning: No valid plugins found."
  # Optional: Exit with error if no plugins found, depending on your strictness needs
  # exit 1 
else
  echo "Success! Processed $plugins_found plugins."
fi