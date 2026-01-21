-- Migration 007: Fix test_case unique constraint to only apply to active records
-- This allows reprocessing policies without getting duplicate key violations
-- Date: 2025-11-19

-- Drop the old unique constraint
ALTER TABLE test_cases DROP CONSTRAINT IF EXISTS unique_test_case_name;

-- Create a partial unique index that only applies to active records
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_test_case_name
ON test_cases (bank_id, policy_type_id, test_case_name, version)
WHERE is_active = true;

-- Add comment explaining the index
COMMENT ON INDEX unique_active_test_case_name IS 'Ensures unique test case names per bank/policy/version, but only for active records. This allows keeping historical (inactive) test cases with the same name.';

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 007 completed successfully!';
    RAISE NOTICE 'Replaced unique_test_case_name constraint with partial index unique_active_test_case_name';
    RAISE NOTICE 'Test cases can now be reprocessed without duplicate key violations';
END $$;
