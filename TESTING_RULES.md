# Testing Drools Rules - API Guide

This guide shows how to test the deployed Drools underwriting rules using the `/rule-agent/test_rules` endpoint.

## Endpoint

```
POST http://localhost:9000/rule-agent/test_rules
Content-Type: application/json
```

## Request Body Format

```json
{
  "container_id": "chase-insurance-underwriting-rules",
  "applicant": {
    "name": "John Doe",
    "age": 35,
    "occupation": "Engineer",
    "healthConditions": null
  },
  "policy": {
    "policyType": "Term Life",
    "coverageAmount": 500000,
    "term": 20
  }
}
```

## Response Format

```json
{
  "status": "success",
  "container_id": "chase-insurance-underwriting-rules",
  "decision": {
    "approved": true,
    "reason": "Initial evaluation",
    "requiresManualReview": false,
    "premiumMultiplier": 1.0
  }
}
```

## Test Scenarios

### 1. Valid Applicant (Age 35, No Health Issues, Normal Coverage)

**Expected Result**: Approved

```bash
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d '{
    "container_id": "chase-insurance-underwriting-rules",
    "applicant": {
      "name": "John Doe",
      "age": 35,
      "occupation": "Engineer",
      "healthConditions": null
    },
    "policy": {
      "policyType": "Term Life",
      "coverageAmount": 500000,
      "term": 20
    }
  }'
```

### 2. Applicant Too Young (Age 17)

**Expected Result**: Rejected - Age requirement check

```bash
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d '{
    "container_id": "chase-insurance-underwriting-rules",
    "applicant": {
      "name": "Jane Smith",
      "age": 17,
      "occupation": "Student",
      "healthConditions": null
    },
    "policy": {
      "policyType": "Term Life",
      "coverageAmount": 100000,
      "term": 10
    }
  }'
```

### 3. Applicant Too Old (Age 70)

**Expected Result**: Rejected - Age requirement check

```bash
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d '{
    "container_id": "chase-insurance-underwriting-rules",
    "applicant": {
      "name": "Bob Senior",
      "age": 70,
      "occupation": "Retired",
      "healthConditions": null
    },
    "policy": {
      "policyType": "Term Life",
      "coverageAmount": 250000,
      "term": 10
    }
  }'
```

### 4. Applicant with Health Conditions

**Expected Result**: Rejected - Health condition check

```bash
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d '{
    "container_id": "chase-insurance-underwriting-rules",
    "applicant": {
      "name": "Alice Johnson",
      "age": 45,
      "occupation": "Teacher",
      "healthConditions": "Diabetes"
    },
    "policy": {
      "policyType": "Term Life",
      "coverageAmount": 300000,
      "term": 20
    }
  }'
```

### 5. High Coverage Amount (Over $1M)

**Expected Result**: Rejected - Coverage amount too high

```bash
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d '{
    "container_id": "chase-insurance-underwriting-rules",
    "applicant": {
      "name": "Rich Person",
      "age": 40,
      "occupation": "CEO",
      "healthConditions": null
    },
    "policy": {
      "policyType": "Whole Life",
      "coverageAmount": 2000000,
      "term": 30
    }
  }'
```

### 6. Edge Case - Age 18 (Minimum)

**Expected Result**: Approved

```bash
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d '{
    "container_id": "chase-insurance-underwriting-rules",
    "applicant": {
      "name": "Young Adult",
      "age": 18,
      "occupation": "College Student",
      "healthConditions": null
    },
    "policy": {
      "policyType": "Term Life",
      "coverageAmount": 100000,
      "term": 20
    }
  }'
```

### 7. Edge Case - Age 65 (Maximum)

**Expected Result**: Approved

```bash
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d '{
    "container_id": "chase-insurance-underwriting-rules",
    "applicant": {
      "name": "Senior Citizen",
      "age": 65,
      "occupation": "Consultant",
      "healthConditions": null
    },
    "policy": {
      "policyType": "Term Life",
      "coverageAmount": 500000,
      "term": 10
    }
  }'
```

## Understanding the Decision Object

The `decision` object in the response contains:

- **approved** (boolean): Whether the application is approved
- **reason** (string): Explanation for the decision
- **requiresManualReview** (boolean): Whether manual review is needed
- **premiumMultiplier** (double): Multiplier for premium calculation (1.0 = standard rate)

## Rules Summary

Based on the generated DRL rules, the following checks are performed:

1. **Initialize Decision**: Creates the initial decision object with default approval
2. **Age Requirement Check**: Rejects if age < 18 or age > 65
3. **Health Condition Check**: Rejects if healthConditions is not null
4. **Policy Coverage Amount Check**: Rejects if coverageAmount > $1,000,000

## Troubleshooting

### Container Not Found
If you get a "container not found" error, list available containers:

```bash
curl http://localhost:9000/rule-agent/drools_containers
```

### Check Container Status
```bash
curl "http://localhost:9000/rule-agent/drools_container_status?container_id=chase-insurance-underwriting-rules"
```

### View Backend Logs
```bash
docker-compose logs backend
```

## Using Test Files

Save test data to a JSON file:

```bash
# Create test file
cat > test_valid.json <<EOF
{
  "container_id": "chase-insurance-underwriting-rules",
  "applicant": {
    "name": "John Doe",
    "age": 35,
    "occupation": "Engineer",
    "healthConditions": null
  },
  "policy": {
    "policyType": "Term Life",
    "coverageAmount": 500000,
    "term": 20
  }
}
EOF

# Test with file
curl -X POST http://localhost:9000/rule-agent/test_rules \
  -H "Content-Type: application/json" \
  -d @test_valid.json
```
