#!/bin/bash
# setup-caddy.sh - Automated Caddy Web Server installation and configuration script.
# This script installs Caddy, configures the reverse proxy for Next.js + FastAPI,
# and initiates Automatic HTTPS.
#
# Usage: sudo ./setup-caddy.sh [-d domain.com] [-n]

set -e

# Defaults
DOMAIN=""
NON_INTERACTIVE=false

# Print header
echo "========================================="
echo "   OdysseyAI Caddy Setup & Automation   "
echo "========================================="

# Helper functions
log_info() {
    echo -e "\e[34m[INFO]\e[0m $1"
}

log_success() {
    echo -e "\e[32m[SUCCESS]\e[0m $1"
}

log_warn() {
    echo -e "\e[33m[WARNING]\e[0m $1"
}

log_error() {
    echo -e "\e[31m[ERROR]\e[0m $1" >&2
}

# Parse command line options
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -d|--domain) DOMAIN="$2"; shift ;;
        -n|--non-interactive) NON_INTERACTIVE=true ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -d, --domain <domain>    Target deployment domain (e.g., travel.odyssey.ai)"
            echo "  -n, --non-interactive    Run non-interactively without user prompts"
            echo "  -h, --help               Show this help message"
            exit 0
            ;;
        *) log_error "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Ensure script is run with root privileges
if [ "$EUID" -ne 0 ]; then
    log_error "Please run this script as root or with sudo."
    exit 1
fi

# Verify we are on a supported Debian/Ubuntu platform (Caddy installation target)
if [ -f /etc/debian_version ]; then
    log_info "Debian/Ubuntu system detected. Proceeding with installation steps..."
else
    log_warn "This script is optimized for Debian/Ubuntu systems. Package installation may fail on other distributions."
fi

# 1. Install Caddy if not already present
if ! command -v caddy &> /dev/null; then
    log_info "Caddy is not installed. Installing Caddy..."
    
    # Update APT and install dependencies
    apt-get update -qq
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gpg -qq >/dev/null
    
    # Download Caddy GPG Key and add to sources
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg --yes
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    
    # Update packages and install Caddy
    apt-get update -qq
    apt-get install caddy -y -qq >/dev/null
    
    log_success "Caddy installed successfully."
else
    log_info "Caddy is already installed on this machine ($(caddy version | awk '{print $1}'))."
fi

# 2. Configure Caddyfile
log_info "Configuring Caddyfile..."

# Ensure we are in the project root directory where the Caddyfile exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -f "$PROJECT_ROOT/Caddyfile" ]; then
    log_error "Could not find Caddyfile template in $PROJECT_ROOT."
    exit 1
fi

# If domain is not provided and we are in interactive mode, prompt the user
if [ -z "$DOMAIN" ] && [ "$NON_INTERACTIVE" = false ]; then
    read -p "Enter your target deployment domain (leave blank for localhost): " DOMAIN
fi

# Prepare target configuration
TARGET_CADDYFILE="/etc/caddy/Caddyfile"

# Create backup of current Caddyfile if it exists
if [ -f "$TARGET_CADDYFILE" ]; then
    cp "$TARGET_CADDYFILE" "${TARGET_CADDYFILE}.bak"
    log_info "Existing Caddyfile backed up to ${TARGET_CADDYFILE}.bak"
fi

# Write configuration
if [ -n "$DOMAIN" ]; then
    log_info "Replacing placeholder with domain: $DOMAIN"
    sed "s/{\$DEPLOY_DOMAIN:localhost}/$DOMAIN/g" "$PROJECT_ROOT/Caddyfile" > "$TARGET_CADDYFILE"
else
    log_info "No domain specified. Defaulting to localhost config."
    sed "s/{\$DEPLOY_DOMAIN:localhost}/localhost/g" "$PROJECT_ROOT/Caddyfile" > "$TARGET_CADDYFILE"
fi

# 3. Validate Caddyfile Configuration
log_info "Validating Caddy configuration..."
if caddy validate --config "$TARGET_CADDYFILE" &> /dev/null; then
    log_success "Caddyfile configuration validation passed."
else
    log_error "Caddyfile configuration validation failed. Reverting to backup."
    if [ -f "${TARGET_CADDYFILE}.bak" ]; then
        mv "${TARGET_CADDYFILE}.bak" "$TARGET_CADDYFILE"
    fi
    exit 1
fi

# 4. Reload Caddy Service
log_info "Reloading Caddy service..."
if command -v systemctl &> /dev/null && systemctl is-active --quiet caddy; then
    systemctl reload caddy
    log_success "Caddy service reloaded successfully."
else
    # Fallback if systemd is not present or service is not running
    log_warn "Caddy systemd service not running. Starting Caddy directly in background..."
    caddy stop &>/dev/null || true
    caddy start --config "$TARGET_CADDYFILE"
    log_success "Caddy background service started."
fi

echo "========================================="
if [ -n "$DOMAIN" ]; then
    log_success "Deployment automated at: https://$DOMAIN"
    log_info "Make sure your domain's DNS A/AAAA records point to this server's public IP address."
else
    log_success "Deployment automated at: http://localhost"
fi
echo "========================================="
