-- Rollback Migration 007: Restore original test_case unique constraint
-- Date: 2025-11-19

-- Drop the partial unique index
DROP INDEX IF EXISTS unique_active_test_case_name;

-- Restore the original unique constraint (applies to all records)
ALTER TABLE test_cases
ADD CONSTRAINT unique_test_case_name UNIQUE (bank_id, policy_type_id, test_case_name, version);

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Rollback migration 007 completed successfully!';
    RAISE NOTICE 'Restored original unique_test_case_name constraint';
END $$;
