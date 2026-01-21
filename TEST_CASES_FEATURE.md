# Test Cases Feature - Automated Test Generation

## Overview

The Test Cases feature automatically generates comprehensive test scenarios for policy evaluation during the policy processing workflow. This ensures thorough testing coverage and validates that the generated rules work correctly across various scenarios.

## Key Features

### 1. Automatic Test Case Generation ✨
- **LLM-Powered**: Uses advanced language models to analyze policy documents and generate intelligent test cases
- **Context-Aware**: Considers extracted rules and hierarchical rules to create relevant test scenarios
- **Comprehensive Coverage**: Generates positive, negative, boundary, and edge cases automatically

### 2. Database Persistence
- All test cases stored in PostgreSQL database
- Execution history tracking
- Summary statistics and pass rates
- Version control with document hash linkage

### 3. Multiple Test Categories
- **Positive Cases**: Scenarios that should be approved
- **Negative Cases**: Scenarios that should be rejected
- **Boundary Cases**: Applicants at approval/rejection thresholds
- **Edge Cases**: Unusual or rare scenarios

### 4. Test Execution Tracking
- Records every test run with timestamp
- Compares expected vs actual results
- Calculates pass/fail status
- Tracks performance metrics (execution time)

---

## Database Schema

### test_cases Table

Stores test case definitions with input data and expected results.

```sql
CREATE TABLE test_cases (
    id SERIAL PRIMARY KEY,

    -- Multi-tenant identifiers
    bank_id VARCHAR(50) REFERENCES banks(bank_id),
    policy_type_id VARCHAR(50) REFERENCES policy_types(policy_type_id),

    -- Test case metadata
    test_case_name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100), -- 'positive', 'negative', 'boundary', 'edge_case', 'regression'
    priority INTEGER DEFAULT 1, -- 1=high, 2=medium, 3=low

    -- Test data (JSONB)
    applicant_data JSONB NOT NULL,
    policy_data JSONB,

    -- Expected results
    expected_decision VARCHAR(50), -- 'approved', 'rejected', 'pending'
    expected_reasons TEXT[], -- Array of expected reasons
    expected_risk_category INTEGER, -- 1-5

    -- Metadata
    document_hash VARCHAR(64),
    source_document VARCHAR(500),
    is_auto_generated BOOLEAN DEFAULT false,
    generation_method VARCHAR(50), -- 'llm', 'manual', 'template'

    -- Versioning
    is_active BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);
```

### test_case_executions Table

Tracks execution history and results of test cases.

```sql
CREATE TABLE test_case_executions (
    id SERIAL PRIMARY KEY,
    test_case_id INTEGER REFERENCES test_cases(id),

    -- Execution details
    execution_id VARCHAR(100) NOT NULL,
    container_id VARCHAR(200),

    -- Actual results
    actual_decision VARCHAR(50),
    actual_reasons TEXT[],
    actual_risk_category INTEGER,

    -- Full response
    request_payload JSONB,
    response_payload JSONB,

    -- Test result
    test_passed BOOLEAN,
    pass_reason TEXT,
    fail_reason TEXT,

    -- Performance
    execution_time_ms INTEGER,

    -- Audit
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_by VARCHAR(100)
);
```

### test_case_summary View

Provides aggregated statistics for test cases.

```sql
CREATE VIEW test_case_summary AS
SELECT
    tc.id,
    tc.bank_id,
    tc.policy_type_id,
    tc.test_case_name,
    tc.category,
    tc.priority,
    COUNT(tce.id) as total_executions,
    COUNT(CASE WHEN tce.test_passed = true THEN 1 END) as passed_executions,
    COUNT(CASE WHEN tce.test_passed = false THEN 1 END) as failed_executions,
    ROUND((COUNT(CASE WHEN tce.test_passed = true THEN 1 END)::numeric /
           COUNT(tce.id)::numeric) * 100, 2) as pass_rate,
    MAX(tce.executed_at) as last_execution_at
FROM test_cases tc
LEFT JOIN test_case_executions tce ON tc.id = tce.test_case_id
WHERE tc.is_active = true
GROUP BY tc.id;
```

---

## Workflow Integration

### Step 4.7: Test Case Generation

Added to the policy processing workflow after hierarchical rules generation:

```
Step 4.6: Generate Hierarchical Rules
    ↓
Step 4.7: Generate Test Cases ✨ NEW!
    - Analyze policy document
    - Review extracted rules
    - Review hierarchical rules
    - Generate 5-10 test cases using LLM
    - Save to database
    ↓
Step 5: Deploy to Drools
```

### Generation Process

1. **Context Gathering**: Collects policy text, extracted rules, and hierarchical rules
2. **LLM Analysis**: Sends context to LLM with specialized prompt
3. **Test Case Generation**: LLM generates diverse test scenarios
4. **Database Persistence**: Saves test cases to PostgreSQL
5. **Summary Reporting**: Returns statistics about generated tests

---

## Test Case Structure

### Example Test Case

```json
{
  "test_case_name": "Ideal Applicant - Mid-Age, Good Health",
  "description": "35-year-old non-smoker with excellent health, high income, and good credit score. Should be approved with low risk.",
  "category": "positive",
  "priority": 1,
  "applicant_data": {
    "age": 35,
    "annualIncome": 75000,
    "creditScore": 720,
    "healthConditions": "good",
    "smoker": false
  },
  "policy_data": {
    "coverageAmount": 500000,
    "termYears": 20,
    "type": "term_life"
  },
  "expected_decision": "approved",
  "expected_reasons": [
    "Meets all eligibility criteria",
    "Low risk profile"
  ],
  "expected_risk_category": 2
}
```

### Test Categories

**1. Positive Cases** (should be approved)
- Ideal applicants meeting all criteria
- Low to medium risk profiles
- Standard approval scenarios

**2. Negative Cases** (should be rejected)
- Applicants failing key requirements
- High risk profiles
- Clear rejection scenarios

**3. Boundary Cases** (at thresholds)
- Minimum/maximum age limits
- Threshold credit scores
- Borderline income levels

**4. Edge Cases** (unusual scenarios)
- Elderly with excellent health
- Young with high coverage
- Rare combinations of factors

---

## API Integration

### GET Policy API with Test Cases

Test cases are now included in the `/api/v1/policies` endpoint response when requested.

**Endpoint**: `GET /api/v1/policies`

**Query Parameters**:
- `bank_id` (required): Bank identifier
- `policy_type` (required): Policy type identifier
- `include_test_cases` (optional, default: false): Include test cases in response

**Example Request**:
```bash
curl -G "http://localhost:9000/rule-agent/api/v1/policies" \
  --data-urlencode "bank_id=chase" \
  --data-urlencode "policy_type=insurance" \
  --data-urlencode "include_test_cases=true"
```

**Example Response**:
```json
{
  "status": "success",
  "container": {
    "container_id": "chase-insurance-underwriting-rules",
    "bank_id": "chase",
    "policy_type_id": "insurance",
    "endpoint": "http://drools-chase-insurance:8081/kie-server/services/rest/server",
    "status": "running",
    "health_status": "healthy",
    "deployed_at": "2025-11-15T10:00:00"
  },
  "test_cases": [
    {
      "id": 1,
      "test_case_name": "Ideal Applicant - Mid-Age, Good Health",
      "description": "35-year-old non-smoker with excellent health...",
      "category": "positive",
      "priority": 1,
      "applicant_data": {
        "age": 35,
        "annualIncome": 75000,
        "creditScore": 720,
        "healthConditions": "good",
        "smoker": false
      },
      "policy_data": {
        "coverageAmount": 500000,
        "termYears": 20,
        "type": "term_life"
      },
      "expected_decision": "approved",
      "expected_reasons": ["Meets all eligibility criteria", "Low risk profile"],
      "expected_risk_category": 2,
      "is_auto_generated": true,
      "generation_method": "llm",
      "created_at": "2025-11-15T10:30:00"
    }
  ],
  "test_cases_count": 7,
  "test_cases_by_category": {
    "positive": 3,
    "negative": 2,
    "boundary": 1,
    "edge_case": 1
  }
}
```

### DatabaseService Methods

```python
# Save multiple test cases
test_case_ids = db_service.save_test_cases(
    bank_id="chase",
    policy_type_id="insurance",
    test_cases=[...],
    document_hash="abc123...",
    source_document="s3://..."
)

# Get test cases
test_cases = db_service.get_test_cases(
    bank_id="chase",
    policy_type_id="insurance",
    category="positive"  # Optional filter
)

# Get single test case
test_case = db_service.get_test_case_by_id(test_case_id=1)

# Save test execution
execution_id = db_service.save_test_execution(
    test_case_id=1,
    execution_data={
        "execution_id": "uuid-123",
        "actual_decision": "approved",
        "test_passed": True,
        ...
    }
)

# Get execution history
executions = db_service.get_test_executions(
    test_case_id=1,
    limit=10
)

# Get summary statistics
summary = db_service.get_test_case_summary(
    bank_id="chase",
    policy_type_id="insurance"
)
```

---

## TestCaseGenerator Class

### Overview

The `TestCaseGenerator` class uses LLM to automatically generate test cases based on policy documents and extracted rules.

### Usage

```python
from TestCaseGenerator import TestCaseGenerator
from CreateLLM import create_llm

# Initialize
llm = create_llm()
generator = TestCaseGenerator(llm)

# Generate test cases
test_cases = generator.generate_test_cases(
    policy_text="Full policy document text...",
    extracted_rules=[...],  # Optional
    hierarchical_rules=[...],  # Optional
    policy_type="insurance"
)
```

### Methods

**generate_test_cases()**
- Main method to generate test cases
- Returns list of test case dictionaries
- Handles LLM errors with fallback templates

**_build_rules_context()**
- Builds context string from extracted and hierarchical rules
- Limits to 20 extracted rules and 10 hierarchical rules

**_create_test_generation_prompt()**
- Creates specialized LLM prompt for test generation
- Includes policy text and rules context

**_parse_test_cases()**
- Parses JSON response from LLM
- Handles markdown code blocks
- Adds metadata flags

**_generate_default_test_cases()**
- Fallback method when LLM fails
- Returns template-based test cases

---

## Migration Files

### Forward Migration

**File**: `db/migrations/004_create_test_cases_table.sql`

Creates:
- `test_cases` table
- `test_case_executions` table
- `test_case_summary` view
- Indexes for performance
- Sample test case data

Run migration:
```bash
psql -U your_username -d your_database -f db/migrations/004_create_test_cases_table.sql
```

### Rollback Migration

**File**: `db/migrations/004_rollback_test_cases_table.sql`

Drops all test case-related objects.

Run rollback:
```bash
psql -U your_username -d your_database -f db/migrations/004_rollback_test_cases_table.sql
```

---

## Workflow Response

### Processing Response

When processing a policy with `POST /process_policy_from_s3`, the response now includes:

```json
{
  "status": "completed",
  "steps": {
    "generate_test_cases": {
      "status": "success",
      "count": 7,
      "test_case_ids": [1, 2, 3, 4, 5, 6, 7],
      "categories": {
        "positive": 3,
        "negative": 2,
        "boundary": 1,
        "edge_case": 1
      }
    }
  }
}
```

---

## Benefits

### 1. Automated Testing
- No manual test case creation required
- Comprehensive coverage automatically
- Time savings for QA teams

### 2. Policy-Aware Tests
- LLM analyzes actual policy rules
- Tests reflect real business logic
- Context-specific scenarios

### 3. Continuous Validation
- Track test results over time
- Identify rule regressions
- Monitor pass rates

### 4. Multi-Tenant Support
- Separate test cases per bank+policy
- Isolated test execution
- Independent test histories

### 5. Traceability
- Link test cases to policy documents via hash
- Audit trail of test executions
- Performance metrics

---

## Example Use Cases

### Use Case 1: Policy Processing

```bash
curl -X POST "http://localhost:9000/rule-agent/process_policy_from_s3" \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "s3://bucket/chase_insurance_policy.pdf",
    "bank_id": "chase",
    "policy_type": "insurance"
  }'
```

**Result**:
- Policy processed
- Rules generated
- **7 test cases automatically created**
- Test cases saved to database

### Use Case 2: View Generated Test Cases

```python
# Get all test cases for chase insurance
test_cases = db_service.get_test_cases(
    bank_id="chase",
    policy_type_id="insurance"
)

for tc in test_cases:
    print(f"{tc['test_case_name']} ({tc['category']})")
    print(f"  Priority: {tc['priority']}")
    print(f"  Expected: {tc['expected_decision']}")
```

### Use Case 3: Execute Test Cases

```python
# Run a test case
test_case = db_service.get_test_case_by_id(1)

# Call evaluation API with test data
response = evaluate_policy(
    bank_id=test_case['bank_id'],
    policy_type_id=test_case['policy_type_id'],
    applicant=test_case['applicant_data'],
    policy=test_case['policy_data']
)

# Compare expected vs actual
test_passed = response['decision']['approved'] == (test_case['expected_decision'] == 'approved')

# Save execution results
db_service.save_test_execution(
    test_case_id=1,
    execution_data={
        "execution_id": str(uuid.uuid4()),
        "actual_decision": response['decision']['approved'],
        "test_passed": test_passed,
        ...
    }
)
```

### Use Case 4: View Test Statistics

```python
# Get summary statistics
summary = db_service.get_test_case_summary(
    bank_id="chase",
    policy_type_id="insurance"
)

for s in summary:
    print(f"{s['test_case_name']}")
    print(f"  Executions: {s['total_executions']}")
    print(f"  Pass Rate: {s['pass_rate']}%")
    print(f"  Last Run: {s['last_execution_at']}")
```

---

## Best Practices

### 1. Review Generated Tests
- LLM-generated tests should be reviewed
- Verify expected results are correct
- Adjust priority as needed

### 2. Run Tests Regularly
- Execute test cases after rule changes
- Monitor pass rates over time
- Investigate failures promptly

### 3. Update Test Cases
- Keep tests in sync with policy changes
- Use document hash to track versions
- Soft-delete obsolete tests (is_active=false)

### 4. Mix Auto and Manual Tests
- LLM generates good baseline coverage
- Add manual tests for specific edge cases
- Use generation_method to distinguish

### 5. Monitor Performance
- Track execution_time_ms
- Optimize slow tests
- Set appropriate timeouts

---

## Future Enhancements

### 1. Test Execution API
- Endpoint to run all test cases
- Batch execution support
- Scheduled test runs

### 2. Test Coverage Analysis
- Map tests to specific rules
- Identify untested rules
- Coverage percentage reporting

### 3. Test Case Templates
- Predefined templates per industry
- Quick test generation without LLM
- Customizable parameters

### 4. CI/CD Integration
- Automated test runs on deployment
- Fail deployment if tests fail
- Test results in deployment logs

### 5. Test Case Recommendations
- LLM suggests missing test scenarios
- Identifies gaps in coverage
- Auto-generates regression tests

---

## File References

**Database:**
- [db/migrations/004_create_test_cases_table.sql](db/migrations/004_create_test_cases_table.sql) - Forward migration
- [db/migrations/004_rollback_test_cases_table.sql](db/migrations/004_rollback_test_cases_table.sql) - Rollback migration

**Code:**
- [rule-agent/TestCaseGenerator.py](rule-agent/TestCaseGenerator.py) - Test generation logic
- [rule-agent/DatabaseService.py](rule-agent/DatabaseService.py) - Database methods (lines 301-395)
- [rule-agent/UnderwritingWorkflow.py](rule-agent/UnderwritingWorkflow.py) - Integration (Step 4.7)

**Models:**
- TestCase - Line 301 in DatabaseService.py
- TestCaseExecution - Line 354 in DatabaseService.py

---

## Summary

The Test Cases feature provides **automatic, intelligent test generation** during policy processing, ensuring comprehensive test coverage without manual effort. It integrates seamlessly into the existing workflow, stores results in PostgreSQL, and tracks execution history for continuous validation and quality assurance.

**Key Metrics:**
- ✅ 5-10 test cases generated per policy
- ✅ 4 test categories (positive, negative, boundary, edge)
- ✅ LLM-powered generation with fallback templates
- ✅ Full execution tracking and statistics
- ✅ Multi-tenant support with isolation

**Status:** ✨ Production-Ready!
