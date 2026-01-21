"""
Hierarchical Rules Agent
Analyzes policy documents and generates hierarchical rules with parent-child dependencies
"""

import json
from typing import Dict, List, Any


class HierarchicalRulesAgent:
    """
    Uses LLM to generate hierarchical rules from policy documents.
    Rules are organized in a tree structure with parent-child dependencies.
    """

    def __init__(self, llm):
        """
        Initialize the agent with an LLM

        :param llm: Language model instance (e.g., ChatOpenAI)
        """
        self.llm = llm

    def generate_hierarchical_rules(self, policy_text: str, policy_type: str = "general") -> List[Dict[str, Any]]:
        """
        Generate hierarchical rules from policy document

        :param policy_text: Full text of the policy document
        :param policy_type: Type of policy (insurance, loan, etc.)
        :return: List of root-level rules with nested dependencies
        """

        prompt = f"""You are an expert underwriting rules analyst. Analyze the following {policy_type} policy document and generate a hierarchical structure of underwriting rules.

IMPORTANT INSTRUCTIONS:
1. Create a tree structure with parent rules and child dependencies
2. **LIMIT DEPTH TO 3 LEVELS MAXIMUM** (e.g., 1 → 1.1 → 1.1.1, then stop)
3. **KEEP TOTAL RULES UNDER 20** - focus on the most important rules only
4. Each rule should have:
   - id: Dot notation (e.g., "1", "1.1", "1.1.1")
   - name: Brief descriptive name (max 10 words)
   - description: Brief explanation (max 20 words)
   - expected: Brief condition (max 15 words)
   - actual: "To be evaluated" (standard placeholder)
   - confidence: 0.9 (use fixed value to save tokens)
   - passed: null
   - page_number: Integer (estimate if unsure)
   - clause_reference: Brief reference (e.g., "Art II, Sec 2.1")
   - dependencies: Array of child rules (max 3 levels deep)

5. Organize rules logically:
   - Top-level: 4-6 major categories (e.g., "Eligibility", "Risk Assessment", "Coverage")
   - Level 2: Key sub-checks (2-4 per parent)
   - Level 3: Specific validations (1-3 per level 2)

6. Use dot notation IDs that reflect the hierarchy

7. **CRITICAL**: Return ONLY valid JSON - no markdown, no explanation. Keep descriptions concise to avoid token limits.

POLICY DOCUMENT:
{policy_text[:15000]}

Return a JSON array of top-level rules with nested dependencies. Example structure:
[
  {{
    "id": "1",
    "name": "Eligibility Verification",
    "description": "Verify applicant meets all basic eligibility requirements",
    "expected": "All eligibility criteria met",
    "actual": "To be evaluated",
    "confidence": 0.95,
    "passed": null,
    "page_number": 3,
    "clause_reference": "Article II",
    "dependencies": [
      {{
        "id": "1.1",
        "name": "Age Requirement Check",
        "description": "Verify applicant age is within acceptable range",
        "expected": "Age between 18 and 65",
        "actual": "To be evaluated",
        "confidence": 0.98,
        "passed": null,
        "page_number": 3,
        "clause_reference": "Article II, Section 2.1",
        "dependencies": [
          {{
            "id": "1.1.1",
            "name": "Minimum Age Check",
            "description": "Verify applicant is at least 18 years old",
            "expected": "Age >= 18",
            "actual": "To be evaluated",
            "confidence": 0.99,
            "passed": null,
            "page_number": 3,
            "clause_reference": "Article II, Section 2.1.1",
            "dependencies": []
          }},
          {{
            "id": "1.1.2",
            "name": "Maximum Age Check",
            "description": "Verify applicant is not older than 65 years",
            "expected": "Age <= 65",
            "actual": "To be evaluated",
            "confidence": 0.99,
            "passed": null,
            "page_number": 3,
            "clause_reference": "Article II, Section 2.1.2",
            "dependencies": []
          }}
        ]
      }},
      {{
        "id": "1.2",
        "name": "Credit Score Check",
        "description": "Verify minimum credit score requirement",
        "expected": "Credit score >= 600",
        "actual": "To be evaluated",
        "confidence": 0.92,
        "passed": null,
        "page_number": 5,
        "clause_reference": "Article III, Section 3.1",
        "dependencies": []
      }}
    ]
  }}
]

CRITICAL: Include page_number and clause_reference for EVERY rule at all levels of the hierarchy. Look for section headers, article numbers, and clause references in the policy document.

Generate comprehensive hierarchical rules now:"""

        try:
            print("🤖 Invoking LLM to generate hierarchical rules...")

            # Get response from LLM
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)

            print(f"✓ LLM response received ({len(response_text)} characters)")

            # Clean up response - remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON response with error recovery
            try:
                hierarchical_rules = json.loads(response_text)
            except json.JSONDecodeError as parse_error:
                print(f"⚠ Initial JSON parse failed: {parse_error}")
                print(f"⚠ Attempting to repair truncated JSON...")

                # Try to repair truncated JSON
                response_text = self._repair_truncated_json(response_text)

                try:
                    hierarchical_rules = json.loads(response_text)
                    print(f"✓ Successfully repaired and parsed JSON")
                except json.JSONDecodeError as e:
                    # If repair fails, save the response for debugging and raise
                    print(f"✗ JSON repair failed: {e}")
                    print(f"Response preview (first 1000 chars): {response_text[:1000]}")
                    print(f"Response preview (last 500 chars): {response_text[-500:]}")
                    raise ValueError(f"LLM did not return valid JSON even after repair: {e}")

            # Validate structure
            if not isinstance(hierarchical_rules, list):
                raise ValueError("Expected a list of rules at the top level")

            # Count total rules
            def count_rules(rules):
                count = len(rules)
                for rule in rules:
                    if rule.get('dependencies'):
                        count += count_rules(rule['dependencies'])
                return count

            total_rules = count_rules(hierarchical_rules)
            print(f"✓ Generated {len(hierarchical_rules)} top-level rules with {total_rules} total rules in hierarchy")

            # Print tree structure for verification
            def print_tree(rules, indent=0):
                for rule in rules:
                    print(f"{'  ' * indent}├─ {rule['id']}: {rule['name']}")
                    if rule.get('dependencies'):
                        print_tree(rule['dependencies'], indent + 1)

            print("\n📋 Hierarchical Rules Structure:")
            print_tree(hierarchical_rules)

            return hierarchical_rules

        except Exception as e:
            print(f"✗ Error generating hierarchical rules: {e}")
            raise

    def _repair_truncated_json(self, json_text: str) -> str:
        """
        Attempt to repair truncated JSON by closing open brackets/braces and strings

        :param json_text: Potentially truncated JSON text
        :return: Repaired JSON text
        """
        import re

        # Find the last complete character
        json_text = json_text.rstrip()

        # Count open/close brackets and braces
        open_brackets = json_text.count('[')
        close_brackets = json_text.count(']')
        open_braces = json_text.count('{')
        close_braces = json_text.count('}')

        # Check if we're in the middle of a string (odd number of quotes before last char)
        # Find the last quote position
        last_quote_pos = max(json_text.rfind('"'), json_text.rfind("'"))

        if last_quote_pos > 0:
            # Count quotes before this position
            quotes_before = json_text[:last_quote_pos].count('"')

            # If odd number of quotes, we're in an unterminated string
            if quotes_before % 2 == 1:
                print(f"⚠ Detected unterminated string at position {last_quote_pos}")

                # Try to find a safe place to truncate
                # Look backwards for the last complete JSON object
                # Simple heuristic: find last "}," or last complete field

                # Find the last complete property before the truncation
                # Pattern: "field": "value" or "field": number or "field": {...}
                safe_cutoff = max(
                    json_text.rfind('},'),
                    json_text.rfind('],'),
                    json_text.rfind('",'),
                    json_text.rfind(': null,'),
                    json_text.rfind(': true,'),
                    json_text.rfind(': false,')
                )

                if safe_cutoff > 0:
                    print(f"⚠ Truncating JSON at safe position: {safe_cutoff}")
                    json_text = json_text[:safe_cutoff + 1]  # Keep the comma

                    # Recount after truncation
                    open_brackets = json_text.count('[')
                    close_brackets = json_text.count(']')
                    open_braces = json_text.count('{')
                    close_braces = json_text.count('}')

        # Remove incomplete fields at the end (various patterns)
        # Pattern 1: "field": (no value at all)
        json_text = re.sub(r',\s*"[^"]*"\s*:\s*$', '', json_text)

        # Pattern 2: "field": "incomplete_value (unterminated string)
        json_text = re.sub(r',\s*"[^"]*"\s*:\s*"[^"]*$', '', json_text)

        # Pattern 3: "field": { (incomplete object)
        json_text = re.sub(r',\s*"[^"]*"\s*:\s*\{\s*$', '', json_text)

        # Pattern 4: "field": [ (incomplete array)
        json_text = re.sub(r',\s*"[^"]*"\s*:\s*\[\s*$', '', json_text)

        # Pattern 5: "field":}  or "field":]  (missing value before close bracket)
        json_text = re.sub(r'"[^"]*"\s*:\s*([}\]])', r'\1', json_text)

        # Remove trailing commas before closing brackets
        json_text = re.sub(r',\s*([}\]])', r'\1', json_text)

        # Close unclosed braces
        if open_braces > close_braces:
            print(f"⚠ Closing {open_braces - close_braces} unclosed braces")
            json_text += '}' * (open_braces - close_braces)

        # Close unclosed brackets
        if open_brackets > close_brackets:
            print(f"⚠ Closing {open_brackets - close_brackets} unclosed brackets")
            json_text += ']' * (open_brackets - close_brackets)

        return json_text

    def validate_rule_structure(self, rule: Dict[str, Any]) -> bool:
        """
        Validate that a rule has the required structure

        :param rule: Rule dictionary to validate
        :return: True if valid, False otherwise
        """
        required_fields = ['id', 'name', 'description', 'expected', 'confidence']

        for field in required_fields:
            if field not in rule:
                print(f"⚠ Rule missing required field: {field}")
                return False

        # Validate dependencies if present
        if 'dependencies' in rule and rule['dependencies']:
            if not isinstance(rule['dependencies'], list):
                print(f"⚠ Rule dependencies must be a list")
                return False

            # Recursively validate child rules
            for child in rule['dependencies']:
                if not self.validate_rule_structure(child):
                    return False

        return True

    def flatten_hierarchical_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Flatten hierarchical rules into a list for easier processing
        (Maintains parent-child relationships via rule IDs)

        :param rules: Hierarchical rules list
        :return: Flattened list of all rules
        """
        flattened = []

        def flatten_recursive(rule_list, parent_id=None):
            for rule in rule_list:
                rule_copy = rule.copy()
                dependencies = rule_copy.pop('dependencies', [])

                if parent_id:
                    rule_copy['parent_rule_id'] = parent_id

                flattened.append(rule_copy)

                # Process children
                if dependencies:
                    flatten_recursive(dependencies, rule['id'])

        flatten_recursive(rules)
        return flattened
