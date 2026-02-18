# Google Cloud / Vertex AI Setup Instructions

## Prerequisites

To use the Discovery Agent chat functionality, you need:

1. **Google Cloud Account** with billing enabled
2. **Vertex AI API** enabled in your project
3. **Gemini API** access

## Setup Steps

### 1. Set Up Google Cloud Project

```bash
# Create a new project (or use existing)
gcloud projects create YOUR-PROJECT-ID --name="Discovery Agent"

# Set the project as default
gcloud config set project YOUR-PROJECT-ID

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable generativelanguage.googleapis.com
```

### 2. Install Google Cloud SDK

**Windows:**
- Download from: https://cloud.google.com/sdk/docs/install
- Run the installer
- Open a new terminal after installation

**Verify installation:**
```bash
gcloud --version
```

### 3. Authenticate with Google Cloud

```bash
# Login to your Google Cloud account
gcloud auth login

# Set application default credentials (required for ADK)
gcloud auth application-default login

# Set your project
gcloud config set project YOUR-PROJECT-ID
```

### 4. Configure Environment Variables

Copy `.env.template` to `.env` and update:

```bash
# Copy template
copy .env.template .env

# Edit .env file and update:
# - GCP_PROJECT_ID: Your Google Cloud project ID
# - GCP_REGION: Your region (e.g., us-central1)
# - GEMINI_MODEL: Model to use (e.g., gemini-2.0-flash-exp)
```

### 5. Verify Configuration

Test that your credentials are properly configured:

```bash
# Test with Python
python -c "import google.auth; creds, project = google.auth.default(); print(f'Project: {project}')"
```

### 6. Restart the Server

```bash
# Stop the current server (Ctrl+C)
# Restart with updated configuration
python main_server.py
```

## Common Issues

### Issue: "Could not automatically determine credentials"

**Solution:**
```bash
# Re-run application default login
gcloud auth application-default login
```

### Issue: "Vertex AI API has not been used"

**Solution:**
```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Wait a few minutes for API to be fully enabled
```

### Issue: "Permission denied" or "403 Forbidden"

**Solution:**
- Ensure billing is enabled on your project
- Verify your account has necessary permissions:
  - `AI Platform User` role
  - `Vertex AI User` role

```bash
# Add roles to your account
gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
    --member="user:YOUR-EMAIL@gmail.com" \
    --role="roles/aiplatform.user"
```

### Issue: "Model not found" or "Model access denied"

**Solution:**
- Some models require early access approval
- Use publicly available models like:
  - `gemini-1.5-flash`
  - `gemini-1.5-pro`
  - `gemini-2.0-flash-exp` (if you have access)

## Alternative: Use OpenAI or Azure OpenAI

If you don't want to use Google Cloud, you can modify the agents to use OpenAI:

1. Install OpenAI SDK: `pip install openai`
2. Update agent model configuration to use OpenAI models
3. Set `OPENAI_API_KEY` environment variable

## Cost Considerations

**Gemini Models Pricing (approximate):**
- Gemini 1.5 Flash: ~$0.075 per 1M input tokens
- Gemini 1.5 Pro: ~$1.25 per 1M input tokens
- Free tier available: 15 requests per minute

**Tips to minimize costs:**
- Use Flash models for development
- Set request quotas/limits
- Monitor usage in Google Cloud Console

## Testing Without Google Cloud

To test the API endpoints without Google Cloud, you can:

1. Use mock responses (modify the chat endpoint)
2. Test the database tools directly (already working)
3. Use the `/health`, `/agents`, and other GET endpoints

The database functionality works completely offline.

## Need Help?

- Google Cloud Support: https://cloud.google.com/support
- Vertex AI Documentation: https://cloud.google.com/vertex-ai/docs
- ADK Documentation: https://github.com/google/adk
