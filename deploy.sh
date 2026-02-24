#!/bin/bash

# Energy Enterprise Platform - Quick Deploy Script
# Run this on your AWS EC2 instance

set -e

echo "=========================================="
echo "Energy Enterprise Platform - Deployment"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_warning "Running as non-root user. Some operations may require sudo."
fi

# Step 1: Install Docker
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi
print_status "Docker installed"

# Step 2: Install Docker Compose
print_status "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi
print_status "Docker Compose installed"

# Step 3: Enable and start Docker
print_status "Starting Docker..."
sudo systemctl enable docker
sudo systemctl start docker

# Step 4: Clone repository (if not already present)
if [ ! -d "/opt/Energy-Enterprise" ]; then
    print_status "Cloning repository..."
    sudo mkdir -p /opt
    cd /opt
    echo "Enter your repository URL:"
    read -r REPO_URL
    sudo git clone "$REPO_URL" Energy-Enterprise
else
    print_warning "Repository already exists at /opt/Energy-Enterprise"
    cd /opt/Energy-Enterprise
    print_status "Pulling latest changes..."
    sudo git pull
fi

cd /opt/Energy-Enterprise

# Step 5: Setup environment file
if [ ! -f ".env" ]; then
    print_status "Creating environment file..."
    sudo cp .env.example .env 2>/dev/null || echo "Please create .env file manually"
fi

# Step 6: Build services
print_status "Building Docker services..."
sudo docker-compose build

# Step 7: Start services
print_status "Starting services..."
sudo docker-compose up -d

# Step 8: Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Step 9: Check service status
print_status "Checking service status..."
sudo docker-compose ps

# Step 10: Display access information
echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  - Web UI:        http://$(curl -s ifconfig.me):3000"
echo "  - Device API:    http://$(curl -s ifconfig.me):8000"
echo "  - Data Service:  http://$(curl -s ifconfig.me):8081"
echo "  - Reports API:   http://$(curl -s ifconfig.me):8085"
echo "  - InfluxDB:      http://$(curl -s ifconfig.me):8086"
echo "  - MinIO Console: http://$(curl -s ifconfig.me):9001"
echo "  - MQTT Broker:   mqtt://$(curl -s ifconfig.me):1883"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop:      docker-compose down"
echo "=========================================="
