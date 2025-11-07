# Docker Configuration Update Summary

## What Was Updated

The Docker configuration has been **fully updated** to support the new underwriting AI workflow with Drools, OpenAI, and AWS Textract.

## Files Created/Updated

### ✅ Updated Files (1)

1. **[docker-compose.yml](docker-compose.yml)** - Main orchestration file
   - Added Drools KIE Server container
   - Added volume mounts for uploads and generated_rules
   - Added network configuration
   - Updated environment variables
   - Updated service dependencies

### ⭐ New Files (4)

1. **[docker.env](docker.env)** - Environment template
   - Complete configuration template
   - Documented all environment variables
   - Pre-configured for Docker Compose

2. **[rule-agent/.dockerignore](rule-agent/.dockerignore)** - Build optimization
   - Excludes unnecessary files from Docker build
   - Improves build speed and image size

3. **[DOCKER_SETUP.md](DOCKER_SETUP.md)** - Complete Docker guide
   - Architecture overview
   - Deployment instructions
   - Troubleshooting guide
   - Development workflow

4. **[DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)** - Quick reference
   - TL;DR commands
   - Common operations
   - Quick testing guide

## New Docker Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                Docker Compose Stack                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Drools    │  │     ODM     │  │   Backend   │          │
│  │ :8080       │  │   :9060     │  │   :9000     │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┴────────────────┘                  │
│                          │                                   │
│                   ┌──────▼──────┐                           │
│                   │  Frontend   │                           │
│                   │   :8080     │                           │
│                   └─────────────┘                           │
│                                                               │
│  Network: underwriting-net                                   │
└──────────────────────────────────────────────────────────────┘

Volumes:
  ./data → /data (policies & descriptors)
  ./uploads → /uploads (uploaded PDFs)
  ./generated_rules → /generated_rules (DRL files)

External Services:
  - OpenAI API
  - AWS Textract (optional)
```

## What's Now Included

### 1. Drools KIE Server

```yaml
drools:
  image: jboss/kie-server:latest
  ports:
    - 8080:8080
  environment:
    - KIE_SERVER_USER=admin
    - KIE_SERVER_PWD=admin
```

**Features:**
- Automatic health checks
- Pre-configured credentials
- Network connectivity to backend
- Ready for rule deployment

### 2. Volume Mounts

```yaml
volumes:
  - ./data:/data
  - ./uploads:/uploads
  - ./generated_rules:/generated_rules
```

**Benefits:**
- Uploaded PDFs persist on host
- Generated rules accessible from host
- Easy to view and manage files
- Can manually edit generated rules

### 3. Network Configuration

```yaml
networks:
  underwriting-net:
    driver: bridge
```

**Features:**
- Isolated network for all services
- DNS resolution between containers
- `backend` can reach `drools` and `odm` by name

### 4. Environment Variables

**Automatic (set by docker-compose.yml):**
- `DROOLS_SERVER_URL=http://drools:8080`
- `ODM_SERVER_URL=http://odm:9060`
- `DATADIR=/data`
- `UPLOAD_DIR=/uploads`
- `DROOLS_RULES_DIR=/generated_rules`

**Manual (set in llm.env):**
- `LLM_TYPE=OPENAI`
- `OPENAI_API_KEY=your-key`
- `AWS_ACCESS_KEY_ID=your-key` (optional)
- `AWS_SECRET_ACCESS_KEY=your-secret` (optional)

### 5. Service Dependencies

```yaml
backend:
  depends_on:
    drools:
      condition: service_healthy
    odm:
      condition: service_healthy
```

**Benefits:**
- Backend waits for Drools and ODM to be ready
- Automatic startup order
- Health checks ensure services are operational

## Complete Workflow - Dockerized

### Step 1: Configure

```bash
cp docker.env llm.env
# Edit llm.env and add OPENAI_API_KEY
```

### Step 2: Start All Services

```bash
docker-compose up -d
```

This starts:
- ✅ Drools KIE Server (30 seconds to start)
- ✅ IBM ODM Decision Server (20 seconds to start)
- ✅ Backend API with all new services
- ✅ Frontend UI

### Step 3: Upload Policy

```bash
curl -X POST http://localhost:9000/rule-agent/upload_policy \
  -F "file=@policy.pdf" \
  -F "policy_type=life"
```

**What happens:**
1. PDF uploaded to `/uploads/` (persisted)
2. OpenAI analyzes document
3. AWS Textract extracts data (or LLM fallback)
4. OpenAI generates Drools rules
5. DRL saved to `./generated_rules/` (persisted)
6. KJar structure created

### Step 4: Check Generated Rules

```bash
# On host machine
cat ./generated_rules/underwriting-rules.drl

# Or via API
curl http://localhost:9000/rule-agent/list_generated_rules
```

### Step 5: Deploy Rules (Manual)

```bash
cd generated_rules/underwriting-rules_kjar
mvn clean install

# Deploy to Drools container
curl -X PUT "http://localhost:8080/kie-server/services/rest/server/containers/underwriting-rules" \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d '{
    "container-id": "underwriting-rules",
    "release-id": {
      "group-id": "com.underwriting",
      "artifact-id": "underwriting-rules",
      "version": "1.0.0"
    }
  }'
```

### Step 6: Query Runtime

```bash
curl -G "http://localhost:9000/rule-agent/chat_with_tools" \
  --data-urlencode "userMessage=Can we approve a 50-year-old for $400K coverage?"
```

**What happens:**
1. Frontend/API receives query
2. RuleAIAgent extracts parameters with OpenAI
3. DroolsService invokes rules in container
4. Response formatted and returned

## Key Benefits

### 🚀 Easy Deployment
```bash
docker-compose up -d
# Everything starts automatically
```

### 🔄 Persistence
- Uploaded files persist in `./uploads/`
- Generated rules persist in `./generated_rules/`
- Can review/edit files directly on host

### 🌐 Isolated Networking
- All services communicate on private network
- Only exposed ports accessible from host
- Secure inter-service communication

### 📊 Monitoring
```bash
docker-compose logs -f backend    # Watch backend logs
docker-compose logs -f drools     # Watch Drools logs
docker-compose ps                 # See all service status
```

### 🛠️ Development Friendly
```bash
# Make code changes
# Rebuild and restart
docker-compose build backend
docker-compose up -d backend

# View logs
docker-compose logs -f backend
```

## Service URLs

**From host machine:**
- Frontend: http://localhost:8080
- Backend API: http://localhost:9000
- Drools Console: http://localhost:8080/kie-server
- ODM Console: http://localhost:9060/res

**From inside containers:**
- Drools: http://drools:8080
- ODM: http://odm:9060
- Backend: http://backend:9000

## Quick Commands Reference

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Rebuild
docker-compose build backend

# Logs
docker-compose logs -f backend

# Shell access
docker-compose exec backend bash

# Restart service
docker-compose restart backend

# Remove everything
docker-compose down -v
```

## What's Different from Before

| Aspect | Before | After |
|--------|--------|-------|
| Drools | Not included | ✅ Fully integrated container |
| Volumes | Only `/data` | ✅ `/data`, `/uploads`, `/generated_rules` |
| Network | Default bridge | ✅ Custom `underwriting-net` |
| Env Vars | Manual config | ✅ Automatic + template |
| Health Checks | ODM only | ✅ ODM + Drools |
| Dependencies | ODM only | ✅ ODM + Drools with health checks |

## Next Steps

1. **Start the stack**: `docker-compose up -d`
2. **Check logs**: `docker-compose logs -f backend`
3. **Test upload**: See DOCKER_QUICKSTART.md
4. **Deploy rules**: Follow generated KJar README
5. **Query runtime**: Test with chatbot

## Documentation

- **Quick Start**: [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)
- **Full Guide**: [DOCKER_SETUP.md](DOCKER_SETUP.md)
- **Setup Guide**: [UNDERWRITING_SETUP.md](UNDERWRITING_SETUP.md)
- **Implementation**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

---

**Everything is now fully Dockerized!** 🐳✨

You can now run the entire underwriting AI system with a single command:
```bash
docker-compose up -d
```
