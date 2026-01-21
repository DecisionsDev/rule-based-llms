# Extracted Rules Integration Fix

## Issue

After implementing the extracted rules feature, the API endpoint `/api/v1/extracted-rules` was returning empty results even though the workflow successfully processed policy documents and deployed Drools rules.

```json
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "rule_count": 0,
  "rules": [],
  "status": "success"
}
```

## Root Cause

The underwriting workflow (`UnderwritingWorkflow.py`) was:
1. ✅ Extracting policy rules using LLM
2. ✅ Generating Drools DRL rules
3. ✅ Deploying to Drools KIE Server
4. ✅ Uploading artifacts to S3
5. ❌ **But NOT saving the extracted rules to the `extracted_rules` database table**

The workflow had all the necessary data (queries/rules extracted by the LLM) but wasn't persisting them to the database for the frontend API to retrieve.

## Solution

Added **Step 2.5** to the workflow to save extracted rules to the database immediately after LLM analysis.

### Changes Made

**File**: [rule-agent/UnderwritingWorkflow.py](rule-agent/UnderwritingWorkflow.py#L170-L220)

Added new step after LLM query generation (Step 2) to save rules to database:

```python
# Step 2.5: Save extracted rules to database
if bank_id and policy_type:
    try:
        print("\n" + "="*60)
        print("Step 2.5: Saving extracted rules to database...")
        print("="*60)

        # Convert queries into rule format for database
        rules_for_db = []
        categories = analysis.get("rule_categories", [])

        # Map each query to a rule entry
        for idx, query in enumerate(queries):
            # Try to determine category from the query text
            category = "General Requirements"
            for cat in categories:
                if any(keyword in query.lower() for keyword in cat.lower().split()):
                    category = cat
                    break

            rule_entry = {
                "rule_name": f"Rule {idx + 1}",
                "requirement": query,
                "category": category,
                "source_document": s3_key.split('/')[-1]
            }
            rules_for_db.append(rule_entry)

        # Save to database
        saved_ids = self.db_service.save_extracted_rules(
            bank_id=bank_id,
            policy_type_id=policy_type,
            rules=rules_for_db,
            source_document=s3_key,
            document_hash=document_hash
        )

        print(f"✓ Saved {len(saved_ids)} extracted rules to database")

    except Exception as e:
        print(f"⚠ Failed to save extracted rules to database: {e}")
```

## Updated Workflow

The complete workflow now includes:

1. **Step 0**: Parse S3 URL
2. **Step 1**: Extract text from PDF
3. **Step 1.5**: Check cache for rules
4. **Step 2**: LLM analyzes document and generates queries
5. **Step 2.5**: 🆕 **Save extracted rules to database**
6. **Step 3**: AWS Textract extracts structured data
7. **Step 4**: Generate Drools DRL rules
8. **Step 5**: Deploy rules to Drools KIE Server
9. **Step 6**: Upload JAR, DRL, and Excel to S3
10. **Step 6.5**: Update container registry in database
11. **Step 7**: Cache rules for future use

## How It Works

### Rule Extraction and Categorization

The workflow:
1. Takes the LLM-generated queries (policy rules)
2. Maps them to categories based on keywords
3. Formats them as rule entries with:
   - `rule_name`: Sequential naming ("Rule 1", "Rule 2", etc.)
   - `requirement`: The actual rule text
   - `category`: Inferred from rule categories
   - `source_document`: The PDF filename
4. Saves to `extracted_rules` table with metadata:
   - `document_hash`: For version tracking
   - `is_active`: TRUE for current rules
   - `extraction_timestamp`: Auto-generated

### Example Rule Entry

From the LLM query: *"What is the minimum age requirement?"*

Becomes database entry:
```json
{
  "rule_name": "Rule 1",
  "requirement": "What is the minimum age requirement?",
  "category": "Age Requirements",
  "source_document": "sample_life_insurance_policy.pdf",
  "document_hash": "2eca5cadb415866e...",
  "is_active": true
}
```

## Testing

### Before Fix

```bash
curl "http://localhost:9000/rule-agent/api/v1/extracted-rules?bank_id=chase&policy_type=insurance"
```

Response:
```json
{
  "rule_count": 0,
  "rules": []
}
```

### After Fix

After running the workflow again:

```bash
# Process the policy document
curl -X POST "http://localhost:9000/rule-agent/process_policy_from_s3" \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "s3://uw-data-extraction/sample-policies/sample_life_insurance_policy.pdf",
    "bank_id": "chase",
    "policy_type": "insurance"
  }'

# Then retrieve extracted rules
curl "http://localhost:9000/rule-agent/api/v1/extracted-rules?bank_id=chase&policy_type=insurance"
```

Expected Response:
```json
{
  "status": "success",
  "bank_id": "chase",
  "policy_type": "insurance",
  "rule_count": 77,
  "rules": [
    {
      "id": 1,
      "rule_name": "Rule 1",
      "requirement": "What is the maximum coverage amount?",
      "category": "Coverage Details",
      "source_document": "sample_life_insurance_policy.pdf",
      "document_hash": "2eca5cadb415866e...",
      "is_active": true,
      "created_at": "2025-11-10T20:45:30",
      "updated_at": "2025-11-10T20:45:30"
    },
    // ... 76 more rules
  ]
}
```

## Workflow Console Output

When you run the workflow, you'll now see:

```
============================================================
Step 2.5: Saving extracted rules to database...
============================================================
✓ Saved 77 extracted rules to database
```

## Database Migration Required

Make sure you've run the database migration first:

```sql
-- Run in pgAdmin Query Tool
\i d:/work/underwriter-agent/underwriter-rule-based-llms/db/migrations/001_create_extracted_rules_table.sql
```

Or open the file in pgAdmin and execute it.

## Related Files

- [UnderwritingWorkflow.py](rule-agent/UnderwritingWorkflow.py) - Workflow orchestration (modified)
- [DatabaseService.py](rule-agent/DatabaseService.py) - Database operations (already had save_extracted_rules method)
- [ChatService.py](rule-agent/ChatService.py) - API endpoint (already had /api/v1/extracted-rules endpoint)
- [swagger.yaml](rule-agent/swagger.yaml) - API documentation (already documented)
- [001_create_extracted_rules_table.sql](db/migrations/001_create_extracted_rules_table.sql) - Database schema

## Next Steps

1. **Run Database Migration** (if you haven't already):
   - Open pgAdmin
   - Execute `001_create_extracted_rules_table.sql`

2. **Reprocess Your Policy Document**:
   - The workflow needs to run again to populate the database
   - Previous runs didn't save rules because the integration wasn't there
   - New runs will automatically save rules

3. **Verify Rules Were Saved**:
   ```bash
   curl "http://localhost:9000/rule-agent/api/v1/extracted-rules?bank_id=chase&policy_type=insurance"
   ```

4. **Integrate with Frontend**:
   - Frontend can now display extracted rules
   - Rules are grouped by category
   - Shows source document and timestamps

## Benefits

1. **Complete Feature**: Frontend can now display policy rules to users
2. **Version Tracking**: Rules are tracked with document hash
3. **Soft Deletes**: Old rules are deactivated, not deleted (audit trail)
4. **Automatic**: No manual steps needed - rules saved during workflow
5. **Categorized**: Rules are automatically categorized for better UX

---

**Status**: ✅ **Fix Applied - Backend Rebuilding**

**Date**: 2025-11-10

**Impact**: High - Enables frontend to display extracted policy rules to customers
