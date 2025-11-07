# Troubleshooting: Backend Container Build Errors

## Error: "exec /code/serverStart.sh: no such file or directory"

### Symptoms

Container fails to start with error:
```
exec /code/serverStart.sh: no such file or directory
```

Or when checking logs:
```bash
docker logs backend
# Shows: exec /code/serverStart.sh: no such file or directory
```

### Root Causes

This error happens when:
1. ❌ **Files not copied to container** - Shell scripts excluded by `.dockerignore`
2. ❌ **Wrong line endings** - Windows CRLF vs Linux LF
3. ❌ **Build context issue** - Building from wrong directory
4. ❌ **File permissions** - Script not executable

---

## Solution 1: Fix Line Endings (Most Common on Windows)

### The Problem

If you cloned the repo on **Windows**, Git may have converted line endings from LF (Linux) to CRLF (Windows). Docker containers use Linux, which can't execute files with CRLF line endings.

### The Fix

#### Option A: Convert Line Endings (Recommended)

**Using Git Bash or WSL:**
```bash
cd rule-agent

# Convert serverStart.sh to LF
dos2unix serverStart.sh
# Or if dos2unix is not installed:
sed -i 's/\r$//' serverStart.sh

# Convert deploy_ruleapp_to_odm.sh to LF
dos2unix deploy_ruleapp_to_odm.sh
# Or:
sed -i 's/\r$//' deploy_ruleapp_to_odm.sh
```

**Using VS Code:**
1. Open `serverStart.sh` in VS Code
2. Look at bottom-right corner - it shows "CRLF" or "LF"
3. Click on "CRLF" and select "LF"
4. Save the file
5. Repeat for `deploy_ruleapp_to_odm.sh`

**Using Notepad++:**
1. Open `serverStart.sh`
2. Edit → EOL Conversion → Unix (LF)
3. Save
4. Repeat for `deploy_ruleapp_to_odm.sh`

#### Option B: Configure Git to Keep LF (Prevent Future Issues)

Create/edit `.gitattributes` in repo root:

```bash
# In repository root
cat > .gitattributes << 'EOF'
# Shell scripts must use LF (Linux line endings)
*.sh text eol=lf

# Python files can use LF
*.py text eol=lf

# Dockerfile and docker-compose use LF
Dockerfile text eol=lf
docker-compose.yml text eol=lf
EOF
```

Then reset files:
```bash
# Remove all files from Git's index
git rm --cached -r .

# Re-add all files with correct line endings
git add .

# Commit
git commit -m "Normalize line endings"
```

### Verify Line Endings

```bash
# Check line endings
file rule-agent/serverStart.sh

# Should show:
# serverStart.sh: Bourne-Again shell script, ASCII text executable

# If it shows "CRLF", you need to convert
```

---

## Solution 2: Verify Files Are Copied

### Check Dockerfile

The `Dockerfile` should have:

```dockerfile
COPY . /code
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt && chmod a+x /code/*.sh
```

The `chmod a+x /code/*.sh` makes all shell scripts executable.

### Verify Build Context

**Build from the repository root, NOT from rule-agent:**

```bash
# CORRECT - from repo root
cd underwriter-rule-based-llms
docker-compose build backend

# WRONG - from rule-agent
cd underwriter-rule-based-llms/rule-agent  # ❌ DON'T DO THIS
docker build -t backend .  # ❌ This won't work with docker-compose
```

The `docker-compose.yml` expects to build from repo root with context pointing to `rule-agent/`:

```yaml
backend:
  build: rule-agent  # This sets the build context
```

---

## Solution 3: Check .dockerignore

Ensure `.dockerignore` is NOT excluding shell scripts.

**In `rule-agent/.dockerignore`, verify these lines exist:**

```
# Shell scripts should NOT be ignored
# *.sh  ← This line should NOT exist
```

**If you see `*.sh` in `.dockerignore`, REMOVE IT!**

Current `.dockerignore` is correct - it doesn't exclude `.sh` files.

---

## Solution 4: Clean Build (Nuclear Option)

If above solutions don't work, do a complete rebuild:

```bash
# Stop and remove all containers
docker-compose down

# Remove the backend image
docker rmi backend

# Remove build cache
docker builder prune -a

# Rebuild from scratch
docker-compose build --no-cache backend

# Start
docker-compose up -d
```

---

## Solution 5: Debug Inside Container

### Inspect the Built Image

```bash
# Build the image
docker-compose build backend

# Run a shell in the image to inspect
docker run -it --rm backend sh

# Once inside, check if files exist
ls -la /code/serverStart.sh
ls -la /code/deploy_ruleapp_to_odm.sh

# Check line endings
cat -A /code/serverStart.sh | head -5
# If you see ^M at end of lines, that's CRLF (bad)
# If you don't see ^M, it's LF (good)
```

### Check File Permissions

```bash
# Inside the container
ls -la /code/*.sh

# Should show:
# -rwxr-xr-x  1 root root  306 Nov  3 16:44 serverStart.sh
# -rwxr-xr-x  1 root root 1322 Nov  4 14:30 deploy_ruleapp_to_odm.sh

# If not executable (no 'x'), the chmod in Dockerfile didn't work
```

---

## Complete Step-by-Step Fix (Windows Users)

If your colleague is on **Windows**, have them follow these exact steps:

### Step 1: Fix Line Endings

```powershell
# Open PowerShell in repository root
cd underwriter-rule-based-llms

# Install dos2unix (if not installed)
# Using Git Bash:
#   pacman -S dos2unix

# Or use WSL:
wsl dos2unix rule-agent/serverStart.sh
wsl dos2unix rule-agent/deploy_ruleapp_to_odm.sh

# Or manually in VS Code (see above)
```

### Step 2: Create .gitattributes

```powershell
# In repo root
@"
# Shell scripts must use LF
*.sh text eol=lf
*.py text eol=lf
Dockerfile text eol=lf
docker-compose.yml text eol=lf
"@ | Out-File -FilePath .gitattributes -Encoding ASCII
```

### Step 3: Clean and Rebuild

```powershell
# Stop containers
docker-compose down

# Remove old image
docker rmi backend

# Rebuild
docker-compose build backend

# Start
docker-compose up -d

# Verify
docker logs backend
```

### Step 4: Verify Working

```powershell
# Should see Flask starting
docker logs backend

# Should show:
# * Serving Flask app 'ChatService'
# * Running on all addresses (0.0.0.0)
# * Running on http://127.0.0.1:9000
```

---

## Alternative: Use Pre-Built Image (Quick Workaround)

If build keeps failing, you can share a pre-built image:

### On Your Machine (Working Setup)

```bash
# Save the image
docker save backend:latest -o backend-image.tar

# Compress it
gzip backend-image.tar

# Share backend-image.tar.gz with colleague (1-2 GB file)
```

### On Colleague's Machine

```bash
# Load the image
docker load -i backend-image.tar.gz

# Tag it
docker tag backend:latest backend

# Start (skip build)
docker-compose up -d
```

**Note**: This is a workaround, not a permanent solution.

---

## Verification Commands

After fixing, verify everything works:

```bash
# 1. Check container is running
docker-compose ps
# STATUS should be "Up"

# 2. Check logs show Flask started
docker logs backend | grep "Running on"
# Should show: * Running on http://127.0.0.1:9000

# 3. Test API
curl http://localhost:9000/rule-agent/docs
# Should return HTML

# 4. Check file inside container
docker exec backend ls -la /code/serverStart.sh
# Should show: -rwxr-xr-x ... serverStart.sh
```

---

## Summary: Most Common Fix for Windows Users

**TL;DR:**

```bash
# 1. Fix line endings
cd underwriter-rule-based-llms/rule-agent
dos2unix serverStart.sh deploy_ruleapp_to_odm.sh

# 2. Rebuild
cd ..
docker-compose down
docker rmi backend
docker-compose build backend
docker-compose up -d

# 3. Verify
docker logs backend
```

**Root Cause**: Windows line endings (CRLF) don't work in Linux containers. Converting to LF fixes it.

---

## Additional Resources

- **Line endings explained**: https://docs.github.com/en/get-started/getting-started-with-git/configuring-git-to-handle-line-endings
- **.gitattributes guide**: https://git-scm.com/docs/gitattributes
- **Docker build context**: https://docs.docker.com/build/building/context/

---

## Quick Diagnostic

Run this to diagnose the issue:

```bash
# Check if files exist
ls -la rule-agent/serverStart.sh

# Check line endings
file rule-agent/serverStart.sh

# Check permissions
ls -la rule-agent/*.sh

# Check what's being copied
docker-compose build backend 2>&1 | grep -i "copy"

# Check inside container
docker run --rm backend ls -la /code/*.sh
```

**Expected output:**
```
-rwxr-xr-x ... serverStart.sh: Bourne-Again shell script, ASCII text executable
```

**Problem output:**
```
serverStart.sh: Bourne-Again shell script, ASCII text executable, with CRLF line terminators
```

If you see "CRLF line terminators", that's the issue!
