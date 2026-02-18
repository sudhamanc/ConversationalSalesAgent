# B2B Agentic Sales System - Deployment Guide

## 📋 Overview

This guide provides cost-effective deployment options for our B2B Agentic Sales System (Payment Agent & Service Fulfillment Agent) with support for 5 team members.

**Project Requirements:**
- Deploy Payment Agent and Service Fulfillment Agent
- Support 5 team members for development and testing
- Cost-effective solution for group project
- Easy collaboration and deployment workflow

---

## 🎯 Recommended Deployment Options

### Quick Comparison

| Option | Setup Time | Monthly Cost | Best For | Team Size | Free Credits |
|--------|-----------|--------------|----------|-----------|--------------|
| **Railway.app (Hobby)** ⭐ | 3 min | $5 | Quick deployment, demos | Unlimited via GitHub | $5 trial |
| **Google Cloud (Vertex AI)** | 30 min | $11-35 | Production, native ADK support | 5+ (IAM roles) | $300 (90 days) |
| **Google Cloud Run** | 20 min | $0-20 | API deployment, containers | 5+ (IAM roles) | $300 (90 days) |
| **Azure (Students)** | 40 min | $0 | Student projects | 5+ | $100 (renewable) |
| **Render.com** | 5 min | $0-7 | Side projects | Unlimited via GitHub | Free tier |

---

## 🥇 Option 1: Railway.app (Recommended for Group Projects)

### Overview
**Perfect for:** Quick deployment, demos, and group projects  
**Cost:** $5/month (Hobby tier) - **$1 per person**  
**Setup Time:** 3 minutes  
**Team Support:** Unlimited via GitHub

### Pricing Tiers

#### Free Tier
- **Cost:** $0/month
- **Trial:** 30-day free trial with $5 credits, then $1/month
- **Resources:** Up to 1 vCPU / 0.5 GB RAM per service
- **Storage:** 0.5 GB
- **Best for:** Initial testing and proof of concept

#### Hobby Tier ⭐ **RECOMMENDED**
- **Cost:** $5/month total (NOT per person)
- **Credits:** $5 monthly usage credits included
- **Resources:** Up to 48 vCPU / 48 GB RAM per service
- **Storage:** Up to 5 GB
- **Replicas:** Up to 6 replicas at 8 vCPU / 8 GB RAM each
- **Support:** Community support
- **Workspace:** Single developer workspace (doesn't matter - see workflow below)
- **Best for:** Development, testing, and project presentations

#### Pro Tier
- **Cost:** $20/month
- **Credits:** $20 monthly usage credits included
- **Resources:** Up to 1,000 vCPU / 1 TB RAM per service
- **Storage:** Up to 1 TB
- **Support:** Priority support
- **Workspace:** Unlimited workspace seats
- **Best for:** Production applications and professional teams

### Why Hobby Tier is Perfect for Your Group

✅ **Affordable:** $5/month total = **$1 per person**  
✅ **Sufficient Resources:** 48 GB RAM is way more than needed  
✅ **Easy Setup:** Deploy in 3 minutes from GitHub  
✅ **Team-Friendly:** All 5 people collaborate via GitHub  
✅ **Auto-Deploy:** Automatic deployment on git push  
✅ **No Infrastructure:** Zero DevOps overhead

### Important: Railway Workspace vs. GitHub Collaboration

**Railway's "Single Developer Workspace" Does NOT Limit Team Size!**

Here's how it actually works:

```
┌─────────────────────────────────────────────────────┐
│         GitHub Repository (5 people)                │
│  - All team members commit code here                │
│  - Standard git workflow (branches, PRs, reviews)   │
│  - Full version control and collaboration           │
└─────────────────────┬───────────────────────────────┘
                      │
                      │ (Railway watches this repo)
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│         Railway Deployment (1 account)              │
│  - Automatically deploys from GitHub                │
│  - Only 1 person needs Railway login                │
│  - Provides live URL for everyone to test           │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│         Live Application                            │
│  - All 5 team members can access and test           │
│  - Shared URL: https://your-app.railway.app         │
└─────────────────────────────────────────────────────┘
```

**Key Points:**
- ✅ Code collaboration = **GitHub** (all 5 people have full access)
- ✅ Deployment = **Railway** (only 1 person needs account)
- ✅ Testing = **Live URL** (everyone can access)
- ✅ Railway "workspace" only refers to the Railway dashboard, which you rarely need to access

### Railway Team Workflow

#### Step 1: Initial Setup (One Person - 3 minutes)

**Person 1 (Designated "Deployer"):**

```bash
# 1. Create Railway account
# Go to https://railway.app and sign up with GitHub

# 2. Create new project
# Click "Deploy a new project" → "Deploy from GitHub repo"

# 3. Select your repository
# Choose: your-team/adk-b2b-sales-project

# 4. Railway auto-detects Python and deploys
# No additional configuration needed!

# 5. Get your deployment URL
# Railway provides: https://adk-b2b-sales-production.up.railway.app
```

**Share this URL with all team members for testing.**

#### Step 2: Daily Development (All 5 Team Members)

**Everyone works on GitHub normally:**

```bash
# Clone the repository (all team members)
git clone https://github.com/your-team/adk-b2b-sales-project.git
cd adk-b2b-sales-project

# Create feature branch for your work
git checkout -b feature/payment-validation

# Make your changes
# Edit files, add features, fix bugs...

# Commit your work
git add .
git commit -m "Add credit card validation with Luhn algorithm"

# Push to GitHub
git push origin feature/payment-validation

# Create Pull Request on GitHub
# Request reviews from team members
# After approval, merge to main branch
```

**Railway automatically deploys when code is merged to main!**

```
GitHub: main branch updated
    ↓
Railway: Detects change
    ↓
Railway: Rebuilds application
    ↓
Railway: Deploys automatically
    ↓
Everyone: Tests at live URL
```

#### Step 3: Environment Variables (One Person)

**In Railway Dashboard:**

```bash
# Go to your project → Variables tab
# Add environment variables:

GEMINI_MODEL=gemini-2.5-flash
GOOGLE_API_KEY=your-api-key-here
ENVIRONMENT=production
AGENT_NAME=b2b_sales_agents
```

**These variables are automatically available to your application.**

#### Step 4: Monitoring (Anyone Can Access)

**Share Railway credentials with team or:**
- Monitor via application logs
- Set up health check endpoint
- Use Railway's public metrics

```python
# Add health check to your app
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
```

### Railway Project Structure

```
your-repo/
├── bootstrap_agent/
│   ├── sub_agents/
│   │   ├── payment_agent.py
│   │   └── service_fulfillment_agent.py
│   ├── api_tools/
│   │   └── payment_tools.py
│   └── agent.py
├── main.py                    # FastAPI entry point
├── requirements.txt           # Python dependencies
├── railway.json              # Railway configuration (optional)
└── README.md
```

**railway.json (Optional):**
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python main.py",
    "restartPolicyType": "ON_FAILURE",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300
  }
}
```

### Cost Breakdown (Hobby Tier)

**Monthly Costs:**
```
Base subscription: $5.00
Monthly credits:  -$5.00
─────────────────────────
Included usage:    $0.00

Only pay for usage above $5
```

**Typical Usage (Development):**
- API requests: ~$1-2/month
- Compute time: ~$1-2/month
- Storage: ~$0.50/month
- **Total: $2-4.50/month** (covered by $5 credit)

**Per Person Cost:**
```
$5 ÷ 5 team members = $1 per person per month
```

### Deployment Commands

**Initial Deploy:**
```bash
# Railway auto-deploys from GitHub
# No manual commands needed!
```

**Manual Deploy (if needed):**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy manually
railway up
```

**View Logs:**
```bash
railway logs
```

---

## 🥈 Option 2: Google Cloud Platform - Vertex AI

### Overview
**Perfect for:** Production deployments, native ADK support  
**Cost:** $11-35/month (after free credits)  
**Setup Time:** 30 minutes  
**Team Support:** 5+ users via IAM roles  
**Free Credits:** $300 for 90 days (new accounts)

### Why Choose GCP Vertex AI

✅ **Native ADK Support** - Built specifically for Google ADK  
✅ **$300 Free Credits** - 3+ months free for new accounts  
✅ **Enterprise-Grade** - Production-ready infrastructure  
✅ **Team IAM Roles** - Granular access control for all 5 members  
✅ **Auto-Scaling** - Pay only for what you use  
✅ **Free Tier Included:**
  - Cloud Run: 2 million requests/month free
  - Cloud Storage: 5 GB free
  - Limited free Gemini API usage

### Setup Instructions

#### Step 1: Create GCP Project

```bash
# Install Google Cloud SDK
# Download from: https://cloud.google.com/sdk/docs/install

# Login to GCP
gcloud auth login

# Create new project
gcloud projects create adk-b2b-sales-project --name="B2B Sales Agents"

# Set as default project
gcloud config set project adk-b2b-sales-project

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
```

#### Step 2: Add Team Members

```bash
# Add team member as Editor
gcloud projects add-iam-policy-binding adk-b2b-sales-project \
  --member="user:teammate1@example.com" \
  --role="roles/editor"

# Repeat for all 5 members
gcloud projects add-iam-policy-binding adk-b2b-sales-project \
  --member="user:teammate2@example.com" \
  --role="roles/editor"

# Add as Viewer (read-only access)
gcloud projects add-iam-policy-binding adk-b2b-sales-project \
  --member="user:teammate3@example.com" \
  --role="roles/viewer"
```

#### Step 3: Deploy to Cloud Run

```bash
# Deploy Payment Agent
gcloud run deploy payment-agent \
  --source ./bootstrap_agent \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2 \
  --memory 1Gi \
  --set-env-vars GEMINI_MODEL=gemini-2.5-flash

# Deploy Service Fulfillment Agent
gcloud run deploy service-agent \
  --source ./bootstrap_agent \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2 \
  --memory 1Gi
```

#### Step 4: Get Service URLs

```bash
# Get URLs
gcloud run services list --platform managed

# Output:
# SERVICE           REGION        URL
# payment-agent     us-central1   https://payment-agent-xxx.run.app
# service-agent     us-central1   https://service-agent-xxx.run.app
```

### Monthly Cost Breakdown (After Free Credits)

```
Cloud Run (within free tier):     $0
Gemini API calls (~1000/month):   $10-25
Cloud Storage (< 5GB):            $1-2
Cloud Functions (if used):        $2-5
Networking:                       $1-3
─────────────────────────────────────
Total: $11-35/month
```

**With $300 Free Credits:**
- Lasts approximately 8-12 months at $25-30/month usage
- Perfect for entire semester + summer

### Team Collaboration on GCP

```bash
# Each team member can:
# 1. Access GCP Console: https://console.cloud.google.com
# 2. View deployments, logs, and metrics
# 3. Deploy updates (if Editor role)
# 4. Monitor costs and usage

# Everyone works on GitHub for code
# Anyone can deploy from their machine:
gcloud run deploy payment-agent --source .
```

---

## 🥉 Option 3: Google Cloud Run (Container-Based)

### Overview
**Perfect for:** API deployments, microservices  
**Cost:** $0-20/month  
**Setup Time:** 20 minutes  
**Team Support:** 5+ users via IAM

### Why Choose Cloud Run

✅ **Scales to Zero** - No cost when idle  
✅ **Container-Based** - Full control over environment  
✅ **HTTPS Automatic** - Built-in SSL certificates  
✅ **Pay Per Use** - Only charged for actual requests  
✅ **Free Tier:** 2 million requests/month

### Setup with Docker

**Create Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY bootstrap_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY bootstrap_agent/ ./bootstrap_agent/
COPY main.py .

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "main.py"]
```

**Build and Deploy:**
```bash
# Build container
gcloud builds submit --tag gcr.io/adk-b2b-sales-project/payment-agent

# Deploy to Cloud Run
gcloud run deploy payment-agent \
  --image gcr.io/adk-b2b-sales-project/payment-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 5
```

### Cost Breakdown

```
Free Tier:
  - 2 million requests/month
  - 360,000 GB-seconds/month
  - 180,000 vCPU-seconds/month
  
Beyond Free Tier:
  - Requests: $0.40 per million
  - Memory: $0.0000025 per GB-second
  - CPU: $0.00001 per vCPU-second
  
Typical Cost: $0-20/month for development
```

---

## 🎓 Option 4: Azure (For Students)

### Overview
**Perfect for:** Student projects with free credits  
**Cost:** $0 with student benefits  
**Setup Time:** 40 minutes  
**Team Support:** 5+ users

### Student Benefits

✅ **$100 Azure Credits** (renewable annually)  
✅ **Free Services:** App Service, Azure Functions  
✅ **No Credit Card Required**  
✅ **GitHub Integration**

### Setup Instructions

```bash
# 1. Apply for GitHub Student Developer Pack
# Visit: https://education.github.com/pack

# 2. Activate Azure for Students
# Visit: https://azure.microsoft.com/en-us/free/students/

# 3. Install Azure CLI
# Download from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# 4. Login
az login

# 5. Deploy to Azure Container Apps
az containerapp up \
  --name b2b-sales-agents \
  --resource-group adk-group \
  --location eastus \
  --source .
```

### Cost with Student Credits

```
Monthly Usage: ~$15-25
Student Credits: $100
Duration: 4-6 months free
```

---

## 📊 Detailed Cost Comparison

### Development Phase (3 months)

| Platform | Month 1 | Month 2 | Month 3 | Total | Notes |
|----------|---------|---------|---------|-------|-------|
| **Railway (Hobby)** | $0 (trial) | $5 | $5 | **$10** | Easiest setup |
| **GCP (Vertex AI)** | $0 | $0 | $0 | **$0** | $300 credits |
| **Cloud Run** | $0 | $0-10 | $0-10 | **$0-20** | Free tier likely covers |
| **Azure (Student)** | $0 | $0 | $0 | **$0** | Student credits |
| **Render.com** | $0 | $0 | $0-7 | **$0-7** | Free tier available |

### Production Phase (6 months)

| Platform | Monthly | 6 Months | Best For |
|----------|---------|----------|----------|
| **Railway (Hobby)** | $5 | **$30** | Quick demos |
| **Railway (Pro)** | $20 | $120 | Production apps |
| **GCP (Vertex AI)** | $11-35 | **$66-210** | Enterprise grade |
| **Cloud Run** | $0-20 | **$0-120** | Cost-effective |
| **Azure** | $15-25 | $90-150 | Microsoft ecosystem |

---

## 🎯 Team Workflow Best Practices

### Git Workflow (All Platforms)

```bash
# 1. Feature Branch Development
git checkout -b feature/payment-fraud-detection

# 2. Make changes
# ... code, test, commit ...

# 3. Push to GitHub
git push origin feature/payment-fraud-detection

# 4. Create Pull Request
# Request review from 2 team members

# 5. After approval, merge to main
# Automated deployment triggers

# 6. Test on live URL
# All team members verify changes
```

### Code Review Process

```
Developer A: Creates PR
    ↓
Developer B: Reviews code
    ↓
Developer C: Reviews code
    ↓
(Requires 2 approvals)
    ↓
Merge to main
    ↓
Auto-deploy to production
    ↓
Team tests together
```

### Environment Management

```
Development:
├── Local testing (everyone's machine)
├── Feature branches (individual work)
└── Dev deployment (shared testing)

Production:
└── Main branch → Auto-deploy
```

---

## 💰 Cost-Saving Tips

### 1. Use Free Tiers Wisely

```python
# Implement rate limiting
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

@app.get("/payment/process")
@limiter.limit("60/minute")  # Limit API calls
async def process_payment():
    pass
```

### 2. Scale to Zero When Idle

```yaml
# Cloud Run config
min_instances: 0  # Scale to zero when idle
max_instances: 2  # Limit maximum cost
```

### 3. Use Cheaper Models for Testing

```python
# Development
GEMINI_MODEL = "gemini-1.5-flash"  # Cheaper

# Production
GEMINI_MODEL = "gemini-2.5-flash"  # More capable
```

### 4. Cache API Responses

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache credit checks for 1 hour
credit_cache = {}

def check_credit_score(ein: str):
    if ein in credit_cache:
        cached_time, result = credit_cache[ein]
        if datetime.now() - cached_time < timedelta(hours=1):
            return result
    
    # Make actual API call
    result = actual_credit_check(ein)
    credit_cache[ein] = (datetime.now(), result)
    return result
```

### 5. Monitor Usage

```python
# Add usage tracking
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response
```

---

## 🚀 Quick Start Guide

### For Immediate Deployment (Railway - 3 minutes)

```bash
# 1. Push code to GitHub
git add .
git commit -m "Initial deployment"
git push origin main

# 2. Go to railway.app
# Sign up with GitHub account

# 3. Click "Deploy from GitHub repo"
# Select your repository

# 4. Railway auto-deploys!
# Get your URL: https://your-app.railway.app

# Done! Share URL with team
```

### For Long-Term Project (GCP - 30 minutes)

```bash
# 1. Create GCP account (get $300 credits)
gcloud auth login

# 2. Create project
gcloud projects create adk-b2b-sales

# 3. Deploy
gcloud run deploy payment-agent --source .

# 4. Add team members
gcloud projects add-iam-policy-binding adk-b2b-sales \
  --member="user:teammate@example.com" \
  --role="roles/editor"

# Done! Team has full access
```

---

## 💎 Gemini API Usage Costs

### 🎯 Critical Information: Gemini Costs Are Separate

**Important:** Gemini API costs are **separate** from your deployment platform costs (Railway or GCP). You pay Google for Gemini API usage regardless of where you deploy.

**However**, there are significant differences in pricing and free tiers depending on how you access Gemini.

---

### Two Ways to Access Gemini API

#### Option 1: Google AI Studio (Free Tier) ⭐ **RECOMMENDED**
**Access Method:** `generativelanguage.googleapis.com`  
**Best for:** Development, testing, group projects  
**Works with:** Railway, GCP, Azure, anywhere

#### Option 2: Vertex AI (Pay-as-you-go)
**Access Method:** Vertex AI on Google Cloud  
**Best for:** Production, enterprise applications  
**Works with:** GCP only

---

### Gemini 2.0 Flash Pricing

#### Google AI Studio (Free Tier)

| Feature | Free Tier | Paid Tier |
|---------|-----------|-----------|
| **Rate Limit** | 15 requests/minute | Higher limits |
| **Daily Quota** | 1,500 requests/day | Unlimited |
| | 1 million tokens/day | Unlimited |
| **Monthly Limit** | **~37,500 requests FREE** | Unlimited |
| **Cost** | **$0** ✅ | $0.075 per 1M input tokens |
| | | $0.30 per 1M output tokens |

**Free Tier Calculation:**
```
Daily limit:    1,500 requests
Monthly limit:  ~37,500 requests (FREE)
Token limit:    1M tokens/day = 30M tokens/month (FREE)

Typical agent request:
- Input:  ~500 tokens (user query + context)
- Output: ~300 tokens (agent response)
- Total:  ~800 tokens per request

Free tier effectively covers:
~37,500 requests/month = ~1,250 requests/day
```

#### Vertex AI (GCP Only - No Free Tier)

| Model | Input Cost | Output Cost |
|-------|-----------|-------------|
| **Gemini 2.0 Flash** | $0.075 / 1M tokens | $0.30 / 1M tokens |
| **Gemini 1.5 Flash** | $0.075 / 1M tokens | $0.30 / 1M tokens |
| **Gemini 1.5 Pro** | $1.25 / 1M tokens | $5.00 / 1M tokens |

**Cost Examples (Vertex AI):**

```
Light Development (1,000 requests/month):
─────────────────────────────────────────
Input:  500K tokens × $0.075 = $0.04
Output: 300K tokens × $0.30  = $0.09
Total: $0.13/month

Moderate Usage (10,000 requests/month):
─────────────────────────────────────────
Input:  5M tokens × $0.075 = $0.38
Output: 3M tokens × $0.30  = $0.90
Total: $1.28/month

Heavy Testing (50,000 requests/month):
─────────────────────────────────────────
Input:  25M tokens × $0.075 = $1.88
Output: 15M tokens × $0.30  = $4.50
Total: $6.38/month
```

---

### 📊 Total Cost Comparison: Platform + Gemini

#### Railway + Google AI Studio ⭐⭐

**Infrastructure:**
```
Railway Hobby:          $5.00/month
Railway credits:       -$5.00/month
Net Railway cost:       $0.00 (if under $5 usage)
```

**AI Costs:**
```
Gemini (Free tier):     $0.00/month
  - Up to 37,500 requests/month
  - Up to 30M tokens/month
```

**Total: $0-5/month**
- **Gemini is FREE**
- Only pay for Railway if you exceed $5 usage credits

---

#### GCP Cloud Run + Google AI Studio ⭐⭐⭐ **BEST VALUE**

**Infrastructure:**
```
Cloud Run (free tier):  $0.00/month
  - 2M requests/month free
  - Scales to zero when idle
```

**AI Costs:**
```
Gemini (Free tier):     $0.00/month
  - Up to 37,500 requests/month
```

**Total: $0/month** 🎉
- **Completely FREE for development**
- Both Cloud Run and Gemini within free tiers

---

#### GCP Cloud Run + Vertex AI

**Infrastructure:**
```
Cloud Run (free tier):  $0.00/month
Beyond free tier:       ~$5-15/month
```

**AI Costs:**
```
Gemini via Vertex AI:   $1-13/month
  (depends on usage)
```

**Total: $1-28/month**
- **BUT: Covered by $300 GCP credits!**
- Free for 3-4 months with new GCP account

---

### 💰 Updated Cost Comparison Table

| Deployment | Platform Cost | Gemini Cost | **Total/Month** | Free Duration | Best For |
|------------|---------------|-------------|-----------------|---------------|----------|
| **GCP Run + AI Studio** ⭐⭐⭐ | $0 | **$0** | **$0** | Unlimited | **Development** |
| **Railway + AI Studio** ⭐⭐ | $0-5 | **$0** | **$0-5** | Unlimited | **Easiest Setup** |
| GCP Run + Vertex AI | $0-15 | $1-13 | $1-28 | 3-4 months* | Production |
| Railway + Vertex AI | $0-5 | $1-13 | $1-18 | None | Not recommended |

*With $300 GCP credits for new accounts

---

### 📈 Usage Estimation for Your Project

#### Development Phase (3 months)

**Team Usage:**
- 5 team members
- 50 tests per person per day
- Total: 250 requests/day
- Monthly: 7,500 requests

**Cost with Google AI Studio (Free Tier):**
```
Your usage:       7,500 requests/month
Free tier limit: 37,500 requests/month
Usage percentage: 20%

Gemini Cost: $0/month ✅
```

**You're using only 20% of the free tier!**

```
Your Usage vs Free Tier:
┌─────────────────────────────────────┐
│  7,500/month    ████░░░░░░░░░░ 20%  │
│ 37,500/month    ████████████ 100%  │
└─────────────────────────────────────┘
```

---

#### Demo/Presentation Phase (1 month)

**Heavy Testing:**
- 500 requests/day
- Monthly: 15,000 requests

**Cost with Google AI Studio (Free Tier):**
```
Your usage:       15,000 requests/month
Free tier limit:  37,500 requests/month
Usage percentage: 40%

Gemini Cost: $0/month ✅ (still well within free tier)
```

---

### 🔧 Cost Optimization Strategies

#### 1. Use Free Tier Efficiently

**Stay within free limits with smart rate limiting:**

```python
class GeminiRateLimiter:
    def __init__(self):
        self.daily_requests = 0
        self.daily_tokens = 0
        self.daily_limit_requests = 1500  # Free tier limit
        self.daily_limit_tokens = 1000000  # 1M tokens/day
        
    def can_make_request(self, estimated_tokens: int = 800) -> bool:
        """Check if within free tier limits"""
        if self.daily_requests >= self.daily_limit_requests:
            return False
        if self.daily_tokens + estimated_tokens > self.daily_limit_tokens:
            return False
        return True
    
    def track_request(self, input_tokens: int, output_tokens: int):
        """Track request against daily limits"""
        self.daily_requests += 1
        self.daily_tokens += (input_tokens + output_tokens)
```

#### 2. Implement Request Caching

```python
import hashlib
from datetime import datetime, timedelta

cache = {}

def cached_gemini_request(prompt: str, cache_duration_hours: int = 1):
    """Cache responses to avoid duplicate API calls"""
    
    # Create cache key
    cache_key = hashlib.md5(prompt.encode()).hexdigest()
    
    # Check cache
    if cache_key in cache:
        cached_time, response = cache[cache_key]
        if datetime.now() - cached_time < timedelta(hours=cache_duration_hours):
            return response  # Return cached, no API call
    
    # Make API call only if not cached
    response = model.generate_content(prompt)
    cache[cache_key] = (datetime.now(), response)
    
    return response
```

#### 3. Optimize Prompts (Reduce Tokens)

```python
# ❌ Bad: Long, inefficient prompt (500+ tokens)
prompt = f"""
Please analyze the following customer data and determine 
if they are eligible for our premium service package.
Here is all the customer information we have collected:
Name: {name}
Full Address: {address}
Credit Score: {score}
[... lots more text ...]
"""

# ✅ Good: Concise, focused prompt (50 tokens)
prompt = f"Credit check: EIN {ein}, Score {score}. Approve if >650."
```

**Savings: 10x fewer tokens = 10x cheaper!**

#### 4. Monitor Usage Daily

```python
import logging

def tracked_gemini_request(prompt: str):
    """Track token usage for monitoring"""
    response = model.generate_content(prompt)
    
    # Log usage
    input_tokens = response.usage_metadata.prompt_token_count
    output_tokens = response.usage_metadata.candidates_token_count
    
    logging.info(f"Gemini: {input_tokens} in, {output_tokens} out")
    
    return response
```

---

### 🔐 API Key Setup

#### Google AI Studio (Free - No Credit Card)

```bash
# 1. Get free API key
# Visit: https://aistudio.google.com/app/apikey

# 2. Create API key (instant, no credit card needed)

# 3. Add to your environment
# Railway: Dashboard → Variables → Add Variable
GOOGLE_AI_STUDIO_API_KEY=your_api_key_here

# Or for local testing:
export GOOGLE_AI_STUDIO_API_KEY=your_api_key_here
```

**Code Setup:**
```python
import os
import google.generativeai as genai

# Configure with free API key
api_key = os.environ.get('GOOGLE_AI_STUDIO_API_KEY')
genai.configure(api_key=api_key)

# Use free tier model
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Make request
response = model.generate_content('Your prompt here')
print(response.text)
```

#### Vertex AI (GCP - Requires GCP Project)

```bash
# 1. Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# 2. Set up authentication
gcloud auth application-default login

# 3. Set environment variables
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1
```

**Code Setup:**
```python
import os
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel

# Initialize Vertex AI
aiplatform.init(
    project=os.environ['GCP_PROJECT_ID'],
    location=os.environ['GCP_REGION']
)

# Use Vertex AI model
model = GenerativeModel('gemini-2.0-flash-001')

# Make request
response = model.generate_content('Your prompt here')
print(response.text)
```

---

## 📝 Final Recommendations

### 🏆 BEST OPTION: GCP Cloud Run + Google AI Studio (Free Tier)

**Total Cost: $0/month** ✅

```
Platform: Google Cloud Run (Free Tier)
├── Cost: $0/month
├── Limits: 2M requests/month (more than enough)
├── Features: Auto-scaling, HTTPS, zero when idle
└── Setup time: 30 minutes

Gemini AI: Google AI Studio (Free Tier)
├── Cost: $0/month
├── Limits: 37,500 requests/month (5x your needs)
├── Features: Latest models, no credit card required
└── Setup time: 5 minutes

Total Monthly Cost: $0
Free Duration: Unlimited (both have permanent free tiers)
```

**Perfect For:**
- ✅ Maximum cost savings ($0 forever)
- ✅ Development and testing
- ✅ Group projects
- ✅ Learning and experimentation
- ✅ Demo presentations

**Setup Steps:**
```bash
# 1. Create GCP account (get $300 credits as bonus)
# 2. Get free Gemini API key from AI Studio
# 3. Deploy to Cloud Run (free tier)
# 4. Start building - everything is free!
```

---

### 🥈 RUNNER-UP: Railway Hobby + Google AI Studio (Free Tier)

**Total Cost: $5/month = $1 per person** ⭐

```
Platform: Railway Hobby Tier
├── Cost: $5/month ($1 per person)
├── Credits: $5/month included
├── Features: Auto-deploy, easy setup, team-friendly
└── Setup time: 3 minutes

Gemini AI: Google AI Studio (Free Tier)
├── Cost: $0/month
├── Limits: 37,500 requests/month
├── Features: Same as GCP option
└── Setup time: 5 minutes

Total Monthly Cost: $5 ($1 per person)
Free Duration: Gemini unlimited, Railway ongoing
```

**Perfect For:**
- ✅ Fastest deployment (3 minutes)
- ✅ Teams who want simplicity
- ✅ Worth $1/person for zero DevOps
- ✅ Quick demos and testing

**Why Choose This:**
- Easiest setup in the industry
- Railway auto-deploys from GitHub
- No infrastructure management
- Gemini AI is still FREE

---

### 🥉 ENTERPRISE OPTION: GCP Full Stack (For Impressive Demos)

**Total Cost: $0/month (using $300 credits)**

```
Platform: GCP Cloud Run
├── Cost: $0-15/month (covered by credits)
├── Free tier: 2M requests/month
└── Setup time: 30 minutes

Gemini AI: Vertex AI
├── Cost: $1-13/month (covered by credits)
├── Features: Enterprise-grade, higher limits
└── Production-ready

GCP Credits: $300 for new accounts
├── Duration: 90 days or until credits run out
├── Covers: 3-4 months of full usage
└── Perfect for: Semester project

Total Monthly Cost: $0 (for 3-4 months)
Then: $12-28/month after credits
```

**Perfect For:**
- ✅ Final project presentations
- ✅ Production-quality demos
- ✅ Resume-worthy deployments
- ✅ When you want to impress

---

### 📊 Final Cost Summary for Your Group

#### Option 1: GCP Run + AI Studio (Recommended) ⭐⭐⭐

```
Month 1:     $0 (free tiers)
Month 2:     $0 (free tiers)
Month 3:     $0 (free tiers)
Month 4:     $0 (free tiers)
────────────────────────────
Semester:    $0 total 🎉

Per person:  $0
```

**Why Recommended:**
- Completely free forever
- Professional infrastructure
- Both platform and AI are free
- Great for resumes

---

#### Option 2: Railway + AI Studio ⭐⭐

```
Month 1:     $0 (Railway free trial + free Gemini)
Month 2:     $5 (Railway Hobby + free Gemini)
Month 3:     $5 (Railway Hobby + free Gemini)
Month 4:     $5 (Railway Hobby + free Gemini)
────────────────────────────
Semester:    $15 total

Per person:  $3 total ($0.75/month)
```

**Why Good:**
- Easiest setup (3 minutes)
- Minimal cost ($0.75/person/month)
- Gemini still FREE
- Auto-deploy from GitHub

---

#### Option 3: GCP Full (Best for Final Demo)

```
Month 1:     $0 (using $300 credits)
Month 2:     $0 (using $300 credits)
Month 3:     $0 (using $300 credits)
Month 4:     $0 (using $300 credits)
────────────────────────────
Semester:    $0 total 🎉

After credits: $12-28/month
```

**Why For Demos:**
- Enterprise-grade
- Impressive for presentations
- Production-ready
- Free for full semester

---

### 🎯 Our Specific Recommendation for Your 5-Person Group

**Start with Option 1 (GCP + AI Studio), fallback to Option 2 (Railway) if needed:**

```
Week 1-2: Setup Phase
├── Platform: GCP Cloud Run (free)
├── AI: Google AI Studio (free)
├── Cost: $0
└── Action: Get familiar with both services

Week 3-8: Development Phase
├── If GCP works well: Stay with it ($0)
├── If team wants simpler: Switch to Railway ($5/month)
├── AI: Keep using free AI Studio
└── Cost: $0-5/month

Week 9-12: Demo Phase
├── Platform: Upgrade to GCP full stack if needed
├── AI: Could switch to Vertex AI for demos
├── Use $300 GCP credits
└── Cost: Still $0 (credits cover it)

Total Semester Cost: $0-15
Per Person Cost: $0-3
```

---

### 💡 Pro Tips

**1. Start Free, Upgrade if Needed**
```
Week 1: GCP free tier ($0)
       ↓
Week 4: Still free and working? Great!
       ↓
Week 8: Need easier deployment? 
        Switch to Railway ($5/month)
       ↓
Week 12: Final demo?
         GCP full stack (use $300 credits)
```

**2. Gemini Always Free**
```
Throughout entire project:
└── Use Google AI Studio (free tier)
    ├── 37,500 requests/month
    ├── Your usage: ~7,500/month
    └── Cost: $0 ✅
```

**3. Split Costs Fairly**
```
If using Railway ($5/month):
- Month 1: Person A pays ($5)
- Month 2: Person B pays ($5)
- Month 3: Person C pays ($5)
- Everyone contributes equally!
```

---

### ✅ Final Decision Matrix

**Choose GCP Run + AI Studio if:**
- ✅ You want $0 cost forever
- ✅ Team comfortable with 30-min setup
- ✅ Want professional infrastructure
- ✅ Building resume-worthy project

**Choose Railway + AI Studio if:**
- ✅ You want 3-minute deployment
- ✅ $1/person/month is acceptable
- ✅ Prefer simplicity over cost
- ✅ Want zero DevOps headaches

**Choose GCP Full Stack if:**
- ✅ Final semester project
- ✅ Want impressive demo
- ✅ Need enterprise features
- ✅ Have $300 GCP credits

---

### 🎓 Student Bonus Options

**If ALL 5 members are students:**

```
Option A: GitHub Student Pack → Azure
├── Get $100 Azure credits (renewable)
├── Deploy to Azure Container Apps
├── Use Google AI Studio for Gemini (free)
└── Total cost: $0 for entire year

Option B: Multiple GCP Accounts
├── Each person creates GCP account
├── Each gets $300 credits
├── Total: $1,500 in credits for team!
├── Deploy across multiple projects
└── Free for entire semester + summer
```

---

**Bottom Line: You can build and deploy your entire B2B sales agent system for $0-15 for the whole semester!** 🎉

---

## 🔗 Useful Resources

### Platform Documentation
- [Railway Documentation](https://docs.railway.app/)
- [Google Cloud Run Docs](https://cloud.google.com/run/docs)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)

### Google ADK Resources
- [Google ADK Documentation](https://cloud.google.com/generative-ai/docs/agent-builder)
- [ADK Bootstrap Template](https://github.com/comcast-ixt-aix-ai/ADK-Bootstrap-Template-Repo)
- [Gemini API Pricing](https://ai.google.dev/pricing)

### Free Credit Programs
- [GCP Free Tier](https://cloud.google.com/free)
- [GitHub Student Pack](https://education.github.com/pack)
- [Azure for Students](https://azure.microsoft.com/en-us/free/students/)

### Team Collaboration
- [GitHub Team Workflows](https://docs.github.com/en/organizations/collaborating-with-groups-in-organizations)
- [Git Branching Strategy](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)

---

## ❓ FAQ

### Q: Do all 5 people need accounts on Railway/GCP/Azure?

**A:** 
- **Railway:** No, only 1 person needs a Railway account. Everyone collaborates via GitHub.
- **GCP:** Yes, but only for console access. Only 1 person needs to deploy.
- **Azure:** Same as GCP.

**Everyone always uses GitHub for code collaboration.**

### Q: How do we split the $5 Railway cost?

**A:** 
- Option 1: $1 per person per month
- Option 2: Rotate monthly (different person pays each month)
- Option 3: One person pays, others buy coffee ☕

### Q: What if we exceed the free tier/credits?

**A:**
- **Railway:** You'll be charged for overages. Monitor usage in dashboard.
- **GCP:** $300 credit lasts 3-4 months typically. Set up billing alerts.
- **Azure:** $100 credit lasts 4-6 months. Renew annually with student status.

### Q: Can we switch platforms mid-project?

**A:** Yes! All platforms support standard Docker containers and environment variables. Migration is straightforward.

### Q: Which platform is best for final presentation?

**A:** Google Cloud Platform (Vertex AI) - most impressive for academic/professional presentations due to enterprise-grade infrastructure and native ADK support.

### Q: How do we handle secrets (API keys)?

**A:**
```bash
# Never commit secrets to GitHub!
# Add to .gitignore:
echo ".env" >> .gitignore

# Use platform environment variables:
# Railway: Dashboard → Variables tab
# GCP: gcloud run deploy --set-env-vars KEY=value
# Azure: az containerapp create --secrets KEY=value
```

### Q: What if our app gets too much traffic?

**A:**
- **Railway Hobby:** Upgrade to Pro ($20/month)
- **GCP:** Auto-scales, you just pay more
- **Free tiers:** Set max instances to control costs

---

## 📞 Support

### Getting Help

**Platform Support:**
- Railway: [Community Discord](https://discord.gg/railway)
- GCP: [Stack Overflow](https://stackoverflow.com/questions/tagged/google-cloud-platform)
- Azure: [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/)

**Team Contact:**
- Create issues in your GitHub repo
- Use team Slack/Discord channel
- Schedule weekly sync meetings

---

**Last Updated:** January 2025  
**Version:** 1.0  
**Maintained by:** B2B Sales Agents Team

---

## ✅ Deployment Checklist

Before deploying, ensure:

### Code Preparation
- [ ] All agents tested locally
- [ ] Requirements.txt updated
- [ ] Environment variables documented
- [ ] .gitignore configured (exclude .env files)
- [ ] README.md updated
- [ ] Health check endpoint added

### Platform Setup
- [ ] Account created (Railway/GCP/Azure)
- [ ] Team members added (if applicable)
- [ ] Billing alerts configured
- [ ] Environment variables set
- [ ] Domain/URL noted and shared

### Team Coordination
- [ ] Git workflow agreed upon
- [ ] Code review process established
- [ ] Deployment responsibilities assigned
- [ ] Testing procedures documented
- [ ] Cost splitting agreed upon

### Post-Deployment
- [ ] Application accessible at URL
- [ ] All endpoints tested
- [ ] Logs monitored
- [ ] Performance acceptable
- [ ] Team notified of deployment

---

**Ready to deploy? Choose your platform and follow the quick start guide above!** 🚀
