# Container-Per-Ruleset Architecture

This document explains the **one container per rule set** architecture for the underwriting system.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [How It Works](#how-it-works)
- [API Examples](#api-examples)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

Instead of running a single Drools container with multiple KIE containers (logical rule sets), this architecture creates a **separate Docker/Kubernetes container for each rule set**.

### Benefits

✅ **Complete Isolation** - Each rule set runs in its own process space
✅ **Independent Scaling** - Scale busy rule sets independently
✅ **Version Flexibility** - Different Drools versions per rule set
✅ **Fault Isolation** - One rule set crashing doesn't affect others
✅ **Better Multi-tenancy** - Stronger isolation for different customers
✅ **Resource Control** - Set specific CPU/memory limits per rule set

### Trade-offs

⚠️ **Higher Resource Usage** - Each JVM uses ~500MB-1GB memory
⚠️ **Slower Cold Start** - Container/JVM startup overhead
⚠️ **More Complex** - Additional orchestration layer required

## Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────┐
│                    Backend Service                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Container Orchestrator                             │    │
│  │  - Creates new containers on deployment             │    │
│  │  - Tracks container registry (JSON file)            │    │
│  │  - Routes requests to correct container             │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────┬──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ drools-chase │ │ drools-bofa  │ │ drools-wells │
│ Port: 8081   │ │ Port: 8082   │ │ Port: 8083   │
│ Container:   │ │ Container:   │ │ Container:   │
│ chase-ins... │ │ bofa-loan... │ │ wells-mtg... │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Component Roles

1. **Backend Service** ([rule-agent/](rule-agent/))
   - Flask API for PDF upload, rule generation
   - Integrates LLM (OpenAI, Watsonx, etc.)
   - Manages deployment workflow

2. **Container Orchestrator** ([ContainerOrchestrator.py](rule-agent/ContainerOrchestrator.py))
   - Creates Docker containers or Kubernetes pods dynamically
   - Maintains service registry (container_id → endpoint mapping)
   - Handles container lifecycle (create, delete, health checks)

3. **Drools Containers** (one per rule set)
   - Standard KIE Server image: `quay.io/kiegroup/kie-server-showcase:latest`
   - Each hosts a single KIE container
   - Independent scaling and resource limits

4. **Service Registry** ([/data/container_registry.json](data/container_registry.json))
   - JSON file tracking all deployed containers
   - Maps container_id to endpoint URL
   - Persisted across backend restarts

## Getting Started

### Prerequisites

**For Docker:**
- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB+ RAM recommended (16GB+ for multiple rule sets)

**For Kubernetes:**
- Kubernetes 1.20+
- kubectl configured
- Storage class with ReadWriteMany support
- 16GB+ cluster capacity recommended

### Quick Start (Docker)

Container orchestration is **enabled by default**. Each rule set gets its own dedicated Drools container.

1. **Start the System**
```bash
docker-compose build
docker-compose up -d
```

2. **Verify Backend**
```bash
curl http://localhost:9000/rule-agent/health
```

3. **Deploy Your First Rule Set**
```bash
curl -X POST http://localhost:9000/rule-agent/deploy_from_pdf \
  -F "file=@insurance_policy.pdf" \
  -F "bank_id=chase-insurance" \
  -F "policy_type=life-insurance"
```

This will:
- Extract rules from PDF using AWS Textract
- Generate DRL rules using LLM
- Build KJar (Drools package)
- **Create new Docker container**: `drools-chase-insurance-underwriting-rules`
- Deploy rules to that container

4. **Verify New Container**
```bash
# List all containers
docker ps

# You should see:
# - backend
# - drools (default)
# - drools-chase-insurance-underwriting-rules (NEW!)

# Check container registry
curl http://localhost:9000/rule-agent/list_containers
```

## Docker Deployment

### Configuration

Container orchestration is **enabled by default** in [docker-compose.yml](docker-compose.yml):

```yaml
backend:
  environment:
    # Container orchestration (ENABLED by default)
    - USE_CONTAINER_ORCHESTRATOR=true
    - ORCHESTRATION_PLATFORM=docker
    - DOCKER_NETWORK=underwriting-net
  volumes:
    # Required for Docker-in-Docker
    - /var/run/docker.sock:/var/run/docker.sock
```

To disable and use shared container mode (not recommended), set `USE_CONTAINER_ORCHESTRATOR=false`.

### How Containers Are Created

When you deploy rules, the backend:

1. **Builds KJar** - Compiles DRL into JAR file
2. **Calls Orchestrator** - `orchestrator.create_drools_container(container_id, jar_path)`
3. **Orchestrator Creates Container**:
   ```python
   container = docker_client.containers.run(
       image="quay.io/kiegroup/kie-server-showcase:latest",
       name=f"drools-{container_id}",
       ports={'8080/tcp': next_available_port},
       network='underwriting-net',
       ...
   )
   ```
4. **Waits for Health** - Polls container until KIE Server is ready
5. **Registers Endpoint** - Saves to `/data/container_registry.json`
6. **Deploys KJar** - Uploads to container's Maven repo

### Port Allocation

Containers are assigned sequential ports starting from 8081:
- Default Drools: 8080
- First rule set: 8081
- Second rule set: 8082
- Third rule set: 8083
- etc.

### Container Registry

Example `/data/container_registry.json`:
```json
{
  "chase-insurance-underwriting-rules": {
    "platform": "docker",
    "container_name": "drools-chase-insurance-underwriting-rules",
    "docker_container_id": "a3f5b2c8...",
    "endpoint": "http://drools-chase-insurance-underwriting-rules:8080",
    "port": 8081,
    "created_at": "2025-01-15T10:30:00",
    "status": "running"
  },
  "bofa-loan-underwriting-rules": {
    "platform": "docker",
    "container_name": "drools-bofa-loan-underwriting-rules",
    "docker_container_id": "d7e9f1a2...",
    "endpoint": "http://drools-bofa-loan-underwriting-rules:8080",
    "port": 8082,
    "created_at": "2025-01-15T11:45:00",
    "status": "running"
  }
}
```

### Request Routing

When you test rules:
```bash
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d '{
    "container_id": "chase-insurance-underwriting-rules",
    "applicant": {...},
    "policy": {...}
  }'
```

The backend:
1. Extracts `container_id` from request
2. Looks up endpoint in registry
3. Routes to `http://drools-chase-insurance-underwriting-rules:8080`

## Kubernetes Deployment

See [kubernetes/README.md](kubernetes/README.md) for complete K8s setup.

### Quick Start

1. **Build and Push Image**
```bash
cd rule-agent
docker build -t your-registry/underwriting-backend:latest .
docker push your-registry/underwriting-backend:latest
```

2. **Create Secrets**
```bash
kubectl create secret generic underwriting-secrets \
  --from-literal=AWS_ACCESS_KEY_ID=... \
  --from-literal=AWS_SECRET_ACCESS_KEY=... \
  --from-literal=OPENAI_API_KEY=... \
  --namespace=underwriting
```

3. **Deploy**
```bash
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/rbac.yaml
kubectl apply -f kubernetes/storage.yaml
kubectl apply -f kubernetes/backend-deployment.yaml
```

4. **Verify**
```bash
kubectl get pods -n underwriting
kubectl logs deployment/underwriting-backend -n underwriting
```

### How K8s Pods Are Created

When you deploy rules on Kubernetes:

1. **Backend Creates Deployment**:
   ```python
   deployment = k8s_client.V1Deployment(
       metadata=V1ObjectMeta(name=f"drools-{container_id}"),
       spec=V1DeploymentSpec(
           replicas=1,
           template=V1PodTemplateSpec(
               spec=V1PodSpec(
                   containers=[...KIE Server container...]
               )
           )
       )
   )
   apps_v1.create_namespaced_deployment(namespace='underwriting', body=deployment)
   ```

2. **Creates Service**:
   ```python
   service = k8s_client.V1Service(
       metadata=V1ObjectMeta(name=f"drools-{container_id}-svc"),
       spec=V1ServiceSpec(
           type='ClusterIP',
           selector={'app': f"drools-{container_id}"},
           ports=[V1ServicePort(port=8080, target_port=8080)]
       )
   )
   v1.create_namespaced_service(namespace='underwriting', body=service)
   ```

3. **Registers Endpoint**:
   ```json
   {
     "chase-insurance-underwriting-rules": {
       "platform": "kubernetes",
       "deployment_name": "drools-chase-insurance-underwriting-rules",
       "service_name": "drools-chase-insurance-underwriting-rules-svc",
       "namespace": "underwriting",
       "endpoint": "http://drools-chase-insurance-underwriting-rules-svc.underwriting.svc.cluster.local:8080",
       "status": "running"
     }
   }
   ```

### RBAC Requirements

The backend needs permissions to create/delete pods and services:

See [kubernetes/rbac.yaml](kubernetes/rbac.yaml):
- ServiceAccount: `underwriting-backend-sa`
- Role: permissions for pods, services, deployments
- RoleBinding: binds role to service account

## How It Works

### Deployment Flow

```
User Uploads PDF
       │
       ▼
Backend: Extract text (AWS Textract)
       │
       ▼
Backend: Generate rules (LLM)
       │
       ▼
Backend: Build KJar (Maven)
       │
       ▼
Orchestrator: Create container
       │
       ├─── Docker: docker run ...
       │
       └─── K8s: kubectl create deployment ...
       │
       ▼
Orchestrator: Wait for health
       │
       ▼
Orchestrator: Register endpoint
       │
       ▼
Backend: Deploy KJar to container
       │
       ▼
✓ Ready to receive rule execution requests
```

### Request Routing Flow

```
User: POST /test_rules
       │
       ▼
Backend: Extract container_id from request
       │
       ▼
DroolsService: Resolve endpoint
       │
       ├─── Lookup in registry
       │
       ├─── Found: http://drools-chase-...:8080
       │
       └─── Not found: Use default
       │
       ▼
DroolsService: Execute rules at resolved endpoint
       │
       ▼
Drools Container: Execute rules
       │
       ▼
Return: Decision object
```

## API Examples

### Deploy Rules from PDF

```bash
curl -X POST http://localhost:9000/rule-agent/deploy_from_pdf \
  -F "file=@policy.pdf" \
  -F "bank_id=chase-insurance" \
  -F "policy_type=life-insurance"
```

**Response:**
```json
{
  "status": "success",
  "message": "Rules automatically deployed to container chase-insurance-underwriting-rules (dedicated Drools container)",
  "container_id": "chase-insurance-underwriting-rules",
  "steps": {
    "create_container": {
      "status": "success",
      "container_name": "drools-chase-insurance-underwriting-rules",
      "endpoint": "http://drools-chase-insurance-underwriting-rules:8080",
      "port": 8081
    },
    "deploy": {
      "status": "success"
    }
  }
}
```

### List All Containers

```bash
curl http://localhost:9000/rule-agent/list_containers
```

**Response:**
```json
{
  "platform": "docker",
  "containers": {
    "chase-insurance-underwriting-rules": {
      "platform": "docker",
      "container_name": "drools-chase-insurance-underwriting-rules",
      "endpoint": "http://drools-chase-insurance-underwriting-rules:8080",
      "port": 8081,
      "status": "running"
    }
  }
}
```

### Test Rules

```bash
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d '{
    "container_id": "chase-insurance-underwriting-rules",
    "applicant": {
      "name": "John Doe",
      "age": 35,
      "occupation": "Engineer",
      "healthConditions": null
    },
    "policy": {
      "policyType": "Term Life",
      "coverageAmount": 500000,
      "term": 20
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "container_id": "chase-insurance-underwriting-rules",
  "decision": {
    "approved": true,
    "reason": "Application meets all approval criteria",
    "requiresManualReview": false,
    "premiumMultiplier": 1.0
  }
}
```

### Delete Container

```bash
curl -X DELETE http://localhost:9000/rule-agent/delete_container/chase-insurance-underwriting-rules
```

## Monitoring

### Docker

```bash
# List all Drools containers
docker ps | grep drools

# View logs
docker logs drools-chase-insurance-underwriting-rules

# Monitor resources
docker stats

# Inspect container
docker inspect drools-chase-insurance-underwriting-rules
```

### Kubernetes

```bash
# List all Drools pods
kubectl get pods -n underwriting -l component=drools

# View logs
kubectl logs drools-chase-insurance-underwriting-rules-xyz -n underwriting

# Monitor resources
kubectl top pods -n underwriting

# Describe pod
kubectl describe pod drools-chase-insurance-underwriting-rules-xyz -n underwriting
```

### Application Logs

Check backend logs for orchestration events:
```bash
# Docker
docker logs backend

# Kubernetes
kubectl logs deployment/underwriting-backend -n underwriting
```

Look for:
- `✓ Container orchestrator enabled`
- `Creating dedicated Drools container for...`
- `✓ Dedicated container created:`
- `✓ Routing to container: ... at http://...`

## Troubleshooting

### Container Creation Fails (Docker)

**Symptom:** Container not appearing in `docker ps`

**Check:**
```bash
# View backend logs
docker logs backend

# Check Docker socket permissions
ls -l /var/run/docker.sock

# Verify backend can access Docker
docker exec backend docker ps
```

**Common Issues:**
- Docker socket not mounted: Add volume in docker-compose.yml
- Permission denied: Backend needs access to Docker socket
- Port conflict: Check if port already in use

### Container Creation Fails (Kubernetes)

**Symptom:** Pod stuck in Pending or CrashLoopBackOff

**Check:**
```bash
# Describe pod
kubectl describe pod drools-<name> -n underwriting

# Check events
kubectl get events -n underwriting

# View logs
kubectl logs drools-<name> -n underwriting
```

**Common Issues:**
- RBAC permissions: Check service account has role binding
- Image pull error: Verify image name and registry credentials
- Resource limits: Insufficient CPU/memory in cluster
- Storage: PVC not bound (check storage class)

### Requests Not Routing

**Symptom:** Rules work with default container but not dedicated containers

**Check:**
```bash
# View container registry
curl http://localhost:9000/rule-agent/list_containers

# Check if container_id matches
# Verify endpoint is reachable from backend

# Docker: Test connectivity
docker exec backend curl http://drools-chase-insurance-underwriting-rules:8080/kie-server/services/rest/server

# Kubernetes: Test from backend pod
kubectl exec deployment/underwriting-backend -n underwriting -- \
  curl http://drools-chase-insurance-underwriting-rules-svc:8080/kie-server/services/rest/server
```

**Common Issues:**
- Container ID mismatch: Ensure exact match in registry
- Network isolation: Containers not on same network (Docker) or namespace (K8s)
- Container not healthy: Check health check logs

### Registry Corruption

**Symptom:** Containers exist but not in registry, or registry has stale entries

**Fix:**
```bash
# Docker: View and edit registry
docker exec backend cat /data/container_registry.json
docker exec backend sh -c "echo '{}' > /data/container_registry.json"

# Kubernetes: Delete PVC and recreate
kubectl delete pvc underwriting-data-pvc -n underwriting
kubectl apply -f kubernetes/storage.yaml
```

### High Memory Usage

**Symptom:** System running out of memory with multiple containers

**Solution:**

Set resource limits in:

**Docker:** Each container uses ~1GB by default. Limit with:
```yaml
# In orchestrator creation code, add:
mem_limit='1g'
```

**Kubernetes:** Set in deployment spec:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

## Performance Considerations

### Memory

- Each Drools JVM: ~500MB-1GB
- 10 rule sets = ~10GB RAM needed
- Use resource limits to prevent OOM

### CPU

- Rule compilation: CPU intensive
- Rule execution: Moderate CPU
- Set appropriate limits

### Storage

- Each KJar: ~5-50MB
- Maven repo grows over time
- Use PVC cleanup or volume size limits

### Network

- Container-to-container: Fast (same host/network)
- Cross-node (K8s): Slightly slower
- Use node affinity if needed

## Best Practices

1. **Development:** Use single shared Drools container (`USE_CONTAINER_ORCHESTRATOR=false`)
2. **Production:** Use separate containers for isolation
3. **Set Resource Limits:** Prevent one rule set from consuming all resources
4. **Monitor Registry:** Periodically check for orphaned entries
5. **Clean Up:** Delete unused containers to free resources
6. **Use Kubernetes for Scale:** Better orchestration, auto-scaling, health management
7. **Backup Registry:** `/data/container_registry.json` is critical
8. **Version Control:** Use consistent Drools versions across containers

## Migration Guide

### From Shared to Dedicated Containers

1. **Backup existing data**
   ```bash
   docker cp backend:/data ./data-backup
   ```

2. **Enable orchestration**
   ```yaml
   # docker-compose.yml
   - USE_CONTAINER_ORCHESTRATOR=true
   ```

3. **Restart backend**
   ```bash
   docker-compose up -d backend
   ```

4. **Redeploy rules** (they'll create new containers automatically)

5. **Verify** new containers are created

6. **Remove old default container** (optional)
   ```bash
   docker-compose stop drools
   ```

### From Docker to Kubernetes

1. **Export container registry**
   ```bash
   docker cp backend:/data/container_registry.json ./
   ```

2. **Deploy to Kubernetes** (follow [kubernetes/README.md](kubernetes/README.md))

3. **Upload registry** to new backend pod
   ```bash
   kubectl cp container_registry.json \
     underwriting-backend-pod:/data/container_registry.json \
     -n underwriting
   ```

4. **Redeploy rules** to create K8s pods

Note: Endpoints will change from Docker to K8s DNS format

## Additional Resources

- [Main README](README.md) - Project overview
- [CLAUDE.md](CLAUDE.md) - Development guide
- [kubernetes/README.md](kubernetes/README.md) - Kubernetes deployment
- [ContainerOrchestrator.py](rule-agent/ContainerOrchestrator.py) - Source code
- [DroolsService.py](rule-agent/DroolsService.py) - Request routing
- [DroolsDeploymentService.py](rule-agent/DroolsDeploymentService.py) - Deployment workflow

## FAQ

**Q: Can I mix shared and dedicated containers?**
A: No, it's either all shared (single Drools) or all dedicated (one per rule set).

**Q: How do I scale a specific rule set?**
A: Kubernetes: `kubectl scale deployment drools-<id> --replicas=3`
   Docker: Create multiple containers manually with load balancer

**Q: Can I use different Drools versions?**
A: Yes! Modify image version in orchestrator per container.

**Q: What happens if a container crashes?**
A: Docker: Restart policy handles it
   Kubernetes: Deployment controller restarts pod automatically

**Q: How do I upgrade Drools version?**
A: Update image in orchestrator, delete old containers, redeploy rules.

**Q: Can I run this on Minikube?**
A: Yes, but you'll need significant RAM (16GB+) for multiple containers.
