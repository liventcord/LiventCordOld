import json
from db_classes.db_main_class import DatabaseManager,create_dm_query
from utils.utils import create_random_id, DATABASE_PATH, construct_guild_path, Message, logger
from datetime import datetime
from os import remove

DISCORD_IDS_PATH = DATABASE_PATH + 'discord_ids.db'




class MessagesManager(DatabaseManager):

    def __init__(self, guild_id=None):

        db_path = construct_guild_path(guild_id) if guild_id else 'direct_messages.db'

        super().__init__(db_path, isPathRelative=guild_id is False)

        self.db_path = db_path

        self.is_server = bool(guild_id)
    

    def pack_into_dict(self, **kwargs):
        return kwargs

    def pack_messages(self, query, params=None):
        rows = self.fetch_multiple(query, (params))
        columns = ['message_id', 'user_id', 'content', 'channel_id', 'date', 'last_edited', 'attachment_urls', 'reply_to_id', 'reaction_emojis_ids']
        if not rows: return []

        messages = [dict(zip(columns, row)) for row in rows]
        return messages


        

    def db_get_oldest_message_date(self, requested_channel_id):
        result = self.fetch_single('SELECT date FROM Message WHERE channel_id=? ORDER BY date ASC LIMIT 1', (requested_channel_id,))
        return result
    
    

    def save_message_to_db(self, message_id, user_id, content, channel_id, date, last_edited, attachment_urls, reply_to_id, reaction_emojis_ids):
        raise NotImplementedError("Subclasses should implement this method.")
    

    def get_read_messages(self, user_id):
        raise NotImplementedError("Subclasses should implement this method.")
    

    def db_get_history_from_channel(self, requested_channel_id):
        raise NotImplementedError("Subclasses should implement this method.")
    

    def db_get_old_messages(self, channel_id, requested_date):
        raise NotImplementedError("Subclasses should implement this method.")
    

    def db_get_bulk_reply(self, requested_message_ids):
        raise NotImplementedError("Subclasses should implement this method.")


    def db_get_oldest_message_date(self, requested_channel_id):
        raise NotImplementedError("Subclasses should implement this method.")


class GuildMessagesManager(MessagesManager):
    def __init__(self, guild_id):
        super().__init__(guild_id)
        self.db_path = construct_guild_path(guild_id)
        self.guild_id = guild_id
        

    def delete_all_from_db(self):
        logger.info(f"Deleting all guild messages for guild {self.guild_id}")
        remove(self.db_path)


    def delete_all_from_channel(self,channel_id):

        try:
            self.execute_query(f'DELETE FROM Message WHERE channel_id=?',channel_id)
        except Exception:
            return False


    def delete_from_db(self, message_id,channel_id):

        try:
            self.execute_query(f'DELETE FROM Message WHERE message_id=? AND channel_id=?',message_id,channel_id)
            return True

        except Exception:
            return False


    def save_message_to_db(self, message_id, user_id, content, channel_id, date, last_edited, attachment_urls, reply_to_id, reaction_emojis_ids):

        attachment_urls_json = json.dumps(attachment_urls)
        reaction_emojis_ids_json = json.dumps(reaction_emojis_ids)
        logger.info(f"Saving user {user_id}'s content: {content} at channel {channel_id} in server {self.db_path} at date {date}")

        if not message_id:
            message_id = create_random_id()
        
        self.execute_query('''
            INSERT OR REPLACE INTO Message (message_id, user_id, content, channel_id, date, last_edited, attachment_urls, reply_to_id, reaction_emojis_ids) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', message_id, user_id, content, channel_id, date, last_edited, attachment_urls_json, reply_to_id, reaction_emojis_ids_json)
        

    def db_get_oldest_message_date(self, requested_channel_id):
        result = self.fetch_single('SELECT date FROM Message WHERE channel_id=? ORDER BY date ASC LIMIT 1', (requested_channel_id,))
        return result

    def db_get_message_date(self, channel_id, message_id):
        result = self.fetch_single('SELECT date FROM Message WHERE channel_id=? AND message_id =? ORDER BY date ASC LIMIT 1', (channel_id,message_id))

        return str(result[0]) if result else None
    


    def db_get_history_from_channel(self, requested_channel_id):

        query = '''

            SELECT message_id, user_id, content, channel_id, date, last_edited, attachment_urls, reply_to_id, reaction_emojis_ids
            FROM Message 
            WHERE channel_id=?
            ORDER BY date DESC
            LIMIT 50
        '''

        return [Message(msg_data).__dict__ for msg_data in self.pack_messages(query, (requested_channel_id,))]
    

    def db_get_old_messages(self, channel_id, requested_date,message_id=None):

        regular_query = '''

            SELECT DISTINCT message_id, user_id, content, channel_id, date, last_edited, reply_to_id, attachment_urls, reaction_emojis_ids
            FROM Message 
            WHERE channel_id=? AND date < ?
            ORDER BY date DESC
            LIMIT 50
        '''


        fetch_around_query = '''

            WITH ranked_messages AS (
                SELECT 
                    message_id, 
                    user_id, 
                    content, 
                    channel_id, 
                    date, 
                    last_edited, 
                    reply_to_id, 
                    attachment_urls, 
                    reaction_emojis_ids,
                    ROW_NUMBER() OVER (ORDER BY date DESC) AS row_num

                FROM Message 
                WHERE channel_id = ?

            ),

            target_message_row AS (

                SELECT row_num
                FROM ranked_messages
                WHERE message_id = ?
            )

            SELECT 
                message_id, 
                user_id, 
                content, 
                channel_id, 
                date, 
                last_edited, 
                reply_to_id, 
                attachment_urls, 
                reaction_emojis_ids

            FROM ranked_messages

            WHERE 
                row_num BETWEEN 
                (SELECT row_num FROM target_message_row LIMIT 1) - 25 AND 
                (SELECT row_num FROM target_message_row LIMIT 1) + 25

            ORDER BY row_num

            LIMIT 50;
        '''

        

        if message_id: # Fetching around msg
            #target_message_date = self.db_get_message_date(channel_id,message_id)
            return [Message(msg_data).__dict__ for msg_data in self.pack_messages(fetch_around_query, (channel_id, message_id))]
        else:
            return [Message(msg_data).__dict__ for msg_data in self.pack_messages(regular_query, (channel_id, requested_date))]

    def db_get_bulk_reply(self, requested_message_ids, channel_id):

        if not requested_message_ids:
            return []

        sanitized_ids = [str(msg_id) for msg_id in requested_message_ids if str(msg_id).isdigit()]

        if not sanitized_ids:
            return []

        ids_list = ', '.join(f"'{msg_id}'" for msg_id in sanitized_ids)

        query = f'''

            SELECT message_id, user_id, content, channel_id, date, last_edited, reply_to_id, attachment_urls, reaction_emojis_ids
            FROM Message
            WHERE channel_id=?
            AND message_id IN ({ids_list})
            ORDER BY date DESC
        '''

        params = (channel_id,)
        return [Message(msg_data).__dict__ for msg_data in self.pack_messages(query, params)]


    def search_from_db(self, search_query, channel_id, page_index):

        messages_per_page = 25

        offset = page_index * messages_per_page

        query = '''

            SELECT * 
            FROM Message 
            WHERE channel_id = ? AND content LIKE ? 
            LIMIT ? OFFSET ?
        '''
        

        search_pattern = f"%{search_query}%"
        
        results = self.fetch_multiple(query, channel_id + (search_pattern, messages_per_page, offset))
        return results 
        

class DirectMessagesManager(DatabaseManager):

    def __init__(self):

        super().__init__('direct_messages.db', isPathRelative=True)
        self.execute_query(create_dm_query)
        
        

        
        

    def pack_messages(self, query, params):

        rows = self.fetch_multiple(query, params)

        if not rows: return []

        columns = ['message_id', 'user_id', 'content', 'date', 'last_edited', 'attachment_urls', 'reply_to_id', 'reaction_emojis_ids']

        messages = [dict(zip(columns, row)) for row in rows]
        return messages

    def delete_from_db(self, message_id,user_id,friend_id):

        try:

            self.execute_query(f'DELETE FROM Message WHERE message_id=? AND (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)'
                               ,message_id,user_id, friend_id, friend_id, user_id)
            return True

        except Exception:
            return False


    def save_message_to_db(self, message_id,sender_id, receiver_id, content,date, attachment_urls=None, last_edited=None, reply_to_id=None, reaction_emojis_ids=None):

        attachment_urls_json = json.dumps(attachment_urls) if attachment_urls else None

        reaction_emojis_ids_json = json.dumps(reaction_emojis_ids) if reaction_emojis_ids else None
        

        logger.info(f"Saving message from user {sender_id} to user {receiver_id} at {date}")
        

        self.execute_query('''

            INSERT INTO Message (message_id, sender_id,user_id, receiver_id, content, date, last_edited, attachment_urls, reply_to_id, reaction_emojis_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ''', message_id, sender_id, sender_id, receiver_id, content, date, last_edited, attachment_urls_json, reply_to_id, reaction_emojis_ids_json)


    def get_messages_between_users(self, user1_id, user2_id):

        query = '''

            SELECT message_id, sender_id, receiver_id, content, date, last_edited, attachment_urls, reply_to_id, reaction_emojis_ids
            FROM Message
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY date DESC
            LIMIT 50
        '''

        messages = self.fetch_multiple(query, (user1_id, user2_id, user2_id, user1_id))

        if not messages: return []

        result = []
        

        for msg_data in messages:

            message_dict = {

                'message_id': msg_data[0],

                'user_id': msg_data[1],  

                'content': msg_data[3],

                'channel_id': msg_data[2],  

                'date': msg_data[4],

                'last_edited': msg_data[5],

                'attachment_urls': msg_data[6],

                'reply_to_id': msg_data[7],

                'reaction_emojis_ids': msg_data[8]

            }

            result.append(Message(message_dict).__dict__)
        
        return result


    def db_get_old_messages_between_users(self, user_id, channel_id, requested_date,message_id=None):

        regular_query = '''

            SELECT DISTINCT  message_id, user_id, content, date, last_edited, reply_to_id, attachment_urls, reaction_emojis_ids

            FROM Message 

            WHERE  date < ? AND 

                ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))

            ORDER BY date DESC

            LIMIT 50;
        '''


        fetch_around_query = '''

            WITH ranked_messages AS (

                SELECT message_id, user_id, content, date, last_edited, reply_to_id, attachment_urls, reaction_emojis_ids,ROW_NUMBER() OVER (ORDER BY date DESC) AS row_num

                FROM Message 

                WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)

            ),

            target_message_row AS (

                SELECT row_num

                FROM ranked_messages

                WHERE message_id = ?

            )

            SELECT 

                message_id, user_id, content, date, last_edited, reply_to_id, attachment_urls, reaction_emojis_ids

            FROM ranked_messages

            WHERE 

                row_num BETWEEN 

                (SELECT row_num FROM target_message_row LIMIT 1) - 25 AND 

                (SELECT row_num FROM target_message_row LIMIT 1) + 25

            ORDER BY row_num

            LIMIT 50;
        '''

        

        if message_id:  # Fetching around a specific message

            results = self.pack_messages(fetch_around_query, (user_id, channel_id, user_id, channel_id, message_id))

        else:

            results = self.pack_messages(regular_query, (requested_date, user_id, channel_id, user_id, channel_id))
        

        messages_with_channel_id = [dict(msg_data, channel_id=channel_id) for msg_data in results]

        return [Message(msg_data).__dict__ for msg_data in messages_with_channel_id]


    def db_get_oldest_message_date(self, user_id, friend_id):

        query = '''

            SELECT date FROM Message

            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)

            ORDER BY date ASC LIMIT 1
        '''

        result = self.fetch_single(query, (user_id, friend_id,friend_id, user_id))
        return result