import calendar
from datetime import datetime


def parse_safe_date(date_string: str) -> datetime:
    """
    Parse a YYYY-MM-DD date string and ensure the year is at least 1.
    Handles invalid day values by capping to the last valid day of the month.

    Args:
        date_string: Date string in YYYY-MM-DD format

    Returns:
        Safe datetime object with year >= 1
    """
    try:
        date_string = date_string.replace("0000-", "0001-")
        date_obj = datetime.strptime(date_string, "%Y-%m-%d")
        if date_obj.year < 1:
            # Replace year 0 or negative years with year 1
            return date_obj.replace(year=1)
        return date_obj
    except ValueError as e:
        # Try to handle invalid day values (e.g., 2021-06-31)
        if "day is out of range for month" in str(e):
            parts = date_string.split("-")
            if len(parts) == 3:
                year = int(parts[0])
                month = int(parts[1])
                # Get the last valid day of the month
                last_day = calendar.monthrange(year, month)[1]
                # Use the last valid day instead
                corrected_date = f"{year:04d}-{month:02d}-{last_day:02d}"
                date_obj = datetime.strptime(corrected_date, "%Y-%m-%d")
                if date_obj.year < 1:
                    return date_obj.replace(year=1)
                return date_obj
        raise ValueError(
            f"Invalid date format: {date_string}. Expected YYYY-MM-DD"
        )
