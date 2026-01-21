# Field Naming Issue Fixed

## Problem
Your rejection was caused by **incorrect field names** in the request JSON. The DRL-declared types expect specific field names, and when they don't match, the fields arrive as null/0, triggering unexpected rule behavior.

## Root Cause
Your request used:
- `termYears` (should be `term`)
- `type` (should be `policyType`)

The DRL declarations define:
```drl
declare Policy
    policyType: String
    coverageAmount: double
    term: int
end
```

When JSON field names don't match, Jackson deserialization fails silently, leaving those fields null/0.

## Solution Applied

### 1. Identified Correct Field Names
From the DRL `declare` statements:

**Applicant fields:**
- age (int)
- annualIncome (double) - NOT "income"
- creditScore (int) - NOT "credit_score"
- healthConditions (String) - NOT "health_status"
- smoker (boolean)

**Policy fields:**
- term (int) - NOT "termYears"
- policyType (String) - NOT "type"
- coverageAmount (double)

### 2. Fixed Dedicated Container Deployment
The system was routing to the dedicated Drools container (`drools-chase-insurance-underwriting-rules`) but the KJar wasn't deployed there. Fixed by:
- Copying KJar from main drools container to dedicated container's Maven repository
- Deploying the container with the correct KJar version

### 3. Verified All Rules Work

**Test 1: Valid Application (Should Approve)**
```json
{
  "applicant": {
    "age": 35,
    "annualIncome": 75000,
    "creditScore": 720,
    "healthConditions": "good",
    "smoker": false
  },
  "policy": {
    "term": 20,
    "policyType": "term_life",
    "coverageAmount": 500000
  }
}
```
**Result:** ✓ Approved

**Test 2: Age Too High (Should Reject)**
```json
{
  "applicant": {
    "age": 70,  // > 65
    ...
  }
}
```
**Result:** ✓ Rejected - "Applicant age is outside acceptable range"

**Test 3: Credit Score Too Low (Should Reject)**
```json
{
  "applicant": {
    "creditScore": 550,  // < 600
    ...
  }
}
```
**Result:** ✓ Rejected - "Applicant credit score is below minimum requirement"

## What You Need to Change

Update your requests to use the **correct field names**:

### Before (Incorrect):
```json
{
  "policy": {
    "termYears": 20,        ❌
    "type": "term_life",    ❌
    "coverageAmount": 500000
  }
}
```

### After (Correct):
```json
{
  "policy": {
    "term": 20,             ✓
    "policyType": "term_life",  ✓
    "coverageAmount": 500000
  }
}
```

## Complete Working Request

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
    "term": 20,
    "policyType": "term_life"
  }
}
```

## Reference Documentation

See [API_FIELD_NAMING_CONVENTIONS.md](API_FIELD_NAMING_CONVENTIONS.md) for comprehensive field naming guidelines and more examples.

## System Status

✓ Java POJO generation working
✓ Container orchestration routing correctly
✓ Dedicated Drools container deployed with KJar
✓ All underwriting rules validated
✓ Field deserialization working correctly
