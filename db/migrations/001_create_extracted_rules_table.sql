-- Migration: Create extracted_rules table
-- Purpose: Store extracted underwriting rules from policy documents
-- Date: 2025-11-10

-- Create extracted_rules table
CREATE TABLE IF NOT EXISTS extracted_rules (
    id SERIAL PRIMARY KEY,
    bank_id VARCHAR(50) NOT NULL,
    policy_type_id VARCHAR(50) NOT NULL,

    -- Rule details
    rule_name VARCHAR(255) NOT NULL,
    requirement TEXT NOT NULL,
    category VARCHAR(100),
    source_document VARCHAR(500),

    -- Metadata
    document_hash VARCHAR(64),
    extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign keys
    CONSTRAINT fk_extracted_rules_bank
        FOREIGN KEY (bank_id)
        REFERENCES banks(bank_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_extracted_rules_policy_type
        FOREIGN KEY (policy_type_id)
        REFERENCES policy_types(policy_type_id)
        ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_extracted_rules_bank_policy
    ON extracted_rules(bank_id, policy_type_id);

CREATE INDEX IF NOT EXISTS idx_extracted_rules_active
    ON extracted_rules(is_active);

CREATE INDEX IF NOT EXISTS idx_extracted_rules_created_at
    ON extracted_rules(created_at);

-- Add comment to table
COMMENT ON TABLE extracted_rules IS 'Stores extracted underwriting rules from policy documents for display in frontend';

-- Add comments to columns
COMMENT ON COLUMN extracted_rules.id IS 'Primary key';
COMMENT ON COLUMN extracted_rules.bank_id IS 'Reference to the bank that owns this rule';
COMMENT ON COLUMN extracted_rules.policy_type_id IS 'Reference to the policy type this rule applies to';
COMMENT ON COLUMN extracted_rules.rule_name IS 'Name or title of the rule';
COMMENT ON COLUMN extracted_rules.requirement IS 'The actual requirement or rule text';
COMMENT ON COLUMN extracted_rules.category IS 'Category for grouping rules (e.g., Age Requirements, Income Requirements)';
COMMENT ON COLUMN extracted_rules.source_document IS 'Source document path or name from which the rule was extracted';
COMMENT ON COLUMN extracted_rules.document_hash IS 'Hash of the source document for change detection';
COMMENT ON COLUMN extracted_rules.extraction_timestamp IS 'When the rule was extracted from the document';
COMMENT ON COLUMN extracted_rules.is_active IS 'Whether this rule is currently active (false for historical rules)';
COMMENT ON COLUMN extracted_rules.created_at IS 'Timestamp when the record was created';
COMMENT ON COLUMN extracted_rules.updated_at IS 'Timestamp when the record was last updated';

-- Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_extracted_rules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_extracted_rules_timestamp ON extracted_rules;
CREATE TRIGGER trigger_update_extracted_rules_timestamp
    BEFORE UPDATE ON extracted_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_extracted_rules_updated_at();

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON extracted_rules TO underwriter_user;
-- GRANT USAGE, SELECT ON SEQUENCE extracted_rules_id_seq TO underwriter_user;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Created table: extracted_rules';
    RAISE NOTICE 'Created indexes: idx_extracted_rules_bank_policy, idx_extracted_rules_active, idx_extracted_rules_created_at';
    RAISE NOTICE 'Created trigger: trigger_update_extracted_rules_timestamp';
END $$;
