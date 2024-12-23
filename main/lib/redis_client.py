# redis_client.py
import redis
from django.conf import settings

class RedisClient:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            redis_url = settings.REDIS_URL_PROD if not settings.DEBUG else settings.REDIS_URL_DEV
            cls._instance = redis.from_url(
                url=redis_url,
                decode_responses=True
            )
        return cls._instance
