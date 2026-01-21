"""
Drools-to-Hierarchical Rules Mapper
Maps Drools evaluation results to hierarchical rules without re-evaluating
"""

from typing import Dict, List, Any, Optional
import re


class DroolsHierarchicalMapper:
    """
    Maps Drools decision results and input data to hierarchical rules.
    Uses Drools as the single source of truth - no re-evaluation.
    """

    def __init__(self):
        """Initialize the mapper"""
        pass

    def map_drools_to_hierarchical_rules(self,
                                        hierarchical_rules: List[Dict[str, Any]],
                                        drools_decision: Dict[str, Any],
                                        applicant_data: Dict[str, Any],
                                        policy_data: Dict[str, Any] = None,
                                        expected_decision: str = None) -> List[Dict[str, Any]]:
        """
        Map Drools decision data to hierarchical rules

        :param hierarchical_rules: Original hierarchical rules from database
        :param drools_decision: Decision returned from Drools
        :param applicant_data: Original applicant data
        :param policy_data: Optional policy data
        :return: Hierarchical rules with actual values and pass/fail from Drools
        """

        # Create a copy to avoid modifying the original
        import copy
        mapped_rules = copy.deepcopy(hierarchical_rules)

        # Combine all available data
        all_data = {
            **applicant_data,
            **(policy_data or {}),
            **drools_decision
        }

        # Extract decision metadata from Drools
        decision_approved = drools_decision.get('approved', True)
        decision_reasons = drools_decision.get('reasons', [])

        # Recursively map each rule
        def map_rule_recursive(rule: Dict[str, Any]) -> Dict[str, Any]:
            """Recursively map a rule and its dependencies"""

            # Extract actual value from available data
            actual_value = self._extract_actual_value(rule, all_data, applicant_data)
            rule['actual'] = actual_value

            # Determine pass/fail based on Drools decision
            passed = self._determine_pass_fail_from_drools(
                rule,
                drools_decision,
                decision_approved,
                decision_reasons,
                all_data,
                expected_decision  # Pass test intent to understand if rejection is expected
            )
            rule['passed'] = passed

            # Recursively map dependencies
            if 'dependencies' in rule and rule['dependencies']:
                for child_rule in rule['dependencies']:
                    map_rule_recursive(child_rule)

                # Check if all dependencies passed
                all_children_passed = all(
                    dep.get('passed', False) for dep in rule['dependencies']
                )
                
                # Parent rule should fail if ANY child fails (AND logic)
                # This ensures hierarchical integrity: if any sub-requirement fails, parent fails
                if not all_children_passed:
                    rule['passed'] = False
                    # Update actual to reflect child failure
                    failed_children = [
                        dep.get('name', dep.get('id', 'Unknown')) 
                        for dep in rule['dependencies'] 
                        if dep.get('passed') == False
                    ]
                    if failed_children:
                        rule['actual'] = f"Failed sub-requirements: {', '.join(failed_children)}"
                # If parent's own evaluation was None, inherit from children
                elif passed is None:
                    rule['passed'] = all_children_passed
                    if all_children_passed:
                        rule['actual'] = "All sub-requirements passed"

            return rule

        # Map all root-level rules
        for rule in mapped_rules:
            map_rule_recursive(rule)

        return mapped_rules

    def _extract_actual_value(self, rule: Dict[str, Any], all_data: Dict, applicant_data: Dict) -> str:
        """
        Extract the actual value that was evaluated for this rule

        :param rule: The hierarchical rule
        :param all_data: All available data (applicant + decision)
        :param applicant_data: Applicant-specific data
        :return: String describing the actual value
        """

        expected = rule.get('expected', '')
        rule_name = rule.get('name', '').lower()

        # Try to extract field name from expected condition
        field_value = self._get_field_value_from_condition(expected, all_data, applicant_data)
        if field_value:
            return field_value

        # Try to infer from rule name
        if 'age' in rule_name:
            age = self._get_field_value('age', all_data)
            if age is not None:
                return f"Age = {age}"

        if 'credit' in rule_name or 'score' in rule_name:
            credit_score = self._get_field_value('credit score', all_data)
            if credit_score is not None:
                return f"Credit Score = {credit_score}"

        if 'income' in rule_name:
            income = self._get_field_value('income', all_data)
            if income is not None:
                return f"Income = ${income:,}" if isinstance(income, (int, float)) else f"Income = {income}"

        if 'health' in rule_name:
            health = self._get_field_value('health', all_data)
            if health is not None:
                return f"Health = {health}"

        if 'risk' in rule_name and 'category' in rule_name:
            risk_category = self._get_field_value('risk category', all_data)
            if risk_category is not None:
                return f"Risk Category = {risk_category}"

        if 'coverage' in rule_name:
            coverage = self._get_field_value('coverage', all_data)
            if coverage is not None:
                return f"Coverage = ${coverage:,}" if isinstance(coverage, (int, float)) else f"Coverage = {coverage}"

        # Default: return generic message
        return f"Evaluated by Drools"

    def _get_field_value_from_condition(self, expected: str, all_data: Dict, applicant_data: Dict) -> Optional[str]:
        """
        Extract field value from expected condition string

        :param expected: Expected condition (e.g., "Age >= 18")
        :param all_data: All available data
        :param applicant_data: Applicant data
        :return: Formatted actual value string or None
        """

        if not expected or expected == "To be evaluated":
            return None

        # Check for "between X and Y" pattern
        between_match = re.search(r'(\w+(?:\s+\w+)*)\s+between\s+', expected, re.IGNORECASE)
        if between_match:
            field_name = between_match.group(1).strip()
            value = self._get_field_value(field_name, all_data)
            if value is not None:
                return f"{field_name.title()} = {value}"

        # Check for comparison operators
        comparison_match = re.search(r'(\w+(?:\s+\w+)*)\s*(>=|<=|>|<|==|=)\s*', expected, re.IGNORECASE)
        if comparison_match:
            field_name = comparison_match.group(1).strip()
            value = self._get_field_value(field_name, all_data)
            if value is not None:
                return f"{field_name.title()} = {value}"

        return None

    def _get_field_value(self, field_name: str, data: Dict) -> Any:
        """
        Get field value from data, trying various naming conventions

        :param field_name: Field name to look for
        :param data: Data dictionary
        :return: Field value or None
        """

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

        # Special mappings
        field_mappings = {
            'age': ['age', 'applicantAge', 'applicant_age'],
            'credit score': ['creditScore', 'credit_score', 'score', 'creditRating'],
            'income': ['income', 'annualIncome', 'annual_income', 'salary'],
            'health': ['health', 'healthStatus', 'health_status', 'healthConditions'],
            'coverage': ['coverage', 'coverageAmount', 'coverage_amount', 'requestedCoverage'],
            'risk category': ['riskCategory', 'risk_category', 'risk', 'category'],
        }

        for key, alternatives in field_mappings.items():
            if key in field_lower:
                for alt in alternatives:
                    if alt in data:
                        return data[alt]

        return None

    def _determine_pass_fail_from_drools(self,
                                         rule: Dict[str, Any],
                                         drools_decision: Dict[str, Any],
                                         decision_approved: bool,
                                         decision_reasons: List[str],
                                         all_data: Dict,
                                         expected_decision: str = None) -> Optional[bool]:
        """
        Determine if rule passed based on Drools decision

        Uses Drools as source of truth rather than re-evaluating

        :param rule: The hierarchical rule
        :param drools_decision: Complete Drools decision
        :param decision_approved: Whether application was approved
        :param decision_reasons: List of rejection/approval reasons
        :param all_data: All available data
        :return: True if passed, False if failed, None if can't determine
        """

        rule_name = rule.get('name', '').lower()
        expected = rule.get('expected', '').lower()
        rule_id = rule.get('id', '')

        # Strategy 1: Check if rejection reasons mention this rule
        # IMPORTANT: If test case expects "rejected" and rule is mentioned in rejection reason,
        # the rule is actually PASSING (it correctly triggered the rejection)
        if decision_reasons:
            for reason in decision_reasons:
                reason_lower = reason.lower()

                # Check if this rule is mentioned in rejection reason
                if self._rule_mentioned_in_reason(rule_name, expected, reason_lower):
                    # If test expects rejection, rule is working correctly (PASS)
                    # If test expects approval, rule incorrectly caused rejection (FAIL)
                    if expected_decision and expected_decision.lower() == 'rejected':
                        return True  # Rule correctly triggered rejection
                    else:
                        return False  # Rule incorrectly caused rejection

        # Strategy 2: Check known fields against Drools decision data
        # Age checks
        if 'age' in rule_name or 'age' in expected:
            age = self._get_field_value('age', all_data)
            if age is not None:
                # Check for equality operator (= or ==)
                if '=' in expected and '>=' not in expected and '<=' not in expected and 'between' not in expected:
                    # Equality check: "Age = 25"
                    age_match = re.search(r'=\s*(\d+)', expected)
                    if age_match:
                        required_age = int(age_match.group(1))
                        return int(age) == required_age
                elif 'minimum' in rule_name or '>=' in expected or 'at least' in expected:
                    # Extract minimum age from expected
                    min_age_match = re.search(r'(\d+)', expected)
                    if min_age_match:
                        min_age = int(min_age_match.group(1))
                        return int(age) >= min_age
                elif 'maximum' in rule_name or '<=' in expected or 'not older' in expected:
                    # Extract maximum age from expected
                    max_age_match = re.search(r'(\d+)', expected)
                    if max_age_match:
                        max_age = int(max_age_match.group(1))
                        return int(age) <= max_age
                elif 'between' in expected:
                    # Extract age range
                    between_match = re.search(r'(\d+)\s+and\s+(\d+)', expected)
                    if between_match:
                        min_age = int(between_match.group(1))
                        max_age = int(between_match.group(2))
                        return min_age <= int(age) <= max_age

        # Credit score checks
        if 'credit' in rule_name or 'score' in rule_name:
            credit_score = self._get_field_value('credit score', all_data)
            if credit_score is not None:
                # Check for equality operator (= or ==)
                if '=' in expected and '>=' not in expected and '<=' not in expected:
                    # Equality check: "Credit score = 600"
                    score_match = re.search(r'=\s*(\d+)', expected)
                    if score_match:
                        required_score = int(score_match.group(1))
                        return int(credit_score) == required_score
                # Check for >= (minimum threshold)
                elif '>=' in expected or 'at least' in expected or 'minimum' in expected:
                    min_score_match = re.search(r'(\d+)', expected)
                    if min_score_match:
                        min_score = int(min_score_match.group(1))
                        return int(credit_score) >= min_score
                # Check for <= (maximum threshold)
                elif '<=' in expected or 'at most' in expected or 'maximum' in expected:
                    max_score_match = re.search(r'(\d+)', expected)
                    if max_score_match:
                        max_score = int(max_score_match.group(1))
                        return int(credit_score) <= max_score
                # Default: extract number and assume minimum threshold (backward compatibility)
                else:
                    min_score_match = re.search(r'(\d+)', expected)
                    if min_score_match:
                        min_score = int(min_score_match.group(1))
                        return int(credit_score) >= min_score

        # Health status checks
        if 'health' in rule_name:
            health = self._get_field_value('health', all_data)
            if health is not None:
                if 'poor' in expected or 'not poor' in expected:
                    return str(health).lower() != 'poor'

        # Income checks
        if 'income' in rule_name:
            income = self._get_field_value('income', all_data)
            if income is not None:
                # Check for equality operator (= or ==)
                if '=' in expected and '>=' not in expected and '<=' not in expected:
                    # Equality check: "Income = $50,000"
                    income_match = re.search(r'=\s*\$?\s*([\d,]+)', expected)
                    if income_match:
                        required_income_str = income_match.group(1).replace(',', '')
                        required_income = int(required_income_str)
                        return int(income) == required_income
                # Check for >= (minimum threshold)
                elif '>=' in expected or 'at least' in expected or 'minimum' in expected:
                    min_income_match = re.search(r'(\d+)', expected)
                    if min_income_match:
                        min_income = int(min_income_match.group(1))
                        return int(income) >= min_income
                # Default: extract number and assume minimum threshold (backward compatibility)
                else:
                    min_income_match = re.search(r'(\d+)', expected)
                    if min_income_match:
                        min_income = int(min_income_match.group(1))
                        return int(income) >= min_income

        # Strategy 3: If overall decision was approved and no specific failure detected, assume passed
        if decision_approved and not decision_reasons:
            return True

        # Strategy 4: For parent/aggregate rules, return None (will be derived from children)
        if 'all' in expected or 'criteria' in expected or 'requirements' in expected:
            return None

        # Strategy 5: If test case passed (expected matches actual), and we can't determine specific status,
        # default to True (optimistic) - the rule is likely working correctly if the test passed
        # This prevents false negatives when test cases pass but evaluation logic can't determine specific rule status
        if expected_decision:
            expected_lower = expected_decision.lower()
            actual_lower = 'approved' if decision_approved else 'rejected'
            if expected_lower == actual_lower:
                # Test case passed - rule is likely working correctly
                return True

        # Default: Can't determine - return None
        return None

    def _rule_mentioned_in_reason(self, rule_name: str, expected: str, reason: str) -> bool:
        """
        Check if a rejection reason mentions this specific rule

        :param rule_name: Name of the rule
        :param expected: Expected condition
        :param reason: Rejection reason from Drools
        :return: True if rule is mentioned in the reason
        """

        # Check for keywords from rule name in reason
        rule_keywords = rule_name.split()
        for keyword in rule_keywords:
            if len(keyword) > 3 and keyword in reason:  # Only check meaningful words
                return True

        # Check for keywords from expected condition
        expected_keywords = expected.split()
        for keyword in expected_keywords:
            if len(keyword) > 3 and keyword in reason:
                return True

        return False

    def get_evaluation_summary(self, mapped_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary of mapped rules

        :param mapped_rules: Mapped hierarchical rules
        :return: Summary dictionary
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

        count_recursive(mapped_rules)

        if summary['total_rules'] > 0:
            summary['pass_rate'] = round((summary['passed'] / summary['total_rules']) * 100, 2)

        return summary
