"""Unit tests for ScheduleContextGenerator."""

from datetime import datetime
from unittest.mock import patch

from ai_companion.modules.schedules.context_generation import ScheduleContextGenerator


def test_get_schedule_for_day_returns_dict():
    """get_schedule_for_day should return a non-empty dict for each weekday."""
    for day in range(7):
        schedule = ScheduleContextGenerator.get_schedule_for_day(day)
        assert isinstance(schedule, dict)
        assert len(schedule) > 0, f"Schedule for day {day} is empty"


def test_get_schedule_for_invalid_day_returns_empty():
    """get_schedule_for_day should return empty dict for an invalid day."""
    result = ScheduleContextGenerator.get_schedule_for_day(99)
    assert result == {}


def test_get_current_activity_returns_string_or_none():
    """get_current_activity should return a non-empty string or None."""
    result = ScheduleContextGenerator.get_current_activity()
    assert result is None or (isinstance(result, str) and len(result) > 0)


def test_parse_time_range_normal():
    """_parse_time_range should correctly parse a standard time range."""
    start, end = ScheduleContextGenerator._parse_time_range("09:00-10:00")
    assert start < end


def test_parse_time_range_overnight():
    """_parse_time_range should correctly parse an overnight time range."""
    start, end = ScheduleContextGenerator._parse_time_range("23:00-06:00")
    assert start > end  # Overnight: start is after end


def test_get_current_activity_midday_monday():
    """Activity should be found for Monday at noon."""
    mock_now = datetime(2024, 1, 1, 12, 0, 0)  # Monday at noon
    with patch("ai_companion.modules.schedules.context_generation.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.strptime = datetime.strptime
        result = ScheduleContextGenerator.get_current_activity()
    assert result is not None
    assert isinstance(result, str)
