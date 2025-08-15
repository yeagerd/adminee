# Meetings Service Test Suite

This directory contains comprehensive unit tests for the Meetings Service, covering all major functionality including public booking endpoints, availability calculation, calendar integration, and security features.

## Test Structure

### Core Test Files

- **`test_booking_endpoints.py`** - Tests for public booking API endpoints
- **`test_availability_service.py`** - Tests for availability calculation logic
- **`test_calendar_integration.py`** - Tests for Office Service integration
- **`test_security.py`** - Tests for security and validation functions

### Test Configuration

- **`test_base.py`** - Base test classes and common setup
- **`meetings_test_base.py`** - Meetings-specific test base classes

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-mock
```

2. Ensure you're in the meetings service directory:
```bash
cd services/meetings
```

### Running All Tests

#### Option 1: Using the test runner script
```bash
python run_tests.py
```

#### Option 2: Using pytest directly
```bash
cd tests
pytest -v
```

#### Option 3: Running specific test files
```bash
cd tests
pytest test_booking_endpoints.py -v
pytest test_availability_service.py -v
pytest test_calendar_integration.py -v
pytest test_security.py -v
```

### Running Specific Tests

```bash
# Run a specific test class
pytest test_booking_endpoints.py::TestBookingEndpoints -v

# Run a specific test method
pytest test_booking_endpoints.py::TestBookingEndpoints::test_get_public_link_success -v

# Run tests matching a pattern
pytest -k "availability" -v

# Run tests with specific markers
pytest -m "slow" -v
```

## Test Features

### Mocking and Isolation

All tests use proper mocking to isolate the unit under test:

- **Office Service calls** are mocked to avoid external dependencies
- **Database operations** use in-memory SQLite for fast, isolated testing
- **HTTP clients** are mocked to prevent actual network calls
- **External services** are mocked to ensure test reliability

### Test Data Management

- **Database setup/teardown** ensures clean state between tests
- **Sample data** covers various edge cases and scenarios
- **Test methods** create their own test data as needed

### Coverage Areas

#### Booking Endpoints (`test_booking_endpoints.py`)
- ✅ Public link retrieval
- ✅ Availability calculation
- ✅ Different meeting durations
- ✅ Error handling
- ✅ Rate limiting
- ✅ Timezone handling

#### Availability Service (`test_availability_service.py`)
- ✅ Office service integration
- ✅ Slot filtering and processing
- ✅ Business hours enforcement
- ✅ Buffer time handling
- ✅ Advance booking windows
- ✅ Daily/weekly limits

#### Calendar Integration (`test_calendar_integration.py`)
- ✅ HTTP client management
- ✅ API request formatting
- ✅ Response processing
- ✅ Error handling (HTTP errors, network issues, timeouts)
- ✅ Authentication headers
- ✅ Timezone handling

#### Security Service (`test_security.py`)
- ✅ Token format validation
- ✅ One-time link validation
- ✅ Rate limiting
- ✅ Access control
- ✅ Edge case handling

## Test Configuration

### Environment Variables

Tests automatically set required environment variables:
- `API_MEETINGS_OFFICE_KEY` = "test-meetings-office-key"
- `API_MEETINGS_USER_KEY` = "test-meetings-user-key"
- `OFFICE_SERVICE_URL` = "http://localhost:8003"
- `USER_SERVICE_URL` = "http://localhost:8001"

### Database Configuration

- Uses in-memory SQLite for fast execution
- Tables are created fresh for each test
- Sessions are managed automatically
- No external database required

## Writing New Tests

### Test Class Structure

```python
class TestNewFeature(BaseMeetingsTest):
    """Test suite for new feature."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        # Add test-specific setup here
    
    def test_feature_behavior(self):
        """Test the main behavior of the feature."""
        # Test implementation here
        pass
```

### Using Test Data

```python
def test_with_test_data(self):
    """Test using test data created in setup_method."""
    # Use the test data created in setup_method
    booking_link = self.sample_booking_link_data
    settings = self.mock_settings
    # Test implementation here
```

### Mocking External Dependencies

```python
@patch('services.meetings.services.external_service.call_external')
def test_with_mocked_external_service(self, mock_external):
    """Test with mocked external service."""
    mock_external.return_value = {"result": "success"}
    # Test implementation here
```

## Best Practices

### Test Naming
- Use descriptive test names that explain the scenario
- Follow the pattern: `test_[scenario]_[expected_behavior]`
- Example: `test_get_public_availability_with_expired_link`

### Assertions
- Use specific assertions rather than generic ones
- Include helpful error messages in assertions
- Test both positive and negative cases

### Test Isolation
- Each test should be independent
- Use `setup_method` for test-specific setup
- Avoid sharing state between tests

### Error Testing
- Test error conditions and edge cases
- Verify error handling behavior
- Test with malformed or invalid inputs

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're running from the correct directory
2. **Database errors**: Check that SQLite is available
3. **Mock issues**: Verify patch paths match the actual import paths
4. **Async test errors**: Ensure `pytest-asyncio` is installed

### Debug Mode

Run tests with more verbose output:
```bash
pytest -v -s --tb=long
```

### Test Discovery

Check which tests are discovered:
```bash
pytest --collect-only
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

- **Fast execution** - Complete test suite runs in under 30 seconds
- **No external dependencies** - All external services are mocked
- **Deterministic results** - Tests produce consistent results
- **Coverage reporting** - Can be integrated with coverage tools

## Contributing

When adding new functionality:

1. **Write tests first** - Follow TDD principles
2. **Cover edge cases** - Test error conditions and boundary values
3. **Maintain isolation** - Ensure tests don't interfere with each other
4. **Update documentation** - Keep this README current
5. **Run full suite** - Ensure all tests pass before submitting
