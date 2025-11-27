"""
API Router for SEO Audit Team
Implements three-agent sequential workflow:
1. Page Auditor (Firecrawl scraping + analysis)
2. SERP Analyst (Search engine competitive analysis)
3. Optimization Advisor (Report generation)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl, Field, validator
from typing import List, Optional, Dict, Any
import logging
import os
import asyncio
import json
import httpx
from datetime import datetime
import subprocess
import re

logger = logging.getLogger(__name__)
router = APIRouter()

# =============================================================================
# Configuration & Environment
# =============================================================================

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SERP_API_KEY = os.getenv("SERP_API_KEY", "")

# Choose LLM provider (openai or anthropic)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# Model configuration
if LLM_PROVIDER == "anthropic":
    LLM_MODEL = "claude-3-5-sonnet-20241022"
else:
    LLM_MODEL = "gpt-4o-mini"


# =============================================================================
# Pydantic Models (Request/Response Schemas)
# =============================================================================

class AuditRequest(BaseModel):
    """Request model for SEO audit"""
    url: HttpUrl = Field(..., description="Target URL to audit")
    
    @validator('url')
    def validate_url(cls, v):
        url_str = str(v)
        if not url_str.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class HeadingItem(BaseModel):
    tag: str
    text: str


class LinkCounts(BaseModel):
    internal: Optional[int] = 0
    external: Optional[int] = 0
    broken: Optional[int] = 0
    notes: Optional[str] = ""


class AuditResults(BaseModel):
    title_tag: str = ""
    meta_description: str = ""
    primary_heading: str = ""
    secondary_headings: List[HeadingItem] = []
    word_count: Optional[int] = 0
    content_summary: str = ""
    link_counts: LinkCounts = LinkCounts()
    technical_findings: List[str] = []
    content_opportunities: List[str] = []


class TargetKeywords(BaseModel):
    primary_keyword: str = ""
    secondary_keywords: List[str] = []
    search_intent: str = ""
    supporting_topics: List[str] = []


class PageAuditOutput(BaseModel):
    audit_results: AuditResults
    target_keywords: TargetKeywords


class SerpResult(BaseModel):
    rank: int
    title: str
    url: str
    snippet: str
    content_type: str


class SerpAnalysis(BaseModel):
    primary_keyword: str
    top_10_results: List[SerpResult] = []
    title_patterns: List[str] = []
    content_formats: List[str] = []
    people_also_ask: List[str] = []
    key_themes: List[str] = []
    differentiation_opportunities: List[str] = []


class AuditResponse(BaseModel):
    """Response model for completed audit"""
    status: str
    audit_id: str
    page_audit: Optional[PageAuditOutput] = None
    serp_analysis: Optional[SerpAnalysis] = None
    report: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


# =============================================================================
# Agent Functions
# =============================================================================

async def call_llm(messages: List[Dict], response_format: Optional[Dict] = None, max_tokens: int = 4000) -> str:
    """
    Universal LLM caller supporting OpenAI and Anthropic
    """
    try:
        if LLM_PROVIDER == "anthropic":
            return await call_anthropic(messages, response_format, max_tokens)
        else:
            return await call_openai(messages, response_format, max_tokens)
    except Exception as e:
        logger.error(f"LLM API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM API error: {str(e)}")


async def call_openai(messages: List[Dict], response_format: Optional[Dict] = None, max_tokens: int = 4000) -> str:
    """Call OpenAI API"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


async def call_anthropic(messages: List[Dict], response_format: Optional[Dict] = None, max_tokens: int = 4000) -> str:
    """Call Anthropic Claude API"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")
    
    # Convert OpenAI-style messages to Anthropic format
    system_message = ""
    anthropic_messages = []
    
    for msg in messages:
        if msg["role"] == "system":
            system_message = msg["content"]
        else:
            anthropic_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "model": LLM_MODEL,
            "max_tokens": max_tokens,
            "messages": anthropic_messages
        }
        
        if system_message:
            payload["system"] = system_message
        
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        return result["content"][0]["text"]


async def scrape_with_firecrawl(url: str) -> Dict[str, Any]:
    """
    Scrape webpage using Firecrawl API
    """
    if not FIRECRAWL_API_KEY:
        raise HTTPException(status_code=500, detail="Firecrawl API key not configured")
    
    logger.info(f"Scraping URL with Firecrawl: {url}")
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "url": url,
                    "formats": ["markdown", "html", "links"],
                    "onlyMainContent": True,
                    "timeout": 90000
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise HTTPException(status_code=500, detail="Firecrawl scraping failed")
            
            return data.get("data", {})
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Firecrawl HTTP error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=500, detail=f"Firecrawl error: {str(e)}")
        except Exception as e:
            logger.error(f"Firecrawl error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Scraping error: {str(e)}")


async def search_serp(query: str) -> List[Dict]:
    """
    Search SERP using SerpAPI
    """
    if not SERP_API_KEY:
        logger.warning("SERP API key not configured, using mock data")
        return generate_mock_serp_results(query)
    
    logger.info(f"Searching SERP for: {query}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": SERP_API_KEY,
                    "num": 10,
                    "engine": "google"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            organic_results = data.get("organic_results", [])
            return organic_results[:10]
        
        except Exception as e:
            logger.error(f"SERP API error: {str(e)}")
            return generate_mock_serp_results(query)


def generate_mock_serp_results(query: str) -> List[Dict]:
    """Generate mock SERP results for testing"""
    return [
        {
            "position": i + 1,
            "title": f"Result {i + 1}: {query} - Example Site",
            "link": f"https://example{i + 1}.com/{query.replace(' ', '-')}",
            "snippet": f"This is a comprehensive guide about {query}. Learn everything you need to know..."
        }
        for i in range(10)
    ]


async def agent_page_auditor(url: str) -> PageAuditOutput:
    """
    Agent 1: Page Auditor
    Scrapes the URL and performs on-page SEO analysis
    """
    logger.info(f"[Agent 1] Page Auditor analyzing: {url}")
    
    # Scrape the page
    scraped_data = await scrape_with_firecrawl(url)
    
    markdown_content = scraped_data.get("markdown", "")
    html_content = scraped_data.get("html", "")
    links_data = scraped_data.get("links", [])
    metadata = scraped_data.get("metadata", {})
    
    # Prepare prompt for LLM analysis
    analysis_prompt = f"""You are an expert SEO auditor. Analyze the following webpage data and provide a comprehensive on-page SEO audit.

URL: {url}

METADATA:
Title: {metadata.get('title', 'Not available')}
Description: {metadata.get('description', 'Not available')}
Keywords: {metadata.get('keywords', 'Not available')}

MARKDOWN CONTENT:
{markdown_content[:8000]}

LINKS DATA:
Total Links: {len(links_data)}

INSTRUCTIONS:
1. Extract and analyze:
   - Title tag (exact text)
   - Meta description (exact text)
   - Primary H1 heading
   - Secondary headings (H2-H4) with their text
   - Approximate word count
   - Content summary (2-3 sentences)
   
2. Analyze links:
   - Count internal vs external links
   - Note any obvious issues
   
3. Identify technical SEO issues:
   - Missing elements
   - Optimization opportunities
   - Technical problems
   
4. Infer target keywords:
   - Primary keyword (1-3 words most likely targeted)
   - 2-5 secondary keywords
   - Search intent (informational/transactional/navigational/commercial)
   - 3-5 supporting topics

Provide your response as a valid JSON object matching this structure:
{{
  "audit_results": {{
    "title_tag": "...",
    "meta_description": "...",
    "primary_heading": "...",
    "secondary_headings": [{{"tag": "h2", "text": "..."}}],
    "word_count": 0,
    "content_summary": "...",
    "link_counts": {{
      "internal": 0,
      "external": 0,
      "broken": 0,
      "notes": "..."
    }},
    "technical_findings": ["..."],
    "content_opportunities": ["..."]
  }},
  "target_keywords": {{
    "primary_keyword": "...",
    "secondary_keywords": ["..."],
    "search_intent": "...",
    "supporting_topics": ["..."]
  }}
}}

Return ONLY the JSON object, no other text."""

    messages = [
        {"role": "system", "content": "You are an expert SEO auditor. Always respond with valid JSON only."},
        {"role": "user", "content": analysis_prompt}
    ]
    
    response = await call_llm(messages, max_tokens=3000)
    
    # Parse JSON response
    try:
        # Clean the response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        audit_data = json.loads(response)
        return PageAuditOutput(**audit_data)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response: {response}")
        raise HTTPException(status_code=500, detail="Failed to parse audit results")


async def agent_serp_analyst(primary_keyword: str) -> SerpAnalysis:
    """
    Agent 2: SERP Analyst
    Researches competitive landscape for the primary keyword
    """
    logger.info(f"[Agent 2] SERP Analyst researching: {primary_keyword}")
    
    # Get SERP results
    serp_results = await search_serp(primary_keyword)
    
    # Prepare SERP data for analysis
    serp_summary = json.dumps(serp_results[:10], indent=2)
    
    analysis_prompt = f"""You are an expert SEO competitive analyst. Analyze these Google search results for the keyword: "{primary_keyword}"

SERP RESULTS (Top 10):
{serp_summary}

INSTRUCTIONS:
Analyze the competitive landscape and provide:

1. Parse top 10 results with:
   - Rank (1-10)
   - Title
   - URL
   - Snippet
   - Content type (blog post, landing page, tool, directory, video, guide, etc.)

2. Identify patterns:
   - Common title patterns (e.g., "Best X", "Top 10", "How to", year mentions)
   - Content formats (guides, listicles, comparisons, tools, etc.)
   - People Also Ask questions (infer from context)
   - Key themes competitors emphasize
   - Differentiation opportunities (gaps in current results)

Provide your response as a valid JSON object:
{{
  "primary_keyword": "{primary_keyword}",
  "top_10_results": [
    {{
      "rank": 1,
      "title": "...",
      "url": "...",
      "snippet": "...",
      "content_type": "..."
    }}
  ],
  "title_patterns": ["..."],
  "content_formats": ["..."],
  "people_also_ask": ["..."],
  "key_themes": ["..."],
  "differentiation_opportunities": ["..."]
}}

Return ONLY the JSON object, no other text."""

    messages = [
        {"role": "system", "content": "You are an expert SEO competitive analyst. Always respond with valid JSON only."},
        {"role": "user", "content": analysis_prompt}
    ]
    
    response = await call_llm(messages, max_tokens=3000)
    
    # Parse JSON response
    try:
        # Clean the response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        serp_data = json.loads(response)
        return SerpAnalysis(**serp_data)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse SERP analysis: {e}")
        logger.error(f"Response: {response}")
        raise HTTPException(status_code=500, detail="Failed to parse SERP analysis")


async def agent_optimization_advisor(
    url: str,
    page_audit: PageAuditOutput,
    serp_analysis: SerpAnalysis
) -> str:
    """
    Agent 3: Optimization Advisor
    Synthesizes audit and SERP data into actionable report
    """
    logger.info("[Agent 3] Optimization Advisor generating report")
    
    report_prompt = f"""You are a senior SEO consultant creating a comprehensive optimization report.

TARGET URL: {url}

PAGE AUDIT DATA:
{json.dumps(page_audit.dict(), indent=2)}

SERP COMPETITIVE ANALYSIS:
{json.dumps(serp_analysis.dict(), indent=2)}

INSTRUCTIONS:
Create a professional SEO audit report in Markdown format with these sections:

# SEO Audit Report

## Executive Summary
- Page being audited
- Primary keyword focus
- 2-3 key strengths
- 2-3 critical weaknesses
- Overall SEO health score (estimate)

## Technical & On-Page Findings

### Title Tag Analysis
- Current: [exact title, character count]
- Recommendations: [specific suggestions]

### Meta Description Analysis
- Current: [exact description, character count]
- Recommendations: [specific suggestions]

### Heading Structure
- H1: [current H1]
- H2-H4 Analysis: [structure quality]
- Recommendations: [improvements]

### Content Analysis
- Word Count: [number]
- Content Depth: [assessment]
- Readability: [assessment]
- Recommendations: [specific improvements]

### Technical Issues
[List each issue found with severity and fix]

## Keyword Strategy Analysis

### Primary Keyword: [keyword]
- Current targeting strength: [assessment]
- Search intent alignment: [assessment]
- Recommendations: [how to better optimize]

### Secondary Keywords
[List with optimization recommendations]

### Supporting Topics
[List topics to add/expand]

## Competitive SERP Analysis

### What Top Competitors Are Doing
- Common title patterns: [list]
- Dominant content formats: [list]
- Key themes: [list]

### Content Gaps & Opportunities
[Specific opportunities to differentiate]

## Prioritized Recommendations

### P0 - Critical (Implement Immediately)
1. **[Area]**: [Specific action]
   - Rationale: [Why, citing data]
   - Expected Impact: [Specific benefit]
   - Effort: [Low/Medium/High]

### P1 - High Priority (Implement This Month)
[Same format as P0]

### P2 - Medium Priority (Implement This Quarter)
[Same format as P0]

## Implementation Roadmap

### Week 1-2
[Specific tasks]

### Week 3-4
[Specific tasks]

### Month 2-3
[Specific tasks]

## Measurement Plan
- KPIs to track
- Tools to use
- Expected timeline for results

---

Be specific with data points (e.g., "Title is 45 characters, recommend 55-60").
Use actual numbers and examples from the audit data.
Make recommendations actionable and prioritized.
"""

    messages = [
        {"role": "system", "content": "You are a senior SEO consultant creating detailed audit reports."},
        {"role": "user", "content": report_prompt}
    ]
    
    report = await call_llm(messages, max_tokens=4000)
    
    return report.strip()


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/audit", response_model=AuditResponse)
async def run_seo_audit(request: AuditRequest):
    """
    Main endpoint: Runs complete 3-agent SEO audit workflow
    """
    audit_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    url = str(request.url)
    
    try:
        logger.info(f"Starting SEO audit for: {url}")
        
        # Agent 1: Page Auditor
        page_audit = await agent_page_auditor(url)
        logger.info(f"Page audit complete. Primary keyword: {page_audit.target_keywords.primary_keyword}")
        
        # Agent 2: SERP Analyst
        serp_analysis = await agent_serp_analyst(page_audit.target_keywords.primary_keyword)
        logger.info(f"SERP analysis complete. Found {len(serp_analysis.top_10_results)} competitors")
        
        # Agent 3: Optimization Advisor
        report = await agent_optimization_advisor(url, page_audit, serp_analysis)
        logger.info("Optimization report generated")
        
        return AuditResponse(
            status="completed",
            audit_id=audit_id,
            page_audit=page_audit,
            serp_analysis=serp_analysis,
            report=report,
            timestamp=datetime.now().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audit failed: {str(e)}", exc_info=True)
        return AuditResponse(
            status="failed",
            audit_id=audit_id,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )


@router.get("/status")
async def get_status():
    """Check API and service status"""
    status = {
        "api": "operational",
        "firecrawl": "configured" if FIRECRAWL_API_KEY else "not_configured",
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "llm_configured": bool(OPENAI_API_KEY or ANTHROPIC_API_KEY),
        "serp": "configured" if SERP_API_KEY else "mock_mode"
    }
    return status
