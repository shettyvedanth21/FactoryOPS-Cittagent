# Energy Enterprise Platform - Deployment Guide

This document provides step-by-step instructions for deploying the Energy Enterprise IoT platform on AWS using Git.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [AWS Infrastructure Setup](#aws-infrastructure-setup)
4. [Project Deployment](#project-deployment)
5. [Service Configuration](#service-configuration)
6. [Device Onboarding](#device-onboarding)
7. [Verification](#verification)

---

## Architecture Overview

The platform consists of 11 microservices:

| Service | Port | Purpose |
|---------|------|---------|
| MySQL | 3306 | Relational database |
| InfluxDB | 8086 | Time-series telemetry storage |
| MinIO | 9000/9001 | S3-compatible object storage |
| EMQX | 1883/8083 | MQTT broker |
| device-service | 8000 | Device management |
| data-service | 8081 | Telemetry ingestion |
| rule-engine-service | 8002 | Alert rule processing |
| analytics-service | 8003 | Analytics & ML |
| data-export-service | 8080 | Data export |
| reporting-service | 8085 | Report generation |
| ui-web | 3000 | Web UI |

---

## Prerequisites

### Required Tools
```bash
# Install on local machine
- Git
- Docker & Docker Compose
- AWS CLI (configured with credentials)
- SSH key pair for EC2 access
```

### AWS Account Requirements
- EC2 instance (t3.medium or larger recommended)
- Security groups with ports open: 22, 80, 443, 3000, 8000-9001
- EFS or EBS for persistent storage (optional)

---

## AWS Infrastructure Setup

### Step 1: Launch EC2 Instance
```bash
# Using AWS Console or CLI
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.large \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxx \
  --subnet-id subnet-xxxxx \
  --user-data file://user-data.sh
```

### Step 2: Create Security Group
```bash
aws ec2 create-security-group \
  --group-name energy-platform-sg \
  --description "Security group for Energy Platform"

# Open required ports
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# For demo access (restrict in production)
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 3000-9001 \
  --cidr 0.0.0.0/0
```

### Step 3: User Data Script (cloud-init)
```bash
#!/bin/bash
apt-get update
apt-get install -y docker.io docker-compose git curl

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Enable Docker
systemctl enable docker
systemctl start docker

# Clone project (replace with your repository)
cd /opt
git clone https://github.com/your-repo/Energy-Enterprise.git
cd Energy-Enterprise

# Start services
docker-compose up -d

# Optional: Setup Nginx reverse proxy
apt-get install -y nginx
# Configure nginx for HTTPS/load balancing
```

---

## Project Deployment

### Step 1: Clone Repository
```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Clone the repository
cd /opt
git clone https://github.com/your-org/Energy-Enterprise.git
cd Energy-Enterprise
```

### Step 2: Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with production values
nano .env
```

### Required Environment Variables
```bash
# Database
MYSQL_ROOT_PASSWORD=secure_root_password
MYSQL_USER=energy
MYSQL_PASSWORD=secure_energy_password
MYSQL_DATABASE=energy_platform_db

# InfluxDB
INFLUXDB_TOKEN=your-secure-token
INFLUXDB_ORG=energy-org
INFLUXDB_BUCKET=telemetry

# MinIO/S3
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=secure-minio-password
S3_BUCKET=energy-platform-datasets

# MQTT
MQTT_BROKER_HOST=emqx
MQTT_BROKER_PORT=1883

# External URLs (for production)
EXTERNAL_URL=https://your-domain.com
```

### Step 3: Build and Start Services
```bash
# Build all services
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### Step 4: Initialize Databases
```bash
# Wait for MySQL to be ready
docker-compose exec mysql mysqladmin ping -u root -p

# Run initialization scripts (if any)
docker-compose exec mysql mysql -u root -p < init-scripts/mysql/init.sql
```

---

## Service Configuration

### Database Initialization
```bash
# Connect to MySQL
docker-compose exec mysql mysql -u energy -p

# Create databases
CREATE DATABASE energy_device_db;
CREATE DATABASE energy_rule_db;
CREATE DATABASE energy_analytics_db;
CREATE DATABASE energy_export_db;
CREATE DATABASE energy_reporting_db;
```

### InfluxDB Setup
```bash
# Access InfluxDB UI at http://your-ip:8086
# Use credentials from docker-compose or .env

# Create bucket (if not auto-created)
influx bucket create -n telemetry -o energy-org
```

### MinIO Setup
```bash
# Access MinIO Console at http://your-ip:9001
# Create bucket: energy-platform-datasets

# Or via CLI
docker-compose exec minio mc mb local/energy-platform-datasets
```

---

## Device Onboarding

### Method 1: Via REST API

```bash
# Create a new device
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "METER-001",
    "device_name": "Building A Main Meter",
    "device_type": "meter",
    "phase_type": "three",
    "location": "Building A",
    "metadata": {
      "manufacturer": "Schneider",
      "model": "PM5560"
    }
  }'
```

### Method 2: Via Web UI
1. Navigate to `http://your-ip:3000`
2. Login with admin credentials
3. Go to Devices → Add Device
4. Fill in device details

### Method 3: MQTT Auto-Registration
Devices can auto-register by publishing to:
```
Topic: devices/{device_id}/register
Payload: {
  "device_name": "Device Name",
  "device_type": "meter",
  "phase_type": "three"
}
```

### Device Types
- `meter` / `power_meter` / `energy_meter` - For energy reporting
- `sensor` - Temperature, humidity, etc.
- `switch` - On/Off control
- `inverter` - Solar inverters

---

## Connecting Devices

### MQTT Connection Details
```
Broker: mqtt://your-ec2-ip:1883
Protocol: MQTT v3.1.1
Username: (none required - anonymous enabled)
Password: (none)
```

### Telemetry Payload Format
```json
{
  "device_id": "METER-001",
  "timestamp": "2026-02-24T10:00:00Z",
  "power": 1500.5,
  "voltage": 230.0,
  "current": 6.5,
  "power_factor": 0.95,
  "reactive_power": 500.0,
  "frequency": 50.0,
  "thd": 3.2
}
```

### Publish Telemetry
```bash
# Using mosquitto_pub
mosquitto_pub -h your-ec2-ip -p 1883 \
  -t telemetry/METER-001 \
  -m '{"power":1500.5,"voltage":230.0,"current":6.5,"power_factor":0.95}'
```

---

## Verification

### Check All Services
```bash
# Docker compose status
docker-compose ps

# Individual service logs
docker-compose logs -f device-service
docker-compose logs -f data-service
docker-compose logs -f reporting-service
```

### Health Checks
```bash
# MySQL
curl http://localhost:8000/health

# Device Service
curl http://localhost:8000/health

# Data Service
curl http://localhost:8081/health

# Reporting Service
curl http://localhost:8085/health

# InfluxDB
curl http://localhost:8086/health
```

### Test Report Generation
```bash
# Create consumption report
curl -X POST http://localhost:8085/api/reports/energy/consumption \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["METER-001"],
    "tenant_id": "tenant-001",
    "start_date": "2026-02-20",
    "end_date": "2026-02-24"
  }'

# Check status
curl "http://localhost:8085/api/reports/{report_id}/status?tenant_id=tenant-001"

# Download PDF
curl -o report.pdf "http://localhost:8085/api/reports/{report_id}/download?tenant_id=tenant-001"
```

---

## Production Considerations

### Security
1. **Enable HTTPS** - Use Nginx with SSL/TLS certificates
2. **Restrict MQTT** - Add authentication to EMQX
3. **Secure MySQL** - Change default passwords
4. **MinIO** - Enable SSL and access keys
5. **Firewall** - Restrict IP access

### Monitoring
```bash
# Setup Docker logs rotation
# Add to /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### Backup
```bash
# Backup MySQL
docker-compose exec mysqldump -u root -p energy_device_db > backup.sql

# Backup InfluxDB
influx backup /backup/influxdb
```

### Scaling
- Use AWS ECS/EKS for auto-scaling
- Separate services to different EC2 instances
- Use RDS for MySQL (managed)
- Use AWS InfluxDB (managed)
- Use S3 for object storage

---

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   docker-compose logs <service-name>
   docker-compose restart <service-name>
   ```

2. **Database connection errors**
   ```bash
   # Check MySQL is ready
   docker-compose exec mysql mysqladmin ping
   
   # Check connectivity between services
   docker-compose exec data-service ping mysql
   ```

3. **MQTT devices not connecting**
   ```bash
   # Check EMQX status
   docker-compose logs emqx
   
   # Check port accessibility
   telnet your-ec2-ip 1883
   ```

4. **Report generation failing**
   ```bash
   # Check InfluxDB has data
   docker-compose exec influxdb influx
   
   # Check reporting service logs
   docker-compose logs reporting-service
   ```

---

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- Review API documentation at `/api/docs`
- Check platform documentation: `PLATFORM_DOCUMENTATION.md`
