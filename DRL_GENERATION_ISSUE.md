# DRL Generation Issue - Multi-Object Field References

## Problem Summary

When deploying rules for bank `tb`, the Drools KIE Server rejects the generated DRL with a compilation error:

```
Unable to Analyse Expression annualIncome * 10 < coverageAmount:
[Error: unable to resolve method using strict-mode: com.underwriting.rules.Applicant.coverageAmount()]
```

## Root Cause

The LLM-powered rule generator ([RuleGeneratorAgent.py](rule-agent/RuleGeneratorAgent.py)) is creating invalid DRL syntax when it needs to compare fields from **different declared types** (Applicant vs Policy).

### What the LLM Generated (INVALID):
```drl
rule "Coverage Limit vs Income Check"
    when
        $applicant : Applicant( annualIncome * 10 < coverageAmount )  // ERROR!
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Coverage amount exceeds 10x annual income");
        update($decision);
end
```

**Problem**: `coverageAmount` belongs to the `Policy` type, not the `Applicant` type. Drools tries to find `Applicant.getCoverageAmount()` and fails.

### What It Should Generate (VALID):
```drl
rule "Coverage Limit vs Income Check"
    when
        $applicant : Applicant( $income : annualIncome )
        $policy : Policy( coverageAmount > ($income * 10) )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Coverage amount exceeds 10x annual income");
        update($decision);
end
```

**Solution**: Bind `annualIncome` to a variable `$income`, then reference that variable in the Policy constraint.

## Type Declarations

The system uses these declared types:

```drl
declare Applicant
    name: String
    age: int
    creditScore: int
    annualIncome: double
    healthCondition: String
    smoker: boolean
end

declare Policy
    policyType: String
    coverageAmount: double
    term: int
end

declare Decision
    approved: boolean
    reasons: java.util.List
end
```

## Examples from Policy

From the logs, the policy extraction found:
- **Maximum coverage limit**: "10x annual income" (from Q&A extraction)
- **LLM interpretation**: Created a rule checking if `coverageAmount` exceeds `annualIncome * 10`
- **Rule category**: "Coverage Limit" or "Income Requirements"

The rule intent is correct, but the syntax is wrong.

## Fix Required

### Option 1: Improve LLM Prompts

Update [rule-agent/RuleGeneratorAgent.py](rule-agent/RuleGeneratorAgent.py) prompts to include better examples of multi-object field references.

**Current example prompts** at lines 42-85 show:
```drl
rule "Age Requirement Check"
    when
        $applicant : Applicant( age < 18 || age > 65 )
        $decision : Decision()
    then
        //...
end
```

**Need to add examples like**:
```drl
rule "Coverage vs Income Check"
    when
        $applicant : Applicant( $income : annualIncome )
        $policy : Policy( coverageAmount > ($income * 10) )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Coverage exceeds 10x annual income");
        update($decision);
end

rule "Age and Coverage Combined Check"
    when
        $applicant : Applicant( age > 50, $income : annualIncome )
        $policy : Policy( coverageAmount > 500000, coverageAmount > ($income * 5) )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("High coverage requires manual review for age 50+");
        update($decision);
end
```

### Option 2: Post-Generation Validation

Add DRL syntax validation **before** attempting to deploy to Drools:
1. Parse generated DRL
2. Check for field references
3. Validate fields exist on the referenced types
4. If validation fails, re-prompt LLM with error feedback

### Option 3: Structured Rule Template

Instead of free-form DRL generation, use a structured template approach:
- Define rule templates for common patterns
- LLM selects template and fills in parameters
- Templates guarantee syntactically correct DRL

## Impact

**Current Status**:
- ✗ Chase deployment likely works (simpler rules, single-object constraints)
- ✗ TB deployment **FAILS** (has multi-object constraint: income vs coverage)
- ✗ Any bank with income-to-coverage ratio rules will fail
- ✓ KJar builds successfully (Maven compilation happens in backend container)
- ✗ Drools container deployment fails (KIE Server rejects invalid DRL at runtime)

**User Experience**:
- API returns 200 OK with status "partial" or "completed"
- Rules are uploaded to S3
- Database records created
- **But the rules don't actually work** because Drools rejected them

## Related Issues

1. **Directory Creation Issue**: Fixed in [ContainerOrchestrator.py:840-844](rule-agent/ContainerOrchestrator.py#L840-L844) but not yet deployed (backend rebuild pending)
2. **Port Conflict Issue**: Fixed via cleanup in [PORT_CONFLICT_FIX.md](PORT_CONFLICT_FIX.md)

## Files to Modify

1. **[rule-agent/RuleGeneratorAgent.py](rule-agent/RuleGeneratorAgent.py#L42-L85)**:
   - Add multi-object constraint examples to DRL_RULE_GENERATION_PROMPT
   - Add examples showing variable binding syntax
   - Add examples showing cross-object comparisons

2. **[rule-agent/RuleGeneratorAgent.py](rule-agent/RuleGeneratorAgent.py#L220-L330)**:
   - Add validation step before returning generated DRL
   - Check if field names exist in declared types
   - Provide feedback loop if validation fails

## Testing

After fixing the prompt, test with the same TB deployment:

```bash
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "https://uw-data-extraction.s3.us-east-1.amazonaws.com/sample-policies/sample_life_insurance_policy.pdf",
    "policy_type": "insurance",
    "bank_id": "tb"
  }'
```

**Expected**:
- ✓ DRL generation includes proper variable binding
- ✓ Drools deployment succeeds (status 200/201)
- ✓ Container `drools-tb-insurance-underwriting-rules` starts successfully
- ✓ KJar deployed to both main server and dedicated container

## Next Steps

1. Fix LLM prompt in RuleGeneratorAgent.py to include multi-object examples
2. Rebuild backend container to get both fixes:
   - Directory creation fix (already in code)
   - DRL generation fix (pending)
3. Test deployment end-to-end
4. Consider adding DRL validation as a safety check

## Status

- **Issue Identified**: ✓ LLM generating invalid multi-object DRL syntax
- **Root Cause**: ✓ Missing examples in rule generation prompts
- **Fix Designed**: ✓ Add multi-object constraint examples to prompts
- **Fix Applied**: ✗ Pending
- **Testing**: ✗ Blocked by fix implementation
