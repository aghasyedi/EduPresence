from datetime import datetime, timedelta

def time_ago(timestamp):
    """Converts a timestamp into a human-readable 'time ago' string.
    Parameters: timestamp (datetime) - The datetime object to compare with the current time
    Returns: str - A string describing how long ago the timestamp was (e.g., '5 minutes ago', '3 days ago')
    Detailed Explanation:
        - This function takes a datetime object (timestamp) and calculates how much time has passed since then compared to now.
        - It uses datetime.now() to get the current time and computes the difference (delta) by subtracting the timestamp.
        - Based on the size of delta, it returns a formatted string:
            - If more than 2 weeks ago, returns the date in 'MM/DD/YYYY' format (e.g., '05/13/2025').
            - If less than 60 seconds, shows seconds (e.g., '30 seconds ago').
            - If less than 60 minutes, shows minutes (e.g., '5 minutes ago').
            - If less than 24 hours, shows hours (e.g., '3 hours ago').
            - If less than 7 days, shows days (e.g., '2 days ago').
            - If less than 2 weeks, shows weeks (e.g., '1 week ago').
        - Adds an 's' for plural forms (e.g., '1 minute ago' vs. '2 minutes ago') using a conditional expression.
        - The function is useful for displaying timestamps in a user-friendly way, like in social media posts or activity logs.
    Related: None (standalone utility function, likely used in Flask app to format timestamps for display)
    """
    # Get the current time
    now = datetime.now()
    # Calculate the time difference between now and the input timestamp
    delta = now - timestamp

    # If more than 2 weeks ago, return the date in MM/DD/YYYY format
    if delta > timedelta(weeks=2):
        return timestamp.strftime('%m/%d/%Y')  

    # If less than 60 seconds, show the number of seconds
    if delta < timedelta(seconds=60):
        return f"{delta.seconds} second{'s' if delta.seconds > 1 else ''} ago"
    # If less than 60 minutes, calculate and show minutes
    elif delta < timedelta(minutes=60):
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    # If less than 24 hours, calculate and show hours
    elif delta < timedelta(hours=24):
        hours = delta.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    # If less than 7 days, show days
    elif delta < timedelta(days=7):
        days = delta.days
        return f"{days} day{'s' if days > 1 else ''} ago"
    # If less than 2 weeks, calculate and show weeks
    elif delta < timedelta(weeks=2):
        weeks = delta.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"