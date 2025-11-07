# Underwriting AI System - Complete Guide

## Overview

This system combines Large Language Models with rule-based decision engines to create an intelligent underwriting AI that can:

1. **Process Policy Documents** - Upload insurance policy PDFs and automatically generate executable business rules
2. **Execute Decisions** - Use generated rules to make underwriting decisions via natural language queries

## Architecture

```
Policy PDF → OpenAI Analysis → AWS Textract → Rule Generation →
Drools Deployment → Runtime Execution → Natural Language Response
```

## Quick Start Options

### Option 1: Docker (Recommended)

**Fastest way to get started:**

```bash
# 1. Configure
cp docker.env llm.env
# Edit llm.env: Add OPENAI_API_KEY=sk-your-key

# 2. Start everything
docker-compose up -d

# 3. Test
curl -X POST http://localhost:9000/rule-agent/upload_policy \
  -F "file=@sample_policy.pdf"
```

📖 **Full Docker Guide**: [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)

### Option 2: Local Development

**For development and customization:**

```bash
# 1. Install dependencies
cd rule-agent
pip install -r requirements.txt

# 2. Configure
cp openai.env llm.env
# Edit llm.env: Add OPENAI_API_KEY

# 3. Start Drools (optional)
docker run -d -p 8080:8080 \
  -e KIE_SERVER_USER=admin \
  -e KIE_SERVER_PWD=admin \
  jboss/kie-server:latest

# 4. Start backend
python -m flask --app ChatService run --port 9000
```

📖 **Full Setup Guide**: [UNDERWRITING_SETUP.md](UNDERWRITING_SETUP.md)

## What's Included

### Core Services

1. **Policy Processing Workflow**
   - Upload PDFs via API
   - AI-powered document analysis
   - Automatic rule generation
   - Drools DRL & decision tables

2. **Runtime Execution**
   - Natural language queries
   - Drools rule engine integration
   - Explained decisions

3. **Multiple LLM Providers**
   - OpenAI (GPT-4, GPT-3.5)
   - Local Ollama
   - IBM watsonx.ai
   - IBM BAM

4. **Multiple Rule Engines**
   - Drools (new)
   - IBM ODM
   - IBM ADS

### Key Files Created

**Backend Services (7 new):**
- `DroolsService.py` - Runtime execution
- `TextractService.py` - AWS document extraction
- `PolicyAnalyzerAgent.py` - Document analysis
- `RuleGeneratorAgent.py` - Rule generation
- `DroolsDeploymentService.py` - Rule deployment
- `UnderwritingWorkflow.py` - Main orchestrator
- `CreateLLMOpenAI.py` - OpenAI integration

**Configuration:**
- `docker-compose.yml` - Docker orchestration
- `docker.env` - Environment template
- `openai.env` - Local environment template

**Documentation:**
- `DOCKER_QUICKSTART.md` - Docker quick reference
- `DOCKER_SETUP.md` - Complete Docker guide
- `UNDERWRITING_SETUP.md` - Local setup guide
- `IMPLEMENTATION_SUMMARY.md` - Architecture details
- `DOCKER_UPDATE_SUMMARY.md` - Docker changes

## Usage Examples

### 1. Upload a Policy Document

```bash
curl -X POST http://localhost:9000/rule-agent/upload_policy \
  -F "file=@life_insurance_policy.pdf" \
  -F "policy_type=life" \
  -F "container_id=underwriting-rules"
```

**Response:**
```json
{
  "status": "completed",
  "steps": {
    "text_extraction": {"status": "success"},
    "query_generation": {"queries": ["What is max coverage?", ...]},
    "data_extraction": {"data": {...}},
    "rule_generation": {"status": "success"},
    "save_rules": {"drl_path": "./generated_rules/underwriting-rules.drl"}
  }
}
```

### 2. Query for Underwriting Decision

```bash
curl -G "http://localhost:9000/rule-agent/chat_with_tools" \
  --data-urlencode "userMessage=Can we approve a 45-year-old applicant for $300,000 life insurance coverage?"
```

**Response:**
```json
{
  "input": "Can we approve a 45-year-old applicant for $300,000 life insurance coverage?",
  "output": "Yes, based on the underwriting rules, a 45-year-old applicant is eligible for $300,000 coverage..."
}
```

### 3. List Generated Rules

```bash
curl http://localhost:9000/rule-agent/list_generated_rules
```

### 4. View Rule Content

```bash
curl "http://localhost:9000/rule-agent/get_rule_content?filename=underwriting-rules.drl"
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rule-agent/upload_policy` | POST | Process policy PDF and generate rules |
| `/rule-agent/chat_with_tools` | GET | Query using decision services |
| `/rule-agent/chat_without_tools` | GET | Query using RAG only |
| `/rule-agent/list_generated_rules` | GET | List generated DRL files |
| `/rule-agent/get_rule_content` | GET | View specific rule file |
| `/rule-agent/drools_containers` | GET | List Drools containers |
| `/rule-agent/drools_container_status` | GET | Check container status |

## Components

### Phase 1: Rule Generation Pipeline

```
┌─────────────────────────────────────────────────────────┐
│  Policy PDF                                             │
│     ↓                                                   │
│  PolicyAnalyzerAgent (OpenAI)                          │
│     ↓ (generates extraction queries)                   │
│  TextractService (AWS) or LLM Fallback                 │
│     ↓ (extracts structured data)                       │
│  RuleGeneratorAgent (OpenAI)                           │
│     ↓ (generates Drools DRL)                           │
│  DroolsDeploymentService                               │
│     ↓ (creates KJar package)                           │
│  Generated Rules + Decision Tables                      │
└─────────────────────────────────────────────────────────┘
```

### Phase 2: Runtime Execution

```
┌─────────────────────────────────────────────────────────┐
│  User Query (Natural Language)                          │
│     ↓                                                   │
│  RuleAIAgent (OpenAI)                                  │
│     ↓ (extracts parameters)                            │
│  DroolsService                                          │
│     ↓ (invokes rules)                                  │
│  Decision + Explanation                                 │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Required Environment Variables

```env
LLM_TYPE=OPENAI
OPENAI_API_KEY=sk-your-actual-openai-key-here
```

### Optional Environment Variables

```env
# AWS Textract (for better extraction)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1

# Drools (auto-configured in Docker)
DROOLS_SERVER_URL=http://localhost:8080
DROOLS_USERNAME=admin
DROOLS_PASSWORD=admin
```

## Directory Structure

```
underwriter-rule-based-llms/
├── rule-agent/                     # Backend service
│   ├── DroolsService.py           # New: Drools integration
│   ├── TextractService.py         # New: AWS Textract
│   ├── PolicyAnalyzerAgent.py     # New: Document analysis
│   ├── RuleGeneratorAgent.py      # New: Rule generation
│   ├── UnderwritingWorkflow.py    # New: Orchestrator
│   └── ...
├── data/underwriting/              # New: Use case data
│   ├── catalog/                    # Policy PDFs for RAG
│   └── tool_descriptors/           # Tool definitions
├── uploads/                        # Uploaded policy files
├── generated_rules/                # Generated DRL files & KJars
├── docker-compose.yml              # Updated: Drools + volumes
└── Documentation/
    ├── DOCKER_QUICKSTART.md        # Quick Docker reference
    ├── DOCKER_SETUP.md             # Complete Docker guide
    ├── UNDERWRITING_SETUP.md       # Local setup guide
    └── IMPLEMENTATION_SUMMARY.md   # Architecture details
```

## Supported Policy Types

The system includes templates for:

- **General Insurance** - Basic coverage policies
- **Life Insurance** - Life insurance policies
- **Health Insurance** - Medical coverage policies
- **Auto Insurance** - Vehicle insurance policies
- **Property Insurance** - Home and property policies

## Troubleshooting

### Common Issues

**1. OpenAI API Error**
```
Solution: Check OPENAI_API_KEY in llm.env
```

**2. Drools Not Connected**
```
Solution: Start Drools server or use Docker Compose
```

**3. AWS Textract Not Working**
```
Solution: This is expected without AWS credentials.
System will use PyPDF2 + LLM fallback.
```

**4. Generated Rules Not Found**
```
Solution: Check ./generated_rules/ directory
Ensure DROOLS_RULES_DIR is set correctly
```

## Development

### Add New LLM Provider

1. Create `CreateLLM{Provider}.py`
2. Add to `CreateLLM.py`
3. Update environment template

### Add New Rule Engine

1. Create `{Engine}Service.py` extending `RuleService`
2. Add to `ChatService.py`
3. Create tool descriptors with `"engine": "{engine}"`

### Customize Rule Generation

Edit prompts in:
- `PolicyAnalyzerAgent.py` - Document analysis
- `RuleGeneratorAgent.py` - Rule generation

## Documentation Index

| Document | Purpose |
|----------|---------|
| [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) | Quick Docker commands |
| [DOCKER_SETUP.md](DOCKER_SETUP.md) | Complete Docker guide |
| [DOCKER_UPDATE_SUMMARY.md](DOCKER_UPDATE_SUMMARY.md) | Docker changes |
| [UNDERWRITING_SETUP.md](UNDERWRITING_SETUP.md) | Local development setup |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Architecture & design |
| [CLAUDE.md](CLAUDE.md) | Original project docs |

## Getting Help

1. Check the appropriate documentation file
2. Review logs: `docker-compose logs -f backend`
3. Verify configuration in `llm.env`
4. Test individual components

## License

Apache License 2.0 - See individual files for copyright notices.

---

## Next Steps

1. **Choose deployment method**: Docker or Local
2. **Configure environment**: Add your API keys
3. **Start services**: Follow quick start guide
4. **Upload a policy**: Test the workflow
5. **Query decisions**: Test runtime execution

**Ready to start?** Pick a quick start option above! 🚀
