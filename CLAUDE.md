# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This project demonstrates the integration of Large Language Models (LLMs) with rule-based decision services. It features a chatbot that can answer questions by combining LLM capabilities with Decision Services (IBM ODM or IBM ADS). The system can operate in two modes:
- LLM-only mode using RAG (Retrieval-Augmented Generation) with policy documents
- Decision Services mode using rule-based decision engines for accurate business rule execution

## Architecture

The system consists of three main components:

1. **rule-agent** (Python/Flask backend): LLM integration service that orchestrates between the LLM and decision services
2. **chatbot-frontend** (React/TypeScript): Web UI for the chatbot interface
3. **decision-services**: Sample ODM/ADS decision services and deployment artifacts

Key architectural patterns:
- The backend creates Langchain tools dynamically from JSON descriptors in `data/<use-case>/tool_descriptors/`
- Tool descriptors define how to call decision services (ODM or ADS) and map parameters
- Policy documents in `data/<use-case>/catalog/` are ingested into a vector store for RAG
- The LLM agent (`RuleAIAgent`) decides whether to invoke decision services or use RAG based on the user's query
- Both ODM and ADS services implement the `RuleService` interface for uniform invocation
- **Container-per-ruleset**: Each deployed rule set gets its own dedicated Drools container for complete isolation (see [CONTAINER_PER_RULESET.md](CONTAINER_PER_RULESET.md))

## Development Commands

### Backend (rule-agent)

Install dependencies:
```bash
cd rule-agent
pip3 install -r requirements.txt
```

Run the Flask service locally:
```bash
python3 -m flask --app ChatService run --port 9000
```

Test the API:
```bash
# With decision services
curl -G "http://localhost:9000/rule-agent/chat_with_tools" --data-urlencode "userMessage=<your question>"

# Without decision services (RAG only)
curl -G "http://localhost:9000/rule-agent/chat_without_tools" --data-urlencode "userMessage=<your question>"
```

### Frontend (chatbot-frontend)

Install dependencies:
```bash
cd chatbot-frontend
npm install
```

Run in development mode:
```bash
npm run dev
```

Build for production:
```bash
npm run build
```

Run linter:
```bash
npm run lint        # Check only
npm run lint:fix    # Fix issues
```

### Docker Deployment

Build all services:
```bash
docker-compose build
```

Run the complete stack:
```bash
docker-compose up
```

This starts:
- Drools KIE Server on port 8080 (default container)
- Backend API on port 9000
- Container orchestrator enabled (creates separate Drools containers per rule set)

**Important**: The system uses **container-per-ruleset architecture**. When you deploy rules, a new dedicated Drools container will be created automatically. See [CONTAINER_PER_RULESET.md](CONTAINER_PER_RULESET.md) for details.

Example deployment workflow:
1. Deploy rules → Creates `drools-chase-insurance-rules` container on port 8081
2. Deploy more rules → Creates `drools-bofa-loan-rules` container on port 8082
3. Each rule set runs in complete isolation with its own JVM

## LLM Configuration

The backend supports three LLM providers, configured via environment variables in `llm.env`:

1. **Ollama (Local)**: Copy `ollama.env` to `llm.env`
   - Requires Ollama running locally with the `mistral` model
   - Set `LLM_TYPE=LOCAL_OLLAMA`

2. **Watsonx.ai (Cloud)**: Copy `watsonx.env` to `llm.env`
   - Set `LLM_TYPE=WATSONX`
   - Configure `WATSONX_APIKEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`

3. **IBM BAM**: Copy appropriate config to `llm.env`
   - Set `LLM_TYPE=BAM`

The LLM provider is selected in [rule-agent/CreateLLM.py:22](rule-agent/CreateLLM.py#L22) based on the `LLM_TYPE` environment variable.

## Adding a New Use Case

To extend the application with a custom use case:

1. Create directory structure:
   ```
   data/<use-case-name>/
   ├── catalog/              # PDF policy documents for RAG
   ├── tool_descriptors/     # JSON files describing decision service APIs
   └── decisionapps/         # ODM ruleapps for automatic deployment (optional)
   ```

2. Add policy documents (PDF) to `catalog/` directory

3. Create tool descriptor JSON in `tool_descriptors/`:
   ```json
   {
     "engine": "odm",  // or "ads"
     "toolName": "YourToolName",
     "toolDescription": "Description for the LLM to understand when to use this tool",
     "toolPath": "/your_decision_service/1.0/operation/1.0",
     "args": [
       {
         "argName": "paramName",
         "argType": "str",  // str, number, or bool
         "argDescription": "Description of this parameter"
       }
     ],
     "output": "propertyNameInResponse"
   }
   ```

4. For ODM: Place ruleapp JAR files in `decisionapps/` or deploy manually via ODM console

5. Restart the backend to load the new use case

The system automatically discovers all `tool_descriptors/` and `catalog/` directories under `data/` at startup via [rule-agent/Utils.py](rule-agent/Utils.py) `find_descriptors()` function.

## Key Code Locations

- **LLM Agent orchestration**: [rule-agent/RuleAIAgent.py](rule-agent/RuleAIAgent.py) - main agent that coordinates tool selection and execution
- **Tool registration**: [rule-agent/DecisionServiceTools.py](rule-agent/DecisionServiceTools.py) - dynamically creates Langchain tools from JSON descriptors
- **ODM integration**: [rule-agent/ODMService.py](rule-agent/ODMService.py) - handles ODM REST API calls
- **ADS integration**: [rule-agent/ADSService.py](rule-agent/ADSService.py) - handles ADS REST API calls
- **RAG implementation**: [rule-agent/AIAgent.py](rule-agent/AIAgent.py) - vector store and document ingestion
- **Flask routes**: [rule-agent/ChatService.py](rule-agent/ChatService.py) - REST API endpoints
- **LLM prompts**: [rule-agent/prompts.py](rule-agent/prompts.py) - system prompts for the LLM

## Environment Variables

**Backend (rule-agent)**:
- `LLM_TYPE`: `LOCAL_OLLAMA`, `WATSONX`, or `BAM`
- `ODM_SERVER_URL`: ODM server URL (default: `http://localhost:9060`)
- `ODM_USERNAME`: ODM username (default: `odmAdmin`)
- `ODM_PASSWORD`: ODM password (default: `odmAdmin`)
- `ADS_SERVER_URL`: ADS server URL
- `ADS_USER_ID`: ADS user ID
- `ADS_ZEN_APIKEY`: ADS API key
- `DATADIR`: Path to data directory (default: `/data` in Docker)

**Frontend (chatbot-frontend)**:
- `API_URL`: Backend API URL (set at Docker build time)
