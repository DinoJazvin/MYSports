import redis

cache = redis.Redis(host='localhost', port=6379, decode_responses=True)
CACHE_TIMEOUT = 43200 # 12 hours

