# Cloudflare Container Deployment Guide

This guide will help you deploy the GitHub Resume Generator to Cloudflare using Cloudflare Containers.

## What is Cloudflare Containers?

Cloudflare Containers allows you to deploy containerized applications (like this FastAPI + CrewAI app) on Cloudflare's global network. The container runs alongside a Cloudflare Worker that handles routing and orchestration.

## Prerequisites

Before you begin, make sure you have:

1. **Docker** installed and running on your machine
   - Verify with: `docker info`
   - Download from: https://www.docker.com/get-started

2. **Node.js** (v18 or later) and npm installed
   - Verify with: `node --version` and `npm --version`
   - Download from: https://nodejs.org/

3. **A Cloudflare account** with Workers and Containers enabled
   - Sign up at: https://dash.cloudflare.com/sign-up

4. **A Gemini API key** from Google AI Studio
   - Get one at: https://aistudio.google.com/apikey

## Installation

### Step 1: Install Node.js Dependencies

Install the Cloudflare Workers SDK and wrangler CLI:

```bash
npm install
```

### Step 2: Authenticate with Cloudflare

Log in to your Cloudflare account:

```bash
npx wrangler login
```

This will open a browser window where you can authorize wrangler to access your account.

## Configuration

### Step 3: Set Your Secrets

Your API keys and credentials need to be stored as Cloudflare secrets (encrypted environment variables):

#### Gemini API Key (Required)

```bash
npm run secret:gemini
```

Or using wrangler directly:

```bash
npx wrangler secret put GEMINI_API_KEY
```

When prompted, paste your Gemini API key and press Enter.

#### LinkedIn Credentials (Optional, for Job Search)

To enable LinkedIn job search with authentication (gets more detailed results):

```bash
npx wrangler secret put LINKEDIN_USERNAME
# Enter your LinkedIn email when prompted

npx wrangler secret put LINKEDIN_PASSWORD
# Enter your LinkedIn password when prompted
```

**Note**: LinkedIn credentials are optional. Job search will work without them, but authenticated searches return more detailed information.

### Step 4: Review the Configuration

The project includes these configuration files:

- **`wrangler.jsonc`**: Cloudflare Worker configuration (JSON with comments)
  - Container settings (max instances, image location)
  - Durable Objects bindings for container orchestration
  - Node.js compatibility flags

- **`worker/index.js`**: Worker script that routes requests to the container
  - Handles all HTTP routing
  - Manages container lifecycle (start/stop)
  - Passes environment variables to the container

- **`Dockerfile`**: Container image definition
  - Built for `linux/amd64` architecture (required by Cloudflare)
  - Multi-stage build for optimal image size
  - Runs FastAPI on port 8080

**Note**: We use `wrangler.jsonc` instead of `wrangler.toml` because the current wrangler version (3.114.x) requires the containers configuration to be an object rather than an array, which is more naturally expressed in JSON format.

## Local Development

### Step 5: Test Locally

Before deploying to Cloudflare, test your container locally:

```bash
npm run dev
```

Or with wrangler directly:

```bash
npx wrangler dev
```

This will:
1. Build your Docker container locally
2. Start a local development server
3. Make your app available at `http://localhost:8787`

**Note**: The first request may take a few seconds as the container needs to start up.

### Testing the Application

Open your browser and navigate to:
- http://localhost:8787/ - Main application page
- http://localhost:8787/resume?username=GITHUB_USERNAME - Test the resume API directly

## Deployment to Cloudflare

### Step 6: Deploy to Production

When you're ready to deploy to Cloudflare's global network:

```bash
npm run deploy
```

Or with wrangler:

```bash
npx wrangler deploy
```

This will:
1. Build your Docker image for the `linux/amd64` platform
2. Upload the container image to Cloudflare
3. Deploy your Worker script
4. Provision Durable Objects for container orchestration

The deployment typically takes 2-5 minutes depending on your container size.

### Step 7: Access Your Deployed Application

After deployment, wrangler will display your application URL:

```
Published github-resume-generator (X.XX sec)
  https://github-resume-generator.<your-subdomain>.workers.dev
```

Visit this URL to access your deployed resume generator!

## Container Behavior

### Lifecycle Management

- **Cold Start**: The first request to your container takes a few seconds as it needs to boot up
- **Warm Instances**: Subsequent requests are fast (< 100ms) while the container is running
- **Auto-Sleep**: The container automatically stops after **10 minutes** of inactivity to save resources
- **Auto-Wake**: The container automatically starts when a new request arrives

### Scaling

- **Max Instances**: Configured for up to 5 concurrent container instances
- **Auto-Scaling**: Cloudflare automatically scales based on traffic
- **Global Distribution**: Containers run in Cloudflare's data centers closest to your users

## Monitoring and Debugging

### View Logs

Monitor your application in real-time:

```bash
npm run tail
```

Or with wrangler:

```bash
npx wrangler tail
```

This shows:
- Container startup/shutdown events
- HTTP requests and responses
- Error messages
- Console logs from your application

### Check Container Status

View running containers:

```bash
npx wrangler containers list
```

View deployed images:

```bash
npx wrangler containers images list
```

## Troubleshooting

### Common Issues

1. **"Docker is not running"**
   - Start Docker Desktop or the Docker daemon
   - Verify with: `docker info`

2. **"Container build failed"**
   - Check that your Dockerfile syntax is correct
   - Ensure all required files (pyproject.toml, uv.lock, src/) are present
   - Try building locally: `docker build -t test .`

3. **"Container crashes on startup"**
   - Check logs with: `npx wrangler tail`
   - Verify GEMINI_API_KEY is set: `npx wrangler secret list`
   - Ensure the PORT environment variable is 8080

4. **"Slow first request"**
   - This is expected! Containers take a few seconds to start up
   - Subsequent requests will be much faster
   - Consider keeping the container warm with periodic health checks

5. **"Module not found" errors in worker**
   - Run: `npm install` to install dependencies
   - Verify `@cloudflare/containers` is in package.json

### Getting Help

- **Cloudflare Containers Docs**: https://developers.cloudflare.com/containers/
- **Cloudflare Discord**: https://discord.gg/cloudflaredev
- **Wrangler Issues**: https://github.com/cloudflare/workers-sdk/issues

## Architecture Overview

```
User Request
    ↓
Cloudflare Edge (Worker)
    ↓
worker/index.js
    ↓
ResumeGeneratorContainer (Durable Object)
    ↓
Docker Container (FastAPI + CrewAI)
    ↓
Gemini API
```

### How It Works

1. **User Request**: User visits your workers.dev URL
2. **Worker Routing**: The Worker (worker/index.js) receives the request
3. **Container Orchestration**: Worker gets or creates a container instance via Durable Objects
4. **Request Forwarding**: Worker forwards the HTTP request to the container
5. **FastAPI Processing**: Your FastAPI app processes the request
6. **CrewAI Execution**: CrewAI agents research and generate the resume using Gemini API
7. **Streaming Response**: Progress updates stream back to the user in real-time

## Cost Considerations

Cloudflare Containers pricing (as of January 2025):

- **Workers**: 100,000 requests/day free, then $0.50/million requests
- **Durable Objects**: 1 million requests/month free, then $0.15/million requests
- **Container Runtime**: Billed per GB-second of container uptime
- **Gemini API**: Free tier available, then pay-per-use

The auto-sleep feature (stops after 10 minutes) helps minimize container runtime costs.

## Advanced Configuration

### Customizing Container Behavior

Edit `worker/index.js` to modify:

- **Sleep timeout**: Change `sleepAfter = "10m"` to a different duration
- **Max instances**: Edit `max_instances` in `wrangler.jsonc`
- **Error handling**: Customize the error response in the catch block

### Adding Custom Domains

Once deployed, you can add a custom domain:

1. Go to the Cloudflare Dashboard
2. Navigate to Workers & Pages → your-worker
3. Click "Add Custom Domain"
4. Follow the prompts to add your domain

### Environment Variables

To add more environment variables:

1. Add them to `wrangler.jsonc` under a `"vars"` key (non-sensitive data)
2. Or use secrets: `npx wrangler secret put VARIABLE_NAME` (sensitive data)
3. Access them in the container via `this.envVars` in the Container class

## Next Steps

- ✅ Deploy your container to Cloudflare
- 🌐 Add a custom domain
- 📊 Set up monitoring and alerts
- 🔧 Customize the Worker for your use case
- 🚀 Explore other Cloudflare features (KV, R2, etc.)

## Additional Resources

- [Cloudflare Containers Documentation](https://developers.cloudflare.com/containers/)
- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
- [Durable Objects Documentation](https://developers.cloudflare.com/durable-objects/)
- [Wrangler CLI Reference](https://developers.cloudflare.com/workers/wrangler/)

---

**Need help?** Open an issue at https://github.com/jmbish04/container-crewai/issues or reach out to the Cloudflare community on Discord!
