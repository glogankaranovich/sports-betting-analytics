"""Compliance logger tests"""

from unittest.mock import Mock, patch

import pytest

from compliance_logger import ComplianceLogger


@pytest.fixture
def logger():
    with patch("compliance_logger.boto3"):
        return ComplianceLogger()


def test_init(logger):
    """Test init"""
    assert logger.table is not None


def test_log_user_action_success(logger):
    """Test logging action"""
    logger.table.put_item = Mock()
    
    result = logger.log_user_action("session1", "login", {"user": "test"})
    assert result is True
    logger.table.put_item.assert_called_once()


def test_log_user_action_no_data(logger):
    """Test logging without user data"""
    logger.table.put_item = Mock()
    
    result = logger.log_user_action("session1", "logout")
    assert result is True


def test_log_user_action_error(logger):
    """Test logging error"""
    logger.table.put_item = Mock(side_effect=Exception("Error"))
    
    result = logger.log_user_action("session1", "login")
    assert result is False


def test_log_age_verification(logger):
    """Test age verification logging"""
    with patch.object(logger, "log_user_action", return_value=True):
        result = logger.log_age_verification("session1", True, 25)
        assert result is True


def test_log_age_verification_failed(logger):
    """Test failed age verification"""
    with patch.object(logger, "log_user_action", return_value=True):
        result = logger.log_age_verification("session1", False, 17)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
