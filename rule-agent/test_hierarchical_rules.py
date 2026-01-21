#!/usr/bin/env python3
"""
Test script for hierarchical rules functionality
Run this after migrating the database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from DatabaseService import get_database_service

# Sample hierarchical rules data
sample_rules = [
    {
        "id": "1",
        "name": "Eligibility Check",
        "description": "Verify applicant meets all eligibility requirements",
        "expected": "All checks pass",
        "actual": "Passed",
        "confidence": 0.95,
        "passed": True,
        "dependencies": [
            {
                "id": "1.1",
                "name": "Age Verification",
                "description": "Check minimum age requirement",
                "expected": "Age >= 18",
                "actual": "Age = 25",
                "confidence": 0.98,
                "passed": True,
                "dependencies": []
            },
            {
                "id": "1.2",
                "name": "Income Verification",
                "description": "Verify minimum income requirement",
                "expected": "Income >= $50,000",
                "actual": "Income = $75,000",
                "confidence": 0.92,
                "passed": True,
                "dependencies": [
                    {
                        "id": "1.2.1",
                        "name": "Employment Status",
                        "description": "Verify employment status",
                        "expected": "Employed",
                        "actual": "Full-time employed",
                        "confidence": 0.99,
                        "passed": True,
                        "dependencies": []
                    }
                ]
            }
        ]
    },
    {
        "id": "2",
        "name": "Credit Check",
        "description": "Verify credit score meets requirements",
        "expected": "Credit Score >= 650",
        "actual": "Credit Score = 720",
        "confidence": 0.88,
        "passed": True,
        "dependencies": []
    }
]


def test_hierarchical_rules():
    """Test hierarchical rules save and retrieve operations"""
    db_service = get_database_service()

    # Test parameters
    bank_id = "chase"
    policy_type_id = "insurance"

    print("=" * 60)
    print("Testing Hierarchical Rules Functionality")
    print("=" * 60)

    # Test 1: Save hierarchical rules
    print("\n[1] Saving hierarchical rules...")
    try:
        created_ids = db_service.save_hierarchical_rules(
            bank_id=bank_id,
            policy_type_id=policy_type_id,
            rules_tree=sample_rules,
            document_hash="test_hash_123",
            source_document="test_policy.pdf"
        )
        print(f"✓ Successfully saved {len(created_ids)} rules")
        print(f"  Created rule IDs: {created_ids}")
    except Exception as e:
        print(f"✗ Failed to save rules: {e}")
        return False

    # Test 2: Retrieve hierarchical rules
    print("\n[2] Retrieving hierarchical rules...")
    try:
        retrieved_rules = db_service.get_hierarchical_rules(
            bank_id=bank_id,
            policy_type_id=policy_type_id
        )
        print(f"✓ Successfully retrieved {len(retrieved_rules)} top-level rules")

        # Print tree structure
        def print_rule_tree(rules, indent=0):
            for rule in rules:
                prefix = "  " * indent + "├─ "
                print(f"{prefix}{rule['id']}: {rule['name']}")
                print(f"{'  ' * indent}   Expected: {rule['expected']}, Actual: {rule['actual']}")
                print(f"{'  ' * indent}   Confidence: {rule['confidence']}, Passed: {rule['passed']}")
                if rule.get('dependencies'):
                    print_rule_tree(rule['dependencies'], indent + 1)

        print("\n  Rule Tree:")
        print_rule_tree(retrieved_rules)

    except Exception as e:
        print(f"✗ Failed to retrieve rules: {e}")
        return False

    # Test 3: Verify rule structure
    print("\n[3] Verifying rule structure...")
    if len(retrieved_rules) == 2:
        print("✓ Correct number of top-level rules")
    else:
        print(f"✗ Expected 2 top-level rules, got {len(retrieved_rules)}")
        return False

    # Check first rule has dependencies
    first_rule = retrieved_rules[0]
    if len(first_rule.get('dependencies', [])) == 2:
        print("✓ First rule has correct number of dependencies")
    else:
        print(f"✗ Expected 2 dependencies, got {len(first_rule.get('dependencies', []))}")
        return False

    # Check nested dependency
    nested_deps = first_rule['dependencies'][1].get('dependencies', [])
    if len(nested_deps) == 1:
        print("✓ Nested dependency structure is correct")
    else:
        print(f"✗ Expected 1 nested dependency, got {len(nested_deps)}")
        return False

    # Test 4: Delete hierarchical rules
    print("\n[4] Cleaning up - deleting hierarchical rules...")
    try:
        deleted_count = db_service.delete_hierarchical_rules(
            bank_id=bank_id,
            policy_type_id=policy_type_id
        )
        print(f"✓ Successfully deleted {deleted_count} rules")
    except Exception as e:
        print(f"✗ Failed to delete rules: {e}")
        return False

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_hierarchical_rules()
    sys.exit(0 if success else 1)
