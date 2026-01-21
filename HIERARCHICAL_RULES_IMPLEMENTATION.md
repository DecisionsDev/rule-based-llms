# Hierarchical Rules Implementation

## Overview

This document describes the implementation of hierarchical rules feature in the underwriting system. Hierarchical rules allow organizing rules in a tree structure with parent-child dependencies, enabling complex rule validation workflows.

## Features

- **Tree Structure**: Rules can have unlimited nesting depth with parent-child relationships
- **Dot Notation IDs**: Rules use dot notation (e.g., "11.1.1.1.1") for easy identification
- **Validation Tracking**: Each rule tracks expected vs. actual values, confidence scores, and pass/fail status
- **API Integration**: Rules can be included in policy API responses via query parameters
- **Database Persistence**: Rules are stored in PostgreSQL with efficient indexing

## Database Schema

### Table: `hierarchical_rules`

**Columns:**
- `id` (SERIAL PRIMARY KEY): Auto-incrementing database ID
- `bank_id` (VARCHAR(50)): Bank identifier (foreign key to `banks`)
- `policy_type_id` (VARCHAR(50)): Policy type identifier (foreign key to `policy_types`)
- `rule_id` (VARCHAR(50)): Dot-notation ID (e.g., "1", "1.1", "1.1.1")
- `name` (VARCHAR(255)): Rule name/title
- `description` (TEXT): Detailed rule description
- `expected` (VARCHAR(255)): Expected value or condition
- `actual` (VARCHAR(255)): Actual value or result
- `confidence` (FLOAT): Confidence score (0-1)
- `passed` (BOOLEAN): Whether the rule passed validation
- `parent_id` (INTEGER): Reference to parent rule (NULL for root rules)
- `level` (INTEGER): Depth in tree (0=root, 1=child, etc.)
- `order_index` (INTEGER): Order among siblings
- `document_hash` (VARCHAR(64)): Hash of source document
- `source_document` (VARCHAR(500)): Source document path/name
- `is_active` (BOOLEAN): Whether rule is currently active
- `created_at` (TIMESTAMP): Creation timestamp
- `updated_at` (TIMESTAMP): Last update timestamp

**Indexes:**
- `idx_hierarchical_rules_bank_policy` on (bank_id, policy_type_id)
- `idx_hierarchical_rules_parent` on (parent_id)
- `idx_hierarchical_rules_active` on (is_active)
- `idx_hierarchical_rules_hash` on (document_hash)
- `idx_hierarchical_rules_level` on (level)

**Triggers:**
- Auto-update `updated_at` timestamp on row updates

## Migration Files

**Created:**
- `db/migrations/003_create_hierarchical_rules_table.sql` - Creates the table
- `db/migrations/003_rollback_hierarchical_rules_table.sql` - Rollback script

**To apply migration:**
```bash
docker exec -i postgres psql -U underwriting_user -d underwriting_db < db/migrations/003_create_hierarchical_rules_table.sql
```

## Code Changes

### 1. DatabaseService.py

**Added Model (lines 220-261):**
- `HierarchicalRule` SQLAlchemy model with self-referential relationship

**Added Methods (lines 854-983):**

#### `save_hierarchical_rules(bank_id, policy_type_id, rules_tree, document_hash, source_document)`
Recursively saves a tree of rules to the database.

**Parameters:**
- `bank_id`: Bank identifier
- `policy_type_id`: Policy type identifier
- `rules_tree`: List of root-level rules with nested dependencies
- `document_hash`: Optional hash of source document
- `source_document`: Optional source document path

**Returns:** List of created rule IDs

**Example:**
```python
rules = [
    {
        "id": "1",
        "name": "Age Check",
        "description": "Verify minimum age",
        "expected": "Age >= 18",
        "actual": "Age = 25",
        "confidence": 0.95,
        "passed": True,
        "dependencies": [
            {
                "id": "1.1",
                "name": "Birth Date Verification",
                ...
            }
        ]
    }
]
db_service.save_hierarchical_rules("chase", "insurance", rules)
```

#### `get_hierarchical_rules(bank_id, policy_type_id, active_only=True)`
Retrieves hierarchical rules and reconstructs the tree structure.

**Parameters:**
- `bank_id`: Bank identifier
- `policy_type_id`: Policy type identifier
- `active_only`: Only return active rules (default: True)

**Returns:** List of root-level rules with nested dependencies

#### `delete_hierarchical_rules(bank_id, policy_type_id)`
Deletes all hierarchical rules for a bank and policy type.

**Returns:** Number of rules deleted

### 2. ChatService.py

**Updated Endpoints:**

#### GET `/api/v1/policies`
**New Query Parameter:**
- `include_hierarchical_rules` (boolean, default: false)

**New Response Fields:**
- `hierarchical_rules`: Array of hierarchical rules (if requested)
- `hierarchical_rules_count`: Number of top-level rules

**Example:**
```bash
curl "http://localhost:9000/rule-agent/api/v1/policies?bank_id=chase&policy_type=insurance&include_hierarchical_rules=true"
```

#### GET `/api/v1/banks/<bank_id>/policies`
**New Query Parameter:**
- `include_hierarchical_rules` (boolean, default: false)

**New Response Fields (per policy):**
- `hierarchical_rules`: Array of hierarchical rules (if details=true)
- `hierarchical_rules_count`: Number of top-level rules (if requested or details=true)

### 3. swagger.yaml

**Version:** Updated to 2.3.0

**New Schema:**
- `HierarchicalRule` (lines 1284-1332): Recursive schema for tree structure

**Updated Endpoints:**
- `/api/v1/policies`: Added `include_hierarchical_rules` parameter and response fields
- `/api/v1/banks/{bank_id}/policies`: Added `include_hierarchical_rules` parameter and response fields

**Documentation Updates:**
- Added "What's New in v2.3" section describing hierarchical rules feature

## Sample Data Structure

```json
{
  "id": "11",
  "name": "Underwriting Decision",
  "description": "Final underwriting decision based on all checks",
  "expected": "All requirements met",
  "actual": "Approved",
  "confidence": 0.95,
  "passed": true,
  "dependencies": [
    {
      "id": "11.1",
      "name": "Eligibility Check",
      "description": "Verify basic eligibility",
      "expected": "Meets criteria",
      "actual": "Passed",
      "confidence": 0.98,
      "passed": true,
      "dependencies": [
        {
          "id": "11.1.1",
          "name": "Age Verification",
          "description": "Check minimum age",
          "expected": "Age >= 18",
          "actual": "Age = 25",
          "confidence": 0.99,
          "passed": true,
          "dependencies": []
        }
      ]
    }
  ]
}
```

## API Usage Examples

### Save Hierarchical Rules

```python
from DatabaseService import get_database_service

db_service = get_database_service()

rules = [
    {
        "id": "1",
        "name": "Main Rule",
        "description": "Top-level rule",
        "expected": "Pass",
        "actual": "Pass",
        "confidence": 0.9,
        "passed": True,
        "dependencies": [
            {
                "id": "1.1",
                "name": "Sub Rule",
                "description": "Child rule",
                "expected": "Valid",
                "actual": "Valid",
                "confidence": 0.95,
                "passed": True,
                "dependencies": []
            }
        ]
    }
]

db_service.save_hierarchical_rules(
    bank_id="chase",
    policy_type_id="insurance",
    rules_tree=rules,
    document_hash="abc123",
    source_document="policy.pdf"
)
```

### Retrieve Hierarchical Rules

```python
rules = db_service.get_hierarchical_rules(
    bank_id="chase",
    policy_type_id="insurance"
)
```

### Query via API

```bash
# Get policy with hierarchical rules
curl "http://localhost:9000/rule-agent/api/v1/policies?bank_id=chase&policy_type=insurance&include_hierarchical_rules=true"

# Get all policies with hierarchical rule counts
curl "http://localhost:9000/rule-agent/api/v1/banks/chase/policies?include_hierarchical_rules=true"

# Get all policies with full hierarchical rules details
curl "http://localhost:9000/rule-agent/api/v1/banks/chase/policies?details=true"
```

## Testing

A test script has been created at [rule-agent/test_hierarchical_rules.py](rule-agent/test_hierarchical_rules.py).

**To run tests:**
```bash
cd rule-agent
python3 test_hierarchical_rules.py
```

**Test Coverage:**
1. Save hierarchical rules with nested dependencies
2. Retrieve and verify tree structure
3. Verify parent-child relationships
4. Delete hierarchical rules
5. Verify all data is correctly persisted and retrieved

## Benefits

1. **Better Organization**: Rules can be logically grouped in a hierarchy
2. **Dependency Tracking**: See which rules depend on others
3. **Validation Flow**: Track validation flow through the rule tree
4. **Unlimited Depth**: No limit on nesting levels
5. **API Flexibility**: Optionally include rules in API responses
6. **Performance**: Indexed queries for efficient retrieval

## Future Enhancements

Potential future improvements:
- Rule execution engine that respects dependencies
- Real-time rule validation status updates
- Rule versioning and history tracking
- Visual tree representation in frontend
- Rule templates and reusable rule sets
- Performance metrics per rule
- A/B testing different rule configurations
