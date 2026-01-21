"""
Database Integration Updates for ContainerOrchestrator.py

This file contains the key methods that need to be updated in ContainerOrchestrator.py
to use PostgreSQL database instead of JSON file registry.

INSTRUCTIONS:
1. Update list_containers() method (around line 168)
2. Update create_drools_container() registration logic (around line 222-231)
3. Update delete_container() method (around line 399-438)
4. Update _get_next_available_port() method (around line 485-491)
5. Update _sync_container_statuses() method (around line 555-583)
6. Add new helper methods for database health checks
"""

# ===== Method 1: list_containers() =====
def list_containers_NEW(self) -> Dict:
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


# ===== Method 2: Update create_drools_container() registration =====
# Replace the registry update section (lines 222-231) with:
def register_container_in_db(self, container_id, bank_id, policy_type_id, container_name,
                              endpoint, port, document_hash=None):
    """
    Register container in database after successful creation

    This replaces the old JSON registry logic:
        self.registry[container_id] = {...}
        self._save_registry()
    """
    # Ensure bank and policy type exist
    self.db_service.create_bank(bank_id, bank_id.replace('_', ' ').title())
    self.db_service.create_policy_type(policy_type_id, policy_type_id.replace('_', ' ').title())

    # Register container
    container_data = {
        'container_id': container_id,
        'bank_id': bank_id,
        'policy_type_id': policy_type_id,
        'platform': self.platform,
        'container_name': container_name,
        'endpoint': endpoint,
        'port': port,
        'status': 'running',
        'health_status': 'healthy',
        'document_hash': document_hash
    }

    return self.db_service.register_container(container_data)


# ===== Method 3: delete_container() updates =====
def _delete_docker_container_NEW(self, container_id: str) -> Dict:
    """Delete a Docker container using database"""
    import docker

    try:
        client = docker.from_env()

        # Get container info from database
        container = self.db_service.get_container_by_id(container_id)
        if not container:
            return {
                "status": "error",
                "message": f"Container {container_id} not found in database"
            }

        container_name = container.container_name

        # Stop and remove Docker container
        try:
            docker_container = client.containers.get(container_name)
            docker_container.stop()
            docker_container.remove()
        except Exception as e:
            logger.warning(f"Error stopping Docker container: {e}")

        # Mark as inactive in database
        self.db_service.delete_container(container_id)

        return {
            "status": "success",
            "message": f"Docker container {container_name} deleted successfully"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to delete Docker container: {str(e)}"
        }


def _delete_k8s_pod_NEW(self, container_id: str) -> Dict:
    """Delete a Kubernetes pod using database"""
    from kubernetes import client, config

    try:
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()

        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()

        # Get container info from database
        container = self.db_service.get_container_by_id(container_id)
        if not container:
            return {
                "status": "error",
                "message": f"Container {container_id} not found in database"
            }

        deployment_name = container.container_name
        service_name = f"{deployment_name}-svc"
        namespace = self.k8s_namespace

        # Delete deployment and service
        try:
            apps_v1.delete_namespaced_deployment(name=deployment_name, namespace=namespace)
        except:
            pass

        try:
            v1.delete_namespaced_service(name=service_name, namespace=namespace)
        except:
            pass

        # Mark as inactive in database
        self.db_service.delete_container(container_id)

        return {
            "status": "success",
            "message": f"Kubernetes deployment {deployment_name} deleted successfully"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to delete Kubernetes pod: {str(e)}"
        }


# ===== Method 4: _get_next_available_port() using database =====
def _get_next_available_port_NEW(self) -> int:
    """Get next available port for Docker containers from database"""
    containers = self.db_service.list_containers(active_only=True)
    used_ports = [c.port for c in containers if c.port is not None]

    port = self.base_port
    while port in used_ports:
        port += 1
    return port


# ===== Method 5: _sync_container_statuses() using database =====
def _sync_container_statuses_NEW(self):
    """
    Sync database container statuses with actual container states
    """
    containers = self.db_service.list_containers(active_only=True)

    for container in containers:
        current_status = container.status

        # Check actual health
        if self.platform == 'docker':
            is_healthy = self._check_docker_container_health_db(container)
        elif self.platform == 'kubernetes':
            is_healthy = self._check_k8s_pod_health_db(container)
        else:
            continue

        # Update status if changed
        new_status = 'running' if is_healthy else 'stopped'
        new_health = 'healthy' if is_healthy else 'unhealthy'

        if current_status != new_status:
            self.db_service.update_container_status(
                container.container_id,
                status=new_status,
                health_status=new_health
            )
            logger.info(f"Container {container.container_id} status: {current_status} → {new_status}")


# ===== NEW Method 6: Database-aware health check methods =====
def _check_docker_container_health_db(self, container) -> bool:
    """
    Check if a Docker container is healthy using database container object

    Args:
        container: RuleContainer SQLAlchemy model instance

    Returns:
        True if container is running and healthy, False otherwise
    """
    import docker

    try:
        container_name = container.container_name
        if not container_name:
            return False

        logger.debug(f"Health check: Checking Docker container '{container_name}'...")

        # Check Docker container status
        client = docker.from_env()
        try:
            docker_container = client.containers.get(container_name)

            # Check if container is running
            if docker_container.status != 'running':
                logger.debug(f"Container status is '{docker_container.status}' (not running)")
                return False

            # HTTP endpoint health check
            endpoint = container.endpoint
            try:
                response = requests.get(
                    f"{endpoint}/kie-server/services/rest/server",
                    auth=('kieserver', 'kieserver1!'),
                    timeout=2
                )
                if response.status_code == 200:
                    logger.debug(f"Container is healthy (HTTP 200)")
                    return True
                else:
                    logger.debug(f"Container responded with HTTP {response.status_code}")
                    return False
            except Exception as http_err:
                logger.debug(f"Container not responsive ({type(http_err).__name__})")
                return False

        except docker.errors.NotFound:
            logger.debug(f"Container not found in Docker")
            return False

    except Exception as e:
        logger.error(f"Error checking Docker container health: {e}")
        return False


def _check_k8s_pod_health_db(self, container) -> bool:
    """
    Check if a Kubernetes pod is healthy using database container object

    Args:
        container: RuleContainer SQLAlchemy model instance

    Returns:
        True if pod is running and ready, False otherwise
    """
    from kubernetes import client, config

    try:
        deployment_name = container.container_name
        namespace = self.k8s_namespace

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
            return False

    except Exception as e:
        logger.error(f"Error checking Kubernetes pod health: {e}")
        return False


# ===== SEARCH & REPLACE INSTRUCTIONS =====
"""
In ContainerOrchestrator.py, make these updates:

1. ADD after __init__:
   - _migrate_legacy_registry() method (already added above)

2. REPLACE list_containers() method with list_containers_NEW()

3. In _create_docker_container(), REPLACE lines 222-231:
   OLD:
       self.registry[container_id] = {
           'platform': 'docker',
           ...
       }
       self._save_registry()

   NEW:
       # Extract bank_id and policy_type from container_id
       parts = container_id.split('-')
       bank_id = parts[0] if len(parts) >= 1 else 'unknown'
       policy_type_id = parts[1] if len(parts) >= 2 else 'unknown'

       self.register_container_in_db(
           container_id, bank_id, policy_type_id,
           container_name, endpoint, port
       )

4. Similarly update _create_k8s_pod() around lines 372-381

5. REPLACE _delete_docker_container() with _delete_docker_container_NEW()

6. REPLACE _delete_k8s_pod() with _delete_k8s_pod_NEW()

7. REPLACE _get_next_available_port() with _get_next_available_port_NEW()

8. REPLACE _sync_container_statuses() with _sync_container_statuses_NEW()

9. REPLACE _check_docker_container_health() with _check_docker_container_health_db()

10. REPLACE _check_k8s_pod_health() with _check_k8s_pod_health_db()

11. ADD new methods:
    - register_container_in_db()
    - _check_docker_container_health_db()
    - _check_k8s_pod_health_db()
"""
