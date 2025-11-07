# Docker Deployment Guide

This guide explains how to run the complete underwriting AI system using Docker Compose.

## What Gets Deployed

The Docker setup includes **4 services**:

1. **Drools KIE Server** (port 8080) - Rule execution engine for underwriting rules
2. **IBM ODM** (port 9060) - Alternative rule engine (optional fallback)
3. **Backend API** (port 9000) - Python/Flask service with LLM integration
4. **Frontend UI** (port 8080) - React chatbot interface

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network: underwriting-net         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Drools     │    │     ODM      │    │   Backend    │  │
│  │ KIE Server   │    │  Decision    │    │   (Flask)    │  │
│  │  :8080       │◄───┤   Server     │◄───┤   :9000      │  │
│  └──────────────┘    │  :9060       │    └──────┬───────┘  │
│                      └──────────────┘           │           │
│                                                 │           │
│                                    ┌────────────▼───────┐   │
│                                    │    Frontend        │   │
│                                    │    (React)         │   │
│                                    │    :8080           │   │
│                                    └────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

External Services (accessed from backend):
- OpenAI API (for LLM)
- AWS Textract (optional - for document extraction)
```

## Quick Start

### 1. Configure Environment

Copy the template and add your credentials:

```bash
cp docker.env llm.env
```

Edit `llm.env` and add your OpenAI API key:

```env
LLM_TYPE=OPENAI
OPENAI_API_KEY=sk-your-actual-openai-key-here
OPENAI_MODEL_NAME=gpt-4
```

### 2. Build and Start All Services

```bash
docker-compose build
docker-compose up
```

Or in detached mode:

```bash
docker-compose up -d
```

### 3. Wait for Services to Start

The backend waits for health checks:
- Drools KIE Server (takes ~30 seconds)
- ODM Decision Server (takes ~20 seconds)

Watch the logs:

```bash
docker-compose logs -f backend
```

Look for:
```
Connection with Drools Server is OK
Connection with ODM Server is OK
Running chat service
```

### 4. Access the Services

- **Frontend UI**: http://localhost:8080
- **Backend API**: http://localhost:9000
- **Drools Console**: http://localhost:8080/kie-server (admin/admin)
- **ODM Console**: http://localhost:9060/res (odmAdmin/odmAdmin)

## Testing the System

### Test 1: Upload a Policy Document

```bash
curl -X POST http://localhost:9000/rule-agent/upload_policy \
  -F "file=@sample_policy.pdf" \
  -F "policy_type=life" \
  -F "container_id=underwriting-rules"
```

### Test 2: Query with Chatbot

```bash
curl -G "http://localhost:9000/rule-agent/chat_with_tools" \
  --data-urlencode "userMessage=Can we approve a 45-year-old for $300,000 life insurance?"
```

### Test 3: List Generated Rules

```bash
curl http://localhost:9000/rule-agent/list_generated_rules
```

### Test 4: Check Drools Status

```bash
curl http://localhost:9000/rule-agent/drools_containers
```

## Volume Mounts

The system uses the following volume mounts:

| Host Directory | Container Path | Purpose |
|----------------|---------------|---------|
| `./data` | `/data` | Policy documents for RAG & tool descriptors |
| `./uploads` | `/uploads` | Uploaded policy PDFs |
| `./generated_rules` | `/generated_rules` | Generated DRL files & KJars |

**Important**: Generated rules are persisted on your host machine in `./generated_rules/`

## Environment Variables

### Required (in llm.env)

- `LLM_TYPE` - Set to `OPENAI`
- `OPENAI_API_KEY` - Your OpenAI API key

### Optional (in llm.env)

- `AWS_ACCESS_KEY_ID` - For AWS Textract (if not set, uses PyPDF2)
- `AWS_SECRET_ACCESS_KEY` - For AWS Textract
- `AWS_REGION` - AWS region (default: us-east-1)

### Automatically Configured (by docker-compose.yml)

These are set automatically - you don't need to change them:

- `DROOLS_SERVER_URL=http://drools:8080`
- `ODM_SERVER_URL=http://odm:9060`
- `DATADIR=/data`
- `UPLOAD_DIR=/uploads`
- `DROOLS_RULES_DIR=/generated_rules`

## Docker Commands

### Start Services

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Start specific service
docker-compose up backend
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f drools

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Rebuild

```bash
# Rebuild all
docker-compose build

# Rebuild specific service
docker-compose build backend

# Force rebuild (no cache)
docker-compose build --no-cache backend
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Execute Commands in Containers

```bash
# Open bash in backend container
docker-compose exec backend bash

# Run Python command
docker-compose exec backend python -c "print('Hello')"

# Check Drools status
docker-compose exec backend curl http://drools:8080/kie-server/services/rest/server
```

## Service-Specific Information

### Drools KIE Server

**Image**: `jboss/kie-server:latest`
**Port**: 8080
**Credentials**: admin/admin

**Health Check**: Tests REST API endpoint
**Startup Time**: ~30 seconds

**Web Console**: Not included in this image. To deploy rules:
1. Use the generated KJar from `./generated_rules/`
2. Build with Maven: `cd generated_rules/underwriting-rules_kjar && mvn clean install`
3. Deploy via REST API (see deployment instructions in generated README)

### IBM ODM Decision Server

**Image**: `ibmcom/odm`
**Port**: 9060
**Credentials**: odmAdmin/odmAdmin

**Consoles**:
- Decision Center: http://localhost:9060/decisioncenter
- Rule Execution Server: http://localhost:9060/res
- Decision Server Console: http://localhost:9060/DecisionService

### Backend Service

**Base Image**: `python:3.10`
**Port**: 9000

**Endpoints**:
- `/rule-agent/upload_policy` - Upload policy PDF
- `/rule-agent/chat_with_tools` - Query with decision services
- `/rule-agent/chat_without_tools` - Query with RAG only
- `/rule-agent/list_generated_rules` - List generated rules
- `/rule-agent/get_rule_content` - View rule content
- `/rule-agent/drools_containers` - List Drools containers

### Frontend

**Base Image**: Node.js build → Nginx serve
**Port**: 8080

React application that connects to backend API.

## Troubleshooting

### Services Won't Start

**Check logs**:
```bash
docker-compose logs backend
```

**Common issues**:

1. **Port already in use**:
   ```
   Error: bind: address already in use
   ```
   Solution: Stop the conflicting service or change ports in docker-compose.yml

2. **Health check failing**:
   ```
   unhealthy
   ```
   Solution: Wait longer or check service logs

### Backend Can't Connect to Drools

**Check network**:
```bash
docker-compose exec backend ping drools
```

**Check Drools is running**:
```bash
docker-compose exec backend curl http://drools:8080/kie-server/services/rest/server
```

### OpenAI API Errors

**Check environment variable**:
```bash
docker-compose exec backend printenv OPENAI_API_KEY
```

**Restart after changing llm.env**:
```bash
docker-compose restart backend
```

### Generated Rules Not Persisting

**Check volume mount**:
```bash
docker-compose exec backend ls -la /generated_rules
```

**Check host directory**:
```bash
ls -la ./generated_rules
```

### AWS Textract Not Working

This is expected if AWS credentials are not configured. The system will fall back to:
1. PyPDF2 for text extraction
2. LLM for answering extraction queries

To enable Textract, add to `llm.env`:
```env
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
```

Then restart:
```bash
docker-compose restart backend
```

## Development Workflow

### 1. Make Code Changes

Edit files in `rule-agent/` directory.

### 2. Rebuild Backend

```bash
docker-compose build backend
docker-compose up -d backend
```

### 3. Test Changes

```bash
curl -X POST http://localhost:9000/rule-agent/upload_policy \
  -F "file=@test.pdf"
```

### 4. View Logs

```bash
docker-compose logs -f backend
```

## Production Deployment

For production, consider:

1. **Use specific image versions** instead of `latest`:
   ```yaml
   image: jboss/kie-server:7.74.1.Final
   ```

2. **Add resource limits**:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
   ```

3. **Use secrets for credentials**:
   ```yaml
   secrets:
     - openai_api_key
   ```

4. **Add persistent volumes for Drools**:
   ```yaml
   volumes:
     - drools-data:/opt/jboss/.kie
   ```

5. **Use external Drools/ODM** servers instead of containers

6. **Add HTTPS/TLS** with reverse proxy (Nginx, Traefik)

7. **Set up monitoring** (Prometheus, Grafana)

8. **Configure logging** to external aggregator

## Cleanup

### Remove All Containers and Volumes

```bash
docker-compose down -v
```

### Remove Images

```bash
docker rmi backend chatbot-frontend
docker rmi jboss/kie-server:latest
docker rmi ibmcom/odm
```

### Clean Generated Files

```bash
rm -rf uploads/*
rm -rf generated_rules/*
```

## Network Architecture

All services are on a custom bridge network: `underwriting-net`

**Service DNS names** (accessible within Docker network):
- `drools` → Drools KIE Server
- `odm` → IBM ODM
- `backend` → Flask API
- `frontend` → React UI

**External access** (from host):
- `localhost:8080` → Frontend & Drools
- `localhost:9000` → Backend API
- `localhost:9060` → ODM

## Summary

**Start everything**:
```bash
cp docker.env llm.env
# Edit llm.env with your OPENAI_API_KEY
docker-compose up -d
```

**Check status**:
```bash
docker-compose ps
docker-compose logs -f backend
```

**Test**:
```bash
curl -X POST http://localhost:9000/rule-agent/upload_policy -F "file=@policy.pdf"
```

**Stop**:
```bash
docker-compose down
```

---

**Everything is now fully dockerized!** 🐳
