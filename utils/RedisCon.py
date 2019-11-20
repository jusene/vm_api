import redis
from django.conf import settings


def rdscon():
    try:
        rds = redis.Redis(host=settings.REDIS.get('HOST'),
                          port=settings.REDIS.get('PORT'),
                          db=settings.REDIS.get('DB'),
                          password=settings.REDIS.get('PASSWORD'))
        return None, rds
    except Exception as e:
        return True, e


def get_host(host=None):
    if host is None:
        err, rds = rdscon()
        try:
            assert err is None, 'REDIS CONNECT ERROR'
            host = rds.get("host::ip").decode()
            return None, host
        except Exception as e:
            return True, e
    else:
        return None, host