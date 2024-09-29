import redis,json,subprocess,time
from datetime import datetime
class RedisManager():
    def __init__(self):
        self.port = 6379
        self.host = 'localhost'
        self.db = 0
        self.r = redis.StrictRedis(host=self.host, port=self.port, db=self.db)

    

    def is_redis_running(self):
        try:
            result = subprocess.run(['pgrep', '-x', 'redis-server'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    def set_to_redis_dict(self, key, dictionary):
        """Set a dictionary object to Redis."""
        try:

            value = json.dumps(dictionary)
            self.r.set(key, value)
        except redis.exceptions.ResponseError as e:
            print(f"Error: {e}")
        except TypeError as e:
            print(f"Type Error: {e}")
        
    def get_from_redis_dict(self,key):
        """Get a dictionary object from Redis."""
        try:
            value_type = self.r.type(key)
            if value_type == b'none':
                return {}
            elif value_type == b'string':
                value = self.r.get(key)
                if value:
                    return json.loads(value)
            elif value_type == b'hash':
                pass
            return {}  
        except redis.exceptions.ResponseError as e:
            print(f"Error: {e}")
            return {}
        
    def set_to_redis_list(self, key, value):
        serialized_value = json.dumps(value)
        self.r.set(key, serialized_value)
    
    def get_from_redis_list(self, key):
        serialized_value = self.r.get(key)
        if not serialized_value:
            return {}
        return json.loads(serialized_value)

    def set_to_redis(self,key, value):
        self.r.set(key, json.dumps(value))
        
    def append_to_redis_dict(self,dict_object, key):
        """Directly save a dictionary object to Redis."""
        json_string = json.dumps(dict_object)
        self.r.set(key, json_string)

    

    def append_to_redis_list(self,key, new_value):
        old_value = self.get_from_redis_list(key)
        if new_value not in old_value:
            old_value.append(new_value)
            self.set_to_redis(key, old_value)

    def remove_from_redis_list(self,key, value_to_remove):
        old_value = self.get_from_redis_list(key)
        if value_to_remove in old_value:
            old_value.remove(value_to_remove)
            self.set_to_redis(key, old_value)

    def remove_cache(self,key_prefix, file_path):
        cache_key = f'{key_prefix}:{file_path}'
        self.r.delete(cache_key)
    def update_cache(self,key_prefix, file_path, file_data):
        cache_key = f'{key_prefix}:{file_path}'
        self.r.delete(cache_key)
        success = self.r.set(cache_key, file_data)
        if not success:
            raise Exception(f"Failed to update cache for key: {cache_key}")

    def remove_from_connected_users(self,user_id):
        self.r.hdel('users', user_id)


    def update_redis_channels(self, guild_manager):
        guilds_data = guild_manager.get_all_guilds_data()
        guild_ids = [guild["id"] for guild in guilds_data]
        channels_dict = guild_manager.get_channels(guild_ids)
        for guild_id, channels in channels_dict.items():
            for channel_id, channel_info in channels.items():
                channel_info['is_text_channel'] = channel_info.pop('is_text_channel')

        self.append_to_redis_dict(channels_dict, 'all_guild_channels')



    def update_redis_guilds(self,guild_manager):
        self.append_to_redis_dict(guild_manager.get_all_guilds(),'guilds_cache')
        
        
    def update_sid_timestamp(self,user_id, sid):
        timestamp = int(time.time())
        self.r.hset('sid_timestamps', f"{user_id}:{sid}", timestamp)
    def delete_sid_timestamps(self, user_id, sid):
        self.r.hdel('sid_timestamps', f"{user_id}:{sid}")
        
    def get_sids_raw(self,user_id):
        users_dict_bytes = self.r.hgetall('users')
        users_dict = {key.decode('utf-8'): json.loads(value.decode('utf-8')) for key, value in users_dict_bytes.items()}
        user_sids = users_dict.get(user_id, {}).get('sids', [])
        return user_sids
    
    def get_sids(self,user_id,users_manager):
        self.cleanup_stale_sids(users_manager)
        return self.get_sids_raw(user_id)


        
        
    def add_user_with_sid(self,user_id, request_sid, user_sid):
        if not self.r.exists('users'):  
            self.r.hset('users', user_id, json.dumps({'details': user_sid, 'sids': [request_sid]}))
        else:
            current_sids = self.r.hget('users', user_id)
            if current_sids:
                current_sids = json.loads(current_sids)
                if request_sid not in current_sids['sids']:
                    current_sids['sids'].append(request_sid)
                    self.r.hset('users', user_id, json.dumps(current_sids))
            else:
                self.r.hset('users', user_id, json.dumps({'details': user_sid, 'sids': [request_sid]}))

    def remove_user_sid(self, user_id, request_sid):
        user_id = str(user_id)
        request_sid = str(request_sid)
        
        current_sids = self.r.hget('users', user_id)
        if current_sids:
            current_sids = json.loads(current_sids)
            if request_sid in current_sids.get('sids', []):
                current_sids['sids'].remove(request_sid)
                self.r.hset('users', user_id, json.dumps(current_sids))
                self.delete_sid_timestamps(user_id, request_sid)


    def get_redis_users_raw(self):
        users_dict_bytes = self.r.hgetall('users')
        users_dict = {key.decode('utf-8'): json.loads(value.decode('utf-8')) for key, value in users_dict_bytes.items()}
        return users_dict
        
    def get_redis_users(self,users_manager):
        self.cleanup_stale_sids(users_manager)
        return self.get_redis_users_raw()
    
    def get_all_sids_timestamps(self):
        sid_timestamps = self.r.hgetall('sid_timestamps')
        return {k.decode('utf-8'): datetime.fromtimestamp(int(v.decode('utf-8'))).strftime('%Y-%m-%d %H:%M:%S') for k, v in sid_timestamps.items()}
    def cleanup_stale_sids(self,users_manager):
        current_time = int(time.time())
        DISCONNECT_THRESHOLD = 30

        users_dict = self.get_redis_users_raw()

        for user_id, user_data in users_dict.items():
            sids = user_data.get('sids', [])
            for sid in sids:
                timestamp = self.r.hget('sid_timestamps', f"{user_id}:{sid}")
                if timestamp:
                    timestamp = int(timestamp)
                    if current_time - timestamp > DISCONNECT_THRESHOLD:
                        self.remove_user_sid(user_id, sid)

        for user_id in users_dict:
            if len(self.get_sids_raw(user_id)) == 0:
                self.r.hdel('users', user_id)
                users_manager.db_update_user_last_login(user_id)
                self.remove_from_connected_users(user_id)



    def get_online_users(self, users_manager):
        result = self.get_redis_users(users_manager)
        return list(result.keys()) if result else []

                
    def get_channels_generic(self, guild_id, last_read_datetimes):
        temp_guilds_channels = self.get_from_redis_dict('all_guild_channels')
        
        if not temp_guilds_channels : return []
        
        if guild_id not in temp_guilds_channels:return []
        
        channels_data = temp_guilds_channels[guild_id]
        
        channels_list = []
        for channel_id, channel_info in channels_data.items():
            channel_name = channel_info.get('name')
            is_text_channel = channel_info.get('is_text_channel')
            
            channels_list.append({
                "channel_id": channel_id,
                "channel_name": channel_name,
                "last_read_datetime": last_read_datetimes.get(channel_id),
                'is_text_channel': is_text_channel
            })
        
        return json.dumps(channels_list) if channels_list else []

    def clear_redis_cache(self):
        """
        Connect to Redis and clear the cache.
        """
        try:
            self.r = redis.StrictRedis(host=self.host, port=self.port, db=self.db)
            self.r.flushdb()
            
            print("Cleared redis cache!")
        except Exception as e:
            print(f"Error clearing Redis cache: {e}")


redis_manager = RedisManager()

if __name__ == '__main__':
    redis_manager.clear_redis_cache()