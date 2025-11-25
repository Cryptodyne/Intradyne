# Docker Containerization Guide

## Overview

The Intradyne trading system is fully containerized with Docker for easy deployment and scalability.

---

## Quick Start

### Build Image
```bash
docker build -t intradyne/trading:latest .
```

### Run Container
```bash
docker run -d \
  --name intradyne \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  --env-file .env \
  intradyne/trading:latest
```

### Using Docker Compose (Recommended)
```bash
docker-compose up -d
```

---

## Docker Image Details

### Multi-Stage Build

**Stage 1: Builder**
- Installs build dependencies
- Compiles Python packages
- Creates optimized wheel files

**Stage 2: Runtime**
- Minimal Python slim image
- Copies only necessary files
- Non-root user for security
- Health checks enabled

### Image Size
- **Builder stage**: ~800 MB
- **Final image**: ~400 MB
- **Compressed**: ~150 MB

---

## Configuration

### Environment Variables

```bash
# Required
ENVIRONMENT=production
EXCHANGE_NAME=bitget

# Optional
REDIS_HOST=redis
POSTGRES_HOST=postgres
LOG_LEVEL=INFO
```

### Volumes

```yaml
volumes:
  - ./data:/app/data        # Trading data
  - ./config:/app/config    # Configuration
  - ./logs:/app/logs        # Log files
```

---

## Services

### Main Application
- **Port**: 8501 (Streamlit)
- **Health Check**: Every 30s
- **Restart**: unless-stopped

### Redis Cache
- **Port**: 6379
- **Persistence**: Enabled
- **Volume**: redis-data

### PostgreSQL Database
- **Port**: 5432
- **Database**: intradyne
- **Volume**: postgres-data

### Prometheus Monitoring
- **Port**: 9090
- **Config**: monitoring/prometheus.yml

### Grafana Dashboards
- **Port**: 3000
- **Default**: admin/admin

---

## Docker Compose Commands

### Start Services
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f
docker-compose logs -f intradyne  # Specific service
```

### Stop Services
```bash
docker-compose stop
```

### Remove Everything
```bash
docker-compose down -v  # Including volumes
```

### Restart Service
```bash
docker-compose restart intradyne
```

### Check Status
```bash
docker-compose ps
```

### Execute Commands
```bash
docker-compose exec intradyne bash
docker-compose exec postgres psql -U trader
```

---

## Health Checks

### Container Health
```bash
docker inspect --format='{{.State.Health.Status}}' intradyne
```

### Manual Health Check
```bash
docker exec intradyne /app/scripts/health_check.sh
```

### Health Check Endpoint
```bash
curl http://localhost:8501/healthz
```

---

## Resource Limits

### CPU & Memory
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

### Monitoring Resources
```bash
docker stats intradyne
```

---

## Networking

### Default Network
- **Name**: trading-network
- **Driver**: bridge
- **Isolation**: Container-to-container

### Port Mapping
- 8501 → Streamlit UI
- 9090 → Prometheus
- 3000 → Grafana
- 6379 → Redis (internal)
- 5432 → PostgreSQL (internal)

---

## Security

### Non-Root User
```dockerfile
RUN useradd -m -u 1000 trader
USER trader
```

### Secrets Management
- Use `.env` file (not committed)
- Environment variables
- Docker secrets (Swarm)
- Kubernetes secrets

### Network Isolation
- Internal network for services
- Only expose necessary ports
- Use reverse proxy (Nginx)

---

## Troubleshooting

### Container Won't Start
```bash
docker logs intradyne
docker inspect intradyne
```

### Permission Issues
```bash
docker exec intradyne ls -la /app/data
docker exec intradyne whoami
```

### Network Issues
```bash
docker network inspect trading-network
docker exec intradyne ping redis
```

### Database Connection
```bash
docker exec intradyne nc -zv postgres 5432
docker-compose exec postgres psql -U trader -d intradyne
```

### Clean Rebuild
```bash
docker-compose down -v
docker system prune -a
docker-compose build --no-cache
docker-compose up -d
```

---

## Production Deployment

### Build for Production
```bash
docker build \
  --build-arg ENVIRONMENT=production \
  --tag intradyne/trading:v1.0.0 \
  --tag intradyne/trading:latest \
  .
```

### Push to Registry
```bash
docker login
docker push intradyne/trading:v1.0.0
docker push intradyne/trading:latest
```

### Pull and Run
```bash
docker pull intradyne/trading:latest
docker-compose up -d
```

---

## Monitoring

### Container Metrics
```bash
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Logs
```bash
# Real-time
docker-compose logs -f --tail=100

# Export
docker-compose logs > logs/docker-$(date +%Y%m%d).log
```

### Health Status
```bash
docker-compose ps
docker inspect --format='{{.State.Health}}' intradyne
```

---

## Backup & Restore

### Backup Volumes
```bash
docker run --rm \
  -v intradyne_postgres-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres-$(date +%Y%m%d).tar.gz /data
```

### Restore Volumes
```bash
docker run --rm \
  -v intradyne_postgres-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/postgres-20250125.tar.gz -C /
```

---

## Performance Optimization

### Image Size
- Multi-stage builds
- Minimal base image
- .dockerignore file
- Layer caching

### Runtime Performance
- Resource limits
- Health checks
- Restart policies
- Volume optimization

### Network Performance
- Internal networking
- DNS caching
- Connection pooling

---

## Best Practices

1. **Always use .dockerignore**
2. **Multi-stage builds for smaller images**
3. **Non-root user for security**
4. **Health checks for reliability**
5. **Volume mounts for persistence**
6. **Environment variables for configuration**
7. **Docker Compose for multi-container apps**
8. **Regular image updates**
9. **Monitor resource usage**
10. **Backup volumes regularly**

---

**🐳 Docker containerization complete!**
