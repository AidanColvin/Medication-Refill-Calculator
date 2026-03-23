import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# --- Date Parsing Constants ---
_MONTH_FIXES: Dict[str, str] = {
    r'\b(januray|janury|janaury)\b': 'January',
    r'\b(febuary|feburary|febrary)\b': 'February',
    r'\b(marhc|marcg)\b': 'March',
    r'\b(arpil|apirl|paril)\b': 'April',
    r'\b(juen|jne)\b': 'June',
    r'\b(jully|juy)\b': 'July',
    r'\b(auguts|agust)\b': 'August',
    r'\b(septmber|setember)\b': 'September',
    r'\b(ocotber|octber)\b': 'October',
    r'\b(novmber|noveber|nvember)\b': 'November',
    r'\b(decmber|deceber|dcember)\b': 'December',
}

_ORDINAL_RE = re.compile(r'(?<=\d)(st|nd|rd|th)\b', re.I)
_AGO_RE = re.compile(r'(\d+)\s*(day|week|month|year)s?\s*ago', re.I)
_ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_NON_NUMERIC_RE = re.compile(r'[\-/. ]+')

_WEEKDAYS = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6
}
_MONTH_NAMES = {
    'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
    'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
    'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9, 'october': 10, 'oct': 10,
    'november': 11, 'nov': 11, 'december': 12, 'dec': 12
}

# --- Parsing Logic ---

def _safe_date(year: int, month: int, day: int) -> Optional[datetime]:
    """Validates year, month, and day combination."""
    try:
        return datetime(year, month, day)
    except ValueError:
        return None

def standardize_last_filled(last_filled: str) -> datetime.date:
    """
    Parses a raw date string into a standardized date object.
    Uses regex fallbacks to handle typos, relative dates, and ordinals.
    """
    if not isinstance(last_filled, str) or not last_filled.strip():
        raise ValueError("Input must be a non-empty string.")

    now = datetime.now()
    s = last_filled.strip()
    
    # Clean string
    for pattern, replacement in _MONTH_FIXES.items():
        s = re.sub(pattern, replacement, s, flags=re.I)
    s = _ORDINAL_RE.sub('', s)
    s_lower = s.lower()

    # 1. Relative dates
    if s_lower in ('today', 'now'): return now.date()
    if s_lower == 'yesterday': return (now - timedelta(days=1)).date()
    if s_lower == 'tomorrow': return (now + timedelta(days=1)).date()

    # 2. X days ago
    ago_match = _AGO_RE.match(s_lower)
    if ago_match:
        val, unit = int(ago_match.group(1)), ago_match.group(2)
        if unit == 'day': return (now - timedelta(days=val)).date()
        if unit == 'week': return (now - timedelta(weeks=val)).date()

    # 3. Standard parsing attempts
    formats = (
        '%m/%d/%Y', '%m-%d-%Y', '%m.%d.%Y', '%Y-%m-%d',
        '%m/%d/%y', '%m-%d-%y', '%B %d %Y', '%b %d %Y',
        '%B %d', '%b %d', '%m/%d', '%m-%d'
    )
    for fmt in formats:
        try:
            d = datetime.strptime(s, fmt)
            if d.year == 1900:
                d = d.replace(year=now.year)
            return d.date()
        except ValueError:
            continue
            
    # 4. Fuzzy text fallback
    month_num = None
    for name, num in _MONTH_NAMES.items():
        if name in s_lower:
            month_num = num
            break
    
    day_match = re.search(r'\b(\d{1,2})\b', s_lower)
    if month_num and day_match:
        day = int(day_match.group(1))
        year_match = re.search(r'\b(19|20)\d{2}\b', s_lower)
        year = int(year_match.group(0)) if year_match else now.year
        valid_date = _safe_date(year, month_num, day)
        if valid_date:
            return valid_date.date()

    raise ValueError(f"Unable to parse date: '{last_filled}'")

# --- Core Calculations ---

def calculate_refill_metrics(
    last_filled: str,
    day_supply: int = 30,
    quantity: Optional[int] = None,
    taken_per_day: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculates refill dates, pills taken, and days remaining.
    
    Args:
        last_filled: Raw string of last fill date.
        day_supply: Total days the supply should last.
        quantity: Total pills dispensed.
        taken_per_day: Expected daily pill consumption.
        
    Returns:
        Dictionary containing tracking metrics and formatted dates.
    """
    fill_date = standardize_last_filled(last_filled)
    today = datetime.now().date()
    days_elapsed = (today - fill_date).days
    current_day_num = days_elapsed + 1
    
    # Calculate target refill day (usually 2 days before empty)
    refill_day_offset = min(28, day_supply - 2) if day_supply > 2 else day_supply
    refill_date = fill_date + timedelta(days=refill_day_offset - 1)
    days_until_refill = max(0, (refill_date - today).days)

    result = {
        'fill_date': fill_date,
        'today': today,
        'days_elapsed': days_elapsed,
        'current_day_num': current_day_num,
        'refill_date': refill_date,
        'days_until_refill': days_until_refill,
        'day_supply': day_supply,
        'has_quantity_metrics': False
    }

    # Calculate pill consumption if data is provided
    if quantity is not None and taken_per_day is not None and taken_per_day > 0:
        should_have_taken = round(days_elapsed * taken_per_day, 1)
        should_have_left = max(0, quantity - should_have_taken)
        days_remaining = round(should_have_left / taken_per_day, 1)
        
        result.update({
            'has_quantity_metrics': True,
            'quantity': quantity,
            'taken_per_day': taken_per_day,
            'should_have_taken': should_have_taken,
            'should_have_left': should_have_left,
            'days_remaining': days_remaining
        })

    return result
