# Multi-Turn Evaluation Engine Deployment Guide

This guide provides comprehensive instructions for deploying the Multi-Turn Evaluation Engine in production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Security Considerations](#security-considerations)
7. [Scaling and Performance](#scaling-and-performance)
8. [Backup and Recovery](#backup-and-recovery)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: Minimum 4 cores, recommended 8+ cores
- **Memory**: Minimum 8GB RAM, recommended 16GB+ RAM
- **Storage**: Minimum 100GB, recommended 500GB+ SSD
- **Network**: Stable internet connection with sufficient bandwidth

### Software Requirements

- Docker 20.10+ and Docker Compose 2.0+
- Kubernetes 1.24+ (for Kubernetes deployment)
- PostgreSQL 13+ (external or containerized)
- Redis 6+ (external or containerized)
- SSL/TLS certificates for HTTPS

### Dependencies

- Python 3.11+
- Node.js 18+ (for frontend components, if applicable)
- Git (for source code management)

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Application Configuration
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
APP_NAME="Multi-Turn Evaluation Engine"
APP_VERSION=1.0.0

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=evaluation_engine
DB_USER=eval_user
DB_PASSWORD=your_secure_password_here
DB_SSL_MODE=require

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password_here
REDIS_DB=0

# Security Configuration
SECRET_KEY=your_very_long_secret_key_at_least_32_characters
JWT_SECRET=your_jwt_secret_key_at_least_32_characters
JWT_EXPIRATION_HOURS=24
CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com

# Performance Configuration
MAX_CONCURRENT_EVALUATIONS=10
WORKER_PROCESSES=4
WORKER_THREADS=8
CACHE_SIZE_MB=512
CACHE_TTL_SECONDS=3600

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_TRACING=true

# Storage Configuration
RESULTS_STORAGE_TYPE=filesystem
RESULTS_STORAGE_PATH=/app/results
MAX_RESULT_SIZE_MB=100
RETENTION_DAYS=30
```

### SSL/TLS Certificates

Generate SSL certificates for HTTPS:

```bash
# For production, use certificates from a trusted CA
# For testing, generate self-signed certificates:
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=evaluation-engine.your-domain.com"
```

## Docker Deployment

### Quick Start with Docker Compose

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/evaluation-engine.git
   cd evaluation-engine
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Build and start services:**
   ```bash
   docker-compose -f deployment/docker-compose.yml up -d
   ```

4. **Verify deployment:**
   ```bash
   curl http://localhost:8000/health
   ```

### Production Docker Compose

For production deployment, use the production compose file:

```bash
# Start production stack
docker-compose -f deployment/docker-compose.yml -f deployment/docker-compose.prod.yml up -d

# View logs
docker-compose logs -f evaluation-engine

# Scale workers
docker-compose up -d --scale evaluation-worker=4
```

### Docker Build Options

Build with specific optimizations:

```bash
# Build production image
docker build -f deployment/Dockerfile -t evaluation-engine:latest .

# Build with specific Python version
docker build --build-arg PYTHON_VERSION=3.11 -t evaluation-engine:3.11 .

# Multi-architecture build
docker buildx build --platform linux/amd64,linux/arm64 -t evaluation-engine:latest .
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster 1.24+
- kubectl configured
- Helm 3+ (optional, for package management)
- Ingress controller (nginx, traefik, etc.)
- Storage classes configured

### Step-by-Step Deployment

1. **Create namespace and RBAC:**
   ```bash
   kubectl apply -f deployment/kubernetes/namespace.yaml
   ```

2. **Create secrets:**
   ```bash
   # Update secrets with your values
   kubectl apply -f deployment/kubernetes/secrets.yaml
   ```

3. **Create ConfigMaps:**
   ```bash
   kubectl apply -f deployment/kubernetes/configmap.yaml
   ```

4. **Create persistent volumes:**
   ```bash
   kubectl apply -f deployment/kubernetes/pvc.yaml
   ```

5. **Deploy applications:**
   ```bash
   kubectl apply -f deployment/kubernetes/deployment.yaml
   ```

6. **Create services:**
   ```bash
   kubectl apply -f deployment/kubernetes/service.yaml
   ```

7. **Verify deployment:**
   ```bash
   kubectl get pods -n evaluation-engine
   kubectl get services -n evaluation-engine
   ```

### Helm Deployment (Alternative)

If using Helm:

```bash
# Add repository
helm repo add evaluation-engine https://charts.evaluation-engine.com
helm repo update

# Install
helm install evaluation-engine evaluation-engine/evaluation-engine \
  --namespace evaluation-engine \
  --create-namespace \
  --values values.yaml
```

### Ingress Configuration

Configure ingress for external access:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: evaluation-engine-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.evaluation-engine.com
    secretName: evaluation-engine-tls
  rules:
  - host: api.evaluation-engine.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: evaluation-engine-service
            port:
              number: 8000
```

## Monitoring and Observability

### Prometheus and Grafana

1. **Deploy monitoring stack:**
   ```bash
   # Using kube-prometheus-stack
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install monitoring prometheus-community/kube-prometheus-stack \
     --namespace monitoring \
     --create-namespace
   ```

2. **Configure ServiceMonitor:**
   ```bash
   kubectl apply -f deployment/monitoring/servicemonitor.yaml
   ```

3. **Import Grafana dashboards:**
   - Dashboard ID: 12345 (Evaluation Engine Overview)
   - Dashboard ID: 12346 (Performance Metrics)
   - Dashboard ID: 12347 (Error Analysis)

### Logging

Configure centralized logging:

```bash
# Deploy ELK stack or use cloud logging
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch --namespace logging --create-namespace
helm install kibana elastic/kibana --namespace logging
helm install filebeat elastic/filebeat --namespace logging
```

### Tracing

Enable distributed tracing with Jaeger:

```bash
# Deploy Jaeger
kubectl create namespace observability
kubectl apply -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.41.0/jaeger-operator.yaml -n observability
```

## Security Considerations

### Network Security

1. **Use TLS everywhere:**
   - Enable HTTPS for all external communication
   - Use TLS for internal service communication
   - Configure proper cipher suites

2. **Network policies:**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: evaluation-engine-netpol
   spec:
     podSelector:
       matchLabels:
         app: evaluation-engine
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: nginx-ingress
       ports:
       - protocol: TCP
         port: 8000
   ```

### Authentication and Authorization

1. **API Key management:**
   - Rotate API keys regularly
   - Use different keys for different environments
   - Implement key-based rate limiting

2. **JWT configuration:**
   - Use strong secrets
   - Set appropriate expiration times
   - Implement token refresh mechanisms

### Data Protection

1. **Encryption at rest:**
   - Encrypt database storage
   - Encrypt file system storage
   - Use encrypted backups

2. **Encryption in transit:**
   - TLS 1.2+ for all communications
   - Certificate pinning where applicable
   - Secure WebSocket connections

### Security Scanning

Regular security assessments:

```bash
# Container scanning
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image evaluation-engine:latest

# Kubernetes security scanning
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml
```

## Scaling and Performance

### Horizontal Scaling

1. **API servers:**
   ```bash
   kubectl scale deployment evaluation-engine --replicas=5 -n evaluation-engine
   ```

2. **Workers:**
   ```bash
   kubectl scale deployment evaluation-worker --replicas=10 -n evaluation-engine
   ```

### Vertical Scaling

Update resource limits:

```yaml
resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 4000m
    memory: 8Gi
```

### Auto-scaling

Configure Horizontal Pod Autoscaler:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: evaluation-engine-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: evaluation-engine
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Performance Optimization

1. **Database optimization:**
   - Configure connection pooling
   - Optimize queries and indexes
   - Use read replicas for read-heavy workloads

2. **Caching strategy:**
   - Configure Redis clustering
   - Implement cache warming
   - Monitor cache hit rates

3. **Load balancing:**
   - Use session affinity where needed
   - Configure health checks
   - Implement circuit breakers

## Backup and Recovery

### Database Backups

1. **Automated backups:**
   ```bash
   # PostgreSQL backup script
   #!/bin/bash
   BACKUP_DIR="/backups/postgres"
   DATE=$(date +%Y%m%d_%H%M%S)
   
   pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > $BACKUP_DIR/backup_$DATE.sql
   
   # Compress and upload to S3
   gzip $BACKUP_DIR/backup_$DATE.sql
   aws s3 cp $BACKUP_DIR/backup_$DATE.sql.gz s3://your-backup-bucket/postgres/
   ```

2. **Point-in-time recovery:**
   - Configure WAL archiving
   - Set up continuous archiving
   - Test recovery procedures

### Application Data Backups

1. **Results and artifacts:**
   ```bash
   # Backup evaluation results
   kubectl create job backup-results --from=cronjob/backup-results -n evaluation-engine
   ```

2. **Configuration backups:**
   ```bash
   # Backup Kubernetes resources
   kubectl get all,configmap,secret -n evaluation-engine -o yaml > backup.yaml
   ```

### Disaster Recovery

1. **Multi-region deployment:**
   - Deploy in multiple availability zones
   - Use cross-region database replication
   - Implement DNS failover

2. **Recovery procedures:**
   - Document recovery steps
   - Test recovery regularly
   - Maintain recovery time objectives (RTO)

## Troubleshooting

### Common Issues

1. **Service won't start:**
   ```bash
   # Check logs
   kubectl logs -f deployment/evaluation-engine -n evaluation-engine
   
   # Check configuration
   kubectl describe configmap evaluation-engine-config -n evaluation-engine
   
   # Check secrets
   kubectl get secrets -n evaluation-engine
   ```

2. **Database connection issues:**
   ```bash
   # Test database connectivity
   kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
     psql -h postgres-service -U eval_user -d evaluation_engine
   ```

3. **Performance issues:**
   ```bash
   # Check resource usage
   kubectl top pods -n evaluation-engine
   
   # Check metrics
   curl http://localhost:9090/metrics
   ```

### Health Checks

Monitor service health:

```bash
# API health check
curl -f http://localhost:8000/health

# Database health check
kubectl exec -it postgres-0 -- pg_isready

# Redis health check
kubectl exec -it redis-0 -- redis-cli ping
```

### Log Analysis

Common log patterns to monitor:

```bash
# Error patterns
kubectl logs -f deployment/evaluation-engine | grep -i error

# Performance patterns
kubectl logs -f deployment/evaluation-engine | grep "duration"

# Security patterns
kubectl logs -f deployment/evaluation-engine | grep -i "unauthorized\|forbidden"
```

### Support and Maintenance

1. **Regular maintenance:**
   - Update dependencies monthly
   - Rotate secrets quarterly
   - Review and update configurations

2. **Monitoring and alerting:**
   - Set up comprehensive alerting
   - Monitor key performance indicators
   - Implement automated remediation where possible

3. **Documentation:**
   - Keep deployment documentation updated
   - Document configuration changes
   - Maintain runbooks for common issues

For additional support, consult the [Operations Manual](OPERATIONS_MANUAL.md) or contact the development team.