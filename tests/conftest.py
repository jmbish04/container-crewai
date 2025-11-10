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

"""Pytest configuration and shared fixtures."""

import asyncio
import os
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing application modules
os.environ["GEMINI_API_KEY"] = "test-gemini-key-12345"
os.environ["ENVIRONMENT"] = "test"
os.environ["VERSION"] = "test-1.0.0"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from api.service import app
    return TestClient(app)


@pytest.fixture
def mock_gemini_api():
    """Mock Gemini API responses."""
    with patch('google.generativeai.GenerativeModel') as mock:
        model_instance = Mock()
        model_instance.generate_content.return_value = Mock(
            text="Mocked response from Gemini API"
        )
        mock.return_value = model_instance
        yield mock


@pytest.fixture
def mock_crewai_crew():
    """Mock CrewAI crew execution."""
    with patch('github_resume_generator.crew.GithubResumeGenerator') as mock:
        crew_instance = Mock()
        result = Mock()
        result.raw = "# Generated Resume\n\nTest resume content"
        crew_instance.crew.return_value.kickoff_async.return_value = result
        mock.return_value = crew_instance
        yield mock


@pytest.fixture
def sample_github_profile():
    """Sample GitHub profile data for testing."""
    return {
        "username": "testuser",
        "name": "Test User",
        "bio": "Full Stack Developer",
        "location": "San Francisco, CA",
        "email": "test@example.com",
        "company": "Test Corp",
        "blog": "https://testuser.dev",
        "public_repos": 50,
        "followers": 100,
        "following": 50,
        "repositories": [
            {
                "name": "awesome-project",
                "description": "An awesome test project",
                "language": "Python",
                "stars": 150,
                "forks": 25,
                "url": "https://github.com/testuser/awesome-project"
            },
            {
                "name": "ml-toolkit",
                "description": "Machine learning utilities",
                "language": "Python",
                "stars": 89,
                "forks": 12,
                "url": "https://github.com/testuser/ml-toolkit"
            }
        ]
    }


@pytest.fixture
def sample_linkedin_jobs():
    """Sample LinkedIn job data for testing."""
    return {
        "search_query": {
            "keywords": ["Python", "Machine Learning"],
            "location": "San Francisco, CA",
            "job_type": "Full-time"
        },
        "total_results": 45,
        "jobs": [
            {
                "title": "Senior ML Engineer",
                "company": "AI Corp",
                "location": "San Francisco, CA",
                "description": "Looking for an experienced ML engineer...",
                "posted_date": "2025-01-05",
                "salary_range": "$150k - $200k",
                "url": "https://linkedin.com/jobs/12345"
            },
            {
                "title": "Python Developer",
                "company": "Tech Solutions Inc",
                "location": "Remote",
                "description": "Join our team as a Python developer...",
                "posted_date": "2025-01-08",
                "salary_range": "$120k - $160k",
                "url": "https://linkedin.com/jobs/67890"
            }
        ]
    }


@pytest.fixture
def sample_search_config():
    """Sample search configuration for testing."""
    return {
        "github_config": {
            "username": "testuser",
            "include_projects": True,
            "include_contributions": True,
            "max_repos": 10
        },
        "linkedin_config": {
            "keywords": ["Python", "AI", "ML"],
            "location": "San Francisco, CA",
            "experience_level": "Mid-Senior",
            "job_type": "Full-time",
            "max_results": 20
        }
    }
