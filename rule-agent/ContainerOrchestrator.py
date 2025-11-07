"""
Container Orchestrator - Manages separate Drools containers per rule set
Supports both Docker (development) and Kubernetes (production)
"""

import os
import json
import time
import requests
from typing import Dict, Optional, List
from datetime import datetime


class ContainerOrchestrator:
    """
    Orchestrates Drools containers - one container per rule set.

    Architecture:
    - Development: Uses Docker API to create/manage containers
    - Production: Uses Kubernetes API to create/manage pods
    """

    def __init__(self):
        self.platform = os.getenv('ORCHESTRATION_PLATFORM', 'docker')  # 'docker' or 'kubernetes'
        self.registry_file = '/data/container_registry.json'
        self.base_port = 8081  # Starting port for Drools containers

        # Docker settings
        self.docker_socket = os.getenv('DOCKER_HOST', 'unix:///var/run/docker.sock')
        self.docker_network = os.getenv('DOCKER_NETWORK', 'underwriting-net')

        # Kubernetes settings
        self.k8s_namespace = os.getenv('K8S_NAMESPACE', 'underwriting')
        self.k8s_service_type = os.getenv('K8S_SERVICE_TYPE', 'ClusterIP')

        # Load container registry
        self.registry = self._load_registry()

        print(f"Container Orchestrator initialized for platform: {self.platform}")

    def _load_registry(self) -> Dict:
        """Load the container registry from disk"""
        if os.path.exists(self.registry_file):
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_registry(self):
        """Save the container registry to disk"""
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)

    def get_container_endpoint(self, container_id: str) -> Optional[str]:
        """
        Get the endpoint URL for a container by its container_id (rule set name)

        Args:
            container_id: The KIE container ID (e.g., 'chase-insurance-underwriting-rules')

        Returns:
            Endpoint URL or None if not found
        """
        if container_id in self.registry:
            return self.registry[container_id]['endpoint']
        return None

    def list_containers(self) -> Dict:
        """List all managed Drools containers"""
        return {
            "platform": self.platform,
            "containers": self.registry
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
            client = docker.from_env()

            # Determine next available port
            port = self._get_next_available_port()

            # Container name
            container_name = f"drools-{container_id}"

            # Check if container already exists
            existing = self._check_existing_docker_container(client, container_name)
            if existing:
                # Check if already in registry
                if container_id in self.registry:
                    return {
                        "status": "exists",
                        "message": f"Container {container_name} already exists",
                        "endpoint": self.registry[container_id]['endpoint']
                    }
                else:
                    # Container exists but not in registry - return error to avoid conflicts
                    return {
                        "status": "error",
                        "message": f"Container {container_name} already exists but not in registry. Please delete it first: docker rm -f {container_name}"
                    }

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

            print(f"Creating Docker container: {container_name} on port {port}")

            # Create and start container
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
                },
                volumes={
                    volume_name: {'bind': '/opt/jboss/.m2/repository', 'mode': 'rw'}
                },
                healthcheck={
                    'test': ['CMD', 'curl', '-f', '-u', 'kieserver:kieserver1!',
                            'http://localhost:8080/kie-server/services/rest/server'],
                    'interval': 10000000000,  # 10s in nanoseconds
                    'timeout': 10000000000,
                    'retries': 30,
                    'start_period': 30000000000
                }
            )

            # Wait for container to be healthy
            endpoint = f"http://{container_name}:8080"
            self._wait_for_container_health(endpoint, container_name)

            # Register in registry
            self.registry[container_id] = {
                'platform': 'docker',
                'container_name': container_name,
                'docker_container_id': container.id,
                'endpoint': endpoint,
                'port': port,
                'created_at': datetime.now().isoformat(),
                'status': 'running'
            }
            self._save_registry()

            return {
                "status": "success",
                "message": f"Docker container {container_name} created successfully",
                "container_name": container_name,
                "endpoint": endpoint,
                "port": port
            }

        except Exception as e:
            print(f"Error creating Docker container: {str(e)}")
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
        """Get next available port for Docker containers"""
        used_ports = [info['port'] for info in self.registry.values() if 'port' in info]
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


# Singleton instance
_orchestrator = None

def get_orchestrator() -> ContainerOrchestrator:
    """Get the singleton orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ContainerOrchestrator()
    return _orchestrator
