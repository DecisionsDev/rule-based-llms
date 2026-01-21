-- Rollback Migration: Drop extracted_rules table
-- Purpose: Rollback script for extracted_rules table creation
-- Date: 2025-11-10

-- Drop trigger
DROP TRIGGER IF EXISTS trigger_update_extracted_rules_timestamp ON extracted_rules;

-- Drop function
DROP FUNCTION IF EXISTS update_extracted_rules_updated_at();

-- Drop indexes (they will be dropped automatically with the table, but being explicit)
DROP INDEX IF EXISTS idx_extracted_rules_created_at;
DROP INDEX IF EXISTS idx_extracted_rules_active;
DROP INDEX IF EXISTS idx_extracted_rules_bank_policy;

-- Drop table
DROP TABLE IF EXISTS extracted_rules CASCADE;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Rollback completed successfully!';
    RAISE NOTICE 'Dropped table: extracted_rules';
    RAISE NOTICE 'Dropped trigger: trigger_update_extracted_rules_timestamp';
    RAISE NOTICE 'Dropped function: update_extracted_rules_updated_at';
END $$;
