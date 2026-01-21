# PostgreSQL Integration Guide

## Overview

The underwriting AI system has been upgraded to use PostgreSQL for persistent storage of rule container deployments, banks, and policy types. This replaces the previous JSON file-based registry and enables customer applications to query and use deployed rule engines dynamically.

---

## What's New

### 1. **PostgreSQL Database**
- Persistent storage for container registry
- Tracks banks, policy types, and deployed rule containers
- Automatic audit trail and deployment history
- Request tracking for analytics

### 2. **Customer-Facing API Endpoints**
- Service discovery: Find available banks and policies
- Policy evaluation: Execute rules without knowing container details
- Deployment management: Query and manage rule deployments

### 3. **Automatic Migration**
- Legacy JSON registry automatically migrates to PostgreSQL
- No manual data migration required

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Customer Application                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTP/REST
                     ↓
┌─────────────────────────────────────────────────────────────┐
│               Backend API (ChatService.py)                   │
│  ┌────────────────────────────────────────────────────┐     │
│  │  New API Endpoints:                                 │     │
│  │  - GET  /api/v1/banks                              │     │
│  │  - GET  /api/v1/banks/{id}/policies                │     │
│  │  - GET  /api/v1/policies?bank_id=&policy_type=     │     │
│  │  - POST /api/v1/evaluate-policy                    │     │
│  │  - GET  /api/v1/deployments                        │     │
│  │  - GET  /api/v1/discovery                          │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│           DatabaseService (SQLAlchemy ORM)                   │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Models:                                            │     │
│  │  - Bank                                             │     │
│  │  - PolicyType                                       │     │
│  │  - RuleContainer                                    │     │
│  │  - RuleRequest (analytics)                          │     │
│  │  - ContainerDeploymentHistory (audit)              │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL Database                             │
│  Tables:                                                     │
│  - banks                                                     │
│  - policy_types                                              │
│  - rule_containers (with health status)                      │
│  - rule_requests (request logs)                              │
│  - container_deployment_history (audit trail)                │
└─────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### 1. Start the System

```bash
# Build and start all services
docker-compose build
docker-compose up
```

This will start:
- **PostgreSQL** on port 5432
- **Drools KIE Server** on port 8080
- **Backend API** on port 9000

### 2. Verify Database Connection

```bash
curl http://localhost:9000/rule-agent/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "drools": "connected"
}
```

### 3. Check Available Services

```bash
curl http://localhost:9000/rule-agent/api/v1/discovery
```

Response shows all banks with their available policy types.

---

## Customer Application Integration

### Use Case: Insurance Application Underwriting

#### Step 1: Discover Available Banks

```bash
GET /rule-agent/api/v1/banks
```

**Response:**
```json
{
  "status": "success",
  "banks": [
    {
      "bank_id": "chase",
      "bank_name": "Chase Bank",
      "description": "Chase Manhattan Bank underwriting policies"
    },
    {
      "bank_id": "bofa",
      "bank_name": "Bank of America",
      "description": "Bank of America lending policies"
    }
  ]
}
```

#### Step 2: Check Available Policies for a Bank

```bash
GET /rule-agent/api/v1/banks/chase/policies
```

**Response:**
```json
{
  "status": "success",
  "bank_id": "chase",
  "policies": [
    {
      "policy_type_id": "insurance",
      "policy_name": "Insurance Underwriting",
      "description": "Life and health insurance underwriting policies",
      "category": "insurance"
    },
    {
      "policy_type_id": "loan",
      "policy_name": "Loan Underwriting",
      "description": "Personal and business loan underwriting rules",
      "category": "loan"
    }
  ]
}
```

#### Step 3: Verify Rules Are Deployed

```bash
GET /rule-agent/api/v1/policies?bank_id=chase&policy_type=insurance
```

**Response:**
```json
{
  "status": "success",
  "container": {
    "container_id": "chase-insurance-underwriting-rules",
    "bank_id": "chase",
    "policy_type_id": "insurance",
    "endpoint": "http://drools-chase-insurance:8080",
    "status": "running",
    "health_status": "healthy",
    "deployed_at": "2025-11-10T10:30:00"
  }
}
```

#### Step 4: Evaluate an Application

```bash
POST /rule-agent/api/v1/evaluate-policy
Content-Type: application/json

{
  "bank_id": "chase",
  "policy_type": "insurance",
  "applicant": {
    "age": 35,
    "income": 75000,
    "credit_score": 720,
    "medical_history": "good"
  },
  "policy": {
    "coverage_amount": 500000,
    "term_years": 20
  }
}
```

**Response:**
```json
{
  "status": "success",
  "bank_id": "chase",
  "policy_type": "insurance",
  "container_id": "chase-insurance-underwriting-rules",
  "decision": {
    "approved": true,
    "premium_rate": 0.85,
    "reasons": ["Good credit score", "Favorable medical history"],
    "conditions": ["Annual health checkup required"]
  },
  "execution_time_ms": 45
}
```

---

## API Reference

### Service Discovery

#### `GET /api/v1/banks`
List all available banks.

#### `GET /api/v1/banks/{bank_id}/policies`
List policies available for a specific bank.

#### `GET /api/v1/discovery`
Get all banks with their available policies in one call.

### Policy Execution

#### `POST /api/v1/evaluate-policy`
Evaluate an application using deployed rules.

**Required fields:**
- `bank_id`: Bank identifier
- `policy_type`: Policy type identifier
- `applicant`: Applicant data object
- `policy` (optional): Policy-specific data

**Returns:**
- `decision`: Rule engine decision
- `execution_time_ms`: Performance metric
- Logs request to database for analytics

### Admin Endpoints

#### `GET /api/v1/deployments`
List all rule deployments.

**Query parameters:**
- `bank_id`: Filter by bank
- `policy_type`: Filter by policy type
- `status`: Filter by status (deploying, running, stopped, failed)
- `active_only`: Show only active deployments (true/false)

#### `GET /api/v1/deployments/{id}`
Get detailed information about a specific deployment including:
- Container details
- S3 artifact URLs
- Request statistics
- Health status

#### `GET /api/v1/health`
System health check.

---

## Database Schema

### Core Tables

#### `banks`
- `bank_id` (PK): Unique bank identifier
- `bank_name`: Display name
- `description`: Bank description
- `is_active`: Active status
- `created_at`, `updated_at`: Timestamps

#### `policy_types`
- `policy_type_id` (PK): Unique policy type identifier
- `policy_name`: Display name
- `description`: Policy description
- `category`: Policy category (insurance, loan, credit, etc.)
- `is_active`: Active status

#### `rule_containers`
- `id` (PK): Auto-increment ID
- `container_id` (Unique): KIE container ID (e.g., "chase-insurance-underwriting-rules")
- `bank_id` (FK): Reference to banks table
- `policy_type_id` (FK): Reference to policy_types table
- `platform`: Deployment platform (docker, kubernetes, local)
- `container_name`: Docker/K8s container name
- `endpoint`: HTTP endpoint URL
- `port`: Port number
- `status`: Container status (deploying, running, stopped, failed, unhealthy)
- `health_status`: Health check result (healthy, unhealthy, unknown)
- `document_hash`: SHA-256 of source policy document
- `s3_policy_url`, `s3_jar_url`, `s3_drl_url`, `s3_excel_url`: S3 artifact URLs
- `version`: Rule version number
- `is_active`: Only one active container per bank+policy
- `deployed_at`, `updated_at`, `stopped_at`: Timestamps

**Constraint:** Only one active container per `bank_id` + `policy_type_id` combination.

#### `rule_requests`
Analytics table for tracking all rule evaluation requests:
- Request/response payloads (JSONB)
- Execution time
- Success/error status
- Timestamp

#### `container_deployment_history`
Audit trail for all container lifecycle events:
- Deployment, updates, stops, failures
- Version tracking
- Change descriptions

### Views

#### `active_containers`
Convenient view joining containers with bank and policy type details.

#### `container_stats`
Aggregated statistics: total requests, success rate, avg execution time.

---

## Deployment Workflow

### Automatic Registration

When you deploy rules using the underwriting workflow:

1. **Policy Processing** (`/process_policy_from_s3`)
   - Upload policy PDF to S3
   - System extracts rules using LLM + Textract
   - Generates DRL files and builds KJar

2. **Container Creation** (`ContainerOrchestrator`)
   - Creates dedicated Drools container
   - Registers container in PostgreSQL
   - Sets status to "deploying"

3. **Deployment** (`DroolsDeploymentService`)
   - Deploys rules to container
   - Updates status to "running"
   - Performs health checks

4. **S3 Upload** (`UnderwritingWorkflow`)
   - Uploads JAR, DRL, Excel to S3
   - Updates database with S3 URLs

5. **Ready for Use**
   - Container is now discoverable via API
   - Customer applications can use `/api/v1/evaluate-policy`

### Example: Deploy Rules for Chase Insurance

```bash
POST /rule-agent/process_policy_from_s3
Content-Type: application/json

{
  "s3_url": "s3://my-bucket/policies/chase-life-insurance-policy.pdf",
  "bank_id": "chase",
  "policy_type": "insurance",
  "use_cache": true
}
```

**Result:**
- Container `chase-insurance-underwriting-rules` created
- Rules extracted and deployed
- Artifacts uploaded to S3
- Database updated with all metadata
- Ready for customer applications to use

---

## Monitoring & Analytics

### Request Tracking

All API calls to `/api/v1/evaluate-policy` are logged to the `rule_requests` table:

```sql
SELECT
    bank_id,
    policy_type_id,
    COUNT(*) as total_requests,
    AVG(execution_time_ms) as avg_time,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful
FROM rule_requests
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY bank_id, policy_type_id;
```

### Container Health

Check container health status:

```sql
SELECT
    container_id,
    bank_id,
    policy_type_id,
    status,
    health_status,
    last_health_check
FROM rule_containers
WHERE is_active = true;
```

### Deployment Audit Trail

View deployment history:

```sql
SELECT
    container_id,
    action,
    version,
    created_at
FROM container_deployment_history
WHERE container_id = 'chase-insurance-underwriting-rules'
ORDER BY created_at DESC;
```

---

## Migration from JSON Registry

The system automatically migrates legacy JSON registry on first startup:

1. Reads `/data/container_registry.json`
2. Extracts `bank_id` and `policy_type` from `container_id`
3. Creates database entries
4. Renames file to `container_registry.json.migrated`

No manual intervention required!

---

## Environment Variables

### Database Configuration

Add to `llm.env` or set in `docker-compose.yml`:

```bash
DATABASE_URL=postgresql://underwriting_user:underwriting_pass@postgres:5432/underwriting_db
DB_HOST=postgres
DB_PORT=5432
DB_NAME=underwriting_db
DB_USER=underwriting_user
DB_PASSWORD=underwriting_pass
```

### Container Orchestration

```bash
USE_CONTAINER_ORCHESTRATOR=true
ORCHESTRATION_PLATFORM=docker  # or kubernetes
DOCKER_NETWORK=underwriting-net
```

---

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Test connection manually
docker exec -it postgres psql -U underwriting_user -d underwriting_db
```

### Container Not Found

If `/api/v1/policies` returns 404:

1. Check if rules were deployed:
   ```bash
   GET /rule-agent/drools_containers
   ```

2. Verify database entry:
   ```bash
   docker exec -it postgres psql -U underwriting_user -d underwriting_db \
     -c "SELECT * FROM rule_containers WHERE container_id = 'your-container-id';"
   ```

3. Re-deploy rules if necessary

### Health Check Failures

If container status is "unhealthy":

1. Check Drools container logs:
   ```bash
   docker logs drools-chase-insurance-underwriting-rules
   ```

2. Verify endpoint is reachable:
   ```bash
   curl -u kieserver:kieserver1! \
     http://drools-chase-insurance-underwriting-rules:8080/kie-server/services/rest/server
   ```

3. Restart container via orchestrator

---

## Security Considerations

### Database Credentials
- Change default passwords in production
- Use strong passwords
- Consider AWS RDS or managed PostgreSQL for production

### API Authentication
- Add authentication middleware (JWT, OAuth2)
- Rate limiting for customer-facing endpoints
- API keys for service-to-service communication

### Network Security
- Use HTTPS for all API endpoints
- Restrict database access to backend only
- Implement network policies in Kubernetes

---

## Performance Optimization

### Database Indexing
The schema includes optimized indexes for common queries:
- `(bank_id, policy_type_id)` for container lookups
- `status` for filtering active containers
- `created_at` for time-based queries

### Connection Pooling
SQLAlchemy uses connection pooling by default:
```python
engine = create_engine(database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
```

### Caching
- Rule results are cached using `RuleCacheService`
- Container endpoints are cached during active requests
- Consider Redis for distributed caching

---

## Production Deployment Checklist

- [ ] Change database passwords
- [ ] Set up managed PostgreSQL (AWS RDS, Azure Database, etc.)
- [ ] Configure SSL/TLS for database connections
- [ ] Add API authentication (JWT/OAuth2)
- [ ] Set up monitoring (Prometheus, DataDog, etc.)
- [ ] Configure log aggregation (ELK, Splunk, etc.)
- [ ] Implement rate limiting
- [ ] Set up automated backups
- [ ] Create disaster recovery plan
- [ ] Document SLAs for customer applications
- [ ] Set up alerting for health check failures

---

## Example Client Code

### Python Client

```python
import requests

BASE_URL = "http://localhost:9000/rule-agent"

class UnderwritingClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url

    def get_banks(self):
        """Get all available banks"""
        response = requests.get(f"{self.base_url}/api/v1/banks")
        return response.json()

    def get_policies(self, bank_id):
        """Get policies for a bank"""
        response = requests.get(f"{self.base_url}/api/v1/banks/{bank_id}/policies")
        return response.json()

    def evaluate_application(self, bank_id, policy_type, applicant, policy=None):
        """Evaluate an application"""
        payload = {
            "bank_id": bank_id,
            "policy_type": policy_type,
            "applicant": applicant,
            "policy": policy or {}
        }
        response = requests.post(
            f"{self.base_url}/api/v1/evaluate-policy",
            json=payload
        )
        return response.json()

# Usage
client = UnderwritingClient()

# Discover services
banks = client.get_banks()
print(f"Available banks: {banks}")

# Evaluate application
result = client.evaluate_application(
    bank_id="chase",
    policy_type="insurance",
    applicant={
        "age": 35,
        "income": 75000,
        "credit_score": 720
    }
)
print(f"Decision: {result['decision']}")
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

class UnderwritingClient {
  constructor(baseUrl = 'http://localhost:9000/rule-agent') {
    this.baseUrl = baseUrl;
  }

  async getBanks() {
    const response = await axios.get(`${this.baseUrl}/api/v1/banks`);
    return response.data;
  }

  async getPolicies(bankId) {
    const response = await axios.get(`${this.baseUrl}/api/v1/banks/${bankId}/policies`);
    return response.data;
  }

  async evaluateApplication(bankId, policyType, applicant, policy = {}) {
    const response = await axios.post(`${this.baseUrl}/api/v1/evaluate-policy`, {
      bank_id: bankId,
      policy_type: policyType,
      applicant,
      policy
    });
    return response.data;
  }
}

// Usage
const client = new UnderwritingClient();

(async () => {
  const banks = await client.getBanks();
  console.log('Available banks:', banks);

  const result = await client.evaluateApplication(
    'chase',
    'insurance',
    { age: 35, income: 75000, credit_score: 720 }
  );
  console.log('Decision:', result.decision);
})();
```

---

## Support & Documentation

- **API Documentation**: http://localhost:9000/rule-agent/docs (Swagger UI)
- **Database Schema**: See [rule-agent/db/init.sql](rule-agent/db/init.sql)
- **Code Reference**:
  - [DatabaseService.py](rule-agent/DatabaseService.py) - ORM models and CRUD operations
  - [ChatService.py](rule-agent/ChatService.py) - API endpoints
  - [ContainerOrchestrator.py](rule-agent/ContainerOrchestrator.py) - Container management

---

## Changelog

### v2.0.0 - PostgreSQL Integration (2025-11-10)

**Added:**
- PostgreSQL database for persistent storage
- Customer-facing API endpoints
- Request tracking and analytics
- Deployment audit trail
- Automatic JSON registry migration
- Health check endpoints
- Service discovery API

**Changed:**
- Container registry moved from JSON file to PostgreSQL
- Container orchestrator now uses database
- Underwriting workflow registers containers in database

**Improved:**
- Multi-tenant isolation with proper database constraints
- Better error handling and logging
- Performance metrics tracking
- Container health monitoring

---

## License

Copyright 2024 IBM Corp. Licensed under the Apache License, Version 2.0.
