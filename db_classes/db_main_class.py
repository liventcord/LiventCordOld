import sqlite3,os
import psycopg2,traceback
from psycopg2 import pool
from utils.utils import DATABASE_PATH,db_logger 
from colorama import Fore,init
init()

import time

create_emails_query = '''
    CREATE TABLE IF NOT EXISTS sent_emails (
        email TEXT PRIMARY KEY,
        sent_time TIMESTAMP,
        send_count INTEGER DEFAULT 1
    )
'''

create_guilds_query = '''
    CREATE TABLE IF NOT EXISTS guilds (
        guild_id TEXT PRIMARY KEY,
        owner_id TEXT NOT NULL,
        guild_name TEXT NOT NULL,
        users TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        root_channel TEXT NOT NULL,
        region TEXT,
        settings TEXT,
        is_guild_uploaded_img INTEGER NOT NULL
    )
'''
create_users_query = '''
    CREATE TABLE IF NOT EXISTS users(   
        user_id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nickname TEXT NOT NULL,
        discriminator TEXT NOT NULL,
        bot INTEGER NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('offline', 'online', 'idle', 'invisible', 'do not disturb')),
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        verified INTEGER DEFAULT 0,
        location TEXT,
        language TEXT,
        phone_number TEXT UNIQUE,
        social_media_links TEXT,
        date_of_birth DATE,
        hide_profile INTEGER DEFAULT 0,
        preferences JSON,
        UNIQUE (nickname, discriminator)
    )
'''


create_channels_query = """
    CREATE TABLE IF NOT EXISTS channels (
        channel_id TEXT PRIMARY KEY,
        guild_id TEXT,
        channel_name TEXT,
        is_text_channel INTEGER NOT NULL,
        FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
        
    )
"""

create_dm_query = '''
    CREATE TABLE IF NOT EXISTS Message (
        message_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        sender_id TEXT NOT NULL,
        receiver_id TEXT NOT NULL,
        date TEXT NOT NULL, 
        last_edited TEXT,
        attachment_urls TEXT,
        reply_to_id TEXT,
        reaction_emojis_ids TEXT
    )
'''
create_messages_query = '''
    CREATE TABLE IF NOT EXISTS Message (
        message_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        date TEXT NOT NULL, 
        last_edited TEXT,
        attachment_urls TEXT,
        reply_to_id TEXT,
        reaction_emojis_ids TEXT
    )
'''
create_permissions_query = '''
    CREATE TABLE IF NOT EXISTS permissions (
        guild_id TEXT NOT NULL UNIQUE,
        user_id TEXT NOT NULL,
        read_messages BOOLEAN NOT NULL,
        send_messages BOOLEAN NOT NULL,
        manage_roles BOOLEAN NOT NULL,
        kick_members BOOLEAN NOT NULL,
        ban_members BOOLEAN NOT NULL,
        manage_channels BOOLEAN NOT NULL,
        mention_everyone BOOLEAN NOT NULL,
        add_reaction BOOLEAN NOT NULL,
        is_admin BOOLEAN NOT NULL,
        can_invite BOOLEAN NOT NULL,
        PRIMARY KEY (guild_id, user_id)
    );
'''
create_invites_query = '''
    CREATE TABLE IF NOT EXISTS invites (
        invite_id TEXT PRIMARY KEY NOT NULL,
        group_id TEXT NOT NULL,
        FOREIGN KEY (group_id) REFERENCES invite_groups(group_id)
    );

'''

create_invite_groups_query = '''
    CREATE TABLE IF NOT EXISTS invite_groups (
        group_id TEXT PRIMARY KEY NOT NULL,
        creator_id TEXT NOT NULL,
        guild_id TEXT NOT NULL,
        channel_id TEXT NOT NULL
    );
'''


create_message_read_status_query = '''
    CREATE TABLE IF NOT EXISTS UserChannelReadStatus (
        user_id TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        read_at TEXT NOT NULL,
        PRIMARY KEY (user_id, channel_id)
    );
'''

create_friends_query = '''
    CREATE TABLE IF NOT EXISTS friends (
        user_id TEXT,
        friend_id TEXT,
        status TEXT,
        PRIMARY KEY (user_id, friend_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (friend_id) REFERENCES users(id)
    )
'''
create_user_dms_query = '''
    CREATE TABLE IF NOT EXISTS user_dms (
        user_id TEXT,
        friend_id TEXT,
        PRIMARY KEY (user_id, friend_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (friend_id) REFERENCES users(id)
    );
'''



class DatabaseManager:
    def __init__(self, database_path, is_post_gress=False,isPathRelative=True):
        self.database_path = DATABASE_PATH + database_path if isPathRelative else database_path

        self.is_post_gress = is_post_gress
        self.connection_pool = None
        password = os.getenv('PSQL_PASS')
        
        if self.is_post_gress:
            try:      
                self.connection_pool = pool.SimpleConnectionPool(1, 10,  
                    user='liventcord',password=password,host='localhost',port='5432', database='liventdb'
                )
            except Exception as e:
                db_logger.exception(f"Error initializing connection pool: {e}")
            
    def connect(self, retries=1):
        try:
            if self.is_post_gress:
                if self.connection_pool:
                    return self.connection_pool.getconn()
            else:
                return sqlite3.connect(self.database_path)
        except psycopg2.pool.PoolError as e:
            db_logger.exception(f"PoolError: {e}")
            if retries > 0:
                time.sleep(1) 
                return self.connect(retries - 1)
            else:
                db_logger.info("Exceeded maximum retries for getting a connection from the pool.")
                raise

    def close_connection(self, conn):
        if self.is_post_gress and self.connection_pool:
            self.connection_pool.putconn(conn)
        else:
            conn.close()
    

    def print_message(self, color, *msg):
        message_str = ' '.join(map(str, msg))
        
        if len(message_str) > 1500:
            message_str = message_str[:1500] + '... (message truncated)'
        
        is_saving = True 
        if is_saving:
            db_logger.info(message_str)
        else:
            print(color, message_str)
    

    def do_query(self, query, args, is_multiple,row_factory):
        try:
            conn = None
            cursor = None
            conn = self.connect()
            if not conn or not hasattr(conn,'cursor'): 
                db_logger.exception(f"Conn does not exists! is postgres:{self.is_post_gress}")
                return
            if row_factory:conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            self.print_message(Fore.BLUE,f"Query: {query} {f'Args: {args}' if args else '' }")
            
            if args is not None:
                cursor.execute(query, args)
            else:
                cursor.execute(query)
            
            result = cursor.fetchall() if is_multiple else cursor.fetchone()
            self.close_connection(conn)
            if is_multiple:
                self.print_message(Fore.GREEN, f'Result : {result}')
            else:
                self.print_message(Fore.MAGENTA, f'Result : {result}')
            return result

        except Exception as e:
            print(f"{e}, Query: {query}, Args: {args}")

    def fetch_multiple(self, query, args=None,row_factory=False):
        """
        Fetches multiple rows from the database.

        :param query: The SQL query to execute.
        :param params: The parameters to use in the SQL query.
        :return: The fetched rows or None if no row matches.
        """
        try:
            return self.do_query(query, args, True,row_factory)
        except Exception as e:
            
            traceback.print_exc()
            db_logger.exception(f"Error while fetching database: ")
            
    def fetch_single(self, query, args=None,row_factory=False):
        """
        Fetches single row from the database.

        :param query: The SQL query to execute.
        :param params: The parameters to use in the SQL query.
        :return: The fetched row or None if no row matches.
        """
        try:
            return self.do_query(query, args, False,row_factory)
        except Exception as e:
            db_logger.exception(f"Error while fetching database: ")
            
    def execute_query(self, query, *args):
        """
        Executes query in the database.

        :param query: The SQL query to execute.
        :param args: The parameters to use in the SQL query.
        """
        conn = None
        cursor = None

        conn = self.connect()
        if not conn: 
            db_logger.exception("Connection is ignored")
            return
        
        cursor = conn.cursor()
        
        self.print_message(Fore.CYAN, f"Query: {query} {f'Args: {args}' if args else ''} ")

        if args:
            # Unpack single tuple args
            if len(args) == 1 and isinstance(args[0], tuple):
                cursor.execute(query, args[0])  # Unpack the tuple
            else:
                cursor.execute(query, args)  # Use args as-is
        else:
            cursor.execute(query)
        
        conn.commit()
        self.close_connection(conn)

