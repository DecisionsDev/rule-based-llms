# API Field Naming Conventions

## Important: Field Names Must Match DRL Declarations

When calling the `/api/v1/evaluate-policy` endpoint, **field names in your JSON request must exactly match the field names declared in the DRL rules**.

## Why This Matters

The Drools rule engine uses Java POJOs generated from DRL `declare` statements. For proper deserialization, JSON field names must match the Java field names (which are generated from DRL declarations).

## Current Field Names for Insurance Policies

### Applicant Object

Based on the DRL declaration:
```drl
declare Applicant
    name: String
    age: int
    occupation: String
    healthConditions: String
    creditScore: int
    annualIncome: double
    smoker: boolean
end
```

**Correct field names (camelCase):**
```json
{
  "applicant": {
    "name": "John Doe",
    "age": 35,
    "occupation": "Engineer",
    "healthConditions": "good",
    "creditScore": 720,
    "annualIncome": 75000,
    "smoker": false
  }
}
```

**Incorrect field names (snake_case) - WILL NOT WORK:**
```json
{
  "applicant": {
    "health_status": "good",      ❌ Use "healthConditions"
    "credit_score": 720,           ❌ Use "creditScore"
    "annual_income": 75000,        ❌ Use "annualIncome"
    "income": 75000                ❌ Use "annualIncome"
  }
}
```

### Policy Object

Based on the DRL declaration:
```drl
declare Policy
    policyType: String
    coverageAmount: double
    term: int
end
```

**Correct field names:**
```json
{
  "policy": {
    "policyType": "term_life",
    "coverageAmount": 500000,
    "term": 20
  }
}
```

**Note:** The example also shows alternative fields like `termYears` and `type` being used in practice - verify with your actual DRL file which fields are expected.

## Complete Working Example

```json
{
  "bank_id": "chase",
  "policy_type": "insurance",
  "applicant": {
    "age": 35,
    "annualIncome": 75000,
    "creditScore": 720,
    "healthConditions": "good",
    "smoker": false
  },
  "policy": {
    "coverageAmount": 500000,
    "termYears": 20,
    "type": "term_life"
  }
}
```

### Expected Response (Approved)
```json
{
  "bank_id": "chase",
  "container_id": "chase-insurance-underwriting-rules",
  "decision": {
    "approved": true,
    "reason": "Application meets all requirements",
    "requiresManualReview": false,
    "premiumMultiplier": 1.0
  },
  "status": "success"
}
```

## Rejection Examples

### Example 1: Age Too High
```json
{
  "applicant": {
    "age": 70,  // > 65, will be rejected
    "annualIncome": 75000,
    "creditScore": 720,
    "healthConditions": "good",
    "smoker": false
  }
}
```

**Response:**
```json
{
  "decision": {
    "approved": false,
    "reason": "Applicant age is outside acceptable range"
  }
}
```

### Example 2: Credit Score Too Low
```json
{
  "applicant": {
    "age": 35,
    "annualIncome": 75000,
    "creditScore": 550,  // < 600, will be rejected
    "healthConditions": "good",
    "smoker": false
  }
}
```

**Response:**
```json
{
  "decision": {
    "approved": false,
    "reason": "Applicant credit score is below minimum requirement"
  }
}
```

### Example 3: Income Too Low
```json
{
  "applicant": {
    "age": 35,
    "annualIncome": 20000,  // < 25000, will be rejected
    "creditScore": 720,
    "healthConditions": "good",
    "smoker": false
  }
}
```

**Response:**
```json
{
  "decision": {
    "approved": false,
    "reason": "Applicant annual income is below minimum requirement"
  }
}
```

### Example 4: Coverage Too High Relative to Income
```json
{
  "applicant": {
    "age": 35,
    "annualIncome": 50000,
    "creditScore": 720,
    "healthConditions": "good",
    "smoker": false
  },
  "policy": {
    "coverageAmount": 600000  // > 10x income (500,000), will be rejected
  }
}
```

**Response:**
```json
{
  "decision": {
    "approved": false,
    "reason": "Coverage amount is outside acceptable range"
  }
}
```

## Troubleshooting

### Symptom: Getting unexpected rejections
**Cause:** Field names don't match DRL declarations, so values aren't being read by rules.

**Solution:** Check your DRL file and ensure JSON field names exactly match the declared field names.

### How to Check Your DRL File

1. Find your deployed DRL file in S3 or the database
2. Look for `declare` statements
3. Use those exact field names in your JSON requests

### Example DRL Check
```bash
# Get the DRL file from S3
aws s3 cp s3://uw-data-extraction/generated-rules/chase-insurance-underwriting-rules/latest/*.drl - | grep -A 10 "declare Applicant"
```

## Best Practices

1. **Always use camelCase** for field names (matches Java conventions)
2. **Verify field names** against the actual DRL file for your policy
3. **Test with known values** before integrating
4. **Check the response** - if fields are missing from the decision object, they weren't properly deserialized

## Updated Documentation

The swagger documentation at `/rule-agent/docs` has been updated with correct examples showing the proper field names.
