import nox

nox.options.sessions = [
    "format", "lint", "typecheck", "typecheck_strict", "test", "test_fast", "test_cov"
]
nox.options.reuse_existing_virtualenvs = True

@nox.session(venv_backend="none")
def format(session):
    session.run("black", "--check", "--diff", "services/", external=True)
    session.run("isort", "--check-only", "--diff", "services/", external=True)

@nox.session(venv_backend="none")
def lint(session):
    session.run("ruff", "check", "services/", external=True)

@nox.session(venv_backend="none")
def typecheck(session):
    session.run("bash", "-c", "cd services/user && python -m mypy . --ignore-missing-imports --no-strict-optional --exclude='alembic/'", external=True)
    session.run("bash", "-c", "cd services/chat && python -m mypy . --ignore-missing-imports --no-strict-optional --exclude='alembic/'", external=True)
    session.run("bash", "-c", "cd services/office && python -m mypy . --ignore-missing-imports --no-strict-optional --exclude='alembic/'", external=True)

@nox.session(venv_backend="none")
def typecheck_strict(session):
    session.run("mypy", "services", "--strict", external=True)

@nox.session(venv_backend="none")
def test(session):
    session.run("pytest", "services/", "-n", "auto", "-q", "--tb=short", external=True)

@nox.session(venv_backend="none")
def test_fast(session):
    session.run("bash", "-c", "cd services/user && python -m pytest tests/ -x -q", external=True)
    session.run("bash", "-c", "cd services/chat && python -m pytest tests/ -x -q", external=True)
    session.run("bash", "-c", "cd services/office && python -m pytest tests/ -x -q", external=True)

@nox.session(venv_backend="none")
def test_cov(session):
    session.run("bash", "-c", "cd services/user && python -m pytest tests/ --cov=. --cov-report=xml:../../coverage-user-management.xml --cov-report=term-missing -x -q", external=True)
    session.run("bash", "-c", "cd services/chat && python -m pytest tests/ --cov=. --cov-report=xml:../../coverage-chat-service.xml --cov-report=term-missing -x -q", external=True)
    session.run("bash", "-c", "cd services/office && python -m pytest tests/ --cov=. --cov-report=xml:../../coverage-office-service.xml --cov-report=term-missing -x -q", external=True) 