# Contributing

We welcome contributions to this project! Here's how you can help:

## How to Contribute

1. **Fork the Repository**
   - Fork this repository to your own GitHub account
   - Clone your fork locally

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**
   - Write clear, readable code
   - Follow existing code style and conventions
   - Add tests for new functionality
   - Update documentation as needed

4. **Test Your Changes**
   ```bash
   # Install dev dependencies
   uv sync --dev

   # Run tests
   uv run pytest

   # Run linter
   uv run ruff check .
   ```

5. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

6. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   - Open a pull request on GitHub
   - Describe your changes clearly
   - Reference any related issues

## Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write descriptive commit messages
- Keep functions focused and small

## Testing

- Add tests for new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage

## Documentation

- Update README.md if adding new features
- Add docstrings to new functions and classes
- Update API_GUIDE.md for API changes

## Questions?

Open an issue for questions or discussions.

Thank you for contributing!
