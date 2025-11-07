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

    def __init__(self, llm):
        self.llm = llm

        self.rule_generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in insurance underwriting rules and Drools rule engine.

Given extracted policy data, generate executable Drools DRL (Drools Rule Language) rules.

IMPORTANT: Use 'declare' statements to define types directly in the DRL file. Do NOT import external Java classes.

The rules should follow this structure:

```drl
package com.underwriting.rules;

// Declare types directly in DRL (no external Java classes needed)
declare Applicant
    name: String
    age: int
    occupation: String
    healthConditions: String
end

declare Policy
    policyType: String
    coverageAmount: double
    term: int
end

declare Decision
    approved: boolean
    reason: String
    requiresManualReview: boolean
    premiumMultiplier: double
end

// Rules using the declared types
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

rule "Age Requirement Check"
    when
        $applicant : Applicant( age < 18 || age > 65 )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.setReason("Applicant age is outside acceptable range");
        update($decision);
end
```

Guidelines:
1. ALWAYS use 'declare' statements to define Applicant, Policy, and Decision types at the top of the DRL file
2. Do NOT use import statements for model classes
3. Create clear, specific rule names based on the extracted data
4. Include an "Initialize Decision" rule that creates the Decision object if it doesn't exist
5. Use appropriate conditions based on the extracted data
6. Make rules executable and testable
7. Add comments explaining complex logic
8. Handle edge cases and validation
9. Use proper getter/setter methods (e.g., setApproved(), setReason())

Return your response with:
1. Complete DRL rules in ```drl code blocks (including declare statements)
2. Brief explanation of the rules

DO NOT generate decision tables - only generate DRL rules."""),
            ("user", """Extracted policy data:

{extracted_data}

Generate complete, self-contained Drools DRL rules with 'declare' statements for all types.""")
        ])

        self.chain = self.rule_generation_prompt | self.llm

    def generate_rules(self, extracted_data: Dict) -> Dict[str, str]:
        """
        Generate Drools rules from extracted data

        :param extracted_data: Data extracted by Textract
        :return: Dictionary with 'drl', 'decision_table', and 'explanation' keys
        """
        try:
            result = self.chain.invoke({
                "extracted_data": json.dumps(extracted_data, indent=2)
            })

            # Parse LLM response to extract DRL and CSV
            content = result.content

            # Extract DRL (between ```drl or ```java and ```)
            drl = self._extract_code_block(content, 'drl') or \
                  self._extract_code_block(content, 'java')

            # Extract CSV (between ```csv and ```)
            decision_table = self._extract_code_block(content, 'csv')

            # Extract explanation (everything not in code blocks)
            explanation = self._extract_explanation(content)

            return {
                'drl': drl or "// No DRL rules generated",
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
            return None

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
