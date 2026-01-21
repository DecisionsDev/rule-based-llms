"""
Hierarchical Rules Evaluator
Evaluates application data against hierarchical rules and populates actual values and pass/fail status
"""

import re
from typing import Dict, List, Any, Optional


class HierarchicalRulesEvaluator:
    """
    Evaluates application data against hierarchical rules.
    Populates 'actual' values and 'passed' status for each rule in the tree.
    """

    def __init__(self):
        """Initialize the evaluator"""
        pass

    def evaluate_rules(self, hierarchical_rules: List[Dict[str, Any]],
                      applicant_data: Dict[str, Any],
                      policy_data: Dict[str, Any] = None,
                      decision_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Evaluate application data against hierarchical rules

        :param hierarchical_rules: List of root-level rules with nested dependencies
        :param applicant_data: Application data to evaluate
        :param policy_data: Optional policy-specific data
        :param decision_data: Optional decision result from rule engine
        :return: Rules tree with actual values and passed status populated
        """

        # Create a copy to avoid modifying the original
        import copy
        evaluated_rules = copy.deepcopy(hierarchical_rules)

        # Combine all data sources for evaluation
        all_data = {
            'applicant': applicant_data,
            'policy': policy_data or {},
            'decision': decision_data or {}
        }

        # Recursively evaluate each rule
        def evaluate_rule_recursive(rule: Dict[str, Any]) -> Dict[str, Any]:
            """Recursively evaluate a rule and its dependencies"""

            # Extract expected condition
            expected = rule.get('expected', '')

            # Evaluate the rule based on expected condition
            actual_value, passed = self._evaluate_condition(expected, all_data, applicant_data)

            # Update rule with evaluation results
            rule['actual'] = actual_value
            rule['passed'] = passed

            # If rule has dependencies, evaluate them too
            if 'dependencies' in rule and rule['dependencies']:
                for child_rule in rule['dependencies']:
                    evaluate_rule_recursive(child_rule)

                # Check if all dependencies passed (for parent rule logic)
                all_deps_passed = all(
                    dep.get('passed', False)
                    for dep in rule['dependencies']
                )

                # If any dependency failed, parent might need to reflect that
                # (unless parent has its own specific check)
                if not all_deps_passed and passed is None:
                    rule['passed'] = False
                    rule['actual'] = f"One or more sub-requirements failed"

            return rule

        # Evaluate all root-level rules
        for rule in evaluated_rules:
            evaluate_rule_recursive(rule)

        return evaluated_rules

    def _evaluate_condition(self, expected: str, all_data: Dict, applicant_data: Dict) -> tuple:
        """
        Evaluate a single condition and return (actual_value, passed)

        :param expected: Expected condition string (e.g., "Age >= 18")
        :param all_data: All available data
        :param applicant_data: Applicant-specific data
        :return: Tuple of (actual_value_string, passed_boolean)
        """

        if not expected or expected == "To be evaluated":
            return ("Not evaluated", None)

        try:
            # Try to extract field name and comparison from expected
            # Common patterns:
            # - "Age >= 18"
            # - "Age between 18 and 65"
            # - "Credit score >= 600"
            # - "All checks pass"
            # - "All criteria met"

            # Check for "between X and Y" pattern
            between_match = re.search(r'(\w+(?:\s+\w+)*)\s+between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)', expected, re.IGNORECASE)
            if between_match:
                field_name = between_match.group(1).strip().lower()
                min_val = float(between_match.group(2))
                max_val = float(between_match.group(3))

                actual_val = self._get_field_value(field_name, applicant_data)
                if actual_val is not None:
                    try:
                        actual_num = float(actual_val)
                        passed = min_val <= actual_num <= max_val
                        return (f"{field_name.title()} = {actual_val}", passed)
                    except:
                        return (f"{field_name.title()} = {actual_val}", None)
                else:
                    return (f"{field_name.title()} not provided", False)

            # Check for comparison operators: >=, <=, >, <, =, ==
            comparison_match = re.search(r'(\w+(?:\s+\w+)*)\s*(>=|<=|>|<|==|=)\s*(\d+(?:\.\d+)?|\w+)', expected, re.IGNORECASE)
            if comparison_match:
                field_name = comparison_match.group(1).strip().lower()
                operator = comparison_match.group(2)
                expected_val = comparison_match.group(3)

                actual_val = self._get_field_value(field_name, applicant_data)

                if actual_val is not None:
                    passed = self._compare_values(actual_val, operator, expected_val)
                    return (f"{field_name.title()} = {actual_val}", passed)
                else:
                    return (f"{field_name.title()} not provided", False)

            # Check for general validation phrases
            if any(phrase in expected.lower() for phrase in ['all checks pass', 'all criteria met', 'all requirements met']):
                # This is likely a parent rule - its status depends on children
                return ("Evaluated based on sub-requirements", None)

            # Default: Can't parse, mark as not evaluated
            return (f"Condition: {expected}", None)

        except Exception as e:
            return (f"Evaluation error: {str(e)}", None)

    def _get_field_value(self, field_name: str, data: Dict) -> Any:
        """
        Get field value from data, trying various naming conventions

        :param field_name: Field name to look for (e.g., "age", "credit score")
        :param data: Data dictionary
        :return: Field value or None
        """

        # Normalize field name
        field_lower = field_name.lower().strip()

        # Try direct lookup (various formats)
        lookups = [
            field_lower,
            field_lower.replace(' ', '_'),
            field_lower.replace(' ', ''),
            ''.join(word.capitalize() for word in field_lower.split()),  # camelCase
            field_lower.replace(' ', '-')
        ]

        for lookup in lookups:
            if lookup in data:
                return data[lookup]

        # Try case-insensitive search
        for key, value in data.items():
            if key.lower() == field_lower:
                return value

        # Special mappings for common fields
        field_mappings = {
            'age': ['age', 'applicant_age', 'applicantAge'],
            'credit score': ['creditScore', 'credit_score', 'score', 'creditRating'],
            'income': ['income', 'annual_income', 'annualIncome', 'salary'],
            'health': ['health', 'healthStatus', 'health_status'],
            'coverage': ['coverage', 'coverageAmount', 'coverage_amount', 'requestedCoverage'],
        }

        for key, alternatives in field_mappings.items():
            if key in field_lower:
                for alt in alternatives:
                    if alt in data:
                        return data[alt]

        return None

    def _compare_values(self, actual: Any, operator: str, expected: Any) -> bool:
        """
        Compare two values based on operator

        :param actual: Actual value
        :param operator: Comparison operator (>=, <=, >, <, ==, =)
        :param expected: Expected value
        :return: True if comparison passes, False otherwise
        """

        try:
            # Try numeric comparison first
            try:
                actual_num = float(actual)
                expected_num = float(expected)

                if operator == '>=' or operator == '≥':
                    return actual_num >= expected_num
                elif operator == '<=' or operator == '≤':
                    return actual_num <= expected_num
                elif operator == '>':
                    return actual_num > expected_num
                elif operator == '<':
                    return actual_num < expected_num
                elif operator in ['==', '=']:
                    return actual_num == expected_num

            except ValueError:
                # Not numeric, try string comparison
                actual_str = str(actual).lower()
                expected_str = str(expected).lower()

                if operator in ['==', '=']:
                    return actual_str == expected_str
                else:
                    # For string comparisons with <, >, etc., use alphabetical
                    if operator == '>=':
                        return actual_str >= expected_str
                    elif operator == '<=':
                        return actual_str <= expected_str
                    elif operator == '>':
                        return actual_str > expected_str
                    elif operator == '<':
                        return actual_str < expected_str

        except Exception:
            pass

        return False

    def get_evaluation_summary(self, evaluated_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of the evaluation

        :param evaluated_rules: Evaluated rules tree
        :return: Summary dictionary with pass/fail counts
        """

        summary = {
            'total_rules': 0,
            'passed': 0,
            'failed': 0,
            'not_evaluated': 0,
            'pass_rate': 0.0,
            'failed_rules': []
        }

        def count_recursive(rules):
            for rule in rules:
                summary['total_rules'] += 1

                if rule.get('passed') is True:
                    summary['passed'] += 1
                elif rule.get('passed') is False:
                    summary['failed'] += 1
                    summary['failed_rules'].append({
                        'id': rule['id'],
                        'name': rule['name'],
                        'expected': rule.get('expected'),
                        'actual': rule.get('actual')
                    })
                else:
                    summary['not_evaluated'] += 1

                if 'dependencies' in rule and rule['dependencies']:
                    count_recursive(rule['dependencies'])

        count_recursive(evaluated_rules)

        if summary['total_rules'] > 0:
            summary['pass_rate'] = round((summary['passed'] / summary['total_rules']) * 100, 2)

        return summary
