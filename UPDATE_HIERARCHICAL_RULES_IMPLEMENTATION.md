# Update Hierarchical Rules Implementation - Complete

## Summary

Successfully implemented a new endpoint `/api/v1/policies/update-hierarchical-rules` that allows updating validation fields in hierarchical rules (expected, actual, confidence, passed, description, name) without regenerating the entire rule tree.

This complements the existing `/api/v1/policies/update-rules` endpoint (for DRL rules) by providing a dedicated way to update hierarchical rule validation data.

## Changes Made

### 1. Database Method Added (`rule-agent/DatabaseService.py`)

#### `update_hierarchical_rules(bank_id, policy_type_id, updates)` (Lines 1049-1177)

**Purpose:** Update fields in existing hierarchical rules

**Features:**
- ✅ **Dual identifier support** - Update by `rule_id` (dot notation like "1.1") OR `id` (database ID)
- ✅ **Batch updates** - Update multiple rules in a single transaction
- ✅ **Partial updates** - Only update fields you provide (others remain unchanged)
- ✅ **Error handling** - Returns detailed errors for failed updates while succeeding on others
- ✅ **Atomic operations** - All updates committed together

**Supported Fields:**
- `expected` - Expected value or condition
- `actual` - Actual value or result
- `confidence` - Confidence score (0.0-1.0)
- `passed` - Pass/fail status (boolean)
- `description` - Rule description
- `name` - Rule name

**Parameters:**
```python
updates = [
    {
        "rule_id": "1.1",  # OR "id": 42
        "expected": "Age >= 18",
        "actual": "Age = 25",
        "confidence": 0.95,
        "passed": True
    }
]
```

**Returns:**
```python
{
    "updated_count": 3,
    "updated_ids": [42, 43, 44],
    "errors": [...]  # If any updates failed
}
```

### 2. New API Endpoint (`rule-agent/ChatService.py`)

#### `/api/v1/policies/update-hierarchical-rules` (Lines 1014-1135)
**Method:** POST  
**Description:** Update hierarchical rules validation fields

**Request Body:**
```json
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "updates": [
    {
      "rule_id": "1.1",
      "expected": "Age >= 18",
      "actual": "Age = 25",
      "confidence": 0.95,
      "passed": true
    },
    {
      "rule_id": "1.2",
      "expected": "Credit Score >= 600",
      "actual": "Credit Score = 720",
      "confidence": 0.98,
      "passed": true
    }
  ]
}
```

**Response (Success):**
```json
{
  "status": "success",
  "bank_id": "chase",
  "policy_type": "insurance",
  "updated_count": 2,
  "updated_ids": [42, 43]
}
```

**Response (Partial Success - HTTP 207):**
```json
{
  "status": "partial",
  "bank_id": "chase",
  "policy_type": "insurance",
  "updated_count": 2,
  "updated_ids": [42, 43],
  "error_count": 1,
  "message": "Updated 2 rules, but 1 failed.",
  "errors": [
    {
      "error": "Rule not found",
      "identifier": "rule_id=1.5",
      "bank_id": "chase",
      "policy_type_id": "insurance"
    }
  ]
}
```

**HTTP Status Codes:**
- `200` - All updates successful
- `207` - Multi-Status (some succeeded, some failed)
- `400` - Bad request or all updates failed
- `500` - Server error

### 3. Swagger Documentation (`rule-agent/swagger.yaml`)

- **Version Updated:** 2.4.0 → 2.5.0
- **New Section:** Added comprehensive documentation for `/api/v1/policies/update-hierarchical-rules`
- **Includes:**
  - Detailed endpoint description and use cases
  - Request/response schemas with all fields documented
  - Multiple examples:
    - Update by rule_id (dot notation)
    - Update by database ID
    - Partial updates
  - Error response documentation (200, 207, 400, 500)
  - Batch update examples
  - Field constraints and validation rules

## Understanding the Two Types of Rules

### DRL Rules (Drools Rules)
- **Table:** `extracted_rules`
- **Purpose:** Technical rules that execute in Drools engine
- **Fields:** `rule_name`, `requirement`, `category`
- **Updated by:** `/api/v1/policies/update-rules`
- **Use:** Runtime decision-making

### Hierarchical Rules (Validation Rules) ⭐ NEW ENDPOINT
- **Table:** `hierarchical_rules`
- **Purpose:** Tree-structured validation and tracking
- **Fields:** `rule_id`, `name`, `description`, **`expected`**, **`actual`**, **`confidence`**, **`passed`**, `parent_id`
- **Updated by:** `/api/v1/policies/update-hierarchical-rules` ✅ NEW
- **Use:** Validation workflows, UI visualization, audit tracking

## Key Features

### 1. Flexible Identification
Update rules using either:
- **Dot notation** (`rule_id`): "1.1", "1.2.3", "5.1.2"
- **Database ID** (`id`): 42, 43, 44

```json
// By rule_id
{"rule_id": "1.1", "expected": "Age >= 18"}

// By database ID
{"id": 42, "expected": "Age >= 18"}
```

### 2. Batch Updates
Update multiple rules in a single request:
```json
{
  "updates": [
    {"rule_id": "1.1", "expected": "Age >= 18", "passed": true},
    {"rule_id": "1.2", "expected": "Score >= 600", "passed": true},
    {"rule_id": "2.1", "confidence": 0.95}
  ]
}
```

### 3. Partial Updates
Only update fields you provide - others remain unchanged:
```json
// Only update confidence
{"rule_id": "1.1", "confidence": 0.92}

// Only update pass/fail status
{"rule_id": "1.2", "passed": false}

// Update multiple fields
{"rule_id": "1.3", "expected": "New value", "confidence": 0.88}
```

### 4. Error Handling
Gracefully handles failures while succeeding on other updates:
- Returns HTTP 207 (Multi-Status) for partial success
- Provides detailed error information
- Commits successful updates even if some fail

### 5. Validation
- Validates bank_id and policy_type
- Checks that rules exist before updating
- Type-checks confidence scores (0.0-1.0)
- Ensures at least one field is being updated

## Use Cases

### Use Case 1: Set Expected Values After Rule Creation
```bash
POST /rule-agent/api/v1/policies/update-hierarchical-rules
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "updates": [
    {"rule_id": "1.1", "expected": "Age between 18-65"},
    {"rule_id": "1.2", "expected": "Credit score >= 600"},
    {"rule_id": "2.1", "expected": "Annual income >= $50,000"}
  ]
}
```

### Use Case 2: Record Evaluation Results
```bash
POST /rule-agent/api/v1/policies/update-hierarchical-rules
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "updates": [
    {
      "rule_id": "1.1",
      "actual": "Age = 35",
      "passed": true,
      "confidence": 1.0
    },
    {
      "rule_id": "1.2",
      "actual": "Credit score = 720",
      "passed": true,
      "confidence": 0.98
    }
  ]
}
```

### Use Case 3: Update Confidence Scores
```bash
POST /rule-agent/api/v1/policies/update-hierarchical-rules
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "updates": [
    {"rule_id": "1.1", "confidence": 0.95},
    {"rule_id": "1.2", "confidence": 0.88},
    {"rule_id": "2.1", "confidence": 0.92}
  ]
}
```

### Use Case 4: Fix Rule Descriptions
```bash
POST /rule-agent/api/v1/policies/update-hierarchical-rules
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "updates": [
    {
      "rule_id": "1.1",
      "name": "Minimum Age Check",
      "description": "Verify applicant meets the minimum age requirement of 18 years"
    }
  ]
}
```

## Workflow Integration

### Complete Rule Management Workflow

```
1. Initial Policy Processing
   POST /process_policy_from_s3
   ↓
   Creates hierarchical rules (expected/actual/confidence empty)

2. Set Expected Values
   POST /api/v1/policies/update-hierarchical-rules
   ↓
   Sets expected values for validation

3. Evaluate Application
   POST /api/v1/evaluate-policy
   ↓
   Gets actual values from evaluation

4. Record Results
   POST /api/v1/policies/update-hierarchical-rules
   ↓
   Updates actual, passed, confidence

5. Query Rules
   GET /api/v1/policies?include_hierarchical_rules=true
   ↓
   View updated rules with validation data
```

## Comparison with DRL Rules Endpoint

| Feature | `/update-rules` (DRL) | `/update-hierarchical-rules` (NEW) |
|---------|----------------------|-----------------------------------|
| **Purpose** | Update Drools execution rules | Update validation tracking rules |
| **Input** | DRL content (code) | Field updates (data) |
| **Fields** | rule_name, requirement, category | expected, actual, confidence, passed |
| **Redeployment** | Yes (to Drools) | No (database only) |
| **Version Increment** | Yes | No |
| **Use Case** | Change business logic | Track validation results |
| **Batch Support** | No (single rule set) | Yes (multiple rules) |
| **Partial Updates** | No (full DRL) | Yes (field-level) |

## Testing Recommendations

### 1. Happy Path Tests
```bash
# Test 1: Update by rule_id
curl -X POST http://localhost:9000/rule-agent/api/v1/policies/update-hierarchical-rules \
  -H "Content-Type: application/json" \
  -d '{
    "bank_id": "chase",
    "policy_type": "insurance",
    "updates": [
      {"rule_id": "1.1", "expected": "Age >= 18", "confidence": 0.95}
    ]
  }'

# Test 2: Batch update
curl -X POST http://localhost:9000/rule-agent/api/v1/policies/update-hierarchical-rules \
  -H "Content-Type: application/json" \
  -d '{
    "bank_id": "chase",
    "policy_type": "insurance",
    "updates": [
      {"rule_id": "1.1", "passed": true, "actual": "Age = 25"},
      {"rule_id": "1.2", "passed": true, "actual": "Score = 720"},
      {"rule_id": "2.1", "passed": false, "actual": "Income = $45k"}
    ]
  }'
```

### 2. Error Case Tests
```bash
# Test 1: Non-existent rule
curl -X POST ... \
  -d '{
    "updates": [{"rule_id": "99.99", "expected": "Test"}]
  }'
# Expected: HTTP 207 with error details

# Test 2: Missing identifier
curl -X POST ... \
  -d '{
    "updates": [{"expected": "Test"}]
  }'
# Expected: HTTP 400 with "Missing identifier" error

# Test 3: Empty updates array
curl -X POST ... \
  -d '{
    "updates": []
  }'
# Expected: HTTP 400 with "cannot be empty" error
```

### 3. Validation Tests
```bash
# Verify updates in database
curl http://localhost:9000/rule-agent/api/v1/policies?bank_id=chase&policy_type=insurance&include_hierarchical_rules=true

# Check specific rule
# Should see updated expected, actual, confidence, passed fields
```

## Benefits

✅ **Granular Updates** - Update individual fields without touching others  
✅ **Batch Efficiency** - Update multiple rules in one request  
✅ **Flexible Identification** - Use dot notation or database ID  
✅ **Error Resilience** - Partial success with detailed error reporting  
✅ **Validation Tracking** - Track expected vs actual, pass/fail, confidence  
✅ **No Redeployment** - Database-only updates (fast)  
✅ **Audit Trail** - `updated_at` timestamp automatically maintained  
✅ **Multi-Tenant Safe** - Bank+policy isolation preserved  

## Files Modified

1. `rule-agent/DatabaseService.py` - Added `update_hierarchical_rules()` method (129 lines)
2. `rule-agent/ChatService.py` - Added new endpoint (122 lines)
3. `rule-agent/swagger.yaml` - Updated documentation and version

## No Breaking Changes

✅ All existing endpoints work unchanged  
✅ No route conflicts  
✅ No schema modifications  
✅ Compatible with existing hierarchical rules  
✅ No linter errors  

## Summary

This implementation provides a clean, dedicated way to update hierarchical rule validation data. It complements the existing DRL rules update endpoint and enables complete rule lifecycle management:

1. **Create** rules via `/process_policy_from_s3`
2. **Update DRL logic** via `/api/v1/policies/update-rules`
3. **Update validation data** via `/api/v1/policies/update-hierarchical-rules` ⭐ NEW
4. **Query rules** via `/api/v1/policies?include_hierarchical_rules=true`
5. **Evaluate** via `/api/v1/evaluate-policy`

The system now supports the complete validation workflow with granular control over each rule's expected values, actual results, confidence scores, and pass/fail status! 🎉

