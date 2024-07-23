from datetime import datetime
from django.utils import timezone
from calendar import timegm

def get_first_matching_attr(obj, *attrs, default=None):
    for attr in attrs:
        if hasattr(obj, attr):
            return getattr(obj, attr)

    return default


def get_error_message(exc) -> str:
    if hasattr(exc, 'message_dict'):
        return exc.message_dict
    error_msg = get_first_matching_attr(exc, 'message', 'messages')

    if isinstance(error_msg, list):
        error_msg = ', '.join(error_msg)

    if error_msg is None:
        error_msg = str(exc)

    return error_msg

def get_now() -> datetime:
    return timezone.now()

def unix_epoch(datetime_object=None):
    """Get unix epoch from datetime object."""

    if not datetime_object:
        datetime_object = datetime.utcnow()
    return timegm(datetime_object.utctimetuple())

