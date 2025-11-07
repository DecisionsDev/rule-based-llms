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
from langchain_core.output_parsers import JsonOutputParser
from typing import List, Dict
import json
import os

class PolicyAnalyzerAgent:
    """
    Analyzes policy documents and generates queries for Textract extraction

    CRITICAL: Ensures ALL policies are captured, not just the first few.

    Supports two modes:
    1. TOC-based (RECOMMENDED): Extracts TOC and processes each section systematically
    2. Full-document: Analyzes entire document at once (legacy mode)
    """

    def __init__(self, llm):
        self.llm = llm
        self.use_toc_mode = os.getenv("USE_TOC_EXTRACTION", "true").lower() == "true"

        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert insurance policy analyst specializing in underwriting rules.

Your task is to analyze policy document text and identify ALL underwriting criteria that need to be extracted.

CRITICAL: Extract EVERY policy, rule, threshold, limit, and requirement - do not skip any.

Focus on extracting:
- Coverage limits and amounts (min/max)
- Age restrictions and requirements
- Eligibility criteria (ALL conditions)
- Income and credit requirements
- Debt-to-income (DTI) ratios
- Loan-to-value (LTV) ratios
- Premium calculation factors
- Excluded conditions or situations
- Risk assessment criteria
- Required documentation
- Approval/denial thresholds
- Employment requirements
- Collateral requirements
- Exception criteria

Generate specific, targeted queries that AWS Textract can use to extract precise data from the document.

Return a JSON object with this structure:
{{
    "queries": [
        "What is the maximum coverage amount?",
        "What is the minimum age requirement for applicants?",
        "What is the maximum age limit for applicants?",
        "What is the maximum debt-to-income ratio?",
        "What is the minimum credit score required?"
    ],
    "key_sections": [
        "Coverage Limits",
        "Eligibility Requirements",
        "Credit Requirements"
    ],
    "rule_categories": [
        "age_restrictions",
        "coverage_limits",
        "credit_requirements"
    ]
}}

IMPORTANT:
- Generate AT LEAST 15-25 queries to ensure comprehensive coverage
- Extract BOTH positive criteria (what IS allowed) and negative criteria (what is NOT allowed)
- Include ALL numeric thresholds, percentages, and limits
- Make queries specific and actionable - each query should extract a concrete value or fact
- Do NOT summarize - extract EVERY distinct policy separately"""),
            ("user", "Policy document text:\n\n{document_text}")
        ])

        self.chain = self.analysis_prompt | self.llm | JsonOutputParser()

    def analyze_policy(self, document_text: str, use_toc: bool = None) -> Dict:
        """
        Analyze policy document and generate Textract queries

        CRITICAL: Handles long documents by chunking to ensure ALL policies are captured

        :param document_text: Text extracted from PDF (via PyPDF or basic parsing)
        :param use_toc: Whether to use TOC-based extraction (default: env var USE_TOC_EXTRACTION)
        :return: Dictionary with queries, key_sections, and rule_categories
        """
        try:
            # Determine extraction mode
            use_toc_extraction = use_toc if use_toc is not None else self.use_toc_mode

            # TOC-based extraction (RECOMMENDED for completeness)
            if use_toc_extraction:
                print("Using TOC-based systematic extraction (ensures ALL sections are analyzed)")
                return self._analyze_with_toc(document_text)

            # Legacy: Full-document analysis
            # Handle long documents by chunking (do NOT truncate - this loses policies!)
            if len(document_text) > 30000:
                print(f"⚠ Document is long ({len(document_text)} chars), using chunked analysis to capture ALL policies")
                result = self._analyze_in_chunks(document_text)
            else:
                result = self.chain.invoke({"document_text": document_text})

            # Ensure result has expected structure
            if "queries" not in result:
                result["queries"] = []

            if "key_sections" not in result:
                result["key_sections"] = []

            if "rule_categories" not in result:
                result["rule_categories"] = []

            # Warning if too few queries generated
            if len(result['queries']) < 10:
                print(f"⚠ WARNING: Only {len(result['queries'])} queries generated - may be missing policies!")
                print("  Consider manual review to ensure completeness")

            print(f"✓ Policy analysis complete: {len(result['queries'])} queries generated")
            return result

        except Exception as e:
            print(f"✗ Error analyzing policy: {e}")
            # Return default comprehensive queries
            return {
                "queries": self._get_comprehensive_fallback_queries(),
                "key_sections": [],
                "rule_categories": [],
                "error": str(e)
            }

    def _analyze_in_chunks(self, document_text: str) -> Dict:
        """
        Analyze long documents in chunks to ensure ALL policies are captured

        Args:
            document_text: Full document text

        Returns:
            Combined analysis from all chunks
        """
        chunk_size = 25000
        overlap = 2000  # Overlap to avoid missing policies at chunk boundaries

        chunks = []
        start = 0
        while start < len(document_text):
            end = min(start + chunk_size, len(document_text))
            chunks.append(document_text[start:end])
            start += (chunk_size - overlap)

        print(f"  Analyzing document in {len(chunks)} chunks...")

        all_queries = []
        all_sections = []
        all_categories = []

        for i, chunk in enumerate(chunks):
            try:
                print(f"  Processing chunk {i+1}/{len(chunks)}...")
                result = self.chain.invoke({"document_text": chunk})

                all_queries.extend(result.get("queries", []))
                all_sections.extend(result.get("key_sections", []))
                all_categories.extend(result.get("rule_categories", []))

            except Exception as e:
                print(f"  ⚠ Error in chunk {i+1}: {e}")

        # Deduplicate while preserving order
        unique_queries = list(dict.fromkeys(all_queries))
        unique_sections = list(dict.fromkeys(all_sections))
        unique_categories = list(dict.fromkeys(all_categories))

        print(f"  ✓ Combined analysis: {len(unique_queries)} unique queries from {len(chunks)} chunks")

        return {
            "queries": unique_queries,
            "key_sections": unique_sections,
            "rule_categories": unique_categories
        }

    def _analyze_with_toc(self, document_text: str) -> Dict:
        """
        Analyze document using TOC-based systematic extraction

        This ensures COMPLETE coverage by:
        1. Extracting Table of Contents
        2. Processing EVERY section individually
        3. Combining results from all sections

        Args:
            document_text: Full document text

        Returns:
            Combined analysis with queries from all sections
        """
        from TableOfContentsExtractor import get_toc_extractor

        toc_extractor = get_toc_extractor(self.llm)

        # Process document section-by-section
        toc_result = toc_extractor.process_document_by_toc(document_text)

        # Extract queries and organize results
        queries = toc_result.get("queries", [])
        all_policies = toc_result.get("all_policies", [])
        section_results = toc_result.get("section_results", [])

        # FALLBACK: If TOC extraction found 0 queries, fall back to full document analysis
        if len(queries) == 0:
            print("\n⚠ WARNING: TOC-based extraction found 0 queries")
            print("  Falling back to full document analysis (chunked mode)...\n")

            # Use chunked analysis as fallback
            if len(document_text) > 30000:
                fallback_result = self._analyze_in_chunks(document_text)
            else:
                fallback_result = self._analyze_full_document(document_text)

            # Add fallback metadata
            fallback_result["extraction_method"] = "toc_failed_fallback_to_chunked"
            fallback_result["toc_failure_reason"] = "No queries generated from TOC extraction"
            return fallback_result

        # Extract key sections from TOC
        key_sections = [
            f"{s['section_number']} - {s['section_title']}"
            for s in toc_result.get("toc", [])[:10]  # Top 10 sections
        ]

        # Extract rule categories from policies
        rule_categories = list(set([
            p.get("policy_type", "unknown")
            for p in all_policies
            if p.get("policy_type")
        ]))

        # Add metadata about TOC-based extraction
        result = {
            "queries": queries,
            "key_sections": key_sections,
            "rule_categories": rule_categories,
            "extraction_method": "toc_based",
            "total_sections_analyzed": toc_result.get("sections_analyzed", 0),
            "coverage_percentage": toc_result.get("coverage_percentage", 0),
            "section_breakdown": section_results
        }

        return result

    def _get_comprehensive_fallback_queries(self) -> List[str]:
        """
        Return comprehensive fallback queries if LLM analysis fails

        Returns:
            List of comprehensive queries covering common policy areas
        """
        return [
            # Age requirements
            "What is the minimum age requirement?",
            "What is the maximum age limit?",

            # Coverage/Loan amounts
            "What is the minimum coverage amount?",
            "What is the maximum coverage amount?",
            "What is the minimum loan amount?",
            "What is the maximum loan amount?",

            # Credit requirements
            "What is the minimum credit score required?",
            "What credit score is needed for approval?",

            # Income requirements
            "What is the minimum annual income required?",
            "What is the maximum debt-to-income ratio?",

            # LTV requirements
            "What is the maximum loan-to-value ratio?",
            "What is the maximum LTV for different property types?",

            # Employment
            "What is the minimum employment history required?",
            "How long must the applicant be employed?",

            # Terms
            "What are the available loan terms?",
            "What is the minimum term length?",
            "What is the maximum term length?",

            # Collateral
            "What collateral is required?",
            "What is the minimum collateral value?",

            # Exclusions
            "What are the excluded conditions?",
            "What situations are not covered?",

            # Interest rates
            "What is the interest rate range?",
            "What factors affect the interest rate?",

            # Approval criteria
            "What are the automatic approval criteria?",
            "What requires manual review?",

            # Documentation
            "What documentation is required?",
            "What proof of income is needed?"
        ]

    def generate_template_queries(self, policy_type: str = "general") -> List[str]:
        """
        Generate template queries for common policy types

        :param policy_type: Type of policy (general, life, health, auto, property)
        :return: List of template queries
        """
        templates = {
            "general": [
                "What is the maximum coverage amount?",
                "What is the minimum coverage amount?",
                "What is the age limit for applicants?",
                "What are the excluded conditions?",
                "What is the deductible amount?"
            ],
            "life": [
                "What is the maximum life insurance coverage amount?",
                "What is the minimum age for life insurance applicants?",
                "What is the maximum age for life insurance applicants?",
                "What pre-existing conditions are excluded?",
                "What is the waiting period for coverage?",
                "What are the premium payment options?"
            ],
            "health": [
                "What is the maximum health insurance coverage?",
                "What is the annual deductible?",
                "What is the out-of-pocket maximum?",
                "What pre-existing conditions are covered?",
                "What is the waiting period for major medical procedures?",
                "What preventive care services are covered?"
            ],
            "auto": [
                "What is the minimum liability coverage required?",
                "What is the maximum coverage for collision damage?",
                "What is the age requirement for primary drivers?",
                "What is the deductible for comprehensive coverage?",
                "Are rental car expenses covered?"
            ],
            "property": [
                "What is the maximum property value covered?",
                "What natural disasters are covered?",
                "What is the deductible for property damage?",
                "Are earthquake and flood damages covered?",
                "What is the replacement cost coverage limit?"
            ]
        }

        return templates.get(policy_type.lower(), templates["general"])
