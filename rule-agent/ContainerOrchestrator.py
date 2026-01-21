"""
Container Orchestrator - Manages separate Drools containers per rule set
Supports both Docker (development) and Kubernetes (production)
Uses PostgreSQL database for persistent container registry
"""

import os
import json
import time
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime

from DatabaseService import get_database_service

logger = logging.getLogger(__name__)


class ContainerOrchestrator:
    """
    Orchestrates Drools containers - one container per rule set.

    Architecture:
    - Development: Uses Docker API to create/manage containers
    - Production: Uses Kubernetes API to create/manage pods
    """

    def __init__(self):
        self.platform = os.getenv('ORCHESTRATION_PLATFORM', 'docker')  # 'docker' or 'kubernetes'
        self.registry_file = '/data/container_registry.json'  # Legacy JSON registry (for migration)
        self.base_port = 8081  # Starting port for Drools containers

        # Docker settings
        self.docker_socket = os.getenv('DOCKER_HOST', 'unix:///var/run/docker.sock')
        self.docker_network = os.getenv('DOCKER_NETWORK', 'underwriting-net')

        # Kubernetes settings
        self.k8s_namespace = os.getenv('K8S_NAMESPACE', 'underwriting')
        self.k8s_service_type = os.getenv('K8S_SERVICE_TYPE', 'ClusterIP')

        # Database service for persistent registry
        self.db_service = get_database_service()

        # Migrate legacy JSON registry to database if exists
        self._migrate_legacy_registry()

        logger.info(f"Container Orchestrator initialized for platform: {self.platform}")

    def _load_registry(self) -> Dict:
        """Load the container registry from disk (LEGACY - for migration only)"""
        if os.path.exists(self.registry_file):
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_registry(self):
        """DEPRECATED: Registry is now saved to database automatically"""
        # This method is kept for backward compatibility but does nothing
        pass

    def _migrate_legacy_registry(self):
        """Migrate legacy JSON registry to PostgreSQL database"""
        if not os.path.exists(self.registry_file):
            logger.info("No legacy registry file found, skipping migration")
            return

        try:
            legacy_registry = self._load_registry()
            if not legacy_registry:
                logger.info("Legacy registry is empty, skipping migration")
                return

            logger.info(f"Migrating {len(legacy_registry)} containers from JSON to database...")

            for container_id, container_info in legacy_registry.items():
                # Extract bank_id and policy_type_id from container_id
                # Format: {bank_id}-{policy_type}-underwriting-rules
                parts = container_id.split('-')
                if len(parts) >= 2:
                    bank_id = parts[0]
                    policy_type_id = parts[1]

                    # Ensure bank and policy type exist in database
                    self.db_service.create_bank(bank_id, bank_id.replace('_', ' ').title())
                    self.db_service.create_policy_type(policy_type_id, policy_type_id.replace('_', ' ').title())

                    # Check if container already exists in database
                    existing = self.db_service.get_container_by_id(container_id)
                    if existing:
                        logger.info(f"  Container {container_id} already exists in database, skipping")
                        continue

                    # Register container in database
                    container_data = {
                        'container_id': container_id,
                        'bank_id': bank_id,
                        'policy_type_id': policy_type_id,
                        'platform': container_info.get('platform', self.platform),
                        'container_name': container_info.get('container_name', container_id),
                        'endpoint': container_info['endpoint'],
                        'port': container_info.get('port'),
                        'status': container_info.get('status', 'running'),
                        'deployed_at': datetime.fromisoformat(container_info['created_at']) if 'created_at' in container_info else datetime.now()
                    }

                    self.db_service.register_container(container_data)
                    logger.info(f"  Migrated container: {container_id}")

            # Rename legacy file to prevent re-migration
            os.rename(self.registry_file, f"{self.registry_file}.migrated")
            logger.info("Legacy registry migration completed successfully")

        except Exception as e:
            logger.error(f"Error migrating legacy registry: {e}")
            # Don't fail if migration fails - continue with database

    def get_container_endpoint(self, container_id: str) -> Optional[str]:
        """
        Get the endpoint URL for a container by its container_id (rule set name)

        This method performs health checking to ensure the container is actually running
        before returning the endpoint. If the container is stopped, it returns None
        and updates the database status accordingly.

        Args:
            container_id: The KIE container ID (e.g., 'chase-insurance-underwriting-rules')

        Returns:
            Endpoint URL or None if not found or not healthy
        """
        # Get container from database
        container = self.db_service.get_container_by_id(container_id)
        if not container or not container['is_active']:
            return None

        endpoint = container['endpoint']

        # Health check: Verify container is actually running
        if self.platform == 'docker':
            is_healthy = self._check_docker_container_health(container_id)
        elif self.platform == 'kubernetes':
            is_healthy = self._check_k8s_pod_health(container_id)
        else:
            # Unknown platform, assume healthy
            is_healthy = True

        if is_healthy:
            # Update status to running if it was previously stopped
            if container['status'] != 'running':
                self.db_service.update_container_status(
                    container_id,
                    status='running',
                    health_status='healthy'
                )
            return endpoint
        else:
            # Container is not healthy, update database and return None
            logger.warning(f"Container {container_id} is not healthy (stopped or unreachable)")
            if container['status'] != 'stopped':
                self.db_service.update_container_status(
                    container_id,
                    status='unhealthy',
                    health_status='unhealthy'
                )
            return None

    def list_containers(self) -> Dict:
        """
        List all managed Drools containers with updated health status from database
        """
        # Get all active containers from database
        containers = self.db_service.list_containers(active_only=False)

        # Convert to legacy format for backward compatibility
        result = {}
        for container in containers:
            result[container.container_id] = {
                'platform': container.platform,
                'container_name': container.container_name,
                'endpoint': container.endpoint,
                'port': container.port,
                'status': container.status,
                'health_status': container.health_status,
                'bank_id': container.bank_id,
                'policy_type_id': container.policy_type_id,
                'deployed_at': container.deployed_at.isoformat() if container.deployed_at else None,
                'is_active': container.is_active
            }

        return {
            "platform": self.platform,
            "containers": result
        }

    def create_drools_container(self, container_id: str, ruleapp_path: str) -> Dict:
        """
        Create a new Drools container for a rule set

        Args:
            container_id: The KIE container ID (e.g., 'chase-insurance-underwriting-rules')
            ruleapp_path: Path to the ruleapp JAR file

        Returns:
            Dictionary with status and endpoint information
        """
        if self.platform == 'docker':
            return self._create_docker_container(container_id, ruleapp_path)
        elif self.platform == 'kubernetes':
            return self._create_k8s_pod(container_id, ruleapp_path)
        else:
            raise ValueError(f"Unknown platform: {self.platform}")

    def _create_docker_container(self, container_id: str, ruleapp_path: str) -> Dict:
        """Create a Docker container for the rule set"""
        import docker

        try:
            print(f"\n{'='*80}")
            print(f"DEBUG: Starting Docker container creation for container_id: {container_id}")
            print(f"DEBUG: Ruleapp path: {ruleapp_path}")
            print(f"{'='*80}")

            client = docker.from_env()
            print(f"DEBUG: Docker client initialized successfully")

            # Determine next available port
            port = self._get_next_available_port()
            print(f"DEBUG: Allocated port: {port}")

            # Container name
            container_name = f"drools-{container_id}"
            print(f"DEBUG: Container name: {container_name}")

            # Check if container already exists and delete it for clean deployment
            existing = self._check_existing_docker_container(client, container_name)
            if existing:
                print(f"DEBUG: Container {container_name} already exists - deleting for clean deployment...")
                try:
                    # Stop and remove the existing container
                    existing_container = client.containers.get(container_name)
                    existing_container.stop(timeout=10)
                    existing_container.remove()
                    print(f"✓ Deleted existing container {container_name}")

                    # Also remove from database to clean up state
                    db_container = self.db_service.get_container_by_id(container_id)
                    if db_container:
                        # Delete from database
                        with self.db_service.get_session() as session:
                            from DatabaseService import RuleContainer
                            session.query(RuleContainer).filter_by(container_id=container_id).delete()
                            session.commit()
                        print(f"✓ Removed container {container_id} from database")
                except Exception as delete_err:
                    print(f"⚠ Error deleting existing container: {delete_err}")
                    # Continue anyway - container might be in a bad state

            # Create volume for the ruleapp
            volume_name = f"drools-{container_id}-maven"

            # Verify network exists and get full network name
            network_obj = None
            try:
                # Try to find the network
                networks = client.networks.list(names=[self.docker_network])
                if networks:
                    network_obj = networks[0]
                    print(f"✓ Found network: {network_obj.name} (ID: {network_obj.id[:12]})")
                else:
                    # Try to get by name with project prefix
                    all_networks = client.networks.list()
                    for net in all_networks:
                        if net.name.endswith(self.docker_network) or net.name == self.docker_network:
                            network_obj = net
                            print(f"✓ Found network: {network_obj.name} (ID: {network_obj.id[:12]})")
                            break

                if not network_obj:
                    raise Exception(f"Network '{self.docker_network}' not found. Available networks: {[n.name for n in all_networks]}")

            except Exception as net_err:
                print(f"⚠ Network lookup error: {net_err}")
                raise

            print(f"DEBUG: Creating Docker container: {container_name} on port {port}")
            print(f"DEBUG: Network: {network_obj.name}")
            print(f"DEBUG: Volume: {volume_name}")
            print(f"DEBUG: Memory limit: 2GB, JVM heap: 512m-1024m")

            # Create and start container
            try:
                container = client.containers.run(
                    image="quay.io/kiegroup/kie-server-showcase:latest",
                    name=container_name,
                    hostname=container_name,
                    detach=True,
                    ports={'8080/tcp': port},
                    network=network_obj.name,  # Use the actual network name found
                    environment={
                        'KIE_SERVER_ID': container_id,
                        'KIE_SERVER_USER': 'kieserver',
                        'KIE_SERVER_PWD': 'kieserver1!',
                        'KIE_SERVER_LOCATION': f'http://{container_name}:8080/kie-server/services/rest/server',
                        'KIE_SERVER_CONTROLLER_USER': 'kieserver',
                        'KIE_SERVER_CONTROLLER_PWD': 'kieserver1!',
                        'JAVA_OPTS': '-Xms512m -Xmx1024m'  # Set JVM heap size
                    },
                    volumes={
                        volume_name: {'bind': '/opt/jboss/.m2/repository', 'mode': 'rw'}
                    },
                    mem_limit='2g',  # Container memory limit (2GB)
                    memswap_limit='2g',  # Disable swap
                    restart_policy={"Name": "unless-stopped"},  # Auto-restart container unless manually stopped
                    healthcheck={
                        'test': ['CMD', 'curl', '-f', '-u', 'kieserver:kieserver1!',
                                'http://localhost:8080/kie-server/services/rest/server'],
                        'interval': 10000000000,  # 10s in nanoseconds
                        'timeout': 10000000000,
                        'retries': 30,
                        'start_period': 30000000000
                    }
                )
                print(f"DEBUG: Container created successfully - ID: {container.id[:12]}")
                print(f"DEBUG: Container status: {container.status}")
            except Exception as create_err:
                print(f"DEBUG: FAILED to create container - Error: {str(create_err)}")
                import traceback
                traceback.print_exc()
                raise

            # Wait for container to be healthy
            endpoint = f"http://{container_name}:8080"
            print(f"DEBUG: Waiting for container health check at endpoint: {endpoint}")
            try:
                self._wait_for_container_health(endpoint, container_name)
                print(f"DEBUG: Container health check PASSED")
            except Exception as health_err:
                print(f"DEBUG: Container health check FAILED - Error: {str(health_err)}")
                # Get container logs for debugging
                try:
                    container.reload()
                    print(f"DEBUG: Container status after health check failure: {container.status}")
                    logs = container.logs(tail=50).decode('utf-8')
                    print(f"DEBUG: Container logs (last 50 lines):\n{logs}")
                except Exception as log_err:
                    print(f"DEBUG: Could not retrieve container logs: {str(log_err)}")
                raise

            # Extract bank_id and policy_type from container_id
            # Format: {bank_id}-{policy_type}-underwriting-rules
            parts = container_id.split('-')
            bank_id = parts[0] if len(parts) >= 1 else 'unknown'
            policy_type_id = parts[1] if len(parts) >= 2 else 'unknown'
            print(f"DEBUG: Extracted bank_id: {bank_id}, policy_type_id: {policy_type_id}")

            # Ensure bank and policy type exist in database
            print(f"DEBUG: Creating/verifying bank and policy type in database")
            self.db_service.create_bank(bank_id, bank_id.replace('_', ' ').title())
            self.db_service.create_policy_type(policy_type_id, policy_type_id.replace('_', ' ').title())
            print(f"DEBUG: Bank and policy type verified in database")

            # Register in database
            container_data = {
                'container_id': container_id,
                'bank_id': bank_id,
                'policy_type_id': policy_type_id,
                'platform': 'docker',
                'container_name': container_name,
                'endpoint': endpoint,
                'port': port,
                'status': 'running',
                'health_status': 'healthy'
            }
            print(f"DEBUG: Registering container in database with data: {container_data}")
            self.db_service.register_container(container_data)
            logger.info(f"Registered container {container_id} in database")
            print(f"DEBUG: Container registration in database SUCCESSFUL")

            print(f"{'='*80}")
            print(f"DEBUG: Docker container creation COMPLETED SUCCESSFULLY")
            print(f"DEBUG: Container: {container_name}, Endpoint: {endpoint}, Port: {port}")
            print(f"{'='*80}\n")

            return {
                "status": "success",
                "message": f"Docker container {container_name} created successfully",
                "container_name": container_name,
                "endpoint": endpoint,
                "port": port
            }

        except Exception as e:
            print(f"\n{'='*80}")
            print(f"DEBUG: FATAL ERROR in Docker container creation")
            print(f"DEBUG: Error type: {type(e).__name__}")
            print(f"DEBUG: Error message: {str(e)}")
            print(f"{'='*80}")
            import traceback
            traceback.print_exc()
            print(f"{'='*80}\n")
            return {
                "status": "error",
                "message": f"Failed to create Docker container: {str(e)}"
            }

    def _create_k8s_pod(self, container_id: str, ruleapp_path: str) -> Dict:
        """Create a Kubernetes pod and service for the rule set"""
        from kubernetes import client, config

        try:
            # Load K8s config (in-cluster or local kubeconfig)
            try:
                config.load_incluster_config()
            except:
                config.load_kube_config()

            v1 = client.CoreV1Api()
            apps_v1 = client.AppsV1Api()

            # Pod name
            pod_name = f"drools-{container_id}"
            service_name = f"drools-{container_id}-svc"

            # Check if deployment already exists
            existing = self._check_existing_k8s_deployment(apps_v1, pod_name)
            if existing:
                return {
                    "status": "exists",
                    "message": f"Deployment {pod_name} already exists",
                    "endpoint": self.registry[container_id]['endpoint']
                }

            print(f"Creating Kubernetes deployment: {pod_name}")

            # Create Deployment
            deployment = client.V1Deployment(
                metadata=client.V1ObjectMeta(
                    name=pod_name,
                    labels={'app': pod_name, 'component': 'drools'}
                ),
                spec=client.V1DeploymentSpec(
                    replicas=1,
                    selector=client.V1LabelSelector(
                        match_labels={'app': pod_name}
                    ),
                    template=client.V1PodTemplateSpec(
                        metadata=client.V1ObjectMeta(
                            labels={'app': pod_name, 'component': 'drools'}
                        ),
                        spec=client.V1PodSpec(
                            containers=[
                                client.V1Container(
                                    name='kie-server',
                                    image='quay.io/kiegroup/kie-server-showcase:latest',
                                    ports=[client.V1ContainerPort(container_port=8080)],
                                    env=[
                                        client.V1EnvVar(name='KIE_SERVER_ID', value=container_id),
                                        client.V1EnvVar(name='KIE_SERVER_USER', value='kieserver'),
                                        client.V1EnvVar(name='KIE_SERVER_PWD', value='kieserver1!'),
                                        client.V1EnvVar(name='KIE_SERVER_LOCATION',
                                                       value=f'http://{service_name}:8080/kie-server/services/rest/server'),
                                        client.V1EnvVar(name='KIE_SERVER_CONTROLLER_USER', value='kieserver'),
                                        client.V1EnvVar(name='KIE_SERVER_CONTROLLER_PWD', value='kieserver1!'),
                                    ],
                                    readiness_probe=client.V1Probe(
                                        http_get=client.V1HTTPGetAction(
                                            path='/kie-server/services/rest/server',
                                            port=8080,
                                            scheme='HTTP'
                                        ),
                                        initial_delay_seconds=30,
                                        period_seconds=10,
                                        timeout_seconds=10,
                                        failure_threshold=3
                                    ),
                                    liveness_probe=client.V1Probe(
                                        http_get=client.V1HTTPGetAction(
                                            path='/kie-server/services/rest/server',
                                            port=8080,
                                            scheme='HTTP'
                                        ),
                                        initial_delay_seconds=60,
                                        period_seconds=20,
                                        timeout_seconds=10,
                                        failure_threshold=3
                                    )
                                )
                            ]
                        )
                    )
                )
            )

            # Create the deployment
            apps_v1.create_namespaced_deployment(
                namespace=self.k8s_namespace,
                body=deployment
            )

            # Create Service
            service = client.V1Service(
                metadata=client.V1ObjectMeta(
                    name=service_name,
                    labels={'app': pod_name}
                ),
                spec=client.V1ServiceSpec(
                    type=self.k8s_service_type,
                    selector={'app': pod_name},
                    ports=[
                        client.V1ServicePort(
                            port=8080,
                            target_port=8080,
                            protocol='TCP'
                        )
                    ]
                )
            )

            # Create the service
            v1.create_namespaced_service(
                namespace=self.k8s_namespace,
                body=service
            )

            # Wait for pod to be ready
            endpoint = f"http://{service_name}.{self.k8s_namespace}.svc.cluster.local:8080"
            self._wait_for_k8s_pod_ready(apps_v1, pod_name)

            # Register in registry
            self.registry[container_id] = {
                'platform': 'kubernetes',
                'deployment_name': pod_name,
                'service_name': service_name,
                'namespace': self.k8s_namespace,
                'endpoint': endpoint,
                'created_at': datetime.now().isoformat(),
                'status': 'running'
            }
            self._save_registry()

            return {
                "status": "success",
                "message": f"Kubernetes deployment {pod_name} created successfully",
                "deployment_name": pod_name,
                "service_name": service_name,
                "endpoint": endpoint,
                "namespace": self.k8s_namespace
            }

        except Exception as e:
            print(f"Error creating Kubernetes pod: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to create Kubernetes pod: {str(e)}"
            }

    def delete_container(self, container_id: str) -> Dict:
        """Delete a Drools container"""
        if container_id not in self.registry:
            return {
                "status": "error",
                "message": f"Container {container_id} not found in registry"
            }

        if self.platform == 'docker':
            return self._delete_docker_container(container_id)
        elif self.platform == 'kubernetes':
            return self._delete_k8s_pod(container_id)

    def _delete_docker_container(self, container_id: str) -> Dict:
        """Delete a Docker container"""
        import docker

        try:
            client = docker.from_env()
            container_info = self.registry[container_id]
            container_name = container_info['container_name']

            container = client.containers.get(container_name)
            container.stop()
            container.remove()

            # Remove from registry
            del self.registry[container_id]
            self._save_registry()

            return {
                "status": "success",
                "message": f"Docker container {container_name} deleted successfully"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete Docker container: {str(e)}"
            }

    def _delete_k8s_pod(self, container_id: str) -> Dict:
        """Delete a Kubernetes pod and service"""
        from kubernetes import client, config

        try:
            try:
                config.load_incluster_config()
            except:
                config.load_kube_config()

            v1 = client.CoreV1Api()
            apps_v1 = client.AppsV1Api()

            container_info = self.registry[container_id]
            deployment_name = container_info['deployment_name']
            service_name = container_info['service_name']
            namespace = container_info['namespace']

            # Delete deployment
            apps_v1.delete_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )

            # Delete service
            v1.delete_namespaced_service(
                name=service_name,
                namespace=namespace
            )

            # Remove from registry
            del self.registry[container_id]
            self._save_registry()

            return {
                "status": "success",
                "message": f"Kubernetes deployment {deployment_name} deleted successfully"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete Kubernetes pod: {str(e)}"
            }

    def _get_next_available_port(self) -> int:
        """Get next available port for Docker containers from database"""
        containers = self.db_service.list_containers(active_only=True)
        used_ports = [c['port'] for c in containers if c.get('port') is not None]

        port = self.base_port
        while port in used_ports:
            port += 1
        return port

    def _check_existing_docker_container(self, client, container_name: str) -> bool:
        """Check if Docker container already exists"""
        try:
            container = client.containers.get(container_name)
            return True
        except:
            return False

    def _check_existing_k8s_deployment(self, apps_v1, deployment_name: str) -> bool:
        """Check if Kubernetes deployment already exists"""
        try:
            apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.k8s_namespace
            )
            return True
        except:
            return False

    def _wait_for_container_health(self, endpoint: str, container_name: str, timeout: int = 120):
        """Wait for Drools container to be healthy"""
        print(f"Waiting for container {container_name} to be healthy...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{endpoint}/kie-server/services/rest/server",
                    auth=('kieserver', 'kieserver1!'),
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"✓ Container {container_name} is healthy")
                    return True
            except:
                pass

            time.sleep(5)

        raise TimeoutError(f"Container {container_name} did not become healthy within {timeout}s")

    def _wait_for_k8s_pod_ready(self, apps_v1, deployment_name: str, timeout: int = 120):
        """Wait for Kubernetes pod to be ready"""
        print(f"Waiting for deployment {deployment_name} to be ready...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                deployment = apps_v1.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=self.k8s_namespace
                )
                if deployment.status.ready_replicas and deployment.status.ready_replicas > 0:
                    print(f"✓ Deployment {deployment_name} is ready")
                    return True
            except:
                pass

            time.sleep(5)

        raise TimeoutError(f"Deployment {deployment_name} did not become ready within {timeout}s")

    def _sync_container_statuses(self):
        """
        Sync registry container statuses with actual container states

        This updates the 'status' field in the registry to reflect reality
        """
        needs_save = False

        for container_id, container_info in self.registry.items():
            current_status = container_info.get('status', 'unknown')

            # Check actual health
            if self.platform == 'docker':
                is_healthy = self._check_docker_container_health(container_id)
            elif self.platform == 'kubernetes':
                is_healthy = self._check_k8s_pod_health(container_id)
            else:
                # Unknown platform, don't update
                continue

            # Update status if changed
            new_status = 'running' if is_healthy else 'stopped'
            if current_status != new_status:
                container_info['status'] = new_status
                needs_save = True
                print(f"Registry sync: {container_id} status changed from '{current_status}' to '{new_status}'")

        if needs_save:
            self._save_registry()

    def _check_docker_container_health(self, container_id: str) -> bool:
        """
        Check if a Docker container is healthy (running and responsive)

        Args:
            container_id: The KIE container ID

        Returns:
            True if container is running and healthy, False otherwise
        """
        import docker

        try:
            # Get container from database
            container_info = self.db_service.get_container_by_id(container_id)
            if not container_info:
                print(f"  Health check: {container_id} not in database")
                return False

            container_name = container_info.get('container_name')
            if not container_name:
                print(f"  Health check: {container_id} has no container_name")
                return False

            print(f"  Health check: Checking Docker container '{container_name}'...")

            # Check Docker container status
            client = docker.from_env()
            try:
                container = client.containers.get(container_name)

                # Check if container is running
                if container.status != 'running':
                    print(f"  Health check: Container status is '{container.status}' (not running)")
                    return False

                print(f"  Health check: Container is running, checking HTTP endpoint...")

                # Quick health check: try to reach the KIE server endpoint
                endpoint = container_info['endpoint']
                health_url = f"{endpoint}/kie-server/services/rest/server"
                print(f"  Health check: Testing endpoint {health_url}")
                try:
                    response = requests.get(
                        health_url,
                        auth=('kieserver', 'kieserver1!'),
                        timeout=2
                    )
                    print(f"  Health check: Got HTTP {response.status_code}")
                    if response.status_code == 200:
                        print(f"  Health check: ✓ Container is healthy (HTTP 200)")
                        return True
                    else:
                        print(f"  Health check: Container responded with HTTP {response.status_code}")
                        print(f"  Health check: Response body: {response.text[:200]}")
                        return False
                except Exception as http_err:
                    # Container is running but not responsive yet
                    print(f"  Health check: Container not responsive ({type(http_err).__name__}: {str(http_err)})")
                    return False

            except docker.errors.NotFound:
                # Container doesn't exist
                print(f"  Health check: Container not found in Docker")
                return False

        except Exception as e:
            print(f"  Health check: Error checking Docker container health: {e}")
            return False

    def deploy_kjar_to_container(self, container_id: str, jar_path: str,
                                  group_id: str, artifact_id: str, version: str) -> Dict:
        """
        Deploy a KJar to a dedicated Drools container

        This method:
        1. Copies the JAR and POM from the source to the dedicated container's Maven repository
        2. Deploys the KIE container within the dedicated Drools server

        Args:
            container_id: The KIE container ID (e.g., 'chase-insurance-underwriting-rules')
            jar_path: Path to the JAR file on the host or in the main drools container
            group_id: Maven group ID (e.g., 'com.underwriting')
            artifact_id: Maven artifact ID (e.g., 'underwriting-rules')
            version: Maven version (e.g., '20251111.005208')

        Returns:
            Dictionary with status and message
        """
        if self.platform == 'docker':
            return self._deploy_kjar_to_docker_container(container_id, jar_path, group_id, artifact_id, version)
        elif self.platform == 'kubernetes':
            return self._deploy_kjar_to_k8s_pod(container_id, jar_path, group_id, artifact_id, version)
        else:
            return {"status": "error", "message": f"Unknown platform: {self.platform}"}

    def _deploy_kjar_to_docker_container(self, container_id: str, jar_path: str,
                                          group_id: str, artifact_id: str, version: str) -> Dict:
        """Deploy KJar to a Docker container"""
        import docker
        import tarfile
        import io

        try:
            client = docker.from_env()

            # Get container info from database
            db_container = self.db_service.get_container_by_id(container_id)
            if not db_container:
                return {"status": "error", "message": f"Container {container_id} not found in registry"}

            container_name = db_container['container_name']

            # Check if container is running
            try:
                container = client.containers.get(container_name)
                if container.status != 'running':
                    return {"status": "error", "message": f"Container {container_name} is not running (status: {container.status})"}
            except docker.errors.NotFound:
                return {"status": "error", "message": f"Docker container {container_name} not found"}

            print(f"Deploying KJar to dedicated container {container_name}...")

            # Maven repository path structure: group_id/artifact_id/version/
            maven_path = f"{group_id.replace('.', '/')}/{artifact_id}/{version}"

            # Step 1: Copy JAR from main drools container to dedicated container
            # Get the parent directory containing the version folder
            parent_path = f"/opt/jboss/.m2/repository/{group_id.replace('.', '/')}/{artifact_id}"
            source_version_path = f"{parent_path}/{version}"

            try:
                # Use docker exec to create a tar archive and copy it
                main_drools = client.containers.get('drools')

                # Create tar in main drools container
                tar_result = main_drools.exec_run(
                    f"sh -c 'cd {parent_path} && tar -czf /tmp/kjar_copy.tar.gz {version}'",
                    user='root'
                )

                if tar_result.exit_code != 0:
                    return {
                        "status": "error",
                        "message": f"Failed to create tar in main drools container: {tar_result.output.decode()}"
                    }

                # Get the tar file
                bits, stat = main_drools.get_archive('/tmp/kjar_copy.tar.gz')
                tar_data = b''.join(bits)

                # Put it in the dedicated container
                container.put_archive('/tmp', tar_data)

                # Create parent directory in dedicated container if it doesn't exist
                mkdir_result = container.exec_run(
                    f"sh -c 'mkdir -p {parent_path}'",
                    user='root'
                )

                # Extract it in the dedicated container
                extract_result = container.exec_run(
                    f"sh -c 'cd {parent_path} && tar -xzf /tmp/kjar_copy.tar.gz && rm /tmp/kjar_copy.tar.gz'",
                    user='root'
                )

                if extract_result.exit_code != 0:
                    return {
                        "status": "error",
                        "message": f"Failed to extract tar in dedicated container: {extract_result.output.decode()}"
                    }

                # Clean up in main drools
                main_drools.exec_run("rm /tmp/kjar_copy.tar.gz", user='root')

                print(f"  ✓ Copied KJar files to {container_name}:{source_version_path}")

            except docker.errors.NotFound as e:
                return {
                    "status": "error",
                    "message": f"KJar not found in main drools container: {str(e)}"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error copying KJar: {str(e)}"
                }

            # Step 2: Deploy the KIE container within the dedicated Drools server
            endpoint = db_container['endpoint']
            deploy_url = f"{endpoint}/kie-server/services/rest/server/containers/{container_id}"

            payload = {
                "container-id": container_id,
                "release-id": {
                    "group-id": group_id,
                    "artifact-id": artifact_id,
                    "version": version
                }
            }

            print(f"  Deploying KIE container {container_id} in {container_name}...")

            # Check if container already exists in KIE server
            check_response = requests.get(
                deploy_url,
                auth=requests.auth.HTTPBasicAuth('admin', 'admin'),
                headers={'Accept': 'application/json'}
            )

            if check_response.status_code == 200:
                print(f"  Container {container_id} already exists in KIE server, disposing first...")
                requests.delete(
                    deploy_url,
                    auth=requests.auth.HTTPBasicAuth('admin', 'admin'),
                    headers={'Accept': 'application/json'}
                )

            # Deploy the container
            response = requests.put(
                deploy_url,
                auth=requests.auth.HTTPBasicAuth('admin', 'admin'),
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                json=payload
            )

            if response.status_code in [200, 201]:
                print(f"  ✓ KIE container {container_id} deployed successfully in {container_name}")
                return {
                    "status": "success",
                    "message": f"KJar deployed to {container_name} and KIE container started",
                    "container_name": container_name,
                    "endpoint": endpoint
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to deploy KIE container: {response.status_code} - {response.text}"
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deploying KJar to container: {str(e)}"
            }

    def _deploy_kjar_to_k8s_pod(self, container_id: str, jar_path: str,
                                 group_id: str, artifact_id: str, version: str) -> Dict:
        """Deploy KJar to a Kubernetes pod"""
        # For Kubernetes, we would use ConfigMaps or PersistentVolumes
        # This is a placeholder for future implementation
        return {
            "status": "error",
            "message": "Kubernetes KJar deployment not yet implemented"
        }

    def _check_k8s_pod_health(self, container_id: str) -> bool:
        """
        Check if a Kubernetes pod is healthy (running and ready)

        Args:
            container_id: The KIE container ID

        Returns:
            True if pod is running and ready, False otherwise
        """
        from kubernetes import client, config

        try:
            if container_id not in self.registry:
                return False

            container_info = self.registry[container_id]
            deployment_name = container_info.get('deployment_name')
            namespace = container_info.get('namespace', self.k8s_namespace)

            if not deployment_name:
                return False

            # Load K8s config
            try:
                config.load_incluster_config()
            except:
                config.load_kube_config()

            apps_v1 = client.AppsV1Api()

            # Check deployment status
            try:
                deployment = apps_v1.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace
                )

                # Check if at least one replica is ready
                return deployment.status.ready_replicas and deployment.status.ready_replicas > 0

            except client.exceptions.ApiException:
                # Deployment doesn't exist
                return False

        except Exception as e:
            print(f"Error checking Kubernetes pod health: {e}")
            return False


# Singleton instance
_orchestrator = None

def get_orchestrator() -> ContainerOrchestrator:
    """Get the singleton orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ContainerOrchestrator()
    return _orchestrator
