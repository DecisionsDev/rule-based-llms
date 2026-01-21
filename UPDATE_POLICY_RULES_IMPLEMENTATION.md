# Update Policy Rules Implementation - Complete

## Summary

Successfully implemented a new endpoint `/api/v1/policies/update-rules` that allows updating rules for an existing policy without reprocessing the entire document. This enables quick rule updates, fixes, and modifications after initial policy processing.

## Changes Made

### 1. Database Methods Added (`rule-agent/DatabaseService.py`)

#### `update_container_version(container_id, version)` (Lines 610-620)
- Updates the version number for a container
- Automatically updates the `updated_at` timestamp
- Returns the updated container object
- Used for version tracking after rule updates

#### `log_deployment_history(...)` (Lines 622-648)
- Logs deployment history entries for audit trail
- Tracks action type (deployed, updated, stopped, restarted, failed)
- Records version, platform, endpoint, and document hash
- Includes optional change description and deployed_by fields
- Creates entries in the `container_deployment_history` table

### 2. New API Endpoint (`rule-agent/ChatService.py`)

#### `/api/v1/policies/update-rules` (Lines 757-1011)
**Method:** POST  
**Description:** Update policy rules and redeploy without reprocessing the document

**Request Body:**
```json
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "drl_content": "package com.underwriting; rule \"New Rule\" when ... then ... end"
}
```

**Workflow:**
1. **Step 1:** Parse DRL and save rules to database
   - Uses `underwritingWorkflow._parse_drl_rules()`
   - Saves extracted rules via `db_service.save_extracted_rules()`
   - Automatically deactivates old rules (soft delete)

2. **Step 2:** Redeploy rules to Drools KIE Server
   - Uses `underwritingWorkflow.drools_deployment.deploy_rules_automatically()`
   - Creates new KJar with updated rules
   - Deploys to both main server and dedicated container

3. **Step 3:** Update container metadata
   - Increments version number
   - Updates `updated_at` timestamp

4. **Step 4:** Upload artifacts to S3
   - Uploads new JAR file
   - Uploads new DRL file
   - Updates S3 URLs in database
   - Cleans up temporary files

5. **Step 5:** Log deployment history
   - Records the update action
   - Tracks version change
   - Adds audit trail entry

**Response:**
```json
{
  "status": "completed",
  "bank_id": "chase",
  "policy_type": "insurance",
  "container_id": "chase-insurance-underwriting-rules",
  "new_version": 2,
  "steps": {
    "update_database_rules": {
      "status": "success",
      "count": 5,
      "rule_ids": [101, 102, 103, 104, 105]
    },
    "redeployment": {
      "status": "success",
      "container_id": "chase-insurance-underwriting-rules"
    },
    "update_container": {
      "status": "success",
      "new_version": 2
    },
    "s3_upload": {
      "jar": { "status": "success", "s3_url": "..." },
      "drl": { "status": "success", "s3_url": "..." }
    }
  }
}
```

### 3. Swagger Documentation (`rule-agent/swagger.yaml`)

- **Version Updated:** 2.3.0 → 2.4.0
- **New Section:** Added comprehensive documentation for `/api/v1/policies/update-rules`
- **Includes:**
  - Detailed endpoint description
  - Request/response schemas
  - Multiple examples (insurance rules, loan rules)
  - Error response documentation (400, 404, 500)
  - Use case explanations
  - Prerequisites and version management details

## Existing Functionality Verification

✅ **No Breaking Changes:**
- All existing endpoints remain unchanged
- No route conflicts (different path/method combinations)
- No changes to existing database schemas
- No modifications to existing methods

✅ **Compatible with Existing Code:**
- Uses same patterns as existing database methods
- Follows same workflow structure as `process_policy_from_s3`
- Reuses existing services (`UnderwritingWorkflow`, `DroolsDeploymentService`, `S3Service`)
- All required imports already present

✅ **Database Integrity:**
- New methods follow same SQLAlchemy patterns
- Uses existing models and relationships
- No schema migrations required
- Compatible with existing audit trail system

## Key Features

### Version Management
- Automatic version incrementing on each update
- Version tracked in `rule_containers.version` column
- Deployment history records version changes

### Audit Trail
- All updates logged to `container_deployment_history` table
- Tracks who made changes and when
- Records change descriptions
- Full audit compliance

### Multi-Tenant Support
- Works with existing bank+policy isolation
- Container IDs auto-generated consistently
- Supports all existing policy types

### Error Handling
- Validates container exists before proceeding
- Graceful handling of deployment failures
- Detailed error messages in responses
- Doesn't fail entire workflow if metadata update fails

### Clean Architecture
- Reuses existing deployment infrastructure
- Follows same patterns as initial policy processing
- Maintains separation of concerns
- Easy to extend in the future

## Usage Example

### Initial Policy Processing
```bash
POST /rule-agent/process_policy_from_s3
{
  "s3_url": "s3://bucket/chase-insurance-policy.pdf",
  "bank_id": "chase",
  "policy_type": "insurance"
}
# Creates container with version 1
```

### Update Rules
```bash
POST /rule-agent/api/v1/policies/update-rules
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "drl_content": "package com.underwriting;\n\nrule \"Updated Age Rule\" ..."
}
# Updates container to version 2
```

### Query Updated Rules
```bash
GET /rule-agent/api/v1/policies?bank_id=chase&policy_type=insurance&include_rules=true
# Returns updated rules with new version
```

## Testing Recommendations

1. **Happy Path:**
   - Process initial policy
   - Update rules with valid DRL
   - Verify version increment
   - Check deployment history

2. **Error Cases:**
   - Update non-existent container (404)
   - Invalid DRL syntax (500)
   - Missing required fields (400)

3. **Integration:**
   - Verify rules work after update
   - Check S3 artifacts uploaded correctly
   - Confirm database entries created
   - Test evaluate-policy endpoint still works

## Benefits

✅ **Faster Rule Updates** - No need to reprocess entire document  
✅ **Version Control** - Track all rule changes over time  
✅ **Audit Compliance** - Complete deployment history  
✅ **Flexibility** - Quickly fix bugs or tweak rules  
✅ **Consistency** - Uses same deployment infrastructure  
✅ **Multi-Tenant** - Works with existing isolation model  

## Files Modified

1. `rule-agent/DatabaseService.py` - Added 2 new methods
2. `rule-agent/ChatService.py` - Added new endpoint (255 lines)
3. `rule-agent/swagger.yaml` - Updated documentation and version

## No Files Deleted

All changes are additive - no existing functionality removed or modified.

