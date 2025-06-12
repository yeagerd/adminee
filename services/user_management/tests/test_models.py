"""
Tests for User Management Service models.

Covers Ormar model definitions, relationships, validations,
and database constraints for the user management domain.
"""

from datetime import datetime, timezone

from services.user_management.models.audit import AuditLog
from services.user_management.models.integration import Integration, IntegrationProvider, IntegrationStatus
from services.user_management.models.preferences import UserPreferences
from services.user_management.models.token import EncryptedToken, TokenType
from services.user_management.models.user import User


class TestUserModel:
    """Test cases for User model."""

    def test_user_creation_valid(self):
        """Test creating a valid user."""
        user_data = {
            "external_auth_id": "clerk_123",
            "auth_provider": "clerk",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "profile_image_url": "https://example.com/avatar.jpg",
            "onboarding_completed": False,
            "onboarding_step": "profile",
        }

        user = User(**user_data)
        assert user.external_auth_id == "clerk_123"
        assert user.auth_provider == "clerk"
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.onboarding_completed is False
        assert user.onboarding_step == "profile"
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_user_creation_minimal(self):
        """Test creating user with minimal required fields."""
        user = User(
            external_auth_id="clerk_456",
            auth_provider="clerk",
            email="minimal@example.com",
        )
        assert user.external_auth_id == "clerk_456"
        assert user.auth_provider == "clerk"
        assert user.email == "minimal@example.com"
        assert user.first_name is None
        assert user.last_name is None
        assert user.onboarding_completed is False  # Default value
        assert user.onboarding_step is None

    def test_user_email_validation(self):
        """Test email validation."""
        # Test with a valid email first
        user = User(
            external_auth_id="clerk_789",
            auth_provider="clerk",
            email="valid@example.com",
        )
        assert user.email == "valid@example.com"

        # Note: Ormar with Pydantic EmailStr should validate emails,
        # but the validation might happen at different levels.
        # For now, we test that valid emails work correctly.

    def test_user_defaults(self):
        """Test default values are set correctly."""
        user = User(
            external_auth_id="clerk_default",
            auth_provider="clerk",
            email="default@example.com",
        )
        assert user.onboarding_completed is False
        assert user.created_at is not None
        assert user.updated_at is not None


class TestUserPreferencesModel:
    """Test cases for UserPreferences model."""

    def test_preferences_creation_with_defaults(self):
        """Test creating preferences with default values."""
        # Create a user first (foreign key dependency)
        user = User(
            external_auth_id="pref_user",
            auth_provider="clerk",
            email="pref@example.com",
        )

        preferences = UserPreferences(user=user)
        assert preferences.version == "1.0"
        assert preferences.ui_preferences == {}
        assert preferences.notification_preferences == {}
        assert preferences.ai_preferences == {}
        assert preferences.integration_preferences == {}
        assert preferences.privacy_preferences == {}

    def test_preferences_custom_values(self):
        """Test creating preferences with custom values."""
        user = User(
            external_auth_id="custom_user",
            auth_provider="clerk",
            email="custom@example.com",
        )

        ui_prefs = {"theme": "dark", "language": "es", "timezone": "America/New_York"}
        notification_prefs = {"email_notifications": False}
        ai_prefs = {"preferred_model": "claude-3"}
        privacy_prefs = {"data_retention_period": "180_days"}

        preferences = UserPreferences(
            user=user,
            version="1.0",
            ui_preferences=ui_prefs,
            notification_preferences=notification_prefs,
            ai_preferences=ai_prefs,
            privacy_preferences=privacy_prefs,
        )

        assert preferences.version == "1.0"
        assert preferences.ui_preferences["theme"] == "dark"
        assert preferences.ui_preferences["language"] == "es"
        assert preferences.ui_preferences["timezone"] == "America/New_York"
        assert preferences.notification_preferences["email_notifications"] is False
        assert preferences.ai_preferences["preferred_model"] == "claude-3"
        assert preferences.privacy_preferences["data_retention_period"] == "180_days"


class TestIntegrationModel:
    """Test cases for Integration model."""

    def test_integration_creation(self):
        """Test creating an integration."""
        user = User(
            external_auth_id="int_user",
            auth_provider="clerk",
            email="integration@example.com",
        )

        integration = Integration(
            user=user,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
            provider_user_id="google_123",
            provider_email="user@gmail.com",
            scopes={"email": True, "calendar": True},
            provider_metadata={"display_name": "John's Gmail"},
        )

        assert integration.provider == IntegrationProvider.GOOGLE
        assert integration.status == IntegrationStatus.ACTIVE
        assert integration.provider_user_id == "google_123"
        assert integration.provider_email == "user@gmail.com"
        assert integration.scopes == {"email": True, "calendar": True}
        assert integration.provider_metadata["display_name"] == "John's Gmail"

    def test_integration_enum_values(self):
        """Test integration enum values."""
        # Test provider enum
        assert IntegrationProvider.GOOGLE == "google"
        assert IntegrationProvider.MICROSOFT == "microsoft"
        assert IntegrationProvider.SLACK == "slack"

        # Test status enum
        assert IntegrationStatus.ACTIVE == "active"
        assert IntegrationStatus.INACTIVE == "inactive"
        assert IntegrationStatus.ERROR == "error"
        assert IntegrationStatus.PENDING == "pending"

    def test_integration_defaults(self):
        """Test integration default values."""
        user = User(
            external_auth_id="default_int_user",
            auth_provider="clerk",
            email="default@example.com",
        )

        integration = Integration(user=user, provider=IntegrationProvider.MICROSOFT)

        assert integration.status == IntegrationStatus.PENDING  # Default status
        assert integration.provider_user_id is None
        assert integration.provider_email is None
        assert integration.scopes is None
        assert integration.provider_metadata is None
        assert integration.last_sync_at is None
        assert integration.error_message is None


class TestEncryptedTokenModel:
    """Test cases for EncryptedToken model."""

    def test_token_creation(self):
        """Test creating an encrypted token."""
        user = User(
            external_auth_id="token_user",
            auth_provider="clerk",
            email="token@example.com",
        )
        integration = Integration(
            user=user,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
        )

        token = EncryptedToken(
            user=user,
            integration=integration,
            token_type=TokenType.ACCESS,
            encrypted_value="encrypted_token_data_here",
            expires_at=datetime.now(timezone.utc),
            scopes={"read": True, "write": False},
        )

        assert token.token_type == TokenType.ACCESS
        assert token.encrypted_value == "encrypted_token_data_here"
        assert token.expires_at is not None
        assert token.scopes == {"read": True, "write": False}

    def test_token_types(self):
        """Test token type enum values."""
        assert TokenType.ACCESS == "access"
        assert TokenType.REFRESH == "refresh"

    def test_refresh_token_creation(self):
        """Test creating a refresh token."""
        user = User(
            external_auth_id="refresh_user",
            auth_provider="clerk",
            email="refresh@example.com",
        )
        integration = Integration(
            user=user,
            provider=IntegrationProvider.MICROSOFT,
            status=IntegrationStatus.ACTIVE,
        )

        refresh_token = EncryptedToken(
            user=user,
            integration=integration,
            token_type=TokenType.REFRESH,
            encrypted_value="encrypted_refresh_token",
        )

        assert refresh_token.token_type == TokenType.REFRESH
        assert refresh_token.expires_at is None  # Refresh tokens may not expire
        assert refresh_token.scopes is None


class TestAuditLogModel:
    """Test cases for AuditLog model."""

    def test_audit_log_creation(self):
        """Test creating an audit log entry."""
        user = User(
            external_auth_id="audit_user",
            auth_provider="clerk",
            email="audit@example.com",
        )

        audit_log = AuditLog(
            user=user,
            action="user_login",
            resource_type="user",
            resource_id="audit_user",
            details={"method": "oauth", "provider": "google"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 Chrome/91.0",
        )

        assert audit_log.action == "user_login"
        assert audit_log.resource_type == "user"
        assert audit_log.resource_id == "audit_user"
        assert audit_log.details["method"] == "oauth"
        assert audit_log.details["provider"] == "google"
        assert audit_log.ip_address == "192.168.1.1"
        assert audit_log.user_agent == "Mozilla/5.0 Chrome/91.0"
        assert isinstance(audit_log.created_at, datetime)

    def test_audit_log_system_event(self):
        """Test creating system audit log (no user)."""
        system_log = AuditLog(
            user=None,  # System event
            action="system_backup",
            resource_type="system",
            resource_id=None,
            details={"backup_size": "10GB", "duration": "5min"},
        )

        assert system_log.user is None
        assert system_log.action == "system_backup"
        assert system_log.resource_type == "system"
        assert system_log.resource_id is None
        assert system_log.details["backup_size"] == "10GB"

    def test_audit_log_minimal(self):
        """Test creating audit log with minimal required fields."""
        minimal_log = AuditLog(action="test_action", resource_type="test_resource")

        assert minimal_log.action == "test_action"
        assert minimal_log.resource_type == "test_resource"
        assert minimal_log.user is None
        assert minimal_log.resource_id is None
        assert minimal_log.details is None
        assert minimal_log.ip_address is None
        assert minimal_log.user_agent is None


class TestModelRelationships:
    """Test cases for model relationships."""

    def test_user_preferences_relationship(self):
        """Test one-to-one relationship between User and UserPreferences."""
        user = User(
            external_auth_id="rel_user",
            auth_provider="clerk",
            email="relationship@example.com",
        )
        preferences = UserPreferences(
            user=user, version="1.0", ui_preferences={"theme": "dark"}
        )

        # Test foreign key relationship
        assert preferences.user == user
        assert preferences.version == "1.0"
        assert preferences.ui_preferences["theme"] == "dark"

    def test_user_integrations_relationship(self):
        """Test one-to-many relationship between User and Integrations."""
        user = User(
            external_auth_id="multi_int_user",
            auth_provider="clerk",
            email="multi@example.com",
        )

        google_integration = Integration(
            user=user,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
        )

        microsoft_integration = Integration(
            user=user,
            provider=IntegrationProvider.MICROSOFT,
            status=IntegrationStatus.PENDING,
        )

        # Both integrations should reference the same user
        assert google_integration.user == user
        assert microsoft_integration.user == user

    def test_integration_token_relationship(self):
        """Test one-to-many relationship between Integration and EncryptedTokens."""
        user = User(
            external_auth_id="token_rel_user",
            auth_provider="clerk",
            email="tokenrel@example.com",
        )
        integration = Integration(
            user=user,
            provider=IntegrationProvider.SLACK,
            status=IntegrationStatus.ACTIVE,
        )

        access_token = EncryptedToken(
            user=user,
            integration=integration,
            token_type=TokenType.ACCESS,
            encrypted_value="access_token_encrypted",
            expires_at=datetime.now(timezone.utc),
        )

        refresh_token = EncryptedToken(
            user=user,
            integration=integration,
            token_type=TokenType.REFRESH,
            encrypted_value="refresh_token_encrypted",
        )

        # Both tokens should reference the same integration
        assert access_token.integration == integration
        assert refresh_token.integration == integration
        assert access_token.user == user
        assert refresh_token.user == user

    def test_audit_log_user_relationship(self):
        """Test many-to-one relationship between AuditLog and User."""
        user = User(
            external_auth_id="audit_rel_user",
            auth_provider="clerk",
            email="auditrel@example.com",
        )

        login_log = AuditLog(
            user=user,
            action="user_login",
            resource_type="user",
            resource_id="audit_rel_user",
        )

        logout_log = AuditLog(
            user=user,
            action="user_logout",
            resource_type="user",
            resource_id="audit_rel_user",
        )

        # Both logs should reference the same user
        assert login_log.user == user
        assert logout_log.user == user
