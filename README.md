# GitHub Weekly Summary Workflow

This n8n workflow generates a weekly narrative summary of a GitHub repository's activity using the Claude API and delivers it via email.

## Setup Instructions

1. **Install n8n**: Follow the [n8n installation guide](https://docs.n8n.io/docs/installation/) to set up your n8n instance.
2. **Configure GitHub API Credentials**:
   - Go to the n8n UI and add a new credential of type "GitHub API".
   - Enter your GitHub personal access token.
3. **Configure SMTP Credentials**:
   - Go to the n8n UI and add a new credential of type "SMTP".
   - Enter your SMTP server details and authentication credentials.
4. **Import the Workflow**:
   - In the n8n UI, go to the "Workflows" section.
   - Click on "Import" and select the `github_weekly_summary_workflow.json` file.
5. **Set Environment Variables**:
   - Set the following environment variables in your n8n instance:
     - `GITHUB_REPO`: The GitHub repository you want to generate the summary for.
     - `DESTINATION_EMAIL`: The email address where the summary will be sent.
     - `CLAUDE_API_KEY`: Your Claude API key.
     - `LANGUAGE`: The language for the summary (e.g., "EN" for English, "FR" for French).

## Testing

- Trigger the workflow manually in the n8n UI to test it.
- Check the email to verify that the summary is generated and delivered correctly.

## Notes

- Ensure that the GitHub API and Claude API are accessible and properly configured.
- Adjust the cron expression in the workflow if you want to change the trigger time.
