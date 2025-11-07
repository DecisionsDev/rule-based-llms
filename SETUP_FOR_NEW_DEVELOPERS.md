# Setup Guide for New Developers

## Prerequisites

Before cloning the repository, ensure you have:

- ✅ **Docker Desktop** installed and running
- ✅ **Git** installed
- ✅ **AWS Credentials** (for Textract and S3 access)
- ✅ **LLM Access** (Ollama, Watsonx, OpenAI, or IBM BAM)

---

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd underwriter-rule-based-llms
```

### ⚠️ IMPORTANT for Windows Users

If you're on Windows, Git may convert line endings from LF (Linux) to CRLF (Windows), which will cause Docker build failures.

**Quick Fix - Configure Git Before Cloning:**
```bash
# Set Git to preserve LF line endings
git config --global core.autocrlf input

# Then clone
git clone <repository-url>
```

**Already Cloned? Fix Line Endings:**
```bash
# In repo root
cd underwriter-rule-based-llms

# Fix shell scripts (requires Git Bash or WSL)
dos2unix rule-agent/serverStart.sh rule-agent/deploy_ruleapp_to_odm.sh

# Or use sed
sed -i 's/\r$//' rule-agent/serverStart.sh
sed -i 's/\r$//' rule-agent/deploy_ruleapp_to_odm.sh
```

See [TROUBLESHOOTING_BUILD_ERRORS.md](TROUBLESHOOTING_BUILD_ERRORS.md) for detailed solutions.

---

## Step 2: Create Required Configuration Files

### ⚠️ CRITICAL: These files are NOT in Git (for security)

The following files are in `.gitignore` and **must be created manually**:

### File 1: `llm.env` (REQUIRED)

This file configures the LLM provider and AWS credentials.

**Get this file from your colleague** or create it based on your LLM provider:

#### Option A: Using Ollama (Local LLM)

Create `llm.env` with:

```bash
# LLM Configuration
LLM_TYPE=LOCAL_OLLAMA
OLLAMA_SERVER_URL=http://host.docker.internal:11434
OLLAMA_MODEL_NAME=mistral

# AWS Configuration (for Textract and S3)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-east-1

# S3 Bucket for policy documents
S3_BUCKET_NAME=your-s3-bucket-name

# Drools Configuration (default values)
DROOLS_SERVER_URL=http://drools:8080/kie-server/services/rest/server
DROOLS_USERNAME=kieserver
DROOLS_PASSWORD=kieserver1!

# ODM Configuration (optional - only if using IBM ODM)
# ODM_SERVER_URL=http://odm:9060/DecisionService/rest
# ODM_USERNAME=odmAdmin
# ODM_PASSWORD=odmAdmin

# ADS Configuration (optional - only if using IBM ADS)
# ADS_SERVER_URL=https://your-ads-server
# ADS_USER_ID=your_user_id
# ADS_ZEN_APIKEY=your_api_key
```

**Before proceeding, replace:**
- `your_aws_access_key_id` with your actual AWS access key
- `your_aws_secret_access_key` with your actual AWS secret key
- `your-s3-bucket-name` with your S3 bucket name

#### Option B: Using Watsonx

Create `llm.env` with:

```bash
# LLM Configuration
LLM_TYPE=WATSONX
WATSONX_APIKEY=your_watsonx_api_key
WATSONX_PROJECT_ID=your_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_NAME=mistralai/mistral-7b-instruct-v0-2

# AWS Configuration (for Textract and S3)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-east-1

# S3 Bucket for policy documents
S3_BUCKET_NAME=your-s3-bucket-name

# Drools Configuration
DROOLS_SERVER_URL=http://drools:8080/kie-server/services/rest/server
DROOLS_USERNAME=kieserver
DROOLS_PASSWORD=kieserver1!
```

#### Option C: Using OpenAI

Create `llm.env` with:

```bash
# LLM Configuration
LLM_TYPE=OPENAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL_NAME=gpt-4
OPENAI_TEMPERATURE=0.0
OPENAI_MAX_TOKENS=4000

# AWS Configuration (for Textract and S3)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-east-1

# S3 Bucket for policy documents
S3_BUCKET_NAME=your-s3-bucket-name

# Drools Configuration
DROOLS_SERVER_URL=http://drools:8080/kie-server/services/rest/server
DROOLS_USERNAME=kieserver
DROOLS_PASSWORD=kieserver1!
```

### File 2: AWS Credentials (Alternative)

Instead of adding AWS credentials to `llm.env`, you can use AWS credential file:

**On Linux/Mac:**
```bash
~/.aws/credentials
```

**On Windows:**
```
C:\Users\<YourUsername>\.aws\credentials
```

**Content:**
```ini
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

---

## Step 3: Verify File Structure

After creating `llm.env`, verify you have:

```
underwriter-rule-based-llms/
├── llm.env                    ✅ YOU CREATED THIS
├── docker-compose.yml         ✅ From Git
├── rule-agent/
│   ├── Dockerfile             ✅ From Git
│   ├── requirements.txt       ✅ From Git
│   ├── serverStart.sh         ✅ From Git
│   └── ... (all Python files) ✅ From Git
├── data/
│   └── sample-loan-policy/
│       └── catalog/
│           └── loan-application-policy.txt  ✅ From Git
└── .gitignore                 ✅ From Git
```

---

## Step 4: Start Ollama (If Using Local LLM)

**Only if using `LLM_TYPE=LOCAL_OLLAMA`:**

### Install Ollama

**Mac:**
```bash
brew install ollama
```

**Windows/Linux:**
Download from https://ollama.com/download

### Start Ollama

```bash
# Start Ollama server
ollama serve

# In another terminal, pull the model
ollama pull mistral
```

**Verify:**
```bash
ollama list
# Should show: mistral
```

---

## Step 5: Build and Start Docker Containers

### Build the Backend Image

```bash
docker-compose build backend
```

**Expected output:**
```
Building backend
[+] Building 120.5s (10/10) FINISHED
 => [internal] load build definition from Dockerfile
 => => transferring dockerfile: 1.43kB
 => [internal] load .dockerignore
 => [internal] load metadata for docker.io/library/python:3.10
 => [1/5] FROM docker.io/library/python:3.10
 => [2/5] WORKDIR /code
 => [3/5] RUN apt-get update && apt-get install -y maven default-jdk
 => [4/5] COPY . /code
 => [5/5] RUN pip3 install -r requirements.txt
 => exporting to image
 => => naming to docker.io/library/backend
```

### Start All Services

```bash
docker-compose up -d
```

**Expected output:**
```
Creating network "underwriter-rule-based-llms_underwriting-net" ... done
Creating volume "underwriter-rule-based-llms_maven-repository" ... done
Creating volume "underwriter-rule-based-llms_rule-cache" ... done
Creating drools  ... done
Creating backend ... done
```

### Verify Services are Running

```bash
docker-compose ps
```

**Expected output:**
```
NAME       COMMAND                  SERVICE   STATUS         PORTS
backend    "/code/serverStart.sh"   backend   Up             0.0.0.0:9000->9000/tcp
drools     "/opt/jboss/tools/do…"   drools    Up (healthy)   0.0.0.0:8080->8080/tcp
```

---

## Step 6: Verify Setup

### Test Backend API

```bash
curl http://localhost:9000/rule-agent/docs
```

**Expected:** Swagger UI HTML should be returned

### Check Backend Logs

```bash
docker logs backend
```

**Expected output:**
```
Using LLM Service: Ollama
Using Ollama Server: http://host.docker.internal:11434
Rule cache initialized at: /data/rule_cache
✓ Container orchestrator enabled
Drools Deployment Service initialized with container orchestration enabled
 * Serving Flask app 'ChatService'
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:9000
 * Running on http://172.18.0.3:9000
```

### Check Drools Server

```bash
curl http://localhost:8080/kie-server/services/rest/server
```

**Expected:** XML response with server info

---

## Common Build Errors and Solutions

### Error 1: "llm.env: No such file or directory"

**Cause:** `llm.env` file is missing

**Solution:**
```bash
# Create the file as shown in Step 2
touch llm.env
# Edit with your configuration
nano llm.env  # or use your favorite editor
```

### Error 2: "Cannot connect to the Docker daemon"

**Cause:** Docker Desktop is not running

**Solution:**
1. Start Docker Desktop
2. Wait for it to fully start (whale icon in system tray)
3. Run `docker-compose up` again

### Error 3: "pip install failed" or "requirements.txt not found"

**Cause:** Building from wrong directory

**Solution:**
```bash
# Make sure you're in the root directory
cd underwriter-rule-based-llms
# NOT in rule-agent/

# Then build
docker-compose build backend
```

### Error 4: "Port 9000 already in use"

**Cause:** Another service is using port 9000

**Solution:**

**Option A - Stop the other service:**
```bash
# Find what's using port 9000
lsof -i :9000  # Mac/Linux
netstat -ano | findstr :9000  # Windows

# Kill the process
```

**Option B - Change the port:**

Edit `docker-compose.yml`:
```yaml
backend:
  ports:
    - "9001:9000"  # Change 9000 to 9001
```

### Error 5: "ERROR: Cannot start service drools: driver failed"

**Cause:** Not enough memory for Docker

**Solution:**

1. Open Docker Desktop → Settings → Resources
2. Increase memory to at least 4GB
3. Restart Docker Desktop
4. Run `docker-compose up` again

### Error 6: "AWS credentials not found"

**Cause:** Missing or invalid AWS credentials

**Solution:**

**Verify credentials in llm.env:**
```bash
cat llm.env | grep AWS_ACCESS_KEY_ID
```

**Or set up AWS CLI:**
```bash
aws configure
# Enter your credentials
```

---

## Step 7: Test the System

### Upload a Test Policy Document to S3

```bash
# Upload the sample policy
aws s3 cp data/sample-loan-policy/catalog/loan-application-policy.txt \
  s3://your-bucket-name/policies/loan-policy.txt
```

### Generate Rules from Policy

```bash
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "s3://your-bucket-name/policies/loan-policy.txt",
    "policy_type": "loan",
    "bank_id": "sample"
  }'
```

**Expected response:**
```json
{
  "status": "completed",
  "document_hash": "a3b5c7d9e1f2a4b6...",
  "steps": {
    "text_extraction": { "status": "success", "length": 45230 },
    "query_generation": { "queries": [...], "count": 48 },
    "rule_generation": { "status": "success" },
    "deployment": { "status": "success" }
  }
}
```

---

## What Files to Share with Your Colleague

### ✅ MUST Share

1. **`llm.env`** - LLM and AWS configuration
   - ⚠️ **Send securely** (contains credentials)
   - ⚠️ **Don't commit to Git**

### ✅ Already in Git (No Need to Share)

These are all version-controlled:
- `docker-compose.yml`
- `rule-agent/Dockerfile`
- `rule-agent/requirements.txt`
- `rule-agent/*.py` (all Python code)
- `data/sample-loan-policy/catalog/*.txt` (sample policies)

### ❌ DON'T Share

- `__pycache__/` folders (auto-generated)
- `*.pyc` files (auto-generated)
- `.env.local` files (local overrides)
- `data/rule_cache/` (will be created automatically)

---

## Quick Start Checklist for New Developer

- [ ] Clone repository
- [ ] Create `llm.env` file with:
  - [ ] LLM configuration (Ollama/Watsonx/OpenAI)
  - [ ] AWS credentials
  - [ ] S3 bucket name
- [ ] (If using Ollama) Install and start Ollama
- [ ] (If using Ollama) Pull mistral model: `ollama pull mistral`
- [ ] Build Docker image: `docker-compose build backend`
- [ ] Start services: `docker-compose up -d`
- [ ] Verify services: `docker-compose ps`
- [ ] Check logs: `docker logs backend`
- [ ] Test API: `curl http://localhost:9000/rule-agent/docs`
- [ ] Upload test policy to S3
- [ ] Test rule generation

---

## Advanced: Local Development (Without Docker)

If you want to run the backend locally for development:

### Install Dependencies

```bash
cd rule-agent
pip3 install -r requirements.txt
```

### Set Environment Variables

**Mac/Linux:**
```bash
export LLM_TYPE=LOCAL_OLLAMA
export OLLAMA_SERVER_URL=http://localhost:11434
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export DROOLS_SERVER_URL=http://localhost:8080/kie-server/services/rest/server
```

**Windows (PowerShell):**
```powershell
$env:LLM_TYPE="LOCAL_OLLAMA"
$env:OLLAMA_SERVER_URL="http://localhost:11434"
$env:AWS_ACCESS_KEY_ID="your_key"
$env:AWS_SECRET_ACCESS_KEY="your_secret"
```

### Start Backend

```bash
cd rule-agent
python3 -m flask --app ChatService run --port 9000
```

### Start Drools (Still Need Docker)

```bash
docker run -d \
  --name drools \
  -p 8080:8080 \
  quay.io/kiegroup/kie-server-showcase:latest
```

---

## Getting Help

### Check Logs

```bash
# Backend logs
docker logs backend -f

# Drools logs
docker logs drools -f

# All services
docker-compose logs -f
```

### Restart Services

```bash
# Restart everything
docker-compose restart

# Restart just backend
docker-compose restart backend

# Full rebuild
docker-compose down
docker-compose build backend
docker-compose up -d
```

### Clean Slate

```bash
# Stop and remove everything
docker-compose down -v

# Remove all images
docker-compose down --rmi all

# Start fresh
docker-compose build backend
docker-compose up -d
```

---

## Summary

**Minimum files your colleague needs:**

1. ✅ Git repository (clone it)
2. ✅ `llm.env` (you must share this - it's not in Git)
3. ✅ AWS credentials (in llm.env or ~/.aws/credentials)
4. ✅ Docker Desktop installed
5. ✅ (Optional) Ollama installed if using local LLM

**That's it!** Everything else is in Git.
