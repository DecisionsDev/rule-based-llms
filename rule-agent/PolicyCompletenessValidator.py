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
import re
from typing import Dict, List, Set
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class PolicyCompletenessValidator:
    """
    Validates that all policies from a document have been extracted and converted to rules

    Uses multiple strategies:
    1. Pattern-based detection (regex for policy indicators)
    2. Section header detection
    3. LLM-based comprehensive analysis
    4. Coverage metrics and gap analysis
    """

    def __init__(self, llm):
        self.llm = llm

        # Common policy indicators (patterns that suggest a policy/rule)
        self.policy_patterns = [
            r'(?i)\b(must|shall|should|required|mandatory)\b',
            r'(?i)\b(minimum|maximum|limit|threshold|cap)\b',
            r'(?i)\b(not (allowed|permitted|eligible))\b',
            r'(?i)\b(criteria|requirement|condition|restriction)\b',
            r'(?i)\b(age|income|credit score|DTI|LTV|coverage)\b.*?(\d+)',
            r'(?i)\b(approved|denied|rejected|disqualified)\b.*?\bif\b',
            r'(?i)\b(exceeds?|below|above|less than|greater than|between)\b.*?(\d+)',
        ]

        # Section headers that typically contain policies
        self.policy_section_patterns = [
            r'(?i)^[\d.]+\s+(eligibility|requirements?|criteria)',
            r'(?i)^[\d.]+\s+(limitations?|restrictions?|exclusions?)',
            r'(?i)^[\d.]+\s+(approval|denial|underwriting)',
            r'(?i)^[\d.]+\s+(coverage|benefits?|terms?)',
            r'(?i)^[\d.]+\s+(conditions?|rules?|policies)',
        ]

        # LLM prompt for comprehensive policy extraction
        self.comprehensive_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert policy analyst specializing in complete policy extraction.

Your task is to identify EVERY single policy, rule, criterion, threshold, limit, and requirement in the document.

Return a JSON object with this structure:
{{
    "policies": [
        {{
            "policy_id": "unique_id",
            "section": "section_name",
            "policy_statement": "exact text of the policy",
            "policy_type": "eligibility|coverage_limit|age_restriction|credit_requirement|etc",
            "contains_numeric_threshold": true/false,
            "threshold_value": "value if applicable",
            "severity": "critical|important|informational"
        }}
    ],
    "total_policies_found": 0,
    "document_sections_analyzed": [],
    "coverage_confidence": 0.0
}}

CRITICAL RULES:
1. Extract EVERY policy, even if it seems minor
2. Include both positive rules (what IS allowed) and negative rules (what is NOT allowed)
3. Include numeric thresholds, percentage limits, age ranges, etc.
4. Mark severity: critical = affects approval/denial, important = affects terms, informational = general guidance
5. If a section has 10 sub-policies, extract all 10 separately

Be exhaustive, not selective."""),
            ("user", """Document text (full content):

{document_text}

Extract ALL policies comprehensively.""")
        ])

        self.chain = self.comprehensive_prompt | self.llm | JsonOutputParser()

    def detect_policy_indicators(self, document_text: str) -> Dict:
        """
        Use pattern matching to detect potential policies in the document

        Args:
            document_text: Full document text

        Returns:
            Dict with pattern matches, line numbers, and counts
        """
        lines = document_text.split('\n')

        policy_lines = []
        policy_count = 0

        for line_num, line in enumerate(lines, 1):
            # Check if line matches any policy pattern
            for pattern in self.policy_patterns:
                if re.search(pattern, line):
                    policy_lines.append({
                        "line_number": line_num,
                        "text": line.strip(),
                        "pattern": pattern
                    })
                    policy_count += 1
                    break  # Count each line once

        return {
            "total_policy_indicators": policy_count,
            "unique_policy_lines": len(policy_lines),
            "policy_lines": policy_lines[:50]  # First 50 for inspection
        }

    def detect_policy_sections(self, document_text: str) -> List[Dict]:
        """
        Detect sections likely to contain policies based on headers

        Args:
            document_text: Full document text

        Returns:
            List of detected policy sections with line numbers
        """
        lines = document_text.split('\n')
        sections = []
        current_section = None

        for line_num, line in enumerate(lines, 1):
            # Check if line is a section header
            for pattern in self.policy_section_patterns:
                if re.search(pattern, line):
                    # Save previous section
                    if current_section:
                        sections.append(current_section)

                    # Start new section
                    current_section = {
                        "section_name": line.strip(),
                        "start_line": line_num,
                        "end_line": None,
                        "content": []
                    }
                    break

            # Add content to current section
            if current_section and line.strip():
                current_section["content"].append(line.strip())

        # Save last section
        if current_section:
            current_section["end_line"] = len(lines)
            sections.append(current_section)

        return sections

    def comprehensive_analysis(self, document_text: str, max_chunk_size: int = 30000) -> Dict:
        """
        Use LLM to perform comprehensive policy extraction

        Handles large documents by chunking and merging results

        Args:
            document_text: Full document text
            max_chunk_size: Maximum characters per chunk

        Returns:
            Dict with all extracted policies
        """
        # Split into chunks if document is too large
        chunks = self._chunk_document(document_text, max_chunk_size)

        all_policies = []
        all_sections = set()

        for i, chunk in enumerate(chunks):
            print(f"Analyzing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")

            try:
                result = self.chain.invoke({"document_text": chunk})

                policies = result.get("policies", [])
                all_policies.extend(policies)

                sections = result.get("document_sections_analyzed", [])
                all_sections.update(sections)

                print(f"  Found {len(policies)} policies in chunk {i+1}")

            except Exception as e:
                print(f"  Error analyzing chunk {i+1}: {e}")

        return {
            "total_policies_found": len(all_policies),
            "policies": all_policies,
            "document_sections_analyzed": list(all_sections),
            "chunks_analyzed": len(chunks)
        }

    def validate_completeness(self, document_text: str, extracted_data: Dict,
                             generated_rules: str) -> Dict:
        """
        Validate that all policies from document were extracted and converted to rules

        Args:
            document_text: Original policy document
            extracted_data: Data extracted by Textract
            generated_rules: Generated DRL rules

        Returns:
            Dict with validation results and coverage metrics
        """
        print("\n" + "="*60)
        print("POLICY COMPLETENESS VALIDATION")
        print("="*60)

        # Step 1: Pattern-based detection
        print("\n1. Pattern-based policy detection...")
        pattern_results = self.detect_policy_indicators(document_text)
        print(f"   Found {pattern_results['total_policy_indicators']} policy indicators")

        # Step 2: Section detection
        print("\n2. Policy section detection...")
        sections = self.detect_policy_sections(document_text)
        print(f"   Found {len(sections)} policy sections")

        # Step 3: LLM comprehensive analysis
        print("\n3. LLM comprehensive policy extraction...")
        comprehensive = self.comprehensive_analysis(document_text)
        print(f"   Found {comprehensive['total_policies_found']} policies via LLM")

        # Step 4: Rule coverage analysis
        print("\n4. Analyzing rule coverage...")
        coverage = self._analyze_rule_coverage(
            comprehensive['policies'],
            generated_rules
        )

        # Step 5: Gap analysis
        print("\n5. Gap analysis...")
        gaps = self._identify_gaps(
            pattern_results,
            sections,
            comprehensive,
            extracted_data
        )

        # Calculate overall completeness score
        completeness_score = self._calculate_completeness_score(
            pattern_results,
            comprehensive,
            coverage,
            gaps
        )

        validation_result = {
            "completeness_score": completeness_score,
            "total_policies_in_document": comprehensive['total_policies_found'],
            "total_rules_generated": coverage['total_rules'],
            "coverage_ratio": coverage['coverage_ratio'],
            "pattern_detection": pattern_results,
            "policy_sections": sections,
            "comprehensive_policies": comprehensive['policies'],
            "rule_coverage": coverage,
            "gaps_identified": gaps,
            "recommendation": self._get_recommendation(completeness_score, gaps)
        }

        print("\n" + "="*60)
        print(f"COMPLETENESS SCORE: {completeness_score:.1f}%")
        print(f"Policies in document: {comprehensive['total_policies_found']}")
        print(f"Rules generated: {coverage['total_rules']}")
        print(f"Coverage ratio: {coverage['coverage_ratio']:.1f}%")
        print("="*60)

        return validation_result

    def _chunk_document(self, text: str, max_size: int) -> List[str]:
        """Split document into chunks for processing"""
        # Split by paragraphs to avoid breaking mid-sentence
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) > max_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _analyze_rule_coverage(self, policies: List[Dict], generated_rules: str) -> Dict:
        """
        Analyze how many policies are covered by generated rules

        Args:
            policies: List of policies from comprehensive analysis
            generated_rules: DRL rules as string

        Returns:
            Dict with coverage metrics
        """
        # Count rules in DRL
        rule_count = len(re.findall(r'\brule\s+"[^"]+"', generated_rules))

        # Count declare statements (data model fields)
        declare_count = len(re.findall(r'\bdeclare\s+\w+', generated_rules))

        # Estimate coverage by comparing numeric thresholds
        policies_with_thresholds = [p for p in policies if p.get('contains_numeric_threshold')]

        coverage_ratio = 0.0
        if len(policies) > 0:
            # Simple heuristic: assume 1 rule per 1-2 policies
            expected_rules = len(policies) * 0.7  # Conservative estimate
            coverage_ratio = min(100.0, (rule_count / expected_rules) * 100) if expected_rules > 0 else 0

        return {
            "total_rules": rule_count,
            "total_declares": declare_count,
            "policies_with_thresholds": len(policies_with_thresholds),
            "coverage_ratio": coverage_ratio
        }

    def _identify_gaps(self, pattern_results: Dict, sections: List[Dict],
                      comprehensive: Dict, extracted_data: Dict) -> List[Dict]:
        """Identify potential gaps in policy extraction"""
        gaps = []

        # Gap 1: High pattern count but low policy extraction
        if pattern_results['total_policy_indicators'] > comprehensive['total_policies_found'] * 2:
            gaps.append({
                "gap_type": "under_extraction",
                "severity": "high",
                "description": f"Found {pattern_results['total_policy_indicators']} policy indicators but only extracted {comprehensive['total_policies_found']} policies",
                "recommendation": "Review document manually for missed policies"
            })

        # Gap 2: Policy sections not in extracted data
        section_names = [s['section_name'] for s in sections]
        analyzed_sections = comprehensive.get('document_sections_analyzed', [])

        missing_sections = set(section_names) - set(analyzed_sections)
        if missing_sections:
            gaps.append({
                "gap_type": "missing_sections",
                "severity": "medium",
                "description": f"Sections not fully analyzed: {', '.join(list(missing_sections)[:5])}",
                "recommendation": "Ensure all document sections are analyzed"
            })

        # Gap 3: Critical policies might be missing
        critical_policies = [p for p in comprehensive.get('policies', []) if p.get('severity') == 'critical']
        if len(critical_policies) < 5:
            gaps.append({
                "gap_type": "low_critical_policy_count",
                "severity": "medium",
                "description": f"Only {len(critical_policies)} critical policies found (expected 10+)",
                "recommendation": "Review for missing critical eligibility/denial criteria"
            })

        return gaps

    def _calculate_completeness_score(self, pattern_results: Dict, comprehensive: Dict,
                                     coverage: Dict, gaps: List[Dict]) -> float:
        """
        Calculate overall completeness score (0-100)

        Factors:
        - Pattern detection vs extracted policies (40%)
        - Rule coverage ratio (40%)
        - Gap severity (20%)
        """
        # Pattern score
        pattern_score = min(100.0, (comprehensive['total_policies_found'] /
                                   max(1, pattern_results['total_policy_indicators'] * 0.5)) * 100)

        # Coverage score
        coverage_score = coverage['coverage_ratio']

        # Gap penalty
        gap_penalty = sum(20 if g['severity'] == 'high' else 10 if g['severity'] == 'medium' else 5
                         for g in gaps)

        # Weighted average
        score = (pattern_score * 0.4 + coverage_score * 0.4) - (gap_penalty * 0.2)

        return max(0.0, min(100.0, score))

    def _get_recommendation(self, score: float, gaps: List[Dict]) -> str:
        """Get recommendation based on completeness score"""
        if score >= 90:
            return "✓ Excellent completeness. All major policies appear to be captured."
        elif score >= 75:
            return "⚠ Good completeness, but review identified gaps to ensure no critical policies are missed."
        elif score >= 60:
            return "⚠ Moderate completeness. Manual review recommended to identify missing policies."
        else:
            high_severity_gaps = [g for g in gaps if g['severity'] == 'high']
            if high_severity_gaps:
                return f"✗ Low completeness with {len(high_severity_gaps)} high-severity gaps. MANUAL REVIEW REQUIRED."
            else:
                return "✗ Low completeness. Significant policies may be missing. MANUAL REVIEW REQUIRED."


# Singleton instance
_validator_instance = None

def get_policy_validator(llm):
    """Get singleton instance of PolicyCompletenessValidator"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = PolicyCompletenessValidator(llm)
    return _validator_instance
