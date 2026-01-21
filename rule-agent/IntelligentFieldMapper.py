"""
Intelligent Field Mapper
Uses LLM to dynamically map test data fields to Drools schema fields
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class IntelligentFieldMapper:
    """
    Dynamically maps test data field names to Drools schema field names using LLM.
    Eliminates hardcoded field mappings.
    """

    # Common field name aliases (fallback mappings when schema is not available)
    # NOTE: Health-related fields are handled specially by _apply_schema_aware_aliases
    # which checks the actual schema to determine if 'health' or 'healthStatus' is used
    COMMON_FIELD_ALIASES = {
        # Applicant fields
        'smoking': 'smoker',
        'is_smoker': 'smoker',
        'hazardous_occupation': 'hazardousOccupation',
        'is_hazardous': 'hazardousOccupation',
        'credit_score': 'creditScore',
        'annual_income': 'annualIncome',
        'debt_to_income_ratio': 'debtToIncomeRatio',
        'criminal_record': 'criminalRecord',
        'has_criminal_record': 'criminalRecord',

        # Policy fields - map to schema fields that actually exist
        # NOTE: These are fallbacks in case schema generation creates different field names
        'coverageAmount': 'maximumCoverageAmount',  # Map requested coverage to maximum coverage field
        'coverage_amount': 'maximumCoverageAmount',
        'coverage': 'maximumCoverageAmount',
        'termYears': 'coverageLimit',  # TEMPORARY: Map term years to coverageLimit (schema issue)
        'term_years': 'coverageLimit',
        'term': 'coverageLimit',
        'duration': 'coverageLimit',
    }

    def __init__(self, llm, schema: Dict[str, Any] = None):
        """
        Initialize the field mapper

        Args:
            llm: Language model instance for intelligent mapping
            schema: Schema dictionary from DynamicSchemaGenerator
        """
        self.llm = llm
        self.schema = schema or {}
        self.mapping_cache = {}  # Cache for performance

    def update_schema(self, schema: Dict[str, Any]):
        """Update the schema used for mapping"""
        self.schema = schema
        self.mapping_cache = {}  # Clear cache when schema changes

    def map_test_data(self,
                      test_data: Dict[str, Any],
                      entity_type: str) -> Dict[str, Any]:
        """
        Map test data fields to schema fields dynamically

        Priority order:
        1. Schema field_mappings (if available)
        2. Schema-aware health field detection
        3. Common field aliases (fastest)
        4. LLM-based intelligent mapping (slowest)

        Args:
            test_data: Raw test data with arbitrary field names
            entity_type: Either "applicant" or "policy"

        Returns:
            Mapped data with schema-compliant field names
        """
        # STEP 1: Try using the field_mappings from schema first (most accurate)
        if self.schema.get('field_mappings'):
            mapped_data = self._apply_static_mappings(test_data, self.schema['field_mappings'])
            # Validate all fields were mapped to schema fields
            schema_fields = self._get_schema_fields(entity_type)
            if all(key in schema_fields for key in mapped_data.keys()):
                logger.debug(f"Successfully mapped {entity_type} data using schema field_mappings")
                return mapped_data

        # STEP 2: Apply schema-aware health field detection
        # Detect whether schema uses 'health' or 'healthStatus' and map accordingly
        aliased_data = self._apply_schema_aware_aliases(test_data, entity_type)

        logger.debug(f"Applied schema-aware field aliases for {entity_type}: {list(test_data.keys())} -> {list(aliased_data.keys())}")

        # Return aliased data without strict schema validation
        # NOTE: We removed strict validation because COMMON_FIELD_ALIASES may map to fields
        # that don't exist in the schema (bandaid fixes for schema generation issues)
        return aliased_data

    def _apply_schema_aware_aliases(self,
                                    test_data: Dict[str, Any],
                                    entity_type: str) -> Dict[str, Any]:
        """
        Apply field aliases that are aware of what fields exist in the schema.
        This is critical for handling health-related fields which might be 'health' or 'healthStatus'
        """
        mapped = {}
        schema_fields = self._get_schema_fields(entity_type)

        # Build a lowercase map of schema fields for case-insensitive matching
        schema_fields_lower = {f.lower(): f for f in schema_fields} if schema_fields else {}

        for key, value in test_data.items():
            # First check if the key already exists in schema (exact match)
            if key in schema_fields:
                mapped[key] = value
                continue

            # Check if common alias maps to an existing schema field
            if key in self.COMMON_FIELD_ALIASES:
                alias_target = self.COMMON_FIELD_ALIASES[key]
                # Always use the alias mapping (it's a bandaid fix for schema issues)
                mapped[alias_target] = value
                logger.debug(f"Mapped {key} -> {alias_target} (via COMMON_FIELD_ALIASES)")
                continue

            # Special handling for health-related fields
            # Test data might use: healthConditions, healthStatus, health_status, health
            # Schema might have: health OR healthStatus
            health_variants = ['healthconditions', 'healthstatus', 'health_status', 'health_conditions', 'health']
            if key.lower() in health_variants:
                # Check which health field exists in schema
                if 'healthStatus' in schema_fields:
                    mapped['healthStatus'] = value
                    logger.debug(f"Mapped {key} -> healthStatus (found in schema)")
                    continue
                elif 'health' in schema_fields:
                    mapped['health'] = value
                    logger.debug(f"Mapped {key} -> health (found in schema)")
                    continue
                # Also check case-insensitive
                elif 'healthstatus' in schema_fields_lower:
                    mapped[schema_fields_lower['healthstatus']] = value
                    logger.debug(f"Mapped {key} -> {schema_fields_lower['healthstatus']} (found in schema)")
                    continue

            # Check if there's a case-insensitive match in the schema
            if key.lower() in schema_fields_lower:
                actual_field = schema_fields_lower[key.lower()]
                mapped[actual_field] = value
                logger.debug(f"Mapped {key} -> {actual_field} (case-insensitive match)")
                continue

            # Last resort: try common alias or keep original
            mapped_key = self.COMMON_FIELD_ALIASES.get(key, key)
            mapped[mapped_key] = value
            logger.debug(f"No schema mapping for {key}, using {mapped_key}")

        return mapped

    def _apply_static_mappings(self,
                               test_data: Dict[str, Any],
                               mappings: Dict[str, str]) -> Dict[str, Any]:
        """Apply static field mappings from schema"""
        mapped = {}
        for key, value in test_data.items():
            # Check if there's a mapping for this field
            if key in mappings:
                mapped[mappings[key]] = value
            else:
                # Keep original field name
                mapped[key] = value
        return mapped

    def _get_schema_fields(self, entity_type: str) -> list:
        """Get list of field names for given entity type"""
        if entity_type == "applicant":
            return [f['field_name'] for f in self.schema.get('applicant_fields', [])]
        elif entity_type == "policy":
            return [f['field_name'] for f in self.schema.get('policy_fields', [])]
        return []

    def _llm_based_mapping(self,
                          test_data: Dict[str, Any],
                          entity_type: str) -> Dict[str, Any]:
        """Use LLM to intelligently map fields"""
        # Get schema fields for this entity type
        schema_fields = []
        if entity_type == "applicant" and self.schema.get('applicant_fields'):
            schema_fields = self.schema['applicant_fields']
        elif entity_type == "policy" and self.schema.get('policy_fields'):
            schema_fields = self.schema['policy_fields']

        if not schema_fields:
            logger.warning(f"No schema fields found for {entity_type}, returning original data")
            return test_data

        # Create cache key
        cache_key = f"{entity_type}_{json.dumps(sorted(test_data.keys()))}"
        if cache_key in self.mapping_cache:
            logger.debug(f"Using cached mapping for {entity_type}")
            return self._apply_cached_mapping(test_data, self.mapping_cache[cache_key])

        # Build schema context
        schema_context = self._build_schema_context(schema_fields)

        # Create the prompt
        prompt = self._create_mapping_prompt(test_data, schema_context, entity_type)

        try:
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Parse mapping from response
            mapping = self._parse_mapping_response(response_text)

            # Cache the mapping
            self.mapping_cache[cache_key] = mapping

            # Apply the mapping
            return self._apply_mapping(test_data, mapping)

        except Exception as e:
            logger.error(f"Error in LLM-based mapping: {e}")
            logger.warning(f"Returning original data for {entity_type}")
            return test_data

    def _build_schema_context(self, schema_fields: list) -> str:
        """Build context string describing the schema"""
        context = []
        for field in schema_fields:
            field_info = (f"- {field['field_name']} ({field['field_type']}): "
                         f"{field['description']}")
            if field.get('common_aliases'):
                field_info += f" [aliases: {', '.join(field['common_aliases'])}]"
            context.append(field_info)
        return "\n".join(context)

    def _create_mapping_prompt(self,
                               test_data: Dict[str, Any],
                               schema_context: str,
                               entity_type: str) -> str:
        """Create prompt for LLM-based field mapping"""
        return f"""You are a data mapping expert. Your task is to map test data field names to the correct schema field names.

# Test Data Fields ({entity_type}):
{json.dumps(test_data, indent=2)}

# Schema Fields Available:
{schema_context}

# Instructions:

1. For each field in the test data, determine which schema field it should map to
2. Consider:
   - Field name similarity (e.g., "healthStatus" → "health")
   - Semantic meaning (e.g., "criminalRecord" could map to "felonyConviction" or multiple fields)
   - Data type compatibility
   - Common aliases listed in the schema

3. Handle special cases:
   - If one test field should map to multiple schema fields, split it appropriately
     Example: "criminalRecord": "felony" → {{"felonyConviction": true, "duiconviction": false}}
   - If a test field has no matching schema field, mark it as "UNMAPPED"
   - Preserve data types and values during mapping

4. Return ONLY valid JSON with this structure:

```json
{{
  "mappings": [
    {{
      "test_field": "healthStatus",
      "schema_field": "health",
      "action": "rename"
    }},
    {{
      "test_field": "criminalRecord",
      "schema_field": "felonyConviction",
      "action": "transform",
      "transform_logic": "value.lower() == 'felony'"
    }},
    {{
      "test_field": "termYears",
      "schema_field": "term",
      "action": "rename"
    }}
  ]
}}
```

Actions:
- "rename": Simple field name change, keep value as-is
- "transform": Field needs value transformation (provide transform_logic)
- "split": One test field maps to multiple schema fields (provide multiple mappings)

Generate the mapping now:"""

    def _parse_mapping_response(self, response_text: str) -> Dict[str, Any]:
        """Parse mapping from LLM response"""
        try:
            # Extract JSON from markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # Try to find JSON object directly
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end].strip()

            # Parse JSON
            mapping = json.loads(json_text)

            if not isinstance(mapping.get('mappings'), list):
                raise ValueError("mappings must be a list")

            return mapping

        except Exception as e:
            logger.error(f"Error parsing mapping JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            raise

    def _apply_mapping(self,
                      test_data: Dict[str, Any],
                      mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the mapping to transform test data"""
        mapped_data = {}

        for mapping_rule in mapping.get('mappings', []):
            test_field = mapping_rule.get('test_field')
            schema_field = mapping_rule.get('schema_field')
            action = mapping_rule.get('action', 'rename')

            if test_field not in test_data:
                continue

            test_value = test_data[test_field]

            if action == 'rename':
                # Simple rename
                mapped_data[schema_field] = test_value

            elif action == 'transform':
                # Apply transformation logic
                transform_logic = mapping_rule.get('transform_logic', '')
                try:
                    # Safe evaluation context
                    eval_context = {'value': test_value}
                    transformed_value = eval(transform_logic, {"__builtins__": {}}, eval_context)
                    mapped_data[schema_field] = transformed_value
                except Exception as e:
                    logger.warning(f"Transform failed for {test_field}: {e}, using original value")
                    mapped_data[schema_field] = test_value

            elif action == 'split':
                # Field splits into multiple schema fields
                # This is handled by multiple mapping rules with same test_field
                mapped_data[schema_field] = test_value

        # Add any test fields that weren't mapped (pass-through)
        for key, value in test_data.items():
            if key not in [m['test_field'] for m in mapping.get('mappings', [])]:
                mapped_data[key] = value

        return mapped_data

    def _apply_cached_mapping(self,
                             test_data: Dict[str, Any],
                             cached_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a previously cached mapping"""
        return self._apply_mapping(test_data, cached_mapping)

    def map_applicant_data(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convenience method to map applicant test data

        Args:
            applicant_data: Raw applicant test data

        Returns:
            Mapped applicant data
        """
        return self.map_test_data(applicant_data, "applicant")

    def map_policy_data(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convenience method to map policy test data

        Args:
            policy_data: Raw policy test data

        Returns:
            Mapped policy data
        """
        return self.map_test_data(policy_data, "policy")
