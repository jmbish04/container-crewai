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

"""Health check endpoints for monitoring container status."""

import asyncio
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, status
from pydantic import BaseModel

try:
    import psutil
except ImportError:
    psutil = None


class HealthStatus(str, Enum):
    """Health status enum."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Individual service health check result."""
    service: str
    status: HealthStatus
    message: Optional[str] = None
    response_time_ms: Optional[float] = None


class HealthResponse(BaseModel):
    """Comprehensive health check response."""
    status: HealthStatus
    timestamp: str
    uptime_seconds: float
    environment: str
    version: str
    checks: Dict[str, ServiceHealth]
    system: Dict[str, Any]


router = APIRouter(prefix="/health", tags=["health"])

# Track startup time
START_TIME = datetime.now(timezone.utc)


def get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics."""
    if not psutil:
        return {"error": "psutil not available"}

    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
            "disk_percent": psutil.disk_usage('/').percent,
            "process_count": len(psutil.pids()),
        }
    except Exception as e:
        return {"error": str(e)}


async def check_gemini_api() -> ServiceHealth:
    """Check Gemini API connectivity."""
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return ServiceHealth(
                service="gemini_api",
                status=HealthStatus.UNHEALTHY,
                message="API key not configured"
            )

        # Simple connectivity check
        start = datetime.now()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
                timeout=5.0
            )

        elapsed = (datetime.now() - start).total_seconds() * 1000

        if response.status_code == 200:
            return ServiceHealth(
                service="gemini_api",
                status=HealthStatus.HEALTHY,
                message="Connected",
                response_time_ms=elapsed
            )
        else:
            return ServiceHealth(
                service="gemini_api",
                status=HealthStatus.DEGRADED,
                message=f"Status code: {response.status_code}",
                response_time_ms=elapsed
            )
    except Exception as e:
        return ServiceHealth(
            service="gemini_api",
            status=HealthStatus.UNHEALTHY,
            message=str(e)
        )


async def check_crewai() -> ServiceHealth:
    """Check CrewAI framework status."""
    try:
        from github_resume_generator.crew import GithubResumeGenerator

        # Try to initialize crew config without running
        crew_instance = GithubResumeGenerator()

        return ServiceHealth(
            service="crewai",
            status=HealthStatus.HEALTHY,
            message="Framework initialized"
        )
    except Exception as e:
        return ServiceHealth(
            service="crewai",
            status=HealthStatus.UNHEALTHY,
            message=str(e)
        )


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness():
    """Simple liveness check for Kubernetes/Cloudflare."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness():
    """Readiness check - verifies all dependencies are available."""
    checks = await asyncio.gather(
        check_gemini_api(),
        check_crewai(),
        return_exceptions=True
    )

    all_healthy = all(
        check.status == HealthStatus.HEALTHY
        for check in checks
        if isinstance(check, ServiceHealth)
    )

    if not all_healthy:
        check_results = [
            check.dict() if isinstance(check, ServiceHealth) else {"error": str(check)}
            for check in checks
        ]
        return {
            "ready": False,
            "checks": check_results
        }, status.HTTP_503_SERVICE_UNAVAILABLE

    return {"ready": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check with all service statuses."""
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()

    # Run all health checks
    gemini_health = await check_gemini_api()
    crewai_health = await check_crewai()

    # Determine overall status
    statuses = [gemini_health.status, crewai_health.status]
    if all(s == HealthStatus.HEALTHY for s in statuses):
        overall_status = HealthStatus.HEALTHY
    elif any(s == HealthStatus.UNHEALTHY for s in statuses):
        overall_status = HealthStatus.UNHEALTHY
    else:
        overall_status = HealthStatus.DEGRADED

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=uptime,
        environment=os.environ.get("ENVIRONMENT", "production"),
        version=os.environ.get("VERSION", "1.0.0"),
        checks={
            "gemini_api": gemini_health,
            "crewai": crewai_health,
        },
        system=get_system_metrics()
    )


@router.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint."""
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    metrics_data = get_system_metrics()

    # Format as Prometheus metrics
    lines = [
        "# HELP uptime_seconds Time since service start",
        "# TYPE uptime_seconds gauge",
        f"uptime_seconds {uptime}",
        "# HELP cpu_percent CPU usage percentage",
        "# TYPE cpu_percent gauge",
        f"cpu_percent {metrics_data.get('cpu_percent', 0)}",
        "# HELP memory_percent Memory usage percentage",
        "# TYPE memory_percent gauge",
        f"memory_percent {metrics_data.get('memory_percent', 0)}",
    ]

    return Response('\n'.join(lines), media_type='text/plain')
