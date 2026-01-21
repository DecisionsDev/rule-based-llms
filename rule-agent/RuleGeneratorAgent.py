#
#    Copyright 2024 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
from langchain_core.prompts import ChatPromptTemplate
import pandas as pd
from typing import Dict
import json
import os
import io

class RuleGeneratorAgent:
    """
    Converts extracted policy data into Drools rules (DRL format and decision tables)
    """

    def __init__(self, llm, schema: Dict = None):
        self.llm = llm
        self.schema = schema  # Dynamic schema from DynamicSchemaGenerator

        self.rule_generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in insurance underwriting rules and Drools rule engine, specializing in multi-level dependency rules.

Given extracted policy data, generate executable Drools DRL (Drools Rule Language) rules that handle SEQUENTIAL EVALUATION where rules build upon previous outcomes.

IMPORTANT: Use 'declare' statements to define types directly in the DRL file. Do NOT import external Java classes.

=== MULTI-LEVEL DEPENDENCY PATTERNS ===

Many policies require STAGED EVALUATION where:
1. Early rules establish INTERMEDIATE FACTS (CreditTier, RiskCategory)
2. Later rules DEPEND on those facts to make decisions
3. Rules must execute IN ORDER using SALIENCE

The rules should follow this structure for MULTI-LEVEL policies:

```drl
package com.underwriting.rules;

// ============================================================================
// PART 1: DECLARE ALL TYPES (including intermediate facts for multi-level rules)
// ============================================================================

// Main input types
declare Applicant
    name: String
    age: int
    creditScore: int
    health: String  // "excellent", "good", "fair"
    annualIncome: double
    debtToIncomeRatio: double
    smoking: boolean
    occupation: String
    occupationType: String  // "standard", "hazardous"
end

declare Policy
    policyType: String
    coverageAmount: double
    term: int
end

// Intermediate fact types for multi-level dependencies
declare CreditTier
    tier: String  // "A" (750+), "B" (700-749), "C" (600-699)
end

declare AgeBracket
    bracket: String  // "young" (18-35), "middle" (36-50), "senior" (51-65)
end

declare RiskPoints
    factor: String  // "credit", "age", "health", "smoking", "dti", "occupation"
    points: int
end

declare RiskCategory
    category: int  // 1 (low) through 5 (very high)
    totalPoints: int
end

declare ApprovalStatus
    stage: String  // "primary", "financial", "risk", "final"
    passed: boolean
    reason: String
end

// Final decision type
declare Decision
    approved: boolean
    reasons: java.util.List
    requiresManualReview: boolean
    premiumMultiplier: double
    riskCategory: int
end

// ============================================================================
// PART 2: INITIALIZATION RULES (Highest Salience)
// ============================================================================

rule "Initialize Decision"
    salience 10000
    when
        not Decision()
    then
        Decision decision = new Decision();
        decision.setApproved(true);
        decision.setReasons(new java.util.ArrayList());
        decision.setRequiresManualReview(false);
        decision.setPremiumMultiplier(1.0);
        decision.setRiskCategory(0);
        insert(decision);
end

// ============================================================================
// PART 3: STAGE 1 - ESTABLISH CLASSIFICATIONS (Salience 9000-9999)
// ============================================================================

rule "Establish Credit Tier A"
    salience 9000
    when
        $applicant : Applicant( creditScore >= 750 )
        not CreditTier()
    then
        CreditTier ct = new CreditTier();
        ct.setTier("A");
        insert(ct);
end

rule "Establish Credit Tier B"
    salience 9000
    when
        $applicant : Applicant( creditScore >= 700, creditScore < 750 )
        not CreditTier()
    then
        CreditTier ct = new CreditTier();
        ct.setTier("B");
        insert(ct);
end

rule "Establish Credit Tier C"
    salience 9000
    when
        $applicant : Applicant( creditScore >= 600, creditScore < 700 )
        not CreditTier()
    then
        CreditTier ct = new CreditTier();
        ct.setTier("C");
        insert(ct);
end

rule "Establish Age Bracket - Young"
    salience 9000
    when
        $applicant : Applicant( age >= 18, age <= 35 )
        not AgeBracket()
    then
        AgeBracket ab = new AgeBracket();
        ab.setBracket("young");
        insert(ab);
end

rule "Establish Age Bracket - Middle"
    salience 9000
    when
        $applicant : Applicant( age >= 36, age <= 50 )
        not AgeBracket()
    then
        AgeBracket ab = new AgeBracket();
        ab.setBracket("middle");
        insert(ab);
end

rule "Establish Age Bracket - Senior"
    salience 9000
    when
        $applicant : Applicant( age >= 51, age <= 65 )
        not AgeBracket()
    then
        AgeBracket ab = new AgeBracket();
        ab.setBracket("senior");
        insert(ab);
end

// ============================================================================
// PART 4: STAGE 1 - PRIMARY ELIGIBILITY CHECKS (Salience 8000-8999)
// ============================================================================

rule "Reject - Age Out of Range"
    salience 8500
    when
        $applicant : Applicant( age < 18 || age > 65 )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Applicant age must be between 18 and 65");
        update($decision);
end

rule "Reject - Credit Score Too Low"
    salience 8500
    when
        $applicant : Applicant( creditScore < 600 )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Minimum credit score of 600 required");
        update($decision);
end

// ============================================================================
// PART 5: STAGE 2 - COMPOUND CONDITION CHECKS (Salience 7000-7999)
// These rules depend on CreditTier being established first
// ============================================================================

rule "Reject - Tier C with Fair Health"
    salience 7500
    when
        CreditTier( tier == "C" )
        $applicant : Applicant( health == "fair" )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Tier C applicants with fair health are not eligible");
        update($decision);
end

rule "Income Check - Tier A Excellent Health"
    salience 7000
    when
        CreditTier( tier == "A" )
        $applicant : Applicant( health == "excellent", annualIncome < 20000 )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Tier A with excellent health requires minimum income $20,000");
        update($decision);
end

rule "Income Check - Tier A Good Health"
    salience 7000
    when
        CreditTier( tier == "A" )
        $applicant : Applicant( health == "good", annualIncome < 25000 )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Tier A with good health requires minimum income $25,000");
        update($decision);
end

rule "Coverage Limit Check - Tier A Excellent Health"
    salience 7000
    when
        CreditTier( tier == "A" )
        $applicant : Applicant( health == "excellent", $income : annualIncome )
        $policy : Policy( coverageAmount > ($income * 12) )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.getReasons().add("Tier A with excellent health limited to 12x annual income");
        update($decision);
end

// ============================================================================
// PART 6: STAGE 3 - RISK POINT CALCULATION (Salience 6000-6999)
// ============================================================================

rule "Calculate Risk Points - Credit Tier"
    salience 6000
    when
        CreditTier( $tier : tier )
        not RiskPoints( factor == "credit" )
    then
        int points = "A".equals($tier) ? 0 : ("B".equals($tier) ? 2 : 5);
        RiskPoints rp = new RiskPoints();
        rp.setFactor("credit");
        rp.setPoints(points);
        insert(rp);
end

rule "Calculate Risk Points - Age"
    salience 6000
    when
        $applicant : Applicant( $age : age )
        not RiskPoints( factor == "age" )
    then
        int points = ($age <= 30) ? 0 : (($age <= 40) ? 1 : (($age <= 50) ? 3 : (($age <= 60) ? 5 : 8)));
        RiskPoints rp = new RiskPoints();
        rp.setFactor("age");
        rp.setPoints(points);
        insert(rp);
end

rule "Calculate Risk Points - Health"
    salience 6000
    when
        $applicant : Applicant( $health : health )
        not RiskPoints( factor == "health" )
    then
        int points = "excellent".equals($health) ? 0 : ("good".equals($health) ? 2 : 6);
        RiskPoints rp = new RiskPoints();
        rp.setFactor("health");
        rp.setPoints(points);
        insert(rp);
end

rule "Calculate Risk Points - Smoking"
    salience 6000
    when
        $applicant : Applicant( $smoking : smoker )
        not RiskPoints( factor == "smoking" )
    then
        int points = $smoking ? 5 : 0;
        RiskPoints rp = new RiskPoints();
        rp.setFactor("smoking");
        rp.setPoints(points);
        insert(rp);
end

// ============================================================================
// PART 7: STAGE 4 - RISK CATEGORY ASSIGNMENT (Salience 5000-5999)
// ============================================================================

rule "Calculate Total Risk Points and Assign Category"
    salience 5000
    when
        not RiskCategory()
        accumulate(
            RiskPoints( $p : points );
            $total : sum($p)
        )
    then
        int total = $total.intValue();
        int category = (total <= 5) ? 1 : ((total <= 10) ? 2 : ((total <= 15) ? 3 : ((total <= 20) ? 4 : 5)));
        RiskCategory rc = new RiskCategory();
        rc.setCategory(category);
        rc.setTotalPoints(total);
        insert(rc);
end

// ============================================================================
// PART 8: STAGE 5 - RISK-BASED DECISIONS (Salience 4000-4999)
// ============================================================================

rule "Risk Category 3+ Requires Manual Review"
    salience 4000
    when
        RiskCategory( category >= 3 )
        $decision : Decision()
    then
        $decision.setRequiresManualReview(true);
        update($decision);
end

rule "Set Premium Multiplier by Risk Category"
    salience 4000
    when
        RiskCategory( $cat : category )
        $decision : Decision()
    then
        double multiplier = ($cat == 1) ? 1.0 : (($cat == 2) ? 1.3 : (($cat == 3) ? 1.7 : (($cat == 4) ? 2.2 : 2.5)));
        $decision.setPremiumMultiplier(multiplier);
        $decision.setRiskCategory($cat);
        update($decision);
end

// ============================================================================
// PART 9: FINAL DECISION RULES (Salience 1000-1999)
// ============================================================================

rule "Final Approval Check"
    salience 1000
    when
        $decision : Decision( approved == true, requiresManualReview == false )
    then
        // All checks passed - automatic approval
        System.out.println("Application APPROVED");
end
```

GUIDELINES FOR MULTI-LEVEL RULES:

1. **ALWAYS use 'declare' statements** to define Applicant, Policy, Decision, and ALL intermediate types (CreditTier, RiskCategory, etc.)
2. **Do NOT use import statements** for model classes
3. **CRITICAL: Use setter-based initialization for declared types**, NOT constructors:
   - CORRECT: `CreditTier ct = new CreditTier(); ct.setTier("A"); insert(ct);`
   - WRONG: `insert(new CreditTier("A"));` (constructors don't work with declared types)
4. **Use SALIENCE to control execution order**:
   - 10000: Initialization
   - 9000-9999: Establish classifications (CreditTier, AgeBracket)
   - 8000-8999: Primary eligibility checks (age, credit minimum)
   - 7000-7999: Compound condition checks (depend on CreditTier + Health)
   - 6000-6999: Risk point calculation
   - 5000-5999: Risk category assignment
   - 4000-4999: Risk-based decisions
   - 1000-1999: Final decisions
5. **Create separate rules for EACH compound condition**:
   - One rule for "Tier A + Excellent Health"
   - One rule for "Tier A + Good Health"
   - One rule for "Tier A + Fair Health"
   - (repeat for Tier B and Tier C)
6. **Use intermediate fact types** for classifications that are used in later rules
7. **Always check "not <FactType>()" before inserting** to prevent duplicates
8. **Use proper getter/setter methods**: setApproved(), getReasons().add("reason")
9. **For rejection rules, use $decision.getReasons().add()** to accumulate ALL rejection reasons
10. **NEVER use setReason() or setReasons()** in rejection rules - always use getReasons().add()
11. **When comparing fields from different objects**, use variable binding:
    - CORRECT: `$applicant : Applicant( $income : annualIncome )  $policy : Policy( coverageAmount > ($income * 10) )`
    - WRONG: `$applicant : Applicant( annualIncome * 10 < coverageAmount )`
12. **CRITICAL: Field Ownership - Access fields from the correct object type**:
    - Applicant fields: age, creditScore, annualIncome, health, smoker, debtToIncome, employmentStatus, occupation, etc.
    - Policy fields: policyType, loanType, coverageAmount, term, interestRate, minimumLoanAmount, maximumLoanAmount, debtServiceCoverageRatio, etc.
    - NEVER access Policy fields from Applicant: `Applicant(loanType == "personal")` is WRONG
    - ALWAYS access Policy fields from Policy: `$policy : Policy(loanType == "personal")` is CORRECT
    - Example for loan rules: `$applicant : Applicant(...) $policy : Policy(loanType == "personal", ...)`
13. **CRITICAL: Variable Binding - Never bind variables directly to field names**:
    - WRONG: `$smoking : smoking` or `$age : age` or `$health : health` - These are INVALID!
    - CORRECT: `$applicant : Applicant($smoking : smoker)` - Bind to the object first, then extract the field
    - To extract a field value: `$applicant : Applicant($smoking : smoker, $age : age, $health : health)`
    - Then use the extracted variables in the then clause: `int points = $smoking ? 5 : 0;`
    - Field names like 'smoking', 'age', 'health' are NOT types - they are properties of Applicant
    - Always follow pattern: `$object : ObjectType($variable : fieldName)`
14. **For point-based systems**, use setter-based initialization for RiskPoints:
    - CORRECT: `RiskPoints rp = new RiskPoints(); rp.setFactor("credit"); rp.setPoints(points); insert(rp);`
15. **CRITICAL: Type Conversion for accumulate() results**:
    - The `accumulate()` function returns a `Long` or `BigDecimal`, NOT an `int`
    - ALWAYS convert accumulate results before using with int setters:
    - CORRECT: `int total = $total.intValue(); rc.setTotalPoints(total);`
    - WRONG: `rc.setTotalPoints($total);` (will fail: Long cannot be used where int is required)
    - For sum operations: `int total = $total.intValue();` then use `total` variable
    - For count operations: `int count = $count.intValue();` then use `count` variable
    - For average operations: `double avg = $avg.doubleValue();` then use `avg` variable
16. **Use 'not' checks** to ensure rules fire only once: `when not CreditTier() then ...`
16. **Add comments** to mark each stage clearly
17. **Handle special rejection rules** early (high salience) to short-circuit evaluation
18. **Create clear, specific rule names** based on the extracted data (e.g., "Income Check - Tier A Excellent Health")
19. **Make rules executable and testable** - ensure all syntax is valid Drools DRL
20. **Add section comments** to organize rules by stage/purpose

SPECIAL HANDLING FOR EXTRACTED DATA:

If extracted data contains:
- **dependency_stages**: Use this to determine salience ranges and intermediate fact types
- **intermediate_facts**: Declare these as Drools types (e.g., CreditTier, RiskCategory)
- **special_rejection_rules**: Generate high-salience rules for these compound rejections
- **Matrix data** (e.g., "Tier A + Excellent Health" combinations): Generate one rule per cell

Return your response with:
1. Complete DRL rules in ```drl code blocks (including ALL declare statements for intermediate facts)
2. Brief explanation of the rules organized by stage
3. List of intermediate facts that later rules depend on

DO NOT generate decision tables - only generate DRL rules."""),
            ("user", """Extracted policy data:

{extracted_data}

Generate complete, self-contained Drools DRL rules with 'declare' statements for all types.""")
        ])

        self.chain = self.rule_generation_prompt | self.llm

    def update_schema(self, schema: Dict):
        """Update the dynamic schema"""
        self.schema = schema

    def _generate_dynamic_declare_statements(self) -> str:
        """
        Generate Drools declare statements from dynamic schema

        Returns:
            String containing declare statements for Applicant, Policy, and Decision
        """
        if not self.schema:
            # Fallback to minimal schema if none provided
            return """// Using minimal fallback schema
declare Applicant
    name: String
    age: int
end

declare Policy
    policyType: String
end

declare Decision
    decision: String
    approved: boolean
    reasons: java.util.List
    riskCategory: int
end
"""

        drl = "// Dynamically generated schema from policy document\n\n"

        # Helper function to map field types to Drools-compatible types
        def map_field_type(field_type: str) -> str:
            """Map schema field types to fully-qualified Drools types"""
            type_mapping = {
                'Date': 'java.util.Date',
                'List': 'java.util.List',
                'Map': 'java.util.Map',
                'Set': 'java.util.Set'
            }
            return type_mapping.get(field_type, field_type)

        # Generate Applicant declaration
        if self.schema.get('applicant_fields'):
            drl += "declare Applicant\n"
            for field in self.schema['applicant_fields']:
                field_name = field['field_name']
                field_type = map_field_type(field['field_type'])
                description = field.get('description', '')
                drl += f"    {field_name}: {field_type}  // {description}\n"
            drl += "end\n\n"

        # Generate Policy declaration
        if self.schema.get('policy_fields'):
            drl += "declare Policy\n"
            for field in self.schema['policy_fields']:
                field_name = field['field_name']
                field_type = map_field_type(field['field_type'])
                description = field.get('description', '')
                drl += f"    {field_name}: {field_type}  // {description}\n"
            drl += "end\n\n"

        # Always include intermediate fact types (for multi-level rule dependencies)
        drl += """// Intermediate fact types for multi-level dependencies
declare CreditTier
    tier: String  // "A" (750+), "B" (700-749), "C" (600-699)
end

declare AgeBracket
    bracket: String  // "young" (18-35), "middle" (36-50), "senior" (51-65)
end

declare RiskPoints
    factor: String  // "credit", "age", "health", "smoking", "dti", "occupation"
    points: int
end

declare RiskCategory
    category: int  // 1 (low) through 5 (very high)
    totalPoints: int
end

declare ApprovalStatus
    stage: String  // "primary", "financial", "risk", "final"
    passed: boolean
    reason: String
end

// Final decision type with comprehensive fields
declare Decision
    decision: String
    approved: boolean
    reasons: java.util.List
    riskCategory: int
    requiresManualReview: boolean
    premiumMultiplier: double
end
"""

        return drl

    def generate_rules(self, extracted_data: Dict, policy_text: str = None) -> Dict[str, str]:
        """
        Generate Drools rules from extracted data and/or full policy text

        :param extracted_data: Data extracted by Textract (may be incomplete)
        :param policy_text: Full policy document text (fallback for incomplete extractions)
        :return: Dictionary with 'drl', 'decision_table', and 'explanation' keys
        """
        try:
            # Generate dynamic schema declarations if schema is available
            schema_declarations = self._generate_dynamic_declare_statements()

            # Add schema information to the prompt context
            schema_context = ""
            if self.schema:
                schema_context = "\n\nDYNAMIC SCHEMA INFORMATION:\n"
                schema_context += "The following fields have been extracted from the policy document:\n\n"
                schema_context += "=== APPLICANT FIELDS (access from Applicant object) ===\n"
                for field in self.schema.get('applicant_fields', []):
                    schema_context += f"  - {field['field_name']} ({field['field_type']}): {field.get('description', '')}\n"
                schema_context += "\n=== POLICY FIELDS (access from Policy object) ===\n"
                for field in self.schema.get('policy_fields', []):
                    schema_context += f"  - {field['field_name']} ({field['field_type']}): {field.get('description', '')}\n"
                schema_context += "\nCRITICAL FIELD OWNERSHIP RULES:\n"
                schema_context += "1. Applicant fields (age, creditScore, annualIncome, etc.) MUST be accessed from Applicant:\n"
                schema_context += "   CORRECT: $applicant : Applicant(age >= 18, creditScore >= 600)\n"
                schema_context += "2. Policy fields (loanType, coverageAmount, term, interestRate, etc.) MUST be accessed from Policy:\n"
                schema_context += "   CORRECT: $policy : Policy(loanType == \"personal\", coverageAmount > 100000)\n"
                schema_context += "3. NEVER access Policy fields from Applicant:\n"
                schema_context += "   WRONG: $applicant : Applicant(loanType == \"personal\")  // loanType is NOT on Applicant!\n"
                schema_context += "4. When a rule needs both Applicant and Policy fields, bind both objects:\n"
                schema_context += "   CORRECT: $applicant : Applicant(...) $policy : Policy(loanType == \"personal\", ...)\n"
                schema_context += "\nUSE THESE EXACT FIELD NAMES in your rules. The declare statements will be added automatically.\n"

            # Prepare input for LLM - combine extracted data with policy text
            llm_input = json.dumps(extracted_data, indent=2) + schema_context

            # If policy text is provided and extracted data has low coverage, add policy text context
            if policy_text:
                queries_dict = extracted_data.get('queries', {})
                if isinstance(queries_dict, dict):
                    queries_with_answers = sum(1 for q_data in queries_dict.values() if q_data.get('answer'))
                    total_queries = len(queries_dict)
                    coverage = (queries_with_answers / total_queries * 100) if total_queries > 0 else 0

                    if coverage < 50:  # Less than 50% coverage
                        print(f"⚠ Low query coverage ({coverage:.1f}%). Including policy text for direct extraction.")
                        llm_input += f"\n\nFULL POLICY TEXT (for extracting missing rules):\n\n{policy_text[:20000]}\n\nIMPORTANT: Extract risk calculation rules, premium multipliers, and scoring systems directly from the policy text above if they are missing from the extracted data."

            print("\n" + "="*80)
            print("DEBUG: RULE GENERATION - LLM INPUT")
            print("="*80)
            print(llm_input[:2000])  # First 2000 chars
            print("...")
            print("="*80)

            result = self.chain.invoke({
                "extracted_data": llm_input
            })

            # Parse LLM response to extract DRL and CSV
            content = result.content

            # Debug: Log LLM response for troubleshooting
            print(f"\n===== DEBUG: LLM Response for Rule Generation =====")
            print(f"Response length: {len(content)} characters")
            print(f"Response preview (first 500 chars):\n{content[:500]}")
            print(f"Response preview (last 500 chars):\n{content[-500:]}")
            print(f"===== END DEBUG =====\n")

            # Extract DRL (between ```drl or ```java and ```)
            drl_rules = self._extract_code_block(content, 'drl') or \
                        self._extract_code_block(content, 'java')

            print(f"DEBUG: Extracted DRL rules: {drl_rules[:200] if drl_rules else 'None'}")

            # If DRL was generated, prepend dynamic schema and ensure package statement
            if drl_rules:
                # Remove any existing declare statements from LLM output (we'll use our dynamic ones)
                drl_rules = self._remove_declare_statements(drl_rules)

                # Ensure package statement at the top
                if not drl_rules.startswith('package '):
                    final_drl = "package com.underwriting.rules;\n\n"
                else:
                    final_drl = ""

                # Add dynamic schema declarations
                final_drl += schema_declarations + "\n"

                print(f"DEBUG: Schema declarations length: {len(schema_declarations)} chars")
                print(f"DEBUG: Schema preview: {schema_declarations[:500]}")

                # Add the generated rules
                final_drl += drl_rules

                print(f"DEBUG: Final DRL length: {len(final_drl)} chars")
                print(f"DEBUG: Final DRL contains 'CreditTier': {('CreditTier' in final_drl)}")
                print(f"DEBUG: Final DRL contains 'AgeBracket': {('AgeBracket' in final_drl)}")
                print(f"DEBUG: Final DRL contains risk calculation: {('Calculate Risk Points' in final_drl or 'RiskCategory' in final_drl)}")

                drl = final_drl
            else:
                drl = "// No DRL rules generated"

            # Extract CSV (between ```csv and ```)
            decision_table = self._extract_code_block(content, 'csv')

            # Extract explanation (everything not in code blocks)
            explanation = self._extract_explanation(content)

            return {
                'drl': drl,
                'decision_table': decision_table or "",
                'explanation': explanation,
                'raw_response': content
            }

        except Exception as e:
            print(f"Error generating rules: {e}")
            return {
                'drl': "// Error generating rules",
                'decision_table': "",
                'explanation': f"Error: {str(e)}",
                'raw_response': ""
            }

    def _remove_declare_statements(self, drl: str) -> str:
        """
        Remove declare statements from DRL (we'll use our dynamic ones)
        This prevents conflicts between LLM-generated and dynamic schema
        """
        import re
        # Remove declare blocks (from 'declare TypeName' to 'end')
        # Also remove ALL package statements (we'll add our own at the top)
        lines = drl.split('\n')
        result_lines = []
        in_declare_block = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip ALL package statements (we add our own at the top)
            if stripped.startswith('package '):
                continue

            # Check if entering a declare block
            if stripped.startswith('declare '):
                in_declare_block = True
                continue

            # Check if exiting a declare block
            if in_declare_block and stripped == 'end':
                in_declare_block = False
                continue

            # Skip lines inside declare blocks
            if in_declare_block:
                continue

            # Keep all other lines
            result_lines.append(line)

        return '\n'.join(result_lines)

    def _extract_code_block(self, text: str, language: str) -> str:
        """Extract code block from markdown"""
        start_marker = f"```{language}"
        end_marker = "```"

        start = text.find(start_marker)
        if start == -1:
            return None

        start += len(start_marker)
        end = text.find(end_marker, start)

        if end == -1:
            # If no end marker found, the response may be truncated
            # Extract everything from start to end of text
            print(f"WARNING: No closing ``` marker found for {language} code block")
            print(f"         Extracting from position {start} to end of response")
            return text[start:].strip()

        return text[start:end].strip()

    def _extract_explanation(self, text: str) -> str:
        """Extract explanation text (non-code-block content)"""
        # Remove all code blocks
        import re
        cleaned = re.sub(r'```[\s\S]*?```', '', text)
        return cleaned.strip()

    def save_decision_table(self, decision_table: str, output_path: str):
        """
        Save decision table as Excel file for Drools

        :param decision_table: CSV content
        :param output_path: Path to save Excel file
        """
        try:
            if not decision_table:
                print("No decision table to save")
                return None

            # Convert CSV to DataFrame
            df = pd.read_csv(io.StringIO(decision_table))

            # Save as Excel
            df.to_excel(output_path, index=False)
            print(f"Decision table saved to: {output_path}")
            return output_path

        except Exception as e:
            print(f"Error saving decision table: {e}")
            # Try saving as CSV instead
            try:
                csv_path = output_path.replace('.xlsx', '.csv')
                with open(csv_path, 'w') as f:
                    f.write(decision_table)
                print(f"Decision table saved as CSV to: {csv_path}")
                return csv_path
            except Exception as e2:
                print(f"Error saving as CSV: {e2}")
                return None

    def generate_template_drl(self, rule_category: str) -> str:
        """
        Generate template DRL for common rule categories

        :param rule_category: Category of rules (age_check, coverage_limit, etc.)
        :return: DRL template
        """
        templates = {
            "age_check": """package com.underwriting.rules;

// Declare types directly in DRL
declare Applicant
    name: String
    age: int
    occupation: String
end

declare Decision
    approved: boolean
    reason: String
    requiresManualReview: boolean
end

rule "Initialize Decision"
    when
        not Decision()
    then
        Decision decision = new Decision();
        decision.setApproved(true);
        decision.setReason("Initial evaluation");
        decision.setRequiresManualReview(false);
        insert(decision);
end

rule "Age Requirement Check"
    when
        $applicant : Applicant( age < 18 || age > 65 )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.setReason("Applicant age is outside acceptable range (18-65)");
        update($decision);
end""",

            "coverage_limit": """package com.underwriting.rules;

// Declare types directly in DRL
declare Policy
    policyType: String
    coverageAmount: double
    term: int
end

declare Decision
    approved: boolean
    reason: String
    requiresManualReview: boolean
end

rule "Initialize Decision"
    when
        not Decision()
    then
        Decision decision = new Decision();
        decision.setApproved(true);
        decision.setReason("Initial evaluation");
        decision.setRequiresManualReview(false);
        insert(decision);
end

rule "Coverage Limit Check"
    when
        $policy : Policy( coverageAmount > 500000 )
        $decision : Decision()
    then
        $decision.setRequiresManualReview(true);
        $decision.setReason("Coverage amount exceeds automatic approval threshold");
        update($decision);
end""",

            "risk_assessment": """package com.underwriting.rules;

// Declare types directly in DRL
declare Applicant
    name: String
    age: int
    occupation: String
end

declare RiskProfile
    riskScore: int
end

declare Decision
    approved: boolean
    reason: String
    requiresManualReview: boolean
    premiumMultiplier: double
end

rule "Initialize Decision"
    when
        not Decision()
    then
        Decision decision = new Decision();
        decision.setApproved(true);
        decision.setReason("Initial evaluation");
        decision.setRequiresManualReview(false);
        decision.setPremiumMultiplier(1.0);
        insert(decision);
end

rule "High Risk Assessment"
    when
        $applicant : Applicant()
        $risk : RiskProfile( riskScore > 80 )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.setReason("Risk score exceeds acceptable threshold");
        $decision.setPremiumMultiplier(1.5);
        update($decision);
end"""
        }

        return templates.get(rule_category, templates["age_check"])
