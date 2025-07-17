import nox

nox.options.sessions = [
    "format",
    "lint",
    "typecheck",
    "typecheck_strict",
    "test",
    "test_fast",
    "test_cov",
    "test_serial",
]
# Create fresh isolated environments using uv backend
nox.options.reuse_existing_virtualenvs = False
nox.options.default_venv_backend = "uv"


@nox.session(python="3.12")
def fix(session):
    """Format and fix code issues."""
    session.install("black", "isort", "ruff")
    session.run("black", "services/")
    session.run("isort", "services/")
    session.run("ruff", "check", "--fix", "services/")


@nox.session(python="3.12")
def format(session):
    """Check code formatting."""
    session.install("black", "isort")
    session.run("black", "--check", "--diff", "services/")
    session.run("isort", "--check-only", "--diff", "services/")


@nox.session(python="3.12")
def lint(session):
    """Run linting."""
    session.install("ruff")
    session.run("ruff", "check", "services/")


@nox.session(python="3.12")
def typecheck(session):
    """Run type checking."""
    session.install("mypy")
    # Install all services for comprehensive type checking
    session.install("-e", "services/common")
    session.install("-e", "services/user")
    session.install("-e", "services/chat")
    session.install("-e", "services/office")
    session.run("mypy", "services/common")
    session.run("npx", "pyright", "services/", external=True)


@nox.session(python="3.12")
def typecheck_strict(session):
    """Run strict type checking."""
    session.install("mypy")
    session.install("-e", "services/common")
    session.run("mypy", "services/common", "--strict")


@nox.session(python="3.12")
def test(session):
    """Run tests for all services."""
    # Install common dependencies
    session.install(
        "pytest", "pytest-cov", "pytest-timeout", "pytest-mock", "pytest-asyncio", "pytest-xdist", "respx"
    )

    # Install services
    session.install("-e", "services/common")
    session.install("-e", "services/user")
    session.install("-e", "services/chat")
    session.install("-e", "services/office")

    # Run tests
    session.run("python", "-m", "pytest", "services/", "-v", "-n", "auto")


@nox.session(python="3.12")
def test_fast(session):
    """Run fast tests only."""
    session.install(
        "pytest", "pytest-cov", "pytest-timeout", "pytest-mock", "pytest-asyncio", "respx"
    )
    session.install("-e", "services/common")
    session.install("-e", "services/user")
    session.install("-e", "services/chat")
    session.install("-e", "services/office")

    session.run(
        "python", "-m", "pytest", "services/user/tests/", "-v", "-k", "not slow"
    )
    session.run(
        "python", "-m", "pytest", "services/chat/tests/", "-v", "-k", "not slow"
    )
    session.run(
        "python", "-m", "pytest", "services/office/tests/", "-v", "-k", "not slow"
    )


@nox.session(python="3.12")
def test_cov(session):
    """Run tests with coverage."""
    session.install(
        "pytest", "pytest-cov", "pytest-timeout", "pytest-mock", "pytest-asyncio", "respx"
    )
    session.install("-e", "services/common")
    session.install("-e", "services/user")
    session.install("-e", "services/chat")
    session.install("-e", "services/office")

    session.run(
        "python",
        "-m",
        "pytest",
        "services/user/tests/",
        "--cov=services/user",
        "--cov-report=xml:coverage-user-management.xml",
        "-v",
    )
    session.run(
        "python",
        "-m",
        "pytest",
        "services/chat/tests/",
        "--cov=services/chat",
        "--cov-report=xml:coverage-chat-service.xml",
        "-v",
    )
    session.run(
        "python",
        "-m",
        "pytest",
        "services/office/tests/",
        "--cov=services/office",
        "--cov-report=xml:coverage-office-service.xml",
        "-v",
    )


@nox.session(python="3.12")
def test_serial(session):
    """Run tests serially (not in parallel)."""
    session.install(
        "pytest", "pytest-cov", "pytest-timeout", "pytest-mock", "pytest-asyncio", "respx"
    )
    session.install("-e", "services/common")
    session.install("-e", "services/user")
    session.install("-e", "services/chat")
    session.install("-e", "services/office")

    session.run("python", "-m", "pytest", "services/user/tests/", "-v", "--tb=short")
    session.run("python", "-m", "pytest", "services/chat/tests/", "-v", "--tb=short")
    session.run("python", "-m", "pytest", "services/office/tests/", "-v", "--tb=short")
