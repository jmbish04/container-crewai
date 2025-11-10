# Computer Use Integration

This document explains the Computer Use integration for browser automation in the CrewAI Container Application.

## Overview

The application uses Google's Computer Use Preview capabilities powered by Gemini and Playwright to automate LinkedIn job searches. This enables actual web scraping with browser automation instead of relying on APIs.

## Features

### LinkedIn Job Search with Authentication

- **Browser Automation**: Uses Playwright to control a headless Chrome browser
- **LinkedIn Authentication**: Securely logs into LinkedIn using credentials from Cloudflare Worker secrets
- **Smart Scraping**: Extracts job listings with multiple selector strategies for reliability
- **Filtering**: Supports filtering by keywords, location, experience level, job type, and company
- **Rate Limiting Friendly**: Includes delays and proper wait strategies to avoid detection

### Gemini Computer Use

- **Vision-Based Actions**: Can understand screenshots and determine actions
- **Natural Language Control**: Execute browser actions using natural language instructions
- **Context Awareness**: Uses screenshots for visual context when making decisions

## Architecture

```
Cloudflare Worker
    ↓ (passes secrets)
Container Environment Variables
    ↓ (LINKEDIN_USERNAME, LINKEDIN_PASSWORD)
ComputerUseAgent
    ↓ (initializes)
Playwright Browser
    ↓ (navigates to)
LinkedIn
    ↓ (scrapes)
Job Results
```

## Setup

### 1. Install Dependencies

The required dependencies are already in `pyproject.toml`:

```toml
dependencies = [
    "playwright>=1.40.0",
    "google-generativeai>=0.3.0",
    "pillow>=10.0.0",
    ...
]
```

Install them:

```bash
uv sync
```

### 2. Install Playwright Browsers

```bash
# Install system dependencies for Playwright
uv run playwright install-deps chromium

# Install the Chrome browser
uv run playwright install chromium
```

### 3. Set LinkedIn Credentials

#### Local Development

```bash
export LINKEDIN_USERNAME="your-linkedin-email@example.com"
export LINKEDIN_PASSWORD="your-secure-password"
```

#### Cloudflare Deployment

Set secrets using wrangler:

```bash
npx wrangler secret put LINKEDIN_USERNAME
# Enter your LinkedIn email when prompted

npx wrangler secret put LINKEDIN_PASSWORD
# Enter your LinkedIn password when prompted
```

**Important**: Secrets are encrypted and never exposed in logs or code.

### 4. Configure Gemini API

```bash
# Already set if you configured it for resume generation
export GEMINI_API_KEY="your-gemini-api-key"

# Or for Cloudflare
npx wrangler secret put GEMINI_API_KEY
```

## Usage

### LinkedIn Job Search API

#### Basic Search (No Authentication)

```bash
curl -X POST http://localhost:8080/api/search/execute \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "linkedin_jobs",
    "linkedin_config": {
      "keywords": ["Python", "Machine Learning"],
      "location": "San Francisco, CA",
      "max_results": 20
    }
  }'
```

#### Authenticated Search (More Results)

When LinkedIn credentials are provided, the system automatically authenticates and can access more detailed job information:

```bash
curl -X POST http://localhost:8080/api/search/execute \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "linkedin_jobs",
    "linkedin_config": {
      "keywords": ["Senior Software Engineer"],
      "location": "Remote",
      "experience_level": "Mid-Senior level",
      "job_type": "Full-time",
      "max_results": 50,
      "company_filter": ["Google", "Meta", "Apple"]
    }
  }'
```

### Using ComputerUseAgent Directly

```python
import asyncio
from computer_use.agent import ComputerUseAgent, BrowserEnvironment

async def search_jobs():
    async with ComputerUseAgent(
        environment=BrowserEnvironment.PLAYWRIGHT,
        headless=True,
        linkedin_username="your-email@example.com",
        linkedin_password="your-password"
    ) as agent:
        # Authenticate
        await agent.login_linkedin()

        # Search jobs
        jobs = await agent.search_linkedin_jobs(
            keywords=["Python", "AI"],
            location="San Francisco",
            max_results=20,
            require_auth=True
        )

        for job in jobs:
            print(f"{job['title']} at {job['company']}")
            print(f"Location: {job['location']}")
            print(f"URL: {job['url']}")
            print("---")

asyncio.run(search_jobs())
```

### Execute Custom Browser Actions

```python
async def custom_action():
    async with ComputerUseAgent() as agent:
        # Execute a natural language action
        result = await agent.execute_action(
            "Navigate to Google and search for 'CrewAI'"
        )
        print(result)

asyncio.run(custom_action())
```

## Configuration Options

### ComputerUseAgent Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `environment` | BrowserEnvironment | PLAYWRIGHT | Browser environment (playwright or browserbase) |
| `initial_url` | str | "https://www.google.com" | Starting URL |
| `headless` | bool | True | Run browser in headless mode |
| `highlight_mouse` | bool | False | Highlight mouse cursor (debugging) |
| `api_key` | str | from env | Gemini API key |
| `linkedin_username` | str | from env | LinkedIn email |
| `linkedin_password` | str | from env | LinkedIn password |

### LinkedIn Search Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keywords` | List[str] | Yes | Job search keywords |
| `location` | str | No | Job location |
| `experience_level` | str | No | Experience level filter |
| `job_type` | str | No | Job type (Full-time, Remote, etc.) |
| `max_results` | int | No (default: 20) | Maximum number of results |
| `require_auth` | bool | No (default: False) | Whether to authenticate |

### Experience Level Options

- "Internship"
- "Entry level"
- "Associate"
- "Mid-Senior level"
- "Director"
- "Executive"

### Job Type Options

- "Full-time"
- "Part-time"
- "Contract"
- "Temporary"
- "Volunteer"
- "Internship"

## Docker/Container Deployment

### Dockerfile Configuration

The Dockerfile includes Playwright installation:

```dockerfile
# Install Playwright browsers in builder stage
RUN uv run playwright install-deps chromium
RUN uv run playwright install chromium

# Install required system libraries in final stage
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libatspi2.0-0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*
```

### Building the Container

```bash
docker build -t crewai-container .
```

### Running Locally with Docker

```bash
docker run -p 8080:8080 \
  -e GEMINI_API_KEY="your-key" \
  -e LINKEDIN_USERNAME="your-email" \
  -e LINKEDIN_PASSWORD="your-password" \
  crewai-container
```

## Cloudflare Deployment

### 1. Set Secrets

```bash
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put LINKEDIN_USERNAME
npx wrangler secret put LINKEDIN_PASSWORD
```

### 2. Deploy

```bash
npx wrangler deploy
```

The Worker automatically passes secrets to the container as environment variables.

## Security Best Practices

### Credential Protection

1. **Never commit credentials** to version control
2. **Use Cloudflare Worker secrets** for production deployments
3. **Rotate passwords regularly**
4. **Use application-specific passwords** if available
5. **Enable 2FA on your LinkedIn account** (may require manual verification)

### Rate Limiting

The browser automation includes built-in delays to avoid detection:

- Waits for page loads (`networkidle`)
- Scrolls gradually to load more results
- Uses realistic user-agent strings

### Error Handling

- Graceful degradation if LinkedIn blocks requests
- Automatic retry with exponential backoff (future enhancement)
- Detailed error messages for debugging

## Troubleshooting

### Common Issues

#### 1. "playwright install-deps" fails

**Solution**: Ensure Docker base image has required system packages.

```bash
# In Dockerfile, install dependencies
RUN apt-get update && apt-get install -y curl build-essential
```

#### 2. LinkedIn login fails

**Causes**:
- Invalid credentials
- LinkedIn 2FA enabled (requires manual verification)
- Too many login attempts (rate limiting)

**Solution**:
- Verify credentials are correct
- Temporarily disable 2FA or use application-specific password
- Wait before retrying

#### 3. Job scraping returns empty results

**Causes**:
- LinkedIn changed their HTML structure
- Browser detected as bot
- Network timeouts

**Solution**:
- Update selectors in `ComputerUseAgent.search_linkedin_jobs()`
- Use authenticated search for better results
- Increase timeouts

#### 4. Container crashes with Playwright errors

**Cause**: Missing system libraries

**Solution**: Ensure all Playwright dependencies are installed in Dockerfile.

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

async with ComputerUseAgent(headless=False) as agent:
    # Browser window will be visible for debugging
    ...
```

### View Browser Screenshots

```python
async with ComputerUseAgent() as agent:
    screenshot = await agent.take_screenshot()
    with open("debug.png", "wb") as f:
        f.write(screenshot)
```

## Performance Considerations

### Resource Usage

- **Memory**: ~500MB per browser instance
- **CPU**: Moderate during scraping, low when idle
- **Disk**: ~200MB for Chromium browser

### Optimization Tips

1. **Use headless mode** in production (default)
2. **Limit max_results** to reduce scraping time
3. **Reuse agent instances** when possible
4. **Enable container sleep** in Cloudflare (10min default)

### Scaling

- **Cloudflare Containers**: Auto-scales based on demand (max_instances: 5)
- **Rate Limiting**: Consider implementing request queuing for high load
- **Caching**: Cache job results for common searches (future enhancement)

## Future Enhancements

- [ ] Support for Browserbase (cloud browser service)
- [ ] Advanced Gemini Computer Use actions
- [ ] Job application automation
- [ ] Resume matching with job descriptions
- [ ] Email notifications for new matching jobs
- [ ] Batch job searches across multiple platforms
- [ ] Integration with job boards beyond LinkedIn

## References

- [Google Computer Use Preview](https://github.com/google/computer-use-preview)
- [Playwright Documentation](https://playwright.dev/)
- [Cloudflare Containers](https://developers.cloudflare.com/containers/)
- [Gemini API](https://ai.google.dev/gemini-api/)

## Support

For issues or questions:
- Check [API_GUIDE.md](./API_GUIDE.md) for API usage
- See [CLOUDFLARE_DEPLOYMENT.md](./CLOUDFLARE_DEPLOYMENT.md) for deployment
- Review [tests/](./tests/) for examples
- Open an issue on GitHub

---

**Security Note**: This tool is for personal use and educational purposes. Respect LinkedIn's terms of service and use responsibly.
