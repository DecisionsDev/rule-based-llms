# Update Hierarchical Rules with DRL Support - Complete

## Enhancement Summary

The `/api/v1/policies/update-hierarchical-rules` endpoint has been enhanced to support **optional DRL regeneration and redeployment**. This makes hierarchical rules the **source of truth** for rule logic, not just display metadata.

## What Changed

### Before (v2.5)
- Update hierarchical rules API only updated metadata in database
- Changes to `expected` values didn't affect actual rule logic
- To change rule logic, you had to use `/update-rules` API with manual DRL editing

### After (v2.6)
- Update hierarchical rules API can **optionally** regenerate and redeploy DRL
- Changes to `expected` values can automatically update the actual business logic
- Hierarchical rules become the source of truth - edit them and the DRL follows
- Backward compatible - old behavior still works without `update_drl` parameter

## New Components

### 1. HierarchicalToDRLConverter.py
A new service that converts hierarchical rules back to executable DRL format.

**Capabilities:**
- Parses `expected` conditions to DRL syntax
- Supports comparison operators: `>=`, `<=`, `>`, `<`, `==`, `=`
- Supports range checks: "between X and Y"
- Supports boolean fields: smoking, smoker
- Supports string comparisons
- Maps human-readable field names to DRL field names
- Generates complete DRL with type declarations and initialization

**Example Conversions:**
```
"Age >= 18" → "age >= 18"
"Credit score = 600" → "creditScore == 600"
"Age between 18 and 65" → "age >= 18, age <= 65"
"Income >= $50,000" → "annualIncome >= 50000"
```

### 2. Enhanced API Endpoint
The `update_hierarchical_rules()` function now:
1. Updates hierarchical rules in database (as before)
2. **Optionally** (if `update_drl: true`):
   - Fetches all hierarchical rules from database
   - Converts them to DRL using `HierarchicalToDRLConverter`
   - Redeploys to Drools KIE Server
   - Increments container version
   - Uploads new artifacts to S3
   - Logs deployment history

### 3. DroolsHierarchicalMapper.py - Bug Fix
Fixed the mapper to correctly handle equality checks:
- Before: `expected: "Credit score = 600"` was treated as `>= 600`
- After: Correctly treats `=` as exact equality check

## How to Use

### Option 1: Update Metadata Only (Default)
```json
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "updates": [
    {
      "rule_id": "1.2",
      "expected": "Credit Score >= 600",
      "description": "Updated description"
    }
  ]
}
```
**Result:** Only database metadata updated. DRL logic unchanged.

### Option 2: Update Metadata AND DRL Logic (NEW)
```json
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "update_drl": true,
  "updates": [
    {
      "rule_id": "1.2",
      "name": "Credit Score Check",
      "expected": "Credit Score >= 650",
      "description": "Increased minimum credit score requirement"
    }
  ]
}
```
**Result:** 
1. Database updated with new expected value
2. DRL regenerated from all hierarchical rules
3. Deployed to Drools (version incremented)
4. S3 artifacts uploaded
5. Deployment history logged

**Response:**
```json
{
  "status": "success",
  "bank_id": "chase",
  "policy_type": "insurance",
  "updated_count": 1,
  "updated_ids": [42],
  "new_version": 2,
  "drl_update": {
    "status": "success",
    "container_id": "chase-insurance-underwriting-rules",
    "release_id": {
      "group-id": "com.underwriting",
      "artifact-id": "underwriting-rules",
      "version": "20251117.143022"
    },
    "s3_upload": {
      "jar": {
        "status": "success",
        "s3_url": "s3://..."
      },
      "drl": {
        "status": "success",
        "s3_url": "s3://..."
      }
    }
  }
}
```

## Use Cases

### 1. Quick Rule Adjustments
**Scenario:** Business wants to increase credit score requirement from 600 to 650

**Old Way:**
1. Edit DRL file manually
2. Call `/api/v1/policies/update-rules` with entire DRL
3. Separately update hierarchical rules for consistency

**New Way:**
```json
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "update_drl": true,
  "updates": [
    {
      "rule_id": "1.2",
      "expected": "Credit Score >= 650"
    }
  ]
}
```
✅ One call updates both metadata and logic!

### 2. Frontend-Driven Rule Management
**Scenario:** Build a UI where business users can adjust rule thresholds

```javascript
// User adjusts slider for credit score
const updateRule = async (ruleId, newThreshold) => {
  await fetch('/api/v1/policies/update-hierarchical-rules', {
    method: 'POST',
    body: JSON.stringify({
      bank_id: 'chase',
      policy_type: 'insurance',
      update_drl: true,  // Auto-deploy changes
      updates: [{
        rule_id: ruleId,
        expected: `Credit Score >= ${newThreshold}`
      }]
    })
  });
};
```

### 3. A/B Testing Rules
**Scenario:** Test different age requirements

```json
// Version 1: Current
{
  "update_drl": true,
  "updates": [{"rule_id": "1.1", "expected": "Age >= 18"}]
}

// Version 2: More restrictive
{
  "update_drl": true,
  "updates": [{"rule_id": "1.1", "expected": "Age >= 21"}]
}
```

Each update creates a new version, allowing rollback if needed.

## Benefits

### ✅ Single Source of Truth
- Hierarchical rules in database drive both display and logic
- No need to manually sync DRL and hierarchical rules
- Frontend can directly manage rule logic

### ✅ Simpler Workflow
- One API call instead of two separate endpoints
- No manual DRL editing required for simple threshold changes
- Automatic version management

### ✅ Better for Non-Technical Users
- Business users can adjust rules without understanding DRL syntax
- Changes are expressed in human-readable format
- Frontend can provide intuitive UI (sliders, inputs, etc.)

### ✅ Audit Trail
- Every change increments version
- Deployment history tracks what changed and when
- Easy rollback to previous versions

### ✅ Backward Compatible
- Default behavior unchanged (`update_drl: false`)
- Existing code continues to work
- Opt-in to new functionality

## Implementation Details

### Field Mapping
The converter maps human-readable field names to DRL field names:

```python
field_mappings = {
    'age': 'age',
    'credit score': 'creditScore',
    'income': 'annualIncome',
    'health': 'health',
    'smoking': 'smoking',
    'coverage': 'coverageAmount',
    'debt to income': 'debtToIncomeRatio',
}
```

### Operator Support
- `>=` - Greater than or equal (minimum threshold)
- `<=` - Less than or equal (maximum limit)
- `>` - Greater than
- `<` - Less than
- `=` or `==` - Exact equality
- `between X and Y` - Range check

### Rejection Rule Detection
The converter automatically identifies rejection rules based on:
- Keywords: "reject", "minimum", "maximum", "required", "must be", etc.
- Comparison operators in expected conditions
- Generates appropriate rejection messages

### Generated DRL Structure
```drl
package com.underwriting.rules;

// Type declarations
declare Applicant ... end
declare Policy ... end
declare Decision ... end

// Initialization
rule "Initialize Decision" ... end

// Rules from hierarchical tree
rule "Credit Score Check"
    salience 8000
    when
        $applicant : Applicant( creditScore >= 650 )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Credit Score Check: Minimum requirement not met");
        update($decision);
end
```

## Limitations

### 1. Simple Conditions Only
The converter supports common patterns but not complex logic:

**Supported:**
- `Age >= 18`
- `Credit Score between 600 and 750`
- `Income >= $50,000`

**Not Supported (requires manual DRL):**
- Multi-field conditions: `(Age >= 18 AND Income > 50000) OR (Age >= 25 AND Income > 30000)`
- Complex calculations: `Coverage Amount <= Income * 12`
- Conditional logic based on other rules

For complex scenarios, use `/api/v1/policies/update-rules` with manual DRL.

### 2. All Hierarchical Rules Used
When `update_drl: true`, ALL hierarchical rules are converted to DRL, not just the ones being updated. This ensures consistency but means you can't have "display-only" rules.

### 3. Container Must Exist
DRL update requires an active container. If no container exists, the update fails.

## Swagger Documentation Updated

- API version: `2.5.0` → `2.6.0`
- New parameter: `update_drl` documented
- New response fields: `new_version`, `drl_update`
- New example: "Update expected values and redeploy DRL"
- Enhanced descriptions explaining the new functionality

## Testing Recommendations

### Test Case 1: Metadata-Only Update
```bash
curl -X POST http://localhost:9000/rule-agent/api/v1/policies/update-hierarchical-rules \
  -H "Content-Type: application/json" \
  -d '{
    "bank_id": "chase",
    "policy_type": "insurance",
    "update_drl": false,
    "updates": [{
      "rule_id": "1.2",
      "confidence": 0.95
    }]
  }'
```
**Expected:** Only database updated, DRL unchanged

### Test Case 2: Update with DRL Regeneration
```bash
curl -X POST http://localhost:9000/rule-agent/api/v1/policies/update-hierarchical-rules \
  -H "Content-Type: application/json" \
  -d '{
    "bank_id": "chase",
    "policy_type": "insurance",
    "update_drl": true,
    "updates": [{
      "rule_id": "1.2",
      "expected": "Credit Score >= 650"
    }]
  }'
```
**Expected:** 
- Database updated
- New DRL generated and deployed
- Container version incremented
- S3 artifacts uploaded

### Test Case 3: Verify Actual Evaluation
```bash
# Update rule
curl -X POST .../update-hierarchical-rules -d '{"update_drl": true, "updates": [{"rule_id": "1.2", "expected": "Credit Score >= 650"}]}'

# Evaluate with credit score 640 (should fail)
curl -X POST .../evaluate-policy -d '{"bank_id": "chase", "policy_type": "insurance", "applicant": {"creditScore": 640}}'

# Evaluate with credit score 660 (should pass)
curl -X POST .../evaluate-policy -d '{"bank_id": "chase", "policy_type": "insurance", "applicant": {"creditScore": 660}}'
```

## Files Changed

1. **New File:** `rule-agent/HierarchicalToDRLConverter.py` - Converter service
2. **Modified:** `rule-agent/ChatService.py` - Enhanced endpoint with DRL support
3. **Modified:** `rule-agent/DroolsHierarchicalMapper.py` - Fixed equality check bug
4. **Modified:** `rule-agent/swagger.yaml` - Updated documentation to v2.6.0
5. **New File:** `UPDATE_HIERARCHICAL_RULES_WITH_DRL_SUPPORT.md` - This document

## Summary

The `/api/v1/policies/update-hierarchical-rules` endpoint now supports **bidirectional synchronization**:

**Before:** Hierarchical Rules ← Drools (one-way for display)
**After:** Hierarchical Rules ↔ Drools (two-way, rules can drive logic)

This makes the system more intuitive for business users and enables frontend-driven rule management while maintaining backward compatibility.

