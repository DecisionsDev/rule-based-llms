-- Migration: Add page and clause columns to extracted_rules, hierarchical_rules, and policy_extraction_queries
-- Purpose: Track the source page number and clause/section reference for each rule and query
-- Date: 2025-11-18

-- Add page and clause columns to extracted_rules table
ALTER TABLE extracted_rules
    ADD COLUMN IF NOT EXISTS page_number INTEGER,
    ADD COLUMN IF NOT EXISTS clause_reference VARCHAR(100);

-- Add page and clause columns to hierarchical_rules table
ALTER TABLE hierarchical_rules
    ADD COLUMN IF NOT EXISTS page_number INTEGER,
    ADD COLUMN IF NOT EXISTS clause_reference VARCHAR(100);

-- Add page and clause columns to policy_extraction_queries table
ALTER TABLE policy_extraction_queries
    ADD COLUMN IF NOT EXISTS page_number INTEGER,
    ADD COLUMN IF NOT EXISTS clause_reference VARCHAR(100);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_extracted_rules_page
    ON extracted_rules(page_number);

CREATE INDEX IF NOT EXISTS idx_extracted_rules_clause
    ON extracted_rules(clause_reference);

CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_page
    ON hierarchical_rules(page_number);

CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_clause
    ON hierarchical_rules(clause_reference);

CREATE INDEX IF NOT EXISTS idx_extraction_queries_page
    ON policy_extraction_queries(page_number);

CREATE INDEX IF NOT EXISTS idx_extraction_queries_clause
    ON policy_extraction_queries(clause_reference);

-- Add comments to new columns
COMMENT ON COLUMN extracted_rules.page_number IS 'Page number in the source document where this rule was found';
COMMENT ON COLUMN extracted_rules.clause_reference IS 'Clause or section reference (e.g., "Article II, Section 3.1", "Clause 5.2")';

COMMENT ON COLUMN hierarchical_rules.page_number IS 'Page number in the source document where this rule was found';
COMMENT ON COLUMN hierarchical_rules.clause_reference IS 'Clause or section reference (e.g., "Article II, Section 3.1", "Clause 5.2")';

COMMENT ON COLUMN policy_extraction_queries.page_number IS 'Page number in the source document where this query was targeted';
COMMENT ON COLUMN policy_extraction_queries.clause_reference IS 'Clause or section reference (e.g., "Article II, Section 3.1", "Clause 5.2")';

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 005 completed successfully!';
    RAISE NOTICE 'Added columns: page_number, clause_reference to extracted_rules';
    RAISE NOTICE 'Added columns: page_number, clause_reference to hierarchical_rules';
    RAISE NOTICE 'Added columns: page_number, clause_reference to policy_extraction_queries';
    RAISE NOTICE 'Created indexes: idx_extracted_rules_page, idx_extracted_rules_clause';
    RAISE NOTICE 'Created indexes: idx_hierarchical_rules_page, idx_hierarchical_rules_clause';
    RAISE NOTICE 'Created indexes: idx_extraction_queries_page, idx_extraction_queries_clause';
END $$;
