"""Leave management tools for the HR assistant."""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from loguru import logger
import holidays
import json
from pathlib import Path

from src.config import settings


# Mock employee database (in production, this would be a real database)
EMPLOYEE_DB_FILE = Path("data/employee_db.json")


class LeaveBalance:
    """Manages employee leave balances."""
    
    @staticmethod
    def _load_employee_data() -> Dict[str, Any]:
        """Load employee data from file."""
        if EMPLOYEE_DB_FILE.exists():
            with open(EMPLOYEE_DB_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def _save_employee_data(data: Dict[str, Any]):
        """Save employee data to file."""
        EMPLOYEE_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EMPLOYEE_DB_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def get_balance(employee_id: str, leave_type: str) -> int:
        """Get leave balance for an employee."""
        db = LeaveBalance._load_employee_data()
        
        if employee_id not in db:
            # Return default balance for new employee
            defaults = {
                "casual": settings.default_leave_balance_casual,
                "sick": settings.default_leave_balance_sick,
                "earned": settings.default_leave_balance_earned
            }
            return defaults.get(leave_type.lower(), 0)
        
        employee = db[employee_id]
        balances = employee.get("leave_balances", {})
        return balances.get(leave_type.lower(), 0)
    
    @staticmethod
    def deduct_leave(employee_id: str, leave_type: str, days: int) -> bool:
        """Deduct leave from balance."""
        db = LeaveBalance._load_employee_data()
        
        if employee_id not in db:
            # Initialize employee
            db[employee_id] = {
                "name": f"Employee {employee_id}",
                "department": "Engineering",
                "leave_balances": {
                    "casual": settings.default_leave_balance_casual,
                    "sick": settings.default_leave_balance_sick,
                    "earned": settings.default_leave_balance_earned
                },
                "leave_history": []
            }
        
        employee = db[employee_id]
        balances = employee.get("leave_balances", {})
        current_balance = balances.get(leave_type.lower(), 0)
        
        if current_balance >= days:
            balances[leave_type.lower()] = current_balance - days
            employee["leave_balances"] = balances
            db[employee_id] = employee
            LeaveBalance._save_employee_data(db)
            return True
        
        return False


class WorkingDaysCalculator:
    """Calculate working days between dates."""
    
    @staticmethod
    def get_company_holidays(year: int = None) -> list:
        """Get company holidays for a year."""
        if year is None:
            year = datetime.now().year
        
        # Using US holidays as example - customize for your region
        us_holidays = holidays.US(years=year)
        
        # Add company-specific holidays
        company_holidays = list(us_holidays.keys())
        
        return company_holidays
    
    @staticmethod
    def calculate_working_days(
        start_date: str,
        end_date: str,
        exclude_holidays: bool = True
    ) -> int:
        """
        Calculate working days between two dates.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            exclude_holidays: Whether to exclude company holidays
            
        Returns:
            Number of working days
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        if start > end:
            raise ValueError("Start date must be before end date")
        
        # Get holidays if needed
        holiday_dates = []
        if exclude_holidays:
            years = range(start.year, end.year + 1)
            for year in years:
                holiday_dates.extend(WorkingDaysCalculator.get_company_holidays(year))
        
        # Count working days
        working_days = 0
        current_date = start
        
        while current_date <= end:
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:
                # Skip holidays
                if not exclude_holidays or current_date.date() not in holiday_dates:
                    working_days += 1
            
            current_date += timedelta(days=1)
        
        return working_days


# Tool function definitions for LangChain

def check_leave_balance(employee_id: str, leave_type: str) -> str:
    """
    Check remaining leave balance for an employee.
    
    Args:
        employee_id: Employee ID (e.g., EMP123)
        leave_type: Type of leave - 'casual', 'sick', or 'earned'
        
    Returns:
        String describing the leave balance
    """
    try:
        leave_type = leave_type.lower()
        if leave_type not in ['casual', 'sick', 'earned']:
            return f"Invalid leave type. Please use 'casual', 'sick', or 'earned'."
        
        balance = LeaveBalance.get_balance(employee_id, leave_type)
        
        return f"Employee {employee_id} has {balance} {leave_type} leaves remaining."
    
    except Exception as e:
        logger.error(f"Error checking leave balance: {e}")
        return f"Error checking leave balance: {str(e)}"


def apply_leave(
    employee_id: str,
    start_date: str,
    end_date: str,
    leave_type: str,
    reason: str
) -> str:
    """
    Apply for leave and send notification to HR.
    
    This tool:
    1. Validates leave eligibility based on company policy
    2. Checks leave balance
    3. Creates leave application
    4. Sends email notification to HR
    
    Args:
        employee_id: Employee ID (e.g., EMP123)
        start_date: Leave start date in YYYY-MM-DD format
        end_date: Leave end date in YYYY-MM-DD format
        leave_type: Type of leave - 'casual', 'sick', or 'earned'
        reason: Reason for leave
        
    Returns:
        String describing the result of the leave application
    """
    try:
        leave_type = leave_type.lower()
        
        # Validate leave type
        if leave_type not in ['casual', 'sick', 'earned']:
            return "Invalid leave type. Please use 'casual', 'sick', or 'earned'."
        
        # Calculate working days
        days_requested = WorkingDaysCalculator.calculate_working_days(
            start_date, end_date
        )
        
        # Check balance
        current_balance = LeaveBalance.get_balance(employee_id, leave_type)
        
        if days_requested > current_balance:
            return (
                f"Insufficient leave balance. You requested {days_requested} days "
                f"but only have {current_balance} {leave_type} leaves remaining."
            )
        
        # Deduct leave
        success = LeaveBalance.deduct_leave(employee_id, leave_type, days_requested)
        
        if not success:
            return "Failed to process leave application. Please contact HR."
        
        # Create application record
        db = LeaveBalance._load_employee_data()
        employee = db.get(employee_id, {})
        
        leave_history = employee.get("leave_history", [])
        application_id = f"LA{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        leave_record = {
            "application_id": application_id,
            "start_date": start_date,
            "end_date": end_date,
            "leave_type": leave_type,
            "days": days_requested,
            "reason": reason,
            "status": "pending_approval",
            "applied_on": datetime.now().isoformat()
        }
        
        leave_history.append(leave_record)
        employee["leave_history"] = leave_history
        db[employee_id] = employee
        LeaveBalance._save_employee_data(db)
        
        # Log the application
        logger.info(
            f"Leave application {application_id} created for {employee_id}: "
            f"{days_requested} days from {start_date} to {end_date}"
        )
        
        # In production, this would send an actual email
        # For now, we'll just log it
        logger.info(f"Email notification sent to HR for application {application_id}")
        
        new_balance = current_balance - days_requested
        
        return (
            f"Leave application submitted successfully!\n\n"
            f"Application ID: {application_id}\n"
            f"Leave Type: {leave_type.title()}\n"
            f"Duration: {start_date} to {end_date} ({days_requested} working days)\n"
            f"Status: Pending HR approval\n"
            f"Remaining {leave_type} leave balance: {new_balance} days\n\n"
            f"An email notification has been sent to HR. "
            f"You will be notified once your leave is approved."
        )
    
    except ValueError as e:
        return f"Invalid date format or range: {str(e)}"
    except Exception as e:
        logger.error(f"Error applying leave: {e}")
        return f"Error processing leave application: {str(e)}"


def get_holiday_calendar(year: Optional[int] = None) -> str:
    """
    Get the company holiday calendar for a specific year.
    
    Args:
        year: Year for which to get holidays (defaults to current year)
        
    Returns:
        String listing all company holidays
    """
    try:
        if year is None:
            year = datetime.now().year
        
        holidays_list = WorkingDaysCalculator.get_company_holidays(year)
        
        if not holidays_list:
            return f"No holidays found for year {year}"
        
        # Sort holidays by date
        sorted_holidays = sorted(holidays_list)
        
        # Format output
        output = [f"Company Holidays for {year}:\n"]
        
        for holiday_date in sorted_holidays:
            holiday_name = holidays.US().get(holiday_date, "Company Holiday")
            output.append(
                f"- {holiday_date.strftime('%A, %B %d, %Y')}: {holiday_name}"
            )
        
        output.append(f"\nTotal: {len(sorted_holidays)} holidays")
        
        return "\n".join(output)
    
    except Exception as e:
        logger.error(f"Error getting holiday calendar: {e}")
        return f"Error retrieving holiday calendar: {str(e)}"


def calculate_working_days_tool(
    start_date: str,
    end_date: str
) -> str:
    """
    Calculate the number of working days between two dates.
    Excludes weekends and company holidays.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        String describing the number of working days
    """
    try:
        working_days = WorkingDaysCalculator.calculate_working_days(
            start_date, end_date
        )
        
        return (
            f"Between {start_date} and {end_date}, there are "
            f"{working_days} working days (excluding weekends and holidays)."
        )
    
    except Exception as e:
        logger.error(f"Error calculating working days: {e}")
        return f"Error calculating working days: {str(e)}"


def get_leave_history(employee_id: str) -> str:
    """
    Get the leave history for an employee.
    
    Args:
        employee_id: Employee ID
        
    Returns:
        String describing the leave history
    """
    try:
        db = LeaveBalance._load_employee_data()
        
        if employee_id not in db:
            return f"No leave history found for employee {employee_id}"
        
        employee = db[employee_id]
        leave_history = employee.get("leave_history", [])
        
        if not leave_history:
            return f"Employee {employee_id} has no leave applications yet."
        
        output = [f"Leave History for {employee_id}:\n"]
        
        for record in leave_history:
            output.append(
                f"Application ID: {record['application_id']}\n"
                f"  Type: {record['leave_type'].title()}\n"
                f"  Dates: {record['start_date']} to {record['end_date']} ({record['days']} days)\n"
                f"  Reason: {record['reason']}\n"
                f"  Status: {record['status']}\n"
                f"  Applied on: {record['applied_on']}\n"
            )
        
        return "\n".join(output)
    
    except Exception as e:
        logger.error(f"Error getting leave history: {e}")
        return f"Error retrieving leave history: {str(e)}"
