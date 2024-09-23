from db_classes.db_main_class import DatabaseManager
from utils.utils import create_random_id,DATABASE_PATH,logger,is_id_valid
from io import BytesIO
from enum import Enum
import subprocess,socket
class FileType(Enum):
    ATTACHMENT = 1
    PROFILE = 2
    EMOJI = 3
    GUILDIMG = 4
timeout = 30

class PostGresFileManager(DatabaseManager):
    def __init__(self):
        if not self.does_postgres_lives():
            subprocess.run(['sudo', 'service', 'postgresql', 'start'])
        database_path = 'user_data.db'
        super().__init__(database_path,is_post_gress=True)
        self.is_post_gres=True
        self.cache = {}
        self.database_path = DATABASE_PATH + database_path
        self.create_files_table(self.get_table_name(FileType.ATTACHMENT))
        self.create_files_table(self.get_table_name(FileType.PROFILE))
        self.create_files_table(self.get_table_name(FileType.EMOJI))
        self.create_files_table(self.get_table_name(FileType.GUILDIMG))



    def does_postgres_lives(self,host = 'localhost', port=5432):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2) 
                s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            print(f"PostgreSQL is not reachable. Error: {e}")
            return False
        
    
    def calculate_total_guild_size(self,guild_id):
        attachmentssize = self.calculate_storage(guild_id,self.get_table_name(FileType.ATTACHMENT))
        print(attachmentssize)
        emojissize = self.calculate_storage(guild_id,self.get_table_name(FileType.EMOJI))
        print(emojissize)
        guildimagesize = self.calculate_storage(guild_id,self.get_table_name(FileType.GUILDIMG))
        print(guildimagesize)
    def calculate_size_query(self,table_name):
        return f"SELECT SUM(pg_column_size(content)) / (1024.0 * 1024.0) AS total_size_mb FROM {table_name} WHERE guild_id=?;"
    
    def get_all_files(self,table_name):
        return f"SELECT file_name, pg_column_size(content) / (1024.0 * 1024.0) AS size_mb FROM {table_name} WHERE guild_id=? ORDER BY size_mb DESC;"
    
    def calculate_storage(self, table_name,guild_id):
        decimal = self.fetch_single(self.calculate_size_query(table_name))
        results = self.fetch_multiple(self.get_all_files(table_name),guild_id)
        if results and decimal:
            print(f"{table_name} has {len(results)} files [{decimal[0]:.1f}MB]:")
        return decimal

        
    def create_files_table(self,tablename):
        create_table_query = f'''
        CREATE TABLE IF NOT EXISTS {tablename} (
            file_name TEXT NOT NULL,
            file_id VARCHAR(20) PRIMARY KEY NOT NULL,
            guild_id VARCHAR(20),
            channel_id TEXT,
            user_id TEXT,
            content BYTEA NOT NULL,
            extension TEXT NOT NULL
        )
        '''
        self.execute_query(create_table_query)


    def get_table_name(self,_file_type):
        _file_type = str(_file_type)
        if _file_type == str(FileType.ATTACHMENT):
            tablename = "attachment_files"
        elif _file_type == str(FileType.PROFILE):
            tablename = "profile_files"
        elif _file_type == str(FileType.EMOJI):
            tablename = "emoji_files"
        elif _file_type == str(FileType.GUILDIMG):
            tablename = "guilds_files"
        if tablename: return tablename
        
    def upload_file(self, file_name, _file_type, content, extension, guild_id=None,channel_id=None,user_id=None,is_guild_image=False):
        
        file_id = guild_id if guild_id and is_guild_image else create_random_id()
        
        table_name = self.get_table_name(_file_type)
        check_query = f"SELECT COUNT(*) FROM {table_name} WHERE file_id = %s"
        result = self.fetch_single(check_query, (file_id,))
        file_exists = result[0] > 0 if result else False
        
        if file_exists and _file_type == FileType.ATTACHMENT:
            logger.info(f"Can not insert file {file_name} on type {_file_type} with guild {guild_id}")
            return
        else:
            if guild_id:
                if channel_id:
                    insert_query = f"""
                        INSERT INTO {table_name} (file_name, file_id, user_id, guild_id, content, extension)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    insert_params = (file_name, file_id, user_id, guild_id, content, extension)
                else:
                    insert_query = f"""
                        INSERT INTO {table_name} (file_name, file_id, user_id, guild_id,channel_id, content, extension)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    insert_params = (file_name, file_id, user_id, guild_id,channel_id, content, extension)
            else:
                insert_query = f"""
                    INSERT INTO {table_name} (file_name, file_id, user_id, content, extension)
                    VALUES (%s, %s, %s, %s)
                """
                insert_params = (file_name, file_id, user_id, content, extension)
            
            self.execute_query(insert_query, *insert_params)
            logger.info(f"Inserted file {file_id, user_id}, {file_name}")

    def upload_attachment_file(self,file_name,user_id,file_content,extension,guild_id,channel_id):
        self.upload_file(file_name,FileType.ATTACHMENT,file_content,extension,guild_id,channel_id,user_id=user_id)
        
    def upload_emoji_file(self,file_name,user_id,file_content,extension,guild_id):
        self.upload_file(file_name,FileType.EMOJI,file_content,extension,guild_id,user_id=user_id)   
        
    def upload_profile_file(self,user_id,file_content,extension):
        self.upload_file(user_id,FileType.PROFILE,file_content,extension)
    
    def upload_guild_file(self,file_name,user_id,file_content,extension,guild_id):
        self.upload_file(file_name,FileType.GUILDIMG,file_content,extension,guild_id,user_id=user_id,is_guild_image=True)
                
    def remove_file(self, file_id, file_type):
        table_name = self.get_table_name(file_type)
        
        check_query = f"SELECT COUNT(*) FROM {table_name} WHERE file_id = %s"
        check_params = (file_id,)
        result = self.fetch_single(check_query, check_params)
        file_exists = result[0] > 0 if result else False
        
        if file_exists:
            delete_query = f"DELETE FROM {table_name} WHERE file_id = %s"
            delete_params = (file_id,)
            self.execute_query(delete_query, delete_params)
            logger.info(f"Deleted file {file_id} from table {table_name}.")
        else:
            logger.info(f"File {file_id} does not exist in table {table_name}, nothing to remove.")


    def remove_attachment_file(self,file_id):
        self.remove_file(file_id,FileType.ATTACHMENT)
        
    def remove_emoji_file(self,file_id):
        self.remove_file(file_id,FileType.EMOJI)   
        
    def remove_profile_file(self,file_id):
        self.remove_file(file_id,FileType.PROFILE)
        
    def remove_guild_image(self,guild_id):
        self.remove_file(guild_id,FileType.GUILDIMG)

    def remove_channel(self,guild_id,channel_id):
        self.execute_query(f'DELETE FROM {self.get_table_name(FileType.ATTACHMENT)} WHERE guild_id =%s AND channel_id =%s',guild_id,channel_id)
        
    def remove_guild_files(self,guild_id,is_guild_uploaded_image):
        if is_guild_uploaded_image:
            self.remove_file(guild_id,FileType.GUILDIMG)
        self.execute_query(f'DELETE FROM {self.get_table_name(FileType.ATTACHMENT)} WHERE guild_id =%s',guild_id,)
        self.execute_query(f'DELETE FROM {self.get_table_name(FileType.EMOJI)} WHERE guild_id =%s',guild_id,)

    def get_guild_files(self,guild_id):
        return self.fetch_multiple('SELECT COUNT(*) FROM AttachmentsTable WHERE guild_id =%s',(guild_id,))
        
    def retrieve_file(self,file_id,_filetype):
        try:
            file_id = str(file_id)
            tablename = self.get_table_name(_filetype)
            query = f"SELECT file_name, content, extension FROM {tablename} WHERE file_id = %s"
            _file = self.fetch_single(query, (file_id,file_id))
            if _file:
                file_name, content, extension = _file
                file_stream = BytesIO(content)
                return file_name,file_stream
        except Exception as e:
            logger.info(e)

        
            
    def retrieve_profile_file(self,file_id):
        return self.retrieve_file(file_id,FileType.PROFILE)
        
    def retrieve_attachment_file(self,file_id):
        return self.retrieve_file(file_id,FileType.ATTACHMENT)
    def retrieve_emoji_file(self,file_id):
        return self.retrieve_file(file_id,FileType.EMOJI)
        
    def retrieve_guild_file(self,file_id):
        return self.retrieve_file(file_id,FileType.GUILDIMG)
        
        