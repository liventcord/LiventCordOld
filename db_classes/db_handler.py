import requests
from db_classes.friends_manager import FriendsManager
from db_classes.users_manager import UsersManager
from db_classes.guild_manager import GuildManager
from db_classes.postgres_manager import PostGresFileManager
from db_classes.email_manager import EmailManager
from db_classes.files_manager import FilesManager
from db_classes.messages_manager import GuildMessagesManager,DirectMessagesManager

from utils.utils import logger,is_using_pg
from redis_handler import redis_manager

project_path = '/home/ubuntu/liventcord'

friends_manager = FriendsManager()
users_manager = UsersManager()
guild_manager = GuildManager()
email_manager = EmailManager()
files_manager = FilesManager(project_path)
direct_messages_manager = DirectMessagesManager()


if is_using_pg:
    try:
        postgres_manager = PostGresFileManager()
    except Exception as e:
        print(e)
        logger.exception(e)
        requests.get('http://localhost:5005/shutdown')

        


from db_classes.db_main_class import create_guilds_query,create_users_query,create_channels_query,create_permissions_query,create_invites_query,create_invite_groups_query,create_emails_query,create_message_read_status_query,create_friends_query
guild_manager.execute_query(create_guilds_query)
guild_manager.execute_query(create_channels_query)
guild_manager.execute_query(create_permissions_query)
guild_manager.execute_query(create_invites_query)
guild_manager.execute_query(create_invite_groups_query)
guild_manager.execute_query(create_emails_query)
friends_manager.execute_query(create_friends_query)
users_manager.execute_query(create_users_query)
users_manager.execute_query(create_message_read_status_query)
users_manager.execute_query("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_channel ON UserChannelReadStatus (user_id, channel_id)")


if __name__ == '__main__':
    guild_manager.create_guild('LandReborn','452491822871085066','916548790662623282',False,users_manager)




    
    
    
    
