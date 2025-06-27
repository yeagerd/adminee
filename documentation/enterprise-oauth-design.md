# Enterprise OAuth Design for Microsoft and Google Providers

## Overview

This document outlines the design for handling enterprise accounts (company domains) using Microsoft Azure AD and Google Workspace OAuth providers. The system will support both personal accounts and enterprise accounts through the same OAuth flows, with automatic detection and appropriate handling of company-specific features.

## Problem Statement

Enterprise users often have email addresses with their company domain (e.g., `user@company.com`) but authenticate through Microsoft Azure AD or Google Workspace. We need to:

1. Support enterprise authentication through existing OAuth providers
2. Distinguish between personal and enterprise accounts
3. Handle email normalization appropriately for different account types
4. Provide company-specific features and policies
5. Maintain security and compliance requirements

## Current OAuth Flow

### Personal Accounts
- **Microsoft**: `user@outlook.com`, `user@hotmail.com`
- **Google**: `user@gmail.com`
- **Email normalization**: Provider-specific rules (remove plus addressing, dots for Gmail, etc.)

### Enterprise Accounts
- **Microsoft Azure AD**: `user@company.com` (authenticated through Microsoft)
- **Google Workspace**: `user@company.com` (authenticated through Google)
- **Email normalization**: Preserve original email (no provider-specific normalization)

## Design Solution

### 1. OAuth Provider Configuration

#### Microsoft OAuth
```python
MICROSOFT_OAUTH_CONFIG = {
    "authorization_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    "scope": "openid email profile",
    "response_type": "code"
}
```

#### Google OAuth
```python
GOOGLE_OAUTH_CONFIG = {
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_url": "https://oauth2.googleapis.com/token",
    "scope": "openid email profile",
    "response_type": "code"
}
```

### 2. Account Type Detection

#### Microsoft Account Detection
```python
def detect_microsoft_account_type(oauth_response: dict) -> dict:
    """
    Detect if Microsoft account is personal or enterprise.
    
    Returns:
        {
            "account_type": "personal" | "enterprise",
            "tenant_id": str,
            "is_company_account": bool,
            "company_domain": str | None
        }
    """
    tenant_id = oauth_response.get('tid')
    
    # Known personal Microsoft tenant IDs
    personal_tenants = {
        "9188040d-6c67-4c5b-b112-36a304b66dad",  # Personal Microsoft
        "f8cdef31-a31e-4b4a-93e4-5f571e91255a",  # Another personal tenant
        "common",  # Multi-tenant (usually personal)
        "consumers"  # Consumer accounts
    }
    
    email = oauth_response.get('email', '')
    domain = email.split('@')[1].lower() if '@' in email else ''
    
    is_personal = tenant_id in personal_tenants or not tenant_id
    
    return {
        "account_type": "personal" if is_personal else "enterprise",
        "tenant_id": tenant_id,
        "is_company_account": not is_personal,
        "company_domain": domain if not is_personal else None
    }
```

#### Google Account Detection
```python
def detect_google_account_type(oauth_response: dict) -> dict:
    """
    Detect if Google account is personal or enterprise (Google Workspace).
    
    Returns:
        {
            "account_type": "personal" | "enterprise",
            "hd": str | None,  # Hosted domain
            "is_company_account": bool,
            "company_domain": str | None
        }
    """
    hosted_domain = oauth_response.get('hd')  # Google Workspace hosted domain
    email = oauth_response.get('email', '')
    domain = email.split('@')[1].lower() if '@' in email else ''
    
    # Personal Google accounts don't have 'hd' parameter
    is_personal = not hosted_domain
    
    return {
        "account_type": "personal" if is_personal else "enterprise",
        "hd": hosted_domain,
        "is_company_account": not is_personal,
        "company_domain": hosted_domain if not is_personal else None
    }
```

### 3. Email Normalization Strategy

#### Smart Email Normalization
```python
def normalize_email_smart(email: str, account_type: str, provider: str) -> str:
    """
    Apply appropriate email normalization based on account type and provider.
    
    Args:
        email: Original email address
        account_type: "personal" or "enterprise"
        provider: "microsoft" or "google"
    
    Returns:
        Normalized email address
    """
    if account_type == "enterprise":
        # For enterprise accounts, preserve the original email
        # Company admins may use plus addressing intentionally
        return email.lower()
    
    # For personal accounts, use provider-specific normalization
    try:
        result = normalize(email)
        return result.normalized_address
    except Exception:
        # Fallback to basic normalization
        return email.strip().lower()

def is_personal_provider_domain(email: str) -> bool:
    """Check if email domain is from a personal provider."""
    personal_domains = {
        # Microsoft personal
        'outlook.com', 'hotmail.com', 'live.com', 'msn.com',
        # Google personal
        'gmail.com', 'googlemail.com',
        # Other personal providers
        'yahoo.com', 'icloud.com', 'me.com', 'mac.com'
    }
    
    domain = email.split('@')[1].lower()
    return domain in personal_domains
```

### 4. Database Schema Updates

#### User Model Enhancements
```python
class User(SQLModel, table=True):
    # Existing fields
    id: Optional[int] = Field(default=None, primary_key=True)
    external_auth_id: str = Field(index=True)
    auth_provider: str = Field(index=True)
    email: str = Field(index=True)
    normalized_email: str = Field(index=True)
    
    # New enterprise fields
    account_type: str = Field(default="personal")  # "personal" | "enterprise"
    tenant_id: Optional[str] = Field(default=None, index=True)  # Microsoft tenant ID
    hosted_domain: Optional[str] = Field(default=None, index=True)  # Google hosted domain
    company_domain: Optional[str] = Field(default=None, index=True)
    is_company_account: bool = Field(default=False, index=True)
    
    # Enterprise-specific fields
    company_name: Optional[str] = Field(default=None)
    department: Optional[str] = Field(default=None)
    job_title: Optional[str] = Field(default=None)
    
    # Existing fields...
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    onboarding_completed: bool = Field(default=False)
    onboarding_step: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
```

#### Company Model (Optional)
```python
class Company(SQLModel, table=True):
    """Company/organization information for enterprise accounts."""
    id: Optional[int] = Field(default=None, primary_key=True)
    domain: str = Field(unique=True, index=True)
    name: str
    tenant_id: Optional[str] = Field(default=None, index=True)  # Microsoft tenant ID
    hosted_domain: Optional[str] = Field(default=None, index=True)  # Google hosted domain
    
    # Company settings
    sso_enabled: bool = Field(default=False)
    mfa_required: bool = Field(default=False)
    allowed_domains: List[str] = Field(default=[])
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### 5. OAuth Flow Implementation

#### Enhanced OAuth Handler
```python
class EnterpriseOAuthHandler:
    """Handle OAuth authentication for both personal and enterprise accounts."""
    
    def __init__(self):
        self.microsoft_config = MICROSOFT_OAUTH_CONFIG
        self.google_config = GOOGLE_OAUTH_CONFIG
    
    async def handle_microsoft_oauth(self, code: str) -> dict:
        """Handle Microsoft OAuth callback."""
        # Exchange code for tokens
        tokens = await self._exchange_microsoft_code(code)
        
        # Get user info
        user_info = await self._get_microsoft_user_info(tokens['access_token'])
        
        # Detect account type
        account_info = detect_microsoft_account_type(user_info)
        
        # Normalize email appropriately
        normalized_email = normalize_email_smart(
            user_info['email'], 
            account_info['account_type'], 
            'microsoft'
        )
        
        return {
            'user_info': user_info,
            'account_info': account_info,
            'normalized_email': normalized_email,
            'provider': 'microsoft'
        }
    
    async def handle_google_oauth(self, code: str) -> dict:
        """Handle Google OAuth callback."""
        # Exchange code for tokens
        tokens = await self._exchange_google_code(code)
        
        # Get user info
        user_info = await self._get_google_user_info(tokens['access_token'])
        
        # Detect account type
        account_info = detect_google_account_type(user_info)
        
        # Normalize email appropriately
        normalized_email = normalize_email_smart(
            user_info['email'], 
            account_info['account_type'], 
            'google'
        )
        
        return {
            'user_info': user_info,
            'account_info': account_info,
            'normalized_email': normalized_email,
            'provider': 'google'
        }
```

### 6. User Creation/Update Logic

#### Enhanced User Service
```python
class EnterpriseUserService:
    """Handle user creation and updates for enterprise accounts."""
    
    def __init__(self):
        self.email_detector = EmailCollisionDetector()
    
    async def create_or_update_user(self, oauth_data: dict) -> User:
        """Create or update user from OAuth data."""
        
        user_info = oauth_data['user_info']
        account_info = oauth_data['account_info']
        normalized_email = oauth_data['normalized_email']
        provider = oauth_data['provider']
        
        # Check for existing user by external_auth_id
        existing_user = await self._get_user_by_external_id(
            user_info['sub'], provider
        )
        
        if existing_user:
            # Update existing user
            return await self._update_user(existing_user, oauth_data)
        
        # Check for email collision
        collision_details = await self.email_detector.get_collision_details(
            normalized_email
        )
        
        if collision_details["collision"]:
            # Handle collision based on business logic
            return await self._handle_email_collision(collision_details, oauth_data)
        
        # Create new user
        return await self._create_user(oauth_data)
    
    async def _create_user(self, oauth_data: dict) -> User:
        """Create new user from OAuth data."""
        user_info = oauth_data['user_info']
        account_info = oauth_data['account_info']
        normalized_email = oauth_data['normalized_email']
        provider = oauth_data['provider']
        
        user = User(
            external_auth_id=user_info['sub'],
            auth_provider=provider,
            email=user_info['email'],
            normalized_email=normalized_email,
            account_type=account_info['account_type'],
            tenant_id=account_info.get('tenant_id'),
            hosted_domain=account_info.get('hd'),
            company_domain=account_info.get('company_domain'),
            is_company_account=account_info['is_company_account'],
            first_name=user_info.get('given_name'),
            last_name=user_info.get('family_name'),
            profile_image_url=user_info.get('picture'),
            onboarding_completed=False,
            onboarding_step="welcome"
        )
        
        # Save to database
        async_session = get_async_session()
        async with async_session() as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        return user
```

### 7. Enterprise-Specific Features

#### Company Detection and Features
```python
class EnterpriseFeatures:
    """Handle enterprise-specific features and policies."""
    
    @staticmethod
    async def get_company_info(user: User) -> Optional[Company]:
        """Get company information for enterprise user."""
        if not user.is_company_account:
            return None
        
        async_session = get_async_session()
        async with async_session() as session:
            result = await session.execute(
                select(Company).where(Company.domain == user.company_domain)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def apply_company_policies(user: User) -> dict:
        """Apply company-specific policies and settings."""
        company = await EnterpriseFeatures.get_company_info(user)
        
        if not company:
            return {"policies": {}}
        
        return {
            "policies": {
                "sso_enabled": company.sso_enabled,
                "mfa_required": company.mfa_required,
                "allowed_domains": company.allowed_domains
            }
        }
    
    @staticmethod
    async def get_company_users(company_domain: str) -> List[User]:
        """Get all users from the same company."""
        async_session = get_async_session()
        async with async_session() as session:
            result = await session.execute(
                select(User).where(
                    User.company_domain == company_domain,
                    User.deleted_at.is_(None)
                )
            )
            return result.scalars().all()
```

### 8. API Endpoints

#### Enhanced OAuth Endpoints
```python
@router.post("/oauth/microsoft/callback")
async def microsoft_oauth_callback(code: str):
    """Handle Microsoft OAuth callback."""
    oauth_handler = EnterpriseOAuthHandler()
    oauth_data = await oauth_handler.handle_microsoft_oauth(code)
    
    user_service = EnterpriseUserService()
    user = await user_service.create_or_update_user(oauth_data)
    
    # Apply company policies
    policies = await EnterpriseFeatures.apply_company_policies(user)
    
    return {
        "user": user,
        "account_type": oauth_data['account_info']['account_type'],
        "company_policies": policies
    }

@router.post("/oauth/google/callback")
async def google_oauth_callback(code: str):
    """Handle Google OAuth callback."""
    oauth_handler = EnterpriseOAuthHandler()
    oauth_data = await oauth_handler.handle_google_oauth(code)
    
    user_service = EnterpriseUserService()
    user = await user_service.create_or_update_user(oauth_data)
    
    # Apply company policies
    policies = await EnterpriseFeatures.apply_company_policies(user)
    
    return {
        "user": user,
        "account_type": oauth_data['account_info']['account_type'],
        "company_policies": policies
    }
```

#### Company Management Endpoints
```python
@router.get("/enterprise/company/{domain}")
async def get_company_info(domain: str):
    """Get company information."""
    async_session = get_async_session()
    async with async_session() as session:
        result = await session.execute(
            select(Company).where(Company.domain == domain)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        return company

@router.get("/enterprise/company/{domain}/users")
async def get_company_users(domain: str):
    """Get all users from a company."""
    users = await EnterpriseFeatures.get_company_users(domain)
    return {"users": users, "count": len(users)}
```

### 9. Security Considerations

#### Enterprise Security Features
```python
class EnterpriseSecurity:
    """Enterprise-specific security features."""
    
    @staticmethod
    async def validate_company_access(user: User, required_domain: str) -> bool:
        """Validate user has access to company resources."""
        if not user.is_company_account:
            return False
        
        return user.company_domain == required_domain
    
    @staticmethod
    async def enforce_mfa_for_company(user: User) -> bool:
        """Check if MFA is required for company account."""
        company = await EnterpriseFeatures.get_company_info(user)
        return company.mfa_required if company else False
    
    @staticmethod
    async def validate_allowed_domains(user: User, target_domain: str) -> bool:
        """Validate if user can access resources from target domain."""
        company = await EnterpriseFeatures.get_company_info(user)
        if not company:
            return False
        
        return target_domain in company.allowed_domains
```

### 10. Migration Strategy

#### Database Migration
```python
# Alembic migration to add enterprise fields
"""Add enterprise account fields

Revision ID: add_enterprise_fields
Revises: add_normalized_email_column
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add enterprise fields to users table
    op.add_column('users', sa.Column('account_type', sa.String(20), nullable=False, server_default='personal'))
    op.add_column('users', sa.Column('tenant_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('hosted_domain', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('company_domain', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('is_company_account', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('company_name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('department', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('job_title', sa.String(255), nullable=True))
    
    # Create indexes
    op.create_index('idx_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('idx_users_hosted_domain', 'users', ['hosted_domain'])
    op.create_index('idx_users_company_domain', 'users', ['company_domain'])
    op.create_index('idx_users_is_company_account', 'users', ['is_company_account'])
    
    # Create companies table
    op.create_table('companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=True),
        sa.Column('hosted_domain', sa.String(255), nullable=True),
        sa.Column('sso_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('mfa_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allowed_domains', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_companies_domain', 'companies', ['domain'], unique=True)
    op.create_index('idx_companies_tenant_id', 'companies', ['tenant_id'])

def downgrade():
    # Remove enterprise fields
    op.drop_index('idx_users_is_company_account', 'users')
    op.drop_index('idx_users_company_domain', 'users')
    op.drop_index('idx_users_hosted_domain', 'users')
    op.drop_index('idx_users_tenant_id', 'users')
    
    op.drop_column('users', 'job_title')
    op.drop_column('users', 'department')
    op.drop_column('users', 'company_name')
    op.drop_column('users', 'is_company_account')
    op.drop_column('users', 'company_domain')
    op.drop_column('users', 'hosted_domain')
    op.drop_column('users', 'tenant_id')
    op.drop_column('users', 'account_type')
    
    # Drop companies table
    op.drop_table('companies')
```

### 11. Testing Strategy

#### Test Cases
```python
class TestEnterpriseOAuth:
    """Test enterprise OAuth functionality."""
    
    def test_microsoft_personal_account_detection(self):
        """Test detection of personal Microsoft account."""
        oauth_response = {
            'sub': '12345678-1234-1234-1234-123456789012',
            'email': 'user@outlook.com',
            'tid': '9188040d-6c67-4c5b-b112-36a304b66dad'
        }
        
        result = detect_microsoft_account_type(oauth_response)
        assert result['account_type'] == 'personal'
        assert result['is_company_account'] == False
    
    def test_microsoft_enterprise_account_detection(self):
        """Test detection of enterprise Microsoft account."""
        oauth_response = {
            'sub': '87654321-4321-4321-4321-210987654321',
            'email': 'user@company.com',
            'tid': 'company-tenant-id-123'
        }
        
        result = detect_microsoft_account_type(oauth_response)
        assert result['account_type'] == 'enterprise'
        assert result['is_company_account'] == True
        assert result['company_domain'] == 'company.com'
    
    def test_google_enterprise_account_detection(self):
        """Test detection of Google Workspace account."""
        oauth_response = {
            'sub': '123456789012345678901',
            'email': 'user@company.com',
            'hd': 'company.com'
        }
        
        result = detect_google_account_type(oauth_response)
        assert result['account_type'] == 'enterprise'
        assert result['is_company_account'] == True
        assert result['company_domain'] == 'company.com'
    
    def test_enterprise_email_normalization(self):
        """Test email normalization for enterprise accounts."""
        # Enterprise email should be preserved
        normalized = normalize_email_smart('user+project@company.com', 'enterprise', 'microsoft')
        assert normalized == 'user+project@company.com'
        
        # Personal email should be normalized
        normalized = normalize_email_smart('user+work@gmail.com', 'personal', 'google')
        assert normalized == 'user@gmail.com'
```

### 12. Implementation Phases

#### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Update database schema with enterprise fields
- [ ] Implement account type detection functions
- [ ] Update email normalization logic
- [ ] Create basic enterprise user service

#### Phase 2: OAuth Integration (Week 3-4)
- [ ] Enhance OAuth handlers for enterprise detection
- [ ] Update user creation/update logic
- [ ] Implement email collision handling for enterprise accounts
- [ ] Add enterprise-specific API endpoints

#### Phase 3: Enterprise Features (Week 5-6)
- [ ] Implement company management features
- [ ] Add enterprise security policies
- [ ] Create company-specific user management
- [ ] Add enterprise analytics and reporting

#### Phase 4: Testing and Documentation (Week 7-8)
- [ ] Comprehensive test suite for enterprise features
- [ ] Security testing and validation
- [ ] Documentation and runbooks
- [ ] Performance testing and optimization

### 13. Monitoring and Analytics

#### Enterprise Metrics
```python
class EnterpriseAnalytics:
    """Track enterprise-specific metrics."""
    
    @staticmethod
    async def get_company_stats(company_domain: str) -> dict:
        """Get statistics for a company."""
        users = await EnterpriseFeatures.get_company_users(company_domain)
        
        return {
            "total_users": len(users),
            "active_users": len([u for u in users if u.deleted_at is None]),
            "providers": list(set(u.auth_provider for u in users)),
            "created_last_30_days": len([u for u in users if (datetime.now(timezone.utc) - u.created_at).days <= 30])
        }
    
    @staticmethod
    async def get_enterprise_overview() -> dict:
        """Get overview of all enterprise accounts."""
        async_session = get_async_session()
        async with async_session() as session:
            # Get all companies
            companies_result = await session.execute(select(Company))
            companies = companies_result.scalars().all()
            
            # Get enterprise user count
            enterprise_users_result = await session.execute(
                select(func.count(User.id)).where(User.is_company_account == True)
            )
            enterprise_user_count = enterprise_users_result.scalar()
            
            return {
                "total_companies": len(companies),
                "total_enterprise_users": enterprise_user_count,
                "companies": [{"domain": c.domain, "name": c.name} for c in companies]
            }
```

## Conclusion

This design provides a comprehensive solution for handling enterprise accounts through Microsoft and Google OAuth providers. The key benefits include:

1. **Single OAuth implementation** for both personal and enterprise accounts
2. **Automatic account type detection** based on OAuth response data
3. **Appropriate email normalization** for different account types
4. **Enterprise-specific features** and security policies
5. **Scalable architecture** that can handle multiple companies
6. **Comprehensive testing** and monitoring capabilities

The implementation maintains backward compatibility with existing personal accounts while adding robust enterprise support. 