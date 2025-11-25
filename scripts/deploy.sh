#!/bin/bash

echo "🚀 Deploying Intradyne Trading System"
echo "======================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not installed"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose not installed"; exit 1; }
echo "✅ Prerequisites OK"
echo ""

# Check .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env with your configuration before continuing"
    echo "Press Enter to continue or Ctrl+C to exit..."
    read
fi

# Create directories
echo "Creating directories..."
mkdir -p data/logs data/cache config logs monitoring/grafana
echo "✅ Directories created"
echo ""

# Build Docker image
echo "Building Docker image..."
docker-compose build
if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi
echo "✅ Docker image built"
echo ""

# Start services
echo "Starting services..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo "❌ Failed to start services"
    exit 1
fi
echo "✅ Services started"
echo ""

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check status
echo "Checking service status..."
docker-compose ps
echo ""

# Show logs
echo "Recent logs:"
docker-compose logs --tail=20
echo ""

echo "======================================"
echo "✅ Deployment complete!"
echo "======================================"
echo ""
echo "📊 Access Points:"
echo "   Trading Dashboard: http://localhost:8501"
echo "   Grafana: http://localhost:3000 (admin/admin)"
echo "   Prometheus: http://localhost:9090"
echo ""
echo "📝 Useful Commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop: docker-compose down"
echo "   Restart: docker-compose restart"
echo "   Status: docker-compose ps"
echo ""
