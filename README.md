# GitHub Weekly Summary Workflow

## Setup Instructions

1. Install and set up n8n on your local machine or a server.
2. Import the provided `.json` file into n8n.
3. Set the environment variables `GITHUB_TOKEN` and `CLAUDE_API_KEY`.
4. Configure the GitHub repository and recipient email in the nodes.
5. Run the workflow and verify the output.

## Environment Variables
- `GITHUB_TOKEN`: Your GitHub personal access token.
- `CLAUDE_API_KEY`: Your Claude API key.

## Notes
- The workflow is triggered weekly on Fridays at 5 PM.
- The summary is sent via email to the specified recipient.
- You can modify the workflow to use a Discord/Slack webhook if needed.
