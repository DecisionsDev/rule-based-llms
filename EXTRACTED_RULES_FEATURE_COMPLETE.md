# Extracted Rules Feature - Implementation Complete

## Overview

Successfully implemented a complete feature to save extracted policy rules to the database and expose them via a REST API endpoint for frontend consumption.

## Changes Made

### 1. Database Schema - ExtractedRule Model

**File**: [rule-agent/DatabaseService.py](rule-agent/DatabaseService.py)

Added new `ExtractedRule` table model (lines 187-217) with the following structure:

```python
class ExtractedRule(Base):
    __tablename__ = 'extracted_rules'

    # Primary Key
    id = Column(Integer, primary_key=True)

    # Foreign Keys
    bank_id = Column(String(50), ForeignKey('banks.bank_id', ondelete='CASCADE'))
    policy_type_id = Column(String(50), ForeignKey('policy_types.policy_type_id', ondelete='CASCADE'))

    # Rule Details
    rule_name = Column(String(255), nullable=False)
    requirement = Column(Text, nullable=False)
    category = Column(String(100))
    source_document = Column(String(500))

    # Metadata
    document_hash = Column(String(64))
    extraction_timestamp = Column(DateTime)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Indexes created:**
- `idx_extracted_rules_bank_policy` - Composite index on (bank_id, policy_type_id)
- `idx_extracted_rules_active` - Index on is_active
- `idx_extracted_rules_created_at` - Index on created_at

### 2. Database Service Methods

Added three new methods to `DatabaseService` class:

#### save_extracted_rules() (lines 563-609)
```python
def save_extracted_rules(self, bank_id: str, policy_type_id: str, rules: List[Dict[str, Any]],
                        source_document: str = None, document_hash: str = None) -> List[int]
```
- Saves a list of extracted rules to the database
- Deactivates old rules (soft delete) before inserting new ones
- Returns list of created rule IDs
- Supports bulk insert operation

#### get_extracted_rules() (lines 611-650)
```python
def get_extracted_rules(self, bank_id: str, policy_type_id: str, active_only: bool = True) -> List[Dict[str, Any]]
```
- Retrieves extracted rules for a bank and policy type
- Optional filtering for active rules only
- Returns rules ordered by category and rule name
- Converts ORM objects to dictionaries within session context

#### delete_extracted_rules() (lines 652-674)
```python
def delete_extracted_rules(self, bank_id: str, policy_type_id: str) -> bool
```
- Soft deletes rules by setting is_active to False
- Used when rules need to be deprecated

### 3. REST API Endpoint

**File**: [rule-agent/ChatService.py](rule-agent/ChatService.py#L807-L832)

Added new endpoint: `GET /api/v1/extracted-rules`

**Query Parameters:**
- `bank_id` (required): The bank identifier
- `policy_type` (required): The policy type identifier

**Response Format:**
```json
{
  "status": "success",
  "bank_id": "chase",
  "policy_type": "insurance",
  "rule_count": 29,
  "rules": [
    {
      "id": 1,
      "rule_name": "Minimum Age Requirement",
      "requirement": "Applicant must be at least 18 years old...",
      "category": "Age Requirements",
      "source_document": "sample_life_insurance_policy.txt",
      "document_hash": "sample_hash_001",
      "extraction_timestamp": "2025-11-10T10:30:00",
      "is_active": true,
      "created_at": "2025-11-10T10:30:00",
      "updated_at": "2025-11-10T10:30:00"
    }
    // ... more rules
  ]
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Both bank_id and policy_type query parameters are required"
}
```

### 4. SQL Migration Scripts

Created complete migration scripts in `db/migrations/`:

#### 001_create_extracted_rules_table.sql
- Creates `extracted_rules` table with all columns and constraints
- Creates foreign keys to `banks` and `policy_types` tables
- Creates indexes for performance
- Creates auto-update trigger for `updated_at` column
- Adds comprehensive comments to table and columns

#### 001_rollback_extracted_rules_table.sql
- Complete rollback script to undo the migration
- Drops table, triggers, functions, and indexes

#### 001_sample_extracted_rules_data.sql
- Inserts 29 sample rules for Chase life insurance policy
- Covers all rule categories:
  - Age Requirements (3 rules)
  - Credit Score Requirements (3 rules)
  - Income Requirements (3 rules)
  - Health Requirements (4 rules)
  - Automatic Rejection Criteria (8 rules)
  - Coverage Tiers (8 rules)

#### README.md
- Complete documentation for migration scripts
- Step-by-step instructions for running in pgAdmin
- Troubleshooting guide
- API usage examples

## How to Use

### Step 1: Run Database Migration

1. Open pgAdmin and connect to your PostgreSQL database
2. Open Query Tool (Tools > Query Tool)
3. Open file: `db/migrations/001_create_extracted_rules_table.sql`
4. Click Execute (F5)
5. Verify success message: "Migration completed successfully!"

### Step 2: Insert Sample Data (Optional)

1. In Query Tool, open file: `db/migrations/001_sample_extracted_rules_data.sql`
2. Click Execute (F5)
3. Verify sample data count

### Step 3: Test the API Endpoint

```bash
# Get extracted rules for Chase life insurance
curl "http://localhost:9000/rule-agent/api/v1/extracted-rules?bank_id=chase&policy_type=insurance"
```

**Expected Response:**
```json
{
  "status": "success",
  "bank_id": "chase",
  "policy_type": "insurance",
  "rule_count": 29,
  "rules": [ /* array of rule objects */ ]
}
```

## Frontend Integration

The frontend can call this endpoint to display policy rules:

```javascript
// Example fetch call
const response = await fetch(
  'http://localhost:9000/rule-agent/api/v1/extracted-rules?' +
  'bank_id=chase&policy_type=insurance'
);
const data = await response.json();

// Group rules by category
const rulesByCategory = data.rules.reduce((acc, rule) => {
  if (!acc[rule.category]) {
    acc[rule.category] = [];
  }
  acc[rule.category].push(rule);
  return acc;
}, {});
```

## Verification

### Database Connection Test
```bash
curl http://localhost:9000/rule-agent/api/v1/health
```
Expected: `{"database":"connected","drools":"connected","status":"healthy"}`

### Endpoint Test (Empty Database)
```bash
curl "http://localhost:9000/rule-agent/api/v1/extracted-rules?bank_id=chase&policy_type=insurance"
```
Expected: `{"status":"success","bank_id":"chase","policy_type":"insurance","rule_count":0,"rules":[]}`

### Endpoint Test (With Sample Data)
After running sample data migration:
```bash
curl "http://localhost:9000/rule-agent/api/v1/extracted-rules?bank_id=chase&policy_type=insurance"
```
Expected: Returns 29 rules grouped into 6 categories

## Architecture Notes

### Soft Delete Pattern
- Rules are never hard-deleted from the database
- When new rules are saved, old rules are marked as `is_active=false`
- This preserves historical data and allows for auditing
- Use `active_only=True` parameter to retrieve only active rules

### Session Management
- All database operations use context managers (`with self.get_session()`)
- ORM objects are converted to dictionaries within session context
- Prevents SQLAlchemy lazy-loading errors after session closes

### Performance Optimization
- Composite index on (bank_id, policy_type_id) for fast lookups
- Index on is_active for filtering active rules
- Index on created_at for sorting by creation time

### Security
- Uses foreign key constraints with CASCADE delete
- Validates required parameters before database queries
- Returns proper HTTP status codes (200, 400, 500)

## Related Documentation

- [DATABASE_HEALTH_CHECK_FIX.md](DATABASE_HEALTH_CHECK_FIX.md) - SQLAlchemy 2.x health check fix
- [SESSION_MANAGEMENT_FIX.md](SESSION_MANAGEMENT_FIX.md) - Session management patterns
- [POSTGRESQL_INTEGRATION_GUIDE.md](POSTGRESQL_INTEGRATION_GUIDE.md) - PostgreSQL integration guide
- [sample_life_insurance_policy.txt](sample_life_insurance_policy.txt) - Updated policy document with comprehensive rules

## Sample Rule Categories

Based on the updated [sample_life_insurance_policy.txt](sample_life_insurance_policy.txt):

1. **Age Requirements**
   - Minimum age: 18 years (mandatory rejection if under)
   - Maximum age: 65 years (mandatory rejection if over)
   - Preferred age range: 25-55 years (best rates)

2. **Credit Score Requirements**
   - Minimum: 600 (mandatory rejection if under)
   - Preferred: 700+ (standard rates)
   - Excellent: 750+ (discounted rates)

3. **Income Requirements**
   - Minimum annual income: $25,000
   - Coverage cannot exceed 10x annual income
   - Income verification required for coverage over $500,000

4. **Health Requirements**
   - Health status must be declared: excellent, good, fair, or poor
   - Poor health: AUTOMATIC REJECTION
   - Fair health: Manual review required
   - Medical exam required for coverage over $500,000

5. **Automatic Rejection Criteria**
   - Age under 18 or over 65
   - Credit score below 600
   - Poor health status
   - Annual income below $25,000
   - Coverage exceeds 10x income
   - Smoker + age 60+ + coverage over $300,000
   - DUI conviction within 5 years
   - Hazardous occupation without riders

6. **Coverage Tiers**
   - Tier 1: $50,000 - $100,000 (Standard)
   - Tier 2: $100,001 - $300,000 (Enhanced)
   - Tier 3: $300,001 - $500,000 (Premium)
   - Tier 4: $500,001 - $1,000,000 (High-Value)

## Testing Status

✅ **Database Service Methods**: Implemented and tested
✅ **API Endpoint**: Created and verified working
✅ **SQL Migration Scripts**: Created with sample data
✅ **Documentation**: Complete with README and examples
✅ **Backend Build**: Successfully rebuilt and deployed
✅ **Health Check**: Database connected, Drools connected
✅ **Endpoint Response**: Returns proper JSON structure

## Next Steps (For User)

1. **Run the migration script** in pgAdmin using the provided SQL file
2. **Insert sample data** (optional) using the sample data script
3. **Integrate with frontend** to display extracted rules
4. **Implement rule extraction** from actual policy documents using LLM or NLP
5. **Add endpoint to save rules** via POST request from extraction pipeline

## Files Created/Modified

### Created:
- `db/migrations/001_create_extracted_rules_table.sql` - Main migration script
- `db/migrations/001_rollback_extracted_rules_table.sql` - Rollback script
- `db/migrations/001_sample_extracted_rules_data.sql` - Sample data insertion
- `db/migrations/README.md` - Migration documentation
- `EXTRACTED_RULES_FEATURE_COMPLETE.md` - This document

### Modified:
- `rule-agent/DatabaseService.py` - Added ExtractedRule model and methods
- `rule-agent/ChatService.py` - Added extracted-rules endpoint
- `rule-agent/swagger.yaml` - Added API documentation for extracted-rules endpoint

## Support

If you encounter any issues:

1. Check database connection: `curl http://localhost:9000/rule-agent/api/v1/health`
2. Verify tables exist: `SELECT * FROM extracted_rules LIMIT 1;`
3. Check backend logs: `docker logs backend`
4. Review migration README: `db/migrations/README.md`

---

**Status**: ✅ **Feature Complete and Ready for Use**

**Last Updated**: 2025-11-10
