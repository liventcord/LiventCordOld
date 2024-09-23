class User:
    def __init__(self, user_id, email='', password='', nickname='', discriminator='', bot=False, status='offline',
                 description='', created_at=None, last_login=None, verified=False, 
                 location='', language='', phone_number='', social_media_links=None, date_of_birth=None, 
                 hide_profile=False,preferences=None):
        
        self.user_id = user_id
        self.email = email
        self.password = password
        self.nickname = nickname
        self.discriminator = discriminator
        self.bot = bot
        self.status = status
        self.description = description
        self.created_at = created_at
        self.last_login = last_login
        self.verified = verified
        self.location = location
        self.language = language
        self.phone_number = phone_number
        self.social_media_links = social_media_links if social_media_links else []
        self.date_of_birth = date_of_birth
        self.hide_profile = hide_profile
    def is_online(self, online_users):
        return False if self.status == 'invisible' else self.user_id in online_users
            