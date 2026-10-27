import redis
# from helpers import get_timeout_time

cache = redis.Redis(host='localhost', port=6379, decode_responses=True)
