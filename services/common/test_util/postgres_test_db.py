"""
Base test class for PostgreSQL-based tests using gocept.testdb.

This module provides a reusable base class that services can inherit from
to get PostgreSQL test database functionality without duplicating setup code.
"""

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import pytest
from gocept.testdb import PostgreSQL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlmodel import SQLModel


class PostgresTestDB:
    """
    Base class for PostgreSQL-based tests using gocept.testdb.
    
    This class provides:
    - Temporary PostgreSQL database setup/teardown
    - Async database engine and session management
    - Table creation/dropping utilities
    - Session fixtures for pytest
    """
    

        
    @classmethod
    def setup_class(cls):
        """Set up the test database once for the entire test class."""
        # Initialize metadata if not set
        if not hasattr(cls, 'metadata'):
            cls.metadata = SQLModel.metadata
            
        # Use existing Docker PostgreSQL container
        # Get connection details from environment or use defaults
        user = os.environ.get('POSTGRES_USER', 'postgres')
        password = os.environ.get('POSTGRES_PASSWORD', 'postgres')
        host = os.environ.get('POSTGRES_HOST', 'localhost')
        port = os.environ.get('POSTGRES_PORT', '5432')
        
        # Create a unique test database name
        cls._db_name = f"testdb_{id(cls)}"
        
        # Construct async database URL for the test database
        cls._database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{cls._db_name}"
        
        # Create async engine
        cls._engine = create_async_engine(
            cls._database_url,
            echo=False,
            future=True
        )
        
        # Create session factory
        cls._session_factory = sessionmaker(
            cls._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create the test database using SQL
        # We'll do this in a separate method that can be called when needed
        
    @classmethod
    async def create_test_database(cls):
        """Create the test database using SQL."""
        try:
            # Create a temporary engine to the default database to create the test database
            temp_engine = create_async_engine(
                f"postgresql+asyncpg://{os.environ.get('POSTGRES_USER', 'postgres')}:{os.environ.get('POSTGRES_PASSWORD', 'postgres')}@{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}/postgres",
                echo=False,
                future=True,
                isolation_level="AUTOCOMMIT"  # Required for CREATE DATABASE
            )
            
            async with temp_engine.connect() as conn:
                # Create the test database
                await conn.execute(text(f"CREATE DATABASE {cls._db_name}"))
            
            await temp_engine.dispose()
            
        except Exception as e:
            # If database already exists, that's fine
            if "already exists" not in str(e):
                raise
        
    @classmethod
    def teardown_class(cls):
        """Clean up the test database after the entire test class."""
        if cls._engine:
            asyncio.run(cls._engine.dispose())
        
        # Drop the test database using SQL
        if cls._db_name:
            try:
                # Create a temporary engine to the default database to drop the test database
                temp_engine = create_async_engine(
                    f"postgresql+asyncpg://{os.environ.get('POSTGRES_USER', 'postgres')}:{os.environ.get('POSTGRES_PASSWORD', 'postgres')}@{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}/postgres",
                    echo=False,
                    future=True
                )
                
                async def drop_test_db():
                    async with temp_engine.begin() as conn:
                        # Terminate all connections to the test database
                        await conn.execute(text(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{cls._db_name}'"))
                        # Drop the database
                        await conn.execute(text(f"DROP DATABASE IF EXISTS {cls._db_name}"))
                
                asyncio.run(drop_test_db())
                asyncio.run(temp_engine.dispose())
                
            except Exception:
                pass  # Ignore cleanup errors
            
        cls._engine = None
        cls._session_factory = None
        cls._database_url = None
        cls._db_name = None
        

        
    @property
    def database_url(self) -> str:
        """Get the current database URL."""
        if not self._database_url:
            raise RuntimeError("Database not set up. Call setup_class() first.")
        return self._database_url
        
    @property
    def engine(self) -> AsyncEngine:
        """Get the current async engine."""
        if not self._engine:
            raise RuntimeError("Database not set up. Call setup_class() first.")
        return self._engine
        
    @property
    def session_factory(self) -> sessionmaker:
        """Get the current session factory."""
        if not self._session_factory:
            raise RuntimeError("Database not set up. Call setup_class() first.")
        return self._session_factory
        
    async def create_tables(self):
        """Create all tables defined in the metadata."""
        async with self.engine.begin() as conn:
            await conn.run_sync(self.metadata.create_all)
            
    async def drop_tables(self):
        """Drop all tables defined in the metadata."""
        async with self.engine.begin() as conn:
            await conn.run_sync(self.metadata.drop_all)
            
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session for testing."""
        async with self.session_factory() as session:
            try:
                yield session
            finally:
                await session.close()
                
    def get_session_fixture(self):
        """
        Get a pytest fixture for database sessions.
        
        Returns:
            A pytest fixture function that provides database sessions
        """
        @pytest.fixture
        async def session():
            async with self.get_session() as session:
                yield session
                
        return session
        
    def get_engine_fixture(self):
        """
        Get a pytest fixture for database engine.
        
        Returns:
            A pytest fixture function that provides database engine
        """
        @pytest.fixture
        def engine():
            return self.engine
            
        return engine
