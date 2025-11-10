# API Guide

Complete API reference for the CrewAI Resume & Job Search Generator.

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Health Endpoints](#health-endpoints)
- [Search Configuration API](#search-configuration-api)
- [Resume Generation](#resume-generation)
- [Examples](#examples)
- [Error Handling](#error-handling)

## Overview

The API provides endpoints for:
- Health monitoring and system metrics
- Configurable GitHub profile analysis
- LinkedIn job search (with browser automation coming soon)
- Combined searches with streaming results

## Base URL

**Local Development**: `http://localhost:8080`
**Cloudflare Deployment**: `https://your-worker.workers.dev`

## Authentication

Currently, the API uses server-side API keys (Gemini API). No client authentication is required for public endpoints.

For production deployments, consider adding:
- API key authentication
- Rate limiting
- OAuth 2.0

## Health Endpoints

### Liveness Check

Check if the service is alive.

**Endpoint**: `GET /health/live`

**Response**:
```json
{
  "status": "alive",
  "timestamp": "2025-01-10T12:00:00Z"
}
```

### Readiness Check

Check if all dependencies are ready.

**Endpoint**: `GET /health/ready`

**Response** (200 OK):
```json
{
  "ready": true,
  "timestamp": "2025-01-10T12:00:00Z"
}
```

**Response** (503 Service Unavailable):
```json
{
  "ready": false,
  "checks": [
    {
      "service": "gemini_api",
      "status": "unhealthy",
      "message": "API key not configured"
    }
  ]
}
```

### Comprehensive Health

Get detailed health information.

**Endpoint**: `GET /health/`

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-10T12:00:00Z",
  "uptime_seconds": 3600.5,
  "environment": "production",
  "version": "1.0.0",
  "checks": {
    "gemini_api": {
      "service": "gemini_api",
      "status": "healthy",
      "message": "Connected",
      "response_time_ms": 150.2
    },
    "crewai": {
      "service": "crewai",
      "status": "healthy",
      "message": "Framework initialized"
    }
  },
  "system": {
    "cpu_percent": 25.5,
    "memory_percent": 45.8,
    "memory_available_mb": 2048,
    "disk_percent": 60.2,
    "process_count": 125
  }
}
```

### Prometheus Metrics

Get metrics in Prometheus format.

**Endpoint**: `GET /health/metrics`

**Response** (text/plain):
```
# HELP uptime_seconds Time since service start
# TYPE uptime_seconds gauge
uptime_seconds 3600.5
# HELP cpu_percent CPU usage percentage
# TYPE cpu_percent gauge
cpu_percent 25.5
# HELP memory_percent Memory usage percentage
# TYPE memory_percent gauge
memory_percent 45.8
```

## Search Configuration API

### Get Configuration Template

Get a pre-filled configuration template for a specific search type.

**Endpoint**: `GET /api/search/config/template/{search_type}`

**Parameters**:
- `search_type`: One of `github_resume`, `linkedin_jobs`, or `combined`

**Example**:
```bash
curl http://localhost:8080/api/search/config/template/github_resume
```

**Response**:
```json
{
  "search_type": "github_resume",
  "github_config": {
    "username": "example_user",
    "include_projects": true,
    "include_contributions": true,
    "max_repos": 10
  },
  "output_format": "markdown"
}
```

### Execute Search

Execute a configurable search with streaming results.

**Endpoint**: `POST /api/search/execute`

**Content-Type**: `application/json`

**Request Body**:

#### GitHub Resume Search

```json
{
  "search_type": "github_resume",
  "github_config": {
    "username": "octocat",
    "include_projects": true,
    "include_contributions": true,
    "max_repos": 10
  },
  "output_format": "markdown"
}
```

#### LinkedIn Job Search

```json
{
  "search_type": "linkedin_jobs",
  "linkedin_config": {
    "keywords": ["Python", "Machine Learning", "AI"],
    "location": "San Francisco, CA",
    "experience_level": "Mid-Senior",
    "job_type": "Full-time",
    "max_results": 20,
    "company_filter": ["Google", "Meta", "OpenAI"]
  },
  "output_format": "json"
}
```

#### Combined Search

```json
{
  "search_type": "combined",
  "github_config": {
    "username": "octocat",
    "max_repos": 10
  },
  "linkedin_config": {
    "keywords": ["Python", "AI"],
    "location": "Remote",
    "max_results": 20
  },
  "output_format": "markdown"
}
```

**Response**: Server-Sent Events (SSE) stream

The response is a stream of events in SSE format:

```
event: progress_update
data: {"status":"started","message":"Starting GitHub profile analysis for octocat"}

event: progress_update
data: {"task":"research","summary":"Analyzing GitHub profile","status":"task_done"}

event: progress_update
data: {"task":"profile_analysis","summary":"Processing repositories","status":"task_done"}

data: {"status":"completed","output":"# Resume for octocat\n\n...","type":"github_resume"}
```

**Event Types**:
- `progress_update`: Task progress update
- `ping`: Keepalive heartbeat (no data)

**Status Values**:
- `started`: Search initiated
- `task_done`: A task completed
- `completed`: All tasks completed
- `error`: An error occurred

### Configuration Fields

#### GitHubSearchConfig

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `username` | string | Yes | - | GitHub username to analyze |
| `include_projects` | boolean | No | true | Include project analysis |
| `include_contributions` | boolean | No | true | Include contribution history |
| `max_repos` | integer | No | 10 | Maximum repositories to analyze |

#### LinkedInJobSearchConfig

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `keywords` | array[string] | Yes | - | Job search keywords |
| `location` | string | No | null | Job location filter |
| `experience_level` | string | No | null | Experience level (e.g., "Mid-Senior") |
| `job_type` | string | No | null | Job type (e.g., "Full-time", "Remote") |
| `max_results` | integer | No | 20 | Maximum results to return |
| `company_filter` | array[string] | No | null | Filter by specific companies |

## Resume Generation (Legacy Endpoint)

### Generate Resume

Original resume generation endpoint (kept for backwards compatibility).

**Endpoint**: `GET /resume?username={username}`

**Parameters**:
- `username`: GitHub username

**Response**: SSE stream (same format as `/api/search/execute`)

**Example**:
```bash
curl "http://localhost:8080/resume?username=octocat"
```

## Examples

### Python Client

```python
import httpx
import json

async def search_github_profile(username: str):
    """Search GitHub profile and generate resume."""
    url = "http://localhost:8080/api/search/execute"
    payload = {
        "search_type": "github_resume",
        "github_config": {
            "username": username,
            "max_repos": 10
        },
        "output_format": "markdown"
    }

    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=payload, timeout=120.0) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    print(f"Status: {data.get('status')}")
                    if data.get('status') == 'completed':
                        print(f"Result: {data.get('output')}")
                        break

# Run it
import asyncio
asyncio.run(search_github_profile("octocat"))
```

### JavaScript/Node.js Client

```javascript
const EventSource = require('eventsource');

function searchGitHubProfile(username) {
  const url = 'http://localhost:8080/api/search/execute';
  const payload = {
    search_type: 'github_resume',
    github_config: {
      username: username,
      max_repos: 10
    },
    output_format: 'markdown'
  };

  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(response => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    function read() {
      reader.read().then(({ done, value }) => {
        if (done) return;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            console.log('Status:', data.status);
            if (data.status === 'completed') {
              console.log('Result:', data.output);
            }
          }
        }

        read();
      });
    }

    read();
  });
}

searchGitHubProfile('octocat');
```

### cURL Examples

#### Get Health Status

```bash
curl http://localhost:8080/health/
```

#### Get Configuration Template

```bash
curl http://localhost:8080/api/search/config/template/combined
```

#### Execute GitHub Search

```bash
curl -X POST http://localhost:8080/api/search/execute \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "github_resume",
    "github_config": {
      "username": "octocat",
      "max_repos": 5
    },
    "output_format": "markdown"
  }'
```

#### Execute Combined Search

```bash
curl -X POST http://localhost:8080/api/search/execute \
  -H "Content-Type": application/json" \
  -d '{
    "search_type": "combined",
    "github_config": {
      "username": "octocat"
    },
    "linkedin_config": {
      "keywords": ["Python", "AI"],
      "location": "San Francisco"
    }
  }'
```

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid configuration) |
| 422 | Validation Error (invalid JSON schema) |
| 500 | Internal Server Error |
| 503 | Service Unavailable (dependencies not ready) |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

#### Missing Configuration

```json
{
  "detail": "github_config required for GitHub resume search"
}
```

#### Invalid Username

```json
{
  "detail": "GitHub username must be alphanumeric and less than 39 characters"
}
```

#### Service Unavailable

```json
{
  "detail": "Gemini API is currently unavailable"
}
```

### Handling Streaming Errors

Errors during streaming are sent as SSE events:

```
data: {"status":"error","message":"Failed to fetch GitHub profile: 404 Not Found"}
```

## Rate Limiting

Currently no rate limiting is implemented. For production:

- Implement rate limiting per IP
- Add authentication with per-user quotas
- Monitor and alert on unusual usage patterns

## API Documentation

Interactive API documentation is available:

- **Swagger UI**: `http://localhost:8080/api/docs`
- **ReDoc**: `http://localhost:8080/api/redoc`

## Future Features

### Coming Soon

- **Browser Automation**: Full LinkedIn scraping with Playwright/Selenium
- **PDF Export**: Export resumes as PDF
- **Email Notifications**: Get results via email
- **Batch Processing**: Process multiple profiles at once
- **Custom Templates**: Use custom resume templates
- **Analytics**: Track search history and performance

### Planned Endpoints

- `POST /api/jobs/scrape`: Direct LinkedIn job scraping
- `GET /api/search/history`: View search history
- `POST /api/export/pdf`: Export resume as PDF
- `POST /api/batch`: Batch processing
- `GET /api/templates`: List available templates

## Support

For issues or questions:
- GitHub Issues: [repository/issues]
- Documentation: [CLOUDFLARE_DEPLOYMENT.md](./CLOUDFLARE_DEPLOYMENT.md)
- API Docs: `http://localhost:8080/api/docs`
