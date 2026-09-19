---
sidebar_position: 2
title: Contributing
---

# Contributing

Contributions to philote-examples are welcome. This guide explains how to set up a development environment and submit changes.

## Getting Started

### 1. Fork and clone

Fork the repository on GitHub, then clone your fork:

```bash
git clone https://github.com/<your-username>/philote-examples.git
cd philote-examples
```

### 2. Install in development mode

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode along with development dependencies: `pytest`, `ruff`, and `pre-commit`.

### 3. Set up pre-commit hooks

```bash
pre-commit install
```

This configures automatic linting and formatting checks before each commit.

## Development Workflow

### Code style

This project uses [Ruff](https://docs.astral.sh/ruff/) for both linting and formatting:

```bash
# Check for lint errors
ruff check src/ tests/ examples/

# Auto-format code
ruff format src/ tests/ examples/
```

The project enforces:
- Line length of 88 characters
- PEP 8 naming conventions
- Import sorting (isort-compatible)
- Python 3.8+ syntax

### Running tests

```bash
# Run all tests (excluding XFOIL tests)
pytest

# Run XFOIL tests (requires XFOIL_PATH to be set)
pytest -m xfoil

# Run gradient validation tests
pytest tests/test_naca_gradients.py
```

### Adding a new discipline

If you are adding a new example discipline:

1. Create a new module under `src/philote_examples/`.
2. Add an example script under `examples/`.
3. Add tests under `tests/`.
4. Update the documentation under `docs/docs/`.
5. Export the discipline class from `src/philote_examples/__init__.py`.

## Submitting Changes

1. Create a feature branch from `main`.
2. Make your changes and ensure all tests pass.
3. Run `ruff check` and `ruff format` to ensure code style compliance.
4. Commit with a clear, descriptive message.
5. Push to your fork and open a pull request against `main`.

## Reporting Issues

Please use the [GitHub Issues](https://github.com/MDO-Standards/philote-examples/issues) page to report bugs or request features.
