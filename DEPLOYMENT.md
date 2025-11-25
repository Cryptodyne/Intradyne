# Intradyne Trading System - Deployment Guide

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- 4GB+ RAM available
- 10GB+ disk space

### Deploy with Docker Compose

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd Intradyne
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Deploy**
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

4. **Access**
   - Trading Dashboard: http://localhost:8501
   - Grafana: http://localhost:3000
   - Prometheus: http://localhost:9090

---

## Configuration

### Exchange Setup

Edit `.env`:
```env
EXCHANGE_NAME=bitget
EXCHANGE_API_KEY=your_key
EXCHANGE_SECRET=your_secret
```

### Risk Management

```env
MAX_POSITIONS=5
STOP_LOSS_PCT=0.03
TAKE_PROFIT_PCT=0.10
DAILY_LOSS_LIMIT=0.05
```

---

## Monitoring

### Grafana Dashboards

1. Open http://localhost:3000
2. Login: admin/admin
3. Import dashboards from `monitoring/grafana/`

### Prometheus Metrics

- Trading metrics: http://localhost:9090
- Query examples:
  - `portfolio_equity`
  - `trades_total`
  - `strategy_performance`

---

## Maintenance

### View Logs
```bash
docker-compose logs -f intradyne
```

### Restart Services
```bash
docker-compose restart
```

### Stop System
```bash
docker-compose down
```

### Backup Data
```bash
docker-compose exec postgres pg_dump -U trader intradyne > backup.sql
tar -czf data-backup.tar.gz data/
```

---

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster
- kubectl configured
- Helm (optional)

### Deploy

1. **Create secrets**
   ```bash
   kubectl create secret generic intradyne-secrets \
     --from-env-file=.env
   ```

2. **Deploy**
   ```bash
   kubectl apply -f k8s/
   ```

3. **Check status**
   ```bash
   kubectl get pods -l app=intradyne
   kubectl get svc intradyne-service
   ```

---

## Troubleshooting

### Container won't start
```bash
docker-compose logs intradyne
docker-compose ps
```

### Database connection issues
```bash
docker-compose exec postgres psql -U trader -d intradyne
```

### Reset everything
```bash
docker-compose down -v
rm -rf data/
./scripts/deploy.sh
```

---

## Production Checklist

- [ ] Change default passwords in `.env`
- [ ] Set up SSL/TLS
- [ ] Configure backups
- [ ] Set up monitoring alerts
- [ ] Test disaster recovery
- [ ] Review security settings
- [ ] Enable logging
- [ ] Configure notifications

---

## Support

For issues and questions:
- Check logs: `docker-compose logs`
- Review documentation
- Check GitHub issues

---

**🚀 Happy Trading!**
