# Database Migration Scripts

This directory contains SQL migration scripts for the underwriter agent database.

## Migration 001: Extracted Rules Table

### Purpose
Create the `extracted_rules` table to store extracted underwriting rules from policy documents for display in the frontend.

### Files

1. **001_create_extracted_rules_table.sql** - Main migration script
   - Creates `extracted_rules` table with all columns and constraints
   - Creates indexes for performance optimization
   - Creates auto-update trigger for `updated_at` column
   - Adds comments to table and columns for documentation

2. **001_rollback_extracted_rules_table.sql** - Rollback script
   - Drops the `extracted_rules` table and all related objects
   - Use this if you need to undo the migration

3. **001_sample_extracted_rules_data.sql** - Sample data script
   - Inserts 29 sample rules for Chase life insurance policy
   - Useful for testing the API endpoint
   - Can be run multiple times (uses ON CONFLICT DO NOTHING)

### How to Run in pgAdmin

#### Step 1: Run the Main Migration

1. Open pgAdmin and connect to your PostgreSQL database
2. Navigate to your database (e.g., `underwriter_db`)
3. Open the Query Tool (Tools > Query Tool)
4. Open the file: `001_create_extracted_rules_table.sql`
5. Click "Execute" (F5) to run the script
6. Verify success by checking the messages tab for "Migration completed successfully!"

#### Step 2: Insert Sample Data (Optional)

1. In the same Query Tool, clear the previous query
2. Open the file: `001_sample_extracted_rules_data.sql`
3. Click "Execute" (F5) to run the script
4. Verify success by checking the messages tab for the rule count

#### Step 3: Verify the Table

Run this query to verify the table was created correctly:

```sql
-- Check table structure
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'extracted_rules'
ORDER BY ordinal_position;

-- Check sample data (if you ran the sample data script)
SELECT
    category,
    COUNT(*) as rule_count
FROM extracted_rules
WHERE bank_id = 'chase' AND policy_type_id = 'insurance'
GROUP BY category
ORDER BY category;
```

### Table Schema

```sql
extracted_rules
├── id (SERIAL PRIMARY KEY)
├── bank_id (VARCHAR(50), FK to banks.bank_id)
├── policy_type_id (VARCHAR(50), FK to policy_types.policy_type_id)
├── rule_name (VARCHAR(255))
├── requirement (TEXT)
├── category (VARCHAR(100))
├── source_document (VARCHAR(500))
├── document_hash (VARCHAR(64))
├── extraction_timestamp (TIMESTAMP)
├── is_active (BOOLEAN)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)
```

### Indexes

- `idx_extracted_rules_bank_policy` - Composite index on (bank_id, policy_type_id)
- `idx_extracted_rules_active` - Index on is_active for filtering
- `idx_extracted_rules_created_at` - Index on created_at for sorting

### API Endpoint

After running the migration, you can use the new API endpoint:

```bash
# Get extracted rules for Chase life insurance
curl "http://localhost:9000/rule-agent/api/v1/extracted-rules?bank_id=chase&policy_type=insurance"
```

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

### Rollback Instructions

If you need to rollback the migration:

1. Open pgAdmin Query Tool
2. Open the file: `001_rollback_extracted_rules_table.sql`
3. Click "Execute" (F5)
4. Verify success by checking the messages tab

⚠️ **Warning**: Rollback will delete all data in the `extracted_rules` table!

### Troubleshooting

**Error: relation "banks" does not exist**
- The migration requires the `banks` and `policy_types` tables to exist first
- Make sure you've run the main database initialization scripts

**Error: permission denied**
- Make sure your database user has CREATE TABLE permissions
- Run: `GRANT CREATE ON DATABASE underwriter_db TO your_username;`

**Sample data not inserting**
- Check if `chase` bank and `insurance` policy type exist in their respective tables
- Run: `SELECT * FROM banks WHERE bank_id = 'chase';`
- Run: `SELECT * FROM policy_types WHERE policy_type_id = 'insurance';`

### Notes

- The `updated_at` column is automatically updated via trigger when a record is modified
- Old rules are soft-deleted (is_active = FALSE) when new rules are saved for the same bank/policy combination
- All timestamps are stored in UTC
- The table uses CASCADE delete to automatically remove rules when a bank or policy type is deleted
