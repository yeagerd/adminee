import nox

nox.options.sessions = [
    "format",
    "lint",
    "typecheck",
    "test",
    "test_fast",
    "test_cov",
    "test_serial",
]
# Create fresh isolated environments using uv backend
nox.options.reuse_existing_virtualenvs = False
nox.options.default_venv_backend = "uv"


@nox.session(python="3.12")
def fix(session: nox.Session) -> None:
    """Format and fix code issues."""
    session.install("black", "isort", "ruff")
    session.run("black", "services/")
    session.run("isort", "services/")
    session.run("ruff", "check", "--fix", "services/")


@nox.session(python="3.12")
def format(session: nox.Session) -> None:
    """Check code formatting."""
    session.install("black", "isort")
    session.run("black", "--check", "--diff", "services/")
    session.run("isort", "--check-only", "--diff", "services/")


@nox.session(python="3.12")
def lint(session: nox.Session) -> None:
    """Run linting."""
    session.install("ruff")
    session.run("ruff", "check", "services/")


@nox.session(python="3.12")
def typecheck(session: nox.Session) -> None:
    """Run type checking."""
    session.install("mypy", "types-requests", "types-pytz")
    
    # Use UV to sync workspace packages
    session.run("uv", "sync", "--all-packages", "--all-extras", "--active", "--group", "dev", external=True)
    
    session.run("mypy", "services")
    session.run("npx", "pyright", "services/", external=True)


@nox.session(python="3.12")
def typecheck_strict(session: nox.Session) -> None:
    """Run strict type checking."""
    session.install("mypy", "types-requests", "types-pytz")
    
    # Use UV to sync workspace packages
    session.run("uv", "sync", "--all-packages", "--all-extras", "--active", "--group", "dev", external=True)
    
    session.run("mypy", "services/common", "--strict")


@nox.session(python="3.12")
def test(session: nox.Session) -> None:
    """Run tests for all services."""
    # Install test dependencies
    session.install(
        "pytest", "pytest-cov", "pytest-timeout", "pytest-mock", "pytest-asyncio", "pytest-xdist", "respx"
    )

    # Use UV to sync workspace packages (this ensures they're installed in editable mode)
    session.run("uv", "sync", "--all-packages", "--all-extras", "--active", "--group", "dev", external=True)

    # Run tests
    session.run(
        "bash",
        "-c",
        "python -m pytest services/ -v -n auto -r fE --disable-warnings | grep -v PASSED",
        external=True,
    )

@nox.session(python="3.12")
def test_cov(session: nox.Session) -> None:
    """Run tests with coverage."""
    session.install(
        "pytest", "pytest-cov", "pytest-timeout", "pytest-mock", "pytest-asyncio", "respx"
    )
    
    # Use UV to sync workspace packages
    session.run("uv", "sync", "--all-packages", "--all-extras", "--active", "--group", "dev", external=True)

    session.run(
        "bash",
        "-c",
        "python -m pytest services --cov=services --cov-report=xml:coverage.xml -v -r fE --disable-warnings | grep -v PASSED",
        external=True,
    )

