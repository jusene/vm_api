import libvirt
from functools import wraps
from utils.RedisCon import get_host


def qemu_connect(host=None):
    if host is None:
        try:
            err, host = get_host()
            assert err is None, "GET HOST ERROR"
            conn = libvirt.open('qemu+tcp://{}:16509/system'.format(host))
            return None, conn
        except libvirt.libvirtError as e:
            return True, {"error": 1, "message": "{}".format(e)}
    else:
        try:
            conn = libvirt.open('qemu+tcp://{}:16509/system'.format(host))
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
