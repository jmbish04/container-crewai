# Test Suite

Comprehensive test suite for the CrewAI Container Application.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_health.py      # Health check endpoint tests
│   └── test_search_config.py # Search configuration tests
├── integration/             # Integration tests
│   └── test_api.py         # Full API integration tests
└── fixtures/                # Test data and fixtures
```

## Running Tests

### Run All Tests

```bash
# Using uv
uv run pytest

# Using pytest directly
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit

# Integration tests only
pytest tests/integration

# Tests with specific marker
pytest -m unit
pytest -m integration
```

### Run with Coverage

```bash
# Terminal report
pytest --cov=src --cov-report=term-missing

# HTML report
pytest --cov=src --cov-report=html
# Then open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=src --cov-report=xml
```

### Run Specific Tests

```bash
# Single test file
pytest tests/unit/test_health.py

# Single test class
pytest tests/unit/test_health.py::TestHealthEndpoints

# Single test function
pytest tests/unit/test_health.py::TestHealthEndpoints::test_liveness_endpoint

# Tests matching a pattern
pytest -k "health"
```

### Verbose Output

```bash
# More verbose
pytest -v

# Even more verbose with output
pytest -vv -s
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation:

- **test_health.py**: Health check endpoints and system metrics
- **test_search_config.py**: Search configuration models and API

### Integration Tests (`tests/integration/`)

Test complete workflows and component interactions:

- **test_api.py**: End-to-end API workflows

## Writing Tests

### Using Fixtures

Fixtures are defined in `conftest.py`:

```python
def test_example(test_client, sample_github_profile):
    # test_client is a FastAPI TestClient
    # sample_github_profile is mock GitHub data
    response = test_client.get("/health/live")
    assert response.status_code == 200
```

### Async Tests

Mark async tests with `@pytest.mark.asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

### Mocking

Use `unittest.mock` or `pytest-mock`:

```python
from unittest.mock import patch, Mock

def test_with_mock():
    with patch('module.function') as mock_func:
        mock_func.return_value = "mocked"
        result = function_under_test()
        assert result == "expected"
```

## Continuous Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests

See `.github/workflows/test.yml` for CI configuration.

## Coverage Goals

- **Overall**: 80%+
- **Critical paths**: 90%+
- **API endpoints**: 100%

## Troubleshooting

### Tests Fail Locally

1. Ensure dependencies are installed:
   ```bash
   uv sync --dev
   ```

2. Check environment variables:
   ```bash
   export GEMINI_API_KEY=test-key
   ```

3. Clear pytest cache:
   ```bash
   pytest --cache-clear
   ```

### Async Tests Timeout

Increase timeout in `pytest.ini`:
```ini
[pytest]
asyncio_default_timeout = 10
```

### Import Errors

Ensure PYTHONPATH includes src:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
```

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
2. **AAA Pattern**: Arrange, Act, Assert
3. **Isolation**: Tests should not depend on each other
4. **Mocking**: Mock external dependencies (APIs, databases)
5. **Fixtures**: Use fixtures for common test data
6. **Markers**: Use markers to categorize tests

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
