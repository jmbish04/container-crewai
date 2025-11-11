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

"""Unit tests for search configuration API."""

import pytest
from api.search_config import SearchType, GitHubSearchConfig, LinkedInJobSearchConfig


class TestSearchConfigModels:
    """Test search configuration Pydantic models."""

    def test_github_search_config_defaults(self):
        """Test GitHubSearchConfig with default values."""
        config = GitHubSearchConfig(username="testuser")

        assert config.username == "testuser"
        assert config.include_projects is True
        assert config.include_contributions is True
        assert config.max_repos == 10

    def test_github_search_config_custom(self):
        """Test GitHubSearchConfig with custom values."""
        config = GitHubSearchConfig(
            username="testuser",
            include_projects=False,
            include_contributions=False,
            max_repos=5
        )

        assert config.username == "testuser"
        assert config.include_projects is False
        assert config.include_contributions is False
        assert config.max_repos == 5

    def test_linkedin_search_config_minimal(self):
        """Test LinkedInJobSearchConfig with minimal requirements."""
        config = LinkedInJobSearchConfig(
            keywords=["Python", "AI"]
        )

        assert config.keywords == ["Python", "AI"]
        assert config.location is None
        assert config.max_results == 20

    def test_linkedin_search_config_full(self):
        """Test LinkedInJobSearchConfig with all fields."""
        config = LinkedInJobSearchConfig(
            keywords=["Python", "Machine Learning"],
            location="San Francisco, CA",
            experience_level="Mid-Senior",
            job_type="Full-time",
            max_results=50,
            company_filter=["Google", "Meta"]
        )

        assert config.keywords == ["Python", "Machine Learning"]
        assert config.location == "San Francisco, CA"
        assert config.experience_level == "Mid-Senior"
        assert config.job_type == "Full-time"
        assert config.max_results == 50
        assert config.company_filter == ["Google", "Meta"]


class TestSearchConfigEndpoints:
    """Test search configuration API endpoints."""

    def test_get_github_config_template(self, test_client):
        """Test GET /api/search/config/template/github_resume."""
        response = test_client.get("/api/search/config/template/github_resume")

        assert response.status_code == 200
        data = response.json()

        assert data["search_type"] == "github_resume"
        assert "github_config" in data
        assert "username" in data["github_config"]
        assert data["output_format"] == "markdown"

    def test_get_linkedin_config_template(self, test_client):
        """Test GET /api/search/config/template/linkedin_jobs."""
        response = test_client.get("/api/search/config/template/linkedin_jobs")

        assert response.status_code == 200
        data = response.json()

        assert data["search_type"] == "linkedin_jobs"
        assert "linkedin_config" in data
        assert "keywords" in data["linkedin_config"]
        assert data["output_format"] == "json"

    def test_get_combined_config_template(self, test_client):
        """Test GET /api/search/config/template/combined."""
        response = test_client.get("/api/search/config/template/combined")

        assert response.status_code == 200
        data = response.json()

        assert data["search_type"] == "combined"
        assert "github_config" in data
        assert "linkedin_config" in data
        assert data["output_format"] == "markdown"

    def test_execute_search_missing_github_config(self, test_client):
        """Test POST /api/search/execute with missing github_config."""
        payload = {
            "search_type": "github_resume"
            # Missing github_config
        }

        response = test_client.post("/api/search/execute", json=payload)

        assert response.status_code == 400
        assert "github_config required" in response.json()["detail"]

    def test_execute_search_missing_linkedin_config(self, test_client):
        """Test POST /api/search/execute with missing linkedin_config."""
        payload = {
            "search_type": "linkedin_jobs"
            # Missing linkedin_config
        }

        response = test_client.post("/api/search/execute", json=payload)

        assert response.status_code == 400
        assert "linkedin_config required" in response.json()["detail"]

    def test_execute_search_combined_missing_both(self, test_client):
        """Test POST /api/search/execute combined without any config."""
        payload = {
            "search_type": "combined"
            # Missing both configs
        }

        response = test_client.post("/api/search/execute", json=payload)

        assert response.status_code == 400
        assert "at least one" in response.json()["detail"].lower()


class TestSearchExecution:
    """Test search execution logic."""

    @pytest.mark.asyncio
    async def test_github_search_process(self, sample_github_profile, mock_crewai_crew):
        """Test GitHub search processing."""
        from api.search_config import _process_github_search, GitHubSearchConfig
        import asyncio

        config = GitHubSearchConfig(username="testuser")
        queue = asyncio.Queue()

        await _process_github_search(config, queue)

        # Check that progress updates were queued
        updates = []
        while not queue.empty():
            updates.append(await queue.get())

        assert len(updates) > 0
        assert any(u.get('status') == 'started' for u in updates)

    @pytest.mark.asyncio
    async def test_linkedin_search_process(self):
        """Test LinkedIn search processing."""
        from api.search_config import _process_linkedin_search, LinkedInJobSearchConfig
        import asyncio

        config = LinkedInJobSearchConfig(
            keywords=["Python", "AI"],
            location="San Francisco"
        )
        queue = asyncio.Queue()

        await _process_linkedin_search(config, queue)

        # Check that progress updates were queued
        updates = []
        while not queue.empty():
            updates.append(await queue.get())

        assert len(updates) > 0
        # Verify structure of response
        completed = [u for u in updates if u.get('status') == 'completed']
        assert len(completed) > 0
        assert completed[0].get('type') == 'linkedin_jobs'
