#!/usr/bin/env bash

set -euo pipefail

UBUNTU_VERSION="${UBUNTU_VERSION:-24.04}"
KUBECTL_VERSION="${KUBECTL_VERSION:-latest}"
KUBELOGIN_VERSION="${KUBELOGIN_VERSION:-latest}"
BUILDX_VERSION="${BUILDX_VERSION:-v0.28.0}"
UV_INSTALL_DIR="${UV_INSTALL_DIR:-$HOME/.local/bin}"
HELM_KEYRING_PATH="/usr/share/keyrings/helm.gpg"
HELM_SOURCE_LIST_PATH="/etc/apt/sources.list.d/helm-stable-debian.list"
AZURE_KEYRING_PATH="/etc/apt/keyrings/microsoft.gpg"
AZURE_SOURCE_LIST_PATH="/etc/apt/sources.list.d/azure-cli.sources"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/init/maintvm/setup.sh

Environment variables:
  UBUNTU_VERSION
      Microsoft package repo に使う Ubuntu version。デフォルト: 24.04
  KUBECTL_VERSION
      az aks install-cli に渡す kubectl version。デフォルト: latest
  KUBELOGIN_VERSION
      az aks install-cli に渡す kubelogin version。デフォルト: latest
  BUILDX_VERSION
      docker buildx plugin が未導入の場合に取得する version。デフォルト: v0.28.0
  UV_INSTALL_DIR
      uv のインストール先ディレクトリ。デフォルト: $HOME/.local/bin
EOF
}

log() {
  printf '==> %s\n' "$*"
}

run_as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
    return
  fi

  if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required to install system packages." >&2
    exit 1
  fi

  sudo "$@"
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command not found: ${command_name}" >&2
    exit 1
  fi
}

ensure_ubuntu() {
  if [[ ! -r /etc/os-release ]]; then
    echo "/etc/os-release not found." >&2
    exit 1
  fi

  # shellcheck disable=SC1091
  source /etc/os-release

  if [[ "${ID:-}" != "ubuntu" ]]; then
    echo "This script supports Ubuntu only. Current ID=${ID:-unknown}" >&2
    exit 1
  fi
}

require_bootstrap_commands() {
  require_command apt-get
  require_command curl
  require_command dpkg
}

install_apt_prerequisites() {
  log "Install APT prerequisites"
  run_as_root apt-get update
  run_as_root apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
}

register_microsoft_packages_repo() {
  log "Register Microsoft packages repo"

  local deb_path
  deb_path="$(mktemp -t packages-microsoft-prod.XXXXXX.deb)"

  curl -fsSL \
    "https://packages.microsoft.com/config/ubuntu/${UBUNTU_VERSION}/packages-microsoft-prod.deb" \
    -o "${deb_path}"
  run_as_root dpkg -i "${deb_path}"
  rm -f "${deb_path}"
}

register_azure_cli_repo() {
  log "Register Azure CLI repo"

  local az_dist
  az_dist="$(lsb_release -cs)"

  run_as_root mkdir -p /etc/apt/keyrings
  curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | \
    gpg --dearmor | run_as_root tee "${AZURE_KEYRING_PATH}" >/dev/null
  run_as_root chmod go+r "${AZURE_KEYRING_PATH}"

  cat <<EOF | run_as_root tee "${AZURE_SOURCE_LIST_PATH}" >/dev/null
Types: deb
URIs: https://packages.microsoft.com/repos/azure-cli/
Suites: ${az_dist}
Components: main
Architectures: $(dpkg --print-architecture)
Signed-by: ${AZURE_KEYRING_PATH}
EOF
}

register_helm_repo() {
  log "Register Helm repo"

  curl -fsSL https://packages.buildkite.com/helm-linux/helm-debian/gpgkey | \
    gpg --dearmor | run_as_root tee "${HELM_KEYRING_PATH}" >/dev/null
  cat <<EOF | run_as_root tee "${HELM_SOURCE_LIST_PATH}" >/dev/null
deb [signed-by=${HELM_KEYRING_PATH}] https://packages.buildkite.com/helm-linux/helm-debian/any/ any main
EOF
}

install_apt_packages() {
  log "Install system packages"
  run_as_root apt-get update
  run_as_root env ACCEPT_EULA=Y apt-get install -y \
    docker.io \
    git \
    make \
    python-is-python3 \
    python3.12 \
    python3.12-venv \
    unixodbc \
    unixodbc-dev \
    msodbcsql18 \
    azure-cli \
    helm
}

configure_docker_access() {
  log "Configure Docker service and group access"

  run_as_root systemctl enable --now docker

  local target_user
  target_user="${SUDO_USER:-$USER}"

  if id -nG "${target_user}" | tr ' ' '\n' | grep -qx docker; then
    return
  fi

  run_as_root usermod -aG docker "${target_user}"
  log "Added ${target_user} to docker group. Re-login is required for group change to take effect."
}

install_docker_buildx_if_needed() {
  if docker buildx version >/dev/null 2>&1; then
    return
  fi

  log "Install docker buildx plugin"

  local arch
  case "$(uname -m)" in
    x86_64)
      arch="amd64"
      ;;
    aarch64|arm64)
      arch="arm64"
      ;;
    *)
      echo "Unsupported architecture for docker buildx: $(uname -m)" >&2
      exit 1
      ;;
  esac

  local plugin_dir="${HOME}/.docker/cli-plugins"
  local plugin_path="${plugin_dir}/docker-buildx"

  mkdir -p "${plugin_dir}"
  curl -fsSL \
    "https://github.com/docker/buildx/releases/download/${BUILDX_VERSION}/buildx-${BUILDX_VERSION}.linux-${arch}" \
    -o "${plugin_path}"
  chmod +x "${plugin_path}"
}

ensure_path_in_bashrc() {
  local path_entry='export PATH="$HOME/.local/bin:$PATH"'
  local bashrc_path="${HOME}/.bashrc"

  touch "${bashrc_path}"
  if ! grep -Fqx "${path_entry}" "${bashrc_path}"; then
    log "Append ~/.local/bin to ~/.bashrc"
    printf '%s\n' "${path_entry}" >>"${bashrc_path}"
  fi

  export PATH="${HOME}/.local/bin:${PATH}"
}

install_uv() {
  log "Install uv"
  local uv_installer
  uv_installer="$(mktemp -t uv-installer.XXXXXX.sh)"

  curl -fsSL https://astral.sh/uv/install.sh -o "${uv_installer}"
  env UV_INSTALL_DIR="${UV_INSTALL_DIR}" sh "${uv_installer}" >/dev/null
  rm -f "${uv_installer}"

  ensure_path_in_bashrc

  if [[ -x "${UV_INSTALL_DIR}/uv" ]]; then
    export PATH="${UV_INSTALL_DIR}:${PATH}"
  fi

  require_command uv
}

install_kubectl_and_kubelogin() {
  log "Install kubectl and kubelogin"
  run_as_root az aks install-cli \
    --client-version "${KUBECTL_VERSION}" \
    --install-location /usr/local/bin/kubectl \
    --kubelogin-version "${KUBELOGIN_VERSION}" \
    --kubelogin-install-location /usr/local/bin/kubelogin
}

verify_installed_commands() {
  log "Verify installed commands"

  docker --version
  docker buildx version
  git --version
  make --version
  python --version
  python3.12 --version
  uv --version
  az version
  kubectl version --client
  helm version
  kubelogin --version
  odbcinst -j

  odbcinst -q -d | grep "ODBC Driver 18 for SQL Server"

  which docker
  which python
  which uv
  which az
  which kubectl
  which helm
  which kubelogin
}

main() {
  if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
  fi

  ensure_ubuntu
  require_bootstrap_commands

  install_apt_prerequisites
  require_command gpg
  require_command lsb_release
  register_microsoft_packages_repo
  register_azure_cli_repo
  register_helm_repo
  install_apt_packages
  configure_docker_access
  install_docker_buildx_if_needed
  install_uv
  install_kubectl_and_kubelogin
  verify_installed_commands
}

main "$@"
