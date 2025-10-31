"""Schedule calculation utilities for light devices."""

from datetime import datetime, time

def get_weekday_str() -> str:
    """Get the current day of the week as a lowercase string."""
    return datetime.now().strftime('%A').lower()

def time_to_minutes(time_obj: time) -> int:
    """Convert a time object to minutes since midnight."""
    return time_obj.hour * 60 + time_obj.minute

def is_time_in_program(program: dict, current_minutes: int) -> bool:
    """Check if the current time is within a program's active period."""
    sunrise_minutes = time_to_minutes(datetime.strptime(program['sunrise'], '%H:%M').time())
    sunset_minutes = time_to_minutes(datetime.strptime(program['sunset'], '%H:%M').time())

    if sunrise_minutes <= sunset_minutes:
        # Same day program (e.g., 08:00-18:00)
        return sunrise_minutes <= current_minutes <= sunset_minutes
    else:
        # Overnight program (e.g., 20:00-08:00)
        return current_minutes >= sunrise_minutes or current_minutes <= sunset_minutes

def get_next_occurrence(program: dict, current_weekday: str, current_minutes: int) -> dict | None:
    """Get the next occurrence of a program."""
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    # Adjust to match Python's weekday() (Monday is 0)
    py_weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    current_day_index = py_weekdays.index(current_weekday)
    sunrise_minutes = time_to_minutes(datetime.strptime(program['sunrise'], '%H:%M').time())

    # Check if program runs today and hasn't started yet
    if current_weekday in program['days'] and current_minutes < sunrise_minutes:
        return {
            'day': 'today',
            'time': program['sunrise'],
            'minutes': sunrise_minutes
        }

    # Find next day in the week that this program runs
    for i in range(1, 8):
        check_day_index = (current_day_index + i) % 7
        check_day = py_weekdays[check_day_index]

        if check_day in program['days']:
            day_name = 'tomorrow' if i == 1 else check_day
            return {
                'day': day_name,
                'time': program['sunrise'],
                'minutes': sunrise_minutes + (i * 24 * 60)
            }
    return None

def get_schedules_with_status(programs: list[dict]) -> list[dict]:
    """
    Takes a list of light auto programs and returns them with an added 'status' field.
    This revised logic is more robust and ensures every program gets a status.
    """
    if not programs:
        return []

    now = datetime.now()
    current_weekday = get_weekday_str()
    current_minutes = time_to_minutes(now.time())

    statuses = {}  # program_id -> status

    # Separate enabled and disabled programs
    enabled_programs = [p for p in programs if p.get('enabled', False)]
    disabled_programs = [p for p in programs if not p.get('enabled', False)]

    # 1. Identify 'current' programs
    for p in enabled_programs:
        if current_weekday in p.get('days', []) and is_time_in_program(p, current_minutes):
            statuses[p['id']] = 'current'

    # 2. Identify the single 'next' program from the remaining enabled ones
    next_occurrences = []
    for p in enabled_programs:
        if p['id'] not in statuses:  # Only consider non-current programs
            occurrence = get_next_occurrence(p, current_weekday, current_minutes)
            if occurrence:
                next_occurrences.append({'program_id': p['id'], **occurrence})
    
    if next_occurrences:
        next_occurrences.sort(key=lambda x: x['minutes'])
        next_program_id = next_occurrences[0]['program_id']
        statuses[next_program_id] = 'next'

    # 3. Build the final list, assigning statuses
    result = []
    for p in programs:
        # Determine the status for the program
        status = statuses.get(p['id'])
        if not status:
            if p.get('enabled', False):
                status = 'upcoming'  # Any enabled program that is not current or next
            else:
                status = 'disabled'
        
        result.append({**p, 'status': status})
        
    return result
