# Contributing to Oiduna

Thank you for your interest in contributing to Oiduna!

## Development Setup

1. Fork and clone the repository
2. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Install dependencies: `uv sync`
4. Run tests: `uv run pytest`

## Code Style

- Python 3.13+
- Follow PEP 8
- Use ruff for linting: `uv run ruff check src/`
- Use mypy for type checking: `uv run mypy src`

## Testing

- Write tests for all new features
- Maintain >80% code coverage
- Run `uv run pytest --cov=src` before submitting PR

## Pull Request Process

1. Create a feature branch
2. Write tests
3. Update documentation
4. Submit PR with clear description

## Architecture Guidelines

Follow the 4-layer architecture:
- Domain: Business logic (no infrastructure dependencies)
- Infrastructure: Technical implementations
- Application: Use cases
- Interface: CLI and HTTP clients

See [ARCHITECTURE.md](ARCHITECTURE.md) for details.
