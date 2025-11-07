# Swagger Documentation Update - Test Rules Endpoint

## Summary

Added comprehensive OpenAPI 3.0 documentation for the new `/test_rules` endpoint in `swagger.yaml`.

## Changes Made

### 1. Added New Tag
- **Tag**: `Rule Testing`
- **Description**: Test deployed Drools rules with sample data

### 2. New Endpoint: `/test_rules` (POST)

**Purpose**: Execute Drools rules with sample applicant and policy data to test underwriting decisions

**Operation ID**: `testRules`

### Request Schema

```yaml
required:
  - container_id
  - applicant
  - policy

properties:
  container_id: string (Drools container ID)
  applicant:
    name: string
    age: integer (0-120)
    occupation: string
    healthConditions: string | null
  policy:
    policyType: string
    coverageAmount: number
    term: integer
```

### 7 Test Examples Included

1. **valid-applicant** - Should approve (age 35, healthy, $500K)
2. **too-young** - Should reject (age 17)
3. **too-old** - Should reject (age 70)
4. **health-conditions** - Should reject (Diabetes)
5. **high-coverage** - Should reject ($2M coverage)
6. **edge-case-min-age** - Should approve (age 18, minimum)
7. **edge-case-max-age** - Should approve (age 65, maximum)

### Response Examples

4 response examples covering different decision outcomes:
- **approved** - Application approved
- **rejected-age** - Age outside acceptable range
- **rejected-health** - Health conditions present
- **rejected-coverage** - Coverage amount too high

### 3. New Schema Component: `RuleTestResult`

```yaml
RuleTestResult:
  status: success | error
  container_id: string
  decision:
    approved: boolean
    reason: string
    requiresManualReview: boolean
    premiumMultiplier: number
  full_response: object (for debugging)
```

## How to Use

### View Swagger UI
If your Flask app serves Swagger UI, navigate to:
```
http://localhost:9000/api/docs
```

### Test with Swagger Editor
Copy `swagger.yaml` into [Swagger Editor](https://editor.swagger.io/) to view interactive documentation.

### Test the Endpoint

**Valid Applicant Example**:
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

**Expected Response**:
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

## Validation

✓ YAML syntax validated successfully
✓ All examples include appropriate test data
✓ Request/response schemas properly defined
✓ All HTTP status codes documented (200, 400, 404, 500)

## Related Files

- [swagger.yaml](swagger.yaml) - Complete OpenAPI specification
- [TESTING_RULES.md](../TESTING_RULES.md) - Detailed testing guide with curl examples
- [ChatService.py](ChatService.py) - Implementation of `/test_rules` endpoint
