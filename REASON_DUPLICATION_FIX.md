# Reason Duplication Fix - Session State Issue

## Problem Identified

The system was returning DUPLICATE rejection reasons across multiple evaluation requests:

```json
{
  "approved": false,
  "reasons": [
    "Applicant age is outside acceptable range",
    "Applicant credit score is below minimum requirement",
    "Applicant age is outside acceptable range",
    "Applicant credit score is below minimum requirement",
    "Applicant age is outside acceptable range",
    "Applicant credit score is below minimum requirement"
  ]
}
```

Additionally, valid requests (age=35, creditScore=720) were incorrectly being rejected with reasons from previous requests.

## Root Cause Analysis

### Issue: Stateful Drools Session

The problem was in [rule-agent/DroolsDeploymentService.py:225](rule-agent/DroolsDeploymentService.py#L225):

```xml
<ksession name="ksession-rules" default="true"/>
```

**Without specifying `type`, Drools defaults to STATEFUL sessions**, which means:
- Facts (including Decision objects) persist across multiple requests
- Each new request ADDS to the existing reasons list instead of starting fresh
- The Decision object from previous evaluations is reused

## Solution Applied

### Changed kmodule.xml to Use Stateless Sessions

Modified [rule-agent/DroolsDeploymentService.py:225](rule-agent/DroolsDeploymentService.py#L225):

```xml
<!-- BEFORE (Stateful - causes duplication) -->
<ksession name="ksession-rules" default="true"/>

<!-- AFTER (Stateless - each request is independent) -->
<ksession name="ksession-rules" type="stateless" default="true"/>
```

### What This Fixes

With `type="stateless"`:
1. **Each request gets a fresh working memory** - no fact persistence
2. **Decision object is created NEW for each evaluation** - reasons list starts empty
3. **No cross-request contamination** - previous evaluations don't affect new ones
4. **Correct behavior** - valid applicants are approved, violations are properly detected

## Deployment Steps

1. **Updated Code**: Modified `DroolsDeploymentService.py` to include `type="stateless"`
2. **Rebuilt Backend**: `docker-compose build backend`
3. **Restarted Services**: `docker-compose up -d`
4. **Trigger New Deployment**: Call `/rule-agent/process_policy_from_s3` to regenerate KJar with stateless session

## Expected Behavior After Fix

### Test Case 1: Valid Applicant
```json
{
  "applicant": {
    "age": 35,
    "creditScore": 720,
    "annualIncome": 75000
  }
}
```

**Expected Result**:
```json
{
  "approved": true,
  "reasons": []  // Empty - no violations
}
```

### Test Case 2: Multiple Violations
```json
{
  "applicant": {
    "age": 70,          // Violates: age > 65
    "creditScore": 550, // Violates: score < 600
    "annualIncome": 75000
  }
}
```

**Expected Result**:
```json
{
  "approved": false,
  "reasons": [
    "Applicant age is outside acceptable range",
    "Applicant credit score is below minimum requirement"
  ]  // Exactly 2 reasons, no duplicates
}
```

### Test Case 3: Multiple Sequential Requests
Making the same request 3 times in a row should return **identical results** each time, with no accumulation.

## Stateful vs Stateless Sessions

### Stateful Session (OLD - Problematic)
- Facts persist across `fireAllRules()` calls
- Working memory maintains state
- **Use case**: Long-running business processes, conversations, workflows
- **Problem**: Not suitable for stateless HTTP requests

### Stateless Session (NEW - Correct)
- Each execution is independent
- Working memory is cleared after each execution
- **Use case**: REST APIs, request/response patterns
- **Benefit**: No state leakage between requests

## Files Modified

1. **[rule-agent/DroolsDeploymentService.py](rule-agent/DroolsDeploymentService.py#L225)**: Added `type="stateless"` to ksession definition

## Testing

After the new deployment completes, test with:

```bash
# Test 1: Valid applicant (should approve)
curl -X POST http://localhost:9000/rule-agent/api/v1/evaluate-policy \
  -H "Content-Type: application/json" \
  -d @test_correct_fields.json

# Test 2: Age violation (should show ONE age reason)
curl -X POST http://localhost:9000/rule-agent/api/v1/evaluate-policy \
  -H "Content-Type: application/json" \
  -d @test_age_rejection.json

# Test 3: Credit violation (should show ONE credit reason)
curl -X POST http://localhost:9000/rule-agent/api/v1/evaluate-policy \
  -H "Content-Type: application/json" \
  -d @test_credit_rejection.json

# Test 4: Repeat Test 2 (should show SAME result, no accumulation)
curl -X POST http://localhost:9000/rule-agent/api/v1/evaluate-policy \
  -H "Content-Type: application/json" \
  -d @test_age_rejection.json
```

## Technical Details

### Drools KIE Server Batch Execution
The system uses KIE Server batch command API:

```python
commands = [
    {"insert": {"object": {...}, "out-identifier": "applicant"}},
    {"insert": {"object": {...}, "out-identifier": "policy"}},
    {"fire-all-rules": {"max": -1}},
    {"get-objects": {"out-identifier": "all-facts"}}
]
```

With stateful sessions, the `get-objects` command would return facts from ALL previous requests.
With stateless sessions, it only returns facts from the CURRENT request.

### Why This Issue Wasn't Caught Earlier
- Initial testing was done with SINGLE requests (no duplication visible)
- The duplication only appeared when making MULTIPLE sequential requests
- The system was working correctly for single-shot evaluations

## Prevention

To avoid similar issues in the future:

1. **Always specify session type** in kmodule.xml
2. **Use stateless sessions** for REST API endpoints
3. **Test with sequential requests** to catch state persistence issues
4. **Clear working memory** explicitly if using stateful sessions

## Related Documentation

- [MULTIPLE_REJECTION_REASONS.md](MULTIPLE_REJECTION_REASONS.md) - Multiple reasons feature implementation
- [ISSUE_RESOLUTION_SUMMARY.md](ISSUE_RESOLUTION_SUMMARY.md) - Previous field naming issues
- [CONTAINER_PER_RULESET.md](CONTAINER_PER_RULESET.md) - Container orchestration architecture

## Status

- **Fix Applied**: ✓ `type="stateless"` added to kmodule.xml
- **Backend Rebuilt**: ✓ Docker image updated
- **Containers Started**: ✓ All services running
- **New Deployment**: ✓ Version 20251111.031540 deployed with stateless session
- **Testing Completed**: ✓ All tests passing

## Test Results

### Test 1: Valid Applicant (age=35, creditScore=720)
```json
{
  "approved": true,
  "reasons": []  // ✓ PASS: Empty reasons, no false rejections
}
```

### Test 2: Multiple Violations (age=70, creditScore=550)
```json
{
  "approved": false,
  "reasons": [
    "Applicant age is outside acceptable range",
    "Applicant's credit score is below the minimum requirement"
  ]  // ✓ PASS: Exactly 2 reasons, no duplicates
}
```

### Test 3 & 4: Repeated Requests
- Second request: ✓ Identical - 2 reasons
- Third request: ✓ Identical - 2 reasons
- **No accumulation across requests** ✓

## Conclusion

The stateless session fix has been successfully deployed and verified. The system now:
- ✓ Returns ALL rejection reasons for a single request
- ✓ Does NOT duplicate reasons across multiple requests
- ✓ Correctly approves valid applicants
- ✓ Each request is independent with fresh working memory
