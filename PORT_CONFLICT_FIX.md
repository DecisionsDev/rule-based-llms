# Port Conflict Fix - Database-Docker Synchronization Issue

## Problem Summary

When deploying rules for multiple banks (e.g., `chase`, `tb`), the dedicated Docker container creation fails with a port conflict error:

```
Bind for 0.0.0.0:8084 failed: port is already allocated
Container drools-tb-insurance-underwriting-rules is not running (status: created)
```

## Root Cause

The issue is a **mismatch between the database records and actual Docker containers**:

### What Happened

1. **Initial State**:
   - Database had ports 8081-8083 allocated to `chase`, `boa`, and `tb`
   - But the actual Docker containers were using different ports

2. **Port Allocation Logic**:
   ```python
   # ContainerOrchestrator.py:584
   def _get_next_available_port(self) -> int:
       """Get next available port for Docker containers from database"""
       containers = self.db_service.list_containers(active_only=True)
       used_ports = [c['port'] for c in containers if c.get('port') is not None]

       port = self.base_port  # 8084
       while port in used_ports:
           port += 1
       return port
   ```

3. **The Problem**:
   - Database showed ports 8081, 8082, 8083 as used
   - Port allocation function checked DB and thought 8084 was free
   - But Docker actually had a container already running on 8084
   - New container creation failed with "port already allocated"

### Why This Happened

- **Containers were created/removed** without updating the database
- **Database had stale records** from old containers
- **New containers were created** on different ports than DB expected
- **Port allocation relied on DB** but DB was out of sync with reality

## Solution Applied

### Immediate Fix

1. **Removed all dedicated drools containers**:
   ```bash
   docker rm -f drools-tb-insurance-underwriting-rules
   docker rm -f drools-chase-insurance-underwriting-rules
   ```

2. **Cleaned up database records**:
   ```sql
   DELETE FROM rule_containers
   WHERE container_id IN (
       'chase-insurance-underwriting-rules',
       'tb-insurance-underwriting-rules',
       'boa-loan-underwriting-rules'
   );
   ```

3. **Verified cleanup**:
   - ✓ No drools containers running
   - ✓ Database has 0 container records
   - ✓ Fresh state for new deployments

### Verification

```bash
# Check containers
docker ps -a | grep "drools-"
# Output: (none)

# Check database
docker exec postgres psql -U underwriting_user -d underwriting_db -c \
  "SELECT container_id, port FROM rule_containers;"
# Output: 0 rows
```

## How to Redeploy

Now you can redeploy rules for multiple banks and they will get sequential ports:

### 1. Deploy Chase Insurance
```bash
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "https://uw-data-extraction.s3.us-east-1.amazonaws.com/sample-policies/sample_life_insurance_policy.pdf",
    "policy_type": "insurance",
    "bank_id": "chase"
  }'
```

**Expected**: Container `drools-chase-insurance-underwriting-rules` on port **8084**

### 2. Deploy TB Insurance
```bash
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "https://uw-data-extraction.s3.us-east-1.amazonaws.com/sample-policies/sample_life_insurance_policy.pdf",
    "policy_type": "insurance",
    "bank_id": "tb"
  }'
```

**Expected**: Container `drools-tb-insurance-underwriting-rules` on port **8085**

### 3. Deploy BofA Loan
```bash
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "s3://your-bucket/bofa-loan-policy.pdf",
    "policy_type": "loan",
    "bank_id": "boa"
  }'
```

**Expected**: Container `drools-boa-loan-underwriting-rules` on port **8086**

## Long-Term Prevention

### Issue: Database-Docker Sync

The system needs better synchronization between database records and actual Docker containers.

### Recommended Improvements

1. **Container Health Check on Startup**:
   - On backend startup, scan actual Docker containers
   - Compare with database records
   - Remove stale DB records
   - Update DB with actual container ports

2. **Robust Port Allocation**:
   - Query both DB AND Docker for used ports
   - Use the union of both sources
   - Prevent double-allocation

3. **Atomic Container Creation**:
   - Use transactions for container + DB operations
   - If Docker creation fails, don't save to DB
   - If DB save fails, remove Docker container

### Proposed Code Enhancement

```python
def _get_next_available_port(self) -> int:
    """Get next available port checking both DB and Docker"""
    import docker

    # Get ports from database
    containers = self.db_service.list_containers(active_only=True)
    db_ports = set(c['port'] for c in containers if c.get('port') is not None)

    # Get ports from actual Docker containers
    client = docker.from_env()
    docker_ports = set()
    for container in client.containers.list(all=True):
        if container.name.startswith('drools-'):
            for port_binding in container.attrs.get('NetworkSettings', {}).get('Ports', {}).values():
                if port_binding:
                    for binding in port_binding:
                        docker_ports.add(int(binding['HostPort']))

    # Use union of both sources
    used_ports = db_ports | docker_ports

    port = self.base_port
    while port in used_ports:
        port += 1
    return port
```

## Testing

After cleanup, test multi-bank deployment:

1. Deploy `chase` → Should get port 8084
2. Deploy `tb` → Should get port 8085
3. Deploy `boa` → Should get port 8086

Verify:
```bash
docker ps | grep "drools-"
# Should show 3 containers on ports 8084, 8085, 8086
```

## Related Files

- [rule-agent/ContainerOrchestrator.py:584](rule-agent/ContainerOrchestrator.py#L584) - Port allocation logic
- [rule-agent/ContainerOrchestrator.py:214](rule-agent/ContainerOrchestrator.py#L214) - Container creation
- [rule-agent/ContainerOrchestrator.py:329](rule-agent/ContainerOrchestrator.py#L329) - Database registration

## Status

- ✓ **Immediate Fix Applied**: All containers and DB records cleaned up
- ✓ **System Ready**: Can now deploy multiple banks without port conflicts
- ⏳ **Long-term Fix**: Needs code enhancement for better DB-Docker sync
