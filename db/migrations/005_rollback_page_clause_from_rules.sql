-- Rollback Migration 005: Remove page and clause columns from rules and queries tables
-- Date: 2025-11-18

-- Drop indexes
DROP INDEX IF EXISTS idx_extracted_rules_page;
DROP INDEX IF EXISTS idx_extracted_rules_clause;
DROP INDEX IF EXISTS idx_hierarchical_rules_page;
DROP INDEX IF EXISTS idx_hierarchical_rules_clause;
DROP INDEX IF EXISTS idx_extraction_queries_page;
DROP INDEX IF EXISTS idx_extraction_queries_clause;

-- Remove columns from extracted_rules
ALTER TABLE extracted_rules
    DROP COLUMN IF EXISTS page_number,
    DROP COLUMN IF EXISTS clause_reference;

-- Remove columns from hierarchical_rules
ALTER TABLE hierarchical_rules
    DROP COLUMN IF EXISTS page_number,
    DROP COLUMN IF EXISTS clause_reference;

-- Remove columns from policy_extraction_queries
ALTER TABLE policy_extraction_queries
    DROP COLUMN IF EXISTS page_number,
    DROP COLUMN IF EXISTS clause_reference;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Rollback migration 005 completed successfully!';
    RAISE NOTICE 'Removed columns: page_number, clause_reference from extracted_rules';
    RAISE NOTICE 'Removed columns: page_number, clause_reference from hierarchical_rules';
    RAISE NOTICE 'Removed columns: page_number, clause_reference from policy_extraction_queries';
    RAISE NOTICE 'Dropped all indexes for page and clause references';
END $$;
