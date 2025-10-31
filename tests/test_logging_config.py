"""Tests for unified logging configuration."""

import logging
import os
from unittest.mock import patch

import pytest

from aquable.logging_config import (
    configure_logging,
    get_log_level,
    get_logging_config,
    get_uvicorn_log_config,
)


def test_get_log_level_default():
    """Test that get_log_level returns INFO by default."""
    with patch.dict(os.environ, {}, clear=True):
        assert get_log_level() == "INFO"


def test_get_log_level_from_env():
    """Test that get_log_level reads from environment variable."""
    with patch.dict(os.environ, {"AQUA_BLE_LOG_LEVEL": "DEBUG"}):
        assert get_log_level() == "DEBUG"


def test_get_log_level_empty_env():
    """Test that get_log_level handles empty environment variable."""
    with patch.dict(os.environ, {"AQUA_BLE_LOG_LEVEL": ""}):
        assert get_log_level() == "INFO"


def test_get_logging_config_structure():
    """Test that get_logging_config returns a valid logging dict."""
    config = get_logging_config()
    
    # Check basic structure
    assert config["version"] == 1
    assert "formatters" in config
    assert "handlers" in config
    assert "loggers" in config
    assert "root" in config
    
    # Check formatters
    assert "default" in config["formatters"]
    assert "access" in config["formatters"]
    assert "%(asctime)s" in config["formatters"]["default"]["format"]
    
    # Check handlers
    assert "default" in config["handlers"]
    assert "access" in config["handlers"]
    
    # Check loggers
    assert "uvicorn" in config["loggers"]
    assert "uvicorn.error" in config["loggers"]
    assert "uvicorn.access" in config["loggers"]
    assert "aquable" in config["loggers"]


def test_get_logging_config_respects_env_level():
    """Test that logging config respects AQUA_BLE_LOG_LEVEL."""
    with patch.dict(os.environ, {"AQUA_BLE_LOG_LEVEL": "DEBUG"}):
        config = get_logging_config()
        assert config["loggers"]["aquable"]["level"] == "DEBUG"
        assert config["loggers"]["uvicorn"]["level"] == "DEBUG"


def test_get_uvicorn_log_config_matches_main_config():
    """Test that uvicorn config matches main logging config."""
    main_config = get_logging_config()
    uvicorn_config = get_uvicorn_log_config()
    
    assert main_config == uvicorn_config


def test_configure_logging_sets_up_handlers():
    """Test that configure_logging sets up logging handlers."""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure logging
    configure_logging()
    
    # Check that handlers were added
    assert len(logging.getLogger().handlers) > 0
    
    # Check that named loggers are configured
    aquable_logger = logging.getLogger("aquable")
    assert aquable_logger.level == logging.INFO or aquable_logger.level == logging.NOTSET
    
    uvicorn_logger = logging.getLogger("uvicorn")
    assert uvicorn_logger.level == logging.INFO or uvicorn_logger.level == logging.NOTSET


def test_configure_logging_with_timezone():
    """Test that configure_logging handles TZ environment variable."""
    with patch.dict(os.environ, {"TZ": "America/New_York"}):
        # Should not raise any exceptions
        configure_logging()
        
        # Verify logger was created
        assert logging.getLogger(__name__)


def test_logging_format_includes_timestamp():
    """Test that log format includes timestamp."""
    config = get_logging_config()
    default_format = config["formatters"]["default"]["format"]
    
    # Check for timestamp placeholder
    assert "%(asctime)s" in default_format
    assert "%(levelname)" in default_format
    assert "%(name)s" in default_format
    assert "%(message)s" in default_format


def test_logging_format_includes_date_format():
    """Test that log format includes date format."""
    config = get_logging_config()
    default_formatter = config["formatters"]["default"]
    
    assert "datefmt" in default_formatter
    assert default_formatter["datefmt"] == "%Y-%m-%d %H:%M:%S"
