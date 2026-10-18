import re
from datetime import datetime


def provider_timestamp(value):
    if not isinstance(value,str):
        raise ValueError('Provider timestamp required')
    normalized=re.sub(r'([+-]\d{2})(\d{2})$',r'\1:\2',value.replace('Z','+00:00'))
    timestamp=datetime.fromisoformat(normalized)
    if timestamp.tzinfo is None:
        raise ValueError('Provider timezone required')
    return timestamp
