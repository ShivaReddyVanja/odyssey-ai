from datetime import datetime, timedelta

def get_next_date(date_str: str, days: int) -> str:
    """
    Safely adds days to a YYYY-MM-DD date string. Falls back to original string on error.
    """
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        next_dt = dt + timedelta(days=days)
        return next_dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str
