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
import pandas as pd
import re
from typing import Dict, List
from datetime import datetime
import tempfile
import os


class ExcelRulesExporter:
    """
    Exports Drools DRL rules to Excel spreadsheet format for easy viewing and auditing
    """

    def __init__(self):
        pass

    def parse_drl_rules(self, drl_content: str) -> List[Dict]:
        """
        Parse DRL content and extract rule information

        :param drl_content: DRL file content
        :return: List of rule dictionaries
        """
        rules = []

        # Split DRL content by rule definitions
        rule_pattern = r'rule\s+"([^"]+)"(.*?)end'
        matches = re.findall(rule_pattern, drl_content, re.DOTALL)

        for rule_name, rule_body in matches:
            # Extract when clause (conditions)
            when_match = re.search(r'when(.*?)then', rule_body, re.DOTALL)
            when_clause = when_match.group(1).strip() if when_match else ""

            # Extract then clause (actions)
            then_match = re.search(r'then(.*)', rule_body, re.DOTALL)
            then_clause = then_match.group(1).strip() if then_match else ""

            # Extract salience (priority)
            salience_match = re.search(r'salience\s+(-?\d+)', rule_body)
            salience = salience_match.group(1) if salience_match else "0"

            # Extract attributes
            attributes = []
            if 'no-loop' in rule_body:
                attributes.append('no-loop')
            if 'lock-on-active' in rule_body:
                attributes.append('lock-on-active')

            rules.append({
                'Rule Name': rule_name,
                'Priority (Salience)': salience,
                'Conditions (When)': self._clean_text(when_clause),
                'Actions (Then)': self._clean_text(then_clause),
                'Attributes': ', '.join(attributes) if attributes else 'None'
            })

        return rules

    def _clean_text(self, text: str) -> str:
        """Clean up DRL text for display in Excel"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def create_excel_file(self, drl_content: str, bank_id: str, policy_type: str,
                         container_id: str, version: str) -> str:
        """
        Create Excel file from DRL rules

        :param drl_content: DRL file content
        :param bank_id: Bank identifier
        :param policy_type: Policy type
        :param container_id: Container ID
        :param version: Version string
        :return: Path to created Excel file (temporary)
        """
        # Parse DRL rules
        rules = self.parse_drl_rules(drl_content)

        # Create temporary Excel file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{bank_id}_{policy_type}_rules_{timestamp}.xlsx"
        temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        temp_file.close()
        excel_path = temp_file.name

        # Create Excel writer
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Create Summary sheet
            summary_data = {
                'Property': ['Bank ID', 'Policy Type', 'Container ID', 'Version',
                            'Generated Date', 'Total Rules'],
                'Value': [
                    bank_id,
                    policy_type,
                    container_id,
                    version,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    str(len(rules))
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Format Summary sheet
            worksheet = writer.sheets['Summary']
            worksheet.column_dimensions['A'].width = 20
            worksheet.column_dimensions['B'].width = 50

            # Create Rules sheet
            if rules:
                rules_df = pd.DataFrame(rules)
                rules_df.to_excel(writer, sheet_name='Rules', index=False)

                # Format Rules sheet
                rules_worksheet = writer.sheets['Rules']
                rules_worksheet.column_dimensions['A'].width = 30  # Rule Name
                rules_worksheet.column_dimensions['B'].width = 15  # Priority
                rules_worksheet.column_dimensions['C'].width = 60  # Conditions
                rules_worksheet.column_dimensions['D'].width = 60  # Actions
                rules_worksheet.column_dimensions['E'].width = 20  # Attributes

                # Enable text wrapping for better readability
                from openpyxl.styles import Alignment
                for row in rules_worksheet.iter_rows(min_row=2, max_row=len(rules)+1):
                    for cell in row:
                        cell.alignment = Alignment(wrap_text=True, vertical='top')
            else:
                # If no rules parsed, create empty sheet with message
                empty_df = pd.DataFrame({
                    'Message': ['No rules found in DRL file or parsing failed']
                })
                empty_df.to_excel(writer, sheet_name='Rules', index=False)

            # Create Raw DRL sheet for reference
            drl_df = pd.DataFrame({
                'DRL Content': [drl_content]
            })
            drl_df.to_excel(writer, sheet_name='Raw DRL', index=False)

            # Format Raw DRL sheet
            drl_worksheet = writer.sheets['Raw DRL']
            drl_worksheet.column_dimensions['A'].width = 120
            for row in drl_worksheet.iter_rows(min_row=2, max_row=2):
                for cell in row:
                    from openpyxl.styles import Alignment, Font
                    cell.alignment = Alignment(wrap_text=True, vertical='top')
                    cell.font = Font(name='Courier New', size=9)

        print(f"✓ Created Excel file: {excel_path}")
        return excel_path

    def get_s3_filename(self, bank_id: str, policy_type: str, version: str) -> str:
        """
        Generate S3 filename for Excel export

        :param bank_id: Bank identifier
        :param policy_type: Policy type
        :param version: Version string
        :return: S3 filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{bank_id}_{policy_type}_rules_{timestamp}.xlsx"
