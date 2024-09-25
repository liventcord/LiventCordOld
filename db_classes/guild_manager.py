from db_classes.db_main_class import DatabaseManager,create_messages_query
import sqlite3,json,os
from pytz import utc as UTC
from utils.utils import create_random_id,DATABASE_PATH ,construct_guild_path,construct_guild_image_path,pack_user_info,create_random_string,logger
from redis_handler import redis_manager
from datetime import datetime
from enum import Enum

class Permission(Enum):
    read_messages = 'read_messages'
    send_messages = 'send_messages'
    manage_roles = 'manage_roles'
    kick_members = 'kick_members'
    ban_members = 'ban_members'
    manage_channels = 'manage_channels'
    mention_everyone = 'mention_everyone'
    add_reaction = 'add_reaction'
    is_admin = 'is_admin'
    can_invite = 'can_invite'

class GuildManager(DatabaseManager):

    def __init__(self):
        database_path = 'guilds.db'
        super().__init__(database_path)
        self.database_path = DATABASE_PATH + database_path
        

        
    def get_owner_id(self,guild_id):
        result = self.fetch_single('SELECT owner_id FROM guilds WHERE guild_id=?',(guild_id,))
        return result[0] if result else None
    
    def can_user_delete_guild(self,user_id,guild_id):
        author_id = self.get_owner_id(guild_id)
        return author_id == user_id
    
    def can_user_invite(self,user_id,guild_id):
        if self.is_user_author(guild_id, user_id): return True
        return self.check_user_permission(guild_id,user_id,Permission.can_invite)
    
    def can_user_upload_guild_image(self,guild_id,user_id):
        if self.is_user_author(guild_id, user_id): return True
        return self.check_user_permission(guild_id,user_id,Permission.is_admin)
    
    def can_user_manage_channel(self,user_id,guild_id):
        if self.is_user_author(guild_id, user_id): return True
        return self.check_user_permission(guild_id,user_id,Permission.manage_channels)
    
    
    def is_user_author(self,guild_id,user_id):
        if not guild_id or not user_id: return False
        return self.get_owner_id(guild_id) == user_id
        
    def does_guild_exists(self,guild_id):
        return self.fetch_single('SELECT guild_id FROM guilds WHERE guild_id = ? ',(guild_id,))
        
   
        
    def resolve_guild_name(self,guild_id):
        result = self.fetch_single("SELECT guild_name FROM guilds WHERE guild_id=?", (guild_id,))
        return result[0] if result else None
    
    def check_guild_channel_existence(self, guild_id, channel_id):
        query = "SELECT channel_name FROM channels WHERE guild_id=? AND channel_id=?"
        result = self.fetch_single(query,(guild_id,channel_id))
        return result is not None

    def create_invite(self, creator_id,guild_id,channel_id):
    
        group_id = self.get_or_create_group(creator_id, guild_id, channel_id)
        invite_id = create_random_string()
        self.execute_query("""
            INSERT INTO invites (invite_id, group_id)
            VALUES (?, ?)
        """, invite_id, group_id)
        logger.info(f"Invite {invite_id} created successfully for group {group_id}.")
        return invite_id
        
        
    def get_or_create_group(self,creator_id: str, guild_id: str, channel_id: str) -> str:
        row = self.fetch_single("""
            SELECT group_id FROM invite_groups 
            WHERE creator_id = ? AND guild_id = ? AND channel_id = ?
        """, (creator_id, guild_id, channel_id))
        if row:
            group_id = row[0]
        else:
            # Create a new group
            group_id = create_random_id()
            self.execute_query("""
                INSERT INTO invite_groups (group_id, creator_id, guild_id, channel_id)
                VALUES (?, ?, ?, ?)
            """, group_id, creator_id, guild_id, channel_id)
        return group_id

    def get_invite_ids(self, guild_id: str):
        invite_ids = self.fetch_multiple("""
            SELECT i.invite_id
            FROM invites i
            JOIN invite_groups g ON i.group_id = g.group_id
            WHERE g.guild_id = ?
        """, (guild_id,))
        return invite_ids




        
    def get_invite_details(self,invite_id: str) :

        row = self.fetch_single("""
            SELECT 
                i.invite_id, 
                i.group_id, 
                g.creator_id, 
                g.guild_id, 
                g.channel_id 
            FROM invites i
            JOIN invite_groups g ON i.group_id = g.group_id
            WHERE i.invite_id = ?
        """,(invite_id,))
        if row:
            invite_details = {
                "invite_id": row[0],
                "group_id": row[1],
                "creator_id": row[2],
                "guild_id": row[3],
                "channel_id": row[4]
            }
            return invite_details
        else:
            return None

    def extract_id(self,input_str):
        # Check if the input_str is a URL (contains "http://" or "https://")
        if input_str.startswith("http://") or input_str.startswith("https://"):
            # Split by '/' and get the last element, which should be the ID
            parts = input_str.split('/')
            return parts[-1]
        else:
            # If not a URL, directly return the input_str as it should be the ID
            return input_str
    
    def get_invites_guild_and_channel(self, invite_id):
        invite_id = self.extract_id(invite_id)
        details = self.get_invite_details(invite_id)
        if details:
            guild_id = details.get("guild_id")
            channel_id = details.get("channel_id")
            if guild_id and channel_id:
                return guild_id, channel_id
        return None, None
           
        
        
    def update_guild_name(self,new_name,guild_id):
        self.execute_query('UPDATE guilds SET guild_name=? WHERE guild_id=?',new_name,guild_id),
        


    def get_users_count(self,guild_id):
        users_ids_str = self.fetch_single('''SELECT users FROM guilds WHERE guild_id = ?''', (guild_id,))[0]
        if not users_ids_str: return 0
        return len(json.loads(users_ids_str))
        
        
    def resolve_channel_name(self, channel_id):
        result = self.fetch_single("SELECT channel_name FROM channels WHERE channel_id=?", (channel_id,))
        return result[0] if result else None

    def create_channel(self, guild_id,user_id, channel_name,is_text_channel,channel_id=None):
        try:
            if not channel_id:
                channel_id = create_random_id()
            typech = 'text' if is_text_channel else 'voice'
            self.execute_query("INSERT INTO channels (channel_id, guild_id, channel_name,is_text_channel) VALUES (?, ?, ?, ?)",
                                channel_id, guild_id, channel_name,is_text_channel)
            
            msg = f'User {user_id}  created {typech} channel {channel_id} on guild {guild_id}'
            logger.info(msg)
            return channel_id
        except Exception as e:
            logger.exception(e)
    
    def edit_channel(self, guild_id,new_channel_name,channel_id):
        self.execute_query("UPDATE channels SET channel_name=? WHERE channel_id=? WHERE guild_id=?", new_channel_name, channel_id,guild_id)

        
    def is_channels_low(self, guild_id):
        channelscount = self.get_channels_single_guild(guild_id)
        return True if not channelscount else len(channelscount) <= 1
        

    def get_channels_single_guild(self, guild_id):
        query = """
            SELECT guild_id, channel_id, channel_name, is_text_channel
            FROM channels
            WHERE guild_id = ?
        """
        results = self.fetch_single(query, (guild_id,))
        return results


    def get_channels(self, guild_ids):
        if len(guild_ids) == 1:
            guild_ids_tuple = (guild_ids[0],)
        else:
            guild_ids_tuple = tuple(guild_ids)
        query = """
            SELECT guild_id, channel_id, channel_name, is_text_channel
            FROM channels
            WHERE guild_id IN ({})
        """.format(','.join(['?'] * len(guild_ids_tuple)))

        results = self.fetch_multiple(query, (guild_ids_tuple))

        channels_dict = {}
        for guild_id, channel_id, channel_name, is_text_channel in results:
            if guild_id not in channels_dict:
                channels_dict[guild_id] = {}
            channels_dict[guild_id][channel_id] = {
                'name': channel_name,
                'is_text_channel': is_text_channel
            }
            
        return channels_dict



    def remove_channel(self, guild_id,channel_id):
        self.execute_query("DELETE FROM channels WHERE guild_id=? AND channel_id=?", guild_id,channel_id)
 

    def get_guilds_users_base(self, guild_id) -> dict:
        users_ids_tuple = self.fetch_single("SELECT users FROM guilds WHERE guild_id = ?", (guild_id,))
        if not users_ids_tuple or not users_ids_tuple[0]: return []  
        str_data = users_ids_tuple[0]
        users_ids_list = json.loads(str_data)
        return users_ids_list
        
    
    def get_guilds_users(self, guild_id, users_manager):
        users_ids_str = self.fetch_single("SELECT users FROM guilds WHERE guild_id = ?", (guild_id,))
        if not users_ids_str:
            return {}
        
        users_ids = json.loads(users_ids_str[0])
        
        user_data = users_manager.get_users_status(users_ids)
        if not user_data: return {}

        online_users = redis_manager.get_online_users(users_manager)
        users_info = {}
        for user in user_data:
            try:
                if user:
                    user_id = user[0]
                    hide_profile = user[10]
                    is_online = user_id in online_users

                    user_info = pack_user_info(hide_profile, is_online, user)
                    users_info.update(user_info)
            except Exception as e:
                logger.exception(f"Error processing user data: {e}")
        return users_info

        
            
    def update_guild_image_boolean(self, guild_id, boolean):
        self.execute_query('UPDATE guilds SET is_guild_uploaded_img=? WHERE guild_id=?', boolean, guild_id)

    def get_guild_image_path(self,is_guild_uploaded_img,guild_id):
        return construct_guild_image_path(guild_id) if is_guild_uploaded_img else 'black'
    def pack_guild(self, guild_rows,is_packing_multiple=False):
        guild_data = []
        if not guild_rows: return []
        if is_packing_multiple:
            for guild_id, guild_name, users_json, channels_json, is_guild_uploaded_img in guild_rows:
                channels = json.loads(channels_json)
                channels_dict = {channel['channel_id']: channel['channel_name'] for channel in channels}
                first_channel_id = next(iter(channels_dict.keys()), None)
                guild_info = {
                    "src": self.get_guild_image_path(is_guild_uploaded_img,  guild_id),
                    "name": guild_name,
                    "id": guild_id,
                    "channels": channels_dict,
                    'first_channel_id' : first_channel_id
                }
                guild_data.append(guild_info)
        else:
            for guild in guild_rows:
                guild_id, guild_name, channels,is_guild_uploaded_img,owner_id,root_channel = guild
                first_channel_id = next(iter(channels.keys()), None)
                guild_info = {
                    "src": self.get_guild_image_path(is_guild_uploaded_img, guild_id),
                    "name": guild_name,
                    "id": guild_id,
                    "channels": channels,
                    'owner_id' : owner_id,
                    'root_channel' : root_channel,
                    'first_channel_id' : first_channel_id
                }
                guild_data.append(guild_info)
        return guild_data
    
    def get_users_guilds_data(self,user_id):
        users_guild_rows = self.get_users_guilds(user_id)
        return self.pack_guild(users_guild_rows)
    
    def get_all_guilds_data(self):
        all_guilds_rows = self.get_all_guilds()
        return self.pack_guild(all_guilds_rows,is_packing_multiple=True)

        



    def create_message_table(self,db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(create_messages_query)
        conn.commit()
        conn.close()
        
        
    def did_guild_upload_image(self, guild_id):
        result = self.fetch_single("SELECT CASE WHEN is_guild_uploaded_img = 1 THEN 1 ELSE 0 END AS is_uploaded FROM guilds WHERE guild_id = ?", (guild_id,))
        if not result: return False
        return result[0] == 1

        
    def create_guild(self, guild_name, creator_id,guild_id,is_guild_uploaded_img,users_manager):  
        if not guild_name or not creator_id or not users_manager:
            logger.warning(f"not guild_name {guild_name} or not creator_user_id {creator_id} or not guild_id {guild_id}")
            return
        users = [creator_id]
        users_json = json.dumps(users)
        region = 'Empty'
        setting = 'Empty'
        setting_json = json.dumps(setting)
        try:
            if self.does_guild_exists(guild_id): return 
            
            self.execute_query("INSERT INTO guilds (guild_id, owner_id, guild_name, users, created_at, region, settings,is_guild_uploaded_img) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            guild_id, creator_id, guild_name, users_json, datetime.now(UTC), region, setting_json,is_guild_uploaded_img)
            new_channel_id = self.create_channel(guild_id,creator_id,'genel',True)
            self.create_invite(creator_id,guild_id,new_channel_id)
            
            redis_manager.update_redis_channels(self)
            self.create_message_table(construct_guild_path(guild_id))
            permissions_dict = {
                'read_messages': True,
                'send_messages': True,
                'manage_roles': True,
                'kick_members': True,
                'ban_members': True,
                'manage_channels': True,
                'mention_everyone': True,
                'add_reaction': True,
                'is_admin': True,
                'can_invite': True
            }
                
            self.update_guild_permissions(guild_id, users_manager, permissions_dict, creator_id)
            logger.info(f"User {creator_id} created new guild {guild_id}")
            return new_channel_id

        except Exception as e:
            logger.exception(e)

            
    def delete_guild(self, guild_id):
        try:
            if not self.does_guild_exists(guild_id): 
                logger.warning("Guild ID Does not exists. Cant delete")
                return
            self.execute_query("DELETE FROM guilds WHERE guild_id=?",guild_id)
            self.execute_query("DELETE FROM permissions WHERE guild_id=?",guild_id)
            logger.warning("Guild removed successfully.")
        except sqlite3.Error as e:
            logger.warning("Error occurred:", e)
            
    def get_permissions_map(self, user_id):
        guild_ids = self.get_users_guilds_ids(user_id)
        perms = {}
        for guild_id in guild_ids:
            permissions = self.fetch_permissions_for_guild(user_id, guild_id)
            perms[guild_id] = {perm.value: has_perm for perm, has_perm in permissions.items()}
        return json.dumps(perms, default=str)
    
    def fetch_permissions_for_guild(self, user_id, guild_id):
        permissions = {}
        query = 'SELECT {} FROM permissions WHERE guild_id = ? AND user_id = ?'.format(
            ', '.join(perm.value for perm in Permission)
        )
        result = self.fetch_single(query, (guild_id, user_id))
        if result:
            permissions = dict(zip(Permission, result))
        else:
            permissions = {perm: 0 for perm in Permission}
        return permissions
        
    def check_user_permission(self, guild_id, user_id, permission_type):
        query = 'SELECT {} FROM permissions WHERE guild_id = ? AND user_id = ?'.format(permission_type.value)
        permission = self.fetch_single(query, (guild_id, user_id))
        return permission[0] if permission else 0
    
    def give_permission_to_user(self, user_id, guild_id, permissions):
        if not self.does_guild_exists(guild_id):
            logger.info(f"Guild {guild_id} does not exist")
            return
        
        existing_permission = self.fetch_single(
            'SELECT * FROM permissions WHERE guild_id = ? AND user_id = ?', (guild_id, user_id)
        )
        
        permission_keys = list(Permission.__members__.keys())

        if existing_permission:
            logger.info(f"Updating permissions for user {user_id} on guild {guild_id}")
            update_query = 'UPDATE permissions SET {} WHERE guild_id = ? AND user_id = ?'.format(
                ', '.join('{} = ?'.format(perm) for perm in permission_keys)
            )
            update_values = [permissions.get(perm, existing_permission[i+2]) for i, perm in enumerate(permission_keys)]
            self.execute_query(update_query, *update_values, guild_id, user_id)
        else:
            logger.info(f"Inserting permissions for user {user_id} on guild {guild_id}")
            columns = ', '.join(['guild_id', 'user_id'] + permission_keys)
            placeholders = ', '.join(['?'] * (2 + len(permission_keys)))
            insert_query = f'INSERT INTO permissions ({columns}) VALUES ({placeholders})'
            insert_values = [permissions.get(perm, 0) for perm in permission_keys]
            self.execute_query(insert_query, guild_id, user_id, *insert_values)

        return True


    def update_guild_permissions(self, guild_id, users_manager, permissions=None, user_id_to_update=None):
        if not self.does_guild_exists(guild_id):
            logger.info(f"Guild {guild_id} does not exist")
            return
        if permissions is None:
            logger.info(f"Updating permissions for Guild {guild_id}, but provided permissions do not exist")
            return

        users = self.get_guilds_users(guild_id, users_manager)
        logger.info(f"Processing users: {users}")

        for user_id in users:
            logger.info(f"Currently at user {user_id}")
            if user_id_to_update is None or user_id == user_id_to_update:
                logger.info("Checking if permission exists...")
                existing_permission = self.fetch_single(
                    'SELECT * FROM permissions WHERE guild_id = ? AND user_id = ?', (guild_id, user_id)
                )

                if existing_permission:
                    logger.info("Permission exists!")
                    update_query = 'UPDATE permissions SET {} WHERE guild_id = ? AND user_id = ?'.format(
                        ', '.join('{} = ?'.format(perm.value) for perm in Permission)
                    )
                    self.execute_query(update_query, *(permissions.get(perm.value, existing_permission[perm]) for perm in Permission), guild_id, user_id)
                else:
                    logger.info("Permission does not exist. Inserting into.")
                    columns = ', '.join(['guild_id', 'user_id'] + [perm.value for perm in Permission])
                    placeholders = ', '.join(['?'] * (2 + len(Permission)))
                    insert_query = f'INSERT INTO permissions ({columns}) VALUES ({placeholders})'
                    values = [permissions.get(perm.value, 0) for perm in Permission]
                    self.execute_query(insert_query, guild_id, user_id, *values)

        return True




    def check_users_guild(self, guild_id, user_id):
        query = "SELECT users FROM guilds WHERE guild_id = ?"
        result = self.fetch_multiple(query, (guild_id,))
        
        if not result or not result[0]:
            logger.warning(f"No users found for guild_id {guild_id}")
            return False
        
        users_data = result[0][0]
        
        if not users_data:
            logger.error(f"Empty users data found for guild_id {guild_id}")
            return False
        
        try:
            users_list = json.loads(users_data)
            
            if not isinstance(users_list, list):
                logger.error(f"Invalid users_list format for guild_id {guild_id}")
                return False
            
            return user_id in users_list
        except (json.JSONDecodeError, TypeError) as e:
            logger.exception(f"Error processing users data for guild_id {guild_id}: {e}")
            return False


        
    def get_all_guilds(self):
        query = """
        SELECT s.guild_id, s.guild_name, s.users, 
            JSON_GROUP_ARRAY(JSON_OBJECT('channel_id', c.channel_id, 'channel_name', c.channel_name)) AS channels_json,
            s.is_guild_uploaded_img
        FROM guilds s
        LEFT JOIN channels c ON s.guild_id = c.guild_id
        GROUP BY s.guild_id
        """
        all_guild = self.fetch_multiple(query)
                
        output_list = [
            (guild_id, guild_name, users_json, channels_json, is_guild_uploaded_img)
            for guild_id, guild_name, users_json, channels_json, is_guild_uploaded_img in all_guild
        ]

        return output_list
            
        
    def get_users_metadata(self, guild_id, users_manager):
        users_ids_str = self.fetch_single('''SELECT users FROM guilds WHERE guild_id = ?''', (guild_id,))[0]
        if not users_ids_str:
            return {}
        try:
            users_ids = json.loads(users_ids_str)
        except json.JSONDecodeError as e:
            logger.exception(f"Error decoding JSON: {e}")
            return {}
        user_data = users_manager.db_get_users_id_nick_discriminator(users_ids)
        if not user_data: return {}
        users_info = {}
        for user in user_data:
            try:
                user_id, nick,discriminator = user
                users_info[user_id] = [nick,discriminator]
            except Exception as e:
                logger.exception(f"Error processing user data: {e}")
        return users_info
    
    def get_users_guilds_ids(self, user_id):
        query = """
                SELECT s.guild_id
                FROM guilds s
                WHERE s.users LIKE ?
            """
        result = self.fetch_multiple(query,(f'%{user_id}%',))
        if not result: return []
        return [str(guild_id[0]) for guild_id in result]
        
    def get_users_guilds(self, user_id):
        try:
            query = """
                SELECT s.guild_id, s.guild_name, c.channel_id, c.channel_name, s.is_guild_uploaded_img, s.owner_id, s.root_channel
                FROM guilds s 
                JOIN channels c ON s.guild_id = c.guild_id 
                WHERE s.users LIKE ?
            """
            rows = self.fetch_multiple(query, (f'%{user_id}%',))
            guilds_dict = {}
            for row in rows:
                guild_id = row[0]
                guild_name = row[1]
                channel_id = row[2]
                channel_name = row[3]
                is_guild_uploaded_img = row[4]
                owner_id = row[5]
                root_channel = row[6]
                
                if guild_id not in guilds_dict:
                    guilds_dict[guild_id] = {
                        'guild_id': guild_id,
                        'guild_name': guild_name,
                        'channels': {},
                        'is_guild_uploaded_img' : is_guild_uploaded_img,
                        'owner_id' : owner_id,
                        'root_channel' : root_channel
                    }
                guilds_dict[guild_id]['channels'][channel_id] = channel_name
            
            result = []
            for guild in guilds_dict.values():
                result.append((guild['guild_id'], guild['guild_name'], guild['channels'],guild['is_guild_uploaded_img'],guild['owner_id'], guild['root_channel']))
            
            return result
        except Exception as e:
            logger.exception(e)
            return []
    def get_author_id(self,guild_id): 
        result = self.fetch_single("SELECT owner_id FROM guilds WHERE guild_id = ?",(guild_id,))
        return result[0] if result else None
    
    def is_users_sharing_guild(self, user_id, friend_id):
        query = """
            SELECT guild_id 
            FROM guilds 
            WHERE json_extract(users, '$[*]') LIKE ? 
            AND json_extract(users, '$[*]') LIKE ?
        """
        user_id_pattern = f'%{json.dumps(user_id)}%'
        friend_id_pattern = f'%{json.dumps(friend_id)}%'
        shared_guilds = self.fetch_multiple(query, (user_id_pattern, friend_id_pattern))
        return bool(shared_guilds)
    def get_shared_guilds_map(self, user_id, friend_ids):
        
        shared_guild_map = {}
        try:
            all_guilds = self.fetch_multiple("SELECT guild_id, users FROM guilds")
        except Exception as e:
            logger.error(f"Failed to fetch guilds: {e}")
            return shared_guild_map
        if not isinstance(all_guilds, list):
            logger.error("Expected a list of guild data")
            return shared_guild_map
        for friend_id in friend_ids:
            shared_guilds = []
            for guild in all_guilds:
                if not isinstance(guild, tuple) or len(guild) != 2:
                    logger.warning(f"Unexpected guild data format: {guild}")
                    continue
                guild_id, users_json = guild
                try:
                    users = json.loads(users_json)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode users JSON for guild {guild_id}: {e}")
                    continue

                if user_id in users and friend_id in users:
                    shared_guilds.append(guild_id)
            
            shared_guild_map[friend_id] = shared_guilds

        return shared_guild_map

    def add_user(self, guild_id, user_id):
        try:
            if not self.does_guild_exists(guild_id): return 
            current_users = self.fetch_single("SELECT users FROM guilds WHERE guild_id = ?", (guild_id,))
            if not current_users:
                logger.warning(f"Guild users {guild_id} Does not exists. Cant add user.")
                return
            if not user_id: return False

            current_users = json.loads(current_users[0])
            if user_id in current_users:
                logger.warning(f"User {user_id} already in the guild {guild_id}.")
                return

            current_users.append(user_id)
            updated_users_json = json.dumps(current_users)

            self.execute_query("UPDATE guilds SET users = ? WHERE guild_id = ?", updated_users_json, guild_id)

            logger.info(f"User {user_id} successfully added to the guild {guild_id}.")
            
            guild_name = self.resolve_guild_name(guild_id)
            author_id = self.get_author_id(guild_id)
            permissions_dict = {
                'read_messages': True,
                'send_messages': True,
                'manage_roles': False,
                'kick_members': False,
                'ban_members': False,
                'manage_channels': False,
                'mention_everyone': True,
                'add_reaction': True,
                'is_admin': False,
                'can_invite': True
            }
                
            self.give_permission_to_user(user_id,guild_id,permissions_dict)
            return (guild_id,user_id,guild_name,author_id)
        except IndexError:
            logger.warning("Guild ID not found.")
        except sqlite3.Error as e:
            logger.warning("Error occurred while adding user:", e)
            
            
    def remove_user(self, guild_id, user_id):
        if not guild_id or not user_id:
            logger.warning("Invalid guild_id or user_id.")
            return
        try:
            guild = self.fetch_single("SELECT * FROM guilds WHERE guild_id = ?", (guild_id,))
            if not guild:
                logger.warning("Guild not found.")
                return
            guild = json.loads(guild)
            current_users_json = guild["users"]
            current_users = json.loads(current_users_json)
            if user_id not in current_users:
                logger.warning("User not found in the guild.")
                return
            current_users.remove(user_id)
            updated_users_json = json.dumps(current_users)
            self.execute_query('''UPDATE guilds SET users = ? WHERE guild_id = ?''',
                                updated_users_json, guild_id)

            logger.warning("User removed successfully from the guild.")

        except Exception as e:
            logger.warning("Error occurred:", e)
            
            
