"""Test suite for tools."""

import pytest
from datetime import datetime
from src.tools.leave_management import (
    check_leave_balance,
    calculate_working_days_tool,
    get_holiday_calendar
)
from src.tools.calendar_tool import (
    is_working_day,
    get_upcoming_holidays
)


class TestLeaveManagement:
    """Test leave management tools."""
    
    def test_check_leave_balance(self):
        """Test leave balance checking."""
        result = check_leave_balance("EMP123", "casual")
        assert isinstance(result, str)
        assert "EMP123" in result
        assert "casual" in result.lower()
    
    def test_calculate_working_days(self):
        """Test working days calculation."""
        result = calculate_working_days_tool("2024-12-01", "2024-12-05")
        assert isinstance(result, str)
        assert "working days" in result.lower()
    
    def test_holiday_calendar(self):
        """Test holiday calendar retrieval."""
        current_year = datetime.now().year
        result = get_holiday_calendar(current_year)
        assert isinstance(result, str)
        assert str(current_year) in result


class TestCalendarTool:
    """Test calendar tools."""
    
    def test_is_working_day(self):
        """Test working day check."""
        # Test a known weekday
        result = is_working_day("2024-12-04")  # Wednesday
        assert isinstance(result, str)
        assert "working day" in result.lower()
    
    def test_upcoming_holidays(self):
        """Test upcoming holidays."""
        result = get_upcoming_holidays(months=3)
        assert isinstance(result, str)
        assert "holidays" in result.lower() or "No holidays" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
