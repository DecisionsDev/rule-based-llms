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
from botocore.exceptions import ClientError
import os
from typing import Dict, Optional
from datetime import datetime

class S3Service:
    """
    Handles S3 operations for policy documents and generated rules
    """

    def __init__(self):
        self.bucket_name = os.getenv("AWS_S3_BUCKET", "uw-data-extraction")
        self.region = os.getenv("AWS_REGION", "us-east-1")

        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )
            print(f"S3 client initialized for bucket: {self.bucket_name}")
        except Exception as e:
            print(f"Warning: Could not initialize S3 client: {e}")
            self.s3_client = None

    def download_policy_from_s3(self, s3_key: str, local_path: str) -> Dict:
        """
        Download a policy PDF from S3

        :param s3_key: S3 key (path) of the file
        :param local_path: Local path to save the file
        :return: Download result
        """
        if not self.s3_client:
            return {
                "status": "error",
                "message": "S3 client not initialized"
            }

        try:
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download file
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)

            file_size = os.path.getsize(local_path)
            print(f"✓ Downloaded {s3_key} from S3 ({file_size} bytes)")

            return {
                "status": "success",
                "message": f"Downloaded {s3_key} from S3",
                "local_path": local_path,
                "s3_key": s3_key,
                "file_size": file_size
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            return {
                "status": "error",
                "message": f"S3 download failed: {error_code}",
                "error": str(e)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error downloading from S3: {str(e)}"
            }

    def download_from_url(self, s3_url: str, local_path: str) -> Dict:
        """
        Download a policy from S3 URL (extracts key from URL)

        :param s3_url: Full S3 URL (e.g., https://bucket.s3.region.amazonaws.com/path/file.pdf)
        :param local_path: Local path to save the file
        :return: Download result
        """
        # Extract S3 key from URL
        # Format: https://bucket.s3.region.amazonaws.com/key/path/file.pdf
        try:
            parts = s3_url.split('.amazonaws.com/')
            if len(parts) == 2:
                s3_key = parts[1]
                return self.download_policy_from_s3(s3_key, local_path)
            else:
                return {
                    "status": "error",
                    "message": "Invalid S3 URL format"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error parsing S3 URL: {str(e)}"
            }

    def upload_jar_to_s3(self, local_jar_path: str, container_id: str, version: str) -> Dict:
        """
        Upload generated JAR file to S3

        :param local_jar_path: Local path to the JAR file
        :param container_id: Container ID for organizing files
        :param version: Version of the rules
        :return: Upload result
        """
        if not self.s3_client:
            return {
                "status": "error",
                "message": "S3 client not initialized"
            }

        try:
            # Create S3 key with timestamp and version
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"generated-rules/{container_id}/{version}/{container_id}_{timestamp}.jar"

            # Upload file
            self.s3_client.upload_file(
                local_jar_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'application/java-archive'}
            )

            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

            file_size = os.path.getsize(local_jar_path)
            print(f"✓ Uploaded JAR to S3: {s3_key} ({file_size} bytes)")

            return {
                "status": "success",
                "message": f"JAR uploaded to S3",
                "s3_key": s3_key,
                "s3_url": s3_url,
                "bucket": self.bucket_name,
                "file_size": file_size
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            return {
                "status": "error",
                "message": f"S3 upload failed: {error_code}",
                "error": str(e)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error uploading to S3: {str(e)}"
            }

    def upload_drl_to_s3(self, local_drl_path: str, container_id: str, version: str) -> Dict:
        """
        Upload generated DRL file to S3

        :param local_drl_path: Local path to the DRL file
        :param container_id: Container ID for organizing files
        :param version: Version of the rules
        :return: Upload result
        """
        if not self.s3_client:
            return {
                "status": "error",
                "message": "S3 client not initialized"
            }

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"generated-rules/{container_id}/{version}/{container_id}_{timestamp}.drl"

            self.s3_client.upload_file(
                local_drl_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'text/plain'}
            )

            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

            print(f"✓ Uploaded DRL to S3: {s3_key}")

            return {
                "status": "success",
                "message": f"DRL uploaded to S3",
                "s3_key": s3_key,
                "s3_url": s3_url,
                "bucket": self.bucket_name
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error uploading DRL to S3: {str(e)}"
            }

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for an S3 object

        :param s3_key: S3 key of the object
        :param expiration: URL expiration time in seconds (default 1 hour)
        :return: Presigned URL or None
        """
        if not self.s3_client:
            return None

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return None

    def read_pdf_from_s3(self, s3_key: str) -> Optional[bytes]:
        """
        Read PDF file content from S3 directly into memory (no local file needed)

        :param s3_key: S3 key of the PDF file
        :return: PDF file bytes or None
        """
        if not self.s3_client:
            return None

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            pdf_bytes = response['Body'].read()
            print(f"✓ Read {len(pdf_bytes)} bytes from S3: {s3_key}")
            return pdf_bytes
        except ClientError as e:
            print(f"Error reading PDF from S3: {e}")
            return None

    def parse_s3_url(self, s3_url: str) -> Dict[str, str]:
        """
        Parse S3 URL to extract bucket and key

        :param s3_url: S3 URL in either format:
                       - s3://bucket/key/path/file.pdf
                       - https://bucket.s3.region.amazonaws.com/key/path/file.pdf
        :return: Dict with 'bucket' and 'key'
        """
        try:
            # Format 1: s3://bucket/key/path/file.pdf
            if s3_url.startswith('s3://'):
                # Remove s3:// prefix
                s3_path = s3_url[5:]
                # Split on first slash to separate bucket from key
                parts = s3_path.split('/', 1)
                if len(parts) == 2:
                    bucket = parts[0]
                    key = parts[1]
                    return {"bucket": bucket, "key": key}
                else:
                    return {"error": "Invalid S3 URL format: missing key after bucket"}

            # Format 2: https://bucket.s3.region.amazonaws.com/key/path/file.pdf
            elif '.amazonaws.com/' in s3_url:
                parts = s3_url.split('.amazonaws.com/')
                if len(parts) == 2:
                    # Extract bucket from domain
                    domain_parts = s3_url.split('/')
                    bucket = domain_parts[2].split('.')[0]
                    key = parts[1]
                    return {"bucket": bucket, "key": key}
                else:
                    return {"error": "Invalid S3 URL format: could not parse HTTPS URL"}
            else:
                return {"error": f"Invalid S3 URL format. Expected 's3://bucket/key' or 'https://bucket.s3.region.amazonaws.com/key', got: {s3_url[:50]}..."}
        except Exception as e:
            return {"error": f"Error parsing S3 URL: {str(e)}"}

    def upload_excel_to_s3(self, local_excel_path: str, bank_id: str, policy_type: str,
                          container_id: str, version: str) -> Dict:
        """
        Upload generated Excel file to S3

        :param local_excel_path: Local path to the Excel file
        :param bank_id: Bank identifier
        :param policy_type: Policy type
        :param container_id: Container ID for organizing files
        :param version: Version of the rules
        :return: Upload result
        """
        if not self.s3_client:
            return {
                "status": "error",
                "message": "S3 client not initialized"
            }

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{bank_id}_{policy_type}_rules_{timestamp}.xlsx"
            s3_key = f"generated-rules/{container_id}/{version}/{filename}"

            # Upload file
            self.s3_client.upload_file(
                local_excel_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                }
            )

            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

            file_size = os.path.getsize(local_excel_path)
            print(f"✓ Uploaded Excel to S3: {s3_key} ({file_size} bytes)")

            return {
                "status": "success",
                "message": f"Excel file uploaded to S3",
                "s3_key": s3_key,
                "s3_url": s3_url,
                "bucket": self.bucket_name,
                "file_size": file_size
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error uploading Excel to S3: {str(e)}"
            }

    def upload_file_to_s3(self, file_content: bytes, filename: str, folder: str = "uploads") -> Dict:
        """
        Upload any file to S3 in a specified folder
        
        :param file_content: File content as bytes
        :param filename: Original filename
        :param folder: S3 folder path (default: "uploads")
        :return: Upload result with S3 URL and key
        """
        if not self.s3_client:
            return {
                "status": "error",
                "message": "S3 client not initialized. Please check AWS credentials."
            }

        try:
            # Sanitize filename to prevent path traversal
            safe_filename = os.path.basename(filename).replace(' ', '_')

            # Add timestamp to filename to prevent overwrites
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(safe_filename)
            timestamped_filename = f"{name}_{timestamp}{ext}"

            # Construct S3 key: folder/filename_timestamp.ext (no date subfolder)
            s3_key = f"{folder}/{timestamped_filename}"
            
            # Determine content type based on file extension
            content_type = self._get_content_type(safe_filename)
            
            # Upload file to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'original-filename': safe_filename,
                    'upload-timestamp': timestamp
                }
            )
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            file_size = len(file_content)
            print(f"✓ Uploaded file to S3: {s3_key} ({file_size} bytes)")
            
            return {
                "status": "success",
                "message": f"File uploaded successfully to S3",
                "s3_key": s3_key,
                "s3_url": s3_url,
                "bucket": self.bucket_name,
                "filename": timestamped_filename,
                "original_filename": safe_filename,
                "folder": folder,
                "file_size": file_size,
                "content_type": content_type
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error'].get('Message', str(e))
            return {
                "status": "error",
                "message": f"S3 upload failed: {error_code}",
                "error": error_message,
                "error_code": error_code
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error uploading file to S3: {str(e)}",
                "error": str(e)
            }

    def generate_presigned_url_from_s3_url(self, s3_url: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL from an S3 URL

        :param s3_url: Full S3 URL (e.g., https://bucket.s3.region.amazonaws.com/path/file.pdf)
        :param expiration: URL expiration time in seconds (default 1 hour)
        :return: Presigned URL or None
        """
        if not s3_url:
            return None

        # Parse S3 URL to extract key
        s3_info = self.parse_s3_url(s3_url)
        if "error" in s3_info:
            print(f"Error parsing S3 URL for presigned URL generation: {s3_info['error']}")
            return None

        s3_key = s3_info["key"]
        return self.generate_presigned_url(s3_key, expiration)

    def _get_content_type(self, filename: str) -> str:
        """
        Determine content type based on file extension

        :param filename: Filename with extension
        :return: MIME content type
        """
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.csv': 'text/csv',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.zip': 'application/zip',
            '.jar': 'application/java-archive',
            '.drl': 'text/plain'
        }
        return content_types.get(ext, 'application/octet-stream')
