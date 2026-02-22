"""User model weight adjuster tests"""

from unittest.mock import Mock, patch

import pytest


def test_module_imports():
    """Test module can be imported"""
    from user_model_weight_adjuster import get_data_source_accuracy
    assert get_data_source_accuracy is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
