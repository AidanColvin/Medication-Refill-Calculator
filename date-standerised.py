import re
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict

# --- 1. CONSTANTS & REGEX COMPILATION ---
# Pre-compiling regex improves performance by doing the heavy lifting once at startup.

# Map of common typos to correct month names
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

# Regex for specific patterns
_ORDINAL_RE = re.compile(r'(?<=\d)(st|nd|rd|th)\b', re.I)  # Matches 1st, 2nd, etc.
_AGO_RE = re.compile(r'(\d+)\s*(day|week|month|year)s?\s*ago', re.I)
_ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')  # Strict YYYY-MM-DD
_NON_NUMERIC_RE = re.compile(r'[\-/. ]+')

# Lookups for relative date logic
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


# --- 2. HELPER FUNCTIONS (LOGIC PATHWAYS) ---

def _safe_date(year: int, month: int, day: int) -> Optional[datetime]:
    """
    Validates if a year/month/day combination is real.
    Handles leap years and invalid days (e.g., Feb 30) automatically.
    """
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def _clean_input_string(s: str) -> str:
    """
    Step 1: Normalization.
    Fixes typos and removes ordinal suffixes (st, nd, rd, th) to make parsing easier.
    """
    s = s.strip()
    # Fix known misspellings
    for pattern, replacement in _MONTH_FIXES.items():
        s = re.sub(pattern, replacement, s, flags=re.I)
    # Remove ordinals (e.g., "15th" -> "15")
    s = _ORDINAL_RE.sub('', s)
    return s


def _parse_relative_dates(s: str, now: datetime) -> Optional[datetime]:
    """
    Step 2: Relative Logic.
    Handles words like 'today', 'yesterday', 'ago', 'last friday'.
    """
    s_lower = s.lower()
    
    # Immediate mappings
    if s_lower in ('today', 'now'):
        return now
    if s_lower == 'yesterday':
        return now - timedelta(days=1)
    if s_lower == 'tomorrow':
        return now + timedelta(days=1)
    if s_lower in ('this week', 'this month', 'this year'):
        return now

    # "X [unit] ago" logic
    ago_match = _AGO_RE.match(s_lower)
    if ago_match:
        val = int(ago_match.group(1))
        unit = ago_match.group(2)
        if unit == 'day': return now - timedelta(days=val)
        if unit == 'week': return now - timedelta(weeks=val)
        if unit == 'month': return now - timedelta(days=30 * val) # Approx
        if unit == 'year': return now - timedelta(days=365 * val) # Approx

    # "Last [Day]" logic
    if s_lower.startswith('last '):
        day_name = s_lower[5:].strip()
        if day_name in _WEEKDAYS:
            current_weekday = now.weekday()
            target_weekday = _WEEKDAYS[day_name]
            # Calculate days to subtract to get to the previous instance of that day
            days_back = (current_weekday - target_weekday) % 7
            if days_back == 0: days_back = 7
            return now - timedelta(days=days_back)

    return None


def _parse_compact_numeric(s: str, now: datetime) -> Optional[datetime]:
    """
    Step 3: Compact Numeric Logic.
    Handles pure numbers with separators removed: 1115, 20241115, 0229.
    """
    # Remove all separators (- / . space)
    compact = _NON_NUMERIC_RE.sub('', s)
    
    if not compact.isdigit():
        return None
    
    length = len(compact)
    
    # Format: MMDD (Current Year)
    if length == 4:
        return _safe_date(now.year, int(compact[:2]), int(compact[2:]))
    
    # Format: MMDDYY (2-digit year)
    elif length == 6:
        m, d, y = int(compact[:2]), int(compact[2:4]), int(compact[4:])
        # Pivot year: 0-69 -> 2000s, 70-99 -> 1900s
        full_year = 2000 + y if y < 70 else 1900 + y
        return _safe_date(full_year, m, d)
        
    # Format: YYYYMMDD or MMDDYYYY
    elif length == 8:
        # Try YYYYMMDD first (Standard ISO compact)
        y, m, d = int(compact[:4]), int(compact[4:6]), int(compact[6:])
        date_obj = _safe_date(y, m, d)
        if date_obj:
            return date_obj
            
        # Fallback to MMDDYYYY (US Standard)
        m, d, y = int(compact[:2]), int(compact[2:4]), int(compact[4:])
        return _safe_date(y, m, d)

    return None


def _parse_standard_formats(s: str, now: datetime) -> Optional[datetime]:
    """
    Step 4: Explicit Format Logic.
    Attempts standard Python strptime patterns.
    """
    # Fast path for ISO format
    if _ISO_RE.match(s):
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            pass

    formats = (
        '%m/%d/%Y', '%m-%d-%Y', '%m.%d.%Y',   # US Full
        '%m/%d/%y', '%m-%d-%y',               # US Short Year
        '%d-%b-%Y', '%d %b %Y',               # European Text
        '%B %d %Y', '%b %d %Y',               # US Text
        '%B %d', '%b %d', '%m/%d', '%m-%d'    # No Year
    )

    for fmt in formats:
        try:
            d = datetime.strptime(s, fmt)
            # If format had no year, it defaults to 1900. Reset to current year.
            if d.year == 1900:
                d = d.replace(year=now.year)
            return d
        except ValueError:
            continue
            
    return None


def _parse_flexible_text(s: str, now: datetime) -> Optional[datetime]:
    """
    Step 5: Fuzzy Text Logic.
    Scans for a number (day) and a month name anywhere in the string.
    Example: "the 15th of november", "nov-15"
    """
    s_lower = s.lower()
    
    # Find the Month
    month_num = None
    for name, num in _MONTH_NAMES.items():
        if name in s_lower:
            month_num = num
            break
    if not month_num:
        return None

    # Find the Day (1 or 2 digits)
    day_match = re.search(r'\b(\d{1,2})\b', s_lower)
    if not day_match:
        return None
    day = int(day_match.group(1))

    # Find the Year (4 digits, starting with 19 or 20)
    year_match = re.search(r'\b(19|20)\d{2}\b', s_lower)
    year = int(year_match.group(0)) if year_match else now.year

    return _safe_date(year, month_num, day)


# --- 3. MAIN EXECUTION FUNCTION ---

def standardize_last_filled(last_filled: str) -> str:
    """
    Takes a raw date string, parses it through a waterfall of logic pathways,
    and outputs a standardized MM/DD/YYYY string.
    
    Args:
        last_filled (str): Input date string (e.g., "today", "Novmber 15", "11/15/2024")
        
    Returns:
        str: Date formatted as 'MM/DD/YYYY'
        
    Raises:
        ValueError: If the date cannot be parsed or input is empty.
    """
    if not isinstance(last_filled, str) or not last_filled.strip():
        raise ValueError("Input must be a non-empty string.")

    # 1. Define "Now" once for consistency across all helpers
    now = datetime.now()
    
    # 2. Pre-process string (fix typos, remove ordinals)
    cleaned_str = _clean_input_string(last_filled)

    # 3. Logic Pathways (Waterfall)
    # We check explicitly in order of specificity.
    
    # Path A: Relative ("today", "yesterday", "last friday")
    result = _parse_relative_dates(cleaned_str, now)
    
    # Path B: Compact Numeric ("1115", "20241115")
    if not result:
        result = _parse_compact_numeric(cleaned_str, now)
        
    # Path C: Standard Formats ("11/15/2024", "Nov 15 2024")
    if not result:
        result = _parse_standard_formats(cleaned_str, now)
        
    # Path D: Flexible/Fuzzy ("15th of November")
    if not result:
        result = _parse_flexible_text(cleaned_str, now)

    # 4. Final Output
    if result:
        return result.strftime('%m/%d/%Y')
    
    raise ValueError(f"Unable to parse date: '{last_filled}'")


# --- 4. SCRIPT EXECUTION ---

if __name__ == '__main__':
    # Tests to verify coverage of requirements
    test_cases = [
        "Novmber 15, 2024", "Febuary 29 2024", "today", "yesterday", 
        "last Monday", "2024-11-15", "1115", "11/15/24", 
        "15th of November", "Nov 15"
    ]
    
    print(f"{'INPUT':<20} | {'OUTPUT'}")
    print("-" * 35)
    
    # If command line arg provided, use that. Otherwise run tests.
    if len(sys.argv) > 1:
        try:
            inp = sys.argv[1]
            print(f"{inp:<20} | {standardize_last_filled(inp)}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        for t in test_cases:
            try:
                out = standardize_last_filled(t)
                print(f"{t:<20} | {out}")
            except Exception as e:
                print(f"{t:<20} | ERROR: {e}")