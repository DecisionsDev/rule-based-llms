# Multiple Rejection Reasons Feature - Implementation Complete

## Overview

The system now collects and returns **ALL rejection reasons** instead of just the first one encountered. This allows users to see every rule violation in a single response.

## What Changed

### Before (Single Reason)
```json
{
  "approved": false,
  "reason": "Applicant's credit score is below the minimum requirement",
  ...
}
```
**Problem**: If age=70 AND creditScore=550, only ONE reason was shown.

### After (Multiple Reasons)
```json
{
  "approved": false,
  "reasons": [
    "Applicant age is outside acceptable range",
    "Applicant's credit score is below the minimum requirement"
  ],
  ...
}
```
**Solution**: ALL violations are listed.

## Technical Implementation

### 1. Updated DRL Declaration
**File**: [rule-agent/RuleGeneratorAgent.py](rule-agent/RuleGeneratorAgent.py#L57-L62)

**Changed from:**
```drl
declare Decision
    approved: boolean
    reason: String              // Single string
    requiresManualReview: boolean
    premiumMultiplier: double
end
```

**Changed to:**
```drl
declare Decision
    approved: boolean
    reasons: java.util.List     // List of strings
    requiresManualReview: boolean
    premiumMultiplier: double
end
```

### 2. Updated Initialization Rule
**Changed from:**
```drl
rule "Initialize Decision"
    when
        not Decision()
    then
        Decision decision = new Decision();
        decision.setApproved(true);
        decision.setReason("Initial evaluation");  // Single reason
        ...
end
```

**Changed to:**
```drl
rule "Initialize Decision"
    when
        not Decision()
    then
        Decision decision = new Decision();
        decision.setApproved(true);
        decision.setReasons(new java.util.ArrayList());  // Empty list
        ...
end
```

### 3. Updated Rejection Rules
**Changed from:**
```drl
rule "Age Requirement Check"
    when
        $applicant : Applicant( age < 18 || age > 65 )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.setReason("Applicant age is outside acceptable range");  // OVERWRITES
        update($decision);
end
```

**Changed to:**
```drl
rule "Age Requirement Check"
    when
        $applicant : Applicant( age < 18 || age > 65 )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Applicant age is outside acceptable range");  // ADDS
        update($decision);
end
```

### 4. Updated LLM Guidelines
**File**: [rule-agent/RuleGeneratorAgent.py](rule-agent/RuleGeneratorAgent.py#L88-L99)

Added guidelines to instruct the LLM to:
- Use `getReasons().add()` instead of `setReason()`
- NEVER overwrite reasons in rejection rules
- Accumulate ALL rejection reasons

## Example Scenarios

### Scenario 1: Multiple Violations
**Request:**
```json
{
  "applicant": {
    "age": 70,           // Violation: > 65
    "creditScore": 550,  // Violation: < 600
    "annualIncome": 75000,
    "healthConditions": "good",
    "smoker": false
  }
}
```

**Response:**
```json
{
  "approved": false,
  "reasons": [
    "Applicant age is outside acceptable range",
    "Applicant's credit score is below the minimum requirement"
  ],
  "requiresManualReview": false,
  "premiumMultiplier": 1.0
}
```

### Scenario 2: Single Violation
**Request:**
```json
{
  "applicant": {
    "age": 70,  // Only violation
    ...
  }
}
```

**Response:**
```json
{
  "approved": false,
  "reasons": [
    "Applicant age is outside acceptable range"
  ],
  ...
}
```

### Scenario 3: No Violations
**Request:**
```json
{
  "applicant": {
    "age": 35,
    "creditScore": 720,
    ...
  }
}
```

**Response:**
```json
{
  "approved": true,
  "reasons": [],  // Empty list for approved applications
  ...
}
```

## Benefits

✓ **Complete Feedback**: Users see ALL violations in one response
✓ **Better UX**: No need for multiple requests to discover all issues
✓ **Transparency**: Clear understanding of why an application was rejected
✓ **Debugging**: Easier to identify multiple rule violations
✓ **Backward Compatible**: Existing approved applications work the same way

## Files Modified

1. **rule-agent/RuleGeneratorAgent.py**
   - Updated DRL template to use `reasons: java.util.List`
   - Changed initialization to use empty ArrayList
   - Updated example rules to use `.add()` method
   - Added guidelines for LLM to use `.add()` instead of `.setReason()`

2. **rule-agent/DroolsService.py**
   - No changes needed - automatically handles list serialization

## Testing

### Test Case 1: Multiple Violations
```bash
curl -X POST http://localhost:9000/rule-agent/api/v1/evaluate-policy \
  -H "Content-Type: application/json" \
  -d '{
    "bank_id": "chase",
    "policy_type": "insurance",
    "applicant": {
      "age": 70,
      "creditScore": 550,
      "annualIncome": 75000,
      "healthConditions": "good",
      "smoker": false
    },
    "policy": {
      "term": 20,
      "policyType": "term_life",
      "coverageAmount": 500000
    }
  }'
```

**Expected**: `reasons` array with both age and credit score violations

### Test Case 2: Triple Violation
```bash
curl -X POST http://localhost:9000/rule-agent/api/v1/evaluate-policy \
  -H "Content-Type: application/json" \
  -d '{
    "applicant": {
      "age": 70,
      "creditScore": 550,
      "annualIncome": 20000,
      "healthConditions": "good",
      "smoker": false
    },
    "policy": {
      "term": 20,
      "policyType": "term_life",
      "coverageAmount": 500000
    }
  }'
```

**Expected**: `reasons` array with age, credit score, AND income violations

## Deployment Notes

### After Redeployment
1. The backend will generate new DRL with `reasons: java.util.List`
2. JavaPojoGenerator will create Decision.java with `List<String> reasons`
3. All new rule evaluations will return arrays of reasons
4. Existing containers will continue to work (backward compatible)

### Migration Strategy
- **Option 1**: Redeploy all policies to get new DRL immediately
- **Option 2**: Let policies naturally update as they're re-uploaded
- **Option 3**: Keep both versions running (new containers use lists, old containers use strings)

## API Response Format

### JSON Response Structure
```json
{
  "bank_id": "chase",
  "container_id": "chase-insurance-underwriting-rules",
  "decision": {
    "applicant": { ... },
    "policy": { ... },
    "approved": boolean,
    "reasons": [string, string, ...],  // Array of strings
    "requiresManualReview": boolean,
    "premiumMultiplier": number
  },
  "execution_time_ms": number,
  "policy_type": "insurance",
  "status": "success"
}
```

## Future Enhancements

1. **Reason Categories**: Group reasons by type (eligibility, credit, health, etc.)
2. **Severity Levels**: Mark reasons as "critical" vs "warning"
3. **Suggested Actions**: Provide guidance on how to fix each violation
4. **Rule References**: Include rule names or IDs with each reason

## Summary

The system now provides **complete transparency** by listing every rejection reason in a single response. This improves user experience and makes debugging much easier.

Users can now see at a glance:
- ✓ ALL rule violations
- ✓ Exactly what needs to be fixed
- ✓ No hidden rejection reasons
