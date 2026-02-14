# Discovery Agent - Complete Setup Guide

## Overview

The **Discovery Agent** is a sales intelligence system powered by Google's Gemini AI that provides real-time access to prospecting data, customer discovery, lead qualification, and BANT scoring. It includes both READ and WRITE capabilities for managing accounts, contacts, opportunities, and insights.

### Key Features

- 🔍 **Customer Discovery**: Search companies by name, industry, region, products
- 📊 **Lead Qualification**: BANT methodology with automatic scoring (0-100 scale)
- 💬 **Natural Language Interface**: Chat-based API using Gemini AI
- 📝 **Database Management**: CREATE and UPDATE companies, contacts, opportunities, insights
- 🎯 **Product Intelligence**: Track current products and products of interest
- 📈 **Pipeline Prioritization**: A/B/C priority buckets based on BANT scores
- 🤖 **Multi-Agent Architecture**: Specialized agents for discovery and lead generation

---

## System Architecture

### Core Components

```
DiscoveryAgent/
├── main.py                     # Main FastAPI application entry point
├── main_server.py              # FastAPI REST API server
├── prospect_chat.py            # Natural language chat interface
├── bootstrap_agent/
│   ├── agent.py                # Root agent orchestrator
│   └── sub_agents/
│       ├── discovery/
│       │   ├── discovery_agent.py     # Customer discovery agent
│       │   └── db_tools.py            # Database access layer (READ + WRITE)
│       └── lead_gen/
│           ├── lead_gen_agent.py      # Lead qualification agent
│           └── qualification_tools.py # BANT scoring + WRITE ops
├── data/
│   └── discover_prospecting_clean.db  # SQLite database (100 companies)
└── .env                        # Configuration file
```

### Agent Capabilities

#### **Discovery Agent** (`discovery_agent`)
- **READ Operations**:
  - Search companies by name, industry, region, customer status
  - Get company details (address, products, spend data)
  - Retrieve contacts and decision makers
  - Analyze buying signals and pain points
- **WRITE Operations** (NEW):
  - `add_new_company()` - Create companies with all 11 fields
  - `update_company_info()` - Update any company field(s)
  - `add_new_contact()` - Create contacts with decision-making roles
  - `update_contact_info()` - Update contact details
  - `add_or_update_insights()` - Manage buying signals, pain points, positioning

#### **Lead Gen Agent** (`lead_gen_agent`)
- **READ Operations**:
  - Get qualified leads with BANT scores
  - Find sales-ready opportunities
  - Prioritize pipeline by score
  - Identify data gaps in BANT components
- **WRITE Operations** (NEW):
  - `create_new_opportunity()` - Auto-calculates BANT score (0-100) and priority (A/B/C)
  - `update_opportunity_details()` - Updates fields and recalculates BANT automatically

---

## Database Structure

### SQLite Database: `discover_prospecting_clean.db`

**Accounts Table** (100 companies):
- Company Name, Parent Company, Industry, Territory/Region
- Street, City, State, Website
- **Existing Customer** (Y/N): 61 customers, 39 prospects
- **Current Products**: For existing customers (Internet, Voice, Video, SDWAN, Business Mobile)
- **Products of Interest**: For prospects

**Contacts Table**:
- Name, Title, Email, Phone
- Company Name (foreign key)
- **Role in Decision Making**: Economic Buyer, Champion, Influencer, End User

**Opportunities Table**:
- Opportunity Name, Company Name, Stage, Est. MRC
- **BANT Components**: Budget, Authority, Need, Timeline (days)
- **BANT Scores**: Budget_Score (0-3), Authority_Score (0-3), Need_Score (0-3), Timeline_Score (0-3)
- **BANT_Score_0to100** (0-100): Weighted average
- **Priority Bucket**: A (High) ≥66.7, B (Medium) ≥33.3, C (Low) <33.3
- **Data Gaps**: Comma-separated list of missing BANT components

**Insights Table**:
- Company Name (foreign key)
- Buying Signals, Pain Points, Recommended Positioning

**Spend Table**:
- Company Name (foreign key)
- Estimated Annual Spend, Digital, Programmatic, TV, Audio, OOH, Search, Social
- Primary Agency

---

## Installation

### Prerequisites

1. **Python 3.12+**
2. **Google Gemini API Key** (get from: https://aistudio.google.com/app/apikey)

### Step 1: Clone/Navigate to Project

```bash
cd C:\Code\ConversationalSalesAgent\DiscoveryAgent
```

### Step 2: Create Virtual Environment

```bash
python -m venv .venv312
.venv312\Scripts\Activate.ps1  # Windows PowerShell
```

### Step 3: Install Dependencies

```bash
pip install google-adk==1.20.0
pip install fastapi uvicorn python-dotenv pandas
pip install google-genai  # For Gemini API
```

**Core Dependencies**:
```
google-adk==1.20.0           # Google Agent Development Kit
fastapi                      # REST API framework
uvicorn                      # ASGI server
python-dotenv                # Environment variable management
pandas                       # Data processing
google-genai                 # Gemini AI integration
```

### Step 4: Configure Environment Variables

Create `.env` file from template:

```bash
cp .env.template .env
```

**Edit `.env`** and add your Gemini API key:

```dotenv
# REQUIRED: Your Gemini API Key
GOOGLE_API_KEY="your-api-key-here"

# Gemini Model (recommended)
GEMINI_MODEL="gemini-2.0-flash-exp"

# Server Configuration
PORT=8080
ENVIRONMENT="dev"
```

### Step 5: Verify Database

Ensure the database exists:

```bash
ls data\discover_prospecting_clean.db
```

If missing, contact the system administrator for the latest database backup.

---

## Running the Application

### Start the Server

```bash
# From DiscoveryAgent directory
.venv312\Scripts\python.exe main_server.py
```

**Expected Output**:
```
============================================================
Discovery Agent API Server
============================================================
Server URL: http://localhost:8080
Health Check: http://localhost:8080/health
API Docs: http://localhost:8080/docs
Agents Endpoint: http://localhost:8080/agents
============================================================

Available Agents:
  - discovery_agent: Customer discovery, intent, company details, contact personas
  - lead_gen_agent: BANT qualification, sales readiness, pipeline prioritization
============================================================

INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

### Verify Server is Running

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get
```

**Response**:
```json
{
  "status": "healthy",
  "message": "Discovery Agent API is running",
  "agents_loaded": true,
  "agent_count": 3
}
```

---

## API Endpoints

### 1. Health Check

**GET** `http://localhost:8080/health`

Returns server status and agent count.

### 2. Interactive API Docs

**GET** `http://localhost:8080/docs`

Opens Swagger UI for testing endpoints interactively in your browser.

### 3. Chat Endpoint (Main Interface)

**POST** `http://localhost:8080/chat`

**Request Body**:
```json
{
  "message": "Show me companies interested in Internet",
  "session_id": "user123"
}
```

**Response**:
```json
{
  "response": "Found 15 companies interested in Internet:\n\n**CloudCore Systems**\n  Industry: Technology\n  Location: 4821 Broadway, Denver, CO\n  Status: Prospect\n  Products of Interest: Internet\n...",
  "agent": "prospect_chat",
  "status": "success"
}
```

### 4. List Available Agents

**GET** `http://localhost:8080/agents`

Returns all sub-agents, their descriptions, and tool counts.

---

## Usage Examples

### PowerShell Examples

#### 1. Find Companies by Product Interest

```powershell
$body = @{
    message = "Show me prospects interested in SDWAN"
    session_id = "demo"
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "http://localhost:8080/chat" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

Write-Host $response.response
```

#### 2. Get Company Address

```powershell
$body = @{
    message = "What is the address for CloudCore Systems?"
    session_id = "demo"
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "http://localhost:8080/chat" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

Write-Host $response.response
```

#### 3. Find Existing Customers with Specific Products

```powershell
$body = @{
    message = "Show me existing customers with Voice"
    session_id = "demo"
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "http://localhost:8080/chat" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

Write-Host $response.response
```

#### 4. Search by Industry

```powershell
$body = @{
    message = "List all Healthcare companies"
    session_id = "demo"
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "http://localhost:8080/chat" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

Write-Host $response.response
```

#### 5. Get BANT Qualification

```powershell
$body = @{
    message = "What is the BANT score for Opportunity 001?"
    session_id = "demo"
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "http://localhost:8080/chat" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

Write-Host $response.response
```

---

## BANT Scoring System

### Automatic Score Calculation

When creating or updating opportunities, the system automatically calculates:

#### Component Scores (0-3 each):

- **Budget Score**:
  - Approved: 3
  - Identified: 2
  - Estimated: 1
  - Unknown: 0

- **Authority Score**:
  - Confirmed: 3
  - Identified: 2
  - Suspected: 1
  - Unknown: 0

- **Need Score**:
  - High: 3
  - Medium: 2
  - Low: 1

- **Timeline Score** (days to close):
  - ≤30 days: 3
  - ≤90 days: 2
  - ≤180 days: 1
  - >180 days: 0

#### Overall BANT Score (0-100):

```
BANT Score = ((Budget + Authority + Need + Timeline) / 12) * 100
```

#### Priority Buckets:

- **A (High)**: BANT Score ≥ 66.7
- **B (Medium)**: BANT Score ≥ 33.3
- **C (Low)**: BANT Score < 33.3

---

## Required Files Checklist

### Essential Files (MUST EXIST):

- ✅ `main_server.py` - FastAPI server entry point
- ✅ `prospect_chat.py` - Natural language chat interface
- ✅ `.env` - Environment configuration with GOOGLE_API_KEY
- ✅ `data/discover_prospecting_clean.db` - SQLite database
- ✅ `bootstrap_agent/agent.py` - Root agent
- ✅ `bootstrap_agent/sub_agents/discovery/discovery_agent.py` - Discovery agent
- ✅ `bootstrap_agent/sub_agents/discovery/db_tools.py` - Database layer
- ✅ `bootstrap_agent/sub_agents/lead_gen/lead_gen_agent.py` - Lead gen agent
- ✅ `bootstrap_agent/sub_agents/lead_gen/qualification_tools.py` - BANT scoring

### Optional Files (for testing/development):

- `test_write_operations.py` - Test CRUD operations
- `test_agent_tools.py` - Test agent functions
- `test_database_tools.py` - Test database queries
- `check_schema.py` - Verify database schema
- `verify_all_products.py` - Validate product data

---

## Troubleshooting

### Issue: "GOOGLE_API_KEY not configured"

**Solution**: Add your API key to `.env` file:
```dotenv
GOOGLE_API_KEY="your-actual-api-key-here"
```

### Issue: Server won't start - "Address already in use"

**Solution**: Kill existing process on port 8080:
```powershell
Get-NetTCPConnection -LocalPort 8080 | ForEach-Object { 
    Stop-Process -Id $_.OwningProcess -Force 
}
```

### Issue: "Rate limit exceeded" (429 error)

**Solution**: Gemini API free tier has limits:
- 20 requests per day for gemini-2.5-flash
- 1,500 requests per day for gemini-2.0-flash-exp (recommended)

Either wait or upgrade to paid tier: https://ai.google.dev/pricing

### Issue: Database not found

**Solution**: Ensure database exists at:
```
DiscoveryAgent/data/discover_prospecting_clean.db
```

### Issue: Import errors

**Solution**: Activate virtual environment:
```powershell
.venv312\Scripts\Activate.ps1
```

And ensure all dependencies are installed:
```bash
pip install google-adk==1.20.0 fastapi uvicorn python-dotenv pandas google-genai
```

---

## Data Management

### Adding New Companies

The agents can now CREATE and UPDATE database records directly through the chat interface:

**Example**: Create a new company
```
"Add a new company called Acme Corp in the Technology industry, 
located at 123 Main Street, Boston, MA. They are a prospect 
interested in Internet and SDWAN."
```

**Example**: Update existing company
```
"Update CloudCore Systems to be an existing customer with 
current products: Internet, Voice, SDWAN"
```

### Field Mapping

Python-style names are automatically mapped to database columns:

- `industry` → `Industry`
- `existing_customer` → `"Existing Customer"`
- `current_products` → `"Current Products"`
- `products_of_interest` → `"Products of Interest"`

---

## API Rate Limits

### Gemini API Free Tier

- **gemini-2.0-flash-exp**: 1,500 requests/day (Recommended)
- **gemini-2.5-flash**: 20 requests/day

### Recommendations

1. Use `gemini-2.0-flash-exp` in `.env` for higher limits
2. Cache frequently accessed data
3. Consider upgrading to paid tier for production use

---

## Security Notes

### .env File

**NEVER commit `.env` to version control!**

The `.gitignore` file includes:
```
.env
.venv312/
__pycache__/
```

### API Key Protection

- Store API keys in `.env` only
- Use environment variables in production
- Rotate keys regularly
- Monitor usage at: https://ai.dev/rate-limit

---

## Next Steps

1. ✅ Start the server: `.venv312\Scripts\python.exe main_server.py`
2. ✅ Open API docs: http://localhost:8080/docs
3. ✅ Test health check: http://localhost:8080/health
4. ✅ Try a chat query: POST to `/chat` endpoint
5. ✅ Explore database: Run `test_database_tools.py`

---

## Support

### Documentation

- Main README: `README.md`
- Setup Guides:
  - `DISCOVERY_AGENT_SETUP.md`
  - `LEAD_GEN_AGENT_SETUP.md`
  - `CHAT_SETUP.md`
  - `GOOGLE_CLOUD_SETUP.md`

### External Resources

- Google ADK Docs: https://google.github.io/adk/
- Gemini API Docs: https://ai.google.dev/gemini-api/docs
- FastAPI Docs: https://fastapi.tiangolo.com/

---

## Version History

- **v1.2.0** (2026-02-14): Added full CRUD operations for agents (CREATE/UPDATE)
- **v1.1.0** (2026-02-14): Enhanced product tracking (Current Products, Products of Interest)
- **v1.0.0** (2026-02-13): Initial release with 100 companies, BANT scoring, chat interface

---

**Server Running?** → Test it: http://localhost:8080/docs 🚀
