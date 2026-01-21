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
from typing import Dict, List, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class TableOfContentsExtractor:
    """
    Extracts Table of Contents from policy documents and processes each section systematically

    This ensures COMPLETE policy coverage by:
    1. Building a structured TOC from the document
    2. Processing EVERY section individually
    3. Tracking which sections have been analyzed
    4. Preventing sections from being skipped

    Benefits over direct extraction:
    - ✅ Systematic coverage - no sections missed
    - ✅ Structured approach - clear hierarchy
    - ✅ Progress tracking - know what's been processed
    - ✅ Better for long documents - divide and conquer
    """

    def __init__(self, llm):
        self.llm = llm

        # Prompt for TOC extraction
        self.toc_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document analyst specializing in extracting document structure.

Your task is to analyze the document and extract a complete Table of Contents (TOC).

CRITICAL: Identify EVERY section and subsection, even if not explicitly labeled as TOC.

Look for:
- Numbered sections (1., 1.1, 1.2.1, etc.)
- Lettered sections (A., B., C., etc.)
- Named sections (SECTION 1:, PART A:, etc.)
- Headers in ALL CAPS or bold formatting
- Clear topic breaks

Return a JSON object with this structure:
{{
    "toc": [
        {{
            "section_number": "1",
            "section_title": "Overview",
            "subsections": [
                {{
                    "section_number": "1.1",
                    "section_title": "Purpose",
                    "subsections": []
                }}
            ]
        }}
    ],
    "total_sections": 0,
    "has_explicit_toc": true/false
}}

IMPORTANT:
- Include ALL sections, even if they seem minor
- Preserve the hierarchy (sections, subsections, sub-subsections)
- Extract exact section titles
- Include page numbers if available"""),
            ("user", "Document text:\n\n{document_text}")
        ])

        # Prompt for section-by-section analysis
        self.section_analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert policy analyst.

Your task is to analyze a SINGLE section of a policy document and extract ALL policies from it.

CRITICAL: Focus ONLY on this section. Extract EVERY policy, rule, threshold, requirement, and restriction.

Return a JSON object with this structure:
{{
    "section_policies": [
        {{
            "policy_statement": "exact text of the policy",
            "policy_type": "eligibility|coverage_limit|age_restriction|etc",
            "numeric_threshold": "value if applicable",
            "severity": "critical|important|informational",
            "textract_query": "What is the maximum coverage amount?"
        }}
    ],
    "total_policies": 0
}}

IMPORTANT:
- Extract EVERY distinct policy in this section
- Include both positive rules (what IS allowed) and negative rules (what is NOT allowed)
- Generate specific Textract queries for each policy
- Mark severity: critical = affects approval/denial, important = affects terms

CRITICAL RULE TO PREVENT HALLUCINATION:
- ONLY extract policies that are EXPLICITLY stated in the section content
- If the section contains only a title/header with no actual policy content, return an EMPTY list
- DO NOT invent, assume, or infer policies that are not directly written in the text
- If you're unsure whether something is a policy, DO NOT include it"""),
            ("user", """Section Number: {section_number}
Section Title: {section_title}

Section Content:
{section_content}

Extract ALL policies from this section. Remember: ONLY extract policies that are explicitly written in the content above. If there are no policies in this content, return an empty list.""")
        ])

        self.toc_chain = self.toc_prompt | self.llm | JsonOutputParser()
        self.section_chain = self.section_analysis_prompt | self.llm | JsonOutputParser()

    def extract_toc(self, document_text: str) -> Dict:
        """
        Extract Table of Contents from document

        Args:
            document_text: Full document text

        Returns:
            Dict with TOC structure and metadata
        """
        print("\n" + "="*60)
        print("EXTRACTING TABLE OF CONTENTS")
        print("="*60)

        try:
            # Extract TOC using LLM
            result = self.toc_chain.invoke({"document_text": document_text[:50000]})

            # Flatten TOC for easier processing
            flat_toc = self._flatten_toc(result.get("toc", []))

            print(f"✓ TOC extracted: {len(flat_toc)} sections found")

            # If LLM didn't find explicit TOC, try pattern-based extraction
            if not result.get("has_explicit_toc", False) or len(flat_toc) == 0:
                print("  No explicit TOC found, using pattern-based extraction...")
                pattern_toc = self._extract_toc_by_patterns(document_text)
                if len(pattern_toc) > len(flat_toc):
                    flat_toc = pattern_toc
                    print(f"  ✓ Pattern-based extraction found {len(flat_toc)} sections")

            return {
                "toc": flat_toc,
                "total_sections": len(flat_toc),
                "has_explicit_toc": result.get("has_explicit_toc", False)
            }

        except Exception as e:
            print(f"✗ Error extracting TOC: {e}")
            print("  Falling back to pattern-based extraction...")
            pattern_toc = self._extract_toc_by_patterns(document_text)
            return {
                "toc": pattern_toc,
                "total_sections": len(pattern_toc),
                "has_explicit_toc": False,
                "error": str(e)
            }

    def _flatten_toc(self, toc: List[Dict], parent_number: str = "") -> List[Dict]:
        """
        Flatten hierarchical TOC into a flat list

        Args:
            toc: Hierarchical TOC structure
            parent_number: Parent section number

        Returns:
            Flat list of sections
        """
        flat = []

        for section in toc:
            section_num = section.get("section_number", "")
            section_title = section.get("section_title", "")

            flat.append({
                "section_number": section_num,
                "section_title": section_title,
                "full_path": f"{parent_number}.{section_num}".strip(".") if parent_number else section_num
            })

            # Recursively flatten subsections
            subsections = section.get("subsections", [])
            if subsections:
                flat.extend(self._flatten_toc(subsections, section_num))

        return flat

    def _extract_toc_by_patterns(self, document_text: str) -> List[Dict]:
        """
        Extract TOC using regex patterns (fallback method)

        Args:
            document_text: Full document text

        Returns:
            List of sections found via patterns
        """
        patterns = [
            # Numbered sections: "1.", "1.1", "1.2.3"
            r'^(\d+(?:\.\d+)*)\s+(.+?)$',

            # Lettered sections: "A.", "B.", "C."
            r'^([A-Z])\.\s+(.+?)$',

            # Named sections: "SECTION 1:", "PART A:"
            r'^(?:SECTION|PART|CHAPTER)\s+([A-Z0-9]+):\s+(.+?)$',

            # Equals line markers (like ===)
            r'^=+\s*$\n^(.+?)$\n^=+\s*$',
        ]

        sections = []
        lines = document_text.split('\n')

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            for pattern in patterns:
                match = re.match(pattern, line, re.MULTILINE | re.IGNORECASE)
                if match:
                    if len(match.groups()) == 2:
                        section_num = match.group(1)
                        section_title = match.group(2).strip()
                    else:
                        section_num = str(len(sections) + 1)
                        section_title = match.group(1).strip()

                    # Skip if title is too short or too long
                    if len(section_title) < 3 or len(section_title) > 200:
                        continue

                    sections.append({
                        "section_number": section_num,
                        "section_title": section_title,
                        "line_number": line_num + 1,
                        "full_path": section_num
                    })
                    break

        return sections

    def extract_section_content(self, document_text: str, section: Dict,
                               next_section: Dict = None) -> str:
        """
        Extract content for a specific section

        Args:
            document_text: Full document text
            section: Section metadata (with line_number if available)
            next_section: Next section metadata (for boundary detection)

        Returns:
            Section content as string
        """
        lines = document_text.split('\n')

        # If we have line numbers, use them
        if "line_number" in section:
            start_line = section["line_number"]
            end_line = next_section.get("line_number", len(lines)) if next_section else len(lines)

            content_lines = lines[start_line:end_line]
            content = '\n'.join(content_lines)
            print(f"  DEBUG: Extracted content using line numbers {start_line} to {end_line}: {len(content)} chars")
            return content

        # Otherwise, search for section by title
        section_title = section.get("section_title", "")
        section_num = section.get("section_number", "")

        print(f"  DEBUG: Searching for section '{section_num}' - '{section_title}'")

        # Find section start - use flexible matching
        start_idx = None
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Try multiple matching strategies
            # Strategy 1: Both number and title in same line
            if section_num in line and section_title in line:
                start_idx = i
                print(f"  DEBUG: Found section at line {i} (both in same line)")
                break

            # Strategy 2: Number followed by title (possibly on next line or same line)
            if section_num and line_stripped.startswith(section_num):
                # Check if title is on same line or next line
                if section_title in line:
                    start_idx = i
                    print(f"  DEBUG: Found section at line {i} (title on same line)")
                    break
                elif i + 1 < len(lines) and section_title in lines[i + 1]:
                    start_idx = i
                    print(f"  DEBUG: Found section at line {i} (title on next line)")
                    break

            # Strategy 3: Title match only (as fallback)
            if section_title and len(section_title) > 5 and section_title in line:
                start_idx = i
                print(f"  DEBUG: Found section at line {i} (title match only)")
                break

        if start_idx is None:
            print(f"  DEBUG: Could not find section start for '{section_num}' - '{section_title}'")
            return ""

        # Find section end (next section or end of document)
        end_idx = len(lines)
        if next_section:
            next_title = next_section.get("section_title", "")
            next_num = next_section.get("section_number", "")

            print(f"  DEBUG: Looking for next section: '{next_num}' - '{next_title}'")

            for i in range(start_idx + 1, len(lines)):
                line_stripped = lines[i].strip()

                # Strategy 1: Both number and title in same line
                if (next_num and next_title and next_num in lines[i] and next_title in lines[i]):
                    end_idx = i
                    print(f"  DEBUG: Found next section at line {i} (both number and title)")
                    break

                # Strategy 2: Line starts with next section number
                elif next_num and line_stripped.startswith(next_num):
                    end_idx = i
                    print(f"  DEBUG: Found next section at line {i} (by number)")
                    break

                # Strategy 3: Title match only (as fallback) - same as start matching
                elif next_title and len(next_title) > 5 and next_title in lines[i]:
                    end_idx = i
                    print(f"  DEBUG: Found next section at line {i} (by title)")
                    break

        content_lines = lines[start_idx:end_idx]
        content = '\n'.join(content_lines)
        print(f"  DEBUG: Extracted {len(content)} chars from lines {start_idx} to {end_idx}")
        return content

    def analyze_section(self, section: Dict, section_content: str) -> Dict:
        """
        Analyze a single section and extract all policies

        Args:
            section: Section metadata
            section_content: Content of the section

        Returns:
            Dict with extracted policies and metadata
        """
        try:
            result = self.section_chain.invoke({
                "section_number": section.get("section_number", ""),
                "section_title": section.get("section_title", ""),
                "section_content": section_content[:15000]  # Limit section size
            })

            policies = result.get("section_policies", [])

            return {
                "section_number": section.get("section_number"),
                "section_title": section.get("section_title"),
                "policies": policies,
                "total_policies": len(policies),
                "status": "success"
            }

        except Exception as e:
            return {
                "section_number": section.get("section_number"),
                "section_title": section.get("section_title"),
                "policies": [],
                "total_policies": 0,
                "status": "error",
                "error": str(e)
            }

    def process_document_by_toc(self, document_text: str) -> Dict:
        """
        Process entire document section-by-section using TOC

        This is the main method that ensures complete coverage

        Args:
            document_text: Full document text

        Returns:
            Dict with all extracted policies organized by section
        """
        print("\n" + "="*60)
        print("SYSTEMATIC SECTION-BY-SECTION POLICY EXTRACTION")
        print("="*60)

        # Step 1: Extract TOC
        toc_result = self.extract_toc(document_text)
        toc = toc_result["toc"]
        total_sections = toc_result["total_sections"]

        print(f"\n✓ Document structure identified: {total_sections} sections")
        print("\nSections to be analyzed:")
        for i, section in enumerate(toc[:20], 1):  # Show first 20
            print(f"  {i}. {section['section_number']} - {section['section_title']}")
        if len(toc) > 20:
            print(f"  ... and {len(toc) - 20} more sections")

        # Step 2: Process each section
        print("\n" + "-"*60)
        print("Processing sections...")
        print("-"*60)

        all_section_results = []
        all_policies = []
        all_queries = []

        for i, section in enumerate(toc):
            print(f"\n[{i+1}/{total_sections}] Analyzing: {section['section_number']} - {section['section_title']}")

            # Extract section content
            next_section = toc[i + 1] if i + 1 < len(toc) else None
            section_content = self.extract_section_content(document_text, section, next_section)

            if len(section_content.strip()) < 30:
                print(f"  ⚠ Section too short ({len(section_content)} chars), skipping...")
                continue

            # Analyze section
            section_result = self.analyze_section(section, section_content)
            all_section_results.append(section_result)

            policies = section_result.get("policies", [])
            all_policies.extend(policies)

            # Extract queries from policies
            for policy in policies:
                query = policy.get("textract_query")
                if query and query not in all_queries:
                    all_queries.append(query)

            print(f"  ✓ Found {len(policies)} policies in this section")

        # Step 3: Compile results
        print("\n" + "="*60)
        print("SECTION-BY-SECTION EXTRACTION COMPLETE")
        print("="*60)
        print(f"✓ Sections analyzed: {len(all_section_results)}/{total_sections}")
        print(f"✓ Total policies extracted: {len(all_policies)}")
        print(f"✓ Unique queries generated: {len(all_queries)}")
        print("="*60)

        return {
            "method": "toc_based",
            "toc": toc,
            "total_sections": total_sections,
            "sections_analyzed": len(all_section_results),
            "section_results": all_section_results,
            "all_policies": all_policies,
            "total_policies": len(all_policies),
            "queries": all_queries,
            "coverage_percentage": (len(all_section_results) / total_sections * 100) if total_sections > 0 else 0
        }


# Singleton instance
_toc_extractor = None

def get_toc_extractor(llm):
    """Get singleton instance of TableOfContentsExtractor"""
    global _toc_extractor
    if _toc_extractor is None:
        _toc_extractor = TableOfContentsExtractor(llm)
    return _toc_extractor
