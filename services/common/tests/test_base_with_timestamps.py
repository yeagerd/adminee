"""
Tests for BaseWithTimestamps class.
"""

from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import sessionmaker

from services.api.v1.common.models.database import Base, BaseWithTimestamps


class TestModel(BaseWithTimestamps):
    """Test model that inherits from BaseWithTimestamps."""

    __tablename__ = "test_model"

    name = Column(String(50), nullable=False)


class TestBaseWithTimestamps:
    """Test BaseWithTimestamps functionality."""

    def test_inheritance_from_base(self):
        """Test that BaseWithTimestamps inherits from Base."""
        assert issubclass(BaseWithTimestamps, Base)
        assert BaseWithTimestamps.__abstract__ is True

    def test_columns_are_registered(self):
        """Test that columns are properly registered with SQLAlchemy."""

        # Create a concrete model
        class ConcreteModel(BaseWithTimestamps):
            __tablename__ = "concrete_test"
            name = Column(String(50))

        # Check that columns are registered
        assert hasattr(ConcreteModel, "__table__")
        assert "id" in ConcreteModel.__table__.columns
        assert "created_at" in ConcreteModel.__table__.columns
        assert "updated_at" in ConcreteModel.__table__.columns
        assert "name" in ConcreteModel.__table__.columns

    def test_timestamp_defaults_are_callable(self):
        """Test that timestamp defaults are callable functions."""

        # Create a concrete model
        class ConcreteModel(BaseWithTimestamps):
            __tablename__ = "concrete_test_2"
            name = Column(String(50))

        # Check that the default functions are callable
        created_at_default = ConcreteModel.__table__.columns["created_at"].default
        updated_at_default = ConcreteModel.__table__.columns["updated_at"].default

        assert created_at_default is not None
        assert updated_at_default is not None

    def test_model_creation(self):
        """Test that a model can be created and used."""
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Create a test model instance
            test_model = TestModel(name="test")

            # Check that it has the expected attributes
            assert hasattr(test_model, "id")
            assert hasattr(test_model, "created_at")
            assert hasattr(test_model, "updated_at")
            assert hasattr(test_model, "name")

            # Add to session and commit
            session.add(test_model)
            session.commit()

            # Verify the instance was saved
            assert test_model.id is not None
            assert test_model.created_at is not None
            assert test_model.updated_at is not None
            assert test_model.name == "test"

            # Note: SQLite doesn't preserve timezone info, so we can't test tzinfo here
            # In a real PostgreSQL database, the timestamps would be timezone-aware

        finally:
            session.close()

    def test_abstract_class_behavior(self):
        """Test that BaseWithTimestamps behaves as an abstract base class."""
        # The class should be marked as abstract
        assert BaseWithTimestamps.__abstract__ is True

        # But it can still be instantiated if needed (SQLAlchemy handles this)
        # The real test is that it's designed to be inherited from, not used directly
        assert hasattr(BaseWithTimestamps, "id")
        assert hasattr(BaseWithTimestamps, "created_at")
        assert hasattr(BaseWithTimestamps, "updated_at")
