#!/bin/bash
# =============================================================================
# inventotrackV2 - Rebuild Script
# Run this on the VPS to rebuild everything from scratch
# =============================================================================

set -e

echo "=========================================="
echo "inventotrackV2 - Rebuild from Scratch"
echo "=========================================="

# Stop and remove all containers
echo "Stopping containers..."
docker compose down --volumes --remove-orphans

# Remove old images
echo "Removing old images..."
docker image rm inventotrackv2_web || true

# Build fresh images
echo "Building images..."
docker compose build --no-cache

# Start containers
echo "Starting containers..."
docker compose up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 30

# Check status
echo ""
echo "=========================================="
echo "Container Status:"
echo "=========================================="
docker compose ps

echo ""
echo "=========================================="
echo "Recent Logs:"
echo "=========================================="
docker compose logs --tail=20

echo ""
echo "=========================================="
echo "Done!"
echo "=========================================="
echo "Access the application at:"
echo "  - http://your-server-ip/admin/"
echo "  - http://your-server-ip/api/"
echo ""
echo "Default login:"
echo "  Username: admin"
echo "  Password: admin123"
