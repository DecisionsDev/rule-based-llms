# Deterministic Rule Generation Guide

## Problem Statement

When generating Drools rules from the same policy document multiple times, you want to ensure that you get the **exact same set of rules** every time, regardless of how many times you run the generation process.

## Current Non-Deterministic Factors

The rule generation process currently has several sources of non-determinism:

### 1. **LLM Temperature/Sampling** (PRIMARY ISSUE)
The LLM uses random sampling which produces different outputs each time:

**Current Configuration:**
- Ollama: No explicit temperature setting (defaults to ~0.7-0.8)
- Watsonx: Uses "greedy" decoding but limited tokens may cause variation
- LLMs are inherently probabilistic and will generate different text even with the same input

**Impact:** Even with identical policy documents, the LLM will generate slightly different:
- Rule names
- Condition expressions
- Comments and explanations
- Variable names
- Rule ordering

### 2. **Timestamp-Based Versioning**
```python
# DroolsDeploymentService.py:82
if not version:
    version = datetime.now().strftime("%Y%m%d.%H%M%S")
```
**Impact:** Each deployment gets a unique timestamp version, making it impossible to detect duplicate deployments.

### 3. **No Content Hashing/Fingerprinting**
The system doesn't track what policy document was used to generate which rules.

**Impact:** You can't detect if the same policy document has already been processed.

### 4. **No Rule Deduplication**
No mechanism exists to check if identical rules already exist before deploying.

---

## Solution: Multi-Layered Deterministic Approach

To achieve truly deterministic rule generation, implement these strategies:

---

## Solution 1: **Set LLM Temperature to 0** (RECOMMENDED - Quick Fix)

### What is Temperature?

Temperature controls randomness in LLM outputs:
- **Temperature = 0**: Deterministic, always picks the most likely token (greedy decoding)
- **Temperature > 0**: Random sampling, different outputs each time
- **Temperature = 1**: Full randomness

### Implementation

#### For Ollama (CreateLLMLocal.py)

```python
# CreateLLMLocal.py
from langchain_community.llms import Ollama
import os

def createLLMLocal():
    ollama_server_url = os.getenv("OLLAMA_SERVER_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL_NAME", "mistral")

    print("Using Ollama Server: " + str(ollama_server_url))

    # DETERMINISTIC: Set temperature to 0
    return Ollama(
        base_url=ollama_server_url,
        model=ollama_model,
        temperature=0.0,  # ← Deterministic output
        seed=42           # ← Optional: fixes random seed for complete reproducibility
    )
```

#### For Watsonx (CreateLLMWatson.py)

```python
# CreateLLMWatson.py
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames

def createLLMWatson():
    # ... existing validation code ...

    parameters = {
        GenTextParamsMetaNames.DECODING_METHOD: "greedy",  # Already deterministic
        GenTextParamsMetaNames.MAX_NEW_TOKENS: 4000,       # Increase token limit
        GenTextParamsMetaNames.TEMPERATURE: 0.0,           # ← Explicit temperature = 0
        GenTextParamsMetaNames.RANDOM_SEED: 42,            # ← Optional: reproducible randomness
    }

    llm = ChatWatsonx(
        model_id=watsonx_model,
        url=api_url,
        api_key=api_key,
        project_id=project_id,
        params=parameters
    )
    return llm
```

#### For OpenAI (CreateLLMOpenAI.py)

```python
# CreateLLMOpenAI.py
def createLLMOpenAI():
    api_key = os.getenv("OPENAI_API_KEY")

    return ChatOpenAI(
        api_key=api_key,
        model="gpt-4",
        temperature=0.0,  # ← Deterministic
        seed=42           # ← Optional: OpenAI supports seed for reproducibility
    )
```

### Limitations of Temperature = 0

**Important:** Even with temperature=0, you may still get slight variations due to:
- Model updates by provider (Ollama, OpenAI, etc.)
- Different model versions
- Tokenization differences
- Context window truncation

**Best Practice:** Use temperature=0 + content hashing (Solution 2) for true determinism.

---

## Solution 2: **Content-Based Hashing & Caching** (RECOMMENDED - Production)

Instead of relying on LLM determinism, cache generated rules based on policy document content.

### Architecture

```
Policy Document → Hash (SHA-256) → Check Cache → Generate Rules (if not cached)
                                      ↓
                                   Return Cached Rules (if exists)
```

### Implementation

#### Step 1: Create RuleCacheService

Create a new file: `rule-agent/RuleCacheService.py`

```python
import hashlib
import json
import os
from typing import Dict, Optional
from pathlib import Path

class RuleCacheService:
    """
    Caches generated rules based on policy document content hash
    Ensures identical documents always produce identical rules
    """

    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.getenv("RULE_CACHE_DIR", "/data/rule_cache")
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        print(f"Rule cache initialized at: {self.cache_dir}")

    def compute_document_hash(self, document_content: str, queries: list = None) -> str:
        """
        Compute SHA-256 hash of policy document content

        Args:
            document_content: Full text of the policy document
            queries: Optional list of Textract queries (affects rule generation)

        Returns:
            Hex string hash
        """
        # Normalize content (remove extra whitespace, normalize line endings)
        normalized = ' '.join(document_content.split())

        # Include queries in hash if provided (same doc + different queries = different rules)
        hash_input = normalized
        if queries:
            hash_input += '|' + '|'.join(sorted(queries))

        hash_obj = hashlib.sha256(hash_input.encode('utf-8'))
        return hash_obj.hexdigest()

    def get_cached_rules(self, document_hash: str) -> Optional[Dict]:
        """
        Retrieve cached rules for a document hash

        Args:
            document_hash: SHA-256 hash of the document

        Returns:
            Cached rule data or None if not found
        """
        cache_file = os.path.join(self.cache_dir, f"{document_hash}.json")

        if not os.path.exists(cache_file):
            print(f"Cache miss: {document_hash[:16]}...")
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            print(f"✓ Cache hit: {document_hash[:16]}... (saved: {cached_data.get('timestamp')})")
            return cached_data

        except Exception as e:
            print(f"Error reading cache file: {e}")
            return None

    def cache_rules(self, document_hash: str, rule_data: Dict) -> None:
        """
        Cache generated rules for future use

        Args:
            document_hash: SHA-256 hash of the document
            rule_data: Complete rule generation result (DRL, queries, etc.)
        """
        cache_file = os.path.join(self.cache_dir, f"{document_hash}.json")

        try:
            # Add metadata
            from datetime import datetime
            cache_entry = {
                "document_hash": document_hash,
                "timestamp": datetime.now().isoformat(),
                "rule_data": rule_data
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2)

            print(f"✓ Rules cached: {document_hash[:16]}...")

        except Exception as e:
            print(f"Error caching rules: {e}")

    def clear_cache(self, document_hash: str = None) -> None:
        """
        Clear cached rules

        Args:
            document_hash: Specific hash to clear, or None to clear all
        """
        if document_hash:
            cache_file = os.path.join(self.cache_dir, f"{document_hash}.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)
                print(f"Cleared cache for: {document_hash[:16]}...")
        else:
            # Clear all cache files
            import shutil
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
                print("All cache cleared")

    def list_cached_documents(self) -> list:
        """List all cached document hashes"""
        if not os.path.exists(self.cache_dir):
            return []

        cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        return [f.replace('.json', '') for f in cache_files]


# Singleton instance
_cache_instance = None

def get_rule_cache() -> RuleCacheService:
    """Get singleton instance of RuleCacheService"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RuleCacheService()
    return _cache_instance
```

#### Step 2: Integrate Cache into Workflow

Update `rule-agent/UnderwritingWorkflow.py`:

```python
from RuleCacheService import get_rule_cache

class UnderwritingWorkflow:
    def __init__(self):
        # ... existing initialization ...
        self.rule_cache = get_rule_cache()

    def process_document(self, pdf_path: str, container_id: str = None,
                        use_cache: bool = True) -> Dict:
        """
        Process policy document with caching support

        Args:
            pdf_path: Path to PDF document
            container_id: Container ID for Drools deployment
            use_cache: Whether to use cached rules (default: True)
        """

        # Step 1: Read document
        with open(pdf_path, 'rb') as f:
            document_content = f.read()

        # Step 2: Compute hash
        document_hash = self.rule_cache.compute_document_hash(
            document_content.decode('utf-8', errors='ignore')
        )

        print(f"Document hash: {document_hash[:16]}...")

        # Step 3: Check cache
        if use_cache:
            cached_rules = self.rule_cache.get_cached_rules(document_hash)
            if cached_rules:
                print("✓ Using cached rules (deterministic)")
                return {
                    "status": "success",
                    "source": "cache",
                    "document_hash": document_hash,
                    "rules": cached_rules['rule_data']
                }

        # Step 4: Generate rules (cache miss)
        print("Generating new rules from policy document...")

        # ... existing Textract + LLM generation logic ...
        result = self._generate_rules_from_document(pdf_path, container_id)

        # Step 5: Cache the result
        if result.get("status") == "success":
            self.rule_cache.cache_rules(document_hash, result)

        result["document_hash"] = document_hash
        result["source"] = "generated"

        return result
```

#### Step 3: Add API Endpoints

Update `rule-agent/ChatService.py`:

```python
from RuleCacheService import get_rule_cache

# Add new routes

@app.route('/rule-agent/cache/status', methods=['GET'])
def get_cache_status():
    """Get cache statistics"""
    cache = get_rule_cache()
    cached_docs = cache.list_cached_documents()

    return jsonify({
        "cache_directory": cache.cache_dir,
        "cached_documents": len(cached_docs),
        "document_hashes": cached_docs
    })

@app.route('/rule-agent/cache/clear', methods=['POST'])
def clear_cache():
    """Clear rule cache"""
    data = request.get_json() or {}
    document_hash = data.get('document_hash')

    cache = get_rule_cache()
    cache.clear_cache(document_hash)

    return jsonify({
        "status": "success",
        "message": f"Cache cleared for {document_hash if document_hash else 'all documents'}"
    })

@app.route('/rule-agent/generate_rules', methods=['POST'])
def generate_rules_with_cache():
    """
    Generate rules with caching support

    Request body:
    {
        "pdf_path": "/data/policy.pdf",
        "container_id": "loan-rules",
        "use_cache": true  // Optional, defaults to true
    }
    """
    data = request.get_json()
    pdf_path = data.get('pdf_path')
    container_id = data.get('container_id')
    use_cache = data.get('use_cache', True)

    if not pdf_path or not container_id:
        return jsonify({"error": "pdf_path and container_id required"}), 400

    workflow = UnderwritingWorkflow()
    result = workflow.process_document(pdf_path, container_id, use_cache)

    return jsonify(result)
```

#### Step 4: Environment Configuration

Add to `docker-compose.yml`:

```yaml
backend:
  environment:
    - RULE_CACHE_DIR=/data/rule_cache
  volumes:
    - ./data:/data
    - rule-cache:/data/rule_cache

volumes:
  rule-cache:
```

### Benefits of Content Hashing

✅ **100% Deterministic**: Same document = same hash = same rules
✅ **Fast**: Instant retrieval for previously processed documents
✅ **Version Control**: Can track which documents produced which rules
✅ **Storage Efficient**: Only stores unique rule sets
✅ **Cache Invalidation**: Clear cache for specific documents or all
✅ **Works Across LLM Providers**: Hash-based, independent of LLM behavior

---

## Solution 3: **Version-Based Deployment Prevention**

Prevent duplicate deployments of the same rules by using content-based versioning instead of timestamps.

### Implementation

Update `DroolsDeploymentService.py`:

```python
import hashlib
from datetime import datetime

class DroolsDeploymentService:

    def deploy_rules(self, drl_content: str, container_id: str,
                     group_id: str = "com.underwriting",
                     artifact_id: str = "underwriting-rules",
                     version: str = None) -> Dict:
        """
        Deploy DRL rules with content-based versioning
        """

        # Generate version from DRL content hash if not provided
        if not version:
            # Compute hash of DRL content
            drl_hash = hashlib.sha256(drl_content.encode('utf-8')).hexdigest()[:12]
            version = f"1.0.{drl_hash}"
            print(f"Generated content-based version: {version}")

        # Check if this exact version already exists
        existing_version = self._check_existing_version(container_id, version)
        if existing_version:
            return {
                "status": "already_deployed",
                "message": f"Rules with version {version} already exist (identical content)",
                "container_id": container_id,
                "version": version
            }

        # Proceed with deployment
        # ... rest of deployment logic ...
```

---

## Solution 4: **Structured Rule Templates** (Advanced)

For maximum control, use a two-phase approach:

### Phase 1: Extract Structured Data (Deterministic)
Extract key-value pairs from policy document:

```json
{
  "min_age": 18,
  "max_age": 65,
  "min_coverage": 5000,
  "max_coverage": 100000,
  "min_credit_score": 620,
  "max_dti": 43
}
```

### Phase 2: Template-Based Rule Generation
Use Jinja2 templates to generate rules from structured data:

```python
# RuleTemplateEngine.py
from jinja2 import Template

class RuleTemplateEngine:

    AGE_CHECK_TEMPLATE = """
package com.underwriting.rules;

declare Applicant
    age: int
end

declare Decision
    approved: boolean
    reason: String
end

rule "Age Minimum Check"
    when
        $applicant : Applicant( age < {{ min_age }} )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.setReason("Age below minimum ({{ min_age }})");
        update($decision);
end

rule "Age Maximum Check"
    when
        $applicant : Applicant( age > {{ max_age }} )
        $decision : Decision()
    then
        $decision.setApproved(false);
        $decision.setReason("Age above maximum ({{ max_age }})");
        update($decision);
end
"""

    def generate_age_rules(self, min_age: int, max_age: int) -> str:
        template = Template(self.AGE_CHECK_TEMPLATE)
        return template.render(min_age=min_age, max_age=max_age)
```

**Benefits:**
- 100% deterministic (no LLM involved in final generation)
- Faster generation
- Easier to test and validate
- Consistent code style

---

## Comparison of Solutions

| Solution | Determinism | Speed | Complexity | Flexibility |
|----------|-------------|-------|------------|-------------|
| Temperature=0 | 95% | Fast | Low | High |
| Content Hashing | 100% | Very Fast (cached) | Medium | High |
| Content-Based Versioning | 100% | Fast | Low | High |
| Template-Based | 100% | Very Fast | High | Low |

---

## Recommended Implementation Strategy

### Phase 1: Quick Win (1-2 hours)
1. Set `temperature=0` in all LLM creation functions
2. Add `seed` parameter for complete reproducibility
3. Test with same policy document multiple times

### Phase 2: Production-Ready (4-6 hours)
1. Implement `RuleCacheService` with content hashing
2. Integrate cache into `UnderwritingWorkflow`
3. Add cache management API endpoints
4. Update frontend to show cache status

### Phase 3: Enterprise (Optional)
1. Implement content-based versioning in deployment
2. Add rule deduplication checks
3. Build template-based rule engine for common patterns
4. Add cache expiration policies

---

## Testing Determinism

### Test Script

```python
# test_determinism.py

def test_deterministic_generation():
    """Test that same document produces same rules"""

    policy_path = "/data/sample-loan-policy/catalog/loan-application-policy.txt"

    # Generate rules 5 times
    results = []
    for i in range(5):
        result = workflow.process_document(policy_path, f"test-loan-{i}")
        results.append(result['rules']['drl'])

    # Check if all results are identical
    first_result = results[0]
    for i, result in enumerate(results[1:], 1):
        assert result == first_result, f"Result {i} differs from first result"

    print("✓ All 5 generations produced identical rules")

if __name__ == "__main__":
    test_deterministic_generation()
```

### Expected Output

```
Document hash: a3b5c7d9e1f2a4b6...
Cache miss: a3b5c7d9e1f2a4b6...
Generating new rules from policy document...
✓ Rules cached: a3b5c7d9e1f2a4b6...

Document hash: a3b5c7d9e1f2a4b6...
✓ Cache hit: a3b5c7d9e1f2a4b6... (saved: 2025-01-06T10:30:45)
✓ Using cached rules (deterministic)

[... 3 more cache hits ...]

✓ All 5 generations produced identical rules
```

---

## API Usage Examples

### Generate Rules with Cache

```bash
curl -X POST http://localhost:9000/rule-agent/generate_rules \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_path": "/data/sample-loan-policy/catalog/loan-application-policy.txt",
    "container_id": "loan-underwriting-rules",
    "use_cache": true
  }'
```

### Check Cache Status

```bash
curl http://localhost:9000/rule-agent/cache/status
```

Response:
```json
{
  "cache_directory": "/data/rule_cache",
  "cached_documents": 3,
  "document_hashes": [
    "a3b5c7d9e1f2a4b6c8d0e2f4a6b8c0d2",
    "b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4",
    "c5d7e9f1a3b5c7d9e1f3a5b7c9d1e3f5"
  ]
}
```

### Clear Cache for Specific Document

```bash
curl -X POST http://localhost:9000/rule-agent/cache/clear \
  -H "Content-Type: application/json" \
  -d '{
    "document_hash": "a3b5c7d9e1f2a4b6c8d0e2f4a6b8c0d2"
  }'
```

### Force Regeneration (Bypass Cache)

```bash
curl -X POST http://localhost:9000/rule-agent/generate_rules \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_path": "/data/sample-loan-policy/catalog/loan-application-policy.txt",
    "container_id": "loan-underwriting-rules",
    "use_cache": false
  }'
```

---

## Monitoring and Debugging

### Enable Cache Logging

```python
# Add to RuleCacheService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RuleCacheService:
    def get_cached_rules(self, document_hash: str) -> Optional[Dict]:
        logger.info(f"Cache lookup: {document_hash[:16]}...")
        # ... rest of method ...
```

### View Cache Files

```bash
# List all cached documents
ls -lh /data/rule_cache/

# View specific cached rules
cat /data/rule_cache/a3b5c7d9e1f2a4b6c8d0e2f4a6b8c0d2.json | jq .
```

---

## Conclusion

To achieve deterministic rule generation:

1. **Set temperature=0** for immediate improvement (95% determinism)
2. **Implement content hashing cache** for production (100% determinism)
3. **Use content-based versioning** to prevent duplicate deployments
4. **Consider template-based generation** for critical business rules

The combination of temperature=0 + content hashing provides the best balance of flexibility and determinism for your use case.
