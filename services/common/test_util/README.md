# PostgreSQL Testing Utilities

This module provides utilities for testing services with real PostgreSQL databases using `gocept.testdb`.

## Overview

The `PostgresTestDB` base class provides a foundation for writing tests that use real PostgreSQL databases instead of mocks. This approach offers several benefits:

- **Real database behavior**: Tests run against actual PostgreSQL, catching real database issues
- **No mock complexity**: Eliminates the need to mock complex database interactions
- **Better test coverage**: Tests actual SQL queries and database constraints
- **Faster feedback**: Catches database-related bugs earlier in development

## Installation

Add `gocept.testdb` to your service's test dependencies:

```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "gocept.testdb>=2.0.0",
]
```

## Basic Usage

### 1. Inherit from PostgresTestDB

```python
from services.common.test_util import PostgresTestDB
from services.contacts.database import metadata

class TestMyService(PostgresTestDB):
    def setup_method(self):
        super().setup_method()
        # Use your service's metadata
        self.metadata = metadata
```

### 2. Set up and tear down tables

```python
async def async_setup(self):
    """Create tables before each test."""
    await self.create_tables()
    
async def async_teardown(self):
    """Drop tables after each test."""
    await self.drop_tables()
```

### 3. Use database sessions

```python
@pytest.fixture
async def session(self):
    """Provide database session for tests."""
    async with self.get_session() as session:
        yield session

@pytest.mark.asyncio
async def test_my_function(self, session):
    await self.async_setup()
    try:
        # Your test code here
        # Use the real session to make database calls
        pass
    finally:
        await self.async_teardown()
```

## Complete Example

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from services.common.test_util import PostgresTestDB
from services.contacts.database import metadata
from services.contacts.models.contact import Contact

class TestContactService(PostgresTestDB):
    def setup_method(self):
        super().setup_method()
        self.metadata = metadata
        
    async def async_setup(self):
        await self.create_tables()
        
    async def async_teardown(self):
        await self.drop_tables()
        
    @pytest.fixture
    async def session(self):
        async with self.get_session() as session:
            yield session
            
    @pytest.mark.asyncio
    async def test_create_contact(self, session: AsyncSession):
        await self.async_setup()
        try:
            # Create a contact
            contact = Contact(
                user_id="test_user",
                email_address="test@example.com",
                display_name="Test User",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
            )
            
            session.add(contact)
            await session.commit()
            await session.refresh(contact)
            
            # Verify it was created
            assert contact.id is not None
            
            # Query from database
            result = await session.execute(
                select(Contact).where(Contact.email_address == "test@example.com")
            )
            db_contact = result.scalar_one_or_none()
            assert db_contact is not None
            
        finally:
            await self.async_teardown()
```

## Converting Existing Tests

### Before (Mock-based)

```python
async def test_create_contact_mock(self, mock_session, sample_contact_data):
    # Mock database operations
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    
    # Test service method
    result = await contact_service.create_contact(mock_session, sample_contact_data)
    
    # Verify mocks were called
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
```

### After (Real database)

```python
@pytest.mark.asyncio
async def test_create_contact_real_db(self, session: AsyncSession):
    await self.async_setup()
    try:
        # Test with real database
        contact = Contact(...)
        session.add(contact)
        await session.commit()
        
        # Verify actual database state
        result = await session.execute(select(Contact).where(...))
        db_contact = result.scalar_one_or_none()
        assert db_contact is not None
        
    finally:
        await self.async_teardown()
```

## Key Benefits

1. **Real database constraints**: Tests actual foreign keys, unique constraints, etc.
2. **SQL validation**: Catches SQL syntax errors and invalid queries
3. **Transaction behavior**: Tests actual commit/rollback behavior
4. **Performance insights**: Real database performance characteristics
5. **Integration testing**: Tests the full database stack

## Best Practices

1. **Always use try/finally**: Ensure tables are cleaned up even if tests fail
2. **Isolate tests**: Each test should create its own data
3. **Use fixtures**: Leverage pytest fixtures for common setup
4. **Test cleanup**: Verify that data is properly removed after tests
5. **Async setup/teardown**: Use async methods for database operations

## Troubleshooting

### Common Issues

1. **Port conflicts**: `gocept.testdb` automatically finds available ports
2. **Permission errors**: The test database runs with full permissions
3. **Connection timeouts**: Tests should complete quickly with small datasets

### Debugging

Enable SQL logging by setting `echo=True` in the engine creation:

```python
self._engine = create_async_engine(
    self._database_url,
    echo=True,  # Enable SQL logging
    future=True
)
```

## Migration Path

1. **Start small**: Convert one test file at a time
2. **Keep mocks**: Some tests may still benefit from mocking
3. **Parallel development**: Run both mock and real database tests during transition
4. **CI integration**: Ensure CI environment supports PostgreSQL testing
