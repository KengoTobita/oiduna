"""
Unit tests for authentication utilities.
"""

import pytest
from oiduna.infrastructure.auth import generate_token, validate_token, AuthConfig, load_auth_config


class TestToken:
    """Test token utilities."""

    def test_generate_token(self):
        """Test token generation."""
        token = generate_token()
        assert len(token) == 36
        assert token.count("-") == 4

    def test_generate_unique_tokens(self):
        """Test tokens are unique."""
        tokens = {generate_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_validate_valid_token(self):
        """Test validating a valid token."""
        token = generate_token()
        assert validate_token(token) is True

    def test_validate_invalid_token(self):
        """Test validating invalid tokens."""
        assert validate_token("invalid") is False
        assert validate_token("") is False
        assert validate_token("not-a-uuid") is False


class TestAuthConfig:
    """Test auth configuration."""

    def test_auth_config_defaults(self):
        """Test default auth config."""
        config = AuthConfig()
        assert config.admin_password == "change_me_in_production"

    def test_auth_config_custom(self):
        """Test custom auth config."""
        config = AuthConfig(admin_password="secure_password")
        assert config.admin_password == "secure_password"

    def test_load_auth_config_no_file(self, tmp_path):
        """Test loading config when file doesn't exist."""
        config_path = tmp_path / "nonexistent.yaml"
        config = load_auth_config(config_path)
        assert config.admin_password == "change_me_in_production"

    def test_load_auth_config_with_file(self, tmp_path):
        """Test loading config from file."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
auth:
  admin_password: "test_password"
""")
        config = load_auth_config(config_path)
        assert config.admin_password == "test_password"

    def test_load_auth_config_empty_file(self, tmp_path):
        """Test loading config from empty file."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("")
        config = load_auth_config(config_path)
        assert config.admin_password == "change_me_in_production"
