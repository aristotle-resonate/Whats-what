from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from app.tasks.collect import run_collectors_for_city


def test_run_collectors_for_city_returns_counts():
    mock_run = AsyncMock(return_value=5)
    with patch("app.tasks.collect.ALL_COLLECTORS") as mock_collectors:
        mock_collector = MagicMock()
        mock_collector.source_name = "test_source"
        mock_collector.run = mock_run
        mock_collectors.__iter__ = MagicMock(return_value=iter([mock_collector]))

        result = run_collectors_for_city("austin")

    assert "test_source" in result
    assert result["test_source"] == 5
