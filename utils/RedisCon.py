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
