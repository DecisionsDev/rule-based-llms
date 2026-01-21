# Drools Field Mapping Issue

## Problem

When evaluating policies through the Drools KIE Server, only some fields from the JSON payload are being populated in the Drools fact objects, causing rules to not fire correctly.

### Example

**Request:**
```json
{
  "applicant": {
    "age": 35,
    "annualIncome": 75000,
    "creditScore": 550,
    "healthConditions": "good",
    "smoker": false
  }
}
```

**Expected:** Credit score rule should fire (creditScore < 600)
**Actual:** Age rule fires instead with incorrect reason

**Drools Working Memory shows:**
```
'com.underwriting.rules.Applicant': {
  'name': None,
  'age': 35,  // ✓ Populated
  'occupation': None,
  'healthConditions': 'good',  // ✓ Populated
  'smoker': False,  // ✓ Populated
  'creditScore': <MISSING>,  // ✗ Not populated
  'annualIncome': <MISSING>,  // ✗ Not populated
  'tier': 0
}
```

## Root Cause

The DRL file uses `declare` statements to define fact types:

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

However, **Drools cannot properly deserialize JSON into declared types** without backing Java POJO classes. The `declare` statement creates a runtime type, but JSON deserialization requires actual Java classes with proper getters/setters that follow Java bean conventions.

## Current Deployment

The JAR file (`chase-insurance-underwriting-rules_*.jar`) only contains:
- `rules/underwriting-rules.drl` (DRL rules file)
- **NO** Java `.class` files

## Solution Options

### Option 1: Generate Java POJOs (Recommended)

Generate Java POJO classes for all declared types and include them in the deployment JAR.

**Steps:**
1. Parse the DRL `declare` statements
2. Generate corresponding Java classes:
   ```java
   package com.underwriting.rules;

   public class Applicant implements java.io.Serializable {
       private String name;
       private int age;
       private String occupation;
       private String healthConditions;
       private int creditScore;
       private double annualIncome;
       private boolean smoker;

       // Getters and setters for all fields
       public int getCreditScore() { return creditScore; }
       public void setCreditScore(int creditScore) { this.creditScore = creditScore; }
       // ... etc
   }
   ```
3. Compile the Java classes
4. Package them into the JAR along with the DRL file
5. Deploy to Drools KIE Server

### Option 2: Use Maps Instead of Typed Objects

Modify the invocation to use `Map` objects instead of typed facts. This is simpler but loses type safety.

### Option 3: Pre-create POJOs in Separate Module

Create a separate Maven module with hand-coded POJOs that match the DRL declarations, and include it as a dependency.

## Files to Modify

1. **rule-agent/DroolsDeploymentService.py** - Add POJO generation step
2. **rule-agent/UnderwritingWorkflow.py** - Update deployment workflow
3. Add Java code generation utilities

## Impact

Until this is fixed:
- ❌ Credit score validation will not work
- ❌ Income validation will not work
- ❌ Coverage amount vs income ratio check will not work
- ✓ Age validation works (partial)
- ✓ Health conditions check works (partial)
- ✓ Smoker check works (partial)

## Workaround

None currently available without code changes.
