-- Rollback Migration: Drop policy_extraction_queries table
-- Purpose: Rollback the creation of policy_extraction_queries table
-- Date: 2025-11-12

-- Drop trigger
DROP TRIGGER IF EXISTS trigger_update_extraction_queries_timestamp ON policy_extraction_queries;

-- Drop function
DROP FUNCTION IF EXISTS update_extraction_queries_updated_at();

-- Drop indexes
DROP INDEX IF EXISTS idx_extraction_queries_confidence;
DROP INDEX IF EXISTS idx_extraction_queries_created_at;
DROP INDEX IF EXISTS idx_extraction_queries_active;
DROP INDEX IF EXISTS idx_extraction_queries_document_hash;
DROP INDEX IF EXISTS idx_extraction_queries_bank_policy;

-- Drop table
DROP TABLE IF EXISTS policy_extraction_queries CASCADE;

-- Display rollback message
DO $$
BEGIN
    RAISE NOTICE 'Rollback completed successfully!';
    RAISE NOTICE 'Dropped table: policy_extraction_queries';
    RAISE NOTICE 'Dropped all associated indexes, triggers, and functions';
END $$;
