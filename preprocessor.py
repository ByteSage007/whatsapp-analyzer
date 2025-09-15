import re
from datetime import datetime
import pandas as pd

TIMESTAMP_REGEX = re.compile(
    r"^(\d{1,4}[/-]\d{1,2}[/-]\d{1,4}),\s(\d{1,2}:\d{2})(?:\s?(AM|PM|am|pm))?\s-\s"
)

AUTHOR_MESSAGE_PATTERN = re.compile(r"^([^:]+):\s(.*)")


def try_parse_datetime(date_str: str, time_str: str, ampm: str = None):
    ampm = (ampm or '').strip()
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", date_str):
        candidates = ["%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M"]
    else:
        candidates = [
            "%d/%m/%Y %I:%M %p", "%d/%m/%Y %H:%M",
            "%d/%m/%y %I:%M %p", "%d/%m/%y %H:%M"
        ]
    for fmt in candidates:
        try:
            if "%p" in fmt and not ampm:
                continue
            if "%p" in fmt:
                return datetime.strptime(f"{date_str} {time_str} {ampm}", fmt)
            return datetime.strptime(f"{date_str} {time_str}", fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(f"{date_str} {time_str}")
    except Exception:
        return None


def preprocess(raw_text: str) -> pd.DataFrame:
    raw_text = raw_text.replace('\r\n', '\n').replace('\r', '\n')
    lines = raw_text.split('\n')
    parsed, buffer = [], None
    for line in lines:
        if not line.strip():
            if buffer is not None:
                buffer['message'] += '\n'
            continue
        m = TIMESTAMP_REGEX.match(line)
        if m:
            date_str, time_str, ampm = m.group(1), m.group(2), m.group(3)
            content = line[m.end():]
            if buffer is not None:
                parsed.append(buffer)
            am = AUTHOR_MESSAGE_PATTERN.match(content)
            if am:
                user, message = am.group(1).strip(), am.group(2).strip()
            else:
                user, message = 'system', content.strip()
            dt = try_parse_datetime(date_str, time_str, ampm)
            buffer = {
                'datetime': dt if dt else pd.NaT,
                'date': dt.date() if dt else None,
                'time': dt.time() if dt else None,
                'user': user,
                'message': message,
            }
        else:
            if buffer is None:
                parsed.append({
                    'datetime': pd.NaT,
                    'date': None,
                    'time': None,
                    'user': 'system',
                    'message': line
                })
            else:
                buffer['message'] += '\n' + line
    if buffer is not None:
        parsed.append(buffer)
    df = pd.DataFrame(parsed)
    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    expected_cols = ['datetime', 'date', 'time', 'user', 'message']
    for c in expected_cols:
        if c not in df.columns:
            df[c] = None
    return df[expected_cols]