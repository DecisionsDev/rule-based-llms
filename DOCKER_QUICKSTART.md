# Docker Quick Start - Underwriting AI

## TL;DR

```bash
# 1. Configure
cp docker.env llm.env
# Edit llm.env and add: OPENAI_API_KEY=sk-your-key

# 2. Start
docker-compose up -d

# 3. Wait for services (check logs)
docker-compose logs -f backend

# 4. Access
# Frontend:  http://localhost:8080
# Backend:   http://localhost:9000
# Drools:    http://localhost:8080/kie-server (admin/admin)
# ODM:       http://localhost:9060/res (odmAdmin/odmAdmin)
```

## Test It

```bash
# Upload policy
curl -X POST http://localhost:9000/rule-agent/upload_policy \
  -F "file=@your_policy.pdf" \
  -F "policy_type=life"

# Query
curl -G "http://localhost:9000/rule-agent/chat_with_tools" \
  --data-urlencode "userMessage=Can we approve a 50-year-old for $400K?"
```

## What's Running

| Service | Port | Container Name |
|---------|------|----------------|
| Frontend | 8080 | frontend |
| Backend API | 9000 | backend |
| Drools | 8080 | drools |
| ODM | 9060 | odm |

## Common Commands

```bash
# View logs
docker-compose logs -f backend

# Restart backend
docker-compose restart backend

# Rebuild after code changes
docker-compose build backend && docker-compose up -d backend

# Stop everything
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Volume Mounts

Your files are here:

- `./data/` → Policy documents & tool descriptors
- `./uploads/` → Uploaded PDFs
- `./generated_rules/` → Generated Drools rules

## Environment Setup

Edit `llm.env`:

```env
# Required
LLM_TYPE=OPENAI
OPENAI_API_KEY=sk-your-key-here

# Optional (for better extraction)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

## Full Documentation

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for complete documentation.
