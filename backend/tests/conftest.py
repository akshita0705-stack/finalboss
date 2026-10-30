import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, hash_api_key
from app.models.user import User, ApiKey

TEST_DATABASE_URL = "sqlite:///./test_traceguard.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_traceguard.db"):
        try:
            os.remove("./test_traceguard.db")
        except Exception:
            pass


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_admin_user(db_session):
    user = User(
        email="test_admin@traceguard.ai",
        hashed_password=get_password_hash("TestAdminPass123!"),
        full_name="Test Administrator",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_auth_headers(test_admin_user):
    token = create_access_token(subject=test_admin_user.id, role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def extension_auth_headers():
    return {
        "X-API-Key": settings.EXTENSION_API_KEY,
        "X-Installation-ID": "test-install-chrome-99",
    }


def make_user_headers(db, email, installation_id=None):
    """Create a user (optionally owning an extension installation) and return bearer headers."""
    user = User(email=email, hashed_password=get_password_hash("TestUserPass123!"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    if installation_id:
        db.add(ApiKey(installation_id=installation_id, user_id=user.id,
                      hashed_key=hash_api_key(f"key-{email}"), name="test"))
        db.commit()
    return {"Authorization": f"Bearer {create_access_token(subject=user.id, role='user')}"}


@pytest.fixture
def linked_admin_headers(db_session, test_admin_user, admin_auth_headers):
    """Admin user who owns the same installation that `extension_auth_headers` posts events for."""
    db_session.add(ApiKey(installation_id="test-install-chrome-99", user_id=test_admin_user.id,
                          hashed_key=hash_api_key("linked-admin-key"), name="test"))
    db_session.commit()
    return admin_auth_headers

