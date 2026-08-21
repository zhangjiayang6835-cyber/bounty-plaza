import json

catalog = {
    "schema_version": "agent-bounties/error-recovery-catalog-v1",
    "task_id": "agent-error-recovery-catalog-v1",
    "errors": [
        {
            "code": "release_not_configured",
            "state": "unconfigured",
            "next_action": "configure_release",
            "retry_when": "after_configuration"
        },
        {
            "code": "indexer_agreement_unavailable",
            "state": "pending_agreement",
            "next_action": "retry_indexer_agreement",
            "retry_when": "exponential_backoff_30s"
        },
        {
            "code": "beta_creation_disabled",
            "state": "disabled",
            "next_action": "request_beta_access",
            "retry_when": "manual_intervention"
        },
        {
            "code": "reviewed_profile_unavailable",
            "state": "unreviewed",
            "next_action": "submit_profile_for_review",
            "retry_when": "after_review"
        }
    ]
}

print(json.dumps(catalog, indent=2))