from werkzeug.utils import secure_filename,send_file

from flask import jsonify
from utils.utils import create_random_id
from os import path



class FilesManager():
    

    def __init__(self,project_path):

        self.project_path = project_path


    def upload_profile_file(self, project_path,content, extension='png', filename=None):

        if filename is None:

            filename = create_random_id()
        

        filename = secure_filename(f"{filename}.{extension}")
        

        file_path = path.join(project_path,'uploads','profiles', filename)

        with open(file_path, 'wb') as f:

            f.write(content)
        
        return file_path


    def upload_guild_file(self, project_path,content, extension='png', filename=None):

        if filename is None:

            filename = create_random_id()
        

        filename = secure_filename(f"{filename}.{extension}")

        file_path = path.join(self.project_path,'uploads','guild_avatars', filename)

        with open(file_path, 'wb') as f:

            f.write(content)
        
        return file_path
    

    def send_file_from_db(self, file_data,file_name, typeimg,environ):

        if not file_data: return jsonify('404',404)

        filename, stream = file_data

        return send_file(stream, download_name=filename,mimetype='png',environ=environ)

    

    def get_file_path(self, folder, file_name):

        return path.join(self.project_path, "uploads", folder, f"{file_name}.png")
    

    def get_default_image_path(self, image_type):

        if image_type == 'attachments':

            return path.join(self.project_path, 'static', 'images', 'guest.png')

        elif image_type == 'guilds':

            return path.join(self.project_path, 'static', 'images', 'guild_avatars', 'default.png')

        elif image_type == 'profiles':

            return path.join(self.project_path, 'static', 'images', 'guest.png')

        else:

            return None

