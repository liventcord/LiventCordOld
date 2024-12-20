import random,re,os,string
from utils.log_config import logger,db_logger 
from datetime import datetime

staticpath = os.getcwd()+'/static'


DATABASE_PATH = os.getcwd() + '/databases/'


is_using_pg = True
is_logging = True

LENGTH = 19

MIN_VALUE = 10 ** (LENGTH - 1)

MAX_VALUE = (10 ** LENGTH) - 1


def create_random_id():
    return str(random.randint(MIN_VALUE, MAX_VALUE))

def create_random_string():
    length = 8
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length)) 

def is_id_valid(file_id):
    if not file_id: return False

    return bool(len(file_id == LENGTH))

def pack_user_info(hide_profile, is_online, user_data):
    
    if not isinstance(user_data, tuple):
        raise ValueError("user_data must be a tuple")

    user_id, name,discriminator, email, status, bot, description, created_at, last_login, social_media_links, hide_profile = user_data

    user_info = {
        user_id: {
            'user_id': user_id,
            'hide_profile': hide_profile,
            'name': name,
            'discriminator' : discriminator,
            'is_online': is_online,
            'status': status if not hide_profile else None,
            'description': description if not hide_profile else None,
            'created_at': created_at if not hide_profile else None,
            'last_login': last_login if not hide_profile else None,
            'social_media_links': social_media_links if not hide_profile else None
        }
    }
    return user_info

def construct_guild_image_path(guild_id):
    return f"/servers/{guild_id}.png"


def construct_guild_path(guild_id):
    return DATABASE_PATH + f"Server_{guild_id}_database.db"


def datetime_to_string(data):
    """Recursively convert datetime objects to ISO string format in a dictionary or list."""
    if isinstance(data, dict):
        return {k: datetime_to_string(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [datetime_to_string(i) for i in data]
    elif isinstance(data, datetime):
        return data.isoformat()  # Convert datetime to ISO format
    return data


class Message:
    def __init__(self, data):
        self.message_id = data['message_id']
        self.user_id = data['user_id']
        if 'sender_id' in data:
            self.sender_id = data['sender_id']
        self.content = data['content']
        if 'channel_id' in data:
            self.channel_id = data['channel_id']
        
        self.date = self.parse_date(data['date'])
        self.last_edited = data.get('last_edited')
        self.attachment_urls = data.get('attachment_urls', [])
        self.reply_to_id = data.get('reply_to_id')
        self.reaction_emojis_ids = data.get('reaction_emojis_ids', [])

    def parse_date(self, date_str):
        if isinstance(date_str, datetime):
            return date_str

        for fmt in ("%Y-%m-%d %H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Date format for '{date_str}' is not recognized.")

    def to_dict(self):
        return {
            'message_id': self.message_id,
            'user_id': self.user_id,
            'sender_id': getattr(self, 'sender_id', None),
            'content': self.content,
            'channel_id': getattr(self, 'channel_id', None),
            'date': self.date.isoformat(),  # Ensure date is serialized as a string
            'last_edited': self.last_edited,
            'attachment_urls': self.attachment_urls,
            'reply_to_id': self.reply_to_id,
            'reaction_emojis_ids': self.reaction_emojis_ids
        }

    def __repr__(self):
        return f"Message(message_id={self.message_id}, user_id={self.user_id}, content={self.content}, channel_id={self.channel_id}, date={self.date.isoformat()}, last_edited={self.last_edited}, attachment_urls={self.attachment_urls}, reply_to_id={self.reply_to_id}, reaction_emojis_ids={self.reaction_emojis_ids})"

