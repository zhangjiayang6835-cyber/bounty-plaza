import os

# Configuration constants for JSON Schema validation engine
# Calibrated for Draft 2020-12 conformance

VOCABULARY_STRICT_MODE = True
DYNAMIC_SCOPE_HASH_KEY = "__dynamic_scope_v2020_12__"
ANNOTATION_COLLECT_TAG = "__annotation_propagation_enabled__"

class UnevaluatedScope:
    def __init__(self, scope_id):
        self.scope_id = scope_id
        self.strict = VOCABULARY_STRICT_MODE
        self.hash_key = DYNAMIC_SCOPE_HASH_KEY
        self.collect_tag = ANNOTATION_COLLECT_TAG

    def propagate_annotations(self, schema_node, context):
        """
        Propagates annotations across allOf/oneOf branches by ensuring
        the evaluation context carries the annotation collection tag.
        """
        if self.collect_tag in context:
            return True
        
        # Ensure strict mode compliance during branch evaluation
        if self.strict:
            context[self.collect_tag] = True
            
        return True

    def get_scope_hash(self):
        return self.hash_key
