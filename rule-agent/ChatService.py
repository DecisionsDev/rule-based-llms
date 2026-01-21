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
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from RuleAIAgent import RuleAIAgent
from AIAgent import AIAgent
from RuleAIAgent2 import RuleAIAgent2
from CreateLLM import createLLM
from ODMService import ODMService
from ADSService import ADSService
from DroolsService import DroolsService
from UnderwritingWorkflow import UnderwritingWorkflow
from RuleCacheService import get_rule_cache
from DatabaseService import get_database_service
from S3Service import S3Service
from DroolsHierarchicalMapper import DroolsHierarchicalMapper
import json,os
from Utils import find_descriptors
from werkzeug.utils import secure_filename

ROUTE="/rule-agent"

# Initialize database service
db_service = get_database_service()

app = Flask(__name__)

# Configure CORS to allow all origins with all necessary headers and methods
# Apply to all routes including /rule-agent/* paths
cors = CORS(app, resources={
    r"/rule-agent/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
        "expose_headers": ["Content-Type", "X-Total-Count"],
        "supports_credentials": False,
        "max_age": 3600
    },
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
        "expose_headers": ["Content-Type", "X-Total-Count"],
        "supports_credentials": False,
        "max_age": 3600
    }
})
app.config['CORS_HEADERS'] = 'Content-Type'

# Add after_request handler to ensure CORS headers on all responses
@app.after_request
def after_request(response):
    """Add CORS headers to every response"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response

# create a LLM service
llm = createLLM()

# print("Using LLM model: ", llm.model_id)


# Create all decision services - always return all services even if not connected
# Tool descriptors need to access services by name, so we include all of them
def get_rule_services():
    services = {
        "ads": adsService,
        "drools": droolsService,
        "odm": odmService
    }
    return services

# create Decision services
adsService = ADSService()
droolsService = DroolsService()
odmService = ODMService()
ruleServices = get_rule_services()

# create Decision services (ODM and ADS)
#odmService = ODMService()
#adsService = ADSService()
#ruleServices = { "odm": odmService, "ads": adsService}

# create an AI Agent using Decision Services
ruleAIAgent = RuleAIAgent(llm, ruleServices)
# alternative way to implement a chain using tools
# ruleAIAgent = RuleAIAgent2(llm, ruleServices)

# create an AI Agent using RAG only
aiAgent = AIAgent(llm)

# create Underwriting Workflow
underwritingWorkflow = UnderwritingWorkflow(llm)

# create S3 Service for file uploads
s3Service = S3Service()

def ingestAllDocuments(directory_path):
    """Reads all PDF files in a directory and returns a list of document to load.

    :param directory_path: The path to the directory containing the JSON files.
    :return: A list of ToolDescriptor instances.
    """
    for filename in os.listdir(directory_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(directory_path, filename)
            print("Ingesting document : "+file_path)
            aiAgent.ingestDocument(file_path)

catalog_dirs = find_descriptors('catalog')
for directory in catalog_dirs:
    ingestAllDocuments(directory)
    
# Web Service routes

@app.route(ROUTE + '/chat_with_tools', methods=['GET'])
def chat_with_tools():
    if (not odmService.isConnected):
        print("Error: Not connected to any Decision runtime")
        return {'output' : 'Not connected to any Decision runtime', 'type' : 'error'}

    userInput = request.args.get('userMessage')    
    print("chat_with_tools: received request ", userInput) 
    response = ruleAIAgent.processMessage(userInput)    
    # response = ruleAIAgent2.processMessage(userInput)
    # print("response: ", response)  
    return response

@app.route(ROUTE + '/chat_without_tools', methods=['GET'])
def chat_without_tools():
    userInput = request.args.get('userMessage')
    print("chat_without_tools: received request ", userInput)
    response = aiAgent.processMessage(userInput)
    # print("response: ", response)
    return response

# New endpoints for underwriting workflow

@app.route(ROUTE + '/upload_policy', methods=['POST', 'OPTIONS'])
def upload_policy():
    """DEPRECATED: Local file upload is no longer supported. Use /process_policy_from_s3 instead."""
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        return '', 200

    return jsonify({
        'error': 'Local file upload is deprecated. Please upload your PDF to S3 and use /process_policy_from_s3 endpoint instead.',
        'status': 'deprecated'
    }), 400

@app.route(ROUTE + '/process_policy_from_s3', methods=['POST', 'OPTIONS'])
def process_policy_from_s3():
    """Process a policy PDF from S3 URL through the underwriting workflow"""
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()

    if not data:
        return jsonify({'error': 'JSON body is required'}), 400

    # Validate required fields
    if 's3_url' not in data:
        return jsonify({'error': 's3_url is required in JSON body'}), 400

    if 'policy_type' not in data:
        return jsonify({'error': 'policy_type is required in JSON body (e.g., "life_insurance", "auto", "property")'}), 400

    if 'bank_id' not in data:
        return jsonify({'error': 'bank_id is required in JSON body (e.g., "chase", "bofa", "wells-fargo")'}), 400

    s3_url = data['s3_url']
    policy_type = data['policy_type']
    bank_id = data['bank_id']

    # Process through workflow with S3 URL
    # container_id is auto-generated from bank_id and policy_type
    # LLM generates queries by analyzing the document
    # Rules are transformed to user-friendly text using OpenAI
    try:
        result = underwritingWorkflow.process_policy_document(
            s3_url=s3_url,
            policy_type=policy_type,
            bank_id=bank_id
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'failed'}), 500

@app.route(ROUTE + '/list_generated_rules', methods=['GET'])
def list_generated_rules():
    """List all generated rule files - DEPRECATED

    Note: This endpoint is deprecated as rules are no longer persisted locally.
    Rules are now uploaded directly to S3 and deployed to Drools KIE Server.
    Use S3 API to list generated rules from S3 bucket.
    """
    return jsonify({
        'rules': [],
        'count': 0,
        'message': 'Rules are no longer stored locally. Check S3 bucket for generated rules.'
    })

@app.route(ROUTE + '/get_rule_content', methods=['GET'])
def get_rule_content():
    """Get content of a generated rule file - DEPRECATED

    Note: This endpoint is deprecated as rules are no longer persisted locally.
    Use S3 API to retrieve rule content from S3 bucket.
    """
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'filename parameter is required'}), 400

    return jsonify({
        'error': 'Rules are no longer stored locally. Retrieve from S3 bucket instead.'
    }), 404

@app.route(ROUTE + '/drools_containers', methods=['GET'])
def drools_containers():
    """List Drools KIE Server containers"""
    from DroolsDeploymentService import DroolsDeploymentService
    deployment = DroolsDeploymentService()
    result = deployment.list_containers()
    return jsonify(result)

@app.route(ROUTE + '/orchestrated_containers', methods=['GET'])
def orchestrated_containers():
    """List orchestrated Docker/K8s containers with health status"""
    from ContainerOrchestrator import get_orchestrator
    orchestrator = get_orchestrator()
    result = orchestrator.list_containers()
    return jsonify(result)

@app.route(ROUTE + '/drools_container_status', methods=['GET'])
def drools_container_status():
    """Get status of a specific Drools container"""
    container_id = request.args.get('container_id')
    if not container_id:
        return jsonify({'error': 'container_id parameter is required'}), 400

    from DroolsDeploymentService import DroolsDeploymentService
    deployment = DroolsDeploymentService()
    result = deployment.get_container_status(container_id)
    return jsonify(result)

@app.route(ROUTE + '/test_rules', methods=['POST', 'OPTIONS'])
def test_rules():
    """
    Test deployed Drools rules with sample data

    Request body:
    {
        "container_id": "chase-insurance-underwriting-rules",
        "applicant": {
            "name": "John Doe",
            "age": 35,
            "occupation": "Engineer",
            "healthConditions": null
        },
        "policy": {
            "policyType": "Term Life",
            "coverageAmount": 500000,
            "term": 20
        }
    }

    Returns the Decision object with approval status, reason, and premium multiplier
    """
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    container_id = data.get('container_id')
    if not container_id:
        return jsonify({'error': 'container_id is required'}), 400

    applicant = data.get('applicant', {})
    policy = data.get('policy', {})

    try:
        # Get container endpoint from database (no fallback)
        container = db_service.get_container(container_id)
        if not container:
            return jsonify({'error': f'Container {container_id} not found in database'}), 404

        if not container.endpoint:
            return jsonify({'error': f'Container {container_id} has no endpoint configured'}), 500

        # Execute rules via Drools KIE Server REST API
        import requests
        from requests.auth import HTTPBasicAuth

        drools_url = f"{container.endpoint}/kie-server/services/rest/server"
        drools_user = os.getenv('DROOLS_USERNAME', 'kieserver')
        drools_password = os.getenv('DROOLS_PASSWORD', 'kieserver1!')

        # Build the request payload for Drools
        payload = {
            "lookup": None,
            "commands": [
                {
                    "insert": {
                        "object": {
                            "com.underwriting.rules.Applicant": applicant
                        },
                        "out-identifier": "applicant",
                        "return-object": True
                    }
                },
                {
                    "insert": {
                        "object": {
                            "com.underwriting.rules.Policy": policy
                        },
                        "out-identifier": "policy",
                        "return-object": True
                    }
                },
                {
                    "fire-all-rules": {
                        "max": -1,
                        "out-identifier": "fired"
                    }
                },
                {
                    "query": {
                        "name": "getDecision",
                        "out-identifier": "decision"
                    }
                }
            ]
        }

        # Alternative: Get all objects approach
        payload_alt = {
            "lookup": None,
            "commands": [
                {
                    "insert": {
                        "object": {
                            "com.underwriting.rules.Applicant": applicant
                        },
                        "out-identifier": "applicant",
                        "return-object": False
                    }
                },
                {
                    "insert": {
                        "object": {
                            "com.underwriting.rules.Policy": policy
                        },
                        "out-identifier": "policy",
                        "return-object": False
                    }
                },
                {
                    "fire-all-rules": {
                        "max": -1,
                        "out-identifier": "fired"
                    }
                },
                {
                    "get-objects": {
                        "out-identifier": "objects"
                    }
                }
            ]
        }

        print(f"Testing rules in container: {container_id}")
        print(f"Payload: {json.dumps(payload_alt, indent=2)}")

        response = requests.post(
            f"{drools_url}/containers/instances/{container_id}",
            auth=HTTPBasicAuth(drools_user, drools_password),
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            json=payload_alt
        )

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        if response.status_code == 200:
            result = response.json()

            # Extract Decision object from results
            decision = None
            if 'result' in result and 'execution-results' in result['result']:
                exec_results = result['result']['execution-results']
                if 'results' in exec_results:
                    for res in exec_results['results']:
                        if res.get('key') == 'objects':
                            objects = res.get('value', [])
                            # Objects is a list of dictionaries
                            if isinstance(objects, list):
                                for obj in objects:
                                    if 'com.underwriting.rules.Decision' in obj:
                                        decision = obj['com.underwriting.rules.Decision']
                                        break

            return jsonify({
                'status': 'success',
                'container_id': container_id,
                'decision': decision,
                'rules_fired': result.get('result', {}).get('execution-results', {}).get('results', []),
                'full_response': result
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Drools execution failed with status {response.status_code}',
                'response': response.text
            }), response.status_code

    except Exception as e:
        print(f"Error testing rules: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Cache management endpoints
@app.route(ROUTE + '/cache/status', methods=['GET'])
def get_cache_status():
    """
    Get cache statistics and list of cached documents

    Returns:
        JSON with cache directory, document count, and list of cached documents
    """
    try:
        cache = get_rule_cache()
        stats = cache.get_cache_stats()
        cached_docs = cache.list_cached_documents()

        return jsonify({
            "status": "success",
            "cache_stats": stats,
            "cached_documents": cached_docs
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route(ROUTE + '/cache/clear', methods=['POST', 'OPTIONS'])
def clear_cache():
    """
    Clear rule cache (specific document or all)

    Request body (optional):
        {
            "document_hash": "abc123..."  // Optional: clear specific document only
        }

    Returns:
        JSON with status and message
    """
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json() or {}
        document_hash = data.get('document_hash')

        cache = get_rule_cache()
        cache.clear_cache(document_hash)

        if document_hash:
            message = f"Cache cleared for document: {document_hash[:16]}..."
        else:
            message = "All cache cleared successfully"

        return jsonify({
            "status": "success",
            "message": message
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route(ROUTE + '/cache/get', methods=['GET'])
def get_cached_rules():
    """
    Get cached rules for a specific document hash

    Query parameters:
        document_hash: SHA-256 hash of the document

    Returns:
        JSON with cached rule data or 404 if not found
    """
    try:
        document_hash = request.args.get('document_hash')
        if not document_hash:
            return jsonify({
                "status": "error",
                "message": "document_hash parameter required"
            }), 400

        cache = get_rule_cache()
        cached_result = cache.get_cached_rules(document_hash)

        if cached_result:
            return jsonify({
                "status": "success",
                "cached": True,
                "data": cached_result
            })
        else:
            return jsonify({
                "status": "success",
                "cached": False,
                "message": f"No cached rules found for {document_hash[:16]}..."
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ============================================================================
# CUSTOMER-FACING API ENDPOINTS (Database-backed)
# ============================================================================

@app.route(ROUTE + '/api/v1/banks', methods=['GET'])
def list_banks():
    """List all available banks"""
    try:
        banks = db_service.list_banks(active_only=True)
        return jsonify({
            "status": "success",
            "banks": [{
                "bank_id": bank['bank_id'],
                "bank_name": bank['bank_name'],
                "description": bank['description']
            } for bank in banks]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route(ROUTE + '/api/v1/banks/<bank_id>/policies', methods=['GET'])
def list_bank_policies(bank_id):
    """
    List all available policy types for a specific bank

    Query parameters:
    - include_queries: Include extraction queries count (optional, default: false)
    - include_rules: Include extracted rules count (optional, default: false)
    - include_hierarchical_rules: Include hierarchical rules count (optional, default: false)
    - details: Include full details with queries and rules (optional, default: false)
    """
    try:
        include_queries = request.args.get('include_queries', 'false').lower() == 'true'
        include_rules = request.args.get('include_rules', 'false').lower() == 'true'
        include_hierarchical_rules = request.args.get('include_hierarchical_rules', 'false').lower() == 'true'
        include_details = request.args.get('details', 'false').lower() == 'true'

        # Get active containers for this bank
        containers = db_service.list_containers(bank_id=bank_id, active_only=True)

        # Get unique policy type IDs
        policy_type_ids = list(set([c['policy_type_id'] for c in containers]))

        # Get all policy types and filter by the ones available for this bank
        all_policy_types = db_service.list_policy_types(active_only=True)

        # Filter to only include policy types that have containers for this bank
        policies = []
        for pt in all_policy_types:
            if pt['policy_type_id'] in policy_type_ids:
                policy_data = {
                    "policy_type_id": pt['policy_type_id'],
                    "policy_name": pt['policy_name'],
                    "description": pt['description'],
                    "category": pt['category']
                }

                # Add counts if requested
                if include_queries or include_details:
                    extraction_queries = db_service.get_extraction_queries(
                        bank_id=bank_id,
                        policy_type_id=pt['policy_type_id'],
                        active_only=True
                    )
                    policy_data["extraction_queries_count"] = len(extraction_queries)
                    if include_details:
                        policy_data["extraction_queries"] = extraction_queries

                if include_rules or include_details:
                    extracted_rules = db_service.get_extracted_rules(
                        bank_id=bank_id,
                        policy_type_id=pt['policy_type_id'],
                        active_only=True
                    )
                    policy_data["extracted_rules_count"] = len(extracted_rules)
                    if include_details:
                        policy_data["extracted_rules"] = extracted_rules

                if include_hierarchical_rules or include_details:
                    hierarchical_rules = db_service.get_hierarchical_rules(
                        bank_id=bank_id,
                        policy_type_id=pt['policy_type_id'],
                        active_only=True
                    )
                    policy_data["hierarchical_rules_count"] = len(hierarchical_rules)
                    if include_details:
                        policy_data["hierarchical_rules"] = hierarchical_rules

                policies.append(policy_data)

        return jsonify({
            "status": "success",
            "bank_id": bank_id,
            "policies": policies,
            "total_policies": len(policies)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route(ROUTE + '/api/v1/policies', methods=['GET'])
def query_policies():
    """
    Query for available policy containers with extraction queries, rules, and test cases

    Query parameters:
    - bank_id: Bank identifier (required)
    - policy_type: Policy type identifier (required)
    - include_queries: Include extraction queries (optional, default: false)
    - include_rules: Include extracted rules (optional, default: false)
    - include_hierarchical_rules: Include hierarchical rules tree (optional, default: false)
    - include_test_cases: Include test cases (optional, default: false)
    """
    try:
        bank_id = request.args.get('bank_id')
        policy_type = request.args.get('policy_type')
        include_queries = request.args.get('include_queries', 'false').lower() == 'true'
        include_rules = request.args.get('include_rules', 'false').lower() == 'true'
        include_hierarchical_rules = request.args.get('include_hierarchical_rules', 'false').lower() == 'true'
        include_test_cases = request.args.get('include_test_cases', 'false').lower() == 'true'

        if not bank_id or not policy_type:
            return jsonify({
                "error": "Both bank_id and policy_type query parameters are required"
            }), 400

        # Get active container for this bank+policy combination
        container = db_service.get_active_container(bank_id, policy_type)

        if not container:
            return jsonify({
                "status": "not_found",
                "message": f"No active container found for bank '{bank_id}' and policy type '{policy_type}'"
            }), 404

        response_data = {
            "status": "success",
            "container": {
                "container_id": container['container_id'],
                "bank_id": container['bank_id'],
                "policy_type_id": container['policy_type_id'],
                "endpoint": container['endpoint'],
                "status": container['status'],
                "health_status": container['health_status'],
                "deployed_at": container['deployed_at']
            }
        }

        # Add S3 URLs and generate pre-signed URLs for documents
        if container.get('s3_policy_url'):
            response_data["container"]["s3_policy_url"] = container['s3_policy_url']
            # Generate pre-signed URL for policy document
            policy_presigned = s3Service.generate_presigned_url_from_s3_url(container['s3_policy_url'], expiration=86400)
            if policy_presigned:
                response_data["container"]["policy_presigned_url"] = policy_presigned

        if container.get('s3_jar_url'):
            response_data["container"]["s3_jar_url"] = container['s3_jar_url']
            # Generate pre-signed URL for JAR file
            jar_presigned = s3Service.generate_presigned_url_from_s3_url(container['s3_jar_url'], expiration=86400)
            if jar_presigned:
                response_data["container"]["jar_presigned_url"] = jar_presigned

        if container.get('s3_drl_url'):
            response_data["container"]["s3_drl_url"] = container['s3_drl_url']
            # Generate pre-signed URL for DRL file
            drl_presigned = s3Service.generate_presigned_url_from_s3_url(container['s3_drl_url'], expiration=86400)
            if drl_presigned:
                response_data["container"]["drl_presigned_url"] = drl_presigned

        if container.get('s3_excel_url'):
            response_data["container"]["s3_excel_url"] = container['s3_excel_url']
            # Generate pre-signed URL for Excel file
            excel_presigned = s3Service.generate_presigned_url_from_s3_url(container['s3_excel_url'], expiration=86400)
            if excel_presigned:
                response_data["container"]["excel_presigned_url"] = excel_presigned

        if container.get('s3_test_harness_url'):
            response_data["container"]["s3_test_harness_url"] = container['s3_test_harness_url']
            # Generate pre-signed URL for test harness file
            test_harness_presigned = s3Service.generate_presigned_url_from_s3_url(container['s3_test_harness_url'], expiration=86400)
            if test_harness_presigned:
                response_data["container"]["test_harness_presigned_url"] = test_harness_presigned

        # Include extraction queries if requested
        if include_queries:
            extraction_queries = db_service.get_extraction_queries(
                bank_id=bank_id,
                policy_type_id=policy_type,
                active_only=True
            )
            response_data["extraction_queries"] = extraction_queries
            response_data["extraction_queries_count"] = len(extraction_queries)

        # Include extracted rules if requested
        if include_rules:
            extracted_rules = db_service.get_extracted_rules(
                bank_id=bank_id,
                policy_type_id=policy_type,
                active_only=True
            )
            response_data["extracted_rules"] = extracted_rules
            response_data["extracted_rules_count"] = len(extracted_rules)

        # Include hierarchical rules if requested
        if include_hierarchical_rules:
            hierarchical_rules = db_service.get_hierarchical_rules(
                bank_id=bank_id,
                policy_type_id=policy_type,
                active_only=True
            )
            response_data["hierarchical_rules"] = hierarchical_rules
            response_data["hierarchical_rules_count"] = len(hierarchical_rules)

        # Include test cases if requested
        if include_test_cases:
            test_cases = db_service.get_test_cases(
                bank_id=bank_id,
                policy_type_id=policy_type,
                is_active=True
            )
            response_data["test_cases"] = test_cases
            response_data["test_cases_count"] = len(test_cases)

            # Add test case statistics by category
            category_stats = {
                "positive": len([tc for tc in test_cases if tc.get('category') == 'positive']),
                "negative": len([tc for tc in test_cases if tc.get('category') == 'negative']),
                "boundary": len([tc for tc in test_cases if tc.get('category') == 'boundary']),
                "edge_case": len([tc for tc in test_cases if tc.get('category') == 'edge_case'])
            }
            response_data["test_cases_by_category"] = category_stats

        return jsonify(response_data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route(ROUTE + '/api/v1/policies/update-rules', methods=['POST', 'OPTIONS'])
def update_policy_rules():
    """
    Update a policy with new DRL rules and redeploy
    
    This endpoint allows updating rules for an existing policy without reprocessing the entire document.
    It will:
    1. Parse and save the new rules to the database
    2. Redeploy the rules to Drools KIE Server
    3. Increment the container version
    4. Update S3 URLs for new artifacts
    5. Log deployment history for audit
    
    Request body:
    {
        "bank_id": "chase",
        "policy_type": "insurance",
        "drl_content": "package com.underwriting; rule \"New Rule\" when ... then ... end"
    }
    """
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON body is required'}), 400
        
        # Validate required fields
        if 'bank_id' not in data:
            return jsonify({'error': 'bank_id is required'}), 400
        
        if 'policy_type' not in data:
            return jsonify({'error': 'policy_type is required'}), 400
        
        if 'drl_content' not in data:
            return jsonify({'error': 'drl_content is required. Provide the updated Drools rules.'}), 400
        
        bank_id = data['bank_id']
        policy_type = data['policy_type']
        drl_content = data['drl_content']
        
        # Normalize IDs (same as process_policy_from_s3)
        normalized_bank = bank_id.lower().strip().replace(' ', '-')
        normalized_type = policy_type.lower().strip().replace(' ', '-')
        container_id = f"{normalized_bank}-{normalized_type}-underwriting-rules"
        
        print(f"\n{'='*60}")
        print(f"Update Rules Request for: {container_id}")
        print(f"{'='*60}")
        
        # Get existing container
        container = db_service.get_active_container(normalized_bank, normalized_type)
        if not container:
            return jsonify({
                "status": "error",
                "message": f"No active container found for bank '{bank_id}' and policy type '{policy_type}'. Please deploy rules first using /process_policy_from_s3"
            }), 404
        
        result = {
            "bank_id": normalized_bank,
            "policy_type": normalized_type,
            "container_id": container_id,
            "steps": {},
            "status": "in_progress"
        }
        
        # Step 1: Parse and save rules to database
        try:
            print("\n" + "="*60)
            print("Step 1: Parsing and saving rules to database...")
            print("="*60)
            
            # Parse DRL content to extract actual rules
            rules_for_db = underwritingWorkflow._parse_drl_rules(drl_content)
            
            if rules_for_db:
                # Get current document info from container
                source_document = container.get('s3_policy_url', '')
                document_hash = container.get('document_hash', '')
                
                # Save to database (this will deactivate old rules)
                saved_ids = db_service.save_extracted_rules(
                    bank_id=normalized_bank,
                    policy_type_id=normalized_type,
                    rules=rules_for_db,
                    source_document=source_document,
                    document_hash=document_hash
                )
                
                print(f"✓ Updated {len(saved_ids)} rules in database")
                result["steps"]["update_database_rules"] = {
                    "status": "success",
                    "count": len(saved_ids),
                    "rule_ids": saved_ids
                }
            else:
                print("⚠ No parseable rules found in DRL content")
                result["steps"]["update_database_rules"] = {
                    "status": "warning",
                    "message": "No parseable rules found in DRL content"
                }
        except Exception as e:
            print(f"⚠ Failed to parse/save rules to database: {e}")
            result["steps"]["update_database_rules"] = {
                "status": "error",
                "message": str(e)
            }
        
        # Step 2: Redeploy rules to Drools KIE Server
        try:
            print("\n" + "="*60)
            print("Step 2: Redeploying rules to Drools KIE Server...")
            print("="*60)
            
            # Deploy new rules using existing deployment infrastructure
            deployment_result = underwritingWorkflow.drools_deployment.deploy_rules_automatically(
                drl_content=drl_content,
                container_id=container_id
            )
            
            result["steps"]["redeployment"] = deployment_result
            
            if deployment_result["status"] == "success":
                print(f"✓ Rules redeployed successfully")
                
                # Step 3: Update container version and metadata in database
                try:
                    print("\n" + "="*60)
                    print("Step 3: Updating container version in database...")
                    print("="*60)
                    
                    # Increment version
                    current_version = container.get('version', 1)
                    new_version = current_version + 1
                    
                    # Update container version
                    db_service.update_container_version(
                        container_id=container_id,
                        version=new_version
                    )
                    
                    print(f"✓ Container version updated from {current_version} to {new_version}")
                    result["new_version"] = new_version
                    
                    # Step 4: Upload new artifacts to S3 if deployment was successful
                    if "steps" in deployment_result:
                        build_step = deployment_result["steps"].get("build", {})
                        if build_step.get("status") == "success":
                            print("\n" + "="*60)
                            print("Step 4: Uploading new artifacts to S3...")
                            print("="*60)
                            
                            jar_path = build_step.get("jar_path")
                            drl_path = deployment_result["steps"].get("save_drl", {}).get("path")
                            version_str = deployment_result["release_id"]["version"]
                            
                            s3_upload_results = {}
                            
                            # Upload JAR file
                            if jar_path and os.path.exists(jar_path):
                                jar_upload = s3Service.upload_jar_to_s3(jar_path, container_id, version_str)
                                if jar_upload["status"] == "success":
                                    db_service.update_container_urls(
                                        container_id,
                                        s3_jar_url=jar_upload["s3_url"]
                                    )
                                    s3_upload_results["jar"] = jar_upload
                                    print(f"✓ JAR uploaded to S3: {jar_upload['s3_url']}")
                                    
                                    # Clean up temp JAR file
                                    try:
                                        os.unlink(jar_path)
                                        print(f"✓ Temporary JAR file deleted")
                                    except Exception as e:
                                        print(f"Warning: Could not delete temp JAR file: {e}")
                            
                            # Upload DRL file
                            if drl_path and os.path.exists(drl_path):
                                drl_upload = s3Service.upload_drl_to_s3(drl_path, container_id, version_str)
                                if drl_upload["status"] == "success":
                                    db_service.update_container_urls(
                                        container_id,
                                        s3_drl_url=drl_upload["s3_url"]
                                    )
                                    s3_upload_results["drl"] = drl_upload
                                    print(f"✓ DRL uploaded to S3: {drl_upload['s3_url']}")
                                    
                                    # Clean up temp DRL file
                                    try:
                                        os.unlink(drl_path)
                                        print(f"✓ Temporary DRL file deleted")
                                    except Exception as e:
                                        print(f"Warning: Could not delete temp DRL file: {e}")
                            
                            result["steps"]["s3_upload"] = s3_upload_results
                    
                    # Step 5: Log deployment history for audit trail
                    db_service.log_deployment_history(
                        container_id=container_id,
                        bank_id=normalized_bank,
                        policy_type_id=normalized_type,
                        action="updated",
                        version=new_version,
                        changes_description="Rules updated via /api/v1/policies/update-rules endpoint"
                    )
                    
                    print(f"✓ Deployment history logged")
                    result["steps"]["update_container"] = {
                        "status": "success",
                        "new_version": new_version
                    }
                    
                except Exception as e:
                    print(f"⚠ Failed to update container metadata: {e}")
                    result["steps"]["update_container"] = {
                        "status": "error",
                        "message": str(e)
                    }
                    # Don't fail the whole request if metadata update fails
            else:
                print(f"✗ Redeployment failed: {deployment_result.get('message', 'Unknown error')}")
                result["status"] = "partial"
                result["error"] = deployment_result.get('message', 'Redeployment failed')
                return jsonify(result), 500
                
        except Exception as e:
            print(f"✗ Error redeploying rules: {e}")
            import traceback
            traceback.print_exc()
            result["steps"]["redeployment"] = {
                "status": "error",
                "message": str(e)
            }
            result["status"] = "failed"
            result["error"] = str(e)
            return jsonify(result), 500
        
        result["status"] = "completed"
        print("\n" + "="*60)
        print("✓ Rules update completed successfully!")
        print("="*60)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"✗ Error in update_policy_rules: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route(ROUTE + '/api/v1/policies/update-hierarchical-rules', methods=['POST', 'OPTIONS'])
def update_hierarchical_rules():
    """
    Update hierarchical rules fields (expected, actual, confidence, passed, etc.)
    
    This endpoint allows you to update validation fields in hierarchical rules without
    regenerating the entire rule tree. Useful for:
    - Setting expected values after rule creation
    - Recording actual values from evaluations
    - Updating confidence scores
    - Setting pass/fail status
    - Modifying descriptions or names
    
    Supports batch updates and partial field updates.
    
    **NEW: Optional DRL Update**
    Set "update_drl": true to also regenerate and redeploy DRL rules based on updated
    expected values. This makes hierarchical rules the source of truth for rule logic.
    
    Request body:
    {
        "bank_id": "chase",
        "policy_type": "insurance",
        "update_drl": false,  // Optional: set to true to also update DRL rules
        "updates": [
            {
                "rule_id": "1.1",  // or "id": 42 for database ID
                "expected": "Age >= 18",
                "actual": "Age = 25",
                "confidence": 0.95,
                "passed": true
            }
        ]
    }
    """
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON body is required'}), 400
        
        # Validate required fields
        if 'bank_id' not in data:
            return jsonify({'error': 'bank_id is required'}), 400
        
        if 'policy_type' not in data:
            return jsonify({'error': 'policy_type is required'}), 400
        
        if 'updates' not in data or not isinstance(data['updates'], list):
            return jsonify({'error': 'updates array is required'}), 400
        
        if len(data['updates']) == 0:
            return jsonify({'error': 'updates array cannot be empty'}), 400
        
        bank_id = data['bank_id']
        policy_type = data['policy_type']
        updates = data['updates']
        update_drl = data.get('update_drl', False)  # Optional: also update DRL rules
        
        # Normalize IDs (same as other endpoints)
        normalized_bank = bank_id.lower().strip().replace(' ', '-')
        normalized_type = policy_type.lower().strip().replace(' ', '-')
        container_id = f"{normalized_bank}-{normalized_type}-underwriting-rules"
        
        print(f"\n{'='*60}")
        print(f"Update Hierarchical Rules Request")
        print(f"Bank: {normalized_bank}, Policy: {normalized_type}")
        print(f"Updates: {len(updates)} rules")
        print(f"Update DRL: {update_drl}")
        print(f"{'='*60}")
        
        # Verify container exists (optional check, but good for validation)
        container = db_service.get_active_container(normalized_bank, normalized_type)
        if not container and update_drl:
            return jsonify({
                "status": "error",
                "message": f"No active container found for bank '{bank_id}' and policy type '{policy_type}'. Cannot update DRL without container."
            }), 404
        
        # Update hierarchical rules in database
        result = db_service.update_hierarchical_rules(
            bank_id=normalized_bank,
            policy_type_id=normalized_type,
            updates=updates
        )
        
        # Build response
        response = {
            "status": "success" if result['updated_count'] > 0 else "no_updates",
            "bank_id": normalized_bank,
            "policy_type": normalized_type,
            "updated_count": result['updated_count'],
            "updated_ids": result['updated_ids']
        }
        
        # Include errors if any occurred
        if result['errors']:
            response["errors"] = result['errors']
            response["error_count"] = len(result['errors'])
            if result['updated_count'] == 0:
                response["status"] = "failed"
                response["message"] = "All updates failed. See errors for details."
            else:
                response["status"] = "partial"
                response["message"] = f"Updated {result['updated_count']} rules, but {len(result['errors'])} failed."
        
        print(f"✓ Updated {result['updated_count']} hierarchical rules in database")
        if result['errors']:
            print(f"⚠ {len(result['errors'])} updates failed")
        
        # If update_drl is requested, regenerate and redeploy DRL rules
        if update_drl and result['updated_count'] > 0:
            try:
                print("\n" + "="*60)
                print("Step 2: Regenerating DRL from updated hierarchical rules...")
                print("="*60)
                
                # Get all hierarchical rules (with updates applied)
                hierarchical_rules = db_service.get_hierarchical_rules(
                    bank_id=normalized_bank,
                    policy_type_id=normalized_type,
                    active_only=True
                )
                
                if not hierarchical_rules:
                    response["drl_update"] = {
                        "status": "skipped",
                        "message": "No hierarchical rules found to convert to DRL"
                    }
                else:
                    # Convert hierarchical rules to DRL
                    from HierarchicalToDRLConverter import HierarchicalToDRLConverter
                    converter = HierarchicalToDRLConverter()
                    drl_content = converter.convert_to_drl(hierarchical_rules)
                    
                    print(f"✓ Generated DRL with {len(drl_content.splitlines())} lines")
                    
                    # Redeploy using existing deployment infrastructure
                    print("\n" + "="*60)
                    print("Step 3: Redeploying DRL rules to Drools...")
                    print("="*60)
                    
                    deployment_result = underwritingWorkflow.drools_deployment.deploy_rules_automatically(
                        drl_content=drl_content,
                        container_id=container_id
                    )
                    
                    response["drl_update"] = deployment_result
                    
                    if deployment_result["status"] == "success":
                        print(f"✓ DRL rules redeployed successfully")
                        
                        # Update container version
                        current_version = container.get('version', 1)
                        new_version = current_version + 1
                        
                        db_service.update_container_version(
                            container_id=container_id,
                            version=new_version
                        )
                        
                        response["new_version"] = new_version
                        print(f"✓ Container version updated to {new_version}")
                        
                        # Upload new artifacts to S3 if available
                        if "steps" in deployment_result:
                            build_step = deployment_result["steps"].get("build", {})
                            if build_step.get("status") == "success":
                                jar_path = build_step.get("jar_path")
                                drl_path = deployment_result["steps"].get("save_drl", {}).get("path")
                                version_str = deployment_result["release_id"]["version"]
                                
                                s3_upload_results = {}
                                
                                # Upload JAR
                                if jar_path and os.path.exists(jar_path):
                                    jar_upload = s3Service.upload_jar_to_s3(jar_path, container_id, version_str)
                                    if jar_upload["status"] == "success":
                                        db_service.update_container_urls(container_id, s3_jar_url=jar_upload["s3_url"])
                                        s3_upload_results["jar"] = jar_upload
                                        os.unlink(jar_path)
                                
                                # Upload DRL
                                if drl_path and os.path.exists(drl_path):
                                    drl_upload = s3Service.upload_drl_to_s3(drl_path, container_id, version_str)
                                    if drl_upload["status"] == "success":
                                        db_service.update_container_urls(container_id, s3_drl_url=drl_upload["s3_url"])
                                        s3_upload_results["drl"] = drl_upload
                                        os.unlink(drl_path)
                                
                                if s3_upload_results:
                                    response["drl_update"]["s3_upload"] = s3_upload_results
                        
                        # Log deployment history
                        db_service.log_deployment_history(
                            container_id=container_id,
                            bank_id=normalized_bank,
                            policy_type_id=normalized_type,
                            action="updated",
                            version=new_version,
                            changes_description="DRL rules regenerated from updated hierarchical rules"
                        )
                        
                        print(f"✓ Deployment history logged")
                    else:
                        print(f"✗ DRL redeployment failed: {deployment_result.get('message', 'Unknown error')}")
                        response["status"] = "partial"
                        response["message"] = f"Hierarchical rules updated, but DRL redeployment failed: {deployment_result.get('message')}"
            
            except Exception as drl_error:
                print(f"✗ Error updating DRL: {drl_error}")
                import traceback
                traceback.print_exc()
                response["drl_update"] = {
                    "status": "error",
                    "message": str(drl_error)
                }
                response["status"] = "partial"
                response["message"] = f"Hierarchical rules updated, but DRL update failed: {str(drl_error)}"
        
        status_code = 200
        if response["status"] == "failed":
            status_code = 400
        elif response["status"] == "partial":
            status_code = 207  # Multi-Status
        
        return jsonify(response), status_code
        
    except Exception as e:
        print(f"✗ Error in update_hierarchical_rules: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route(ROUTE + '/api/v1/evaluate-policy', methods=['POST', 'OPTIONS'])
def evaluate_policy():
    """
    Evaluate a policy application using deployed rule engine

    This is the main customer-facing endpoint for evaluating applications
    """
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'JSON body is required'}), 400

        # Validate required fields
        if 'bank_id' not in data:
            return jsonify({'error': 'bank_id is required'}), 400

        if 'policy_type' not in data:
            return jsonify({'error': 'policy_type is required'}), 400

        if 'applicant' not in data:
            return jsonify({'error': 'applicant data is required'}), 400

        bank_id = data['bank_id']
        policy_type = data['policy_type']
        applicant = data['applicant']
        policy_data = data.get('policy', {})

        # Get the active container for this bank+policy
        container = db_service.get_active_container(bank_id, policy_type)

        if not container:
            return jsonify({
                "status": "error",
                "message": f"No active rules deployed for bank '{bank_id}' and policy type '{policy_type}'. Please deploy rules first."
            }), 404

        print(f"DEBUG: Container retrieved from DB - ID: {container['container_id']}, Status: {container['status']}, Health: {container['health_status']}")

        # If container appears unhealthy, try to get fresh endpoint (which triggers health check)
        if container['status'] != 'running' or container['health_status'] != 'healthy':
            print(f"DEBUG: Container appears unhealthy, running fresh health check via orchestrator...")
            from ContainerOrchestrator import ContainerOrchestrator
            orchestrator = ContainerOrchestrator()
            fresh_endpoint = orchestrator.get_container_endpoint(container['container_id'])

            if fresh_endpoint:
                print(f"DEBUG: Health check PASSED! Endpoint: {fresh_endpoint}")
                # Refresh container data from database after health check
                container = db_service.get_active_container(bank_id, policy_type)
                print(f"DEBUG: Refreshed container - Status: {container['status']}, Health: {container['health_status']}")
            else:
                print(f"DEBUG: Health check FAILED - container not responsive")
                return jsonify({
                    "status": "error",
                    "message": f"Rule container is not healthy. Status: {container['status']}, Health: {container['health_status']}"
                }), 503

        # Prepare request for Drools
        container_path = f"/kie-server/services/rest/server/containers/instances/{container['container_id']}"

        # Build the payload for Drools
        request_payload = {
            "applicant": applicant,
            "policy": policy_data
        }

        import time
        start_time = time.time()

        # Invoke the rule engine
        try:
            decision = droolsService.invokeDecisionService(container_path, request_payload)
            execution_time = int((time.time() - start_time) * 1000)  # ms

            # Log the request to database for analytics
            db_service.log_request({
                'container_id': container['id'],
                'bank_id': bank_id,
                'policy_type_id': policy_type,
                'endpoint': container_path,
                'http_method': 'POST',
                'request_payload': request_payload,
                'response_payload': decision,
                'execution_time_ms': execution_time,
                'status': 'success',
                'status_code': 200
            })

            # Map Drools decision to hierarchical rules
            hierarchical_rules_result = None
            try:
                # Get hierarchical rules from database
                hierarchical_rules = db_service.get_hierarchical_rules(
                    bank_id=bank_id,
                    policy_type_id=policy_type,
                    active_only=True
                )

                if hierarchical_rules:
                    # Map Drools decision data to hierarchical rules
                    # This uses Drools as the source of truth (no re-evaluation)
                    mapper = DroolsHierarchicalMapper()
                    mapped_rules = mapper.map_drools_to_hierarchical_rules(
                        hierarchical_rules=hierarchical_rules,
                        drools_decision=decision,
                        applicant_data=applicant,
                        policy_data=policy_data
                    )

                    # Get evaluation summary
                    evaluation_summary = mapper.get_evaluation_summary(mapped_rules)

                    hierarchical_rules_result = {
                        "rules": mapped_rules,
                        "summary": evaluation_summary
                    }

                    print(f"✓ Mapped {evaluation_summary['total_rules']} hierarchical rules from Drools decision")
            except Exception as map_error:
                print(f"⚠ Failed to map hierarchical rules: {map_error}")
                import traceback
                traceback.print_exc()
                # Don't fail the request if hierarchical rules mapping fails

            response = {
                "status": "success",
                "bank_id": bank_id,
                "policy_type": policy_type,
                "container_id": container['container_id'],
                "decision": decision,
                "execution_time_ms": execution_time
            }

            # Add hierarchical rules if available
            if hierarchical_rules_result:
                response["hierarchical_rules"] = hierarchical_rules_result["rules"]
                response["rule_evaluation_summary"] = hierarchical_rules_result["summary"]

            return jsonify(response)

        except Exception as rule_error:
            execution_time = int((time.time() - start_time) * 1000)

            # Log the error
            db_service.log_request({
                'container_id': container['id'],
                'bank_id': bank_id,
                'policy_type_id': policy_type,
                'endpoint': container_path,
                'http_method': 'POST',
                'request_payload': request_payload,
                'execution_time_ms': execution_time,
                'status': 'error',
                'status_code': 500,
                'error_message': str(rule_error)
            })

            return jsonify({
                "status": "error",
                "message": f"Error executing rules: {str(rule_error)}"
            }), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route(ROUTE + '/api/v1/deployments', methods=['GET'])
def list_deployments():
    """List all rule deployments (admin endpoint)"""
    try:
        bank_id = request.args.get('bank_id')
        policy_type = request.args.get('policy_type')
        status = request.args.get('status')
        active_only = request.args.get('active_only', 'false').lower() == 'true'

        containers = db_service.list_containers(
            bank_id=bank_id,
            policy_type_id=policy_type,
            status=status,
            active_only=active_only
        )

        return jsonify({
            "status": "success",
            "total": len(containers),
            "deployments": [{
                "id": c['id'],
                "container_id": c['container_id'],
                "bank_id": c['bank_id'],
                "policy_type_id": c['policy_type_id'],
                "endpoint": c['endpoint'],
                "status": c['status'],
                "health_status": c['health_status'],
                "platform": c['platform'],
                "version": c['version'],
                "is_active": c['is_active'],
                "deployed_at": c['deployed_at'],
                "s3_jar_url": c['s3_jar_url'],
                "s3_drl_url": c['s3_drl_url'],
                "s3_excel_url": c['s3_excel_url']
            } for c in containers]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route(ROUTE + '/api/v1/deployments/<int:deployment_id>', methods=['GET'])
def get_deployment(deployment_id):
    """Get details of a specific deployment"""
    try:
        container = db_service.get_container_by_db_id(deployment_id)

        if not container:
            return jsonify({
                "status": "not_found",
                "message": f"Deployment {deployment_id} not found"
            }), 404

        # Get statistics
        stats = db_service.get_container_stats(container['container_id'])

        deployment_data = {
            "id": container['id'],
            "container_id": container['container_id'],
            "bank_id": container['bank_id'],
            "policy_type_id": container['policy_type_id'],
            "endpoint": container['endpoint'],
            "status": container['status'],
            "health_status": container['health_status'],
            "platform": container['platform'],
            "port": container['port'],
            "version": container['version'],
            "is_active": container['is_active'],
            "deployed_at": container['deployed_at'],
            "document_hash": container['document_hash'],
            "s3_policy_url": container['s3_policy_url'],
            "s3_jar_url": container['s3_jar_url'],
            "s3_drl_url": container['s3_drl_url'],
            "s3_excel_url": container['s3_excel_url'],
            "s3_test_harness_url": container.get('s3_test_harness_url')
        }

        # Generate pre-signed URLs for all S3 documents
        if container.get('s3_policy_url'):
            policy_presigned = s3Service.generate_presigned_url_from_s3_url(container['s3_policy_url'], expiration=86400)
            if policy_presigned:
                deployment_data["policy_presigned_url"] = policy_presigned

        if container.get('s3_jar_url'):
            jar_presigned = s3Service.generate_presigned_url_from_s3_url(container['s3_jar_url'], expiration=86400)
            if jar_presigned:
                deployment_data["jar_presigned_url"] = jar_presigned

        if container.get('s3_drl_url'):
            drl_presigned = s3Service.generate_presigned_url_from_s3_url(container['s3_drl_url'], expiration=86400)
            if drl_presigned:
                deployment_data["drl_presigned_url"] = drl_presigned

        if container.get('s3_excel_url'):
            excel_presigned = s3Service.generate_presigned_url_from_s3_url(container['s3_excel_url'], expiration=86400)
            if excel_presigned:
                deployment_data["excel_presigned_url"] = excel_presigned

        if container.get('s3_test_harness_url'):
            test_harness_presigned = s3Service.generate_presigned_url_from_s3_url(container['s3_test_harness_url'], expiration=86400)
            if test_harness_presigned:
                deployment_data["test_harness_presigned_url"] = test_harness_presigned

        return jsonify({
            "status": "success",
            "deployment": deployment_data,
            "statistics": stats
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route(ROUTE + '/api/v1/discovery', methods=['GET'])
def service_discovery():
    """Service discovery endpoint - list all banks with their available policies"""
    try:
        result = db_service.get_banks_with_policies()
        return jsonify({
            "status": "success",
            "services": result
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route(ROUTE + '/api/v1/extracted-rules', methods=['GET'])
def get_extracted_rules():
    """Get extracted rules for a specific bank and policy type"""
    try:
        bank_id = request.args.get('bank_id')
        policy_type = request.args.get('policy_type')

        if not bank_id or not policy_type:
            return jsonify({
                "status": "error",
                "message": "Both bank_id and policy_type query parameters are required"
            }), 400

        # Fetch extracted rules from database
        rules = db_service.get_extracted_rules(bank_id, policy_type, active_only=True)

        return jsonify({
            "status": "success",
            "bank_id": bank_id,
            "policy_type": policy_type,
            "rule_count": len(rules),
            "rules": rules
        })
    except Exception as e:
        logger.error(f"Error fetching extracted rules: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route(ROUTE + '/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        db_healthy = db_service.health_check()
        drools_healthy = droolsService.isConnected

        return jsonify({
            "status": "healthy" if (db_healthy and drools_healthy) else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "drools": "connected" if drools_healthy else "disconnected"
        }), 200 if (db_healthy and drools_healthy) else 503
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

# File upload endpoint
@app.route(ROUTE + '/upload_file', methods=['POST', 'OPTIONS'])
def upload_file():
    """
    Upload a file to AWS S3 bucket

    Accepts multipart/form-data with a file field.
    Files are stored in S3 with organized folder structure: uploads/YYYY-MM-DD/filename_timestamp.ext

    Returns:
        - 200: File uploaded successfully with S3 URL
        - 400: Missing file or invalid request
        - 500: Upload failed (S3 error, network error, etc.)
    """
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file provided. Please include a file in the "file" field.',
                'error_code': 'MISSING_FILE'
            }), 400
        
        file = request.files['file']
        
        # Check if file is actually selected
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected. Please select a file to upload.',
                'error_code': 'EMPTY_FILENAME'
            }), 400
        
        # Get optional parameters
        folder = request.form.get('folder', 'uploads')  # Default folder: 'uploads'
        max_file_size = 100 * 1024 * 1024  # 100 MB limit
        
        # Validate folder name (prevent path traversal)
        if '..' in folder or '/' in folder or '\\' in folder:
            return jsonify({
                'status': 'error',
                'message': 'Invalid folder name. Folder cannot contain path separators or ".."',
                'error_code': 'INVALID_FOLDER'
            }), 400
        
        # Read file content
        file_content = file.read()
        file_size = len(file_content)
        
        # Validate file size
        if file_size == 0:
            return jsonify({
                'status': 'error',
                'message': 'File is empty. Please upload a non-empty file.',
                'error_code': 'EMPTY_FILE'
            }), 400
        
        if file_size > max_file_size:
            return jsonify({
                'status': 'error',
                'message': f'File size ({file_size} bytes) exceeds maximum allowed size ({max_file_size} bytes)',
                'error_code': 'FILE_TOO_LARGE',
                'file_size': file_size,
                'max_size': max_file_size
            }), 400
        
        # Get original filename
        original_filename = secure_filename(file.filename)
        
        # Upload to S3
        upload_result = s3Service.upload_file_to_s3(
            file_content=file_content,
            filename=original_filename,
            folder=folder
        )
        
        # Check upload result
        if upload_result.get('status') == 'error':
            return jsonify({
                'status': 'error',
                'message': upload_result.get('message', 'Upload failed'),
                'error': upload_result.get('error', 'Unknown error'),
                'error_code': upload_result.get('error_code', 'UPLOAD_FAILED')
            }), 500
        
        # Return success response
        return jsonify({
            'status': 'success',
            'message': 'File uploaded successfully to S3',
            'data': {
                's3_url': upload_result.get('s3_url'),
                's3_key': upload_result.get('s3_key'),
                'bucket': upload_result.get('bucket'),
                'filename': upload_result.get('filename'),
                'original_filename': upload_result.get('original_filename'),
                'folder': upload_result.get('folder'),
                'file_size': upload_result.get('file_size'),
                'content_type': upload_result.get('content_type')
            }
        }), 200
        
    except Exception as e:
        print(f"Error in upload_file endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'error_code': 'INTERNAL_ERROR'
        }), 500

# Swagger documentation endpoints
@app.route(ROUTE + '/swagger.yaml', methods=['GET'])
def get_swagger_yaml():
    """Serve Swagger YAML specification"""
    return send_from_directory('.', 'swagger.yaml')

@app.route(ROUTE + '/docs', methods=['GET'])
def swagger_ui():
    """Serve Swagger UI HTML page"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Underwriting API Documentation</title>
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui.css">
        <style>
            body { margin: 0; padding: 0; }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-bundle.js"></script>
        <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {
                const ui = SwaggerUIBundle({
                    url: '/rule-agent/swagger.yaml',
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout"
                });
                window.ui = ui;
            };
        </script>
    </body>
    </html>
    """
    return html

print ('Running chat service')

if __name__ == '__main__':
    app.run(debug=True)
