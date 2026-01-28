# Contributing to SQLlog

Thank you for your interest in contributing to SQLlog! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - Python version (`python --version`)
   - Operating system and version
   - PLC model and firmware version
   - SQL Server version
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant log output

### Suggesting Features

1. Check existing issues and discussions
2. Use the feature request template
3. Describe the use case and benefits
4. Consider backwards compatibility

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Add or update tests as needed
5. Ensure all tests pass
6. Update documentation if applicable
7. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/SQLlog.git
cd SQLlog

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8

# Run tests
pytest

# Run linter
flake8 src tests

# Format code
black src tests
```

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Use type hints where practical

### Example

```python
def read_recipe(self, tag: str = "RECIPE[0]") -> dict | None:
    """
    Read recipe data from PLC.

    Args:
        tag: PLC tag address for recipe UDT

    Returns:
        Recipe data dictionary or None if read fails
    """
    with self._lock:
        result = self._driver.read(tag)
        if result.error:
            self.logger.error(f"Failed to read {tag}: {result.error}")
            return None
        return result.value
```

## Testing

- Write tests for new functionality
- Maintain or improve code coverage
- Use mocks for external dependencies (PLC, SQL)
- Test edge cases and error conditions

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_handshake.py::test_idle_to_triggered -v
```

## Commit Messages

Use clear, descriptive commit messages:

```
Add fault recovery to handshake state machine

- Monitor for PLC reset when in FAULT state
- Clear error code when trigger returns to IDLE
- Add status callback for tray app integration
```

## Documentation

- Update README.md for user-facing changes
- Update relevant docs/ files for detailed changes
- Add inline comments for complex logic
- Keep CHANGELOG.md updated

## Questions?

Feel free to open an issue for questions or discussions about contributing.
