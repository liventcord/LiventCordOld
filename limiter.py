from functools import wraps
from flask import make_response, session
import time
from datetime import timedelta
isRateLimiting = False
class Limiter:
    def __init__(self, redis_manager):
        self.redis_manager = redis_manager

    def limit(self, requests_per_minute):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                user_id = self.get_user_id_from_session()
                if not user_id:
                    print("NO USER ID!")
                    return
                if isRateLimiting:
                    current_time = time.time()  
                    key = f"request_count:{user_id}:{func.__name__}"
                    count = self.redis_manager.r.get(key)
                    # Ensure count is an integer, defaulting to 0 if it's None or not convertible to int
                    try:
                        count = int(count) if count is not None else 0
                    except (TypeError, ValueError):
                        count = 0
                    last_request_time = self.redis_manager.r.get(f"last_request_time:{user_id}:{func.__name__}")
                    if last_request_time is not None:
                        last_request_time = float(last_request_time)
                        if current_time - 60 > last_request_time: 
                            count = 1
                            self.redis_manager.r.set(f"last_request_time:{user_id}:{func.__name__}", current_time)
                        else:
                            count += 1
                    else:
                        count = 1
                        self.redis_manager.r.set(f"last_request_time:{user_id}:{func.__name__}", current_time)
                    self.redis_manager.r.setex(key, timedelta(minutes=1), str(count))  
                    if count > requests_per_minute:
                        remaining_time = int(60 - (current_time - last_request_time))
                        return make_response(f'{remaining_time} saniye içerisinde tekrar deneyin', 429)
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(e)
            return wrapper
        return decorator

    def get_user_id_from_session(self):
        return session.get('user_id')
