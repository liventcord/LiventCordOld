from db_classes.db_main_class import DatabaseManager
from datetime import datetime
from pytz import utc as UTC
from utils.utils import logger
from bcrypt import gensalt,hashpw,checkpw
import random

class UsersManager(DatabaseManager):
    def __init__(self):   super().__init__('user_data.db')
        
        
            
    def mark_as_read(self, user_id, channel_id):
        readen_time = datetime.now(UTC)
        self.execute_query('''
            INSERT OR REPLACE INTO UserChannelReadStatus (user_id, channel_id, read_at)
            VALUES (?, ?, ?)
        ''', user_id, channel_id,str(readen_time))
        
        logger.info(f"User {user_id} has readen channel {channel_id} for {readen_time}")
        
    def get_last_read_datetimes(self, redis_manager, user_id, guild_id=None):
        all_guilds_channels = redis_manager.get_from_redis_dict('all_guild_channels')
        channels_data_to_process = all_guilds_channels.get(guild_id, {}) if guild_id else all_guilds_channels
        default_datetime = str(datetime(1970, 1, 1, tzinfo=UTC).isoformat())
        
        last_read_datetimes = {}
        for channel_id in channels_data_to_process.keys():
            res = self.fetch_single('''
                SELECT read_at
                FROM UserChannelReadStatus
                WHERE user_id = ? AND channel_id = ?
            ''', (user_id, channel_id))
            last_read_datetimes[channel_id] = res[0] if res else default_datetime
        
        return last_read_datetimes
            
    def get_encrypted_password(self,password: str) -> str:
        """
        Hashes the provided password using bcrypt and returns the hash.

        :param password: The password to be hashed.
        :return: The hashed password.
        """
        salt = gensalt()
        hashed = hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    def check_if_password_is_matching(self,password: str, hashed_password: str) -> bool:
        """
        Checks if the provided password matches the hashed password using bcrypt.

        :param password: The password to be checked.
        :param hashed_password: The previously hashed password to compare against.
        :return: True if the password matches the hashed password, False otherwise.
        """
        return checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    def get_hashed_password(self,email: str) -> str:
        """
        Retrieves the hashed password for the given email from the database.

        :param email: The email of the user.
        :return: The hashed password or None if the user does not exist.
        """

        try:

            result = self.fetch_single('''
                SELECT password FROM users WHERE email = ?
            ''', (email,))

            return result[0] if result else None
        except Exception as e:
            logger.exception(f"Error retrieving password for user '{email}': {e}")



    
    
    def change_password(self,nickname: str, current_password: str, new_password: str) -> bool:
        """
        Changes the user's password if the current password is verified.

        :param nickname: The nickname of the user.
        :param current_password: The user's current password.
        :param new_password: The new password to be set.
        :return: True if the password was changed successfully, False otherwise.
        """

        try:

            result = self.fetch_single('''
                SELECT password FROM users WHERE nickname = ?
            ''', (nickname,))

            if result and self.check_if_password_is_matching(current_password, result[0]):
                new_hashed_password = self.save_encrypted_password(new_password)
                self.execute_query('''
                        UPDATE users
                        SET password = ?
                        WHERE nickname = ?
                    ''', new_hashed_password, nickname)
                logger.info(f"Password for user '{nickname}' changed successfully.")
                return True
            else:
                logger.info(f"Current password for user '{nickname}' is incorrect.")
                return False
        except Exception as e:
            logger.exception(f"Error changing password for user '{nickname}': {e}")
            return False

    def db_check_for_user(self, user_id):
        return bool(self.fetch_single('SELECT user_id FROM users WHERE user_id=?', (user_id,)))

    def db_get_nick_discriminator_from_email(self, email):
        result = self.fetch_single('SELECT nickname, discriminator FROM users WHERE email = ?', (email,))
        return result

    
    def db_get_nick_id_from_email(self, email):
        result = self.fetch_single('SELECT nickname,user_id FROM users WHERE email = ?', (email,))
        nickname = str(result[0]) if result else None
        user_id = str(result[1]) if result else None
        return nickname,user_id
    
    def db_resolve_user(self,user_nick,user_discriminator):
        result = self.fetch_single('SELECT user_id FROM users WHERE nickname = ? AND discriminator =?',(user_nick,user_discriminator))
        return result[0] if result else None
    def db_get_users_id_nick_discriminator(self,user_ids):
        data = []
        for user_id in user_ids:
            data.append(self.fetch_single('SELECT user_id, nickname,discriminator FROM users WHERE user_id = ?',(user_id,)))
        return data
 
            
        
    
    def db_update_user_last_login(self, user_id):
        if not user_id: 
            logger.exception("User id does not exists!")
            return
        current_time = datetime.now(UTC).isoformat()
        query = "UPDATE users SET last_login = ? WHERE user_id = ?"
        self.execute_query(query, current_time, user_id)

    def db_get_users_for_status_admin_update(self, online_users):
        users = self.fetch_multiple('SELECT user_id, nickname, email,status,description,bot FROM users')
        users_data = {}
        for user_id, nickname, email,status,description,bot in users:
            is_online = user_id in online_users
            users_data[user_id] = {'nickname': nickname, 'id' : user_id, 'is_online': is_online,'email':email,'status':status,'description':description,'bot':bot}
        return users_data

    def db_get_user_list(self):
        return self.fetch_multiple('SELECT user_id, nickname, email, status, description, bot FROM users')

    def db_reset_password(self, new_password, email):
        self.execute_query('UPDATE users SET password = ? WHERE email = ?', new_password, email)

    def db_get_users_info(self, online_users):
        users = self.fetch_multiple('SELECT user_id, email,  nickname,discriminator , status, description, bot FROM users')
        users_info = []
        for user in users:
            user_id, email, password, nickname,discriminator,status, description, bot = user

            user_info = {
                'user_id': user_id,
                'email': email,
                'nickname': nickname,
                'discriminator' : discriminator,
                'status' : status,
                'description' : description,
                'bot' : bot,
                'is_online' : email in online_users
            }
            users_info.append(user_info)
        return users_info

    def db_authenticate(self, email: str, password: str):
        """
        Authenticates a user by their email and password.

        :param email: The email of the user.
        :param password: The password of the user.
        :return: A tuple of user_id, email, and nickname if authentication is successful, otherwise None.
        """
        hashed_password = self.get_hashed_password(email)
        if hashed_password and self.check_if_password_is_matching(password, hashed_password):
            user_data = self.fetch_single('SELECT user_id, email, nickname FROM users WHERE email = ?', (email,))
            if user_data:
                return user_data
        return None
    
    def db_get_user_name(self,user_id):
        if not user_id: return None
        return self.fetch_single('SELECT nickname FROM users WHERE user_id=?', (user_id,))[0]
    
    def db_get_user_discriminator_name(self,user_id):
        if not user_id: return None
        return self.fetch_single('SELECT nickname, discriminator FROM users WHERE user_id=?', (user_id,))
    
    def db_get_user_id(self,user_email):
        if not user_email: return None
        result = self.fetch_single('SELECT user_id FROM users WHERE email=?', (user_email,))
        return result[0] if result else None
    
    def db_get_user_names(self, user_ids):
        if not user_ids:    return {}
        query = 'SELECT user_id, nickname FROM users WHERE user_id IN ({})'.format(','.join(['?'] * len(user_ids)))
        result = self.fetch_multiple(query, user_ids)
        return {row[0]: row[1] for row in result}
    def get_existing_discriminators(self, nickname):
            rows = self.fetch_multiple(
                'SELECT discriminator FROM users WHERE nickname=?',
                (nickname,)
            )
            return {row[0] for row in rows}

    def create_discriminator(self, nickname):
        length = 4
        min_value = 10 ** (length - 1)
        max_value = (10 ** length) - 1

        all_discriminators = {str(i).zfill(length) for i in range(min_value, max_value + 1)}
        existing_discriminators = self.get_existing_discriminators(nickname)
        available_discriminators = all_discriminators - existing_discriminators

        return random.choice(list(available_discriminators)) if available_discriminators else '0000'
    
    def is_nick_unique(self,nickname):
        nick =  self.fetch_single('SELECT nickname FROM users WHERE nickname=?',(nickname,))
        return nick is None
        
    def db_add_new_user(self, user_id, email, password, nickname,discriminator=None, status='offline', description='', bot=0):
        if not discriminator:
            discriminator = self.create_discriminator() if not self.is_nick_unique(nickname) else '0000'
        password = self.get_encrypted_password(password)
        
        add_new_user_query = 'INSERT INTO users (user_id, email, password, nickname,discriminator, status, description, bot) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
        self.execute_query(add_new_user_query, user_id, email, password, nickname, discriminator,status, description, bot)  

    def db_update_user_status(self, user_id,status):
        self.execute_query('UPDATE users SET status = ? WHERE user_id = ?', status, user_id)
        
    def db_update_user_nickname(self, user_id, new_nickname):
        user = self.fetch_single('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if user:
            self.execute_query('UPDATE users SET nickname = ? WHERE user_id = ?', new_nickname, user_id)
            return True 
        else:
            return False 
        
    def db_get_all_users_ids(self):
        return [str(user_id[0]) for user_id in self.fetch_multiple('SELECT CAST(user_id AS TEXT) FROM users')]
        
    
    def get_users_status(self, user_ids):
        if not isinstance(user_ids, list):
            user_ids = [user_ids]
        data = []
        for user_id in user_ids:
            data.append(self.fetch_single('SELECT user_id, nickname, discriminator, email, status, bot, description, created_at, last_login, social_media_links, hide_profile FROM users WHERE user_id = ?', (user_id,)))
        return data
            
        
        
        




        
