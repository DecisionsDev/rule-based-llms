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
import requests
from requests.auth import HTTPBasicAuth
import os
from typing import Dict
import zipfile
import shutil
import subprocess
import tempfile
from datetime import datetime

class DroolsDeploymentService:
    """
    Handles deployment of generated rules to Drools KIE Server
    Supports container-per-ruleset architecture
    """

    def __init__(self):
        # DROOLS_SERVER_URL should be the full KIE Server REST API base URL
        # e.g., http://drools:8080/kie-server/services/rest/server
        self.server_url = os.getenv("DROOLS_SERVER_URL", "http://localhost:8080/kie-server/services/rest/server")
        self.username = os.getenv("DROOLS_USERNAME", "kieserver")
        self.password = os.getenv("DROOLS_PASSWORD", "kieserver1!")

        # Use temp directory instead of persistent storage
        # Files will be auto-deleted when temp directory context exits
        self.use_temp_dir = True

        # Container orchestration mode
        self.use_orchestrator = os.getenv("USE_CONTAINER_ORCHESTRATOR", "false").lower() == "true"

        # Load orchestrator if enabled
        self.orchestrator = None
        if self.use_orchestrator:
            try:
                from ContainerOrchestrator import get_orchestrator
                self.orchestrator = get_orchestrator()
                print(f"Drools Deployment Service initialized with container orchestration enabled")
            except Exception as e:
                print(f"⚠ Failed to load orchestrator: {e}")
                self.use_orchestrator = False
                print(f"Drools Deployment Service initialized - Using temporary directories (no persistent local storage)")
        else:
            print(f"Drools Deployment Service initialized - Using temporary directories (no persistent local storage)")

    def deploy_rules(self, drl_content: str, container_id: str, group_id: str = "com.underwriting",
                     artifact_id: str = "underwriting-rules", version: str = None) -> Dict:
        """
        Deploy DRL rules to Drools KIE Server

        Note: This is a simplified approach. Full deployment typically requires:
        1. Creating a KJar (Knowledge JAR) with the DRL and kmodule.xml
        2. Deploying to Maven repo
        3. Creating/updating KIE Container

        For production, consider using KIE Workbench or manual KJar creation.

        :param drl_content: The Drools DRL rule content
        :param container_id: KIE container ID
        :param group_id: Maven group ID
        :param artifact_id: Maven artifact ID
        :param version: Version (auto-generated if not provided)
        :return: Deployment result
        """

        # Auto-generate version if not provided
        if not version:
            version = datetime.now().strftime("%Y%m%d.%H%M%S")

        # First, save the DRL file locally
        drl_path = self.save_drl_file(drl_content, f"{container_id}.drl")

        # For now, we'll return instructions for manual deployment
        # In a production system, you would:
        # 1. Create a proper KJar structure
        # 2. Build with Maven
        # 3. Deploy to KIE Server

        return {
            "status": "saved_locally",
            "message": "DRL rules saved. Manual deployment to KIE Server required.",
            "drl_path": drl_path,
            "deployment_instructions": self._get_deployment_instructions(
                container_id, group_id, artifact_id, version
            ),
            "container_id": container_id,
            "release_id": {
                "group-id": group_id,
                "artifact-id": artifact_id,
                "version": version
            }
        }

    def save_drl_file(self, drl_content: str, filename: str, base_dir: str = None) -> str:
        """
        Save DRL content to file

        :param drl_content: DRL rule content
        :param filename: Filename (should end with .drl)
        :param base_dir: Base directory to save to (if None, uses temp directory)
        :return: Full file path
        """
        if not filename.endswith('.drl'):
            filename += '.drl'

        # If no base_dir provided, caller must provide it (for temp directory usage)
        if base_dir is None:
            raise ValueError("base_dir must be provided when using temporary directories")

        filepath = os.path.join(base_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(drl_content)

        print(f"DRL rules saved to: {filepath}")
        return filepath

    def create_kjar_structure(self, drl_content: str, container_id: str,
                              group_id: str = "com.underwriting",
                              artifact_id: str = "underwriting-rules",
                              version: str = "1.0.0",
                              base_dir: str = None) -> str:
        """
        Create a complete KJar structure for Drools deployment

        :param drl_content: DRL rule content
        :param container_id: Container ID
        :param group_id: Maven group ID
        :param artifact_id: Maven artifact ID
        :param version: Version
        :param base_dir: Base directory to create KJar in (if None, uses temp directory)
        :return: Path to the created KJar directory
        """
        # If no base_dir provided, caller must provide it (for temp directory usage)
        if base_dir is None:
            raise ValueError("base_dir must be provided when using temporary directories")

        kjar_dir = os.path.join(base_dir, f"{container_id}_kjar")

        # Clean up if exists
        if os.path.exists(kjar_dir):
            shutil.rmtree(kjar_dir)

        # Create directory structure
        src_main = os.path.join(kjar_dir, "src", "main")
        resources_meta = os.path.join(src_main, "resources", "META-INF")
        rules_dir = os.path.join(src_main, "resources", "rules")

        os.makedirs(resources_meta, exist_ok=True)
        os.makedirs(rules_dir, exist_ok=True)

        # 1. Create pom.xml
        pom_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>{group_id}</groupId>
    <artifactId>{artifact_id}</artifactId>
    <version>{version}</version>
    <packaging>jar</packaging>

    <name>Underwriting Rules</name>
    <description>Auto-generated underwriting rules</description>

    <dependencies>
        <dependency>
            <groupId>org.drools</groupId>
            <artifactId>drools-core</artifactId>
            <version>7.74.1.Final</version>
            <scope>provided</scope>
        </dependency>
        <dependency>
            <groupId>org.drools</groupId>
            <artifactId>drools-compiler</artifactId>
            <version>7.74.1.Final</version>
            <scope>provided</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.kie</groupId>
                <artifactId>kie-maven-plugin</artifactId>
                <version>7.74.1.Final</version>
                <extensions>true</extensions>
            </plugin>
        </plugins>
    </build>
</project>
"""
        with open(os.path.join(kjar_dir, "pom.xml"), 'w') as f:
            f.write(pom_xml)

        # 2. Create kmodule.xml
        kmodule_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kmodule xmlns="http://www.drools.org/xsd/kmodule">
    <kbase name="rules" packages="rules">
        <ksession name="ksession-rules" default="true"/>
    </kbase>
</kmodule>
"""
        with open(os.path.join(resources_meta, "kmodule.xml"), 'w') as f:
            f.write(kmodule_xml)

        # 3. Save DRL file
        with open(os.path.join(rules_dir, "underwriting-rules.drl"), 'w') as f:
            f.write(drl_content)

        # 4. Create README with build instructions
        readme = f"""# Underwriting Rules KJar

## Build Instructions

1. Navigate to this directory:
   cd {kjar_dir}

2. Build with Maven:
   mvn clean install

3. Deploy to KIE Server:

   Option A: Via REST API
   curl -X PUT "http://localhost:8080/kie-server/services/rest/server/containers/{container_id}" \\
     -H "Content-Type: application/json" \\
     -u admin:admin \\
     -d '{{
       "container-id": "{container_id}",
       "release-id": {{
         "group-id": "{group_id}",
         "artifact-id": "{artifact_id}",
         "version": "{version}"
       }}
     }}'

   Option B: Via KIE Workbench UI
   - Login to KIE Workbench
   - Navigate to Deploy > Execution Servers
   - Click "Add Container"
   - Enter the release ID information above

## Container Information
- Container ID: {container_id}
- Group ID: {group_id}
- Artifact ID: {artifact_id}
- Version: {version}
"""
        with open(os.path.join(kjar_dir, "README.md"), 'w') as f:
            f.write(readme)

        print(f"KJar structure created at: {kjar_dir}")
        print(f"To build: cd {kjar_dir} && mvn clean install")

        return kjar_dir

    def _get_deployment_instructions(self, container_id: str, group_id: str,
                                     artifact_id: str, version: str) -> str:
        """Generate deployment instructions"""
        return f"""
Manual Deployment Steps:

1. Create KJar structure:
   Use create_kjar_structure() method or manually create Maven project

2. Build the KJar:
   cd <kjar-directory>
   mvn clean install

3. Deploy to KIE Server via REST API:
   curl -X PUT "{self.server_url}/containers/{container_id}" \\
     -H "Content-Type: application/json" \\
     -u {self.username}:******* \\
     -d '{{
       "container-id": "{container_id}",
       "release-id": {{
         "group-id": "{group_id}",
         "artifact-id": "{artifact_id}",
         "version": "{version}"
       }}
     }}'

4. Verify deployment:
   curl -X GET "{self.server_url}/containers/{container_id}" \\
     -u {self.username}:*******

5. Test the rules:
   Use the DroolsService class to invoke decisions
"""

    def list_containers(self) -> Dict:
        """
        List all deployed containers on KIE Server

        :return: Dictionary with container information
        """
        try:
            response = requests.get(
                f"{self.server_url}/containers",
                auth=HTTPBasicAuth(self.username, self.password),
                headers={'Accept': 'application/json'}
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to list containers: {response.status_code}"}

        except Exception as e:
            return {"error": f"Error listing containers: {str(e)}"}

    def get_container_status(self, container_id: str) -> Dict:
        """
        Get status of a specific container

        :param container_id: Container ID
        :return: Container status
        """
        try:
            response = requests.get(
                f"{self.server_url}/containers/{container_id}",
                auth=HTTPBasicAuth(self.username, self.password),
                headers={'Accept': 'application/json'}
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Container not found or error: {response.status_code}"}

        except Exception as e:
            return {"error": f"Error getting container status: {str(e)}"}

    def build_kjar(self, kjar_dir: str) -> Dict:
        """
        Build KJar using Maven

        :param kjar_dir: Path to KJar directory containing pom.xml
        :return: Build result
        """
        print(f"Building KJar in {kjar_dir}...")

        # Check if Maven is available
        try:
            subprocess.run(["mvn", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                "status": "error",
                "message": "Maven not found. Please install Maven or build manually."
            }

        # Run Maven build
        try:
            result = subprocess.run(
                ["mvn", "clean", "install", "-DskipTests"],
                cwd=kjar_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode == 0:
                # Find the built JAR file
                target_dir = os.path.join(kjar_dir, "target")
                jar_files = [f for f in os.listdir(target_dir) if f.endswith('.jar') and not f.endswith('-sources.jar')]

                if jar_files:
                    jar_path = os.path.join(target_dir, jar_files[0])
                    print(f"✓ KJar built successfully: {jar_path}")
                    return {
                        "status": "success",
                        "message": "KJar built successfully",
                        "jar_path": jar_path,
                        "build_output": result.stdout
                    }
                else:
                    return {
                        "status": "error",
                        "message": "JAR file not found after build",
                        "build_output": result.stdout
                    }
            else:
                return {
                    "status": "error",
                    "message": "Maven build failed",
                    "build_output": result.stdout,
                    "error_output": result.stderr
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "Maven build timed out (5 minutes)"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during Maven build: {str(e)}"
            }

    def deploy_container(self, container_id: str, group_id: str, artifact_id: str, version: str) -> Dict:
        """
        Deploy a KIE container to the KIE Server

        :param container_id: Container ID
        :param group_id: Maven group ID
        :param artifact_id: Maven artifact ID
        :param version: Version
        :return: Deployment result
        """
        print(f"Deploying container {container_id} to KIE Server...")

        # Check if container already exists
        existing = self.get_container_status(container_id)
        if "error" not in existing:
            print(f"Container {container_id} already exists. Disposing first...")
            self.dispose_container(container_id)

        # Create container
        payload = {
            "container-id": container_id,
            "release-id": {
                "group-id": group_id,
                "artifact-id": artifact_id,
                "version": version
            }
        }

        try:
            print(f"DEBUG: Deployment payload: {payload}")
            print(f"DEBUG: Deployment URL: {self.server_url}/containers/{container_id}")

            response = requests.put(
                f"{self.server_url}/containers/{container_id}",
                auth=HTTPBasicAuth(self.username, self.password),
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                json=payload
            )

            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response body: {response.text}")

            if response.status_code in [200, 201]:
                print(f"✓ Container {container_id} deployed successfully")
                return {
                    "status": "success",
                    "message": f"Container {container_id} deployed successfully",
                    "response": response.json()
                }
            else:
                print(f"✗ Deployment failed with status {response.status_code}")
                print(f"✗ Error response: {response.text}")
                return {
                    "status": "error",
                    "message": f"Deployment failed with status {response.status_code}",
                    "response_text": response.text,
                    "response_json": response.json() if response.headers.get('content-type') == 'application/json' else None
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deploying container: {str(e)}"
            }

    def dispose_container(self, container_id: str) -> Dict:
        """
        Dispose (delete) a KIE container

        :param container_id: Container ID
        :return: Disposal result
        """
        try:
            print(f"DEBUG: Disposing container {container_id}")
            print(f"DEBUG: Disposal URL: {self.server_url}/containers/{container_id}")

            response = requests.delete(
                f"{self.server_url}/containers/{container_id}",
                auth=HTTPBasicAuth(self.username, self.password),
                headers={'Accept': 'application/json'}
            )

            print(f"DEBUG: Disposal response status: {response.status_code}")
            print(f"DEBUG: Disposal response body: {response.text}")

            if response.status_code in [200, 204]:
                print(f"✓ Container {container_id} disposed successfully")
                return {"status": "success", "message": f"Container {container_id} disposed"}
            else:
                print(f"⚠ Failed to dispose container: {response.status_code} - {response.text}")
                return {"status": "error", "message": f"Failed to dispose: {response.status_code}", "response_text": response.text}

        except Exception as e:
            print(f"✗ Error disposing container: {str(e)}")
            return {"status": "error", "message": str(e)}

    def deploy_rules_automatically(self, drl_content: str, container_id: str,
                                   group_id: str = "com.underwriting",
                                   artifact_id: str = "underwriting-rules",
                                   version: str = None) -> Dict:
        """
        Fully automated deployment: create KJar, build with Maven, and deploy to KIE Server

        Uses temporary directories - all files are auto-deleted after processing

        :param drl_content: DRL rule content
        :param container_id: Container ID
        :param group_id: Maven group ID
        :param artifact_id: Maven artifact ID
        :param version: Version (auto-generated if not provided)
        :return: Complete deployment result
        """
        # Auto-generate version if not provided
        if not version:
            version = datetime.now().strftime("%Y%m%d.%H%M%S")

        result = {
            "container_id": container_id,
            "release_id": {
                "group-id": group_id,
                "artifact-id": artifact_id,
                "version": version
            },
            "steps": {}
        }

        # Use temporary directory for all build artifacts
        # This auto-deletes when the context exits
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Using temporary directory: {temp_dir}")

            # Step 1: Save DRL file
            drl_path = self.save_drl_file(drl_content, f"{container_id}.drl", base_dir=temp_dir)
            result["steps"]["save_drl"] = {"status": "success", "path": drl_path}

            # Step 2: Create KJar structure
            kjar_dir = self.create_kjar_structure(drl_content, container_id, group_id, artifact_id, version, base_dir=temp_dir)
            result["steps"]["create_kjar"] = {"status": "success", "path": kjar_dir}

            # Step 3: Build KJar with Maven
            build_result = self.build_kjar(kjar_dir)
            result["steps"]["build"] = build_result

            if build_result["status"] != "success":
                result["status"] = "partial"
                result["message"] = "KJar structure created but Maven build failed. Manual build required."
                result["manual_instructions"] = f"Maven build failed - check build output for errors"
                return result

            # Copy JAR and DRL to a second temp location for S3 upload
            # (since current temp_dir will be deleted when context exits)
            jar_path = build_result.get("jar_path")
            if jar_path and os.path.exists(jar_path):
                # Create a named temp file for JAR that won't be auto-deleted
                jar_temp = tempfile.NamedTemporaryFile(suffix='.jar', delete=False)
                jar_temp.close()
                shutil.copy2(jar_path, jar_temp.name)
                result["steps"]["build"]["jar_path"] = jar_temp.name
                print(f"✓ JAR copied to temp location for S3 upload: {jar_temp.name}")

            # Copy DRL file to temp location for S3 upload
            if drl_path and os.path.exists(drl_path):
                drl_temp = tempfile.NamedTemporaryFile(suffix='.drl', delete=False)
                drl_temp.close()
                shutil.copy2(drl_path, drl_temp.name)
                result["steps"]["save_drl"]["path"] = drl_temp.name
                print(f"✓ DRL copied to temp location for S3 upload: {drl_temp.name}")

            # Step 4: Create dedicated Drools container (if orchestrator enabled)
            if self.use_orchestrator and self.orchestrator:
                print(f"Creating dedicated Drools container for {container_id}...")
                jar_path = result["steps"]["build"].get("jar_path")
                if jar_path:
                    orchestration_result = self.orchestrator.create_drools_container(container_id, jar_path)
                    result["steps"]["create_container"] = orchestration_result

                    if orchestration_result["status"] == "success":
                        print(f"✓ Dedicated container created: {orchestration_result.get('container_name')}")
                    elif orchestration_result["status"] == "exists":
                        print(f"ℹ Container already exists: {container_id}")
                    else:
                        print(f"⚠ Failed to create container: {orchestration_result.get('message')}")

            # Step 5: Deploy to KIE Server
            deploy_result = self.deploy_container(container_id, group_id, artifact_id, version)
            result["steps"]["deploy"] = deploy_result

            if deploy_result["status"] == "success":
                result["status"] = "success"
                message = f"Rules automatically deployed to container {container_id}"
                if self.use_orchestrator:
                    message += " (dedicated Drools container)"
                result["message"] = message
            else:
                result["status"] = "partial"
                result["message"] = "KJar built but deployment to KIE Server failed"

            print(f"✓ Build directory will be auto-deleted: {temp_dir}")

        # Temp directory and all contents are now deleted
        return result
