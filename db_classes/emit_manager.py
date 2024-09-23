from flask import session
from flask_socketio import emit



class EmitManager():

    def __init__(self,users_manager,guild_manager,friends_manager,redis_manager,socketio):


        self.guild_manager = guild_manager

        self.users_manager = users_manager

        self.friends_manager = friends_manager


        self.redis_manager = redis_manager


        self.socketio = socketio
        

    def emit_to_guild(self,guild_id,event_name,payload):

        users_dict = self.redis_manager.get_redis_users(self.users_manager)

        users = self.guild_manager.get_guilds_users_base(guild_id)
        if not users : return

        for _id, details in users_dict.items():
            if _id in users:
                for sid in details["sids"]:
                    self.socketio.emit(event_name,payload,to=sid)

    def emit_guild_name_to_guild(self,guild_id,new_name):

        self.emit_to_guild(guild_id,'update_guild_name',new_name)
        




    def emit_guild_image_to_guild(self,is_empty,guild_id):
        self.emit_to_guild(guild_id,'update_guild_image',{'guild_id': guild_id, 'is_empty' : is_empty})



    def emit_user_list_to_guild(self,guild_id):
        users = self.guild_manager.get_guilds_users(guild_id,self.users_manager)
        self.emit_to_guild(guild_id,'update_guild_users',users)
        
        


    def emit_deleted_message_to_friend_self(self,user_id,friend_id,message_id):                

        users_dict = self.get_redis_users()

        if not users_dict : return

        payload_to_user = {'is_dm' : True, 'message_id': message_id, 'channel_id': friend_id}

        payload_to_friend = {'is_dm' : True, 'message_id': message_id, 'channel_id': user_id}


        for _id, details in users_dict.items():

            if _id == friend_id:

                for sid in details["sids"]:

                    self.socketio.emit('deletion_message', payload_to_friend , to=sid)


            elif _id == user_id:

                for sid in details["sids"]:

                    self.socketio.emit('deletion_message', payload_to_user , to=sid)
                    

    def emit_deleted_message_to_guild(self,guild_id, message_id, channel_id):

        payload = {'is_dm' : False,'guild_id': guild_id, 'message_id': message_id, 'channel_id': channel_id}

        self.emit_to_guild(guild_id,'deletion_message',payload)

    def get_redis_users(self):
        return self.redis_manager.get_redis_users(self.users_manager)



    def emit_to_friend_and_self(self, user_id, friend_id, event_name, payload):

        users_dict = self.get_redis_users()

        if not users_dict : return


        for _id, details in users_dict.items():

            if _id == friend_id or _id == user_id:
                for sid in details["sids"]:

                    self.socketio.emit(event_name, payload , to=sid)



    def emit_to_friends(self,user_id,event_name,payload):
        users_dict = self.get_redis_users()

        if not users_dict : return

        friends_ids = self.friends_manager.find_all_friends_ids(user_id)
        if not friends_ids: return
        
        for _id, details in users_dict.items():

            if _id in friends_ids or _id == user_id:

                for sid in details["sids"]:

                    self.socketio.emit(event_name, payload , to=sid)


    def emit_to_friends_and_guild(self,user_id,event_name,payload):

        users_dict = self.get_redis_users()

        if not users_dict: return 

        friends_ids = set(self.friends_manager.find_all_friends_ids(user_id))

        users_guild_ids = set(self.guild_manager.get_users_guilds_ids(user_id))

        guild_user_ids = set()

        for guild_id in users_guild_ids:
            guild_user_ids.update(self.guild_manager.get_guilds_users_base(guild_id))

        targets = friends_ids | guild_user_ids | {user_id}

        for _id, details in users_dict.items():
            if _id in targets:
                for sid in details["sids"]:
                    self.socketio.emit(event_name, payload, to=sid)
                    

    def emit_user_activity(self,user_id, is_online):

        data = {'user_id' : user_id, 'is_online' : is_online}
        self.emit_to_friends_and_guild(user_id,'user_status',data)
        


    def emit_nick_to_friends(self,user_id, user_name=None):
        data = {'user_id': user_id, 'user_name': user_name}

        self.emit_to_friends(user_id,'update_nick',data)


    def emit_profile_to_guild_and_friends(self,user_id):
        data = {'user_id': user_id}

        self.emit_to_friends_and_guild(user_id,'update_user_profile',data)

    def emit_guilds(self,user_id):

        users_guilds = self.guild_manager.get_users_guilds_data(user_id)

        if not users_guilds: return

        self.emit_to_originator(user_id,'update_guilds',users_guilds)

    def emit_to_originator(self,user_id,event_name,payload):

        users_dict = self.get_redis_users()
        for _id, details in users_dict.items(): 

            if _id == user_id:
                for sid in details["sids"]:
                    self.socketio.emit(event_name,payload,to=sid)
                   

    def emit_user_list(self,client_sid, guild_id):

        user_id = self.get_user_id_from_session()
        if user_id:
            users = self.guild_manager.get_guilds_users(guild_id,self.users_manager)
            if users:
                emit('update_users', {'users' : users, 'guild_id': guild_id}, to=client_sid )

    def get_user_id_from_session(self):
        return session.get('user_id')
    







