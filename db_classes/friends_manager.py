from db_classes.db_main_class import DatabaseManager,create_user_dms_query
from utils.utils import DATABASE_PATH , logger
from utils.user_class import User
from enum import Enum

class ErrorType(Enum):
    INVALID_EVENT = 'INVALID_EVENT'
    CANNOT_INTERACT_SELF = 'CANNOT_ADD_SELF'
    USER_NOT_FOUND = 'USER_NOT_FOUND'
    INVALID_IDENTIFIER = 'INVALID_IDENTIFIER'
    FRIEND_REQUEST_EXISTS = 'FRIEND_REQUEST_EXISTS'
    REQUEST_ALREADY_ACCEPTED = 'REQUEST_ALREADY_ACCEPTED'
    NOT_FRIENDS = 'NOT_FRIENDS'
    REQUEST_NOT_SENT = 'REQUEST_NOT_SENT'
    SUCCESS = 'SUCCESS'
    
class FriendsManager(DatabaseManager):
    def __init__(self):
        database_path = 'user_data.db'
        super().__init__(database_path,isPathRelative=True)
        self.database_path = DATABASE_PATH + database_path
        #self.execute_query(create_user_dms_query)

    def add_friend_request(self, sender_id, receiver_id):
        if sender_id == receiver_id: return
        self.execute_query('INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, ?)', sender_id, receiver_id, 'pending')

        return True

        
    def accept_friend_request(self, user_id, friend_id):
        if user_id == friend_id: return
        existing_connection = self.is_friend_request_existing(friend_id,user_id)
        if not existing_connection:
            logger.info(f"Friendship connection  between {user_id} and {friend_id} does not exist!")
            return False
        self.execute_query('UPDATE friends SET status = ? WHERE user_id = ? AND friend_id = ?', 'accepted', user_id, friend_id)
        
        self.execute_query('INSERT OR REPLACE INTO friends (user_id, friend_id, status) VALUES (?, ?, ?)', user_id, friend_id, 'accepted')
        
        self.execute_query('INSERT OR REPLACE INTO friends (user_id, friend_id, status) VALUES (?, ?, ?)', friend_id, user_id, 'accepted')
        
        self.add_user_dm(user_id,friend_id)
        self.add_user_dm(friend_id,user_id)

        logger.info(f'Accepted friend request by user {user_id} to {friend_id}')

        return True
    def is_friend_request_existing(self, user_id, friend_id):
        if not user_id or not friend_id: return False
        user_id = str(user_id)
        friend_id = str(friend_id)
        query = "SELECT * FROM friends WHERE user_id=? AND friend_id=? AND (status=? OR status=?)"
        result = self.fetch_single(query, (user_id, friend_id,'pending','accepted'))
        return result is not None



 
    def remove_friend_request(self, user_id, friend_id):
        if user_id == friend_id: return False
        self.execute_query("DELETE FROM friends WHERE user_id = ? AND friend_id = ? AND status = 'pending'", user_id, friend_id)
        logger.info(f'{user_id} has removed request to {friend_id}')
        return True
    
    def remove_friend(self, user_id, friend_id):
        if user_id == friend_id:
            return False

        query = """
            DELETE FROM friends
            WHERE 
                ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
                AND status = 'accepted'
        """
        self.execute_query(query, user_id, friend_id, friend_id, user_id)
        logger.info(f'User {user_id} has removed friend {friend_id}')
        return True

    def deny_friend_request(self, friend_id,user_id):
        if user_id == friend_id: return False

        self.execute_query('DELETE FROM friends WHERE user_id = ? AND friend_id = ?', user_id, friend_id)
        logger.info(f'Denied user {user_id} s friend {friend_id}')
        return True

    def is_blocked(self, user_id, friend_id):
        blocked_users = self.get_blocked_users(user_id)
        return bool(friend_id in blocked_users)
    def get_blocked_users(self, user_id):
        query = 'SELECT friend_id FROM friends WHERE user_id = ? AND status = ?'
        blocked_users = self.fetch_multiple(query, (user_id,'blocked'))
        return [user[0] for user in blocked_users] if blocked_users else []
    
    def block_friend_request(self,user_id,friend_id):
        if user_id == friend_id: return
        self.execute_query('INSERT OR REPLACE INTO friends (user_id, friend_id, status) VALUES (?, ?, ?)', user_id, friend_id, 'blocked')
        logger.info('User {user_id} has blocked {friend_id}')
        
    def remove_block_friend_request(self,user_id,friend_id):
        if user_id == friend_id: return
        self.execute_query('DELETE FROM friends WHERE user_id = ? AND friend_id = ?', user_id, friend_id)
        logger.info(f'User {user_id} has removed block of {friend_id}')
        return True


    def check_if_friends_old(self, user_id, friend_id):
        if not user_id or not friend_id:
            return False

        query = '''
            SELECT user_id FROM friends 
            WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
        '''
        result = self.fetch_single(query, (user_id, friend_id))
        logger.info(f'User {user_id} is friends with {friend_id} result : {bool(result)}')
        return bool(result)
    
    def check_if_friends(self, user_id, friend_id):
        query = '''
            SELECT COUNT(*)
            FROM friends f
            WHERE ((f.user_id = ? AND f.friend_id = ?)
                OR (f.user_id = ? AND f.friend_id = ?))
            AND f.status = 'accepted'
        '''
        result = self.fetch_single(query, (user_id, friend_id, friend_id, user_id))
        return result[0] > 0

    def db_get_friends(self, user_id, status_str=''):
        status_str = 'pending' if status_str == 'pending' else 'accepted'
        query = '''
            SELECT u.*
            FROM users u
            JOIN friends f ON (u.user_id = f.friend_id AND f.user_id = ?)
                            OR (u.user_id = f.user_id AND f.friend_id = ?)
            WHERE f.status = ?
            AND u.user_id != ?
        '''
        results = self.fetch_multiple(query, (user_id, user_id, status_str, user_id))
        return results
    def db_get_friend_ids(self, user_id):
        query = '''
            SELECT u.user_id
            FROM users u
            JOIN friends f ON (u.user_id = f.friend_id AND f.user_id = ?)
                            OR (u.user_id = f.user_id AND f.friend_id = ?)
            WHERE f.status = 'accepted'
            AND u.user_id != ?
        '''
        
        results = self.fetch_multiple(query, (user_id, user_id, user_id))
        friend_ids = [row[0] for row in results]
        
        return friend_ids
    def db_get_friend_raw(self, user_id, friend_id):
        query = '''
            SELECT u.user_id, u.email, u.password, u.nickname, u.discriminator, u.bot,
                u.status, u.description, u.created_at, u.last_login, u.verified,
                u.location, u.language, u.phone_number, u.social_media_links,
                u.date_of_birth, u.hide_profile, u.preferences
            FROM users u
            JOIN friends f ON (u.user_id = f.friend_id AND f.user_id = ?)
                            OR (u.user_id = f.user_id AND f.friend_id = ?)
            WHERE f.status = 'accepted'
            AND u.user_id != ?
            AND u.user_id = ?
        '''
        params = [user_id, user_id, user_id, friend_id]
        
        result = self.fetch_single(query, params)
        return result

    def db_get_friends_raw(self, user_id, friend_ids):
        if not friend_ids:
            return []

        query = '''
            SELECT u.user_id, u.email, u.password, u.nickname, u.discriminator, u.bot,
                u.status, u.description, u.created_at, u.last_login, u.verified,
                u.location, u.language, u.phone_number, u.social_media_links,
                u.date_of_birth, u.hide_profile
            FROM users u
            JOIN friends f ON (u.user_id = f.friend_id AND f.user_id = ?)
                            OR (u.user_id = f.user_id AND f.friend_id = ?)
            WHERE f.status = 'accepted'
            AND u.user_id != ?
            AND f.friend_id IN ({})
        '''.format(','.join('?' for _ in friend_ids))

        params = [user_id, user_id, user_id] + friend_ids

        results = self.fetch_multiple(query, (params))
        return results




    def db_get_friend(self, user_id, friend_id, redis_manager, users_manager):
        users_status = {}
        user_data_list = self.db_get_friend_raw(user_id, friend_id)
        for user_data in user_data_list:
            user = User(*user_data)
            online_users = redis_manager.get_online_users(users_manager)
            is_online = user.is_online(online_users)
            users_status[user.user_id] = {
                'user_id': user.user_id,
                'nickname': user.nickname,
                'discriminator': user.discriminator,
                'is_online': is_online,
                'bot': user.bot,
                'status': user.status if not user.hide_profile else None,
                'description': user.description if not user.hide_profile else None,
                'created_at': user.created_at if not user.hide_profile else None,
                'last_login': user.last_login if not user.hide_profile else None,
                'social_media_links': user.social_media_links if not user.hide_profile else None,
                'is_friends_requests_to_user': True 
            }
        
        return users_status


    
    def db_get_friends_requesting(self, user_id, isReqPending):
        
        statusstr = 'pending' if isReqPending else 'accepted'
        query = f'''
            SELECT *
            FROM users
            WHERE user_id IN (
                SELECT user_id
                FROM friends
                WHERE friend_id = ?
                AND status = '{statusstr}'
            )
        '''
        results = self.fetch_multiple(query, (user_id,))

        return results


    
    def find_all_friends(self,user_id,isRequestingPending):
        statusstr = 'pending' if isRequestingPending else 'accepted'
        user_id = str(user_id)
        query = f'''
            SELECT u.user_id, u.nickname, u.email, u.status, u.bot, u.description, u.created_at, u.last_login, u.social_media_links, u.hide_profile
            FROM users u
            JOIN (
                SELECT friend_id AS id
                FROM friends
                WHERE user_id = ? AND status = {statusstr}
                UNION
                SELECT user_id AS id
                FROM friends
                WHERE friend_id = ? AND status = {statusstr}
            ) f ON u.user_id = f.id
        '''
        return self.fetch_multiple(query, (user_id, user_id))
    
    def find_all_friends_ids(self,user_id):

        user_id = str(user_id)
        query = f'''
            SELECT u.user_id
            FROM users u
            JOIN (
                SELECT friend_id AS id
                FROM friends
                WHERE user_id = ? AND status = 'accepted'
                UNION
                SELECT user_id AS id
                FROM friends
                WHERE friend_id = ? AND status = 'accepted'
            ) f ON u.user_id = f.id
        '''
        return self.fetch_multiple(query, (user_id, user_id))

    def insert_values(self, user_data, online_users, users_status, is_friends_requests_to_user=False):
        user = User(*user_data) 
        is_online = user.is_online(online_users)
        user_info = {
            'user_id': user.user_id,
            'nickname': user.nickname,
            'discriminator': user.discriminator,
            'is_online': is_online,
            'bot': user.bot,
            'status': user.status if not user.hide_profile else None,
            'description': user.description if not user.hide_profile else None,
            'created_at': user.created_at if not user.hide_profile else None,
            'last_login': user.last_login if not user.hide_profile else None,
            'social_media_links': user.social_media_links if not user.hide_profile else None,
            'is_friends_requests_to_user': is_friends_requests_to_user
        }
        users_status[user.user_id] = user_info


    def get_users_friends_status(self, user_id, status_str='', online_users=None):
        users_status = {}

        isReqPending = status_str == 'pending'
        friends_user_made_request_to = self.db_get_friends(user_id, status_str)
        for user_data in friends_user_made_request_to:
            self.insert_values(user_data, online_users, users_status)
        
        if isReqPending:
            friends_made_request_to_user = self.db_get_friends_requesting(user_id, isReqPending)
            for user_data in friends_made_request_to_user:
                self.insert_values(user_data, online_users, users_status, True)
        return users_status
    


    def validate_and_get_user(self,user_input_data,users_manager):
        requested_friend_name = str(user_input_data.get('friend_name'))
        requested_friend_id = str(user_input_data.get('friend_id'))
        requested_friend_discriminator = str(user_input_data.get('friend_discriminator'))
        if not requested_friend_id or not requested_friend_id.isdigit() :
            requested_friend_id = users_manager.db_resolve_user(requested_friend_name,requested_friend_discriminator)
        data = requested_friend_id, requested_friend_discriminator, requested_friend_name
        return data 
    
    def handle_friend_request_event(self, event, user_input_data, user_id, users_manager,redis_manager):
        
        event_actions = {
            "add_friend_request": self.add_friend_request,
            "remove_friend_request": self.remove_friend_request,
            'remove_friend' : self.remove_friend,
            "accept_friend_request": self.accept_friend_request,
            "deny_friend_request": self.deny_friend_request,
            "block_friend_request": self.block_friend_request,
            "remove_block_friend_request": self.remove_block_friend_request
        }
        event_action = event_actions.get(event)
        
        data = self.validate_and_get_user(user_input_data, users_manager)
        requested_friend_id,requested_friend_discriminator,requested_friend_nick = data
        error_messages = [
            (not event or not event_action,
            ErrorType.INVALID_EVENT.value, 400),
            (not requested_friend_id,
            ErrorType.USER_NOT_FOUND.value, 400),
            (user_id == requested_friend_id,
            ErrorType.CANNOT_INTERACT_SELF.value, 403),
            (event == "add_friend_request" and not requested_friend_discriminator.isdigit() and not 'friend_id' in user_input_data,
            ErrorType.INVALID_IDENTIFIER.value, 400),
            (event == "add_friend_request" and self.is_friend_request_existing(user_id,requested_friend_id),
            ErrorType.FRIEND_REQUEST_EXISTS.value, 409),
            (event == "accept_friend_request" and not self.is_friend_request_existing(requested_friend_id, user_id),
            ErrorType.REQUEST_ALREADY_ACCEPTED.value, 403),
            ((event == "remove_friend_request" or event == "remove_friend") and not self.is_friend_request_existing(user_id, requested_friend_id),
            ErrorType.NOT_FRIENDS.value, 403),
            (event == "deny_friend_request" and not self.is_friend_request_existing(requested_friend_id, user_id),
            ErrorType.REQUEST_NOT_SENT.value, 403)
        ]
        for condition, message, status in error_messages:
            if condition:
                return {'message': {
                    'error' : message, 'type' : event, 'status': status,'success' : False, 'user_id' : requested_friend_id
                }}
            
            
        action_result = bool(event_action(user_id, requested_friend_id))
        response_message = {
            'type': event,
            'success': action_result,
            'user_id': requested_friend_id,
            'user_nick' : requested_friend_nick
        }
        if action_result and event == "add_friend_request" or event == "accept_friend_request":
            friend_data = self.db_get_friend(user_id,requested_friend_id,redis_manager,users_manager)
            response_message['user_data'] = friend_data

        return {'message': response_message}


    def add_user_dm(self, user_id, friend_id,aloneInteraction=True):
        if user_id and friend_id:
            self.execute_query("INSERT OR IGNORE INTO user_dms (user_id, friend_id) VALUES (?, ?)", user_id, friend_id)
            if not aloneInteraction:
                self.execute_query("INSERT OR IGNORE INTO user_dms (user_id, friend_id) VALUES (?, ?)", friend_id, user_id) 


    def get_users_dm(self,user_id):
        friends = self.fetch_multiple("SELECT friend_id FROM user_dms WHERE user_id = ?", (user_id,))
        return [friend[0] for friend in friends] if friends else []

    def remove_users_dm(self,user_id, friend_id):
        self.execute_query("DELETE FROM user_dms WHERE user_id = ? AND friend_id = ?", user_id, friend_id)
