# Gemini API Quota Management Guide

## 🚨 Current Issue: Free Tier Quota Exceeded

Your Gemini API key has exceeded the **free tier quota** for `gemini-2.0-flash`. The error shows:

```
429 RESOURCE_EXHAUSTED
Quota exceeded for metric: generate_content_free_tier_requests
Limit: 0, Model: gemini-2.0-flash
```

## 📊 Gemini API Free Tier Limits (as of Feb 2026)

### gemini-2.0-flash (Newer, Stricter Limits)
- **15 requests per minute (RPM)**
- **1,500 requests per day (RPD)**
- **1 million tokens per minute (TPM)**

### gemini-1.5-flash (Recommended for Free Tier)
- **15 requests per minute (RPM)**
- **1,500 requests per day (RPD)**
- **1 million tokens per minute (TPM)**
- **More stable quota allocation**

### gemini-1.5-pro
- **2 requests per minute (RPM)**
- **50 requests per day (RPD)**
- **Higher quality reasoning**

## ✅ Solutions

### Solution 1: Switch to gemini-1.5-flash (Recommended)

The `1.5-flash` model has more generous free tier quotas and is more stable:

**Step 1**: Edit your `.env` file:
```bash
cd /Users/rbarat738@cable.comcast.com/Documents/GitHub/ConversationalSalesAgent/SuperAgent/server
nano .env
```

**Step 2**: Change the model line:
```bash
# FROM:
GEMINI_MODEL=gemini-2.0-flash

# TO:
GEMINI_MODEL=gemini-1.5-flash
```

**Step 3**: Restart the server:
```bash
pkill -f "python3 main.py"
python3 main.py 2>&1 | tee server.log &
```

### Solution 2: Wait for Quota Reset

Free tier quotas reset:
- **Per-minute quotas**: Reset after ~1 minute
- **Daily quotas**: Reset at midnight Pacific Time (PT)

Current retry advice from API: **Wait 21.9 seconds** before next request

### Solution 3: Upgrade to Paid API (Pay-as-you-go)

**Pricing**: $0.075 per 1M input tokens, $0.30 per 1M output tokens (1.5-flash)

**Benefits**:
- 2,000 requests per minute
- No daily limit
- Higher token limits

**To upgrade**:
1. Visit: https://ai.google.dev/pricing
2. Enable billing in Google Cloud Console
3. API key automatically gets higher limits

### Solution 4: Use Multiple API Keys (Rotation)

If you have multiple Google accounts:

1. Create additional API keys at https://aistudio.google.com/apikey
2. Implement key rotation logic (requires code changes)

## 🔍 Check Your Current Usage

### Monitor Usage Dashboard
Visit: https://ai.dev/rate-limit

This shows:
- Current quota consumption
- Requests per minute/day
- Token usage
- When quotas reset

### Check via API
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash
```

## 🛠 Reducing API Usage

If you continue to hit limits, optimize your usage:

### 1. Reduce Max Output Tokens

Edit `.env`:
```bash
# FROM:
MODEL_MAX_OUTPUT_TOKENS=2048

# TO:
MODEL_MAX_OUTPUT_TOKENS=1024  # Use less tokens per response
```

### 2. Increase Application Rate Limits

Edit `.env` (prevent too many concurrent requests):
```bash
# Current settings (may be too permissive)
RATE_LIMIT_RPM=20
RATE_LIMIT_RPH=200

# More conservative (recommended)
RATE_LIMIT_RPM=10   # Max 10 requests per minute per user
RATE_LIMIT_RPH=100  # Max 100 requests per hour per user
```

### 3. Reduce Temperature (Faster Responses)

Edit `.env`:
```bash
MODEL_TEMPERATURE=0.3  # Lower = faster, more deterministic responses
```

### 4. Disable Sub-Agents During Testing

Edit `.env`:
```bash
ENABLE_SUB_AGENTS=false  # Fewer LLM calls per request
```

## 📈 Recommended Configuration for Free Tier

For optimal free tier usage, use this `.env` configuration:

```bash
# Use 1.5-flash for better free tier quotas
GEMINI_MODEL=gemini-1.5-flash

# Conservative token usage
MODEL_MAX_OUTPUT_TOKENS=1024
MODEL_TEMPERATURE=0.5

# Application rate limiting (10 RPM to stay under 15 RPM API limit)
RATE_LIMIT_RPM=10
RATE_LIMIT_RPH=100
RATE_LIMIT_BURST=3

# Keep sub-agents enabled (they're valuable)
ENABLE_SUB_AGENTS=true
```

## 🚀 Quick Fix Command

Run this to switch to gemini-1.5-flash and restart:

```bash
cd /Users/rbarat738@cable.comcast.com/Documents/GitHub/ConversationalSalesAgent/SuperAgent/server

# Update .env file
sed -i.bak 's/GEMINI_MODEL=gemini-2.0-flash/GEMINI_MODEL=gemini-1.5-flash/' .env

# Restart server
pkill -f "python3 main.py"
sleep 2
python3 main.py 2>&1 | tee server.log &
```

## 📚 Additional Resources

- **Rate Limits Documentation**: https://ai.google.dev/gemini-api/docs/rate-limits
- **Usage Monitoring**: https://ai.dev/rate-limit
- **Pricing Calculator**: https://ai.google.dev/pricing
- **API Key Management**: https://aistudio.google.com/apikey
- **ADK Error Handling**: https://google.github.io/adk-docs/agents/models/#error-code-429-resource_exhausted

## 🔔 Next Steps

1. ✅ **Immediate**: Switch to `gemini-1.5-flash` in your `.env` file
2. ✅ **Monitor**: Check https://ai.dev/rate-limit to see your usage
3. ✅ **Optimize**: Reduce `MODEL_MAX_OUTPUT_TOKENS` if needed
4. ⚠️ **Consider**: Upgrading to paid tier if you need higher limits

---

**Last Updated**: February 16, 2026
