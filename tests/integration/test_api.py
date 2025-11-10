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

"""Integration tests for API endpoints."""

import pytest
import json


class TestAPIIntegration:
    """Integration tests for the complete API flow."""

    def test_api_docs_available(self, test_client):
        """Test that API documentation is accessible."""
        response = test_client.get("/api/docs")
        assert response.status_code == 200

    def test_redoc_available(self, test_client):
        """Test that ReDoc documentation is accessible."""
        response = test_client.get("/api/redoc")
        assert response.status_code == 200

    def test_home_page_loads(self, test_client):
        """Test that home page loads correctly."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_health_endpoints_accessible(self, test_client):
        """Test all health endpoints are accessible."""
        endpoints = ["/health/live", "/health/ready", "/health/", "/health/metrics"]

        for endpoint in endpoints:
            response = test_client.get(endpoint)
            assert response.status_code in [200, 503], f"Endpoint {endpoint} failed"

    def test_search_config_templates_accessible(self, test_client):
        """Test search configuration templates are accessible."""
        search_types = ["github_resume", "linkedin_jobs", "combined"]

        for search_type in search_types:
            response = test_client.get(f"/api/search/config/template/{search_type}")
            assert response.status_code == 200
            data = response.json()
            assert data["search_type"] == search_type


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_complete_github_search_flow(self, test_client, sample_search_config):
        """Test complete GitHub search workflow."""
        # 1. Get template
        template_response = test_client.get("/api/search/config/template/github_resume")
        assert template_response.status_code == 200

        # 2. Customize and submit search
        search_request = {
            "search_type": "github_resume",
            "github_config": sample_search_config["github_config"],
            "output_format": "markdown"
        }

        # Note: This will return a streaming response
        # In a real test, you'd need to handle the stream
        response = test_client.post("/api/search/execute", json=search_request)
        assert response.status_code == 200

    def test_error_handling_workflow(self, test_client):
        """Test error handling in API workflow."""
        # Send invalid request
        invalid_request = {
            "search_type": "invalid_type"
        }

        response = test_client.post("/api/search/execute", json=invalid_request)
        assert response.status_code == 422  # Validation error
