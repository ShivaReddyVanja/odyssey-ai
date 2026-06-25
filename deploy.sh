#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

# Load user profile configurations to ensure NVM, Node, and PM2 are in the PATH
for profile in ~/.bashrc ~/.profile ~/.bash_profile; do
    if [ -f "$profile" ]; then
        source "$profile"
    fi
done

echo "========================================="
echo "Starting PM2 Deployment in ~/odyssey-ai"
echo "========================================="

# Navigate to application root
cd ~/odyssey-ai

# 1. Pull latest code from main
echo "Pulling latest updates from main..."
git fetch origin main
git reset --hard origin/main

# 2. Update Backend Virtual Env & Dependencies
echo "Updating backend Python virtual environment..."
cd backend

# Recreate venv if it does not exist or is in a broken/incomplete state
if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ]; then
    echo "Creating virtual environment..."
    rm -rf venv
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing requirements..."
pip install -r requirements.txt
cd ..

# 3. Update Frontend Dependencies & Build Production Bundle
echo "Installing npm dependencies and building Next.js bundle..."
npm install
cd frontend
npm install
if [ -n "$DEPLOY_DOMAIN" ]; then
    echo "Injecting NEXT_PUBLIC_API_URL=https://$DEPLOY_DOMAIN for production build..."
    NODE_OPTIONS="--max-old-space-size=1536" NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_API_URL="https://$DEPLOY_DOMAIN" npm run build
else
    echo "No DEPLOY_DOMAIN specified, building Next.js frontend with default API URL..."
    NODE_OPTIONS="--max-old-space-size=1536" NEXT_TELEMETRY_DISABLED=1 npm run build
fi
cd ..

# 4. Reload Services with PM2
echo "Reloading PM2 processes..."
if command -v pm2 &> /dev/null; then
    pm2 startOrReload ecosystem.config.js --update-env
    echo "PM2 processes reloaded successfully."
else
    echo "ERROR: PM2 is not installed or not in PATH on this machine."
    exit 1
fi

# 5. Automate Web Server / Reverse Proxy Setup (Caddy)
if [ -n "$DEPLOY_DOMAIN" ]; then
    echo "Reloading Caddy configuration for: $DEPLOY_DOMAIN..."
    export DEPLOY_DOMAIN
    if command -v caddy &> /dev/null; then
        caddy reload --config Caddyfile
        echo "Caddy configuration reloaded successfully."
    else
        echo "WARNING: Caddy is not installed or not in PATH on this server."
        echo "An administrator should install Caddy once using 'sudo ./scripts/setup-caddy.sh --domain $DEPLOY_DOMAIN'."
    fi
else
    echo "Skipping Caddy reverse proxy setup (DEPLOY_DOMAIN not specified)."
fi

echo "========================================="
echo "Deployment completed successfully."
echo "========================================="
