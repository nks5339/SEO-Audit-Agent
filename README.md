# 🚀 AI SEO Audit Team 

A production-ready SEO audit application powered by AI agents, built with FastAPI, Firecrawl, and LLMs (OpenAI/Anthropic).

## 🎯 Features

- **3-Agent Sequential Workflow**:
  1. **Page Auditor**: Scrapes and analyzes on-page SEO elements using Firecrawl
  2. **SERP Analyst**: Researches competitive landscape via SerpAPI
  3. **Optimization Advisor**: Generates comprehensive, actionable reports

- **Production-Ready Architecture**:
  - FastAPI backend with async/await
  - Modern, responsive UI with Tailwind CSS
  - Comprehensive error handling and logging
  - API documentation (Swagger/ReDoc)
  - Environment-based configuration

- **Multiple LLM Support**:
  - OpenAI (GPT-4o-mini, GPT-4o)
  - Anthropic Claude (Claude 3.5 Sonnet)
  - Easy provider switching via environment variables

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+ (for Firecrawl MCP - optional)
- API Keys:
  - Firecrawl API Key (required) - [Get it here](https://firecrawl.dev)
  - OpenAI API Key OR Anthropic API Key (required)
  - SerpAPI Key (optional, uses mock data if not provided)

## 🛠️ Installation

### 1. Clone or Download

```bash
cd seo_audit_team
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required: Firecrawl API Key
FIRECRAWL_API_KEY=fc-your-api-key-here

# Required: Choose ONE LLM provider
LLM_PROVIDER=openai  # or "anthropic"

# If using OpenAI:
OPENAI_API_KEY=sk-your-openai-key-here

# If using Anthropic:
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Optional: SerpAPI for real search results (uses mock data otherwise)
SERP_API_KEY=your-serpapi-key-here
```

## 🚀 Running the Application

### Development Mode

```bash
# Start the server with auto-reload
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at:
- **Main App**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Production Mode

```bash
# Using gunicorn with uvicorn workers
pip install gunicorn

gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

## 📖 Usage

### Web Interface

1. Open http://localhost:8000 in your browser
2. Enter a website URL (e.g., `https://example.com`)
3. Click "Audit Now"
4. View real-time progress as agents work
5. Explore results in three tabs:
   - **SEO Report**: Comprehensive optimization recommendations
   - **Page Audit**: Detailed on-page analysis
   - **SERP Analysis**: Competitive landscape insights

### API Usage

#### Run SEO Audit

```bash
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Response:
```json
{
  "status": "completed",
  "audit_id": "audit_20241127_143022",
  "page_audit": {
    "audit_results": {...},
    "target_keywords": {...}
  },
  "serp_analysis": {
    "primary_keyword": "...",
    "top_10_results": [...]
  },
  "report": "# SEO Audit Report\n\n...",
  "timestamp": "2024-11-27T14:30:22"
}
```

#### Check System Status

```bash
curl http://localhost:8000/api/status
```

Response:
```json
{
  "api": "operational",
  "firecrawl": "configured",
  "llm_provider": "openai",
  "llm_model": "gpt-4o-mini",
  "llm_configured": true,
  "serp": "configured"
}
```

## 🏗️ Project Structure

```
seo_audit_team/
├── main.py              # FastAPI application entry point
├── api.py               # API routes and agent implementations
├── index.html           # Frontend UI
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── .env                # Environment variables (create this)
└── static/             # Static assets (auto-created)
```

## 🔧 Configuration Options

### LLM Providers

**OpenAI** (default):
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**Anthropic Claude**:
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Model Selection

Edit in `api.py`:
```python
# For OpenAI
LLM_MODEL = "gpt-4o-mini"  # or "gpt-4o", "gpt-4-turbo"

# For Anthropic
LLM_MODEL = "claude-3-5-sonnet-20241022"  # or other Claude models
```

### Firecrawl Configuration

The app uses Firecrawl's cloud API. For self-hosted Firecrawl:

1. Deploy Firecrawl instance
2. Update `api.py`:
```python
FIRECRAWL_API_URL = "https://your-firecrawl-instance.com"
```

## 📊 Agent Workflow Details

### Agent 1: Page Auditor
- Scrapes URL using Firecrawl API
- Extracts title, meta description, headings
- Counts words and links
- Identifies technical SEO issues
- Infers target keywords and search intent

### Agent 2: SERP Analyst
- Searches for primary keyword via SerpAPI
- Analyzes top 10 competitors
- Identifies title patterns and content formats
- Extracts key themes and opportunities
- Finds content gaps

### Agent 3: Optimization Advisor
- Synthesizes audit + SERP data
- Generates prioritized recommendations (P0/P1/P2)
- Creates implementation roadmap
- Provides measurement plan
- Outputs professional Markdown report

## 🔒 Security Best Practices

1. **Never commit `.env` file** to version control
2. **Use environment variables** for all secrets
3. **Implement rate limiting** in production
4. **Add authentication** for public deployments
5. **Use HTTPS** in production
6. **Validate all inputs** (already implemented via Pydantic)

## 🐛 Troubleshooting

### Issue: "Firecrawl API key not configured"
**Solution**: Add `FIRECRAWL_API_KEY` to `.env` file

### Issue: "LLM API error"
**Solution**: 
- Check your API key is valid
- Verify you have sufficient credits
- Check API key has correct permissions

### Issue: "Module not found"
**Solution**: Ensure virtual environment is activated and run `pip install -r requirements.txt`

### Issue: Import errors
**Solution**: Make sure you're running from the project root directory

## 📈 Performance Tips

1. **Use faster models** for development:
   - OpenAI: `gpt-4o-mini` instead of `gpt-4o`
   - Anthropic: `claude-3-haiku` for faster responses

2. **Cache results** for repeated URLs (implement Redis/Memcached)

3. **Implement background tasks** for long-running audits:
```python
from fastapi import BackgroundTasks

@router.post("/audit/async")
async def async_audit(request: AuditRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_audit, request.url)
    return {"status": "processing", "audit_id": "..."}
```

4. **Add rate limiting**:
```bash
pip install slowapi

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

## 🚢 Deployment

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t seo-audit-team .
docker run -p 8000:8000 --env-file .env seo-audit-team
```

### Cloud Deployment

**Heroku**:
```bash
# Create Procfile
web: uvicorn main:app --host 0.0.0.0 --port $PORT

# Deploy
heroku create seo-audit-team
git push heroku main
heroku config:set FIRECRAWL_API_KEY=fc-...
```

**AWS/GCP/Azure**: Use standard Python app deployment guides

## 📝 License

MIT License - Feel free to use in your projects

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📧 Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation at `/api/docs`
3. Open an issue on GitHub

## 🎓 Architecture Notes

This application demonstrates:
- **Clean separation of concerns** (main.py, api.py, UI)
- **Async/await patterns** for performance
- **Error handling** at multiple levels
- **Type safety** with Pydantic models
- **Production logging** with structured output
- **API-first design** with OpenAPI documentation
- **Progressive enhancement** UI that works without JS

## 🔄 Roadmap

- [ ] Add authentication (JWT/OAuth)
- [ ] Implement caching layer (Redis)
- [ ] Add webhook support for async audits
- [ ] Create CLI tool
- [ ] Add batch audit support
- [ ] Implement audit history/database
- [ ] Add export to PDF/DOCX
- [ ] Multi-language support
- [ ] Advanced SERP tracking over time

---

Built with ❤️ using FastAPI, Firecrawl, and AI Agents
