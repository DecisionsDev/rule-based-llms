-- PostgreSQL Database Schema for Underwriting AI System
-- Manages rule container deployments, banks, and policy types
-- Includes all migrations (001-007) integrated into a single initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Banks/Organizations table
CREATE TABLE banks (
    bank_id VARCHAR(50) PRIMARY KEY,
    bank_name VARCHAR(255) NOT NULL,
    description TEXT,
    contact_email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Policy types table
CREATE TABLE policy_types (
    policy_type_id VARCHAR(50) PRIMARY KEY,
    policy_name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50), -- e.g., 'insurance', 'loan', 'credit'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Deployed rule containers
CREATE TABLE rule_containers (
    id SERIAL PRIMARY KEY,
    container_id VARCHAR(255) UNIQUE NOT NULL,
    bank_id VARCHAR(50) REFERENCES banks(bank_id) ON DELETE CASCADE,
    policy_type_id VARCHAR(50) REFERENCES policy_types(policy_type_id) ON DELETE CASCADE,

    -- Container details
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('docker', 'kubernetes', 'local')),
    container_name VARCHAR(255),
    endpoint VARCHAR(500) NOT NULL,
    port INTEGER,

    -- Status tracking
    status VARCHAR(20) DEFAULT 'deploying' CHECK (status IN ('deploying', 'running', 'stopped', 'failed', 'unhealthy')),
    health_check_url VARCHAR(500),
    last_health_check TIMESTAMP,
    health_status VARCHAR(20) DEFAULT 'unknown' CHECK (health_status IN ('healthy', 'unhealthy', 'unknown')),
    failure_reason TEXT,

    -- Deployment metadata
    document_hash VARCHAR(64), -- SHA-256 of source policy document
    s3_policy_url VARCHAR(500), -- Original policy document
    s3_jar_url VARCHAR(500), -- Deployed JAR file
    s3_drl_url VARCHAR(500), -- Generated DRL rules
    s3_excel_url VARCHAR(500), -- Excel export of rules
    s3_test_harness_url TEXT, -- Test harness Excel file (Migration 006)

    -- Versioning
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,

    -- Resource usage (optional)
    cpu_limit VARCHAR(20),
    memory_limit VARCHAR(20),

    -- Timestamps
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stopped_at TIMESTAMP
);

-- Create partial unique index to ensure only one active container per bank+policy combination
-- Note: This replaces the table constraint which incorrectly included is_active in the unique constraint
CREATE UNIQUE INDEX idx_unique_active_container
    ON rule_containers(bank_id, policy_type_id)
    WHERE is_active = true;

-- Request tracking for analytics and debugging
CREATE TABLE rule_requests (
    id SERIAL PRIMARY KEY,
    container_id INTEGER REFERENCES rule_containers(id) ON DELETE SET NULL,
    bank_id VARCHAR(50) REFERENCES banks(bank_id) ON DELETE SET NULL,
    policy_type_id VARCHAR(50) REFERENCES policy_types(policy_type_id) ON DELETE SET NULL,

    -- Request details
    request_id UUID DEFAULT uuid_generate_v4(),
    endpoint VARCHAR(255),
    http_method VARCHAR(10),

    -- Payload
    request_payload JSONB,
    response_payload JSONB,

    -- Performance
    execution_time_ms INTEGER,
    status_code INTEGER,
    status VARCHAR(20) CHECK (status IN ('success', 'error', 'timeout')),
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Container deployment history for audit trail
CREATE TABLE container_deployment_history (
    id SERIAL PRIMARY KEY,
    container_id INTEGER REFERENCES rule_containers(id) ON DELETE CASCADE,
    bank_id VARCHAR(50),
    policy_type_id VARCHAR(50),

    -- Deployment details
    action VARCHAR(20) CHECK (action IN ('deployed', 'updated', 'stopped', 'restarted', 'failed')),
    version INTEGER,
    platform VARCHAR(20),
    endpoint VARCHAR(500),

    -- Change tracking
    document_hash VARCHAR(64),
    changes_description TEXT,
    deployed_by VARCHAR(100), -- Could be user ID or system

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- MIGRATION 001: Extracted Rules Table
-- ============================================================================

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

    -- Source location tracking (Migration 005)
    page_number INTEGER,
    clause_reference VARCHAR(100),

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

-- ============================================================================
-- MIGRATION 002: Policy Extraction Queries Table
-- ============================================================================

-- Policy extraction queries table (stores LLM queries and Textract responses)
CREATE TABLE IF NOT EXISTS policy_extraction_queries (
    id SERIAL PRIMARY KEY,
    bank_id VARCHAR(50) REFERENCES banks(bank_id) ON DELETE CASCADE NOT NULL,
    policy_type_id VARCHAR(50) REFERENCES policy_types(policy_type_id) ON DELETE CASCADE NOT NULL,

    -- Query and response details
    query_text TEXT NOT NULL,
    response_text TEXT,
    confidence_score NUMERIC(5, 2), -- Textract confidence score (0-100)

    -- Source location tracking (Migration 005)
    page_number INTEGER,
    clause_reference VARCHAR(100),

    -- Metadata
    document_hash VARCHAR(64) NOT NULL,
    source_document VARCHAR(500),
    extraction_method VARCHAR(50) DEFAULT 'textract', -- textract, manual, etc.
    query_order INTEGER, -- Order in which query was generated

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- MIGRATION 003: Hierarchical Rules Table
-- ============================================================================

-- Create hierarchical_rules table
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

    -- Source location tracking (Migration 005)
    page_number INTEGER,
    clause_reference VARCHAR(100),

    -- Metadata
    document_hash VARCHAR(64),
    source_document VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- MIGRATION 004: Test Cases and Test Executions Tables
-- ============================================================================

-- Create test_cases table
CREATE TABLE IF NOT EXISTS test_cases (
    id SERIAL PRIMARY KEY,

    -- Multi-tenant identifiers
    bank_id VARCHAR(50) NOT NULL REFERENCES banks(bank_id) ON DELETE CASCADE,
    policy_type_id VARCHAR(50) NOT NULL REFERENCES policy_types(policy_type_id) ON DELETE CASCADE,

    -- Test case metadata
    test_case_name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100), -- 'boundary', 'positive', 'negative', 'edge_case', 'regression'
    priority INTEGER DEFAULT 1, -- 1=high, 2=medium, 3=low

    -- Test data (JSONB for flexibility)
    applicant_data JSONB NOT NULL,
    policy_data JSONB,

    -- Expected results
    expected_decision VARCHAR(50), -- 'approved', 'rejected', 'pending'
    expected_reasons TEXT[], -- Array of expected rejection/approval reasons
    expected_risk_category INTEGER, -- Expected risk score 1-5

    -- Metadata
    document_hash VARCHAR(64), -- SHA-256 hash of source policy document
    source_document VARCHAR(500), -- S3 URL or file path

    -- Auto-generated flag
    is_auto_generated BOOLEAN DEFAULT false,
    generation_method VARCHAR(50), -- 'llm', 'manual', 'template', 'boundary_analysis'

    -- Active/versioning
    is_active BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,

    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);

-- Create test_case_executions table to track test runs
CREATE TABLE IF NOT EXISTS test_case_executions (
    id SERIAL PRIMARY KEY,

    -- Foreign key to test case
    test_case_id INTEGER NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,

    -- Execution details
    execution_id VARCHAR(100) NOT NULL, -- UUID for tracking
    container_id VARCHAR(200), -- Which Drools container was used

    -- Actual results
    actual_decision VARCHAR(50),
    actual_reasons TEXT[],
    actual_risk_category INTEGER,

    -- Full response
    request_payload JSONB,
    response_payload JSONB,

    -- Test result
    test_passed BOOLEAN,
    pass_reason TEXT, -- Why it passed
    fail_reason TEXT, -- Why it failed

    -- Performance metrics
    execution_time_ms INTEGER,

    -- Audit fields
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_by VARCHAR(100)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Indexes for rule_containers
CREATE INDEX idx_containers_bank_policy ON rule_containers(bank_id, policy_type_id);
CREATE INDEX idx_containers_status ON rule_containers(status);
CREATE INDEX idx_containers_active ON rule_containers(is_active) WHERE is_active = true;
CREATE INDEX idx_containers_health ON rule_containers(health_status);
CREATE INDEX idx_containers_platform ON rule_containers(platform);
CREATE INDEX idx_containers_deployed_at ON rule_containers(deployed_at DESC);

-- Indexes for rule_requests
CREATE INDEX idx_requests_container ON rule_requests(container_id);
CREATE INDEX idx_requests_bank ON rule_requests(bank_id);
CREATE INDEX idx_requests_created_at ON rule_requests(created_at DESC);
CREATE INDEX idx_requests_status ON rule_requests(status);

-- Indexes for container_deployment_history
CREATE INDEX idx_history_container ON container_deployment_history(container_id);
CREATE INDEX idx_history_created_at ON container_deployment_history(created_at DESC);

-- Indexes for extracted_rules (Migration 001)
CREATE INDEX IF NOT EXISTS idx_extracted_rules_bank_policy
    ON extracted_rules(bank_id, policy_type_id);
CREATE INDEX IF NOT EXISTS idx_extracted_rules_active
    ON extracted_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_extracted_rules_created_at
    ON extracted_rules(created_at);
CREATE INDEX IF NOT EXISTS idx_extracted_rules_page
    ON extracted_rules(page_number);
CREATE INDEX IF NOT EXISTS idx_extracted_rules_clause
    ON extracted_rules(clause_reference);

-- Indexes for policy_extraction_queries (Migration 002)
CREATE INDEX IF NOT EXISTS idx_extraction_queries_bank_policy
    ON policy_extraction_queries(bank_id, policy_type_id);
CREATE INDEX IF NOT EXISTS idx_extraction_queries_document_hash
    ON policy_extraction_queries(document_hash);
CREATE INDEX IF NOT EXISTS idx_extraction_queries_active
    ON policy_extraction_queries(is_active);
CREATE INDEX IF NOT EXISTS idx_extraction_queries_created_at
    ON policy_extraction_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_extraction_queries_confidence
    ON policy_extraction_queries(confidence_score) WHERE confidence_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_extraction_queries_page
    ON policy_extraction_queries(page_number);
CREATE INDEX IF NOT EXISTS idx_extraction_queries_clause
    ON policy_extraction_queries(clause_reference);

-- Indexes for hierarchical_rules (Migration 003)
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_bank_policy
    ON hierarchical_rules(bank_id, policy_type_id);
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_parent
    ON hierarchical_rules(parent_id);
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_active
    ON hierarchical_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_hash
    ON hierarchical_rules(document_hash);
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_level
    ON hierarchical_rules(level);
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_page
    ON hierarchical_rules(page_number);
CREATE INDEX IF NOT EXISTS idx_hierarchical_rules_clause
    ON hierarchical_rules(clause_reference);

-- Indexes for test_cases (Migration 004)
CREATE INDEX IF NOT EXISTS idx_test_cases_bank_policy
    ON test_cases(bank_id, policy_type_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_category
    ON test_cases(category);
CREATE INDEX IF NOT EXISTS idx_test_cases_priority
    ON test_cases(priority);
CREATE INDEX IF NOT EXISTS idx_test_cases_active
    ON test_cases(is_active);
CREATE INDEX IF NOT EXISTS idx_test_cases_document_hash
    ON test_cases(document_hash);

-- Indexes for test_case_executions (Migration 004)
CREATE INDEX IF NOT EXISTS idx_test_executions_test_case
    ON test_case_executions(test_case_id);
CREATE INDEX IF NOT EXISTS idx_test_executions_execution_id
    ON test_case_executions(execution_id);
CREATE INDEX IF NOT EXISTS idx_test_executions_passed
    ON test_case_executions(test_passed);
CREATE INDEX IF NOT EXISTS idx_test_executions_executed_at
    ON test_case_executions(executed_at);

-- ============================================================================
-- MIGRATION 007: Test Case Unique Constraint Fix (Partial Index)
-- ============================================================================

-- Create a partial unique index that only applies to active records
-- This allows reprocessing policies without getting duplicate key violations
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_test_case_name
    ON test_cases (bank_id, policy_type_id, test_case_name, version)
    WHERE is_active = true;

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_banks_updated_at BEFORE UPDATE ON banks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_policy_types_updated_at BEFORE UPDATE ON policy_types
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rule_containers_updated_at BEFORE UPDATE ON rule_containers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for extracted_rules updated_at (Migration 001)
-- Uses the shared update_updated_at_column() function
DROP TRIGGER IF EXISTS trigger_update_extracted_rules_timestamp ON extracted_rules;
CREATE TRIGGER trigger_update_extracted_rules_timestamp
    BEFORE UPDATE ON extracted_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for policy_extraction_queries updated_at (Migration 002)
-- Uses the shared update_updated_at_column() function
DROP TRIGGER IF EXISTS trigger_update_extraction_queries_timestamp ON policy_extraction_queries;
CREATE TRIGGER trigger_update_extraction_queries_timestamp
    BEFORE UPDATE ON policy_extraction_queries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for hierarchical_rules updated_at (Migration 003)
-- Uses the shared update_updated_at_column() function
DROP TRIGGER IF EXISTS hierarchical_rules_updated_at ON hierarchical_rules;
CREATE TRIGGER hierarchical_rules_updated_at
    BEFORE UPDATE ON hierarchical_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to log deployment history
CREATE OR REPLACE FUNCTION log_container_deployment()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO container_deployment_history (
            container_id, bank_id, policy_type_id, action, version,
            platform, endpoint, document_hash
        ) VALUES (
            NEW.id, NEW.bank_id, NEW.policy_type_id, 'deployed', NEW.version,
            NEW.platform, NEW.endpoint, NEW.document_hash
        );
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status != NEW.status THEN
            INSERT INTO container_deployment_history (
                container_id, bank_id, policy_type_id, action, version,
                platform, endpoint, document_hash
            ) VALUES (
                NEW.id, NEW.bank_id, NEW.policy_type_id,
                CASE
                    WHEN NEW.status = 'stopped' THEN 'stopped'
                    WHEN NEW.status = 'running' AND OLD.status = 'stopped' THEN 'restarted'
                    WHEN NEW.status = 'failed' THEN 'failed'
                    ELSE 'updated'
                END,
                NEW.version, NEW.platform, NEW.endpoint, NEW.document_hash
            );
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER log_container_changes AFTER INSERT OR UPDATE ON rule_containers
    FOR EACH ROW EXECUTE FUNCTION log_container_deployment();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View for active containers
CREATE OR REPLACE VIEW active_containers AS
SELECT
    rc.id,
    rc.container_id,
    rc.bank_id,
    b.bank_name,
    rc.policy_type_id,
    pt.policy_name,
    rc.platform,
    rc.endpoint,
    rc.port,
    rc.status,
    rc.health_status,
    rc.version,
    rc.deployed_at,
    rc.last_health_check
FROM rule_containers rc
JOIN banks b ON rc.bank_id = b.bank_id
JOIN policy_types pt ON rc.policy_type_id = pt.policy_type_id
WHERE rc.is_active = true
ORDER BY rc.deployed_at DESC;

-- View for container statistics
CREATE OR REPLACE VIEW container_stats AS
SELECT
    rc.container_id,
    rc.bank_id,
    rc.policy_type_id,
    COUNT(rr.id) as total_requests,
    COUNT(CASE WHEN rr.status = 'success' THEN 1 END) as successful_requests,
    COUNT(CASE WHEN rr.status = 'error' THEN 1 END) as failed_requests,
    AVG(rr.execution_time_ms) as avg_execution_time_ms,
    MAX(rr.created_at) as last_request_at
FROM rule_containers rc
LEFT JOIN rule_requests rr ON rc.id = rr.container_id
WHERE rc.is_active = true
GROUP BY rc.container_id, rc.bank_id, rc.policy_type_id;

-- View for test case summary statistics (Migration 004)
CREATE OR REPLACE VIEW test_case_summary AS
SELECT
    tc.id,
    tc.bank_id,
    tc.policy_type_id,
    tc.test_case_name,
    tc.category,
    tc.priority,
    tc.is_auto_generated,
    tc.created_at,
    COUNT(tce.id) as total_executions,
    COUNT(CASE WHEN tce.test_passed = true THEN 1 END) as passed_executions,
    COUNT(CASE WHEN tce.test_passed = false THEN 1 END) as failed_executions,
    CASE
        WHEN COUNT(tce.id) > 0
        THEN ROUND((COUNT(CASE WHEN tce.test_passed = true THEN 1 END)::numeric / COUNT(tce.id)::numeric) * 100, 2)
        ELSE 0
    END as pass_rate,
    MAX(tce.executed_at) as last_execution_at
FROM test_cases tc
LEFT JOIN test_case_executions tce ON tc.id = tce.test_case_id
WHERE tc.is_active = true
GROUP BY tc.id, tc.bank_id, tc.policy_type_id, tc.test_case_name,
         tc.category, tc.priority, tc.is_auto_generated, tc.created_at;

-- ============================================================================
-- TABLE AND COLUMN COMMENTS
-- ============================================================================

-- Comments for extracted_rules (Migration 001)
COMMENT ON TABLE extracted_rules IS 'Stores extracted underwriting rules from policy documents for display in frontend';
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
COMMENT ON COLUMN extracted_rules.page_number IS 'Page number in the source document where this rule was found';
COMMENT ON COLUMN extracted_rules.clause_reference IS 'Clause or section reference (e.g., "Article II, Section 3.1", "Clause 5.2")';

-- Comments for policy_extraction_queries (Migration 002)
COMMENT ON TABLE policy_extraction_queries IS 'Stores LLM-generated extraction queries and AWS Textract responses with confidence scores';
COMMENT ON COLUMN policy_extraction_queries.id IS 'Primary key';
COMMENT ON COLUMN policy_extraction_queries.bank_id IS 'Reference to the bank that owns this policy';
COMMENT ON COLUMN policy_extraction_queries.policy_type_id IS 'Reference to the policy type';
COMMENT ON COLUMN policy_extraction_queries.query_text IS 'The query text generated by LLM for data extraction';
COMMENT ON COLUMN policy_extraction_queries.response_text IS 'The extracted response from AWS Textract';
COMMENT ON COLUMN policy_extraction_queries.confidence_score IS 'Textract confidence score (0-100)';
COMMENT ON COLUMN policy_extraction_queries.document_hash IS 'Hash of the source document for linking to containers';
COMMENT ON COLUMN policy_extraction_queries.source_document IS 'Source document path or S3 URL';
COMMENT ON COLUMN policy_extraction_queries.extraction_method IS 'Method used for extraction (textract, manual, etc.)';
COMMENT ON COLUMN policy_extraction_queries.query_order IS 'Order in which query was generated';
COMMENT ON COLUMN policy_extraction_queries.is_active IS 'Whether this query is currently active';
COMMENT ON COLUMN policy_extraction_queries.created_at IS 'Timestamp when the record was created';
COMMENT ON COLUMN policy_extraction_queries.updated_at IS 'Timestamp when the record was last updated';
COMMENT ON COLUMN policy_extraction_queries.page_number IS 'Page number in the source document where this query was targeted';
COMMENT ON COLUMN policy_extraction_queries.clause_reference IS 'Clause or section reference (e.g., "Article II, Section 3.1", "Clause 5.2")';

-- Comments for hierarchical_rules (Migration 003)
COMMENT ON TABLE hierarchical_rules IS 'Stores underwriting rules in a hierarchical tree structure with parent-child dependencies';
COMMENT ON COLUMN hierarchical_rules.rule_id IS 'Dot-notation ID representing position in hierarchy (e.g., 11.1.1.1.1)';
COMMENT ON COLUMN hierarchical_rules.parent_id IS 'Reference to parent rule, NULL for root-level rules';
COMMENT ON COLUMN hierarchical_rules.level IS 'Depth in the tree: 0=root, 1=first child, 2=grandchild, etc.';
COMMENT ON COLUMN hierarchical_rules.order_index IS 'Order of this rule among siblings with the same parent';
COMMENT ON COLUMN hierarchical_rules.page_number IS 'Page number in the source document where this rule was found';
COMMENT ON COLUMN hierarchical_rules.clause_reference IS 'Clause or section reference (e.g., "Article II, Section 3.1", "Clause 5.2")';

-- Comments for test_cases (Migration 004)
COMMENT ON TABLE test_cases IS 'Stores test cases for policy evaluation with input data and expected results';
COMMENT ON TABLE test_case_executions IS 'Tracks execution history and results of test cases';
COMMENT ON VIEW test_case_summary IS 'Summary statistics for test cases including pass rates';
COMMENT ON COLUMN test_cases.applicant_data IS 'JSONB containing applicant details (age, income, creditScore, etc.)';
COMMENT ON COLUMN test_cases.policy_data IS 'JSONB containing policy details (coverageAmount, termYears, type, etc.)';
COMMENT ON COLUMN test_cases.expected_decision IS 'Expected decision outcome: approved, rejected, or pending';
COMMENT ON COLUMN test_cases.category IS 'Test category: boundary, positive, negative, edge_case, regression';
COMMENT ON COLUMN test_cases.is_auto_generated IS 'True if generated by LLM, false if manually created';
COMMENT ON COLUMN test_cases.generation_method IS 'Method used to generate test case: llm, manual, template, boundary_analysis';

-- Comments for rule_containers (Migration 006)
COMMENT ON COLUMN rule_containers.s3_test_harness_url IS 'S3 URL of the test harness Excel file containing hierarchical rules and test cases';

-- Comments for test case constraint (Migration 007)
COMMENT ON INDEX unique_active_test_case_name IS 'Ensures unique test case names per bank/policy/version, but only for active records. This allows keeping historical (inactive) test cases with the same name.';

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

-- Grant permissions (adjust as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO underwriting_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO underwriting_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO underwriting_user;

-- ============================================================================
-- INITIALIZATION COMPLETE
-- ============================================================================

-- No sample data inserted - tables start empty
-- Banks, policy types, and containers will be created dynamically through the API

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully!';
    RAISE NOTICE 'All migrations (001-007) have been integrated into this initialization script.';
    RAISE NOTICE 'Tables created: banks, policy_types, rule_containers, rule_requests, container_deployment_history';
    RAISE NOTICE 'Migration tables: extracted_rules, policy_extraction_queries, hierarchical_rules, test_cases, test_case_executions';
    RAISE NOTICE 'Views created: active_containers, container_stats, test_case_summary';
END $$;
