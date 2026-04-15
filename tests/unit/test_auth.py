"""Tests for utils.auth module."""

from flask import Flask
from utils.auth import WebAuth, create_auth_decorator


def _build_auth(app: Flask, enabled=True, username="admin", password_hash=None):
    return WebAuth(
        app=app,
        app_secret="test-secret",
        user_name=lambda: username,
        password_hash=lambda: password_hash,
        enabled=lambda: enabled,
    )


def test_is_authenticated_when_auth_disabled_returns_true():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    auth = _build_auth(app, enabled=False)

    with app.test_request_context("/"):
        assert auth.is_authenticated() is True


def test_is_authenticated_when_auth_enabled_uses_session_flag():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    auth = _build_auth(app, enabled=True)

    with app.test_request_context("/"):
        assert auth.is_authenticated() is False

    with app.test_request_context("/"):
        from flask import session

        session["authenticated"] = True
        assert auth.is_authenticated() is True


def test_verify_password_success_and_failure_paths():
    app = Flask(__name__)
    app.secret_key = "test-secret"

    tmp_auth = _build_auth(app, enabled=True, password_hash="")
    password_hash = tmp_auth.hash_password("s3cr3t")

    auth = _build_auth(app, enabled=True, username="admin", password_hash=password_hash)

    with app.test_request_context("/"):
        assert auth.verify_password("admin", "s3cr3t") is True
        assert auth.verify_password("admin", "wrong") is False
        assert auth.verify_password("wrong", "s3cr3t") is False


def test_verify_password_returns_false_when_credentials_not_configured():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    auth = _build_auth(app, enabled=True, username="", password_hash="")

    with app.test_request_context("/"):
        assert auth.verify_password("admin", "s3cr3t") is False


def test_login_sets_session_and_logout_clears_it():
    app = Flask(__name__)
    app.secret_key = "test-secret"

    tmp_auth = _build_auth(app, enabled=True, password_hash="")
    password_hash = tmp_auth.hash_password("s3cr3t")
    auth = _build_auth(app, enabled=True, username="admin", password_hash=password_hash)

    with app.test_request_context("/"):
        from flask import session

        assert auth.login("admin", "s3cr3t") is True
        assert session.get("authenticated") is True
        assert session.permanent is True

        auth.logout()
        assert session.get("authenticated") is None


def test_login_returns_false_for_invalid_credentials():
    app = Flask(__name__)
    app.secret_key = "test-secret"

    tmp_auth = _build_auth(app, enabled=True, password_hash="")
    password_hash = tmp_auth.hash_password("s3cr3t")
    auth = _build_auth(app, enabled=True, username="admin", password_hash=password_hash)

    with app.test_request_context("/"):
        assert auth.login("admin", "nope") is False


def test_require_auth_redirects_when_not_authenticated():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    auth = _build_auth(app, enabled=True)

    @app.route("/login")
    def login():
        return "login"

    @auth.require_auth
    def protected():
        return "protected"

    with app.test_request_context("/protected"):
        response = protected()
        assert response.status_code == 302
        assert "/login?next=" in response.location


def test_require_auth_executes_function_when_authenticated():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    auth = _build_auth(app, enabled=True)

    @auth.require_auth
    def protected():
        return "protected"

    with app.test_request_context("/protected"):
        from flask import session

        session["authenticated"] = True
        assert protected() == "protected"


def test_create_auth_decorator_redirects_when_not_authenticated():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    auth = _build_auth(app, enabled=True)
    require_auth = create_auth_decorator(auth)

    @app.route("/login")
    def login():
        return "login"

    class Controller:
        @require_auth
        def handler(self):
            return "ok"

    with app.test_request_context("/controller"):
        response = Controller().handler()
        assert response.status_code == 302
        assert "/login?next=" in response.location


def test_create_auth_decorator_executes_method_when_authenticated():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    auth = _build_auth(app, enabled=True)
    require_auth = create_auth_decorator(auth)

    class Controller:
        @require_auth
        def handler(self):
            return "ok"

    with app.test_request_context("/controller"):
        from flask import session

        session["authenticated"] = True
        assert Controller().handler() == "ok"
