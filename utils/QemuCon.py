import libvirt
from functools import wraps
from django.conf import settings


def qemu_connect():
    try:
        conn = libvirt.open(settings.QEMU_URL)
        return None, conn
    except libvirt.libvirtError as e:
        return True, {"error": 1, "message": "{}".format(e)}


def qemu_isalive(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        err, conn = qemu_connect()
        if err:
            return True, {"error": 1, "message": "{}".format(conn)}
        else:
            return func(conn, *args, **kwargs)
    return wrapper
