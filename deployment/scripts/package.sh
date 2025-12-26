#!/usr/bin/env bash
set -euo pipefail

# Resolve directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${SCRIPT_DIR}/.."
TARGET_DIR="${DEPLOY_DIR}/target"
CNAP_DIR="${TARGET_DIR}/cnap"
HELM_CHART_SRC="${DEPLOY_DIR}/helm-chart"
DEP_CHART_SRC="${DEPLOY_DIR}/dependent-chart"

echo "Deployment dir: ${DEPLOY_DIR}"

# Ensure helm is available
if ! command -v helm >/dev/null 2>&1; then
	echo "ERROR: helm is not installed or not in PATH" >&2
	exit 2
fi

# Delete target directory, if exists
if [ -d "${TARGET_DIR}" ]; then
        echo "Deleting Target dir: ${TARGET_DIR}"
        rm -rf "${TARGET_DIR}"
fi

# Create target directories
mkdir -p "${TARGET_DIR}"
mkdir -p "${CNAP_DIR}"

# Copy helm-chart into cnap dir
if [ -d "${HELM_CHART_SRC}" ]; then
	echo "Copying ${HELM_CHART_SRC} -> ${CNAP_DIR}"
	cp -ra "${HELM_CHART_SRC}/." "${CNAP_DIR}/"
else
	echo "ERROR: source helm chart not found: ${HELM_CHART_SRC}" >&2
	exit 3
fi

# Package with helm. Helm will default to Chart.yaml version; we pass --version to be explicit.
helm package "${CNAP_DIR}" --destination "${TARGET_DIR}" --dependency-update

echo "Packaged chart created in ${TARGET_DIR}"

echo "Done. To make the script executable (if needed): chmod +x ${SCRIPT_DIR}/package.sh"

exit 0
