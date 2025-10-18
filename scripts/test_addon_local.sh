#!/usr/bin/env bash
# Build AquaBle add-on container image

set -euo pipefail

echo "🧪 Building AquaBle add-on container image"

# Build frontend first
echo "📦 Building frontend..."
cd frontend
npm install
npm run build
cd ..

# Prepare build context
echo "🔧 Preparing build context..."
mkdir -p aquable/frontend
cp -r frontend/dist aquable/frontend/

# Build the add-on container image
echo "🏗️  Building add-on container image..."
if command -v docker >/dev/null 2>&1; then
    # Detect if we're on Apple Silicon
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        echo "⚠️  Detected Apple Silicon (arm64) architecture"
        echo "💡 Local Docker builds for amd64 containers on ARM64 require docker buildx"
        echo "   The GitHub Actions workflow will build correctly for amd64."
        echo ""
        echo "To test locally on Apple Silicon:"
        echo "   1. Ensure you have docker buildx available (included with Docker Desktop)"
        echo "   2. Run: docker buildx build --platform linux/amd64 -f aquable/Dockerfile -t aquable:test ."
        echo ""
        echo "   Or verify your changes with: make test && make lint"
        exit 1
    fi
    
    docker build \
        -f aquable/Dockerfile \
        -t ghcr.io/caleb-venner/aquable:dev \
        .
    
    echo ""
    echo "✅ Add-on container image built successfully!"
    echo "   Image: ghcr.io/caleb-venner/aquable:dev"
else
    echo "❌ Docker not found. Please install Docker to build the add-on."
    exit 1
fi