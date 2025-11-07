# Underwriting AI System - Setup Guide

This guide will help you set up and use the new underwriting AI system that generates Drools rules from policy documents.

## Overview

The system provides two main capabilities:

1. **Policy Processing Workflow** (New): Upload policy PDFs → Extract data with AWS Textract → Generate Drools rules with LLM
2. **Runtime Execution** (Existing): Use generated rules via chatbot to make underwriting decisions

## Quick Start

### 1. Install Dependencies

```bash
cd rule-agent
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the sample environment file and edit it with your credentials:

```bash
cp openai.env llm.env
```

Edit `llm.env` and add your API keys:

```env
# Required
LLM_TYPE=OPENAI
OPENAI_API_KEY=sk-your-actual-openai-key

# Optional - AWS Textract (if not configured, will use basic text extraction)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1

# Drools (if you have a Drools server running)
DROOLS_SERVER_URL=http://localhost:8080
DROOLS_USERNAME=admin
DROOLS_PASSWORD=admin
```

### 3. Start Drools KIE Server (Optional)

If you have Docker:

```bash
docker run -d -p 8080:8080 \
  -e KIE_SERVER_USER=admin \
  -e KIE_SERVER_PWD=admin \
  --name drools-server \
  jboss/kie-server:latest
```

### 4. Start the Backend Service

```bash
cd rule-agent
python -m flask --app ChatService run --port 9000
```

## Usage

### Workflow 1: Generate Rules from Policy Documents

#### Step 1: Upload a Policy PDF

Using curl:

```bash
curl -X POST http://localhost:9000/rule-agent/upload_policy \
  -F "file=@/path/to/your/policy.pdf" \
  -F "policy_type=life" \
  -F "container_id=underwriting-rules"
```

Using Python:

```python
import requests

files = {'file': open('policy.pdf', 'rb')}
data = {
    'policy_type': 'life',  # Options: general, life, health, auto, property
    'container_id': 'underwriting-rules',
    'use_template_queries': 'false'
}

response = requests.post(
    'http://localhost:9000/rule-agent/upload_policy',
    files=files,
    data=data
)

print(response.json())
```

#### Step 2: Review Generated Rules

The workflow will:
1. Extract text from PDF
2. Generate extraction queries using OpenAI
3. Extract structured data (with Textract if configured)
4. Generate Drools DRL rules
5. Save rules to `./generated_rules/`
6. Create KJar structure for deployment

Check the output:

```bash
# List generated rules
curl http://localhost:9000/rule-agent/list_generated_rules

# View specific rule content
curl "http://localhost:9000/rule-agent/get_rule_content?filename=underwriting-rules.drl"
```

#### Step 3: Deploy Rules to Drools

Navigate to the generated KJar directory and build:

```bash
cd generated_rules/underwriting-rules_kjar
mvn clean install
```

Deploy to Drools:

```bash
curl -X PUT "http://localhost:8080/kie-server/services/rest/server/containers/underwriting-rules" \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d '{
    "container-id": "underwriting-rules",
    "release-id": {
      "group-id": "com.underwriting",
      "artifact-id": "underwriting-rules",
      "version": "1.0.0"
    }
  }'
```

### Workflow 2: Use Rules via Chatbot

Once rules are deployed, you can query them via the chatbot:

```bash
curl -G "http://localhost:9000/rule-agent/chat_with_tools" \
  --data-urlencode "userMessage=Can we approve a 45-year-old applicant for $300,000 life insurance coverage?"
```

The system will:
1. Extract parameters from your question using LLM
2. Invoke the Drools rule engine
3. Return a natural language response with the decision

## API Endpoints

### Policy Processing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rule-agent/upload_policy` | POST | Upload and process policy PDF |
| `/rule-agent/list_generated_rules` | GET | List all generated DRL files |
| `/rule-agent/get_rule_content` | GET | Get content of specific rule file |
| `/rule-agent/drools_containers` | GET | List Drools containers |
| `/rule-agent/drools_container_status` | GET | Get container status |

### Chat/Query (Existing)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rule-agent/chat_with_tools` | GET | Query using decision services |
| `/rule-agent/chat_without_tools` | GET | Query using RAG only |

## Example: Complete Flow

### 1. Process a Life Insurance Policy

```bash
curl -X POST http://localhost:9000/rule-agent/upload_policy \
  -F "file=@life_insurance_policy.pdf" \
  -F "policy_type=life"
```

**Response:**
```json
{
  "status": "completed",
  "steps": {
    "text_extraction": {
      "status": "success",
      "length": 12543
    },
    "query_generation": {
      "status": "success",
      "queries": [
        "What is the maximum life insurance coverage amount?",
        "What is the minimum age for applicants?",
        "What is the maximum age for applicants?"
      ],
      "count": 3
    },
    "data_extraction": {
      "status": "success",
      "data": {
        "queries": {
          "What is the maximum life insurance coverage amount?": {
            "answer": "$500,000",
            "confidence": 95.2
          },
          "What is the minimum age for applicants?": {
            "answer": "18 years",
            "confidence": 98.1
          },
          "What is the maximum age for applicants?": {
            "answer": "65 years",
            "confidence": 97.5
          }
        }
      }
    },
    "rule_generation": {
      "status": "success",
      "drl_length": 1245
    },
    "save_rules": {
      "status": "success",
      "drl_path": "./generated_rules/underwriting-rules.drl"
    },
    "kjar_creation": {
      "status": "success",
      "kjar_path": "./generated_rules/underwriting-rules_kjar"
    }
  }
}
```

### 2. View Generated Rules

```bash
curl "http://localhost:9000/rule-agent/get_rule_content?filename=underwriting-rules.drl"
```

### 3. Deploy (Manual)

```bash
cd generated_rules/underwriting-rules_kjar
mvn clean install

# Then deploy via Drools REST API or KIE Workbench
```

### 4. Query the Rules

```bash
curl -G "http://localhost:9000/rule-agent/chat_with_tools" \
  --data-urlencode "userMessage=Can I get $400,000 coverage if I'm 55 years old?"
```

**Response:**
```json
{
  "input": "Can I get $400,000 coverage if I'm 55 years old?",
  "output": "Yes, based on the underwriting rules, a 55-year-old applicant is eligible for $400,000 coverage as it falls within the acceptable age range (18-65 years) and the coverage amount is below the maximum limit of $500,000."
}
```

## Configuration Options

### LLM Providers

The system supports multiple LLM providers. Set `LLM_TYPE` in `llm.env`:

- `OPENAI` - OpenAI (ChatGPT, GPT-4)
- `LOCAL_OLLAMA` - Local Ollama
- `WATSONX` - IBM watsonx.ai
- `BAM` - IBM BAM

### Drools Invocation Modes

Set `DROOLS_INVOCATION_MODE`:

- `kie-batch` (default) - KIE Server batch command execution
- `dmn` - Decision Model and Notation
- `rest` - Custom REST endpoint

### AWS Textract

If AWS credentials are not configured, the system will:
- Use PyPDF2 for basic text extraction
- Use LLM to answer extraction queries instead of Textract
- Still generate valid Drools rules

## Directory Structure

```
underwriter-rule-based-llms/
├── rule-agent/
│   ├── DroolsService.py              # Drools runtime execution
│   ├── DroolsDeploymentService.py    # Rule deployment
│   ├── TextractService.py            # AWS Textract integration
│   ├── PolicyAnalyzerAgent.py        # Document analysis
│   ├── RuleGeneratorAgent.py         # Rule generation
│   ├── UnderwritingWorkflow.py       # Workflow orchestration
│   ├── CreateLLMOpenAI.py            # OpenAI integration
│   ├── ChatService.py                # Flask API endpoints
│   └── openai.env                    # Sample config
├── data/
│   └── underwriting/
│       ├── catalog/                  # Policy PDFs for RAG
│       └── tool_descriptors/         # Drools tool descriptors
├── uploads/                          # Uploaded policy files
└── generated_rules/                  # Generated DRL files and KJars
```

## Troubleshooting

### AWS Textract Not Available

If you see: `AWS Textract is not configured`

**Solution:** The system will work without Textract using basic extraction. To enable Textract, add AWS credentials to `llm.env`.

### Drools Server Not Running

If you see: `Unable to reach Drools Server`

**Solution:**
1. The system will fall back to ODM if available
2. Rules will still be generated and saved locally
3. Start Drools server to enable runtime execution

### OpenAI API Errors

If you see: `OPENAI_API_KEY environment variable is required`

**Solution:** Add your OpenAI API key to `llm.env`:
```env
OPENAI_API_KEY=sk-your-actual-key-here
```

### Generated Rules Not Working

**Check:**
1. Rule syntax - view with `/get_rule_content` endpoint
2. Drools container status - use `/drools_container_status` endpoint
3. KJar build output for errors

## Next Steps

1. **Test with sample policy**: Try uploading a sample insurance policy PDF
2. **Review generated rules**: Check the DRL output and adjust prompts if needed
3. **Refine prompts**: Edit `PolicyAnalyzerAgent.py` and `RuleGeneratorAgent.py` to improve output
4. **Add validation**: Implement rule validation before deployment
5. **Build UI**: Create a frontend interface for policy upload and rule management

## Support

For issues or questions:
- Check the main CLAUDE.md file for architecture details
- Review the code in the new service files
- Check Flask logs for detailed error messages

## Architecture

```
Policy PDF
    ↓
[PolicyAnalyzerAgent] ← OpenAI
    ↓ (generates queries)
[TextractService] ← AWS Textract
    ↓ (extracts data)
[RuleGeneratorAgent] ← OpenAI
    ↓ (generates DRL)
[DroolsDeploymentService]
    ↓ (saves & packages)
Generated Rules (DRL + KJar)
    ↓
[DroolsService] ← Runtime
    ↓
Chat Interface
```

Enjoy building your underwriting AI system!
