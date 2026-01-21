# ContainerOrchestrator.py - Database Integration Update Instructions

## Overview

The `ContainerOrchestrator.py` file needs several updates to replace JSON file registry with PostgreSQL database. Due to the file's size (710 lines), here are the specific changes needed.

## Files Involved

- **Main file**: `ContainerOrchestrator.py` (to be updated)
- **Reference**: `ContainerOrchestrator_DB_Updates.py` (contains new methods)

---

## Update Instructions

### Step 1: Update Imports (Lines 1-17)

**FIND:**
```python
import os
import json
import time
import requests
from typing import Dict, Optional, List
from datetime import datetime
```

**REPLACE WITH:**
```python
import os
import json
import time
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime

from DatabaseService import get_database_service

logger = logging.getLogger(__name__)
```

---

### Step 2: Update `__init__` Method (Lines 23-48)

**FIND:**
```python
def __init__(self):
    self.platform = os.getenv('ORCHESTRATION_PLATFORM', 'docker')
    self.registry_file = '/data/container_registry.json'
    self.base_port = 8081

    # ... rest of init ...

    # Load container registry
    self.registry = self._load_registry()

    print(f"Container Orchestrator initialized for platform: {self.platform}")
```

**REPLACE WITH:**
```python
def __init__(self):
    self.platform = os.getenv('ORCHESTRATION_PLATFORM', 'docker')
    self.registry_file = '/data/container_registry.json'  # Legacy (for migration)
    self.base_port = 8081

    # ... rest of init ...

    # Database service for persistent registry
    self.db_service = get_database_service()

    # Migrate legacy JSON registry to database if exists
    self._migrate_legacy_registry()

    logger.info(f"Container Orchestrator initialized for platform: {self.platform}")
```

---

### Step 3: Update Registry Methods (Lines 50-60)

**FIND:**
```python
def _load_registry(self) -> Dict:
    """Load the container registry from disk"""
    if os.path.exists(self.registry_file):
        with open(self.registry_file, 'r') as f:
            return json.load(f)
    return {}

def _save_registry(self):
    """Save the container registry to disk"""
    os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
    with open(self.registry_file, 'w') as f:
        json.dump(self.registry, f, indent=2)
```

**REPLACE WITH:**
```python
def _load_registry(self) -> Dict:
    """Load the container registry from disk (LEGACY - for migration only)"""
    if os.path.exists(self.registry_file):
        with open(self.registry_file, 'r') as f:
            return json.load(f)
    return {}

def _save_registry(self):
    """DEPRECATED: Registry is now saved to database automatically"""
    pass  # Kept for backward compatibility
```

---

### Step 4: Add Migration Method (After `_save_registry`)

**ADD NEW METHOD:**

See full implementation in `ContainerOrchestrator_DB_Updates.py` - Method: `_migrate_legacy_registry()`

Key points:
- Reads legacy JSON file
- Extracts bank_id and policy_type from container_id
- Creates database entries
- Renames legacy file to `.migrated`

---

### Step 5: Update `get_container_endpoint` (Lines 118-166)

**Current implementation uses:**
```python
if container_id not in self.registry:
    return None
container_info = self.registry[container_id]
```

**Replace with:**
```python
container = self.db_service.get_container_by_id(container_id)
if not container or not container.is_active:
    return None
```

See full updated method in the main file - already updated.

---

### Step 6: Update `list_containers` (Lines 168-175)

**REPLACE:**
```python
def list_containers(self) -> Dict:
    self._sync_container_statuses()
    return {
        "platform": self.platform,
        "containers": self.registry
    }
```

**WITH:**

See `list_containers_NEW()` in `ContainerOrchestrator_DB_Updates.py`

---

### Step 7: Update Container Registration (Lines 222-231 and 372-381)

In both `_create_docker_container` and `_create_k8s_pod`:

**FIND:**
```python
self.registry[container_id] = {
    'platform': 'docker',
    'container_name': container_name,
    ...
}
self._save_registry()
```

**REPLACE WITH:**
```python
# Extract bank_id and policy_type from container_id
parts = container_id.split('-')
bank_id = parts[0] if len(parts) >= 1 else 'unknown'
policy_type_id = parts[1] if len(parts) >= 2 else 'unknown'

self.register_container_in_db(
    container_id, bank_id, policy_type_id,
    container_name, endpoint, port
)
```

**AND ADD NEW METHOD:**

See `register_container_in_db()` in `ContainerOrchestrator_DB_Updates.py`

---

### Step 8: Update Delete Methods (Lines 412-483)

**Replace both:**
- `_delete_docker_container()`
- `_delete_k8s_pod()`

With database-backed versions from `ContainerOrchestrator_DB_Updates.py`:
- `_delete_docker_container_NEW()`
- `_delete_k8s_pod_NEW()`

Key change: Use `self.db_service.get_container_by_id()` instead of `self.registry`

---

### Step 9: Update `_get_next_available_port` (Lines 485-491)

**REPLACE:**
```python
def _get_next_available_port(self) -> int:
    used_ports = [info['port'] for info in self.registry.values() if 'port' in info]
    port = self.base_port
    while port in used_ports:
        port += 1
    return port
```

**WITH:**
```python
def _get_next_available_port(self) -> int:
    """Get next available port from database"""
    containers = self.db_service.list_containers(active_only=True)
    used_ports = [c.port for c in containers if c.port is not None]

    port = self.base_port
    while port in used_ports:
        port += 1
    return port
```

---

### Step 10: Update Health Check Methods

**Replace:**
- `_check_docker_container_health()` → `_check_docker_container_health_db()`
- `_check_k8s_pod_health()` → `_check_k8s_pod_health_db()`

**Key changes:**
- Accept `container` object (SQLAlchemy model) instead of `container_id` string
- Access properties via `container.container_name`, `container.endpoint`, etc.

See full implementations in `ContainerOrchestrator_DB_Updates.py`

---

### Step 11: Update `_sync_container_statuses` (Lines 555-583)

**REPLACE:**
```python
def _sync_container_statuses(self):
    for container_id, container_info in self.registry.items():
        # ... check health ...
        container_info['status'] = new_status
        self._save_registry()
```

**WITH:**
```python
def _sync_container_statuses(self):
    containers = self.db_service.list_containers(active_only=True)

    for container in containers:
        # ... check health ...
        if status_changed:
            self.db_service.update_container_status(
                container.container_id,
                status=new_status,
                health_status=new_health
            )
```

See full implementation: `_sync_container_statuses_NEW()` in `ContainerOrchestrator_DB_Updates.py`

---

## Quick Update Checklist

- [ ] Update imports to include `DatabaseService` and `logging`
- [ ] Add `self.db_service` in `__init__`
- [ ] Add `_migrate_legacy_registry()` method
- [ ] Update `_save_registry()` to be no-op
- [ ] Update `get_container_endpoint()` to use database
- [ ] Update `list_containers()` to query database
- [ ] Add `register_container_in_db()` helper method
- [ ] Update both `_create_*_container()` methods to use database
- [ ] Update both `_delete_*_container()` methods to use database
- [ ] Update `_get_next_available_port()` to query database
- [ ] Replace `_check_*_health()` with `_check_*_health_db()` versions
- [ ] Update `_sync_container_statuses()` to use database

---

## Testing

After making changes:

1. **Start services:**
   ```bash
   docker-compose up
   ```

2. **Verify migration:**
   - Check logs for "Legacy registry migration completed"
   - Verify legacy file renamed to `.migrated`

3. **Test container operations:**
   ```bash
   # List containers
   curl http://localhost:9000/rule-agent/drools_containers

   # Deploy new rules
   curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
     -H "Content-Type: application/json" \
     -d '{"s3_url": "...", "bank_id": "test", "policy_type": "insurance"}'
   ```

4. **Verify database entries:**
   ```bash
   docker exec -it postgres psql -U underwriting_user -d underwriting_db \
     -c "SELECT container_id, bank_id, status FROM rule_containers;"
   ```

---

## Rollback Plan

If issues occur:

1. **Restore legacy JSON file:**
   ```bash
   mv /data/container_registry.json.migrated /data/container_registry.json
   ```

2. **Revert code changes** using git

3. **Restart services:**
   ```bash
   docker-compose restart backend
   ```

---

## Notes

- The database integration is **backward compatible** - old methods are kept as no-ops
- Migration happens **automatically** on first startup
- All database operations have **error handling** - failures won't crash the system
- The `ContainerOrchestrator_DB_Updates.py` file contains all new method implementations for reference

---

## Support

For questions or issues:
- See main guide: [POSTGRESQL_INTEGRATION_GUIDE.md](../POSTGRESQL_INTEGRATION_GUIDE.md)
- Check database service: [DatabaseService.py](DatabaseService.py)
- Review update reference: [ContainerOrchestrator_DB_Updates.py](ContainerOrchestrator_DB_Updates.py)
