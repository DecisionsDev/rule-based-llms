# Clean Start - Delete and Recreate All Drools Containers

## Option 1: Delete Only Dedicated Containers (Keep Main Drools)

This keeps the main `drools` container (port 8080) but removes the dedicated ones:

```bash
# Stop and remove dedicated containers
docker stop drools-chase-loan-underwriting-rules drools-chase-insurance-underwriting-rules drools-tb-insurance-underwriting-rules
docker rm drools-chase-loan-underwriting-rules drools-chase-insurance-underwriting-rules drools-tb-insurance-underwriting-rules

# Verify they're gone
docker ps -a | grep drools
# Should only show: drools (main container on port 8080)
```

## Option 2: Delete ALL Drools Containers (Complete Clean Start)

This removes everything including the main drools container:

```bash
# Stop all drools containers
docker stop drools drools-chase-loan-underwriting-rules drools-chase-insurance-underwriting-rules drools-tb-insurance-underwriting-rules

# Remove all drools containers
docker rm drools drools-chase-loan-underwriting-rules drools-chase-insurance-underwriting-rules drools-tb-insurance-underwriting-rules

# Verify all are gone
docker ps -a | grep drools
# Should show nothing

# Restart the stack (this recreates main drools container)
docker-compose up -d
```

## Option 3: Nuclear Option (Complete Reset)

This removes everything including volumes and networks:

```bash
# Stop and remove everything
docker-compose down -v

# Remove all drools containers (including orphaned ones)
docker ps -a | grep drools | awk '{print $1}' | xargs docker rm -f

# Remove shared maven volume (optional - forces re-download of dependencies)
docker volume rm underwriter-rule-based-llms_maven-repository

# Start fresh
docker-compose up -d

# Wait for main drools to be healthy
docker ps | grep drools
```

## After Deletion: What Happens Next?

### Automatic Recreation

When you redeploy rules via `/process_policy_from_s3`, the system will:

1. ✅ Create NEW dedicated containers with proper restart policy
2. ✅ Deploy rules to both main server AND dedicated containers
3. ✅ Register containers in PostgreSQL database
4. ✅ Set restart policy to `unless-stopped` automatically

### Database Cleanup (Important!)

If you delete containers, you should also clean the database registry:

```sql
-- Connect to PostgreSQL
docker exec -it postgres psql -U underwriting_user -d underwriting_db

-- View current containers
SELECT container_id, status, health_status, port FROM rule_containers;

-- Delete entries for removed containers
DELETE FROM rule_containers WHERE container_id LIKE 'drools-%';

-- Or delete ALL container entries (complete reset)
DELETE FROM rule_containers;
DELETE FROM extracted_rules;

-- Exit
\q
```

## Recommended Clean Start Process

```bash
# 1. Stop backend to prevent conflicts
docker-compose stop backend

# 2. Remove dedicated containers
docker stop drools-chase-loan-underwriting-rules drools-chase-insurance-underwriting-rules drools-tb-insurance-underwriting-rules
docker rm drools-chase-loan-underwriting-rules drools-chase-insurance-underwriting-rules drools-tb-insurance-underwriting-rules

# 3. Clean database (from host or via docker exec)
docker exec -it postgres psql -U underwriting_user -d underwriting_db -c "DELETE FROM rule_containers WHERE container_id LIKE 'drools-%';"

# 4. Restart backend
docker-compose up -d backend

# 5. Verify main drools is running
docker ps | grep drools
# Should show only: drools (port 8080)

# 6. Redeploy your rules
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "your-policy-pdf-url",
    "policy_type": "loan",
    "bank_id": "chase"
  }'

# 7. Verify new containers created with restart policy
docker ps | grep drools
docker inspect drools-chase-loan-underwriting-rules --format '{{.HostConfig.RestartPolicy.Name}}'
# Should output: unless-stopped
```

## What Gets Preserved?

✅ **PostgreSQL data** - Banks, policy types, extracted rules
✅ **Main drools container** (if using Option 1)
✅ **Docker network** (underwriting-net)
✅ **Maven repository volume** (unless you use -v flag)
✅ **S3 uploaded files** (JARs, DRLs, Excel)

## What Gets Deleted?

❌ **Dedicated Drools containers** (drools-chase-*, drools-tb-*)
❌ **Container registry entries in database** (if you run DELETE commands)
❌ **Deployed KJARs in container memory** (not in volume)

## Benefits of Clean Start

1. ✅ **Tests the fix** - Verifies new containers get restart policy
2. ✅ **Clean state** - No old configuration issues
3. ✅ **Confidence** - Proves the system can recreate everything
4. ✅ **Documentation** - You'll see exactly what happens during deployment

## Quick Commands Cheatsheet

```bash
# Delete dedicated containers only
docker rm -f drools-chase-loan-underwriting-rules drools-chase-insurance-underwriting-rules drools-tb-insurance-underwriting-rules

# Delete database entries
docker exec -it postgres psql -U underwriting_user -d underwriting_db -c "DELETE FROM rule_containers WHERE container_id LIKE 'drools-%';"

# Verify main drools still running
docker ps | grep "^.*drools[^-]"

# Check database is empty
docker exec -it postgres psql -U underwriting_user -d underwriting_db -c "SELECT container_id FROM rule_containers;"
```

## My Recommendation

Go with **Option 1** (delete only dedicated containers):
- ✅ Safest option
- ✅ Main drools stays up (no downtime)
- ✅ Tests the fix properly
- ✅ Quick recovery

Then redeploy your rules to verify everything works with the new restart policy! 🚀
