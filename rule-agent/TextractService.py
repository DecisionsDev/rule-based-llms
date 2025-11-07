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

        :param s3_bucket: S3 bucket name
        :param s3_key: S3 object key
        :param queries: List of questions to ask about the document
        :return: Extracted data with answers and confidence scores
        """
        # AWS Textract limit: Maximum 30 queries per API call
        MAX_QUERIES_PER_CALL = 30

        if len(queries) > MAX_QUERIES_PER_CALL:
            print(f"⚠ WARNING: {len(queries)} queries requested, but AWS Textract supports maximum {MAX_QUERIES_PER_CALL} queries per call")
            print(f"  Processing first {MAX_QUERIES_PER_CALL} queries only...")
            queries = queries[:MAX_QUERIES_PER_CALL]

        try:
            # Start async analysis job
            print(f"Starting asynchronous Textract analysis job with {len(queries)} queries...")
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

        for block in response.get('Blocks', []):
            if block['BlockType'] == 'QUERY_RESULT':
                query_alias = block.get('Query', {}).get('Alias')
                answer = block.get('Text', '')
                confidence = block.get('Confidence', 0)

                if query_alias in query_map:
                    results["queries"][query_map[query_alias]] = {
                        'answer': answer,
                        'confidence': confidence,
                        'alias': query_alias
                    }

        return results
