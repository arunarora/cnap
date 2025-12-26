#!/usr/bin/env bash
set -euo pipefail

# Resolve directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${SCRIPT_DIR}/.."
TARGET_DIR="${DEPLOY_DIR}/target"
CNAP_DIR="${TARGET_DIR}/cnap"
HELM_CHART_SRC="${DEPLOY_DIR}/helm-chart"
DEP_CHART_SRC="${DEPLOY_DIR}/dependent-chart"

# Manually specify relative directories (relative to ${DEPLOY_DIR}) that contain
# CRD YAML files named like 'crd-*.yaml'. Edit this array as needed.
CRD_DIRS=(
	"../crds"
	# add other relative paths here, e.g.:
	# "dependent-charts/kong-ingress-controller/crds"
)


echo "Deployment dir: ${DEPLOY_DIR}"
echo "CRD directories (relative to ${DEPLOY_DIR}): ${CRD_DIRS[*]:-<none>}"


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

# Ensure the crds target exists inside the copied chart
mkdir -p "${CNAP_DIR}/crds"

# Copy all files starting with 'crd-' from each relative directory into ${CNAP_DIR}/crds
if [ ${#CRD_DIRS[@]} -eq 0 ]; then
	echo "No CRD directories configured in CRD_DIRS; skipping copy."
else
	# Avoid literal globs when no matches
	shopt -s nullglob
	for rel in "${CRD_DIRS[@]}"; do
		src_dir="${DEPLOY_DIR}/${rel}"
		files=("${src_dir}"/crd-*.yaml)
		if [ ${#files[@]} -gt 0 ]; then
			echo "Copying CRD files from ${src_dir} -> ${CNAP_DIR}/crds"
			cp -a "${files[@]}" "${CNAP_DIR}/crds/"
		else
			echo "No crd-*.yaml files in ${src_dir}"
		fi
	done
	shopt -u nullglob
fi


# Package with helm. Helm will default to Chart.yaml version; we pass --version to be explicit.
helm package "${CNAP_DIR}" --destination "${TARGET_DIR}" --dependency-update

echo "Packaged chart created in ${TARGET_DIR}"

echo "Done. To make the script executable (if needed): chmod +x ${SCRIPT_DIR}/package.sh"

exit 0
