# Swagger API Documentation Update - Loan Application Examples

## Summary

Updated [swagger.yaml](rule-agent/swagger.yaml) with comprehensive loan application examples for the `/api/v1/evaluate-policy` endpoint.

## Changes Made

### Added 7 New Loan Application Examples

#### 1. **loan-application** (Approved)
Standard loan application that meets all requirements:
```json
{
  "bank_id": "chase",
  "policy_type": "loan",
  "applicant": {
    "age": 35,
    "annualIncome": 85000,
    "creditScore": 720
  },
  "policy": {
    "loanAmount": 150000,
    "personalGuarantee": false
  }
}
```

#### 2. **loan-application-high-amount** (Approved with Personal Guarantee)
High-value loan requiring personal guarantee:
```json
{
  "bank_id": "chase",
  "policy_type": "loan",
  "applicant": {
    "age": 45,
    "annualIncome": 250000,
    "creditScore": 780
  },
  "policy": {
    "loanAmount": 2000000,
    "personalGuarantee": true
  }
}
```

#### 3. **loan-application-rejected-age** (Rejected - Under 18)
Application rejected due to age requirement:
```json
{
  "bank_id": "chase",
  "policy_type": "loan",
  "applicant": {
    "age": 17,
    "annualIncome": 30000,
    "creditScore": 680
  },
  "policy": {
    "loanAmount": 50000,
    "personalGuarantee": false
  }
}
```

#### 4. **loan-application-rejected-income** (Rejected - Low Income)
Application rejected due to insufficient income:
```json
{
  "bank_id": "chase",
  "policy_type": "loan",
  "applicant": {
    "age": 28,
    "annualIncome": 20000,
    "creditScore": 680
  },
  "policy": {
    "loanAmount": 50000,
    "personalGuarantee": false
  }
}
```
**Rejection Reason**: "Applicant's annual income is less than $25,000"

#### 5. **loan-application-rejected-credit** (Rejected - Credit Score)
Application rejected due to insufficient credit score:
```json
{
  "bank_id": "chase",
  "policy_type": "loan",
  "applicant": {
    "age": 35,
    "annualIncome": 60000,
    "creditScore": 590
  },
  "policy": {
    "loanAmount": 100000,
    "personalGuarantee": false
  }
}
```
**Rejection Reason**: Credit score must be 620 or higher

#### 6. **loan-application-rejected-no-guarantee** (Rejected - Missing Personal Guarantee)
Application rejected for high amount without personal guarantee:
```json
{
  "bank_id": "chase",
  "policy_type": "loan",
  "applicant": {
    "age": 40,
    "annualIncome": 120000,
    "creditScore": 750
  },
  "policy": {
    "loanAmount": 500000,
    "personalGuarantee": false
  }
}
```
**Rejection Reason**: Loan amount exceeds $250,000 and requires personal guarantee

#### 7. **loan-application-rejected-amount-limit** (Rejected - Exceeds Maximum)
Application rejected for exceeding maximum loan amount:
```json
{
  "bank_id": "chase",
  "policy_type": "loan",
  "applicant": {
    "age": 50,
    "annualIncome": 500000,
    "creditScore": 800
  },
  "policy": {
    "loanAmount": 6000000,
    "personalGuarantee": true
  }
}
```
**Rejection Reason**: Loan amount exceeds maximum limit of $5,000,000

## Loan Underwriting Rules (Chase)

Based on the deployed `chase-loan-underwriting-rules` container on port **8083**:

### Requirements

| Rule | Requirement | Rejection Reason |
|------|-------------|------------------|
| **Age** | Must be 18 or older | "The application will not be approved if the applicant is under 18 years old" |
| **Income** | Annual income ≥ $25,000 | "Applicant's annual income is less than $25,000" |
| **Credit Score** | Credit score ≥ 620 | "Applicant's credit score is insufficient" |
| **Loan Amount** | Maximum $5,000,000 | "Loan amount exceeds the maximum loan amount limit" |
| **Personal Guarantee** | Required if amount > $250,000 | "Loan amount exceeds $250,000 and requires personal guarantee" |

## Deployed Containers Status

All three Drools containers running successfully:

| Container | Bank | Policy Type | Port | Status |
|-----------|------|-------------|------|--------|
| drools | (main) | all | 8080 | ✅ Healthy |
| drools-tb-insurance-underwriting-rules | tb | insurance | 8081 | ✅ Healthy |
| drools-chase-insurance-underwriting-rules | chase | insurance | 8082 | ✅ Healthy |
| drools-chase-loan-underwriting-rules | chase | loan | 8083 | ✅ Healthy |

## API Testing

### Test Approved Loan Application
```bash
curl -X POST http://localhost:9000/rule-agent/api/v1/evaluate-policy \
  -H "Content-Type: application/json" \
  -d '{
    "bank_id": "chase",
    "policy_type": "loan",
    "applicant": {
      "age": 35,
      "annualIncome": 85000,
      "creditScore": 720
    },
    "policy": {
      "loanAmount": 150000,
      "personalGuarantee": false
    }
  }'
```

**Response**:
```json
{
  "status": "success",
  "bank_id": "chase",
  "policy_type": "loan",
  "container_id": "chase-loan-underwriting-rules",
  "decision": {
    "approved": true,
    "reasons": [],
    "requiresManualReview": false,
    "applicant": {...},
    "policy": {...}
  },
  "execution_time_ms": 325
}
```

### Test Rejected Loan Application (Low Income)
```bash
curl -X POST http://localhost:9000/rule-agent/api/v1/evaluate-policy \
  -H "Content-Type: application/json" \
  -d '{
    "bank_id": "chase",
    "policy_type": "loan",
    "applicant": {
      "age": 35,
      "annualIncome": 20000,
      "creditScore": 720
    },
    "policy": {
      "loanAmount": 50000,
      "personalGuarantee": false
    }
  }'
```

**Response**:
```json
{
  "status": "success",
  "bank_id": "chase",
  "policy_type": "loan",
  "container_id": "chase-loan-underwriting-rules",
  "decision": {
    "approved": false,
    "reasons": ["Applicant's annual income is less than $25,000"],
    "requiresManualReview": false,
    "applicant": {...},
    "policy": {...}
  },
  "execution_time_ms": 49
}
```

## Files Modified

- **[rule-agent/swagger.yaml](rule-agent/swagger.yaml#L255-L338)**: Added 7 loan application examples to `/api/v1/evaluate-policy` endpoint

## Data Model

### Applicant Object (Loan)
```typescript
{
  age: number;           // Must be ≥ 18
  annualIncome: number;  // Must be ≥ $25,000
  creditScore: number;   // Must be ≥ 620
}
```

### Policy Object (Loan)
```typescript
{
  loanAmount: number;          // Must be ≤ $5,000,000
  personalGuarantee: boolean;  // Required if loanAmount > $250,000
}
```

### Decision Object (Response)
```typescript
{
  approved: boolean;
  reasons: string[];
  requiresManualReview: boolean;
  applicant: {...};
  policy: {...};
}
```

## Comparison: Insurance vs Loan Applications

### Insurance Application Fields
```json
{
  "applicant": {
    "age": 35,
    "annualIncome": 75000,
    "creditScore": 720,
    "healthConditions": "good",  // ← Insurance-specific
    "smoker": false               // ← Insurance-specific
  },
  "policy": {
    "coverageAmount": 500000,     // ← Insurance-specific
    "termYears": 20,              // ← Insurance-specific
    "type": "term_life"           // ← Insurance-specific
  }
}
```

### Loan Application Fields
```json
{
  "applicant": {
    "age": 35,
    "annualIncome": 85000,
    "creditScore": 720
    // No health/smoking fields
  },
  "policy": {
    "loanAmount": 150000,          // ← Loan-specific
    "personalGuarantee": false     // ← Loan-specific
  }
}
```

## Benefits

1. **Complete API Documentation**: Developers can see exactly what fields are required for loan applications
2. **Example-Driven Development**: 7 different scenarios covering approval, rejection, and edge cases
3. **Clear Requirements**: Each rejection example shows what rule was violated
4. **Multi-Tenant Support**: Demonstrates bank_id + policy_type routing to correct container
5. **Testable**: All examples are copy-paste ready for testing

## Next Steps

Developers can now:
1. View Swagger UI at the appropriate endpoint
2. Try out different loan application scenarios directly from the documentation
3. Understand the exact data model required for loan underwriting
4. Compare insurance vs loan application structures
5. Test edge cases and rejection scenarios
