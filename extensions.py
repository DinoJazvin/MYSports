import redis
from helpers import get_timeout_time

cache = redis.Redis(host='localhost', port=6379, decode_responses=True)
CACHE_TIMEOUT = get_timeout_time()        # 43200 = 12 hours

