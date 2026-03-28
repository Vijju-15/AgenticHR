"""Calendar and working days calculation tools."""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import holidays
from loguru import logger


def get_upcoming_holidays(months: int = 3) -> str:
    """
    Get upcoming holidays for the next N months.
    
    Args:
        months: Number of months to look ahead (default: 3)
        
    Returns:
        String listing upcoming holidays
    """
    try:
        today = datetime.now().date()
        end_date = today + timedelta(days=months * 30)
        
        # Get holidays for relevant years
        years = list(set([today.year, end_date.year]))
        all_holidays = {}
        
        for year in years:
            year_holidays = holidays.US(years=year)
            all_holidays.update(year_holidays)
        
        # Filter for upcoming holidays
        upcoming = [
            (date, name) for date, name in all_holidays.items()
            if today <= date <= end_date
        ]
        
        if not upcoming:
            return f"No holidays in the next {months} months."
        
        # Sort by date
        upcoming.sort(key=lambda x: x[0])
        
        # Format output
        output = [f"Upcoming Holidays (next {months} months):\n"]
        
        for holiday_date, holiday_name in upcoming:
            days_until = (holiday_date - today).days
            output.append(
                f"- {holiday_date.strftime('%A, %B %d, %Y')}: {holiday_name} "
                f"({days_until} days from now)"
            )
        
        return "\n".join(output)
    
    except Exception as e:
        logger.error(f"Error getting upcoming holidays: {e}")
        return f"Error retrieving upcoming holidays: {str(e)}"


def is_working_day(date_str: str) -> str:
    """
    Check if a given date is a working day.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        String indicating if the date is a working day
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Check if weekend
        if date.weekday() >= 5:  # Saturday=5, Sunday=6
            day_name = date.strftime('%A')
            return f"{date_str} is a {day_name} (weekend). It is not a working day."
        
        # Check if holiday
        us_holidays = holidays.US(years=date.year)
        if date in us_holidays:
            holiday_name = us_holidays[date]
            return f"{date_str} is {holiday_name}. It is not a working day."
        
        day_name = date.strftime('%A')
        return f"{date_str} is a {day_name}. It is a working day."
    
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD format."
    except Exception as e:
        logger.error(f"Error checking working day: {e}")
        return f"Error checking if date is working day: {str(e)}"


def get_next_working_day(date_str: str) -> str:
    """
    Get the next working day after a given date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        String with the next working day
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        us_holidays = holidays.US(years=[date.year, date.year + 1])
        
        next_day = date + timedelta(days=1)
        
        # Find next working day
        while True:
            # Skip weekends
            if next_day.weekday() < 5:  # Monday to Friday
                # Skip holidays
                if next_day not in us_holidays:
                    break
            
            next_day += timedelta(days=1)
        
        return (
            f"The next working day after {date_str} is "
            f"{next_day.strftime('%A, %B %d, %Y')} ({next_day})"
        )
    
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD format."
    except Exception as e:
        logger.error(f"Error getting next working day: {e}")
        return f"Error finding next working day: {str(e)}"


def get_month_info(year: int = None, month: int = None) -> str:
    """
    Get information about a specific month including working days and holidays.
    
    Args:
        year: Year (defaults to current year)
        month: Month (1-12, defaults to current month)
        
    Returns:
        String with month information
    """
    try:
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        # Get first and last day of month
        first_day = datetime(year, month, 1).date()
        
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Count working days
        working_days = 0
        weekend_days = 0
        current_date = first_day
        us_holidays = holidays.US(years=year)
        month_holidays = []
        
        while current_date <= last_day:
            if current_date.weekday() < 5:  # Weekday
                if current_date not in us_holidays:
                    working_days += 1
                else:
                    month_holidays.append((current_date, us_holidays[current_date]))
            else:
                weekend_days += 1
            
            current_date += timedelta(days=1)
        
        # Format output
        month_name = first_day.strftime('%B %Y')
        total_days = (last_day - first_day).days + 1
        
        output = [
            f"Month Information: {month_name}\n",
            f"Total Days: {total_days}",
            f"Working Days: {working_days}",
            f"Weekend Days: {weekend_days}",
            f"Holidays: {len(month_holidays)}\n"
        ]
        
        if month_holidays:
            output.append("Holidays in this month:")
            for holiday_date, holiday_name in month_holidays:
                output.append(f"  - {holiday_date.strftime('%B %d')}: {holiday_name}")
        
        return "\n".join(output)
    
    except Exception as e:
        logger.error(f"Error getting month info: {e}")
        return f"Error retrieving month information: {str(e)}"
