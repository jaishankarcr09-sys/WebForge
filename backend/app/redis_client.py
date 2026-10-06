import redis
from .config import settings

client = redis.from_url(settings.redis_url, decode_responses=True)

def ping() -> bool:
    try:
        return bool(client.ping())
    except redis.RedisError:
        return False
