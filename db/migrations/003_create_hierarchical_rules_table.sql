-- Migration: Add hierarchical_rules table
-- Date: 2025-11-13
-- Description: Creates table for storing rules in a hierarchical/tree structure with parent-child relationships

CREATE TABLE IF NOT EXISTS hierarchical_rules (
    id SERIAL PRIMARY KEY,
    bank_id VARCHAR(50) NOT NULL REFERENCES banks(bank_id) ON DELETE CASCADE,
    policy_type_id VARCHAR(50) NOT NULL REFERENCES policy_types(policy_type_id) ON DELETE CASCADE,

    -- Rule details
    rule_id VARCHAR(50) NOT NULL,  -- e.g., "1", "5.1", "11.1.1.1.1"
    name VARCHAR(255) NOT NULL,
    description TEXT,
    expected VARCHAR(255),
    actual VARCHAR(255),
    confidence FLOAT,
    passed BOOLEAN,

    -- Hierarchy
    parent_id INTEGER REFERENCES hierarchical_rules(id) ON DELETE CASCADE,
    level INTEGER DEFAULT 0,  -- 0 for root, 1 for first level children, etc.
    order_index INTEGER DEFAULT 0,  -- For maintaining order within same parent

    -- Metadata
    document_hash VARCHAR(64),
    source_document VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_bank_policy ON hierarchical_rules(bank_id, policy_type_id);
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_parent ON hierarchical_rules(parent_id);
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_active ON hierarchical_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_hash ON hierarchical_rules(document_hash);
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_level ON hierarchical_rules(level);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_hierarchical_rules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER hierarchical_rules_updated_at
    BEFORE UPDATE ON hierarchical_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_hierarchical_rules_updated_at();

COMMENT ON TABLE hierarchical_rules IS 'Stores underwriting rules in a hierarchical tree structure with parent-child dependencies';
COMMENT ON COLUMN hierarchical_rules.rule_id IS 'Dot-notation ID representing position in hierarchy (e.g., 11.1.1.1.1)';
COMMENT ON COLUMN hierarchical_rules.parent_id IS 'Reference to parent rule, NULL for root-level rules';
COMMENT ON COLUMN hierarchical_rules.level IS 'Depth in the tree: 0=root, 1=first child, 2=grandchild, etc.';
COMMENT ON COLUMN hierarchical_rules.order_index IS 'Order of this rule among siblings with the same parent';
