from flask import render_template
from db_classes.db_main_class import DatabaseManager
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from utils.utils import logger
import re,smtplib,os

class EmailManager(DatabaseManager):
    def __init__(self):   
        super().__init__('email.db')
        self.SMTP_USER = os.getenv('SMTP_USER')
        self.SMTP_PASS = os.getenv('SMTP_PASS')

    def is_length_invalid(self,s):
        return not 1 <= len(s) <= 128
    
    def email_limit_reached(self,email):
        result = self.fetch_single("SELECT send_count FROM sent_emails WHERE email = ?", (email,))
        return result and result[0] >= 6
    
    def send_password_reset_email(self,email, token,domain,users_manager):

        reset_url = f"{domain}/reset-password/{token}"
        user_name,discriminator = users_manager.db_get_nick_discriminator_from_email(email)
        if not user_name or not discriminator: return
        msg_body = render_template('mail.html', reset_url=reset_url, user_name=user_name, user_discriminator=discriminator)
        msg = MIMEMultipart()
        msg['From'] = self.SMTP_USER
        msg['To'] = email
        msg['Subject'] = "Password Reset Request"
        msg.attach(MIMEText(msg_body, 'html'))

        try:
            smptpdaemon = smtplib.SMTP("smtp.gmail.com", 587)
            smptpdaemon.ehlo()
            smptpdaemon.starttls()
            smptpdaemon.ehlo()
            smptpdaemon.login(self.SMTP_USER, self.SMTP_PASS)
            smptpdaemon.sendmail(self.SMTP_USER, email, msg.as_string())
            smptpdaemon.quit()
            logger.info(f'Email sent successfully to {email}')
        except Exception as e:
            logger.info(f'Failed to send email: {str(e)}')
    

    def log_email_sent(self,email):

        self.execute_query('''INSERT INTO sent_emails (email, sent_time, send_count) 
                    VALUES (?, ?, 1)
                    ON CONFLICT(email) 
                    DO UPDATE SET 
                        sent_time = excluded.sent_time,
                        send_count = sent_emails.send_count + 1''',
                (email, datetime.now()))

    def validate_registration_parameters(self,email, password, nickname):

        if not email or not password or not nickname:
            return False
        if email == '' or password == '' or nickname == '':
            return False
        if len(email) < 6:
            return False
        if len(password) < 3:
            return False
        if len(nickname) < 1:
            return False

        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_pattern, email):
            return False
        return True

    def validate_email(self,email): # Regular expression for basic email validation
        try:
            pattern = re.compile(r'^[\w-]+(\.[\w-]+)*@([\w-]+\.)+[a-zA-Z]{2,7}$')
            return pattern.match(email)
        except Exception:
            return False

    def mask_email(self,email):
        parts = email.split('@')
        if len(parts) != 2:
            return email
        username, domain = parts
        hidden_username = '*' * len(username)
        return f"{hidden_username}@{domain}"