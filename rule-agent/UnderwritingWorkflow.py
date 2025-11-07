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
from PolicyAnalyzerAgent import PolicyAnalyzerAgent
from TextractService import TextractService
from RuleGeneratorAgent import RuleGeneratorAgent
from DroolsDeploymentService import DroolsDeploymentService
from S3Service import S3Service
from ExcelRulesExporter import ExcelRulesExporter
from RuleCacheService import get_rule_cache
from PyPDF2 import PdfReader
import json
import os
import io
from typing import Dict, List, Optional

class UnderwritingWorkflow:
    """
    Orchestrates the complete underwriting workflow:
    PDF → Analysis → Textract → Rule Generation → Deployment → Excel Export
    """

    def __init__(self, llm):
        self.llm = llm
        self.policy_analyzer = PolicyAnalyzerAgent(llm)
        self.textract = TextractService()
        self.rule_generator = RuleGeneratorAgent(llm)
        self.drools_deployment = DroolsDeploymentService()
        self.s3_service = S3Service()
        self.excel_exporter = ExcelRulesExporter()
        self.rule_cache = get_rule_cache()

        # Validate Textract is configured (required)
        if not self.textract.isConfigured:
            raise RuntimeError("AWS Textract is not configured. Please configure AWS credentials and Textract service.")

    def process_policy_document(self, s3_url: str,
                                policy_type: str = "general",
                                bank_id: str = None,
                                use_cache: bool = True) -> Dict:
        """
        Complete workflow to process a policy document and generate rules

        :param s3_url: S3 URL to policy PDF (required)
        :param policy_type: Type of policy (general, life, health, auto, property, loan, insurance, etc.)
        :param bank_id: Bank/Tenant identifier (e.g., 'chase', 'bofa', 'wells-fargo')
        :param use_cache: Whether to use cached rules if available (default: True)
        :return: Result dictionary with all workflow steps
        """

        # Auto-generate container_id based on bank_id and policy_type
        # This ensures proper multi-tenant isolation
        # Normalize policy_type: lowercase and replace spaces with hyphens
        normalized_type = policy_type.lower().strip().replace(' ', '-')

        if bank_id:
            # Normalize bank_id: lowercase and replace spaces with hyphens
            normalized_bank = bank_id.lower().strip().replace(' ', '-')
            container_id = f"{normalized_bank}-{normalized_type}-underwriting-rules"
            print(f"Auto-generated container ID (with bank): {container_id}")
        else:
            # Fallback to policy-type only (for backwards compatibility)
            container_id = f"{normalized_type}-underwriting-rules"
            print(f"Auto-generated container ID (no bank): {container_id}")
            print("Warning: No bank_id provided. Consider specifying bank_id for multi-tenant deployments.")

        result = {
            "s3_url": s3_url,
            "policy_type": policy_type,
            "bank_id": bank_id,
            "container_id": container_id,
            "steps": {},
            "status": "in_progress"
        }

        try:
            # Parse S3 URL to extract bucket and key
            print("\n" + "="*60)
            print("Step 0: Parsing S3 URL...")
            print("="*60)

            s3_info = self.s3_service.parse_s3_url(s3_url)
            if "error" in s3_info:
                result["status"] = "failed"
                result["error"] = s3_info["error"]
                return result

            s3_bucket = s3_info["bucket"]
            s3_key = s3_info["key"]
            print(f"✓ S3 bucket: {s3_bucket}")
            print(f"✓ S3 key: {s3_key}")
            result["s3_bucket"] = s3_bucket
            result["s3_key"] = s3_key

            # Step 1: Extract text from PDF
            print("\n" + "="*60)
            print("Step 1: Extracting text from PDF from S3...")
            print("="*60)

            # Read PDF from S3 directly into memory
            document_text = self._extract_text_from_s3(s3_key)

            result["steps"]["text_extraction"] = {
                "status": "success",
                "length": len(document_text),
                "preview": document_text[:500] + "..." if len(document_text) > 500 else document_text
            }
            print(f"✓ Extracted {len(document_text)} characters")

            # Step 1.5: Check cache for deterministic rule generation
            print("\n" + "="*60)
            print("Step 1.5: Checking cache for identical policy document...")
            print("="*60)

            # Compute document hash (for deterministic caching)
            document_hash = self.rule_cache.compute_document_hash(document_text)
            result["document_hash"] = document_hash
            print(f"Document hash: {document_hash[:16]}...")

            # CACHING TEMPORARILY DISABLED FOR TESTING
            # Check if we have cached rules for this exact document
            # if use_cache:
            #     cached_result = self.rule_cache.get_cached_rules(document_hash)
            #     if cached_result:
            #         print("✓ Found cached rules - using deterministic cached version")
            #         # Return cached result with updated metadata
            #         cached_data = cached_result.get("rule_data", {})
            #         cached_data["status"] = "success"
            #         cached_data["source"] = "cache"
            #         cached_data["document_hash"] = document_hash
            #         cached_data["cached_timestamp"] = cached_result.get("timestamp")
            #         return cached_data

            print("Cache disabled - proceeding with fresh rule generation...")

            # Step 2: LLM generates extraction queries by analyzing the document
            print("\n" + "="*60)
            print("Step 2: LLM analyzing document and generating extraction queries...")
            print("="*60)

            analysis = self.policy_analyzer.analyze_policy(document_text)
            queries = analysis.get("queries", [])
            result["steps"]["query_generation"] = {
                "status": "success",
                "method": "llm_generated",
                "queries": queries,
                "count": len(queries),
                "key_sections": analysis.get("key_sections", []),
                "rule_categories": analysis.get("rule_categories", [])
            }

            print(f"✓ LLM generated {len(queries)} custom queries")
            for i, q in enumerate(queries, 1):
                print(f"  {i}. {q}")

            # Step 3: Extract structured data using AWS Textract
            print("\n" + "="*60)
            print("Step 3: Extracting structured data with AWS Textract...")
            print("="*60)

            if len(queries) == 0:
                raise ValueError("No extraction queries generated. Cannot proceed with data extraction.")

            print("Using AWS Textract for data extraction from S3...")
            # Use S3 document directly with Textract
            extracted_data = self.textract.analyze_document(
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                queries=queries
            )

            result["steps"]["data_extraction"] = {
                "status": "success",
                "method": "textract",
                "data": extracted_data
            }
            print(f"✓ Extracted data from {len(queries)} queries using AWS Textract")

            # Step 4: Generate Drools rules
            print("\n" + "="*60)
            print("Step 4: Generating Drools rules...")
            print("="*60)

            rules = self.rule_generator.generate_rules(extracted_data)
            result["steps"]["rule_generation"] = {
                "status": "success",
                "drl_length": len(rules.get('drl', '')),
                "has_decision_table": rules.get('decision_table') is not None and len(rules.get('decision_table', '')) > 0,
                "explanation": rules.get('explanation', '')
            }
            print(f"✓ Generated DRL rules ({len(rules.get('drl', ''))} characters)")
            if rules.get('decision_table'):
                print(f"✓ Generated decision table")

            # Step 5: Automated deployment to Drools KIE Server (includes DRL save)
            print("\n" + "="*60)
            print("Step 5: Automated deployment to Drools KIE Server...")
            print("="*60)

            # Try automated deployment (KJar creation, Maven build, deployment)
            deployment_result = self.drools_deployment.deploy_rules_automatically(
                rules['drl'],
                container_id
            )
            result["steps"]["deployment"] = deployment_result

            if deployment_result["status"] == "success":
                print(f"✓ Rules automatically deployed to container '{container_id}'")
            elif deployment_result["status"] == "partial":
                print(f"⚠ Partial success: {deployment_result['message']}")
                if "manual_instructions" in deployment_result:
                    print(f"  Manual step required: {deployment_result['manual_instructions']}")
            else:
                print(f"✗ Deployment failed: {deployment_result.get('message', 'Unknown error')}")

            # Also save KJar info in a separate step for clarity
            if "steps" in deployment_result and "create_kjar" in deployment_result["steps"]:
                result["steps"]["kjar_creation"] = deployment_result["steps"]["create_kjar"]

            # Step 6: Upload JAR and DRL to S3 if built successfully
            if deployment_result.get("steps", {}).get("build", {}).get("status") == "success":
                print("\n" + "="*60)
                print("Step 6: Uploading generated files to S3...")
                print("="*60)

                jar_path = deployment_result["steps"]["build"].get("jar_path")
                drl_path = deployment_result["steps"]["save_drl"].get("path")
                version = deployment_result["release_id"]["version"]

                s3_upload_results = {}

                # Upload JAR file
                if jar_path and os.path.exists(jar_path):
                    jar_upload = self.s3_service.upload_jar_to_s3(jar_path, container_id, version)
                    s3_upload_results["jar"] = jar_upload
                    if jar_upload["status"] == "success":
                        print(f"✓ JAR uploaded to S3: {jar_upload['s3_url']}")
                        result["jar_s3_url"] = jar_upload["s3_url"]
                    else:
                        print(f"✗ JAR upload failed: {jar_upload.get('message', 'Unknown error')}")

                    # Clean up temp JAR file after upload
                    try:
                        os.unlink(jar_path)
                        print(f"✓ Temporary JAR file deleted: {jar_path}")
                    except Exception as e:
                        print(f"Warning: Could not delete temp JAR file: {e}")

                # Upload DRL file
                drl_content = None
                if drl_path and os.path.exists(drl_path):
                    # Read DRL content for Excel export
                    with open(drl_path, 'r', encoding='utf-8') as f:
                        drl_content = f.read()

                    drl_upload = self.s3_service.upload_drl_to_s3(drl_path, container_id, version)
                    s3_upload_results["drl"] = drl_upload
                    if drl_upload["status"] == "success":
                        print(f"✓ DRL uploaded to S3: {drl_upload['s3_url']}")
                        result["drl_s3_url"] = drl_upload["s3_url"]
                    else:
                        print(f"✗ DRL upload failed: {drl_upload.get('message', 'Unknown error')}")

                    # Clean up temp DRL file after upload
                    try:
                        os.unlink(drl_path)
                        print(f"✓ Temporary DRL file deleted: {drl_path}")
                    except Exception as e:
                        print(f"Warning: Could not delete temp DRL file: {e}")

                # Generate and upload Excel spreadsheet with rules
                if drl_content and bank_id:
                    try:
                        print("✓ Generating Excel spreadsheet from rules...")
                        excel_path = self.excel_exporter.create_excel_file(
                            drl_content, bank_id, policy_type, container_id, version
                        )

                        # Upload Excel to S3
                        excel_upload = self.s3_service.upload_excel_to_s3(
                            excel_path, bank_id, policy_type, container_id, version
                        )
                        s3_upload_results["excel"] = excel_upload

                        if excel_upload["status"] == "success":
                            print(f"✓ Excel spreadsheet uploaded to S3: {excel_upload['s3_url']}")
                            result["excel_s3_url"] = excel_upload["s3_url"]
                        else:
                            print(f"✗ Excel upload failed: {excel_upload.get('message', 'Unknown error')}")

                        # Clean up temp Excel file
                        try:
                            os.unlink(excel_path)
                            print(f"✓ Temporary Excel file deleted: {excel_path}")
                        except Exception as e:
                            print(f"Warning: Could not delete temp Excel file: {e}")

                    except Exception as e:
                        print(f"⚠ Excel generation failed: {e}")
                        s3_upload_results["excel"] = {
                            "status": "error",
                            "message": str(e)
                        }

                result["steps"]["s3_upload"] = s3_upload_results

            result["status"] = "completed"
            result["source"] = "generated"

            # Cache the successful result for future deterministic retrieval
            print("\n" + "="*60)
            print("Step 7: Caching rules for future deterministic generation...")
            print("="*60)

            self.rule_cache.cache_rules(document_hash, result)

            print("\n" + "="*60)
            print("✓ Workflow completed successfully!")
            print("="*60)

        except Exception as e:
            print(f"\n✗ Error in workflow: {e}")
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    def _extract_text_from_s3(self, s3_key: str) -> str:
        """Extract text from S3 PDF directly into memory using PyPDF2"""
        try:
            # Read PDF bytes from S3 directly into memory
            pdf_bytes = self.s3_service.read_pdf_from_s3(s3_key)
            if not pdf_bytes:
                return "Error: Could not read PDF from S3"

            # Create a BytesIO object and use PyPDF2 to read it
            pdf_file = io.BytesIO(pdf_bytes)
            reader = PdfReader(pdf_file)

            text = ""
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                text += f"\n--- Page {page_num} ---\n{page_text}"

            print(f"✓ Extracted text from S3 PDF ({len(reader.pages)} pages)")
            return text
        except Exception as e:
            print(f"Error extracting text from S3 PDF: {e}")
            return f"Error: Could not extract text from S3 PDF - {str(e)}"

