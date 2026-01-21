--
--    Copyright 2024 IBM Corp.
--
--    Licensed under the Apache License, Version 2.0 (the "License");
--    you may not use this file except in compliance with the License.
--    You may obtain a copy of the License at
--
--        http://www.apache.org/licenses/LICENSE-2.0
--
--    Unless required by applicable law or agreed to in writing, software
--    distributed under the License is distributed on an "AS IS" BASIS,
--    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
--    See the License for the specific language governing permissions and
--    limitations under the License.
--

-- Migration: Create test_cases table for storing test scenarios
-- Purpose: Store multiple test cases for policy evaluation with expected results
-- Date: 2025-01-15

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
    created_by VARCHAR(100),

    -- Ensure unique test case names per bank+policy combination
    CONSTRAINT unique_test_case_name UNIQUE (bank_id, policy_type_id, test_case_name, version)
);

-- Create indexes for faster queries
CREATE INDEX idx_test_cases_bank_policy ON test_cases(bank_id, policy_type_id);
CREATE INDEX idx_test_cases_category ON test_cases(category);
CREATE INDEX idx_test_cases_priority ON test_cases(priority);
CREATE INDEX idx_test_cases_active ON test_cases(is_active);
CREATE INDEX idx_test_cases_document_hash ON test_cases(document_hash);

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

-- Create indexes for test executions
CREATE INDEX idx_test_executions_test_case ON test_case_executions(test_case_id);
CREATE INDEX idx_test_executions_execution_id ON test_case_executions(execution_id);
CREATE INDEX idx_test_executions_passed ON test_case_executions(test_passed);
CREATE INDEX idx_test_executions_executed_at ON test_case_executions(executed_at);

-- Create view for test case summary statistics
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

-- Add comments for documentation
COMMENT ON TABLE test_cases IS 'Stores test cases for policy evaluation with input data and expected results';
COMMENT ON TABLE test_case_executions IS 'Tracks execution history and results of test cases';
COMMENT ON VIEW test_case_summary IS 'Summary statistics for test cases including pass rates';

COMMENT ON COLUMN test_cases.applicant_data IS 'JSONB containing applicant details (age, income, creditScore, etc.)';
COMMENT ON COLUMN test_cases.policy_data IS 'JSONB containing policy details (coverageAmount, termYears, type, etc.)';
COMMENT ON COLUMN test_cases.expected_decision IS 'Expected decision outcome: approved, rejected, or pending';
COMMENT ON COLUMN test_cases.category IS 'Test category: boundary, positive, negative, edge_case, regression';
COMMENT ON COLUMN test_cases.is_auto_generated IS 'True if generated by LLM, false if manually created';
COMMENT ON COLUMN test_cases.generation_method IS 'Method used to generate test case: llm, manual, template, boundary_analysis';

-- Insert sample test case for demonstration
-- INSERT INTO test_cases (
--     bank_id,
--     policy_type_id,
--     test_case_name,
--     description,
--     category,
--     priority,
--     applicant_data,
--     policy_data,
--     expected_decision,
--     expected_reasons,
--     expected_risk_category,
--     is_auto_generated,
--     generation_method,
--     created_by
-- ) VALUES (
--     'chase',
--     'insurance',
--     'Ideal Applicant - Mid-Age, Good Health',
--     'Test case for ideal applicant: 35 years old, good health, non-smoker, high income, excellent credit score. Should be approved with low risk.',
--     'positive',
--     1,
--     '{
--         "age": 35,
--         "annualIncome": 75000,
--         "creditScore": 720,
--         "healthConditions": "good",
--         "smoker": false
--     }'::jsonb,
--     '{
--         "coverageAmount": 500000,
--         "termYears": 20,
--         "type": "term_life"
--     }'::jsonb,
--     'approved',
--     ARRAY['Meets all eligibility criteria', 'Low risk profile'],
--     2,
--     false,
--     'manual',
--     'system'
-- ) ON CONFLICT (bank_id, policy_type_id, test_case_name, version) DO NOTHING;

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE ON test_cases TO your_application_user;
-- GRANT SELECT, INSERT ON test_case_executions TO your_application_user;
-- GRANT SELECT ON test_case_summary TO your_application_user;
