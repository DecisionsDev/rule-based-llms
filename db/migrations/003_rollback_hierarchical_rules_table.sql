-- Rollback Migration: Remove hierarchical_rules table
-- Date: 2025-11-13
-- Description: Drops the hierarchical_rules table and related database objects

-- Drop trigger first
DROP TRIGGER IF EXISTS hierarchical_rules_updated_at ON hierarchical_rules;

-- Drop function
DROP FUNCTION IF EXISTS update_hierarchical_rules_updated_at();

-- Drop indexes (will be automatically dropped with table, but explicitly for clarity)
DROP INDEX IF EXISTS idx_hierarchical_rules_bank_policy;
DROP INDEX IF EXISTS idx_hierarchical_rules_parent;
DROP INDEX IF EXISTS idx_hierarchical_rules_active;
DROP INDEX IF EXISTS idx_hierarchical_rules_hash;
DROP INDEX IF EXISTS idx_hierarchical_rules_level;

-- Drop table
DROP TABLE IF EXISTS hierarchical_rules;
