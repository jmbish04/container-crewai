# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""API endpoints for configurable search functionality."""

import asyncio
import json
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


class SearchType(str, Enum):
    """Type of search to perform."""
    GITHUB_RESUME = "github_resume"
    LINKEDIN_JOBS = "linkedin_jobs"
    COMBINED = "combined"


class GitHubSearchConfig(BaseModel):
    """Configuration for GitHub profile search."""
    username: str = Field(..., description="GitHub username to analyze")
    include_projects: bool = Field(default=True, description="Include project analysis")
    include_contributions: bool = Field(default=True, description="Include contribution history")
    max_repos: int = Field(default=10, description="Maximum number of repositories to analyze")


class LinkedInJobSearchConfig(BaseModel):
    """Configuration for LinkedIn job search."""
    keywords: List[str] = Field(..., description="Job search keywords (e.g., ['Python', 'AI', 'ML'])")
    location: Optional[str] = Field(default=None, description="Job location (e.g., 'San Francisco, CA')")
    experience_level: Optional[str] = Field(default=None, description="Experience level (e.g., 'Mid-Senior')")
    job_type: Optional[str] = Field(default=None, description="Job type (e.g., 'Full-time', 'Remote')")
    max_results: int = Field(default=20, description="Maximum number of jobs to return")
    company_filter: Optional[List[str]] = Field(default=None, description="Filter by specific companies")


class SearchRequest(BaseModel):
    """Combined search request."""
    search_type: SearchType = Field(..., description="Type of search to perform")
    github_config: Optional[GitHubSearchConfig] = Field(default=None, description="GitHub search configuration")
    linkedin_config: Optional[LinkedInJobSearchConfig] = Field(default=None, description="LinkedIn job search configuration")
    output_format: str = Field(default="markdown", description="Output format: 'markdown', 'json', 'pdf'")


class SearchResponse(BaseModel):
    """Search result response."""
    search_id: str
    status: str
    message: str
    result: Optional[Dict[str, Any]] = None


router = APIRouter(prefix="/api/search", tags=["search"])


async def _process_github_search(config: GitHubSearchConfig, output_queue: asyncio.Queue):
    """Process GitHub profile search."""
    try:
        await output_queue.put({
            'event': 'progress_update',
            'status': 'started',
            'message': f'Starting GitHub profile analysis for {config.username}'
        })

        from github_resume_generator.crew import GithubResumeGenerator

        resume_loop = asyncio.get_running_loop()

        def update_hook(msg) -> None:
            resume_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(output_queue.put({
                    'event': 'progress_update',
                    'task': getattr(msg, 'name', 'processing'),
                    'summary': getattr(msg, 'summary', ''),
                    'status': 'task_done'
                }))
            )

        crew = GithubResumeGenerator().crew(
            task_callback=update_hook,
            step_callback=update_hook
        )

        result = await crew.kickoff_async(inputs=dict(
            username=config.username,
            max_repos=config.max_repos
        ))

        await output_queue.put({
            'status': 'completed',
            'output': result.raw,
            'type': 'github_resume'
        })
    except Exception as e:
        await output_queue.put({
            'status': 'error',
            'message': str(e),
            'type': 'github_resume'
        })


async def _process_linkedin_search(config: LinkedInJobSearchConfig, output_queue: asyncio.Queue):
    """Process LinkedIn job search using browser automation."""
    try:
        await output_queue.put({
            'event': 'progress_update',
            'status': 'started',
            'message': f'Searching LinkedIn for jobs matching: {", ".join(config.keywords)}'
        })

        # Import computer use agent
        from computer_use.agent import ComputerUseAgent, BrowserEnvironment
        import os

        await output_queue.put({
            'event': 'progress_update',
            'status': 'initializing',
            'message': 'Starting browser automation...'
        })

        # Check if LinkedIn credentials are available
        has_credentials = bool(os.environ.get("LINKEDIN_USERNAME") and os.environ.get("LINKEDIN_PASSWORD"))

        # Initialize browser automation agent
        async with ComputerUseAgent(
            environment=BrowserEnvironment.PLAYWRIGHT,
            headless=True  # Run headless in production
        ) as agent:
            await output_queue.put({
                'event': 'progress_update',
                'status': 'searching',
                'message': 'Searching LinkedIn jobs...'
            })

            # Search LinkedIn jobs
            jobs = await agent.search_linkedin_jobs(
                keywords=config.keywords,
                location=config.location,
                experience_level=config.experience_level,
                job_type=config.job_type,
                max_results=config.max_results,
                require_auth=has_credentials  # Only authenticate if credentials available
            )

            # Filter by company if specified
            if config.company_filter:
                jobs = [
                    job for job in jobs
                    if any(company.lower() in job['company'].lower() for company in config.company_filter)
                ]

            results = {
                'search_query': {
                    'keywords': config.keywords,
                    'location': config.location,
                    'experience_level': config.experience_level,
                    'job_type': config.job_type,
                    'company_filter': config.company_filter
                },
                'jobs_found': len(jobs),
                'jobs': jobs,
                'authenticated': has_credentials,
                'message': f'Found {len(jobs)} matching jobs on LinkedIn'
            }

            await output_queue.put({
                'status': 'completed',
                'output': results,
                'type': 'linkedin_jobs'
            })

    except Exception as e:
        await output_queue.put({
            'status': 'error',
            'message': str(e),
            'type': 'linkedin_jobs'
        })


async def _process_combined_search(
    github_config: Optional[GitHubSearchConfig],
    linkedin_config: Optional[LinkedInJobSearchConfig],
    output_queue: asyncio.Queue
):
    """Process combined GitHub and LinkedIn search."""
    try:
        await output_queue.put({
            'event': 'progress_update',
            'status': 'started',
            'message': 'Starting combined search...'
        })

        results = {}

        # Process GitHub search if configured
        if github_config:
            github_queue = asyncio.Queue()
            await _process_github_search(github_config, github_queue)

            # Collect GitHub results
            while True:
                msg = await github_queue.get()
                await output_queue.put(msg)
                if msg.get('status') in ['completed', 'error']:
                    if msg.get('status') == 'completed':
                        results['github'] = msg.get('output')
                    break

        # Process LinkedIn search if configured
        if linkedin_config:
            linkedin_queue = asyncio.Queue()
            await _process_linkedin_search(linkedin_config, linkedin_queue)

            # Collect LinkedIn results
            while True:
                msg = await linkedin_queue.get()
                await output_queue.put(msg)
                if msg.get('status') in ['completed', 'error']:
                    if msg.get('status') == 'completed':
                        results['linkedin'] = msg.get('output')
                    break

        await output_queue.put({
            'status': 'completed',
            'output': results,
            'type': 'combined'
        })
    except Exception as e:
        await output_queue.put({
            'status': 'error',
            'message': str(e),
            'type': 'combined'
        })


@router.post("/execute", response_class=StreamingResponse)
async def execute_search(request: SearchRequest):
    """
    Execute a configurable search with streaming results.

    Supports:
    - GitHub profile analysis and resume generation
    - LinkedIn job search (with browser automation support coming soon)
    - Combined searches

    Returns a Server-Sent Events stream with progress updates.
    """

    # Validate request
    if request.search_type == SearchType.GITHUB_RESUME and not request.github_config:
        raise HTTPException(status_code=400, detail="github_config required for GitHub resume search")

    if request.search_type == SearchType.LINKEDIN_JOBS and not request.linkedin_config:
        raise HTTPException(status_code=400, detail="linkedin_config required for LinkedIn job search")

    if request.search_type == SearchType.COMBINED:
        if not request.github_config and not request.linkedin_config:
            raise HTTPException(
                status_code=400,
                detail="At least one of github_config or linkedin_config required for combined search"
            )

    async def generate_updates():
        """Stream search updates to client."""
        update_queue = asyncio.Queue()

        # Start appropriate search task
        if request.search_type == SearchType.GITHUB_RESUME:
            search_task = asyncio.create_task(
                _process_github_search(request.github_config, update_queue)
            )
        elif request.search_type == SearchType.LINKEDIN_JOBS:
            search_task = asyncio.create_task(
                _process_linkedin_search(request.linkedin_config, update_queue)
            )
        else:  # COMBINED
            search_task = asyncio.create_task(
                _process_combined_search(
                    request.github_config,
                    request.linkedin_config,
                    update_queue
                )
            )

        data_task = asyncio.create_task(update_queue.get())
        heartbeat_task = asyncio.create_task(asyncio.sleep(5))

        try:
            while True:
                done, pending = await asyncio.wait(
                    [data_task, heartbeat_task],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=120,
                )

                if data_task in done:
                    update = await data_task

                    output = ''
                    if event := update.pop('event', None):
                        output += f'event: {event}\n'

                    output += f"data: {json.dumps(update)}\n\n"
                    yield output

                    data_task = asyncio.create_task(update_queue.get())

                    if update.get('status') in ['completed', 'error']:
                        break

                elif heartbeat_task in done:
                    yield "event: ping\ndata: {}\n\n"
                    heartbeat_task = asyncio.create_task(asyncio.sleep(5))

                elif not done and pending:
                    raise asyncio.TimeoutError("Stream timed out.")

        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'status': 'error', 'message': 'Stream timed out.'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': f'An error occurred: {str(e)}'})}\n\n"

        finally:
            if not search_task.done():
                search_task.cancel()
            if not heartbeat_task.done():
                heartbeat_task.cancel()
            if not data_task.done():
                data_task.cancel()

            await asyncio.gather(search_task, heartbeat_task, return_exceptions=True)

    return StreamingResponse(generate_updates(), media_type="text/event-stream")


@router.get("/config/template/{search_type}")
async def get_config_template(search_type: SearchType):
    """Get a configuration template for a specific search type."""
    templates = {
        SearchType.GITHUB_RESUME: {
            "search_type": "github_resume",
            "github_config": GitHubSearchConfig(
                username="example_user",
                include_projects=True,
                include_contributions=True,
                max_repos=10
            ).dict(),
            "output_format": "markdown"
        },
        SearchType.LINKEDIN_JOBS: {
            "search_type": "linkedin_jobs",
            "linkedin_config": LinkedInJobSearchConfig(
                keywords=["Python", "Machine Learning"],
                location="San Francisco, CA",
                experience_level="Mid-Senior",
                job_type="Full-time",
                max_results=20
            ).dict(),
            "output_format": "json"
        },
        SearchType.COMBINED: {
            "search_type": "combined",
            "github_config": GitHubSearchConfig(
                username="example_user",
                max_repos=10
            ).dict(),
            "linkedin_config": LinkedInJobSearchConfig(
                keywords=["Python", "AI"],
                location="Remote",
                max_results=20
            ).dict(),
            "output_format": "markdown"
        }
    }

    return templates.get(search_type)
