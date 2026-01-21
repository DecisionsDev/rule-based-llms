"""
Hierarchical Rules to DRL Converter
Converts hierarchical rules (with expected conditions) back to executable Drools DRL format
"""

from typing import Dict, List, Any
import re


class HierarchicalToDRLConverter:
    """
    Converts hierarchical rules from database to executable Drools DRL rules.
    Supports converting updated expected values into DRL conditions.
    """

    def __init__(self):
        """Initialize the converter"""
        self.field_mappings = {
            'age': 'age',
            'credit score': 'creditScore',
            'credit': 'creditScore',
            'score': 'creditScore',
            'income': 'annualIncome',
            'annual income': 'annualIncome',
            'health': 'health',
            'health status': 'health',
            'smoking': 'smoking',
            'smoker': 'smoking',
            'coverage': 'coverageAmount',
            'coverage amount': 'coverageAmount',
            'debt to income': 'debtToIncomeRatio',
            'dti': 'debtToIncomeRatio',
        }

    def convert_to_drl(self, hierarchical_rules: List[Dict[str, Any]], 
                       package_name: str = "com.underwriting.rules") -> str:
        """
        Convert hierarchical rules to complete DRL format
        
        :param hierarchical_rules: List of root-level hierarchical rules
        :param package_name: DRL package name
        :return: Complete DRL string
        """
        
        drl_lines = []
        
        # Package declaration
        drl_lines.append(f"package {package_name};")
        drl_lines.append("")
        
        # Type declarations
        drl_lines.extend(self._generate_type_declarations())
        drl_lines.append("")
        
        # Initialization rule
        drl_lines.extend(self._generate_initialization_rule())
        drl_lines.append("")
        
        # Convert hierarchical rules to DRL rules
        rule_number = 1
        for root_rule in hierarchical_rules:
            rules_from_tree = self._convert_rule_tree_to_drl(root_rule, rule_number)
            drl_lines.extend(rules_from_tree)
            drl_lines.append("")
            rule_number += len(rules_from_tree)
        
        return "\n".join(drl_lines)

    def _generate_type_declarations(self) -> List[str]:
        """Generate standard type declarations for DRL"""
        return [
            "// ============================================================================",
            "// TYPE DECLARATIONS",
            "// ============================================================================",
            "",
            "declare Applicant",
            "    age: int",
            "    creditScore: int",
            "    annualIncome: double",
            "    health: String",
            "    smoking: boolean",
            "    debtToIncomeRatio: double",
            "end",
            "",
            "declare Policy",
            "    policyType: String",
            "    coverageAmount: double",
            "    term: int",
            "end",
            "",
            "declare Decision",
            "    approved: boolean",
            "    reasons: java.util.List",
            "end",
        ]

    def _generate_initialization_rule(self) -> List[str]:
        """Generate initialization rule"""
        return [
            "// ============================================================================",
            "// INITIALIZATION",
            "// ============================================================================",
            "",
            "rule \"Initialize Decision\"",
            "    salience 10000",
            "    when",
            "        not Decision()",
            "    then",
            "        Decision decision = new Decision();",
            "        decision.setApproved(true);",
            "        decision.setReasons(new java.util.ArrayList());",
            "        insert(decision);",
            "end",
        ]

    def _convert_rule_tree_to_drl(self, rule: Dict[str, Any], base_salience: int = 8000) -> List[str]:
        """
        Convert a hierarchical rule (and its dependencies) to DRL rules
        
        :param rule: Hierarchical rule with optional dependencies
        :param base_salience: Base salience value
        :return: List of DRL rule strings
        """
        drl_rules = []
        
        # Convert current rule
        rule_drl = self._convert_single_rule_to_drl(rule, base_salience)
        if rule_drl:
            drl_rules.extend(rule_drl)
        
        # Convert dependencies (children) with lower salience
        if rule.get('dependencies'):
            for child_rule in rule['dependencies']:
                child_rules = self._convert_rule_tree_to_drl(child_rule, base_salience - 100)
                drl_rules.extend(child_rules)
        
        return drl_rules

    def _convert_single_rule_to_drl(self, rule: Dict[str, Any], salience: int) -> List[str]:
        """
        Convert a single hierarchical rule to DRL format
        
        :param rule: Single hierarchical rule
        :param salience: Salience value for this rule
        :return: List of DRL lines for this rule
        """
        rule_name = rule.get('name', 'Unnamed Rule')
        expected = rule.get('expected', '')
        description = rule.get('description', '')
        
        # Skip parent/aggregate rules without specific conditions
        if not expected or expected.lower() in ['to be evaluated', 'n/a', 'none']:
            return []
        
        # Parse the expected condition
        condition = self._parse_expected_to_condition(expected)
        if not condition:
            return []
        
        # Determine if this is a rejection rule or approval rule
        is_rejection = self._is_rejection_rule(rule_name, description, expected)
        
        drl_lines = [
            f"rule \"{rule_name}\"",
            f"    salience {salience}",
            "    when",
            f"        $applicant : Applicant( {condition} )",
            "        $decision : Decision()",
            "    then"
        ]
        
        if is_rejection:
            # Rejection rule
            rejection_message = self._generate_rejection_message(rule_name, expected, description)
            drl_lines.extend([
                "        $decision.setApproved(false);",
                f"        $decision.getReasons().add(\"{rejection_message}\");",
                "        update($decision);",
            ])
        else:
            # Approval/passing rule (optional - could set flags or do nothing)
            drl_lines.extend([
                f"        // {description or 'Rule passed'}",
            ])
        
        drl_lines.append("end")
        
        return drl_lines

    def _parse_expected_to_condition(self, expected: str) -> str:
        """
        Parse expected condition string to DRL condition
        
        Examples:
        - "Age >= 18" → "age >= 18"
        - "Credit score = 600" → "creditScore == 600"
        - "Age between 18 and 65" → "age >= 18, age <= 65"
        - "Income >= $50,000" → "annualIncome >= 50000"
        
        :param expected: Expected condition string
        :return: DRL condition string
        """
        expected_lower = expected.lower().strip()
        
        # Check for "between X and Y" pattern
        between_match = re.search(r'(\w+(?:\s+\w+)*)\s+between\s+(\d+)\s+and\s+(\d+)', expected_lower)
        if between_match:
            field_name = between_match.group(1).strip()
            min_val = between_match.group(2)
            max_val = between_match.group(3)
            drl_field = self._map_field_name(field_name)
            return f"{drl_field} >= {min_val}, {drl_field} <= {max_val}"
        
        # Check for comparison operators: >=, <=, >, <, =, ==
        comparison_match = re.search(r'(\w+(?:\s+\w+)*)\s*(>=|<=|>|<|==|=)\s*\$?\s*([\d,]+)', expected_lower)
        if comparison_match:
            field_name = comparison_match.group(1).strip()
            operator = comparison_match.group(2).strip()
            value = comparison_match.group(3).replace(',', '')
            
            drl_field = self._map_field_name(field_name)
            
            # Convert = to == for DRL
            if operator == '=':
                operator = '=='
            
            return f"{drl_field} {operator} {value}"
        
        # Check for boolean fields
        if 'smoking' in expected_lower or 'smoker' in expected_lower:
            if 'not' in expected_lower or 'non' in expected_lower:
                return "smoking == false"
            else:
                return "smoking == true"
        
        # Check for string comparisons
        string_match = re.search(r'(\w+(?:\s+\w+)*)\s*(?:is|equals?|=)\s*["\']?(\w+)["\']?', expected_lower)
        if string_match:
            field_name = string_match.group(1).strip()
            value = string_match.group(2).strip()
            drl_field = self._map_field_name(field_name)
            return f'{drl_field} == "{value}"'
        
        # Default: couldn't parse
        return ""

    def _map_field_name(self, field_name: str) -> str:
        """
        Map human-readable field name to DRL field name
        
        :param field_name: Human-readable field name
        :return: DRL field name
        """
        field_lower = field_name.lower().strip()
        
        # Direct lookup
        if field_lower in self.field_mappings:
            return self.field_mappings[field_lower]
        
        # Try partial matches
        for key, value in self.field_mappings.items():
            if key in field_lower:
                return value
        
        # Default: convert to camelCase
        words = field_lower.split()
        if len(words) > 1:
            return words[0] + ''.join(word.capitalize() for word in words[1:])
        
        return field_lower

    def _is_rejection_rule(self, rule_name: str, description: str, expected: str) -> bool:
        """
        Determine if this is a rejection rule
        
        :param rule_name: Rule name
        :param description: Rule description
        :param expected: Expected condition
        :return: True if rejection rule
        """
        reject_keywords = [
            'reject', 'minimum', 'maximum', 'required', 'must be',
            'cannot', 'not allowed', 'ineligible', 'fail'
        ]
        
        text_to_check = f"{rule_name} {description} {expected}".lower()
        
        for keyword in reject_keywords:
            if keyword in text_to_check:
                return True
        
        # Check for comparison operators that imply requirements
        if any(op in expected for op in ['>=', '<=', '>', '<', '=']):
            return True
        
        return False

    def _generate_rejection_message(self, rule_name: str, expected: str, description: str) -> str:
        """
        Generate a clear rejection message
        
        :param rule_name: Rule name
        :param expected: Expected condition
        :param description: Rule description
        :return: Rejection message string
        """
        if description and len(description) < 100:
            return description
        
        # Generate from expected condition
        if 'between' in expected.lower():
            return f"{rule_name}: {expected}"
        elif '>=' in expected:
            return f"{rule_name}: Minimum requirement not met ({expected})"
        elif '<=' in expected:
            return f"{rule_name}: Maximum limit exceeded ({expected})"
        elif '==' in expected or '=' in expected:
            return f"{rule_name}: Required value not matched ({expected})"
        
        return f"{rule_name} requirement not met"

    def update_single_rule_in_drl(self, drl_content: str, rule_name: str, 
                                   new_expected: str) -> str:
        """
        Update a single rule in existing DRL content
        
        :param drl_content: Existing DRL content
        :param rule_name: Name of rule to update
        :param new_expected: New expected condition
        :return: Updated DRL content
        """
        # Parse the new expected condition
        new_condition = self._parse_expected_to_condition(new_expected)
        if not new_condition:
            return drl_content
        
        # Find and replace the rule
        # Pattern: rule "RuleName" ... when ... $applicant : Applicant( OLD_CONDITION ) ... then ... end
        pattern = rf'(rule\s+"{re.escape(rule_name)}".*?when.*?\$applicant\s*:\s*Applicant\(\s*)([^)]+)(\s*\))'
        
        def replacer(match):
            return f"{match.group(1)}{new_condition}{match.group(3)}"
        
        updated_drl = re.sub(pattern, replacer, drl_content, flags=re.DOTALL)
        
        return updated_drl

