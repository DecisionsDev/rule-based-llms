# API Testing Guide

Complete guide for testing the Underwriting Rule Generation APIs.

## 📚 Interactive Documentation

### Swagger UI (Recommended)

**Access the interactive API documentation:**

```
http://localhost:9000/rule-agent/docs
```

Features:
- ✅ Try out all APIs directly in your browser
- ✅ See request/response examples
- ✅ Understand all parameters
- ✅ View schema definitions
- ✅ Test multi-tenant scenarios

### Raw OpenAPI Spec

Download the OpenAPI 3.0 specification:

```
http://localhost:9000/rule-agent/swagger.yaml
```

---

## 🚀 Quick Start Examples

### 1. Upload Policy Document (Local File)

**Using cURL:**

```bash
# Basic upload - insurance policy
curl -X POST http://localhost:9000/rule-agent/upload_policy \
  -F "file=@path/to/insurance_policy.pdf" \
  -F "policy_type=insurance" \
  -F "bank_id=chase"

# Loan policy with template queries
curl -X POST http://localhost:9000/rule-agent/upload_policy \
  -F "file=@path/to/loan_policy.pdf" \
  -F "policy_type=loan" \
  -F "bank_id=bofa" \
  -F "use_template_queries=true"
```

**Using Python:**

```python
import requests

url = "http://localhost:9000/rule-agent/upload_policy"

files = {
    'file': open('insurance_policy.pdf', 'rb')
}

data = {
    'policy_type': 'insurance',
    'bank_id': 'chase'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**Using Postman:**

1. Method: `POST`
2. URL: `http://localhost:9000/rule-agent/upload_policy`
3. Body: `form-data`
   - Key: `file` (type: File) → Select PDF
   - Key: `policy_type` (type: Text) → `insurance`
   - Key: `bank_id` (type: Text) → `chase`
4. Send

---

### 2. Process Policy from S3

**Using cURL:**

```bash
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "https://uw-data-extraction.s3.us-east-1.amazonaws.com/policies/chase_insurance.pdf",
    "policy_type": "insurance",
    "bank_id": "chase"
  }'
```

**Using Python:**

```python
import requests

url = "http://localhost:9000/rule-agent/process_policy_from_s3"

payload = {
    "s3_url": "https://uw-data-extraction.s3.us-east-1.amazonaws.com/policies/chase_insurance.pdf",
    "policy_type": "insurance",
    "bank_id": "chase"
}

response = requests.post(url, json=payload)
print(response.json())
```

**Using Postman:**

1. Method: `POST`
2. URL: `http://localhost:9000/rule-agent/process_policy_from_s3`
3. Headers: `Content-Type: application/json`
4. Body: `raw` (JSON)
   ```json
   {
     "s3_url": "https://uw-data-extraction.s3.us-east-1.amazonaws.com/policies/chase_insurance.pdf",
     "policy_type": "insurance",
     "bank_id": "chase"
   }
   ```
5. Send

---

### 3. List Drools Containers

**Using cURL:**

```bash
curl -X GET http://localhost:9000/rule-agent/drools_containers
```

**Expected Response:**

```json
{
  "result": {
    "kie-containers": {
      "kie-container": [
        {
          "container-id": "chase-insurance-underwriting-rules",
          "status": "STARTED",
          "release-id": {
            "group-id": "com.underwriting",
            "artifact-id": "underwriting-rules",
            "version": "20250104.143000"
          }
        },
        {
          "container-id": "bofa-loan-underwriting-rules",
          "status": "STARTED",
          "release-id": {
            "group-id": "com.underwriting",
            "artifact-id": "underwriting-rules",
            "version": "20250104.150000"
          }
        }
      ]
    }
  }
}
```

---

### 4. Get Container Status

**Using cURL:**

```bash
curl -X GET "http://localhost:9000/rule-agent/drools_container_status?container_id=chase-insurance-underwriting-rules"
```

---

## 🏦 Multi-Tenant Testing Scenarios

### Scenario 1: Multiple Banks, Same Policy Type

Test complete isolation between banks for the same policy type.

```bash
# Chase Insurance
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "https://bucket.s3.amazonaws.com/chase/insurance.pdf",
    "policy_type": "insurance",
    "bank_id": "chase"
  }'
# → Container: chase-insurance-underwriting-rules

# Bank of America Insurance (separate container!)
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "https://bucket.s3.amazonaws.com/bofa/insurance.pdf",
    "policy_type": "insurance",
    "bank_id": "bofa"
  }'
# → Container: bofa-insurance-underwriting-rules
```

**Verify:**
```bash
curl -X GET http://localhost:9000/rule-agent/drools_containers | jq
```

You should see both containers running independently.

---

### Scenario 2: Same Bank, Multiple Policy Types

Test isolation between policy types for the same bank.

```bash
# Chase Insurance
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "https://bucket.s3.amazonaws.com/chase/insurance.pdf",
    "policy_type": "insurance",
    "bank_id": "chase"
  }'

# Chase Loan (different policy type)
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "https://bucket.s3.amazonaws.com/chase/loan.pdf",
    "policy_type": "loan",
    "bank_id": "chase"
  }'

# Chase Auto (another policy type)
curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "https://bucket.s3.amazonaws.com/chase/auto.pdf",
    "policy_type": "auto",
    "bank_id": "chase"
  }'
```

**Result:** Three separate containers for Chase:
- `chase-insurance-underwriting-rules`
- `chase-loan-underwriting-rules`
- `chase-auto-underwriting-rules`

---

### Scenario 3: Matrix Deployment (Multiple Banks × Multiple Policies)

Deploy a complete matrix:

```bash
# Chase
for policy in insurance loan auto; do
  curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
    -H "Content-Type: application/json" \
    -d "{\"s3_url\": \"https://bucket.s3.amazonaws.com/chase/${policy}.pdf\", \"policy_type\": \"${policy}\", \"bank_id\": \"chase\"}"
done

# Bank of America
for policy in insurance loan auto; do
  curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
    -H "Content-Type: application/json" \
    -d "{\"s3_url\": \"https://bucket.s3.amazonaws.com/bofa/${policy}.pdf\", \"policy_type\": \"${policy}\", \"bank_id\": \"bofa\"}"
done

# Wells Fargo
for policy in insurance loan auto; do
  curl -X POST http://localhost:9000/rule-agent/process_policy_from_s3 \
    -H "Content-Type: application/json" \
    -d "{\"s3_url\": \"https://bucket.s3.amazonaws.com/wellsfargo/${policy}.pdf\", \"policy_type\": \"${policy}\", \"bank_id\": \"wells-fargo\"}"
done
```

**Result:** 9 isolated containers (3 banks × 3 policy types)

---

## 📋 Complete API Reference

### Upload Policy

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `file` | File | Yes | PDF policy document | `insurance.pdf` |
| `policy_type` | String | No | Policy type | `insurance`, `loan`, `auto` |
| `bank_id` | String | Recommended | Bank identifier | `chase`, `bofa` |
| `container_id` | String | No | Custom container ID | `my-custom-container` |
| `use_template_queries` | Boolean | No | Use template queries | `true`, `false` |

**Response Fields:**
- `status`: `completed`, `failed`, `in_progress`
- `container_id`: Generated or custom container ID
- `jar_s3_url`: S3 URL of generated JAR file
- `drl_s3_url`: S3 URL of generated DRL file
- `steps`: Detailed step-by-step results

---

### Process from S3

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `s3_url` | String | Yes | Full S3 URL to PDF |
| `policy_type` | String | No | Policy type |
| `bank_id` | String | Recommended | Bank identifier |
| `container_id` | String | No | Custom container ID |
| `use_template_queries` | Boolean | No | Use templates |

---

## 🔍 Testing Checklist

### Basic Functionality
- [ ] Upload local PDF file
- [ ] Process PDF from S3
- [ ] Generate rules without Textract (mock mode)
- [ ] Generate rules with Textract
- [ ] Deploy to Drools KIE Server
- [ ] Upload JAR/DRL to S3
- [ ] Verify temp file cleanup

### Multi-Tenant Features
- [ ] Same policy type, different banks (isolation)
- [ ] Same bank, different policy types (isolation)
- [ ] Auto-generated container IDs correct
- [ ] S3 organization by bank and policy type
- [ ] Manual container ID override works

### Edge Cases
- [ ] No bank_id provided (backwards compatibility)
- [ ] Spaces in policy type (normalization)
- [ ] Spaces in bank_id (normalization)
- [ ] Duplicate uploads (container disposal and recreation)
- [ ] Invalid S3 URL handling
- [ ] Missing file upload handling

### Drools Integration
- [ ] List all containers
- [ ] Get specific container status
- [ ] Container deployment succeeds
- [ ] Rules execute correctly in KIE Server

---

## 🛠️ Tools & Utilities

### Postman Collection

Import this collection for quick testing:

```json
{
  "info": {
    "name": "Underwriting API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Upload Policy",
      "request": {
        "method": "POST",
        "url": "http://localhost:9000/rule-agent/upload_policy",
        "body": {
          "mode": "formdata",
          "formdata": [
            {"key": "file", "type": "file"},
            {"key": "policy_type", "value": "insurance"},
            {"key": "bank_id", "value": "chase"}
          ]
        }
      }
    },
    {
      "name": "Process from S3",
      "request": {
        "method": "POST",
        "url": "http://localhost:9000/rule-agent/process_policy_from_s3",
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "body": {
          "mode": "raw",
          "raw": "{\"s3_url\": \"https://bucket.s3.amazonaws.com/policy.pdf\", \"policy_type\": \"insurance\", \"bank_id\": \"chase\"}"
        }
      }
    }
  ]
}
```

### Python Test Script

```python
#!/usr/bin/env python3
"""
Comprehensive API test script
"""
import requests
import json

BASE_URL = "http://localhost:9000/rule-agent"

def test_s3_processing():
    """Test S3 policy processing"""
    url = f"{BASE_URL}/process_policy_from_s3"

    payload = {
        "s3_url": "https://uw-data-extraction.s3.us-east-1.amazonaws.com/policies/test.pdf",
        "policy_type": "insurance",
        "bank_id": "chase"
    }

    response = requests.post(url, json=payload)
    result = response.json()

    print(f"Status: {result.get('status')}")
    print(f"Container ID: {result.get('container_id')}")
    print(f"JAR S3 URL: {result.get('jar_s3_url')}")
    print(f"DRL S3 URL: {result.get('drl_s3_url')}")

    return result

def test_list_containers():
    """List all Drools containers"""
    url = f"{BASE_URL}/drools_containers"
    response = requests.get(url)

    containers = response.json()
    print(json.dumps(containers, indent=2))

    return containers

if __name__ == "__main__":
    print("Testing S3 Processing...")
    test_s3_processing()

    print("\nListing Containers...")
    test_list_containers()
```

---

## 📊 Expected Results

### Successful Workflow Response

```json
{
  "pdf_path": null,
  "s3_url": "https://bucket.s3.amazonaws.com/policies/chase_insurance.pdf",
  "policy_type": "insurance",
  "bank_id": "chase",
  "container_id": "chase-insurance-underwriting-rules",
  "status": "completed",
  "jar_s3_url": "https://uw-data-extraction.s3.us-east-1.amazonaws.com/generated-rules/chase-insurance-underwriting-rules/20250104.143000/chase-insurance-underwriting-rules_20250104_143000.jar",
  "drl_s3_url": "https://uw-data-extraction.s3.us-east-1.amazonaws.com/generated-rules/chase-insurance-underwriting-rules/20250104.143000/chase-insurance-underwriting-rules_20250104_143000.drl",
  "steps": {
    "text_extraction": {
      "status": "success",
      "length": 15243
    },
    "query_generation": {
      "status": "success",
      "method": "llm_generated",
      "count": 12
    },
    "data_extraction": {
      "status": "success",
      "method": "textract"
    },
    "rule_generation": {
      "status": "success",
      "drl_length": 2456
    },
    "deployment": {
      "status": "success",
      "message": "Rules automatically deployed to container chase-insurance-underwriting-rules"
    },
    "s3_upload": {
      "jar": {
        "status": "success"
      },
      "drl": {
        "status": "success"
      }
    }
  }
}
```

---

## 🐛 Troubleshooting

### Issue: "No file uploaded"
**Solution:** Ensure `file` field is set with type `File` in form-data

### Issue: "Invalid S3 URL format"
**Solution:** Use full S3 URL: `https://bucket.s3.region.amazonaws.com/key/path/file.pdf`

### Issue: "Maven build failed"
**Solution:** Check Maven and Java are installed in Docker container

### Issue: "Container already exists"
**Solution:** This is expected - the system disposes and recreates containers automatically

---

## 🚀 Next Steps

1. **Start the service:**
   ```bash
   docker-compose up
   # or
   python3 -m flask --app ChatService run --port 9000
   ```

2. **Open Swagger UI:**
   ```
   http://localhost:9000/rule-agent/docs
   ```

3. **Try the examples** in the interactive UI

4. **Monitor logs** to see the workflow progress

5. **Check S3** for generated artifacts

6. **Verify Drools KIE Server** has deployed containers

---

For more information, see:
- [swagger.yaml](swagger.yaml) - OpenAPI specification
- [README_UNDERWRITING.md](../README_UNDERWRITING.md) - Architecture overview
- [CLAUDE.md](../CLAUDE.md) - Development guide
