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
import logging
import json
import os
from RuleService import RuleService

class DroolsService(RuleService):
    """
    Drools KIE Server integration for rule execution
    Supports multiple invocation modes: KIE Server batch commands, DMN, and custom REST
    Supports container-per-ruleset architecture with dynamic routing
    """

    def __init__(self):
        # Configuration from environment variables
        self.server_url = os.getenv("DROOLS_SERVER_URL", "http://localhost:8080")

        if not self.server_url.startswith("http://") and not self.server_url.startswith("https://"):
            self.server_url = "http://" + self.server_url

        self.username = os.getenv("DROOLS_USERNAME", "admin")
        self.password = os.getenv("DROOLS_PASSWORD", "admin")

        # Invocation mode: 'kie-batch', 'dmn', 'rest'
        self.invocation_mode = os.getenv("DROOLS_INVOCATION_MODE", "kie-batch")

        # Container orchestration mode
        self.use_orchestrator = os.getenv("USE_CONTAINER_ORCHESTRATOR", "false").lower() == "true"

        # Load orchestrator if enabled
        self.orchestrator = None
        if self.use_orchestrator:
            try:
                from ContainerOrchestrator import get_orchestrator
                self.orchestrator = get_orchestrator()
                print("✓ Container orchestrator enabled")
            except Exception as e:
                print(f"⚠ Failed to load orchestrator: {e}")
                self.use_orchestrator = False

        # Check connection
        self.isConnected = self.checkDroolsServer()

    def _resolve_container_endpoint(self, rulesetPath):
        """
        Resolve the correct Drools container endpoint for a request

        Args:
            rulesetPath: Path like /kie-server/services/rest/server/containers/chase-insurance-rules/...

        Returns:
            tuple: (base_url, remaining_path)
        """
        if not self.use_orchestrator or not self.orchestrator:
            # Use default server URL
            return self.server_url, rulesetPath

        # Extract container ID from path
        # Path format: /containers/{container_id}/...
        # or: /containers/instances/{container_id}
        parts = rulesetPath.split('/')
        try:
            containers_index = parts.index('containers')
            if containers_index + 1 < len(parts):
                # Check if this is /containers/instances/{container_id} format
                if parts[containers_index + 1] == 'instances' and containers_index + 2 < len(parts):
                    container_id = parts[containers_index + 2]
                else:
                    container_id = parts[containers_index + 1]

                # Look up container endpoint
                endpoint = self.orchestrator.get_container_endpoint(container_id)
                if endpoint:
                    print(f"✓ Routing to DEDICATED container: {container_id} at {endpoint}")
                    return endpoint, rulesetPath
                else:
                    # Container not found - raise error instead of falling back
                    error_msg = f"Container {container_id} not found or unhealthy in dedicated container registry"
                    print(f"✗ {error_msg}")
                    raise ValueError(error_msg)
        except (ValueError, IndexError) as e:
            # Could not extract container ID - raise error instead of falling back
            error_msg = f"Could not extract container ID from path: {rulesetPath}"
            print(f"✗ {error_msg}")
            raise ValueError(error_msg)

        # Should not reach here when orchestrator is enabled
        raise ValueError(f"Unexpected path resolution failure for: {rulesetPath}")

    def invokeDecisionService(self, rulesetPath, decisionInputs):
        """
        Invoke Drools decision service

        :param rulesetPath: Path to the Drools KIE container and decision endpoint
                           Examples:
                           - KIE Batch: /kie-server/services/rest/server/containers/{containerId}/ksession/{sessionId}
                           - DMN: /kie-server/services/rest/server/containers/{containerId}/dmn
                           - Custom: /api/underwriting/evaluate
        :param decisionInputs: Dictionary of input parameters
        :return: JSON response from Drools
        """

        if self.invocation_mode == 'dmn':
            return self._invoke_dmn(rulesetPath, decisionInputs)
        elif self.invocation_mode == 'kie-batch':
            return self._invoke_kie_batch(rulesetPath, decisionInputs)
        else:
            # Simple REST mode - just pass through
            return self._invoke_rest(rulesetPath, decisionInputs)

    def _invoke_kie_batch(self, rulesetPath, decisionInputs):
        """Invoke using KIE Server batch execution commands"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Build commands to insert each fact separately with proper type
        commands = []

        # Insert applicant if present
        if 'applicant' in decisionInputs:
            commands.append({
                "insert": {
                    "object": {
                        "com.underwriting.rules.Applicant": decisionInputs['applicant']
                    },
                    "out-identifier": "applicant",
                    "return-object": True
                }
            })

        # Insert policy if present
        if 'policy' in decisionInputs:
            commands.append({
                "insert": {
                    "object": {
                        "com.underwriting.rules.Policy": decisionInputs['policy']
                    },
                    "out-identifier": "policy",
                    "return-object": True
                }
            })

        # Fire all rules
        commands.append({
            "fire-all-rules": {
                "max": -1
            }
        })

        # Get all facts
        commands.append({
            "get-objects": {
                "out-identifier": "all-facts"
            }
        })

        # Drools KIE Server batch command format
        payload = {
            "lookup": None,
            "commands": commands
        }

        try:
            # Resolve correct container endpoint
            base_url, path = self._resolve_container_endpoint(rulesetPath)
            url = base_url + path
            print(f"Invoking Drools (KIE Batch) at: {url}")
            import json
            print(f"DEBUG - Payload: {json.dumps(payload, indent=2)}")

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                auth=HTTPBasicAuth(self.username, self.password)
            )

            if response.status_code == 200:
                result = response.json()
                print(f"DEBUG - Response facts: {result.get('result', {}).get('execution-results', {}).get('results', [])[:2]}")
                return self._extract_kie_batch_result(result, decisionInputs)
            else:
                print(f"Drools request error, status: {response.status_code}, response: {response.text}")
                return {"error": f"Drools error: {response.status_code}"}

        except requests.exceptions.RequestException as e:
            print(f"Error invoking Drools: {e}")
            return {"error": "An error occurred when invoking Drools Decision Service."}

    def _invoke_dmn(self, rulesetPath, decisionInputs):
        """Invoke using DMN (Decision Model and Notation)"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # DMN request format
        # Extract model namespace and name from environment or use defaults
        payload = {
            "model-namespace": os.getenv("DROOLS_DMN_NAMESPACE", "https://kiegroup.org/dmn/_underwriting"),
            "model-name": os.getenv("DROOLS_DMN_MODEL", "UnderwritingDecision"),
            "dmn-context": decisionInputs
        }

        try:
            # Resolve correct container endpoint
            base_url, path = self._resolve_container_endpoint(rulesetPath)
            url = base_url + path
            print(f"Invoking Drools (DMN) at: {url}")

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                auth=HTTPBasicAuth(self.username, self.password)
            )

            if response.status_code == 200:
                result = response.json()
                return self._extract_dmn_result(result)
            else:
                print(f"Drools DMN error, status: {response.status_code}, response: {response.text}")
                return {"error": f"Drools DMN error: {response.status_code}"}

        except requests.exceptions.RequestException as e:
            print(f"Error invoking Drools DMN: {e}")
            return {"error": "An error occurred when invoking Drools DMN Service."}

    def _invoke_rest(self, rulesetPath, decisionInputs):
        """Invoke using simple REST endpoint (custom wrapper)"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            # Resolve correct container endpoint
            base_url, path = self._resolve_container_endpoint(rulesetPath)
            url = base_url + path
            print(f"Invoking Drools (REST) at: {url}")

            response = requests.post(
                url,
                headers=headers,
                json=decisionInputs,
                auth=HTTPBasicAuth(self.username, self.password)
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Drools REST error, status: {response.status_code}")
                return {"error": f"Drools REST error: {response.status_code}"}

        except requests.exceptions.RequestException as e:
            print(f"Error invoking Drools REST: {e}")
            return {"error": "An error occurred when invoking Drools REST Service."}

    def _extract_kie_batch_result(self, droolsResponse, originalInput):
        """
        Extract decision result from Drools KIE Server batch execution response
        Looks for a Decision object inserted by rules, or returns modified input
        """
        try:
            # KIE Server response structure:
            # {
            #   "type": "SUCCESS",
            #   "msg": "...",
            #   "result": {
            #     "execution-results": {
            #       "results": [...]
            #     }
            #   }
            # }

            if "result" in droolsResponse:
                exec_results = droolsResponse["result"].get("execution-results", {})
                results = exec_results.get("results", [])

                decision_obj = None
                input_obj = None
                all_facts = []

                # Extract all results
                for result in results:
                    key = result.get("key", "")
                    value = result.get("value", {})

                    if key == "decision-input":
                        input_obj = value
                    elif key == "all-facts":
                        # This is a list of all objects in working memory
                        all_facts = value if isinstance(value, list) else []
                    elif isinstance(value, dict):
                        # Check if this looks like a Decision object
                        if "approved" in value or "decision" in value:
                            decision_obj = value

                # Look for Decision object in all-facts list
                if all_facts and not decision_obj:
                    for fact in all_facts:
                        if isinstance(fact, dict):
                            # Check if this is a Decision object directly
                            if "approved" in fact or "decision" in fact:
                                decision_obj = fact
                                break
                            # Check if this is a wrapped Decision object (class name as key)
                            for key, value in fact.items():
                                if "Decision" in key and isinstance(value, dict):
                                    if "approved" in value or "decision" in value:
                                        decision_obj = value
                                        break
                            if decision_obj:
                                break

                # Build response: merge input with decision
                if decision_obj:
                    # Merge decision fields into the response
                    response = originalInput.copy()
                    response.update(decision_obj)
                    print(f"✓ Found Decision object: {decision_obj}")
                    return response
                elif input_obj:
                    # Return modified input
                    print(f"✓ Returning modified input object")
                    return input_obj
                else:
                    # Return original input
                    print(f"⚠ No decision or modified input found, returning original")
                    return originalInput

            # Fallback: return original input
            return originalInput

        except Exception as e:
            print(f"Error extracting KIE batch result: {e}")
            return droolsResponse

    def _extract_dmn_result(self, droolsResponse):
        """
        Extract decision result from Drools DMN response
        """
        try:
            # DMN response structure:
            # {
            #   "type": "SUCCESS",
            #   "result": {
            #     "dmn-evaluation-result": {
            #       "result": {...},
            #       "messages": [...],
            #       "decision-results": [...]
            #     }
            #   }
            # }

            if "result" in droolsResponse:
                dmn_result = droolsResponse["result"].get("dmn-evaluation-result", {})
                return dmn_result.get("result", {})

            return droolsResponse

        except Exception as e:
            print(f"Error extracting DMN result: {e}")
            return droolsResponse

    def checkDroolsServer(self):
        """Verify connectivity to Drools KIE Server with retry logic"""
        import time

        max_retries = 10
        retry_delay = 2  # seconds

        print(f"Checking connection to Drools Server: {self.server_url}")

        for attempt in range(1, max_retries + 1):
            try:
                # KIE Server info endpoint
                response = requests.get(
                    f"{self.server_url}",
                    auth=HTTPBasicAuth(self.username, self.password),
                    headers={"Accept": "application/json"},
                    timeout=10
                )

                if response.status_code == 200:
                    server_info = response.json()
                    print(f"✓ Connected to Drools Server successfully - Version: {server_info.get('version', 'unknown')}")
                    return True
                else:
                    print(f"⚠ Attempt {attempt}/{max_retries}: Drools Server returned status {response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"⚠ Attempt {attempt}/{max_retries}: Unable to reach Drools Server - {e}")

            # Wait before retrying (except on last attempt)
            if attempt < max_retries:
                print(f"  Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # Exponential backoff: increase delay for next retry
                retry_delay = min(retry_delay * 1.5, 30)  # Cap at 30 seconds

        print(f"✗ Failed to connect to Drools Server after {max_retries} attempts")
        return False
