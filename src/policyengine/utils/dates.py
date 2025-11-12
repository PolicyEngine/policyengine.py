from datetime import datetime


def parse_safe_date(date_string: str) -> datetime:
    """
    Parse a YYYY-MM-DD date string and ensure the year is at least 1.

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
    except ValueError:
        raise ValueError(
            f"Invalid date format: {date_string}. Expected YYYY-MM-DD"
        )
