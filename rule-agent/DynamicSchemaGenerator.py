"""
Dynamic Schema Generator
Extracts field definitions from policy documents using LLM to generate dynamic Drools schemas
"""

import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DynamicSchemaGenerator:
    """
    Dynamically generates Drools schema definitions from policy documents.
    Eliminates hardcoded field names and types.
    """

    def __init__(self, llm):
        """
        Initialize the schema generator

        Args:
            llm: Language model instance for schema extraction
        """
        self.llm = llm

    def generate_schema_from_policy(self,
                                    policy_text: str,
                                    extracted_queries: List[Dict[str, Any]] = None,
                                    policy_type: str = "insurance") -> Dict[str, Any]:
        """
        Generate dynamic schema definitions from policy document

        Args:
            policy_text: Full policy document text
            extracted_queries: Previously extracted queries/rules from the document
            policy_type: Type of policy (insurance, loan, etc.)

        Returns:
            Dictionary containing:
            - applicant_fields: List of field definitions for Applicant entity
            - policy_fields: List of field definitions for Policy entity
            - field_mappings: Suggested mappings between common names and schema names
        """
        logger.info("Generating dynamic schema from policy document...")

        # Build context from extracted queries if available
        queries_context = ""
        query_texts = []
        if extracted_queries:
            queries_context = "\n\nPreviously extracted requirements:\n"
            for q in extracted_queries[:20]:  # Limit to first 20
                # Handle both dict and string query formats
                if isinstance(q, dict):
                    query_text = q.get('query_text', q.get('question', str(q)))
                else:
                    query_text = str(q)
                queries_context += f"- {query_text}\n"
                query_texts.append(query_text)

        # Analyze queries to identify required fields dynamically
        required_fields = self._analyze_queries_for_fields(extracted_queries if extracted_queries else [], policy_type)

        # Create the prompt for LLM with dynamic field requirements
        prompt = self._create_schema_extraction_prompt(policy_text, queries_context, policy_type, required_fields)

        try:
            print("\n" + "="*80)
            print("DEBUG: SCHEMA GENERATION - LLM PROMPT")
            print("="*80)
            print(prompt[:2000])  # First 2000 chars
            print("...")
            print("="*80)

            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)

            print("\n" + "="*80)
            print("DEBUG: SCHEMA GENERATION - LLM RESPONSE")
            print("="*80)
            print(response_text[:3000])  # First 3000 chars
            print("...")
            print("="*80)

            # Parse JSON from response
            schema = self._parse_schema_response(response_text)

            print("\n" + "="*80)
            print("DEBUG: GENERATED SCHEMA")
            print("="*80)
            print(f"Applicant Fields ({len(schema.get('applicant_fields', []))}):")
            for field in schema.get('applicant_fields', []):
                print(f"  - {field['field_name']} ({field['field_type']}): {field.get('description', '')}")
            print(f"\nPolicy Fields ({len(schema.get('policy_fields', []))}):")
            for field in schema.get('policy_fields', []):
                print(f"  - {field['field_name']} ({field['field_type']}): {field.get('description', '')}")
            print(f"\nField Mappings:")
            for k, v in schema.get('field_mappings', {}).items():
                print(f"  {k} → {v}")
            print("="*80)

            logger.info(f"Generated schema with {len(schema.get('applicant_fields', []))} applicant fields "
                       f"and {len(schema.get('policy_fields', []))} policy fields")

            return schema

        except Exception as e:
            logger.error(f"Error generating schema: {e}")
            # Return minimal schema as fallback
            return self._generate_minimal_schema(policy_type)

    def _analyze_queries_for_fields(self, extracted_queries: List[Dict[str, Any]], policy_type: str = "insurance") -> Dict[str, set]:
        """
        Analyze extracted queries to identify what fields are referenced.
        This ensures the schema includes all fields needed for the rules.

        Args:
            extracted_queries: List of extracted queries/rules from the document
            policy_type: Type of policy (insurance, loan, etc.) from request body

        Returns:
            Dictionary with 'applicant_hints' and 'policy_hints' sets containing field keywords
        """
        # Convert queries to text
        query_texts = []
        for q in extracted_queries:
            if isinstance(q, dict):
                query_text = q.get('query_text', q.get('question', str(q)))
            else:
                query_text = str(q)
            query_texts.append(query_text.lower())

        # Join all queries into one text for analysis
        all_queries = " ".join(query_texts)

        # DEBUG: Print first 500 chars of queries to see what we're analyzing
        print(f"\n{'='*80}")
        print("DEBUG: SAMPLE OF QUERIES BEING ANALYZED")
        print(f"{'='*80}")
        print(f"First 500 chars: {all_queries[:500]}")
        print(f"Total length: {len(all_queries)} characters")
        print(f"{'='*80}\n")

        # Dynamically identify applicant-related keywords
        applicant_hints = set()
        if any(word in all_queries for word in ['age', 'years old', 'older', 'younger']):
            applicant_hints.add('age')
        if any(word in all_queries for word in ['credit score', 'credit tier', 'tier a', 'tier b', 'tier c']):
            applicant_hints.add('creditScore')
        if any(word in all_queries for word in ['health', 'medical', 'excellent health', 'good health', 'fair health', 'poor health']):
            applicant_hints.add('health')
        if any(word in all_queries for word in ['smoker', 'smoking', 'tobacco', 'non-smoker']):
            applicant_hints.add('smoker')
        if any(word in all_queries for word in ['income', 'annual income', 'salary', 'earnings']):
            applicant_hints.add('income')
        if any(word in all_queries for word in ['debt', 'dti', 'debt-to-income', 'debt to income']):
            applicant_hints.add('debtToIncome')
        if any(word in all_queries for word in ['occupation', 'hazardous occupation', 'job']):
            applicant_hints.add('occupation')
        if any(word in all_queries for word in ['criminal', 'felony', 'dui', 'conviction']):
            applicant_hints.add('criminalRecord')
        if any(word in all_queries for word in ['asset', 'liquid asset', 'total asset']):
            applicant_hints.add('assets')
        if any(word in all_queries for word in ['employed', 'employment', 'years employed']):
            applicant_hints.add('employment')

        # Dynamically identify policy-related keywords
        policy_hints = set()
        if any(word in all_queries for word in ['coverage amount', 'coverage', 'insured amount', 'policy amount']):
            policy_hints.add('coverageAmount')
        if any(word in all_queries for word in ['term', 'duration', 'years', 'policy term', 'term years']):
            policy_hints.add('term')
        # Broader detection for policy type - includes general policy mentions
        if any(word in all_queries for word in ['policy type', 'type of policy', 'term life', 'whole life', 'life insurance', 'insurance policy', 'loan type', 'mortgage type']):
            policy_hints.add('policyType')
        if any(word in all_queries for word in ['premium', 'premium rate', 'base premium', 'premium multiplier']):
            policy_hints.add('premium')
        if any(word in all_queries for word in ['rider', 'accidental death rider', 'additional rider']):
            policy_hints.add('riders')

        # CRITICAL: For insurance policies, ALWAYS include policyType field
        # This is fundamental for insurance underwriting (term_life, whole_life, etc.)
        # The test case generator includes this field, so schema MUST have it
        if policy_type == "insurance":
            policy_hints.add('policyType')
            print(f"✓ Added policyType field (insurance policy detected from request body)")

        print(f"\n{'='*80}")
        print("DEBUG: QUERY ANALYSIS - IDENTIFIED FIELD HINTS")
        print(f"{'='*80}")
        print(f"Policy type from request: {policy_type}")
        print(f"Applicant field hints: {sorted(applicant_hints)}")
        print(f"Policy field hints: {sorted(policy_hints)}")
        print(f"{'='*80}")

        return {
            'applicant_hints': applicant_hints,
            'policy_hints': policy_hints
        }

    def _create_schema_extraction_prompt(self, policy_text: str, queries_context: str, policy_type: str, required_fields: Dict[str, set] = None) -> str:
        """Create the LLM prompt for schema extraction"""

        # Build required fields hint from query analysis
        required_fields_hint = ""
        if required_fields:
            applicant_hints = required_fields.get('applicant_hints', set())
            policy_hints = required_fields.get('policy_hints', set())

            if applicant_hints or policy_hints:
                required_fields_hint = "\n\n# CRITICAL - Required Fields Detected from Policy:\n\n"
                required_fields_hint += "Based on analysis of the extracted policy requirements, your schema MUST include fields for:\n\n"

                if applicant_hints:
                    required_fields_hint += "**Applicant fields** (referenced in policy rules):\n"
                    for hint in sorted(applicant_hints):
                        required_fields_hint += f"  - {hint}\n"
                    required_fields_hint += "\n"

                if policy_hints:
                    required_fields_hint += "**Policy fields** (referenced in policy rules):\n"
                    for hint in sorted(policy_hints):
                        required_fields_hint += f"  - {hint}\n"
                    required_fields_hint += "\n"

                required_fields_hint += "These are the MINIMUM required fields. Add any other fields you find in the policy document.\n"

        return f"""You are a schema extraction expert for {policy_type} underwriting systems.

Your task is to analyze the policy document and extract ALL data fields that would be needed to evaluate applications according to this policy.

# Policy Document:
{policy_text[:10000]}... (truncated for brevity)

{queries_context}
{required_fields_hint}

# Instructions:

1. Identify ALL fields that describe an **Applicant** (person/entity applying for the policy):
   - Demographics (age, gender, location, etc.)
   - Financial attributes (income, credit score, assets, etc.)
   - Health/medical information (health status, pre-existing conditions, smoker status, etc.)
   - Employment information (occupation, employer, years employed, etc.)
   - Legal/criminal record information
   - Any other applicant-specific attributes mentioned in the policy

2. Identify ALL fields that describe the **Policy** being applied for:
   - Coverage details (amount, type, duration, etc.)
   - Premium information
   - Terms and conditions
   - Special features or riders
   - Any other policy-specific attributes

3. For each field, provide:
   - **field_name**: Camel case name (e.g., "annualIncome", "creditScore", "healthStatus")
   - **field_type**: One of ["String", "int", "double", "boolean", "Date"]
   - **description**: Brief description of what this field represents
   - **example_values**: Array of 2-3 example values for this field
   - **common_aliases**: Array of alternative names this field might be called in test data (e.g., ["income", "yearly_income", "annual_income"] for annualIncome)

4. Also provide **field_mappings**: A mapping from common/readable field names to the schema field names.
   - This helps map test data that uses user-friendly names (like "healthStatus") to schema names (like "health")
   - Include bidirectional mappings for flexibility

# Output Format:

Return ONLY valid JSON with this structure:

```json
{{
  "applicant_fields": [
    {{
      "field_name": "age",
      "field_type": "int",
      "description": "Applicant's age in years",
      "example_values": [25, 45, 60],
      "common_aliases": ["age", "applicantAge", "yearsOld"]
    }},
    {{
      "field_name": "annualIncome",
      "field_type": "double",
      "description": "Applicant's annual income in dollars",
      "example_values": [50000, 75000, 120000],
      "common_aliases": ["income", "yearly_income", "annual_income", "salary"]
    }},
    {{
      "field_name": "health",
      "field_type": "String",
      "description": "Overall health status of applicant",
      "example_values": ["excellent", "good", "fair"],
      "common_aliases": ["healthStatus", "health_status", "health_condition", "health"]
    }},
    {{
      "field_name": "smoker",
      "field_type": "boolean",
      "description": "Whether applicant is a smoker",
      "example_values": [true, false],
      "common_aliases": ["smoker", "isSmoker", "smoking", "tobacco_user"]
    }}
  ],
  "policy_fields": [
    {{
      "field_name": "coverageAmount",
      "field_type": "double",
      "description": "Amount of coverage in dollars",
      "example_values": [250000, 500000, 1000000],
      "common_aliases": ["coverage", "coverageAmount", "insured_amount", "coverage_amt"]
    }},
    {{
      "field_name": "term",
      "field_type": "int",
      "description": "Policy term duration in years",
      "example_values": [10, 20, 30],
      "common_aliases": ["term", "termYears", "duration", "policy_term"]
    }},
    {{
      "field_name": "policyType",
      "field_type": "String",
      "description": "Type of insurance policy (e.g., term_life, whole_life, universal_life)",
      "example_values": ["term_life", "whole_life", "universal_life"],
      "common_aliases": ["policyType", "type", "policy_type", "insuranceType"]
    }}
  ],
  "field_mappings": {{
    "healthStatus": "health",
    "health_status": "health",
    "health_condition": "health",
    "termYears": "term",
    "term_years": "term",
    "duration": "term",
    "isSmoker": "smoker",
    "smoking": "smoker",
    "annualIncome": "annualIncome",
    "yearly_income": "annualIncome",
    "type": "policyType",
    "policy_type": "policyType",
    "insuranceType": "policyType"
  }}
}}
```

CRITICAL: Be comprehensive - extract ALL fields mentioned or implied by the policy rules. Missing a field will cause test failures.

Generate the schema now:"""

    def _parse_schema_response(self, response_text: str) -> Dict[str, Any]:
        """Parse schema from LLM response"""
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
                # Try to find JSON object directly
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end].strip()

            # Parse JSON
            schema = json.loads(json_text)

            # Validate structure
            if not isinstance(schema.get('applicant_fields'), list):
                raise ValueError("applicant_fields must be a list")
            if not isinstance(schema.get('policy_fields'), list):
                raise ValueError("policy_fields must be a list")
            if not isinstance(schema.get('field_mappings'), dict):
                raise ValueError("field_mappings must be a dictionary")

            return schema

        except Exception as e:
            logger.error(f"Error parsing schema JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            raise

    def _generate_minimal_schema(self, policy_type: str) -> Dict[str, Any]:
        """Generate minimal schema as fallback when LLM fails"""
        logger.info("Generating minimal schema as fallback...")

        return {
            "applicant_fields": [
                {
                    "field_name": "name",
                    "field_type": "String",
                    "description": "Applicant name",
                    "example_values": ["John Doe", "Jane Smith"],
                    "common_aliases": ["name", "applicantName", "full_name"]
                },
                {
                    "field_name": "age",
                    "field_type": "int",
                    "description": "Applicant age",
                    "example_values": [25, 45, 60],
                    "common_aliases": ["age", "applicantAge"]
                }
            ],
            "policy_fields": [
                {
                    "field_name": "policyType",
                    "field_type": "String",
                    "description": "Type of policy",
                    "example_values": ["term_life", "whole_life"],
                    "common_aliases": ["policyType", "type", "policy_type"]
                }
            ],
            "field_mappings": {
                "applicantAge": "age",
                "policy_type": "policyType"
            }
        }

    def generate_drools_declarations(self, schema: Dict[str, Any]) -> str:
        """
        Generate Drools DRL declare statements from schema

        Args:
            schema: Schema dictionary with applicant_fields and policy_fields

        Returns:
            String containing Drools declare statements
        """
        drl = ""

        # Generate Applicant declaration
        if schema.get('applicant_fields'):
            drl += "declare Applicant\n"
            for field in schema['applicant_fields']:
                field_name = field['field_name']
                field_type = field['field_type']
                drl += f"    {field_name}: {field_type}\n"
            drl += "end\n\n"

        # Generate Policy declaration
        if schema.get('policy_fields'):
            drl += "declare Policy\n"
            for field in schema['policy_fields']:
                field_name = field['field_name']
                field_type = field['field_type']
                drl += f"    {field_name}: {field_type}\n"
            drl += "end\n\n"

        # Always include Decision declaration (standard output)
        drl += """declare Decision
    decision: String
    approved: boolean
    reasons: java.util.List
    riskCategory: int
end
"""

        return drl
