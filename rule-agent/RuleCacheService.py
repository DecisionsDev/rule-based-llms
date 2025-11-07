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
import hashlib
import json
import os
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

class RuleCacheService:
    """
    Caches generated rules based on policy document content hash
    Ensures identical documents always produce identical rules

    This provides 100% deterministic rule generation by caching based on
    document content rather than relying solely on LLM temperature settings.
    """

    def __init__(self, cache_dir: str = None):
        """
        Initialize the rule cache service

        Args:
            cache_dir: Directory to store cache files (defaults to /data/rule_cache)
        """
        self.cache_dir = cache_dir or os.getenv("RULE_CACHE_DIR", "/data/rule_cache")
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        print(f"Rule cache initialized at: {self.cache_dir}")

    def compute_document_hash(self, document_content: str, queries: list = None) -> str:
        """
        Compute SHA-256 hash of policy document content

        The hash is computed from:
        1. Normalized document content (whitespace-normalized)
        2. Optional queries (if provided, affects the hash)

        This ensures that the same document with the same queries always
        produces the same hash, enabling perfect cache hits.

        Args:
            document_content: Full text of the policy document
            queries: Optional list of Textract queries (affects rule generation)

        Returns:
            Hex string hash (64 characters)
        """
        # Normalize content (remove extra whitespace, normalize line endings)
        # This ensures minor formatting differences don't affect the hash
        normalized = ' '.join(document_content.split())

        # Include queries in hash if provided (same doc + different queries = different rules)
        hash_input = normalized
        if queries:
            # Sort queries to ensure order doesn't matter
            hash_input += '|' + '|'.join(sorted(queries))

        # Compute SHA-256 hash
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
            print(f"⚠ Error reading cache file: {e}")
            return None

    def cache_rules(self, document_hash: str, rule_data: Dict) -> None:
        """
        Cache generated rules for future use

        Args:
            document_hash: SHA-256 hash of the document
            rule_data: Complete rule generation result (DRL, queries, extracted data, etc.)
        """
        cache_file = os.path.join(self.cache_dir, f"{document_hash}.json")

        try:
            # Add metadata
            cache_entry = {
                "document_hash": document_hash,
                "timestamp": datetime.now().isoformat(),
                "rule_data": rule_data
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2)

            print(f"✓ Rules cached: {document_hash[:16]}...")

        except Exception as e:
            print(f"⚠ Error caching rules: {e}")

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
                print(f"No cache found for: {document_hash[:16]}...")
        else:
            # Clear all cache files
            import shutil
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
                print("✓ All cache cleared")

    def list_cached_documents(self) -> List[Dict]:
        """
        List all cached document hashes with metadata

        Returns:
            List of dicts with hash, timestamp, and summary info
        """
        if not os.path.exists(self.cache_dir):
            return []

        cached_docs = []
        cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]

        for cache_file in cache_files:
            document_hash = cache_file.replace('.json', '')
            cache_path = os.path.join(self.cache_dir, cache_file)

            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                cached_docs.append({
                    "document_hash": document_hash,
                    "timestamp": cache_data.get("timestamp"),
                    "container_id": cache_data.get("rule_data", {}).get("container_id"),
                    "has_drl": "drl" in cache_data.get("rule_data", {})
                })
            except Exception as e:
                print(f"⚠ Error reading cache file {cache_file}: {e}")

        # Sort by timestamp (newest first)
        cached_docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return cached_docs

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        cached_docs = self.list_cached_documents()

        total_size = 0
        if os.path.exists(self.cache_dir):
            for cache_file in os.listdir(self.cache_dir):
                cache_path = os.path.join(self.cache_dir, cache_file)
                if os.path.isfile(cache_path):
                    total_size += os.path.getsize(cache_path)

        return {
            "cache_directory": self.cache_dir,
            "total_cached_documents": len(cached_docs),
            "total_cache_size_bytes": total_size,
            "total_cache_size_mb": round(total_size / (1024 * 1024), 2)
        }


# Singleton instance
_cache_instance = None

def get_rule_cache() -> RuleCacheService:
    """Get singleton instance of RuleCacheService"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RuleCacheService()
    return _cache_instance
