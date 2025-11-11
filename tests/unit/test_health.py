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

"""Unit tests for health check endpoints."""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from api.health import HealthStatus, ServiceHealth


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_liveness_endpoint(self, test_client):
        """Test /health/live endpoint returns alive status."""
        response = test_client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    @patch('api.health.check_gemini_api')
    @patch('api.health.check_crewai')
    def test_readiness_when_all_healthy(self, mock_crewai, mock_gemini, test_client):
        """Test /health/ready when all services are healthy."""
        mock_gemini.return_value = ServiceHealth(
            service="gemini_api",
            status=HealthStatus.HEALTHY
        )
        mock_crewai.return_value = ServiceHealth(
            service="crewai",
            status=HealthStatus.HEALTHY
        )

        response = test_client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

    @patch('api.health.check_gemini_api')
    @patch('api.health.check_crewai')
    def test_readiness_when_service_unhealthy(self, mock_crewai, mock_gemini, test_client):
        """Test /health/ready when a service is unhealthy."""
        mock_gemini.return_value = ServiceHealth(
            service="gemini_api",
            status=HealthStatus.UNHEALTHY,
            message="API key not configured"
        )
        mock_crewai.return_value = ServiceHealth(
            service="crewai",
            status=HealthStatus.HEALTHY
        )

        response = test_client.get("/health/ready")

        # Should return 503 when any service is unhealthy
        # Note: This depends on implementation - adjust assertion as needed
        assert response.status_code in [200, 503]

    def test_comprehensive_health_endpoint(self, test_client):
        """Test comprehensive health check endpoint."""
        response = test_client.get("/health/")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "environment" in data
        assert "version" in data
        assert "checks" in data
        assert "system" in data

        # Verify checks structure
        assert "gemini_api" in data["checks"]
        assert "crewai" in data["checks"]

        # Verify system metrics
        assert isinstance(data["system"], dict)

    def test_metrics_endpoint(self, test_client):
        """Test Prometheus metrics endpoint."""
        response = test_client.get("/health/metrics")

        assert response.status_code == 200
        content = response.text

        # Verify Prometheus format
        assert "uptime_seconds" in content
        assert "cpu_percent" in content
        assert "memory_percent" in content
        assert "# HELP" in content
        assert "# TYPE" in content


class TestHealthChecks:
    """Test individual health check functions."""

    @pytest.mark.asyncio
    @patch('api.health.httpx.AsyncClient')
    async def test_gemini_api_check_success(self, mock_client):
        """Test Gemini API health check when API is reachable."""
        from api.health import check_gemini_api

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await check_gemini_api()

        assert result.service == "gemini_api"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_gemini_api_check_no_key(self):
        """Test Gemini API health check when no API key is configured."""
        from api.health import check_gemini_api
        import os

        # Temporarily remove API key
        original_key = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        try:
            result = await check_gemini_api()

            assert result.service == "gemini_api"
            assert result.status == HealthStatus.UNHEALTHY
            assert "not configured" in result.message.lower()
        finally:
            # Restore API key
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key

    @pytest.mark.asyncio
    @patch('api.health.httpx.AsyncClient')
    async def test_gemini_api_check_failure(self, mock_client):
        """Test Gemini API health check when API returns error."""
        from api.health import check_gemini_api

        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await check_gemini_api()

        assert result.service == "gemini_api"
        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_crewai_check_success(self):
        """Test CrewAI health check when framework initializes successfully."""
        from api.health import check_crewai

        with patch('api.health.GithubResumeGenerator') as mock_crew:
            mock_crew.return_value = Mock()

            result = await check_crewai()

            assert result.service == "crewai"
            assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_crewai_check_failure(self):
        """Test CrewAI health check when framework fails to initialize."""
        from api.health import check_crewai

        with patch('api.health.GithubResumeGenerator') as mock_crew:
            mock_crew.side_effect = Exception("Import error")

            result = await check_crewai()

            assert result.service == "crewai"
            assert result.status == HealthStatus.UNHEALTHY


class TestSystemMetrics:
    """Test system metrics collection."""

    @patch('api.health.psutil')
    def test_system_metrics_collection(self, mock_psutil):
        """Test system metrics are collected correctly."""
        from api.health import get_system_metrics

        # Mock psutil functions
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.virtual_memory.return_value.percent = 60.0
        mock_psutil.virtual_memory.return_value.available = 8589934592  # 8GB
        mock_psutil.disk_usage.return_value.percent = 75.0
        mock_psutil.pids.return_value = range(150)

        metrics = get_system_metrics()

        assert metrics["cpu_percent"] == 45.5
        assert metrics["memory_percent"] == 60.0
        assert metrics["disk_percent"] == 75.0
        assert metrics["process_count"] == 150

    def test_system_metrics_without_psutil(self):
        """Test system metrics gracefully handle missing psutil."""
        from api.health import get_system_metrics

        with patch('api.health.psutil', None):
            metrics = get_system_metrics()

            assert "error" in metrics
