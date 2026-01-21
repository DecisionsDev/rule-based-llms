-- Rollback Migration 006: Remove s3_test_harness_url column from rule_containers table
-- Date: 2025-11-18

-- Remove column from rule_containers
ALTER TABLE rule_containers
    DROP COLUMN IF EXISTS s3_test_harness_url;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Rollback migration 006 completed successfully!';
    RAISE NOTICE 'Removed column: s3_test_harness_url from rule_containers';
END $$;
