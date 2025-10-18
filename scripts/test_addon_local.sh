#!/usr/bin/env bash
# Test AquaBle add-on locally

set -euo pipefail

echo "🧪 Testing AquaBle add-on locally"

# Build frontend first
echo "📦 Building frontend..."
cd frontend
npm ci
npm run build
cd ..

# Prepare build context
echo "🔧 Preparing build context..."
mkdir -p aquable/frontend
cp -r frontend/dist aquable/frontend/

# Build the add-on using Home Assistant builder
echo "🏗️  Building add-on..."
if command -v docker >/dev/null 2>&1; then
    # Use docker run to execute home-assistant/builder
    docker run --rm \
        -v "$(pwd)":/data \
        -v /var/run/docker.sock:/var/run/docker.sock \
        homeassistant/amd64-builder:latest \
        --target aquable \
        --docker-hub ghcr.io/caleb-venner \
        --version dev

    echo "✅ Add-on built successfully!"
    echo "📋 To install locally:"
    echo "   1. Copy aquable/ to your HA add-ons repository"
    echo "   2. Restart HA and install from add-on store"
else
    echo "❌ Docker not found. Please install Docker to build the add-on."
    echo "   Alternative: Use GitHub Actions to build automatically."
fi

# Optional: Test with HA CLI if available
if command -v ha >/dev/null 2>&1; then
    echo "🔍 HA CLI found - checking for local HA instance..."
    if ha core info >/dev/null 2>&1; then
        echo "🏠 Local HA instance detected"
        echo "💡 To test the add-on:"
        echo "   1. Copy built add-on to HA add-ons directory"
        echo "   2. Run: ha addons install aquable"
        echo "   3. Run: ha addons start aquable"
        echo "   4. Check logs: ha addons logs aquable"
    else
        echo "ℹ️  HA CLI available but no local instance detected"
    fi
else
    echo "ℹ️  HA CLI not installed. Install with: pip install homeassistant-cli"
fi

echo "🎉 Local testing setup complete!"