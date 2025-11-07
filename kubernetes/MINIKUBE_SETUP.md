# Local Kubernetes Development with Minikube

This guide shows how to run the container-per-ruleset architecture on your local machine using Minikube.

## Prerequisites

1. **Install Minikube**
   - Windows: `choco install minikube` or download from [minikube.sigs.k8s.io](https://minikube.sigs.k8s.io/docs/start/)
   - macOS: `brew install minikube`
   - Linux: See [installation docs](https://minikube.sigs.k8s.io/docs/start/)

2. **Install kubectl**
   - Windows: `choco install kubernetes-cli`
   - macOS: `brew install kubectl`
   - Linux: See [installation docs](https://kubernetes.io/docs/tasks/tools/)

3. **System Requirements**
   - 16GB RAM (minimum 8GB)
   - 4 CPUs (minimum 2)
   - 40GB disk space

## Quick Start

### 1. Start Minikube

```bash
# Start with adequate resources
minikube start --memory=8192 --cpus=4 --disk-size=40g

# Verify it's running
minikube status
kubectl get nodes
```

### 2. Build Backend Image

```bash
# Point Docker to Minikube's Docker daemon
eval $(minikube docker-env)

# Build the image (it will be available inside Minikube)
cd rule-agent
docker build -t underwriting-backend:latest .
cd ..
```

**Important**: When using Minikube's Docker daemon, set `imagePullPolicy: Never` in deployments to use local images.

### 3. Update Kubernetes Manifests for Minikube

Edit `kubernetes/backend-deployment.yaml`:

```yaml
spec:
  template:
    spec:
      containers:
      - name: backend
        image: underwriting-backend:latest
        imagePullPolicy: Never  # Use local image, don't pull from registry
```

### 4. Create Secrets

```bash
# Create namespace
kubectl apply -f kubernetes/namespace.yaml

# Create secrets (replace with your actual credentials)
kubectl create secret generic underwriting-secrets \
  --from-literal=AWS_ACCESS_KEY_ID=your-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret \
  --from-literal=AWS_REGION=us-east-1 \
  --from-literal=S3_BUCKET=your-bucket \
  --from-literal=OPENAI_API_KEY=your-openai-key \
  --from-literal=LLM_TYPE=OPENAI \
  --namespace=underwriting
```

### 5. Deploy to Minikube

```bash
# Deploy RBAC
kubectl apply -f kubernetes/rbac.yaml

# Deploy storage
kubectl apply -f kubernetes/storage.yaml

# Deploy backend
kubectl apply -f kubernetes/backend-deployment.yaml
```

### 6. Verify Deployment

```bash
# Check pods
kubectl get pods -n underwriting

# View logs
kubectl logs -f deployment/underwriting-backend -n underwriting

# Wait for pod to be ready
kubectl wait --for=condition=ready pod -l app=underwriting-backend -n underwriting --timeout=300s
```

### 7. Access the Service

**Option 1: Port Forward (Recommended for Testing)**
```bash
# Forward backend service to localhost
kubectl port-forward svc/underwriting-backend-svc 9000:9000 -n underwriting

# Access at: http://localhost:9000
```

**Option 2: Minikube Service**
```bash
# Get the URL
minikube service underwriting-backend-svc -n underwriting --url

# Or open in browser
minikube service underwriting-backend-svc -n underwriting
```

**Option 3: Ingress**
```bash
# Enable ingress addon
minikube addons enable ingress

# Create ingress (see example below)
kubectl apply -f kubernetes/ingress.yaml

# Get Minikube IP
minikube ip

# Access at: http://<minikube-ip>/rule-agent
```

## Test the Deployment

### Deploy Rules

```bash
# Upload PDF and deploy rules
curl -X POST http://localhost:9000/rule-agent/deploy_from_pdf \
  -F "file=@insurance_policy.pdf" \
  -F "bank_id=chase-insurance" \
  -F "policy_type=life-insurance"
```

This will create a new Kubernetes Deployment and Service:
- Deployment: `drools-chase-insurance-underwriting-rules`
- Service: `drools-chase-insurance-underwriting-rules-svc`

### Verify New Drools Pod

```bash
# List all pods
kubectl get pods -n underwriting

# Should see:
# - underwriting-backend-xxx
# - drools-chase-insurance-underwriting-rules-xxx

# View Drools pod logs
kubectl logs drools-chase-insurance-underwriting-rules-xxx -n underwriting

# Check services
kubectl get svc -n underwriting
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

## Monitoring

### View All Resources

```bash
# All resources in namespace
kubectl get all -n underwriting

# Describe backend pod
kubectl describe pod -l app=underwriting-backend -n underwriting

# View events
kubectl get events -n underwriting --sort-by='.lastTimestamp'
```

### Monitor Resource Usage

```bash
# Enable metrics server
minikube addons enable metrics-server

# Wait a minute for metrics to collect, then:
kubectl top pods -n underwriting
kubectl top nodes
```

### Access Kubernetes Dashboard

```bash
# Start dashboard
minikube dashboard

# Navigate to "underwriting" namespace
```

## Troubleshooting

### Pod Stuck in Pending

**Check:**
```bash
kubectl describe pod <pod-name> -n underwriting
```

**Common Issues:**
- **Insufficient resources**: Increase Minikube resources
  ```bash
  minikube stop
  minikube start --memory=12288 --cpus=6
  ```
- **PVC not bound**: Check storage class
  ```bash
  kubectl get pvc -n underwriting
  kubectl get sc
  ```

### ImagePullBackOff

**Issue**: Minikube trying to pull image from registry

**Fix**:
```yaml
# In deployment YAML
imagePullPolicy: Never  # Use local image
```

Or rebuild image in Minikube's Docker:
```bash
eval $(minikube docker-env)
docker build -t underwriting-backend:latest .
```

### Backend Can't Create Pods

**Issue**: RBAC permissions

**Check**:
```bash
kubectl get sa -n underwriting
kubectl get rolebinding -n underwriting
kubectl describe rolebinding underwriting-orchestrator-rolebinding -n underwriting
```

**Fix**: Ensure RBAC is applied:
```bash
kubectl apply -f kubernetes/rbac.yaml
```

### Service Not Accessible

**Check**:
```bash
# Verify service exists
kubectl get svc -n underwriting

# Check endpoints
kubectl get endpoints -n underwriting

# Test from within cluster
kubectl run test-pod --image=curlimages/curl -it --rm -n underwriting -- \
  curl http://underwriting-backend-svc:9000/rule-agent/health
```

## Storage Configuration

Minikube uses `standard` storage class by default. For development, this works fine with single-node access.

If you need ReadWriteMany (multiple pods accessing same volume):

```bash
# Option 1: Use NFS provisioner
minikube addons enable storage-provisioner-nfs

# Option 2: Use hostPath (single node, but simpler)
# Already works with default Minikube setup
```

## Sample Ingress (Optional)

Create `kubernetes/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: underwriting-ingress
  namespace: underwriting
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: underwriting.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: underwriting-backend-svc
            port:
              number: 9000
```

Apply and access:
```bash
kubectl apply -f kubernetes/ingress.yaml

# Add to /etc/hosts (Windows: C:\Windows\System32\drivers\etc\hosts)
echo "$(minikube ip) underwriting.local" | sudo tee -a /etc/hosts

# Access at: http://underwriting.local
```

## Cleanup

### Delete All Resources

```bash
# Delete namespace (removes everything)
kubectl delete namespace underwriting

# Or delete individually
kubectl delete -f kubernetes/backend-deployment.yaml
kubectl delete -f kubernetes/storage.yaml
kubectl delete -f kubernetes/rbac.yaml
kubectl delete -f kubernetes/namespace.yaml
```

### Stop/Delete Minikube

```bash
# Stop (preserves state)
minikube stop

# Delete (removes everything)
minikube delete

# Restart fresh
minikube start --memory=8192 --cpus=4
```

## Performance Tips

1. **Increase Resources**: More RAM/CPU = better performance
   ```bash
   minikube start --memory=16384 --cpus=8
   ```

2. **Use Docker Driver** (fastest on most systems):
   ```bash
   minikube start --driver=docker
   ```

3. **Enable Container Runtime**: Use containerd for better performance
   ```bash
   minikube start --container-runtime=containerd
   ```

4. **Persistent Storage**: Mount local directory for faster I/O
   ```bash
   minikube mount /path/on/host:/path/in/minikube
   ```

## Development Workflow

1. **Code Change** → Rebuild image:
   ```bash
   eval $(minikube docker-env)
   docker build -t underwriting-backend:latest .
   ```

2. **Restart Pod**:
   ```bash
   kubectl rollout restart deployment/underwriting-backend -n underwriting
   ```

3. **View Logs**:
   ```bash
   kubectl logs -f deployment/underwriting-backend -n underwriting
   ```

4. **Test**:
   ```bash
   kubectl port-forward svc/underwriting-backend-svc 9000:9000 -n underwriting
   curl http://localhost:9000/rule-agent/health
   ```

## Comparison: Docker Compose vs Minikube

| Aspect | Docker Compose | Minikube |
|--------|----------------|----------|
| **Startup Time** | ~10s | ~30-60s |
| **Resource Usage** | Lower | Higher (K8s overhead) |
| **Similarity to Prod** | Medium | High |
| **Learning Curve** | Easy | Moderate |
| **Scaling** | Manual | Automatic (HPA) |
| **Service Discovery** | Docker DNS | K8s DNS |
| **Best For** | Quick dev/testing | K8s-specific testing |

**Recommendation**:
- **Daily Development**: Use Docker Compose (faster, simpler)
- **Kubernetes Testing**: Use Minikube (matches production)
- **Production**: Use real Kubernetes cluster (EKS, GKE, AKS)

## Next Steps

- See [README.md](README.md) for full Kubernetes production deployment
- See [../CONTAINER_PER_RULESET.md](../CONTAINER_PER_RULESET.md) for architecture details
- See [../CLAUDE.md](../CLAUDE.md) for development guide
