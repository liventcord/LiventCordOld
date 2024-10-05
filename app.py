from flask import Flask, render_template, request, jsonify, send_file,redirect, url_for,session, make_response,Response,stream_with_context
from flask_socketio import SocketIO, emit
from flask_httpauth import HTTPBasicAuth
from uuid import uuid4
from datetime import datetime,timedelta
from db_classes.emit_manager import EmitManager
from db_classes.db_handler import friends_manager,guild_manager,users_manager,email_manager,files_manager,direct_messages_manager,GuildMessagesManager,redis_manager
from utils.utils import create_random_id,is_using_pg,logger,Message,datetime_to_string
from pytz import utc as UTC
from werkzeug.utils import secure_filename
from sqlite3 import IntegrityError
from io import BytesIO
import os,json,signal,wave,time,requests
from limiter import Limiter
if is_using_pg:
    from db_classes.db_handler import postgres_manager

    
def abort(num):
    return num
isRateLimiting = False

project_path = os.path.dirname(os.path.realpath(__file__))

USERNAME = os.getenv('ADMIN_USERNAME')
PASSWORD = os.getenv('ADMIN_PASSWORD')


print("Should emit when user joins/leaves guild")
print("Should emit when friend accepts/denies request")
print("Should emit when friend sends add request")
print("Should emit when friend removes")
print("Only emit if user has no hidden profile")
    
app = Flask(__name__,static_url_path='/static')
SECRET = os.getenv('FLASKSECRET_KEY')
if not SECRET:
    print("Env secret key is not set.")
    SECRET = '1NCVJVYXDOS213DSFZ*,-&2'
app.config['SECRET_KEY'] = SECRET
app.config['MAX_CONTENT_LENGTH'] = 5000 * 1024 * 1024 
app.config['UPLOADED_PHOTOS_DEST'] = 'uploads'
app.config['SESSION_COOKIE_NAME'] = 'session_id'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.permanent_session_lifetime = timedelta(days=7)


socketio = SocketIO(app,async_mode='threading', ping_timeout=60, ping_interval=20,cors_allowed_origins="*")
auth = HTTPBasicAuth()


emit_manager = EmitManager(users_manager,guild_manager,friends_manager,redis_manager,socketio)

limiter = Limiter(redis_manager)
limit = limiter.limit
                                               
@app.route('/emojis', methods=['GET'])
def get_emojis():
    with open('emoji.json', 'r', encoding='utf-8') as f:
        emojis = json.load(f)
    return jsonify(emojis)




#@app.route('/shutdown', methods=['GET'])
#@auth.login_required
#def shutdown():
#    os.kill(os.getpid(), signal.SIGINT)
 
@socketio.on('connect')
def handle_connect():
    result = get_user_id(True)
    if result is None: return

    user_id, user_name, user_email = result
    if not user_id or not user_name: return

    redis_manager.add_user_with_sid(user_id, request.sid, {'user_name': user_name, 'user_email': user_email})
    redis_manager.update_sid_timestamp(user_id, request.sid)
    redis_manager.cleanup_stale_sids(users_manager)
    emit_manager.emit_user_activity(user_id,True)


@socketio.on('disconnect')
def handle_disconnect():
    user_id = get_user_id()
    if not user_id: return
    
    if len(redis_manager.get_sids(user_id,users_manager)) <= 0:
        redis_manager.remove_user_sid(user_id, request.sid)
        users_manager.db_update_user_last_login(user_id)
        redis_manager.remove_from_connected_users(user_id)
        emit_manager.emit_user_activity(user_id,False)
    redis_manager.cleanup_stale_sids(users_manager)
        
def handle_ping():
    user_id = get_user_id()
    if user_id is None: return
    redis_manager.update_sid_timestamp(user_id, request.sid)
    redis_manager.cleanup_stale_sids(users_manager)

    
@socketio.on('keep-alive')
def keep_alive():
    handle_ping()

guild_messages_managers = {}

def get_guild_messages_manager(guild_id):
    if guild_id not in guild_messages_managers:
        guild_messages_managers[guild_id] = GuildMessagesManager(guild_id)
    return guild_messages_managers[guild_id]



def get_common_data(email,user_id):
    nickname,discriminator = users_manager.db_get_nick_discriminator_from_email(email)
    guilds_data = guild_manager.get_users_guilds_data(user_id)
    masked_email = email_manager.mask_email(email)
    return nickname, discriminator, guilds_data, masked_email

@app.route('/download', methods=['GET', 'POST'])
def download_page():
    path = os.path.join(project_path, "templates", "download.html")
    return send_file(path)
@app.route('/test', methods=['GET'])
def test_page():
    path = os.path.join(project_path, "templates", "test.html")
    return send_file(path)



@app.route('/', methods=['GET', 'POST'])
def main_page():
    return render_template('newdc.html')
    
@app.route('/app', methods=['GET', 'POST'])
def app_main_page():
    return redirect(url_for('me_page'))

@app.route('/app/<path:subpath>', methods=['GET', 'POST'])
def app_subpathmain_page(subpath):
    return redirect(url_for('me_page'))

@app.route('/channels', methods=['GET'])
def channels_page():  
    return redirect('/channels/@me')
@app.route('/channels/@me', methods=['GET'])
def me_page():  
    return get_app_page()
@app.route('/channels/@me/<friend_id>', methods=['GET'])
def friends_page(friend_id):
    user_id = get_user_id()
    if  not friend_id or not user_id: return redirect('/channels/@me')
    
    if not friends_manager.is_friend_request_existing(user_id,friend_id):
        return redirect('/channels/@me')

    return get_app_page(friend_id=friend_id)

@app.route('/channels/<guild_id>/<channel_id>', methods=['GET'])
def app_page(guild_id, channel_id):
    user_id = get_user_id()
    guild_id = str(guild_id)
    channel_id = str(channel_id)
    if  not user_id or not guild_id or not  channel_id: return redirect('/channels/@me')
    
    if not guild_manager.check_guild_channel_existence(guild_id, channel_id) or not guild_manager.check_users_guild(guild_id, user_id):
        return redirect('/channels/@me')

    guild_name = get_guild_name(guild_id)
    author_id = guild_manager.get_author_id(guild_id)
    return get_app_page(guild_id=guild_id,channel_id=channel_id,guild_name=guild_name,author_id=author_id)


def get_app_page(friend_id=None,guild_id=None, channel_id=None,guild_name=None,author_id=None):
    user_id, user_name, email = get_user_id(isNick=True)
    if not email: return redirect(url_for('login_page'))
    nickname, discriminator, guilds_data, maskedemail = get_common_data(email,user_id)
    
    friend_html_path = os.path.join(app.root_path, 'templates', 'friend.html')
    with open(friend_html_path, 'r') as file: friend_html = file.read()
        
    online_users = redis_manager.get_online_users(users_manager)
    friends_status = friends_manager.get_users_friends_status(user_id,'',online_users)
    typing_users = json.dumps(get_users_typing_to(user_id))
    dm_users_ids = friends_manager.get_users_dm(user_id)
    friend_ids = friends_manager.db_get_friend_ids(user_id)
    dm_users_info = {}
    if dm_users_ids:
        user_data_list = friends_manager.db_get_friends_raw(user_id, dm_users_ids)
        if user_data_list:
            for user_data in user_data_list:
                friends_manager.insert_values(user_data, online_users, dm_users_info)
    dm_users_info = json.dumps(dm_users_info)
    blocked_users = friends_manager.get_blocked_users(user_id)
    shared_guilds_map = guild_manager.get_shared_guilds_map(user_id,friend_ids)
    
    context = {
        'user_name': nickname,
        'user_discriminator' : discriminator,
        'email': email,
        'masked_email': maskedemail,
        'guilds': json.dumps(guilds_data),
        'user_id': user_id,
        'message_readen' : users_manager.get_last_read_datetimes(redis_manager, user_id),
        'permissions_map' : guild_manager.get_permissions_map(user_id),
        'friends_status' : json.dumps(friends_status),
        'typing_users' : typing_users,
        'dm_users' : dm_users_info,
        'blocked_users' : blocked_users,
        'shared_guilds_map' : shared_guilds_map
    }
    def is_user_blocked(user_id, friend_id):
        return friend_id in blocked_users if blocked_users else False
    if guild_id and channel_id and guild_name and author_id:
        context['guild_id'] = guild_id
        context['channel_id'] = channel_id
        context['guild_name'] = guild_name
        context['author_id'] = author_id
        
    if friend_id:
        context['friend_id'] = friend_id
        friendname,frienddiscriminator = users_manager.db_get_user_discriminator_name(friend_id)
        context['friend_discriminator'] = frienddiscriminator
        context['friend_name'] = friendname
        context['friend_blocked'] = is_user_blocked(user_id, friend_id)

    index = render_template('index.html', **context)
    
    combined_html = friend_html + index
    return combined_html





@auth.verify_password
def verify_password(username, password):
    return username == USERNAME and password == PASSWORD

@app.route('/panel/users')
@auth.login_required
def users():
    online_users = redis_manager.get_online_users(users_manager)
    users_info = users_manager.db_get_users_info(online_users)
    return render_template('users.html', users=users_info)


domain1 = 'liventcord.serveo.net'
domain2 = 'liventcord.loophole.site'

domain1_active = True
domain2_active = True

@app.route('/check_domains', methods=['GET'])
def check_domains():
    response = {
        'liventcord.serveo.net': domain1_active,
        'liventcord.loophole.site': domain2_active
    }

    return jsonify(response)

        



@app.route('/connected_users', methods=['GET'])
@auth.login_required
def connected_users():
    redis_manager.cleanup_stale_sids(users_manager)
    users_dict = redis_manager.get_redis_users(users_manager)
    online_users = redis_manager.get_online_users(users_manager)
    
    sid_timestamps = redis_manager.get_all_sids_timestamps()

    return jsonify({'connected_users': users_dict ,'online_users' : online_users, 'sid_timestamps' : sid_timestamps})



@app.route('/updateUsersForAdmin', methods=['POST'])
def update_users_for_admin():
    auth_data = request.get_json()
    if 'password' in auth_data and auth_data['password'] == 'SDHUFH217YEJWDR217YUSDFH2CJBDF12731':
        online_users = redis_manager.get_online_users(users_manager)
        users_status = users_manager.db_get_users_for_status_admin_update(online_users)
        return jsonify(users_status)
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/create_guild', methods=['POST'])
@limit(1)
def create_guild():
    user_id = get_user_id()
    if not user_id:  return jsonify({'error': 'User session expired'}), 401
    guild_name = request.form.get('guild_name')
    guild_photo = request.files.get('photo')

    if not guild_name:  return jsonify({'error': 'Guild name is required'}), 400

    if type(guild_name) or len(guild_name) > 50 != str: return jsonify({'error': 'Invalid guild name'})

    is_guild_uploaded_img = True if guild_photo else False
    random_guild_id = create_random_id()
    new_channel_id = guild_manager.create_guild(new_guild_name, user_id, random_guild_id, is_guild_uploaded_img, users_manager)

    if is_guild_uploaded_img:
        try:
            if is_using_pg:
                postgres_manager.upload_guild_file(random_guild_id,guild_photo.read(),'png',random_guild_id)
            else:
                files_manager.upload_guild_file(project_path,guild_photo.read(), 'png', random_guild_id)
        except Exception as e:
            logger.exception(e)


    redis_manager.update_redis_guilds(guild_manager)
    emit_manager.emit_guilds(user_id)

    return jsonify({'new_guild_id':random_guild_id,'new_channel_id':new_channel_id,'new_guild_name':new_guild_name}), 200



def emit_deleted_guilds(guild_id):
    users_dict = redis_manager.get_redis_users(users_manager)
    users = guild_manager.get_guild_users_base(guild_id)
    
    for _id, details in users_dict.items():
        if _id in users:
            for sid in details["sids"]:
                socketio.emit('deleted_guild',  {'guild_id' : guild_id, 'success' : True}, to=sid)
                    
                
                
@socketio.on('delete_guild')
@limit(1)
def delete_guild(guild_id):
    user_id = get_user_id()
    if not user_id:  return abort(403)
    if not guild_id:  return
    if not guild_manager.does_guild_exists(guild_id) : return
    if not guild_manager.can_user_delete_guild(user_id, guild_id): 
        socketio.emit('deleted_guild',{'success' : False})
        return
    
    emit_deleted_guilds(guild_id)
    
    is_guild_uploaded_image = guild_manager.did_guild_upload_image(guild_id)

    if is_using_pg:
        postgres_manager.remove_guild_files(guild_id,is_guild_uploaded_image)
    else:
        files_manager.remove_guild_files(project_path,'png', guild_id)

    messsages_manager = get_guild_messages_manager(guild_id)
    messsages_manager.delete_all_from_db()
    guild_manager.delete_guild(guild_id)
    
    redis_manager.update_redis_guilds(guild_manager)
    
    logger.info(f"User {user_id} has deleted guild {guild_id}")

def generate_reset_token(email):
    token = str(uuid4())
    session['reset_token'] = token
    session['reset_email'] = email
    return token

def origin_is_trusted(origin):
    trusted_origins = ['https://liventcord.loophole.site','https://liventcord.serveo.net']#,'http://localhost'
    return origin in trusted_origins



@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        domain = request.origin
        if not origin_is_trusted(domain):
            return jsonify({'error': 'Invalid origin'}), 403
        email = request.form.get('email')
        if not email_manager.validate_email(email):
            return jsonify({'error': 'Invalid email'}), 400

        user = users_manager.db_get_user_id(email)
        if user:
            if email_manager.email_limit_reached(email):
                return jsonify({'error': 'Email send limit reached'}), 429
            token = generate_reset_token(email)
            email_manager.send_password_reset_email(email, token, domain,users_manager)
            email_manager.log_email_sent(email)
            return "200"
        else:
            return jsonify({'error': 'User not found'}), 404
    return render_template('4042.html')




@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if 'reset_token' in session and session['reset_token'] == token:
        if request.method == 'GET':
            if token:
                return render_template('reset_password.html', token=token), 200
            else:
                return render_template('reset_password.html'), 200
        if request.method == 'POST':
            new_password = request.form.get('new_password')
            if not new_password:
                return jsonify({'error': 'Şifre geçersiz!'}), 400
            users_manager.db_reset_password(new_password, session['reset_email'])
            session.pop('reset_token')
            session.pop('reset_email')
            return jsonify({'message': 'Şifre Başarıyla Değiştirildi'}), 200
    else:
        return jsonify({'error': 'Geçersiz veya süresi dolmuş token'}), 400
    
    
def get_guild_name(guild_id):
    guilds_cache = redis_manager.get_from_redis_dict('guilds_cache')
    for entry in guilds_cache:
        if entry[0] == guild_id:
            return entry[1]

def open_session(request):
    session_id = request.cookies.get('session_id')
    if not session_id:
        session_id = str(uuid4())
        session['session_id'] = session_id
        session.permanent = True 
        return session_id, False  
    return session_id, True 

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('me_page'))

    path = os.path.join(project_path, "templates", "login.html")
    return send_file(path)
    
@app.route('/auth/login', methods=['POST'])
def login_auth():
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not email or not password:
        response1 = jsonify({'message': 'Authentication failed!'})
        response1.status_code = 401
        return response1
    
    if email_manager.is_length_invalid(email) or not email_manager.validate_email(email):
        return jsonify({"message": "E posta geçersiz"}), 400
    

    if email_manager.is_length_invalid(password):
        return jsonify({"message": "Şifre geçersiz"}), 400

        
    user = users_manager.db_authenticate(email, password)
    
    if user:
        session_id, is_session_open = open_session(request)
        user_id = users_manager.db_get_user_id(email)
        session['user_email'] = email  
        session['user_id'] = user_id

        session.permanent = True
        

        if not is_session_open:
            response = make_response(redirect(url_for('me_page')))
            response.set_cookie('session_id', session_id)
            return response
        else:
            return redirect(url_for('me_page'))
    else:
        response = jsonify({'message': 'Authentication failed!'})
        response.status_code = 401
        return response

@app.route('/auth/check', methods=['GET'])
def check_auth():

    session_id = request.cookies.get('session_id')
    if 'session_id' not in session or session['session_id'] != session_id:
        return jsonify({'error': 'Unauthorized'}), 401

    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not authenticated'}), 401

    user = session['user_email']
    
    if user:
        return jsonify({'message': f'Authenticated as {user["name"]}'})
    else:
        return jsonify({'error': 'User not found'}), 404
    
@app.route('/get_nick_discriminator', methods=['POST'])
def isnickunique():
    nickname = request.form.get('nick')
    if nickname is None or nickname.strip() == '':
        return jsonify({'error': 'Invalid parameters'}), 400
    is_unique = users_manager.is_nick_unique(nickname)
    
    random_discriminators = redis_manager.get_from_redis_dict('random_discriminators')
    if nickname not in random_discriminators :
        random_discriminators[nickname] = users_manager.create_discriminator(nickname)
        redis_manager.set_to_redis('random_discriminators',random_discriminators)
        
    
    if is_unique:
        return jsonify({'result' : '#0000', 'nick' : nickname}), 200
    else:
        return jsonify({'result' : f"#{random_discriminators[nickname]}", 'nick' : nickname}), 200
    
@app.route('/auth/register', methods=['POST'])
def register_auth():
    email = request.form.get('email')
    password = request.form.get('password')
    nickname = request.form.get('nick')
    
    if len(nickname) > 32 or len(nickname) == 0:
        return jsonify({"Kullanıcı adı geçersiz, 1 ile 32 karakter arasında olmalıdır"}, 400)
    if len(password) > 20 or len(password) == 0:
        return jsonify({"Şifre geçersiz, 1 ile 20 karakter arasında olmalıdır"}, 400)
    if len(email) > 240 or len(email) == 0:
        return jsonify({"E-posta geçersiz, 1 ile 240 karakter arasında olmalıdır"}, 400)

    if not email_manager.validate_registration_parameters(email, password, nickname):
        return jsonify({'error': 'Invalid parameters'}, 400)

    if not email_manager.validate_email(email):
        return jsonify({'error': 'Invalid email'}, 400)

    existing_user = users_manager.db_get_user_id(email)

    if existing_user:
        response = jsonify({'error': 'Email already exists'}, 409)
        return response
    else:
        logger.info(f"Creating new user: {email}, {nickname}")
        try:
            random_discriminators = redis_manager.get_from_redis_dict('random_discriminators')
            discriminator = random_discriminators[nickname] if nickname in random_discriminators else None
            users_manager.db_add_new_user(create_random_id(), email, password, nickname,discriminator)
            if nickname in random_discriminators:
                del random_discriminators[nickname]
                redis_manager.set_to_redis('random_discriminators',random_discriminators)
            return jsonify({'message': 'Registration successful'}, 200)
        except IntegrityError:
            return jsonify({'error': 'Email already exists'}, 409)



@app.route('/checkforlogin')
def checkforlogin():
    if 'user_email' in session:
        return redirect(url_for('me_page')) 
    return redirect(f"/login")

@app.route('/auth/logout',methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@socketio.on('get_bulk_reply')
def get_bulk_reply(data):
    user_id = get_user_id()
    if not user_id: 
        return jsonify({'error': 'Unauthorized'}), 401

    requested_ids = data.get('ids')
    guild_id = str(data.get('guild_id'))
    channel_id = str(data.get('channel_id'))

    if not channel_id or not guild_id or not requested_ids:
        return jsonify({'error': 'Invalid Request'}), 400
    
    if not guild_manager.check_users_guild(guild_id, user_id):
        return jsonify({'error': 'Access denied'}), 403
    
    messages_manager = get_guild_messages_manager(guild_id)
    bulk_replies = messages_manager.db_get_bulk_reply(requested_ids, channel_id)

    # Convert datetime objects in bulk_replies to strings
    bulk_replies = datetime_to_string(bulk_replies)

    emit('bulk_reply_response', {'bulk_replies': bulk_replies})

@socketio.on('get_message_date')
@limit(30)
def get_message_date(data):
    user_id = get_user_id()
    guild_id = str(data.get('guild_id'))
    message_id = str(data.get('message_id'))
    channel_id = str(data.get('channel_id'))
    if not user_id or not guild_id or not message_id or not channel_id: return
    if not guild_manager.check_users_guild(guild_id,user_id): return
    messages_manager = get_guild_messages_manager(guild_id)
    message_date = messages_manager.db_get_message_date(channel_id, message_id)
    if message_date:
        emit('message_date_response', {'message_id': message_id, 'message_date' : message_date})

    
    

    
@app.route('/messagediscordbot', methods=['POST'])
def message_from_discord():
    try:
        data = request.json
        password = data.get('password')
        if password != '281354LC' : return '403'
        if 'guild_id' not in data:
            return jsonify({'response': 'No guildprovided in request data.'}), 400
        guild_id = data.get('guild_id')
        channel_id = data.get('channel_id')
        random_id = create_random_id()
        #logger.info("Message from Discord bot arrived! Sender: {}, Content: {}, Channel: {}, Date: {}".format(
        #    data.get('user_id'), data.get('content'), channel_id, data.get('date')))
        message_to_emit = {
            'message_id': random_id,
            'user_id' : data.get('user_id'),
            'content': data['content'],
            'channel_id': channel_id,
            'date': data.get('date'),
            'attachment_urls': data.get('attachment_urls'),
            'reply_to_id': None,
            'guild_id': guild_id,
            'last_edited': None,
            'reaction_emojis_ids' : None
        }
        emit_manager.emit_to_guild(guild_id,'guild_message',message_to_emit)
        message_to_emit.pop('guild_id')
        messages_manager = get_guild_messages_manager(guild_id)
        messages_manager.save_message_to_db(**message_to_emit)
        return jsonify({'response': 'ok'}), 200
    except Exception as e:
        logger.exception(str(e))



@app.route('/attachments/<path:attachment_path>', methods=['GET'])
def attachments_route(attachment_path):
    if not attachment_path:   return abort(400)  
    cached_data = redis_manager.r.get(f'attachment:{attachment_path}')
    if cached_data:
        return send_file(BytesIO(cached_data), mimetype='image/png')
    if not is_using_pg:
        path = files_manager.get_file_path("attachments", attachment_path)
        return files_manager.send_file_or_default(path, files_manager.get_default_image_path('attachments'))
    
    file_data = postgres_manager.retrieve_attachment_file(attachment_path)
    if file_data:
        redis_manager.r.set(f'attachment:{attachment_path}', file_data[1].getvalue())
    return files_manager.send_file_from_db(file_data, attachment_path, "attachments", request.environ)



@app.route('/profiles/<path:profile_path>', methods=['GET'])
def profiles_route(profile_path):
    if not profile_path:
        return abort(400)

    profile_id = os.path.splitext(profile_path)[0]  
    
    cached_data = redis_manager.r.get(f'profile:{profile_id}')
    if cached_data:
        return send_file(BytesIO(cached_data), mimetype='image/png')

    if not is_using_pg:
        path = files_manager.get_file_path("profiles", profile_path)
        return files_manager.send_file_or_default(path, files_manager.get_default_image_path('profiles'))

    file_data = postgres_manager.retrieve_profile_file(profile_id)
    if file_data:
        redis_manager.r.set(f'profile:{profile_id}', file_data[1].getvalue())
    return files_manager.send_file_from_db(file_data, profile_id, "profiles", request.environ)



@app.route('/guilds/<path:guild_path>', methods=['GET'])
def guilds_route(guild_path):
    if not guild_path:
        return abort(400)
    
    guild_id = guild_path.split('.')[0]  
    
    cached_data = redis_manager.r.get(f'guild:{guild_id}')
    if cached_data:
        return send_file(BytesIO(cached_data), mimetype='image/png')

    if not is_using_pg:
        path = files_manager.get_file_path("guild_avatars", guild_id)
        return files_manager.send_file_or_default(path, files_manager.get_default_image_path('guilds'))

    file_data = postgres_manager.retrieve_guild_file(guild_id)
    if file_data:
        redis_manager.r.set(f'guild:{guild_id}', file_data[1].getvalue())
    return files_manager.send_file_from_db(file_data, guild_id, "guilds", request.environ)



@app.route('/delete_profile_pic', methods=['POST'])
@limit(5)
def delete_profile_pic():
    user_id = get_user_id()
    if not user_id: return jsonify({'error': 'Unauthorized'}), 401
    postgres_manager.remove_profile_file(user_id)
    redis_manager.remove_cache('profile', user_id)
    return jsonify({'message': 'Profile picture deleted successfully'}), 200

@socketio.on('remove_guild_image')
def remove_guild_image(data):
    user_id = get_user_id()
    guild_id = data.get('guild_id')
    
    if not guild_manager.can_user_upload_guild_image(guild_id,user_id):  return
    postgres_manager.remove_guild_image(guild_id)
    redis_manager.remove_cache('guild', user_id)
    guild_manager.update_guild_image_boolean(guild_id,False)
    emit_manager.emit_guild_image_to_guild(True,guild_id)
    return jsonify({'message': 'Guild image uploaded successfully'}), 200
    



@app.route('/upload_img', methods=['POST'])
@limit(3)
def upload_profile_pic():
    user_id = get_user_id()
    if not user_id: return jsonify({'error': 'Unauthorized'}), 401

    is_guild = bool(request.form.get('guild_id'))
    if 'photo' not in request.files: return jsonify({'error': 'Invalid Request'}), 400
    if not 'content-length' in request.headers : return jsonify({'error': 'Invalid Request'}), 400

    file = request.files['photo']
    if not file.mimetype.startswith('image/'): return jsonify({'error': 'Invalid file type. Only image files are allowed.'}), 400
   
    if int(request.headers['content-length']) > 8 * 1024 * 1024:
        return jsonify({'error': f'File size exceeds {8} MB limit'}), 413

    filename = secure_filename(file.filename)
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    photo = file.read()

    try:
        if is_guild:
            
            if not guild_manager.can_user_upload_guild_image(guild_id,user_id):  return jsonify({'error': 'Access denied'}), 403
            postgres_manager.upload_guild_file(guild_id,photo,'png',guild_id)
            guild_manager.update_guild_image_boolean(guild_id,True)
            emit_manager.emit_guild_image_to_guild(False,guild_id)
            return jsonify({'message': 'Guild image uploaded successfully'}), 200
        else:
            redis_manager.update_cache('profile', user_id, photo)
            if not is_using_pg:
                files_manager.upload_profile_file("profiles", photo, extension, user_id)
            else:
                postgres_manager.upload_profile_file(user_id, photo, extension)
            emit_manager.emit_profile_to_guild_and_friends(user_id)
            return jsonify({'message': 'Profile picture uploaded successfully'}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({'error': 'Upload failed'}), 400
        




@app.errorhandler(404)
def handle_bad_request(e):
    return render_template('4042.html')

def get_users_typing_to(user_id):
    users_typing_to_user = []
    writing_dm_users = redis_manager.get_from_redis_list('writing_dm_users')
    for typing_user, typing_to_list in writing_dm_users.items():
        if user_id in typing_to_list:
            users_typing_to_user.append(typing_user)

    return users_typing_to_user

user_typing_timestamps = {}

@socketio.on('start_writing')
def start_writing(data):
    user_id = get_user_id()
    guild_id = data.get('guild_id')
    channel_id = data.get('channel_id')
    user_typing_timestamps = redis_manager.get_from_redis_dict('user_typing_timestamps')
    is_dm = data.get('is_dm')
    
    current_time = time.time()
    last_typing_time = user_typing_timestamps.get(user_id, 0)

    if current_time - last_typing_time > 1: 
        user_typing_timestamps[user_id] = current_time
        redis_manager.set_to_redis_dict('user_typing_timestamp',user_typing_timestamps)

        if is_dm:
            writing_dm_users = redis_manager.get_from_redis_dict('writing_dm_users')
            if user_id not in writing_dm_users:
                writing_dm_users[user_id] = []
            if channel_id not in writing_dm_users[user_id]:
                writing_dm_users[user_id].append(channel_id)
            redis_manager.set_to_redis_list('writing_dm_users', writing_dm_users)
        else:
            if not user_id or not guild_id or not channel_id or not guild_manager.check_users_guild(guild_id, user_id):
                return
            if not guild_manager.check_guild_channel_existence(guild_id, channel_id):
                return
            writing_users = redis_manager.get_from_redis_dict('writing_users')
            if guild_id not in writing_users:
                writing_users[guild_id] = {}
            if channel_id not in writing_users[guild_id]:
                writing_users[guild_id][channel_id] = []
            redis_manager.set_to_redis_list('writing_users', writing_users)
            payload = {
                'user_id': user_id,
                'channel_id': channel_id,
                'guild_id': guild_id
            }
            emit_manager.emit_to_guild(guild_id, 'user_writing', payload)
        

@socketio.on('join_voice_channel')
@limit(10)
def join_voice_channel(data):
    user_id = get_user_id()
    guild_id = data.get('guild_id')
    channel_id = data.get('channel_id')
    if not user_id or not guild_id or not channel_id or not guild_manager.check_users_guild(guild_id, user_id): return
    if not guild_manager.check_guild_channel_existence(guild_id, channel_id): return
    
    users_in_voice = redis_manager.get_from_redis_dict('voice_users')
    
    if guild_id not in users_in_voice:
        users_in_voice[guild_id] = {}
    
    if channel_id not in users_in_voice[guild_id]:
        users_in_voice[guild_id][channel_id] = []
    
    if not users_in_voice[guild_id][channel_id]:
        users_in_voice[guild_id][channel_id].append(user_id)
    redis_manager.set_to_redis_list('voice_users', users_in_voice)
    
    response = {
        'guild_id' : guild_id,
        'channel_id' : channel_id,
        'users_list' : users_in_voice[guild_id][channel_id]
    }
    emit('voice_users_response', response, broadcast=False)
    emit_manager.emit_to_guild(guild_id,'voice_user_joined',user_id)


@socketio.on('leave_voice_channel')
@limit(10)
def leave_voice_channel(data):
    user_id = get_user_id()
    guild_id = data.get('guild_id')
    channel_id = data.get('channel_id')
    if not user_id or not guild_id or not channel_id or not guild_manager.check_users_guild(guild_id, user_id): return
    if not guild_manager.check_guild_channel_existence(guild_id, channel_id): return
    
    users_in_voice = redis_manager.get_from_redis_dict('voice_users')
    
    if guild_id in users_in_voice and channel_id in users_in_voice[guild_id] and user_id in users_in_voice[guild_id][channel_id]:
        users_in_voice[guild_id][channel_id].remove(user_id)
        redis_manager.set_to_redis_list('voice_users', users_in_voice)
    
    response = users_in_voice.get(guild_id, {}).get(channel_id, [])
    emit('voice_users_response', response, broadcast=False)


@socketio.on('get_voice_users')
@limit(10)
def get_users_voice(guild_id, channel_id):
    user_id = get_user_id()
    if not user_id or not guild_id or not channel_id or not guild_manager.check_users_guild(guild_id, user_id): return
    if not guild_manager.check_guild_channel_existence(guild_id, channel_id): return
    
    users_in_voice = redis_manager.get_from_redis_dict('voice_users')
    
    response = users_in_voice.get(guild_id, {}).get(channel_id, [])
    emit('voice_users_response', response, broadcast=False)

    
    


@socketio.on('create_channel')
@limit(10)
def create_channel(data):
    user_id = get_user_id()
    if not user_id:  return
    channel_name = data.get('channel_name', '').strip()
    guild_id = data.get('guild_id')
    is_text_channel = data.get('is_text_channel')
    if not channel_name or not guild_id:  return
    if not guild_manager.check_users_guild(guild_id,user_id): return
    if not guild_manager.can_user_manage_channel(user_id,guild_id): 
        emit('create_channel_response', {'success':True},broadcast=False)
    
    channel_id = create_random_id()
    guild_manager.create_channel(guild_id,user_id, channel_name,is_text_channel,channel_id=channel_id)
    redis_manager.update_redis_channels(guild_manager)
    emit_manager.emit_to_guild(guild_id,'channel_update',{'type': 'create', 'channel_id' : channel_id, 'channel_name' : channel_name, 'is_text_channel' : is_text_channel})
        
        
@socketio.on('edit_channel')
@limit(10)
def edit_channel(data):
    user_id = get_user_id()
    if not user_id:  return
    
    new_channel_name = data.get('new_channel_name', '').strip()
    guild_id = data.get('guild_id')
    channel_id = data.get('channel_id')
    if not new_channel_name or not guild_id or not channel_id:  return
    if not guild_manager.check_users_guild(guild_id,user_id): return
    
    if not guild_manager.can_user_manage_channel(user_id,guild_id): 
        emit('create_channel_response', {'success':False},broadcast=False)
        return
    if not guild_manager.check_guild_channel_existence(guild_id,channel_id): return
    guild_manager.edit_channel(guild_id,new_channel_name,channel_id)
    redis_manager.update_redis_channels(guild_manager)
    emit_manager.emit_to_guild(guild_id,'channel_update',{'type': 'edit','channel_id': channel_id,'new_channel_name' :new_channel_name,'guild_id' : guild_id})
    
@socketio.on('remove_channel')
@limit(10)
def remove_channel(data):
    user_id = get_user_id()
    if not user_id:  return
    guild_id = data.get('guild_id')
    channel_id = data.get('channel_id')
    if not guild_id or not channel_id:  return
    if not guild_manager.check_users_guild(guild_id,user_id): return
    can_manage_channel = guild_manager.can_user_manage_channel(user_id,guild_id)
    if not can_manage_channel:  return
    if not guild_manager.check_guild_channel_existence(guild_id,channel_id):   return
    if guild_manager.is_channels_low(guild_id): return
    
    guild_manager.remove_channel(guild_id,channel_id)
    postgres_manager.remove_channel(guild_id,channel_id)
    redis_manager.update_redis_channels(guild_manager)
    emit_manager.emit_to_guild(guild_id,'channel_update',{'type': 'remove', 'channel_id' : channel_id,'guild_id' : guild_id})
    
    
    
    
@app.route('/Discord_files/<source>')
def discordfiles(source):
    return send_file(os.path.join(project_path,'Discord_files',source))
    

@app.route('/join-guild/<invite_id>')
def join_to_guild(invite_id):
    
    if not invite_id: return
    user_id = get_user_id()
    
    def has_auth(): 
        return user_id is None or user_id == (None,None,None)

        
    invite_id = str(invite_id)
    details_dict = guild_manager.get_invite_details(invite_id)
    
    if not details_dict: return send_file(os.path.join(project_path,'templates','Discord.html'))
    
    creator_id = details_dict['creator_id']
    guild_id = details_dict['guild_id']
  
    if not guild_manager.does_guild_exists(guild_id): return abort(403)

    creator_name = users_manager.db_get_user_name(creator_id)
    guild_name = get_guild_name(guild_id)
    users_count = guild_manager.get_users_count(guild_id)
    context = {'guild_name' : guild_name, 'creator_name' : creator_name}
    guild_pic_url = f'/guilds/{guild_id}' 


    context = {
        'guild_pic_url': guild_pic_url,
        'creator_name': creator_name,
        'guild_name': guild_name,
        'user_count' : users_count
    }
    
    if has_auth:
        return render_template('guestjoinguild.html', **context)
    else:
        return render_template('joinguild.html', **context)

    

    

@socketio.on('join_to_guild')
@limit(5)   
def join_to_guild(data):
    user_id = get_user_id()
    if not user_id or not data:    return
    invite_id = data.get('invite_id') 
    guild_id,channel_id = guild_manager.get_invites_guild_and_channel(invite_id)
    if not guild_id or not channel_id:
        emit_manager.emit_to_originator(user_id,'join_guild_response',{'success':False})
    result = guild_manager.add_user(guild_id=guild_id, user_id=user_id)
    if result is not False:
        emit_manager.emit_guilds(user_id)
        guild_id,user_id,guild_name,author_id = result
        permsmap = guild_manager.fetch_permissions_for_guild(user_id,guild_id)
        emit_manager.emit_to_originator(user_id,'join_guild_response',{'success':True,'joined_guild_id':guild_id,'joined_guild_channel':channel_id,'joined_guild_name':guild_name,'joined_author_id': author_id,'permissions_map':permsmap})
    else:
        emit_manager.emit_to_originator(user_id,'join_guild_response',{'success':False,'failed_guild_id':guild_id,'failed_guild_channel':channel_id})

    
@socketio.on('leave_from_guild') 
@limit(5)    
def leave_from_guild(guild_id):
    if not guild_id: return
    user_id = get_user_id()
    owner_id = guild_manager.get_owner_id(guild_id)
    if owner_id == user_id:
        logger.warning('Owner attempted to leave guild.')
        return

    if guild_manager.remove_user(guild_id=guild_id, user_id=user_id):
        logger.info(f'User {user_id} has left guild {guild_id}')
        emit_manager.emit_guilds(user_id)
        
@socketio.on('get_users')
@limit(30)
def get_user_list(guild_id):
    if not guild_id: return 
    emit_manager.emit_user_list(request.sid,guild_id)


@socketio.on('get_user_metadata')
@limit(20)
def send_user_metadata(guild_id):
    user_id = get_user_id()
    if not guild_id or not user_id: return
    if not guild_manager.does_guild_exists(guild_id) : return
    user_metadata = guild_manager.get_users_metadata(guild_id,users_manager)
    
    socketio.emit('update_users_metadata', {'users': user_metadata, 'guild_id' : guild_id})
    
@socketio.on('read_message')
@limit(40)
def read_message_event(data):
    user_id = get_user_id()
    if not user_id or not data: return

    channel_id = data.get('channel_id')
    guild_id = data.get('guild_id')
    if not channel_id or not guild_id: return
    
    users_manager.mark_as_read(user_id,channel_id)
    
    payload = users_manager.get_last_read_datetimes(redis_manager, user_id, guild_id)
    emit_manager.emit_to_originator(user_id,'message_readen',payload)

@socketio.on('create_invite')
@limit(2)
def create_new_invite(data):
    return '500'
    user_id = get_user_id()
    if not guild_id or not user_id: return
     
    guild_id = data.get('guild_id')
    channel_id = data.get('channel_id')
    if not guild_id or not channel_id : return
    if not guild_manager.check_guild_channel_existence(guild_id,channel_id): 
        logger.info(f"User {user_id} tried to create an invite for channel {channel_id} which do not exists on the guild.")
        return

    
    can_invite = guild_manager.can_user_invite(user_id,guild_id)
    if can_invite:
        logger.warning(f'User {user_id} has no permission for inviting but he attempted to create invite')
        return

    
    invite_id = guild_manager.create_invite(user_id,guild_id,channel_id)
    
    socketio.emit('invite_response',{'invite_id':invite_id})

    
    
@socketio.on('get_channels')  
def handle_get_channels(guild_id):
    user_id = get_user_id()
    
    if not guild_manager.check_users_guild(guild_id, user_id): return
    
    last_read_datetimes = users_manager.get_last_read_datetimes(redis_manager,user_id, guild_id)
    channels = redis_manager.get_channels_generic(guild_id, last_read_datetimes)

    
    if channels is not None:
        emit('update_channels', {'channels': channels,'guild_id': guild_id},broadcast=False)
   
@socketio.on('set_nick')
@limit(10)   
def set_nick(nick):
    user_id, user_name,user_email = get_user_id(True)

    if user_id and user_email and nick:
        truncated_nick = nick[:32] if len(nick) > 32 else nick
        logger.info(f"User {user_name} with id {user_id} changed nick to: {truncated_nick}")
        isSucceded = users_manager.db_update_user_nickname(user_id, truncated_nick)
        if isSucceded:
            emit_manager.emit_nick_to_friends(user_id,nick)


            
@socketio.on('set_guild_name')
@limit(10)   
def set_guild_name(data):
    
    guild_id = str(data.get('guild_id'))
    new_name = str(data.get('guild_name'))
    
    user_id, user_name,user_email = get_user_id(True)
    if not guild_manager.is_user_author(guild_id,user_id): return
    if user_id  and new_name and guild_id:
        truncated_name = new_name[:32] if len(new_name) > 32 else new_name
        logger.info( f"User {user_name} changed guild {guild_id} to: {truncated_name}")
        guild_manager.update_guild_name(new_name,guild_id)
        emit_manager.emit_guild_name_to_guild(guild_id,new_name)

@socketio.on('get_current_invite_id')
@limit(10)
def get_current_invite_id(data):
    user_id = get_user_id()
    guild_id = str(data.get('guild_id'))
    if not guild_manager.can_user_invite(user_id,guild_id): 
        logger.info(f"User {user_id} tried to get invite id for guild {guild_id} while he does not have invite perms")
        return
    

    invite_ids = guild_manager.get_invite_ids(guild_id)
    
    emit('current_invite_ids_response',{'invite_ids' : invite_ids,'guild_id' : guild_id},broadcast=False)


@socketio.on('add_dm')
def add_user_dm(data):
    user_id = get_user_id()
    if not user_id:  return 
    
    friend_id = data.get('friend_id')
    if not friend_id or not friend_id.isdigit(): return
    
    if not users_manager.db_check_for_user(friend_id): return
    print("added")
    friends_manager.add_user_dm(user_id,friend_id)

@socketio.on('get_history')
def get_history(data):
    user_id = get_user_id()
    if not user_id: return 

    channel_id = str(data.get('channel_id'))
    guild_id = str(data.get('guild_id'))
    is_dm = bool(data.get('is_dm'))
    
    if not channel_id: return 
    if not is_dm:
        if not guild_id: return
        if not guild_manager.check_users_guild(guild_id, user_id): return 

    if is_dm:
        history = direct_messages_manager.get_messages_between_users(user_id, channel_id)
        oldest_message_date = direct_messages_manager.db_get_oldest_message_date(user_id, channel_id)
    else:
        messages_manager = get_guild_messages_manager(guild_id)
        raw_history = messages_manager.db_get_history_from_channel(channel_id)  # Get raw data
        history = [Message(data) for data in raw_history]  # Convert dictionaries to Message instances
        oldest_message_date = messages_manager.db_get_oldest_message_date(channel_id)

    # Convert Message instances to dictionaries, ensuring datetime serialization
    def serialize_message(msg):
        if hasattr(msg, 'to_dict'):
            msg_dict = msg.to_dict()
            # Convert any datetime fields in msg_dict to ISO format
            for key, value in msg_dict.items():
                if isinstance(value, datetime):
                    msg_dict[key] = value.isoformat()  # Convert datetime to ISO format
                elif isinstance(value, list):  # If value is a list, serialize each item
                    msg_dict[key] = [v.isoformat() if isinstance(v, datetime) else v for v in value]
            return msg_dict
        else:
            return msg

    history = [serialize_message(msg) for msg in history]

    # Convert oldest_message_date to ISO format if it's a datetime object
    oldest_message_date = oldest_message_date.isoformat() if isinstance(oldest_message_date, datetime) else oldest_message_date

    emit('history_data_response', {
        'history': history,
        'guild_id': guild_id,
        'channel_id': channel_id,
        'oldest_message_date': oldest_message_date
    }, broadcast=False)
@socketio.on('get_old_messages')
@limit(30)
def get_old_messages(data):
    user_id = get_user_id()
    
    is_dm = bool(data.get('is_dm'))
    if not is_dm:
        guild_id = str(data.get('guild_id'))
    channel_id = str(data.get('channel_id'))
    date_str = str(data.get('date'))
    message_id = data.get('message_id', None)

    if is_dm:
        if not friends_manager.is_friend_request_existing(user_id, channel_id):
            return
    else:
        if not guild_id:
            return
        if not guild_manager.check_users_guild(guild_id, user_id):
            return 
        
    if is_dm:
        raw_history = direct_messages_manager.db_get_old_messages_between_users(user_id, channel_id, date_str, message_id)
        oldest_message_date = direct_messages_manager.db_get_oldest_message_date(user_id, channel_id)
    else:
        messages_manager = get_guild_messages_manager(guild_id)
        raw_history = messages_manager.db_get_old_messages(channel_id, date_str, message_id)
        oldest_message_date = messages_manager.db_get_oldest_message_date(channel_id)

    # Convert dictionaries to Message instances
    history = [Message(data) for data in raw_history]  # Convert raw data to Message instances

    # Convert datetime objects to ISO strings
    history = [msg.to_dict() for msg in history]  # Now we can safely call to_dict()
    oldest_message_date = oldest_message_date.isoformat() if isinstance(oldest_message_date, datetime) else oldest_message_date

    emit('old_messages_response', {
        'history': history,
        'oldest_message_date': oldest_message_date,
        'message_id': message_id
    }, broadcast=False)


def save_attachment_file(file, file_name, guild_id,channel_id,extension,attachment_id):
    if is_using_pg:
        postgres_manager.upload_attachment_file(filename,user_id, file.read(), extension,guild_id,channel_id,file_id)
        return
    uploads_path = os.path.join(project_path, "uploads", "attachments")
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path)
    file_path = os.path.join(uploads_path, file_name + '.' + extension)
    with open(file_path, "wb") as f:
        f.write(file.read())

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    guild_id = request.form.get('guild_id')
    if not guild_id: 
        return jsonify({'error': 'Guild id not provided'})
    channel_id = request.form.get('channel_id')
    if not channel_id: 
        return jsonify({'error': 'Channel id not provided'})
    if file.filename == '':
        return jsonify({'error': 'Empty file name'}), 400
    attachment_id = create_random_id()
    extension = file.filename.split(".")[-1]
    save_attachment_file(file,filename,guild_id,channel_id,extension,attachment_id)
    def create_attachment_urls(ids):
        urls = []
        for idx, _id in enumerate(ids, start=1):
            urls.append(f"/attachments/{_id}")
        return urls
    response_data = {
        'file_name': file.filename,
        'type': file.content_type,
        'attachment_id': attachment_id,
        'attachment_urls': create_attachment_urls([attachment_id])
    }
    return jsonify(response_data), 200



@socketio.on('new_message')
@limit(30)
def handle_message_new(data):
    try:
        user_id = get_user_id()
        if not user_id: return
        if not all(key in data for key in ['content', 'channel_id']): return
        is_dm = bool(data.get('is_dm'))

        content = data['content']
        attachment_urls = data.get('attachment_urls', [])
        
        if not (isinstance(content, str) and content.strip()) and not attachment_urls:
            return


        channel_id = data['channel_id']
        if not channel_id.isdigit(): return
        guild_id = data.get('guild_id') if not is_dm else None
        if is_dm:
            friend_check = friends_manager.check_if_friends(user_id, channel_id)
            if not friend_check:
                guild_check = guild_manager.is_users_sharing_guild(user_id, channel_id)
                if not guild_check: return
        else:
            if not guild_id or not guild_manager.check_users_guild(guild_id, user_id): return
        reply_to_id = data.get('reply_to_id')
        content = data['content']
        attachment_urls = data.get('attachment_urls', [])
        random_id = create_random_id()
        new_date = str(datetime.now(UTC))

        message_to_emit = {
            'message_id': random_id,
            'user_id': user_id,
            'content': content,
            'channel_id': channel_id,
            'date': new_date,
            'attachment_urls': attachment_urls,
            'reply_to_id': reply_to_id,
            'last_edited': None,
            'reaction_emojis_ids': None,
            'is_bot' : False,
            'is_dm': is_dm
        }

        if is_dm:
            message_to_emit.update({
                'sender_id': user_id,
                'receiver_id': channel_id
            })
            emit_manager.emit_to_friend_and_self(user_id, channel_id, 'message', message_to_emit)
            message_to_emit.pop('user_id')
            message_to_emit.pop('channel_id')
        else:
            message_to_emit['guild_id'] = guild_id
            emit_manager.emit_to_guild(guild_id, 'message', message_to_emit)
            message_to_emit.pop('guild_id')

        message_to_emit.pop('is_dm')
        message_to_emit.pop('is_bot')
        messages_manager = get_guild_messages_manager(guild_id) if not is_dm else direct_messages_manager
        
        messages_manager.save_message_to_db(**message_to_emit)

    except Exception as e:
        logger.exception(e)


@socketio.on('search_message')
@limit(20)
def search_message(data):
    pass
    user_id = get_user_id()
    if not user_id or not 'guild_id' in data or not 'message_id' in data or not 'channel_id' in data or not 'is_dm' in data: return
    guild_id = data.get('guild_id')
    searchQuery = data.get('search_query')
    channel_id = data.get('channel_id')
    is_dm = data.get('is_dm')
    if is_dm:
        if not friends_manager.check_if_friends(user_id,channel_id): return
        found_message = messages_manager.search_from_db(searchQuery,channel_id)
    else:
        if not guild_manager.check_users_guild(guild_id, user_id): return
        messages_manager = get_guild_messages_manager(guild_id)
        found_message = messages_manager.search_from_db(searchQuery,channel_id)
    
    return found_message
        
        
@socketio.on('message_delete')
@limit(70)   
def handle_message_delete(data):
    try:
        user_id = get_user_id()
        if not user_id or not 'message_id' in data or not 'channel_id' in data or not 'is_dm' in data:
            return
        guild_id = data.get('guild_id')
        message_id = data.get('message_id')
        channel_id = data.get('channel_id')
        is_dm = data.get('is_dm')
        if is_dm:
            if not friends_manager.check_if_friends(user_id,channel_id): 
                print("Not friends.")

            success = direct_messages_manager.delete_from_db(message_id,user_id,channel_id)
            if success:
                emit_manager.emit_deleted_message_to_friend_self(user_id,channel_id,message_id)
        else:
            if not 'guild_id' in data: return
            if not guild_manager.check_users_guild(guild_id, user_id): return
            messages_manager = get_guild_messages_manager(guild_id)
            success = messages_manager.delete_from_db(message_id,channel_id)
            if success:
                emit_manager.emit_deleted_message_to_guild(guild_id,message_id,channel_id)
    except Exception as e: 
        logger.exception(e)
        
@socketio.on('friend_request_event')
@limit(5)   
def handle_friend_request(event_name, data):
    user_id = get_user_id()
    if not user_id or not data or not event_name: return
    response = friends_manager.handle_friend_request_event(event_name, data,user_id,users_manager,redis_manager)
    emit('friend_request_response', response, broadcast=False)




def save_audio_chunk(audio_bytes):
    path = os.path.join(project_path, "output", "output.wav")
    if os.path.exists(path):
        with wave.open(path, 'rb') as wav_file:
            params = wav_file.getparams()
    else:
        params = (1, 2, 44100, 0, 'NONE', 'not compressed')
    with wave.open(path, 'wb') as wav_file:
        wav_file.setparams(params)
        wav_file.writeframes(audio_bytes)




@socketio.on('audio_data')
def handle_audio(audio_bytes):
    save_audio_chunk(audio_bytes)


@socketio.on('fetch_users_event')
@limit(35)   
def fetch_users_eventt(data):
    request_type = data.get('request_type')
    user_id = get_user_id()
    if not user_id:
        return
    isReqPending = True if request_type == 'pending' else False
    online_users = redis_manager.get_online_users(users_manager)
    users_data = friends_manager.get_users_friends_status(user_id, request_type,online_users)
    emit('users_data_response', {'users': users_data,'isPending':isReqPending}, broadcast=False)
    

def get_user_id(isNick=False):
    user_email = session.get('user_email')
    if not user_email: 
        return None, None, None if isNick else None
    if isNick:
        user_name, user_id = users_manager.db_get_nick_id_from_email(user_email)
        return user_id, user_name,user_email
    else:
        return str(session.get('user_id'))

if __name__ == "__main__":
    PORT = 5005
    DEBUG = True
    redis_manager.update_redis_channels(guild_manager)
    redis_manager.update_redis_guilds(guild_manager)
    socketio.run(app,host='0.0.0.0', port=PORT,allow_unsafe_werkzeug=True,debug=DEBUG,use_reloader=DEBUG)

# sudo uwsgi --socket 0.0.0.0:5005 --protocol=http --enable-threads --buffer-size 65536 -w wsgi:app

# sudo gunicorn -w 2 --threads 100 -b 0.0.0.0:5005 app:app


