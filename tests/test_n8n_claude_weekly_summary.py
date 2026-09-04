"""Unit tests for n8n + Claude GitHub Weekly Activity Workflow.
Validates Issue #497 / claude-builders-bounty/claude-builders-bounty#5 ($200 USD).
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def workflow_json():
    path = Path(__file__).parent.parent / "workflows" / "github_weekly_summary_n8n.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_workflow_schema_and_meta(workflow_json):
    assert "name" in workflow_json
    assert "nodes" in workflow_json
    assert "connections" in workflow_json
    assert workflow_json["active"] is True
    assert len(workflow_json["nodes"]) >= 7


def test_cron_trigger_configuration(workflow_json):
    nodes = {n["name"]: n for n in workflow_json["nodes"]}
    assert "Weekly Friday 5PM Cron Trigger" in nodes
    cron_node = nodes["Weekly Friday 5PM Cron Trigger"]
    assert cron_node["type"] == "n8n-nodes-base.scheduleTrigger"
    expr = cron_node["parameters"]["rule"]["interval"][0]["expression"]
    assert expr == "0 17 * * 5"


def test_parameter_configuration_node(workflow_json):
    nodes = {n["name"]: n for n in workflow_json["nodes"]}
    assert "Configure Workflow Parameters" in nodes
    config_node = nodes["Configure Workflow Parameters"]
    values = config_node["parameters"]["values"]["string"]
    var_names = {v["name"] for v in values}
    assert "REPO_OWNER" in var_names
    assert "REPO_NAME" in var_names
    assert "DESTINATION_WEBHOOK_URL" in var_names
    assert "SUMMARY_LANGUAGE" in var_names


def test_github_fetch_nodes_present(workflow_json):
    nodes = {n["name"]: n for n in workflow_json["nodes"]}
    assert "Fetch Weekly GitHub Commits" in nodes
    assert "Fetch Weekly Closed Issues" in nodes
    assert "Fetch Weekly Merged Pull Requests" in nodes

    commits_node = nodes["Fetch Weekly GitHub Commits"]
    assert "api.github.com" in commits_node["parameters"]["url"]
    assert commits_node["parameters"]["method"] == "GET"


def test_claude_api_node_specification(workflow_json):
    nodes = {n["name"]: n for n in workflow_json["nodes"]}
    assert "Generate Narrative Summary with Claude API" in nodes
    claude_node = nodes["Generate Narrative Summary with Claude API"]
    assert claude_node["parameters"]["url"] == "https://api.anthropic.com/v1/messages"
    assert claude_node["parameters"]["method"] == "POST"
    json_body = claude_node["parameters"]["jsonBody"]
    assert "claude-sonnet-4-20250514" in json_body
    assert "max_tokens" in json_body


def test_end_to_end_node_connectivity(workflow_json):
    connections = workflow_json["connections"]
    assert "Weekly Friday 5PM Cron Trigger" in connections
    assert "Configure Workflow Parameters" in connections
    assert "Aggregate Activity and Build Prompt" in connections
    assert "Generate Narrative Summary with Claude API" in connections

    # Verify webhook dispatch node is connected
    claude_targets = connections["Generate Narrative Summary with Claude API"]["main"][0]
    target_nodes = [t["node"] for t in claude_targets]
    assert "Dispatch Summary to Discord/Slack Webhook" in target_nodes
