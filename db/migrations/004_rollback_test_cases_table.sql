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

-- Rollback Migration: Drop test_cases and related objects
-- Purpose: Rollback the test cases feature migration
-- Date: 2025-01-15

-- Drop view
DROP VIEW IF EXISTS test_case_summary;

-- Drop indexes for test_case_executions
DROP INDEX IF EXISTS idx_test_executions_executed_at;
DROP INDEX IF EXISTS idx_test_executions_passed;
DROP INDEX IF EXISTS idx_test_executions_execution_id;
DROP INDEX IF EXISTS idx_test_executions_test_case;

-- Drop test_case_executions table
DROP TABLE IF EXISTS test_case_executions;

-- Drop indexes for test_cases
DROP INDEX IF EXISTS idx_test_cases_document_hash;
DROP INDEX IF EXISTS idx_test_cases_active;
DROP INDEX IF EXISTS idx_test_cases_priority;
DROP INDEX IF EXISTS idx_test_cases_category;
DROP INDEX IF EXISTS idx_test_cases_bank_policy;

-- Drop test_cases table
DROP TABLE IF EXISTS test_cases;
