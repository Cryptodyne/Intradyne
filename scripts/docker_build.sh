#!/bin/bash

echo "🐳 Building Docker Image"
echo "========================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi

# Build image
echo "Building image..."
docker build -t intradyne/trading:latest .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "Image details:"
    docker images intradyne/trading:latest
    echo ""
    echo "To run:"
    echo "  docker run -p 8501:8501 intradyne/trading:latest"
    echo ""
    echo "Or use docker-compose:"
    echo "  docker-compose up"
else
    echo ""
    echo "❌ Build failed"
    exit 1
fi
