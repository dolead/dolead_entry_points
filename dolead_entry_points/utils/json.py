import types
import enum
import uuid
from typing import Counter

from decimal import Decimal

DECIMALS = (Decimal,)
try:
    from _decimal import Decimal as _decimal
    DECIMALS = (_decimal, *DECIMALS)
except ImportError:
    pass
try:
    from _pydecimal import Decimal as _pydecimal
    DECIMALS = (_pydecimal, *DECIMALS)
except ImportError:
    pass

def default_handler(obj):
    """JSON handler for default query formatting"""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if hasattr(obj, 'dump'):
        return obj.dump()
    if isinstance(obj, (set, frozenset, types.GeneratorType)):
        return list(obj)
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, DECIMALS):
        return float(obj)
    if isinstance(obj, Counter):
        return dict(obj)
    raise TypeError("Object of type %s with value of %s "
            "is not JSON serializable" % (type(obj), repr(obj)))
