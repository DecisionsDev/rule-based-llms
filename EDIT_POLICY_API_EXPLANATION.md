# Edit Policy API - Complete Picture

## Overview

There are **TWO** main endpoints for editing/updating policies after initial deployment:

1. **`/api/v1/policies/update-rules`** - Direct DRL rule updates
2. **`/api/v1/policies/update-hierarchical-rules`** - Hierarchical rule updates (with optional DRL regeneration)

---

## API #1: `/api/v1/policies/update-rules`

### Purpose
Update deployed rules by providing **new DRL content directly**. This is a **quick fix** endpoint for developers who want to update rules without reprocessing the entire policy document.

### What It Does

```
┌─────────────────────────────────────────────────────────────┐
│  POST /api/v1/policies/update-rules                        │
│  {                                                          │
│    "bank_id": "chase",                                      │
│    "policy_type": "insurance",                             │
│    "drl_content": "package com.underwriting; rule ..."      │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │ Step 1: Parse DRL Rules           │
        │ - Extract rule names, conditions   │
        │ - Convert to user-friendly text     │
        │ - Categorize rules                 │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │ Step 2: Update Database            │
        │ - Deactivate old rules (is_active=false)│
        │ - Save new rules to extracted_rules table│
        │ - Preserve document_hash, source_document│
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │ Step 3: Build & Deploy KJar        │
        │ - Create Maven project structure   │
        │ - Generate kmodule.xml            │
        │ - Compile with Maven               │
        │ - Create JAR file                  │
        │ - Deploy to Drools KIE Server      │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │ Step 4: Update Container Version   │
        │ - Increment version (1 → 2 → 3...) │
        │ - Update database record           │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │ Step 5: Upload Artifacts to S3    │
        │ - Upload new JAR file             │
        │ - Upload new DRL file             │
        │ - Generate pre-signed URLs        │
        │ - Update container S3 URLs        │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │ Step 6: Log Deployment History     │
        │ - Record action="updated"         │
        │ - Store version, timestamp        │
        │ - Save changes_description        │
        └───────────────────────────────────┘
```

### Key Features
- ✅ **Direct DRL Input**: You provide the complete DRL content
- ✅ **No Document Reprocessing**: Skips PDF extraction, LLM analysis, Textract
- ✅ **Version Management**: Automatically increments container version
- ✅ **Database Sync**: Updates `extracted_rules` table with new rules
- ✅ **Full Redeployment**: Builds new KJar and deploys to Drools
- ✅ **S3 Artifact Storage**: Uploads new JAR/DRL to S3
- ✅ **Audit Trail**: Logs deployment history

### Use Cases
- Quick rule fixes (typos, logic errors)
- Adding new rules manually
- Updating rule thresholds
- Fixing DRL syntax errors

---

## API #2: `/api/v1/policies/update-hierarchical-rules`

### Purpose
Update **hierarchical rules** (the tree-structured rules in the database) and optionally regenerate DRL from them. This makes hierarchical rules the **source of truth**.

### What It Does

```
┌─────────────────────────────────────────────────────────────┐
│  POST /api/v1/policies/update-hierarchical-rules           │
│  {                                                          │
│    "bank_id": "chase",                                      │
│    "policy_type": "insurance",                             │
│    "update_drl": true,  // Optional: regenerate DRL        │
│    "updates": [                                             │
│      {                                                      │
│        "rule_id": "1.1",  // or "id": 42                   │
│        "expected": "Age >= 18",                            │
│        "actual": "Age = 25",                               │
│        "confidence": 0.95,                                  │
│        "passed": true                                       │
│      }                                                      │
│    ]                                                        │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │ Step 1: Update Hierarchical Rules │
        │ - Find rules by rule_id or id     │
        │ - Update fields: expected, actual,│
        │   confidence, passed, description │
        │ - Batch updates supported         │
        │ - Partial updates (only provided  │
        │   fields are updated)             │
        └───────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ update_drl?   │
                    └───────┬───────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
    ┌───────────────┐              ┌───────────────┐
    │ update_drl=false│              │ update_drl=true│
    │ (Metadata Only) │              │ (Full Update) │
    └───────────────┘              └───────┬───────┘
                                            │
                            ┌───────────────┴───────────────┐
                            │                             │
                            ▼                             ▼
            ┌───────────────────────────┐   ┌───────────────────────────┐
            │ Step 2a: Get Updated      │   │ Step 2b: Convert to DRL    │
            │ Hierarchical Rules        │   │ - Parse expected values    │
            │ - Load from database      │   │ - Map to DRL conditions   │
            │ - Includes all updates    │   │ - Generate rule structure  │
            └───────────────────────────┘   │ - Create complete DRL     │
                                            └───────────────────────────┘
                                                            │
                                                            ▼
                                            ┌───────────────────────────┐
                                            │ Step 3: Redeploy DRL      │
                                            │ - Build KJar              │
                                            │ - Deploy to Drools        │
                                            │ - Increment version       │
                                            │ - Upload to S3            │
                                            │ - Log deployment history  │
                                            └───────────────────────────┘
```

### Key Features

#### Mode 1: Metadata Update Only (`update_drl: false`)
- ✅ Update validation fields: `expected`, `actual`, `confidence`, `passed`
- ✅ Update descriptions and names
- ✅ Batch updates (multiple rules at once)
- ✅ Partial updates (only update fields you provide)
- ✅ Update by `rule_id` (dot notation like "1.1") or database `id`
- ❌ **Does NOT** regenerate DRL or redeploy

**Use Cases:**
- Recording test results (actual values, pass/fail)
- Updating confidence scores after validation
- Fixing rule descriptions
- Setting expected values after initial creation

#### Mode 2: Full Update with DRL Regeneration (`update_drl: true`)
- ✅ Everything from Mode 1, PLUS:
- ✅ Converts updated hierarchical rules back to DRL
- ✅ Regenerates complete DRL file from hierarchical rules
- ✅ Redeploys to Drools KIE Server
- ✅ Increments container version
- ✅ Uploads new artifacts to S3
- ✅ Logs deployment history

**Use Cases:**
- Changing rule logic by updating `expected` values
- Making hierarchical rules the source of truth
- Updating rule thresholds in a user-friendly way
- Fixing rule logic without writing DRL manually

### How DRL Regeneration Works

The `HierarchicalToDRLConverter` converts hierarchical rules back to DRL:

1. **Parse Expected Values**: Converts `expected: "Age >= 18"` → DRL condition `age >= 18`
2. **Field Mapping**: Maps human-readable names to DRL field names
   - "credit score" → `creditScore`
   - "annual income" → `annualIncome`
   - "debt to income" → `debtToIncomeRatio`
3. **Rule Type Detection**: Determines if rule is rejection or approval
4. **DRL Generation**: Creates complete DRL with:
   - Package declaration
   - Type declarations (Applicant, Policy, Decision)
   - Initialization rule
   - All rules from hierarchical tree
   - Proper salience values

---

## Comparison Table

| Feature | `/update-rules` | `/update-hierarchical-rules` |
|---------|----------------|------------------------------|
| **Input Format** | DRL (Drools code) | Hierarchical rules (JSON) |
| **Update Method** | Direct DRL replacement | Field-by-field updates |
| **Source of Truth** | DRL file | Hierarchical rules (when `update_drl=true`) |
| **Use Case** | Quick fixes, manual edits | Validation tracking, rule refinement |
| **DRL Regeneration** | No (you provide DRL) | Yes (optional, converts hierarchical → DRL) |
| **Batch Updates** | No (single DRL file) | Yes (multiple rules) |
| **Partial Updates** | No (full DRL required) | Yes (only update specific fields) |
| **Database Updates** | `extracted_rules` table | `hierarchical_rules` table |
| **Redeployment** | Always | Only if `update_drl=true` |
| **Version Increment** | Always | Only if `update_drl=true` |

---

## Complete Workflow Example

### Scenario: Fix a rule threshold

**Option A: Using `/update-rules` (Direct DRL)**
```json
POST /api/v1/policies/update-rules
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "drl_content": "package com.underwriting;\n\nrule \"Minimum Age\"\nwhen\n    $applicant : Applicant(age < 21)\n    $decision : Decision()\nthen\n    $decision.setApproved(false);\n    $decision.getReasons().add(\"Minimum age is 21\");\nend"
}
```

**Option B: Using `/update-hierarchical-rules` (User-Friendly)**
```json
POST /api/v1/policies/update-hierarchical-rules
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "update_drl": true,
  "updates": [
    {
      "rule_id": "1.1",
      "expected": "Age >= 21",
      "description": "Updated minimum age requirement to 21"
    }
  ]
}
```

Both approaches:
1. ✅ Update the database
2. ✅ Redeploy to Drools
3. ✅ Increment version
4. ✅ Upload to S3
5. ✅ Log deployment history

---

## Database Tables Affected

### `/update-rules` affects:
- ✅ `extracted_rules` - User-friendly rule descriptions
- ✅ `rule_containers` - Version, S3 URLs
- ✅ `container_deployment_history` - Audit trail

### `/update-hierarchical-rules` affects:
- ✅ `hierarchical_rules` - Rule tree structure
- ✅ `extracted_rules` - Only if `update_drl=true` (via DRL regeneration)
- ✅ `rule_containers` - Only if `update_drl=true` (version, S3 URLs)
- ✅ `container_deployment_history` - Only if `update_drl=true`

---

## Key Design Decisions

1. **Two Separate Endpoints**: Different use cases require different approaches
2. **Optional DRL Regeneration**: Hierarchical rules can be metadata-only OR source of truth
3. **Version Management**: Automatic versioning ensures audit trail
4. **S3 Artifact Storage**: All versions stored for rollback capability
5. **Database Sync**: Both `extracted_rules` and `hierarchical_rules` stay in sync
6. **Batch Updates**: Hierarchical rules support updating multiple rules at once
7. **Partial Updates**: Only update fields you provide (flexible)

---

## Summary

- **`/update-rules`**: For developers who want to edit DRL directly
- **`/update-hierarchical-rules`**: For business users who want to update rules via user-friendly fields, with optional DRL regeneration

Both endpoints maintain consistency across:
- Database (rules, containers, history)
- Drools KIE Server (deployed rules)
- S3 (artifact storage)
- Version tracking (audit trail)

