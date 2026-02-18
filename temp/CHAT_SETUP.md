# Prospect Chat Setup Guide

## Quick Start

This guide will help you set up the chat interface for querying your prospect database using Google Gemini.

### Step 1: Get Your Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the API key (starts with `AIza...`)

### Step 2: Configure Your Environment

1. Copy the template file:
   ```powershell
   cp .env.template .env
   ```

2. Open `.env` in your editor and add your API key:
   ```
   GOOGLE_API_KEY='AIzaSy...'  # Paste your actual key here
   GEMINI_MODEL='gemini-2.0-flash-exp'
   ```

3. Save the file

### Step 3: Install Missing Dependencies

Make sure you have the Google Generative AI library:

```powershell
pip install google-generativeai
```

### Step 4: Start the Server

```powershell
python main_server.py
```

You should see:
```
Discovery Agent API Server
Server URL: http://localhost:8080
```

### Step 5: Test the Chat

Open a new terminal and test:

```powershell
python test_chat.py
```

Or use curl:

```powershell
curl -X POST http://localhost:8080/chat -H "Content-Type: application/json" -d '{\"message\": \"What companies do we have in Healthcare?\", \"session_id\": \"test\"}'
```

## What You Can Ask

The chat agent has access to your prospect database and can answer questions about:

### Company Discovery
- "What companies do we have in Healthcare?"
- "Tell me about Company 001"
- "Show me companies in the Northeast region"

### Contact Information
- "Who are the decision makers at Company 001?"
- "Find contacts with title VP at Company 005"
- "Show me economic buyers in Technology companies"

### Intent Signals
- "What are the buying signals for Company 001?"
- "Show me pain points for Company 010"
- "What positioning should I use for Company 015?"

### Lead Qualification
- "What is the BANT score for Company 001?"
- "Show me the most qualified leads"
- "Which opportunities are high priority?"
- "What leads are ready for sales handoff?"

### Pipeline Analysis
- "What are my top 5 opportunities?"
- "Show me urgent leads"
- "Which companies have timelines under 90 days?"

## API Endpoints

### POST /chat
Send a message to the chat agent.

**Request:**
```json
{
  "message": "What are my top qualified leads?",
  "session_id": "user123"
}
```

**Response:**
```json
{
  "response": "Here are your top 5 qualified leads: ...",
  "agent": "prospect_chat",
  "status": "success"
}
```

### GET /health
Check server status.

### GET /agents
List available agents and tools.

### GET /docs
Interactive API documentation (Swagger UI).

## Database Schema

The chat agent queries these tables:

- **accounts** (50 companies): Company details, industry, region, spend
- **contacts** (142 people): Names, titles, roles in decision making
- **opportunities** (102 deals): BANT scores, budgets, timelines
- **insights** (50 records): Buying signals, pain points, positioning
- **spend** (50 records): Ad spend by channel and platform
- **actions** (50 recommendations): Next steps and tactics

## Troubleshooting

### "GOOGLE_API_KEY not configured"
- Make sure you created `.env` (not just `.env.template`)
- Check that your API key is correctly pasted
- Remove quotes if you accidentally added extra ones

### "Database query error"
- Make sure `discover_prospecting_clean.db` exists in the same directory
- Check that the database file is not corrupted

### "Module google.generativeai not found"
- Run: `pip install google-generativeai`

### Chat returns generic answers
- The agent should automatically query the database when you ask about companies
- Try being more specific: "Company 001" instead of "companies"
- Check the terminal logs to see if database queries are executing

## Architecture

```
User → FastAPI (/chat) → prospect_chat.py → Gemini API
                              ↓
                    Database Tools (discovery_db, qualification_db)
                              ↓
                    discover_prospecting_clean.db
```

The chat agent:
1. Detects keywords in your question (company, BANT, qualified, etc.)
2. Queries the database for relevant data
3. Passes the database results to Gemini
4. Gemini formats a natural language response with the actual data

## Next Steps

- **Test different queries**: Try asking about specific companies, BANT scores, buying signals
- **Check data quality**: Use `explore_db.py` to see what's in the database
- **Customize prompts**: Edit `prospect_chat.py` to change the system prompt
- **Add more tools**: Extend the database query methods in `db_tools.py`

## Support

If you encounter issues:
1. Check the server logs in the terminal
2. Verify your `.env` configuration
3. Test the database directly with `explore_db.py`
4. Check API key quota at [Google AI Studio](https://makersuite.google.com/app/apikey)
