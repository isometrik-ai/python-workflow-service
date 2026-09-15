# Python Work Order Service Tests

This directory contains tests for the Python Work Order Service. The tests are organized by module type to ensure comprehensive coverage of the codebase.

## Test Structure

- **api/v1**: Tests for API endpoints
- **core**: Tests for core functionality like utils and services
- **crud**: Tests for database operations
- **models**: Tests for SQLAlchemy models
- **schemas**: Tests for Pydantic schemas

## Running Tests

### Running All Tests

To run all tests with coverage reporting:

```bash
python tests/run_tests.py
```

Or you can use pytest directly:

```bash
pytest -xvs --cov=src --cov-report=term --cov-report=html:htmlcov --cov-config=.coveragerc
```

### Running Specific Tests

To run tests for a specific module:

```bash
pytest tests/v1/test_posts.py -v
```

To run a specific test function:

```bash
pytest tests/v1/test_posts.py::test_create_post_success -v
```

## Coverage Reports

The test suite is configured to generate coverage reports in multiple formats:

- **Terminal**: Basic coverage statistics are displayed in the terminal after the tests run
- **HTML**: A detailed HTML report is generated in the `htmlcov` directory

To view the HTML coverage report, open `htmlcov/index.html` in a web browser.

## Test Configuration

- `.coveragerc`: Controls how coverage is measured and reported
- `conftest.py`: Contains pytest fixtures that can be used across all tests
- `requirements-dev.txt`: Development requirements including testing libraries

## Required Coverage

The project requires at least 85% code coverage. Current areas of focus include:

- API endpoint handlers
- CRUD operations
- Data validation
- Business logic

## Writing New Tests

When adding new features or fixing bugs, please also add or update tests to maintain the 85% coverage requirement.

### Test Naming Convention

- Test files should be named `test_*.py`
- Test functions should be named `test_*`
- Test classes (if used) should be named `Test*`

### Fixture Guidelines

- Create fixtures in conftest.py if they're used across multiple test files
- Create fixtures in test files if they're only used within that file
- Keep fixtures focused and well-documented

### Mocking Guidelines

- Use the `unittest.mock` module for mocking
- Prefer using `patch` as a context manager or decorator
- Mock at the lowest level possible to keep tests focused
- Verify interactions with mocks to ensure correct behavior
