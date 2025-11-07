# Kubernetes Deployment for Underwriting System

This directory contains Kubernetes manifests for deploying the underwriting system with **one Drools container per rule set**.

## Architecture

```
┌─────────────────────────────────────────────┐
│          Ingress / Load Balancer            │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│    Backend Service (underwriting-backend)   │
│    - LLM Integration                        │
│    - Container Orchestrator                 │
│    - Request Router                         │
└──┬──────────┬──────────┬────────────────────┘
   │          │          │
   ▼          ▼          ▼
┌──────┐  ┌──────┐  ┌──────┐
│Drools│  │Drools│  │Drools│  (One pod per rule set)
│ Pod1 │  │ Pod2 │  │ Pod3 │
└──────┘  └──────┘  └──────┘
```

## Prerequisites

1. **Kubernetes Cluster** (v1.20+)
   - Minikube (local development)
   - EKS, GKE, AKS (cloud)
   - On-premise Kubernetes

2. **kubectl** CLI configured

3. **Storage Class** supporting ReadWriteMany (e.g., NFS, AWS EFS)

4. **Container Registry** (Docker Hub, ECR, GCR, etc.)

## Setup Instructions

### 1. Build and Push Backend Image

```bash
# Build the backend image
cd rule-agent
docker build -t your-registry/underwriting-backend:latest .

# Push to registry
docker push your-registry/underwriting-backend:latest
```

Update [backend-deployment.yaml](backend-deployment.yaml#L23) with your image name.

### 2. Create Kubernetes Secrets

```bash
# Create secret with AWS and LLM credentials
kubectl create secret generic underwriting-secrets \
  --from-literal=AWS_ACCESS_KEY_ID=your-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret \
  --from-literal=AWS_REGION=us-east-1 \
  --from-literal=S3_BUCKET=your-bucket \
  --from-literal=OPENAI_API_KEY=your-openai-key \
  --from-literal=LLM_TYPE=OPENAI \
  --namespace=underwriting
```

Or create from file:
```bash
# Create llm-secrets.env file (don't commit to git!)
cat > llm-secrets.env <<EOF
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
S3_BUCKET=your-bucket
OPENAI_API_KEY=your-openai-key
LLM_TYPE=OPENAI
EOF

kubectl create secret generic underwriting-secrets \
  --from-env-file=llm-secrets.env \
  --namespace=underwriting
```

### 3. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Create RBAC (Service Account, Role, RoleBinding)
kubectl apply -f rbac.yaml

# Create storage
kubectl apply -f storage.yaml

# Deploy backend
kubectl apply -f backend-deployment.yaml
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n underwriting

# Check services
kubectl get svc -n underwriting

# View backend logs
kubectl logs -f deployment/underwriting-backend -n underwriting

# Get backend service URL
kubectl get svc underwriting-backend-svc -n underwriting
```

### 5. Access the Application

#### Option A: LoadBalancer (Cloud)
```bash
# Get external IP
kubectl get svc underwriting-backend-svc -n underwriting

# Access at: http://<EXTERNAL-IP>:9000
```

#### Option B: NodePort (Local/On-prem)
```bash
# Change service type to NodePort in backend-deployment.yaml
# Then get the node port
kubectl get svc underwriting-backend-svc -n underwriting

# Access at: http://<NODE-IP>:<NODE-PORT>
```

#### Option C: Port Forward (Development)
```bash
kubectl port-forward svc/underwriting-backend-svc 9000:9000 -n underwriting

# Access at: http://localhost:9000
```

## How It Works

### Dynamic Container Creation

When you deploy a new rule set via the backend API, the system:

1. **Receives ruleapp** - Backend receives the compiled JAR file
2. **Creates Deployment** - Orchestrator creates a new K8s Deployment
3. **Creates Service** - Orchestrator creates a Service for the Deployment
4. **Registers Endpoint** - Saves endpoint in container registry
5. **Routes Requests** - Future requests routed to correct pod

### Example: Deploy New Rules

```bash
# Upload PDF and deploy rules
curl -X POST http://localhost:9000/rule-agent/deploy_to_drools \
  -F "file=@insurance_policy.pdf" \
  -F "bank_id=chase-insurance" \
  -F "policy_type=life-insurance"
```

This creates:
- Deployment: `drools-chase-insurance-underwriting-rules`
- Service: `drools-chase-insurance-underwriting-rules-svc`
- Endpoint: `http://drools-chase-insurance-underwriting-rules-svc.underwriting.svc.cluster.local:8080`

### Testing Rules

```bash
# List all Drools containers
curl http://localhost:9000/rule-agent/list_containers

# Test rules (automatically routed to correct pod)
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d @test_rules.json
```

## Monitoring

### View Drools Pods

```bash
# List all Drools pods
kubectl get pods -n underwriting -l component=drools

# View logs for specific Drools pod
kubectl logs drools-chase-insurance-underwriting-rules-<pod-id> -n underwriting

# Describe pod
kubectl describe pod drools-chase-insurance-underwriting-rules-<pod-id> -n underwriting
```

### View Container Registry

```bash
# Exec into backend pod
kubectl exec -it deployment/underwriting-backend -n underwriting -- bash

# View registry
cat /data/container_registry.json
```

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment underwriting-backend --replicas=3 -n underwriting

# Scale specific Drools deployment
kubectl scale deployment drools-chase-insurance-underwriting-rules --replicas=2 -n underwriting
```

### Auto-scaling (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: drools-chase-insurance-hpa
  namespace: underwriting
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: drools-chase-insurance-underwriting-rules
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Cleanup

### Delete Specific Drools Deployment

```bash
# Via API
curl -X DELETE http://localhost:9000/rule-agent/delete_container/chase-insurance-underwriting-rules

# Or manually
kubectl delete deployment drools-chase-insurance-underwriting-rules -n underwriting
kubectl delete service drools-chase-insurance-underwriting-rules-svc -n underwriting
```

### Delete All Resources

```bash
kubectl delete namespace underwriting
```

## Troubleshooting

### Pod Not Starting

```bash
# Check events
kubectl describe pod <pod-name> -n underwriting

# Check logs
kubectl logs <pod-name> -n underwriting

# Common issues:
# - Image pull error: Check image name and registry credentials
# - CrashLoopBackOff: Check application logs
# - Pending: Check PVC status (kubectl get pvc -n underwriting)
```

### Storage Issues

```bash
# Check PVC status
kubectl get pvc -n underwriting

# If pending, check storage class
kubectl get sc

# You may need to create a storage class or use an existing one
```

### RBAC Issues

```bash
# Check service account
kubectl get sa -n underwriting

# Check role bindings
kubectl get rolebinding -n underwriting

# View backend pod logs for permission errors
kubectl logs deployment/underwriting-backend -n underwriting
```

## Production Considerations

1. **Ingress Controller**
   - Use Nginx, Traefik, or cloud provider ingress
   - Configure TLS/SSL certificates
   - Set up domain routing

2. **Resource Limits**
   - Set appropriate CPU/memory limits for Drools pods
   - Each Drools JVM typically needs 1-2GB memory

3. **Storage**
   - Use cloud-native storage (EFS, Cloud Filestore, Azure Files)
   - Or NFS server for on-premise
   - Ensure ReadWriteMany support for shared data

4. **Security**
   - Use secrets for credentials (never hardcode)
   - Enable RBAC
   - Use NetworkPolicies to restrict pod-to-pod communication
   - Scan images for vulnerabilities

5. **Monitoring**
   - Prometheus + Grafana for metrics
   - ELK or Loki for log aggregation
   - Jaeger for distributed tracing

6. **High Availability**
   - Run multiple backend replicas
   - Use pod anti-affinity for Drools pods
   - Configure proper readiness/liveness probes

## Cost Optimization

- Use spot/preemptible instances for non-critical workloads
- Set appropriate resource requests/limits
- Delete unused Drools deployments via API
- Use cluster autoscaler for node scaling

## Migration from Docker Compose

If migrating from Docker Compose:

1. Keep Docker Compose for local development
2. Use Kubernetes for staging/production
3. Set `ORCHESTRATION_PLATFORM=docker` in Docker Compose
4. Set `ORCHESTRATION_PLATFORM=kubernetes` in K8s deployment

The backend code automatically detects the platform and uses the appropriate orchestration method.
