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

"""
Test Case Generator for Underwriting Policies
Automatically generates comprehensive test cases using LLM based on policy documents and extracted rules.
"""

import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """
    Generates test cases for policy evaluation using LLM analysis
    """

    def __init__(self, llm):
        """
        Initialize the test case generator

        Args:
            llm: Language model instance for test case generation
        """
        self.llm = llm

    def generate_test_cases(self,
                          drl_content: str,
                          schema: Dict[str, Any],
                          policy_type: str = "insurance") -> List[Dict[str, Any]]:
        """
        Generate comprehensive test cases based on DRL rules ONLY

        This method generates test cases directly from DRL rules to ensure perfect
        alignment with the deployed rules. Policy-based generation has been removed.

        Args:
            drl_content: The actual DRL rules content (REQUIRED)
            schema: Dynamic schema with field definitions (REQUIRED for field name consistency)
            policy_type: Type of policy (insurance, loan, etc.)

        Returns:
            List of test case dictionaries
        """
        logger.info("Generating test cases from DRL rules...")

        if not drl_content:
            logger.error("DRL content is required for test case generation")
            raise ValueError("DRL content is required. Cannot generate test cases without rules.")

        if not schema:
            logger.warning("Schema not provided. Test cases may have incorrect field names.")

        return self._generate_test_cases_from_drl(drl_content, schema, policy_type)

    def _build_schema_context(self, schema: Dict[str, Any]) -> str:
        """
        Build schema context to ensure test data uses correct field names
        This is CRITICAL to prevent field name mismatches
        """
        context = []

        context.append("\n# SCHEMA FIELD DEFINITIONS (MUST USE THESE EXACT FIELD NAMES):")

        if schema.get('applicant_fields'):
            context.append("\n## Applicant Fields:")
            for field in schema['applicant_fields']:
                field_name = field['field_name']
                field_type = field['field_type']
                description = field.get('description', '')
                examples = field.get('example_values', [])
                context.append(f"  - {field_name} ({field_type}): {description}")
                if examples:
                    context.append(f"    Example values: {examples}")

        if schema.get('policy_fields'):
            context.append("\n## Policy Fields:")
            for field in schema['policy_fields']:
                field_name = field['field_name']
                field_type = field['field_type']
                description = field.get('description', '')
                examples = field.get('example_values', [])
                context.append(f"  - {field_name} ({field_type}): {description}")
                if examples:
                    context.append(f"    Example values: {examples}")

        context.append("\n**CRITICAL**: You MUST use these exact field names in test data. Do NOT use aliases or variations.")

        return "\n".join(context)

    def _generate_example_from_schema(self, schema: Dict[str, Any]) -> str:
        """
        Generate a concrete example test case from the schema
        This shows the LLM the exact structure and field names to use
        """
        example = {
            "test_case_name": "Example - Age Below Minimum",
            "description": "Example test case structure",
            "category": "negative",
            "priority": 1,
            "applicant_data": {},
            "policy_data": {},
            "expected_decision": "rejected",
            "expected_reasons": ["Example reason from DRL"],
            "expected_risk_category": None,
            "rule_name": "Example Rule Name from DRL"
        }

        # Populate applicant_data with actual field names from schema
        if schema and schema.get('applicant_fields'):
            for field in schema['applicant_fields']:
                field_name = field['field_name']
                field_type = field['field_type']
                examples = field.get('example_values', [])

                # Use example value if available, otherwise generate based on type
                if examples:
                    example['applicant_data'][field_name] = examples[0]
                elif field_type == 'integer':
                    example['applicant_data'][field_name] = 30
                elif field_type == 'double' or field_type == 'float':
                    example['applicant_data'][field_name] = 75000.0
                elif field_type == 'boolean':
                    example['applicant_data'][field_name] = False
                else:  # string
                    example['applicant_data'][field_name] = "example_value"

        # Populate policy_data with actual field names from schema
        if schema and schema.get('policy_fields'):
            for field in schema['policy_fields']:
                field_name = field['field_name']
                field_type = field['field_type']
                examples = field.get('example_values', [])

                # Use example value if available, otherwise generate based on type
                if examples:
                    example['policy_data'][field_name] = examples[0]
                elif field_type == 'integer':
                    example['policy_data'][field_name] = 20
                elif field_type == 'double' or field_type == 'float':
                    example['policy_data'][field_name] = 500000.0
                elif field_type == 'boolean':
                    example['policy_data'][field_name] = False
                else:  # string
                    example['policy_data'][field_name] = "example_value"

        return json.dumps(example, indent=2)

    def _parse_test_cases(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse test cases from LLM response"""
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # Try to find JSON array directly
                json_start = response_text.find("[")
                json_end = response_text.rfind("]") + 1
                json_text = response_text[json_start:json_end].strip()

            # Parse JSON
            test_cases = json.loads(json_text)

            # Add metadata
            for tc in test_cases:
                tc['is_auto_generated'] = True
                tc['generation_method'] = 'llm'

            return test_cases

        except Exception as e:
            logger.error(f"Error parsing test cases JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return []

    def _generate_test_cases_from_drl(self, drl_content: str, schema: Dict[str, Any], policy_type: str) -> List[Dict[str, Any]]:
        """
        Generate test cases by analyzing DRL rules directly
        This ensures test cases are perfectly aligned with deployed rules

        Args:
            drl_content: The DRL rules content
            schema: Dynamic schema with field definitions
            policy_type: Type of policy

        Returns:
            List of test case dictionaries
        """
        logger.info("Analyzing DRL rules to generate test cases...")

        # Build schema context
        schema_context = self._build_schema_context(schema) if schema else ""

        # Generate concrete example from schema
        example_json = self._generate_example_from_schema(schema)

        # Create prompt for DRL-based test generation
        prompt = f"""You are a test case generator for Drools DRL rules.

Your task is to analyze the provided DRL rules and generate test cases that validate the rules.

# DRL Rules to Test:
```drl
{drl_content}
```

{schema_context}

# Instructions:

Generate test cases with these guidelines:

1. **One Test Case Per Rule**: Generate EXACTLY ONE test case for each rule in the DRL
   - Focus on the most important rules (rejection rules, risk calculation rules)
   - Prioritize rules with salience > 100

2. **CRITICAL - Consider ALL Rules That Will Fire**: When generating test data, you MUST ensure the test data ONLY triggers the intended rule and does NOT trigger OTHER rejection rules
   - Example: If testing "Calculate Risk Points - Health", use test data that:
     * Has the health value you want to test (e.g., "fair")
     * BUT also has creditScore/age/income values that AVOID triggering rejection rules
     * Example: health="fair" + creditScore=750 (Tier A) + age=30 + good income = NO rejection
   - Example: If testing "Calculate Risk Points - Health" with health="fair", you MUST use:
     * creditScore >= 750 (Tier A) to avoid "Tier C with Fair Health" rejection
     * OR creditScore >= 700 (Tier B) with health="good" or "excellent" to avoid "Tier B with Fair Health" rejection
   - **Trace through ALL rules**: Before setting expected_decision, check if ANY rejection rule will fire
   - **For multi-level rules**: Consider intermediate facts (CreditTier, RiskCategory) that might trigger rejections

3. **Rejection Rules**: For each rejection rule, create a test case that triggers it
   - Extract the rejection reason from the rule's "then" clause
   - Use that exact text as the expected_reasons
   - Set expected_decision to "rejected"
   - Ensure test data ONLY triggers this specific rejection rule (not multiple rejections)

4. **Risk Calculation Rules**: Test rules that calculate risk points or categories
   - Include test data that triggers the specific risk calculation
   - **CRITICAL**: Ensure test data does NOT trigger any rejection rules
   - Set expected_decision to "approved" ONLY if no rejection rules will fire
   - Use safe values: Tier A credit (750+), excellent/good health, reasonable age (30-40), good income

5. **Field Names**: Use EXACT field names from the schema shown above (CRITICAL)
   - Copy field names exactly from the schema
   - Do NOT use variations or snake_case

6. **Risk Category**: ALWAYS set expected_risk_category to null
   - Risk categories are calculated dynamically by accumulating risk points
   - Cannot be predicted without executing the rules
   - Test validation will skip risk category comparison when null

7. **Decision Logic**: 
   - If ANY rejection rule fires → expected_decision = "rejected"
   - If NO rejection rules fire → expected_decision = "approved"
   - Always check ALL rejection rules in the DRL before setting expected_decision

# Example Test Case Structure:

Use this EXACT structure with the ACTUAL field names from the schema:

```json
{example_json}
```

# Output Format:

Return ONLY a valid JSON array following the structure above.
- Generate ONE test case per rule (maximum 15 test cases total)
- Use EXACT field names from schema
- Extract expected_reasons from the DRL "then" clause
- Set expected_risk_category to null (not 0, not a number - use null)
- Ensure all JSON is valid and properly closed

CRITICAL RULES:
- Limit to 15 test cases maximum (1 per rule)
- Use exact field names from schema above
- ALWAYS use null for expected_risk_category
- **MOST IMPORTANT**: Before setting expected_decision, check ALL rejection rules in the DRL
- For calculation rules, use test data that avoids triggering rejection rules
- For rejection rules, use test data that ONLY triggers that specific rejection
- Keep JSON concise and valid
- Close all brackets properly

**DECISION FLOW FOR EACH TEST CASE:**
1. Identify the target rule you're testing
2. Generate test data that triggers the target rule
3. Check ALL rejection rules in the DRL - will ANY of them fire with this test data?
4. If YES → expected_decision = "rejected", expected_reasons = [rejection reason from the firing rule]
5. If NO → expected_decision = "approved", expected_reasons = []
6. Set expected_risk_category = null (always)

Generate the test cases now:"""

        try:
            print("\n" + "="*80)
            print("DEBUG: DRL-BASED TEST CASE GENERATION - LLM PROMPT")
            print("="*80)
            print(prompt[:2000])  # First 2000 chars
            print("...")
            print("="*80)

            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)

            print("\n" + "="*80)
            print("DEBUG: DRL-BASED TEST CASE GENERATION - LLM RESPONSE")
            print("="*80)
            print(response_text[:3000])  # First 3000 chars
            print("...")
            print("="*80)

            # Parse JSON from response
            test_cases = self._parse_test_cases(response_text)

            print("\n" + "="*80)
            print(f"DEBUG: GENERATED {len(test_cases)} DRL-BASED TEST CASES")
            print("="*80)
            for i, tc in enumerate(test_cases[:5], 1):  # Show first 5
                print(f"\nTest Case {i}: {tc.get('test_case_name', 'Unknown')}")
                print(f"  Rule: {tc.get('rule_name', 'N/A')}")
                print(f"  Category: {tc.get('category')}")
                print(f"  Expected Decision: {tc.get('expected_decision')}")
                print(f"  Expected Reasons: {tc.get('expected_reasons', [])}")
            if len(test_cases) > 5:
                print(f"\n... and {len(test_cases) - 5} more test cases")
            print("="*80)

            logger.info(f"Generated {len(test_cases)} DRL-based test cases")
            return test_cases

        except Exception as e:
            logger.error(f"Error generating DRL-based test cases: {e}")
            import traceback
            traceback.print_exc()
            # Return empty list - no fallback to policy-based generation
            return []
