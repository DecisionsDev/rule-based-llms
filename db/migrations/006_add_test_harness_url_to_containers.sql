-- Migration: Add s3_test_harness_url column to rule_containers table
-- Purpose: Track the S3 URL for the test harness Excel file
-- Date: 2025-11-18

-- Add s3_test_harness_url column to rule_containers table
ALTER TABLE rule_containers
    ADD COLUMN IF NOT EXISTS s3_test_harness_url TEXT;

-- Add comment to new column
COMMENT ON COLUMN rule_containers.s3_test_harness_url IS 'S3 URL of the test harness Excel file containing hierarchical rules and test cases';

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 006 completed successfully!';
    RAISE NOTICE 'Added column: s3_test_harness_url to rule_containers';
END $$;
