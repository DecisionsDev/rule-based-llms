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
import boto3
import os
import time
from typing import Dict, List, Optional

class TextractService:
    """
    AWS Textract service for extracting structured data from policy documents
    Supports both synchronous (single-page) and asynchronous (multi-page) operations
    """

    def __init__(self):
        """
        Initialize AWS Textract client

        Environment variables:
        - AWS_ACCESS_KEY_ID: AWS access key
        - AWS_SECRET_ACCESS_KEY: AWS secret key
        - AWS_REGION: AWS region (default: us-east-1)
        """
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.isConfigured = self.aws_access_key is not None and self.aws_secret_key is not None

        if self.isConfigured:
            try:
                self.textract_client = boto3.client(
                    'textract',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                print(f"AWS Textract client initialized for region: {self.aws_region}")
            except Exception as e:
                print(f"Error initializing AWS Textract client: {e}")
                self.isConfigured = False
        else:
            print("AWS Textract not configured - missing AWS credentials")
            self.textract_client = None

    def analyze_document(self, document_path: Optional[str] = None,
                        s3_bucket: Optional[str] = None,
                        s3_key: Optional[str] = None,
                        queries: List[str] = []) -> Dict:
        """
        Use Textract to extract data based on queries
        Automatically uses async API for multi-page documents

        :param document_path: Local path to PDF document (optional if S3 params provided)
        :param s3_bucket: S3 bucket name (optional if document_path provided)
        :param s3_key: S3 object key (optional if document_path provided)
        :param queries: List of questions to ask about the document
        :return: Extracted data with answers and confidence scores
        """
        if not self.isConfigured:
            return {"error": "AWS Textract is not configured. Please set AWS credentials."}

        try:
            print(f"Analyzing document with {len(queries)} queries using AWS Textract...")

            # Build document parameter for Textract
            if s3_bucket and s3_key:
                # Use S3 document directly - no download needed!
                document_param = {
                    'S3Object': {
                        'Bucket': s3_bucket,
                        'Name': s3_key
                    }
                }
                print(f"Using S3 document: s3://{s3_bucket}/{s3_key}")

                # For S3 documents, use async API (supports multi-page)
                print("Using asynchronous Textract API (supports multi-page documents)...")
                return self._analyze_document_async(s3_bucket, s3_key, queries)

            elif document_path:
                # Use local file bytes - try synchronous first
                with open(document_path, 'rb') as document:
                    document_bytes = document.read()
                document_param = {'Bytes': document_bytes}
                print(f"Using local document: {document_path}")

                try:
                    # Try synchronous API (only works for single-page)
                    response = self.textract_client.analyze_document(
                        Document=document_param,
                        FeatureTypes=['QUERIES'],
                        QueriesConfig={
                            'Queries': [{'Text': q, 'Alias': f'Q{i}'}
                                       for i, q in enumerate(queries)]
                        }
                    )
                    return self._parse_textract_response(response, queries)

                except Exception as sync_error:
                    if 'UnsupportedDocumentException' in str(sync_error):
                        print(f"⚠ Synchronous API failed (multi-page document): {sync_error}")
                        print("Note: Local files with multiple pages require S3 upload for async processing")
                        return {"error": "Multi-page local documents not supported. Please use S3 URL instead."}
                    raise sync_error
            else:
                return {"error": "Either document_path or S3 bucket/key must be provided"}

        except Exception as e:
            print(f"Error analyzing document with Textract: {e}")
            return {"error": f"Textract analysis failed: {str(e)}"}

    def detect_text(self, document_path: str) -> str:
        """
        Simple text detection (OCR) from document

        :param document_path: Path to PDF document
        :return: Extracted text
        """
        if not self.isConfigured:
            return "AWS Textract is not configured. Please set AWS credentials."

        try:
            with open(document_path, 'rb') as document:
                document_bytes = document.read()

            print(f"Detecting text from document using AWS Textract...")

            response = self.textract_client.detect_document_text(
                Document={'Bytes': document_bytes}
            )

            # Extract all text blocks
            text_lines = []
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_lines.append(block.get('Text', ''))

            return '\n'.join(text_lines)

        except Exception as e:
            print(f"Error detecting text with Textract: {e}")
            return f"Textract text detection failed: {str(e)}"

    def _analyze_document_async(self, s3_bucket: str, s3_key: str, queries: List[str]) -> Dict:
        """
        Use asynchronous Textract API for multi-page documents with queries
        Supports batch processing for queries exceeding AWS Textract's 30 query limit

        :param s3_bucket: S3 bucket name
        :param s3_key: S3 object key
        :param queries: List of questions to ask about the document
        :return: Extracted data with answers and confidence scores
        """
        # AWS Textract limit: Maximum 30 queries per API call
        MAX_QUERIES_PER_CALL = 30

        # Deduplicate queries (case-insensitive, strip whitespace)
        # AWS Textract rejects duplicate queries
        original_count = len(queries)
        seen = set()
        deduplicated_queries = []
        for q in queries:
            normalized = q.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                deduplicated_queries.append(q)

        if len(deduplicated_queries) < original_count:
            print(f"⚠ Removed {original_count - len(deduplicated_queries)} duplicate queries")
            queries = deduplicated_queries

        # Check if batch processing is needed
        if len(queries) > MAX_QUERIES_PER_CALL:
            print(f"📊 Batch processing: {len(queries)} queries will be processed in batches of {MAX_QUERIES_PER_CALL}")
            num_batches = (len(queries) + MAX_QUERIES_PER_CALL - 1) // MAX_QUERIES_PER_CALL
            print(f"   Total batches: {num_batches}")

            # Split queries into batches
            query_batches = [queries[i:i + MAX_QUERIES_PER_CALL]
                           for i in range(0, len(queries), MAX_QUERIES_PER_CALL)]

            # Process each batch and merge results
            all_query_results = {}
            total_start_time = time.time()

            for batch_num, batch_queries in enumerate(query_batches, 1):
                print(f"\n{'='*60}")
                print(f"Processing batch {batch_num}/{num_batches} ({len(batch_queries)} queries)")
                print(f"{'='*60}")

                # Process this batch
                batch_result = self._process_single_textract_batch(
                    s3_bucket, s3_key, batch_queries,
                    batch_num, len(batch_queries)
                )

                if "error" in batch_result:
                    print(f"✗ Batch {batch_num} failed: {batch_result['error']}")
                    # Continue with other batches even if one fails
                    continue

                # Merge query results
                batch_query_results = batch_result.get("queries", {})
                all_query_results.update(batch_query_results)

                print(f"✓ Batch {batch_num} completed: {len(batch_query_results)} queries extracted")

            total_elapsed = time.time() - total_start_time
            print(f"\n{'='*60}")
            print(f"✓ Batch processing complete!")
            print(f"   Total time: {total_elapsed:.1f}s")
            print(f"   Total queries processed: {len(all_query_results)}/{len(queries)}")
            print(f"{'='*60}\n")

            return {
                "queries": all_query_results,
                "metadata": {
                    "total_blocks": 0,
                    "batch_count": num_batches,
                    "total_queries": len(queries),
                    "queries_extracted": len(all_query_results),
                    "total_time_seconds": total_elapsed
                }
            }
        else:
            # Single batch - process normally
            print(f"Processing {len(queries)} queries (single batch)")
            return self._process_single_textract_batch(s3_bucket, s3_key, queries, 1, len(queries))

    def _process_single_textract_batch(self, s3_bucket: str, s3_key: str,
                                       queries: List[str], batch_num: int,
                                       total_queries: int) -> Dict:
        """
        Process a single batch of queries with Textract

        :param s3_bucket: S3 bucket name
        :param s3_key: S3 object key
        :param queries: List of questions for this batch (max 30)
        :param batch_num: Batch number for logging
        :param total_queries: Total number of queries across all batches
        :return: Extracted data for this batch
        """
        try:
            # Start async analysis job
            print(f"Starting Textract job for batch {batch_num}...")
            print(f"DEBUG: S3 bucket={s3_bucket}, key={s3_key}")

            response = self.textract_client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': s3_bucket,
                        'Name': s3_key
                    }
                },
                FeatureTypes=['QUERIES'],
                QueriesConfig={
                    'Queries': [{'Text': q, 'Alias': f'Q{i}'}
                               for i, q in enumerate(queries)]
                }
            )

            job_id = response['JobId']
            print(f"✓ Textract job started: {job_id}")
            print("Waiting for job to complete...")

            # Poll for completion
            max_wait_time = 300  # 5 minutes max
            poll_interval = 2    # Poll every 2 seconds
            elapsed_time = 0

            while elapsed_time < max_wait_time:
                time.sleep(poll_interval)
                elapsed_time += poll_interval

                result = self.textract_client.get_document_analysis(JobId=job_id)
                status = result['JobStatus']

                if status == 'SUCCEEDED':
                    print(f"✓ Textract job completed successfully (took {elapsed_time}s)")

                    # Collect all pages of results
                    all_blocks = result.get('Blocks', [])
                    next_token = result.get('NextToken')

                    # Handle pagination if multiple result pages
                    while next_token:
                        result = self.textract_client.get_document_analysis(
                            JobId=job_id,
                            NextToken=next_token
                        )
                        all_blocks.extend(result.get('Blocks', []))
                        next_token = result.get('NextToken')

                    # Build response in same format as synchronous API
                    response_data = {
                        'Blocks': all_blocks,
                        'DocumentMetadata': result.get('DocumentMetadata', {})
                    }

                    return self._parse_textract_response(response_data, queries)

                elif status == 'FAILED':
                    error_msg = result.get('StatusMessage', 'Unknown error')
                    print(f"✗ Textract job failed: {error_msg}")
                    return {"error": f"Textract job failed: {error_msg}"}

                elif status in ['IN_PROGRESS', 'PARTIAL_SUCCESS']:
                    print(f"  Job status: {status} ({elapsed_time}s elapsed)")
                    continue
                else:
                    print(f"✗ Unexpected job status: {status}")
                    return {"error": f"Unexpected job status: {status}"}

            # Timeout
            print(f"✗ Textract job timed out after {max_wait_time}s")
            return {"error": f"Textract job timed out after {max_wait_time}s"}

        except Exception as e:
            print(f"✗ Error in async Textract analysis: {e}")
            print(f"  Exception type: {type(e).__name__}")
            print(f"  Exception details: {str(e)}")
            import traceback
            print(f"  Traceback: {traceback.format_exc()}")
            return {"error": f"Async Textract analysis failed: {str(e)}"}

    def _parse_textract_response(self, response: Dict, queries: List[str]) -> Dict:
        """
        Parse Textract response into structured data
        """
        results = {
            "queries": {},
            "metadata": {
                "total_blocks": len(response.get('Blocks', [])),
                "document_metadata": response.get('DocumentMetadata', {})
            }
        }

        # Map query aliases back to actual questions
        query_map = {f'Q{i}': q for i, q in enumerate(queries)}

        # DEBUG: Count block types to diagnose issue
        block_types = {}
        query_result_blocks = []
        query_blocks = []

        # STEP 1: Build mapping from QUERY_RESULT ID to query alias
        # QUERY blocks have Relationships that link to QUERY_RESULT IDs
        result_id_to_alias = {}

        for block in response.get('Blocks', []):
            if block.get('BlockType') == 'QUERY':
                query_alias = block.get('Query', {}).get('Alias')
                relationships = block.get('Relationships', [])

                for relationship in relationships:
                    if relationship.get('Type') == 'ANSWER':
                        for result_id in relationship.get('Ids', []):
                            result_id_to_alias[result_id] = query_alias

        # STEP 2: Extract answers from QUERY_RESULT blocks using the mapping
        for block in response.get('Blocks', []):
            block_type = block.get('BlockType', 'UNKNOWN')
            block_types[block_type] = block_types.get(block_type, 0) + 1

            if block_type == 'QUERY_RESULT':
                query_result_blocks.append(block)

                # Get answer data
                result_id = block.get('Id')
                answer = block.get('Text', '')
                confidence = block.get('Confidence', 0)

                # Map result ID back to query alias
                query_alias = result_id_to_alias.get(result_id)

                if query_alias and query_alias in query_map:
                    results["queries"][query_map[query_alias]] = {
                        'answer': answer,
                        'confidence': confidence,
                        'alias': query_alias
                    }
            elif block_type == 'QUERY':
                query_blocks.append(block)

        # DEBUG: Print diagnostic information
        print(f"DEBUG: Textract response analysis:")
        print(f"  Total blocks: {len(response.get('Blocks', []))}")
        print(f"  Block types: {block_types}")
        print(f"  QUERY blocks found: {len(query_blocks)}")
        print(f"  QUERY_RESULT blocks found: {len(query_result_blocks)}")
        print(f"  Result ID to alias mapping: {len(result_id_to_alias)} entries")
        print(f"  Expected queries: {len(queries)}")
        print(f"  Queries extracted: {len(results['queries'])}")

        # DEBUG: Show sample QUERY blocks if present
        if query_blocks and len(query_blocks) > 0:
            print(f"  Sample QUERY block: {query_blocks[0]}")

        # DEBUG: Show sample QUERY_RESULT blocks if present
        if query_result_blocks and len(query_result_blocks) > 0:
            print(f"  Sample QUERY_RESULT block: {query_result_blocks[0]}")

        return results
