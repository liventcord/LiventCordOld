from icrawler.builtin import GoogleImageCrawler
from PIL import Image
from io import BytesIO

import shutil,os,requests,time,random,asyncio,discord
from discord import Embed
import sqlite3,aiosqlite,re
from datetime import datetime

from pytube import Search
from requests.exceptions import RequestException
from discord.ext import commands


BOT_SELF_ID = 1172483863331737611
MAX_IMAGES_COUNT = 50
isSaving = False
SEARCH_COMMAND1 = '#google'
SEARCH_COMMAND2 = '#search'
RATE_COMMAND = '#rate'
HORSE_COMMAND = '#horse'
REGIONAL_COMMAND = '#reg'
WARN_COMMAND = "#warn"
SAY_COMMAND = "#say"
DELETE_COMMAND = "#delete"
YOUTUBE_COMMAND = "#youtube"
ME_COMMAND = '#me'
YT_CMD = "#yt"

DOWNLOADPATH = "Temp"
MONEY_COMMAND = "#bal"
MONEY_COMMAND_2 = "#balance"
intents = discord.Intents.all()


bot = commands.Bot(command_prefix='#', intents=intents)

     
@bot.tree.command(name="ping")
async def ping(interaction:discord.Interaction):
    latency = f'{round(bot.latency * 1000)}ms'

    await interaction.response.send_message(f"Pong! Latency: {latency}",ephemeral=False)
       

       

DATABASE_PATH = '/home/debian/liventcordenv/liventcord/databases/'

LANDREBORN_PATH = DATABASE_PATH + 'discord_reborn_database.db'


ReeyukiID = 452491822871085066

LANDREBORN_ID = 916548790662623282

server_ids = {916548790662623282, 1208131142985715712}

BULK_SAVE_THRESHOLD = 300

last_message_time = {}
last_message_content = {}


BASE_PATH = '/home/ubuntu/liventcord'

def download_avatar(user_name, avatar_url):
    filename = os.path.join(BASE_PATH, "static", "profiles", f"{user_name}.png")
    try:
        response = requests.get(avatar_url)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(filename), exist_ok=True)  # Create directories if they don't exist
            with open(filename, "wb") as f:
                print(filename)
                f.write(response.content)
        else:
            print(f"Failed to download avatar for user {user_name}")
    except Exception as e:
        print(f"An error occurred while downloading avatar for user {user_name}: {e}")
        
        
        
emoji_ids = {
    'gn': 1208166963801751664,
    'yes': 1210321157635444786,
    'noo': 1182758340749701260,
    'jack': 1182769822455562270,
    'ahegao': 916764640216743966,
    'headout': 1182373253361193040,
    'shiza': 981226566904324106,
    'elysia': 1208543135303733329,
    'rita': 1208539208541544550,
    'ducks': 1134767222854787074,
    'brainlet': 1182759185058898013,
    'mudae_user': 432610292342587392,
    'everything': 936624539134210068,
    'napim' : 1182761451283304551,
    'suckmydick' : 1171500558029422632,
    'slap' : 1127874594078986291,
    'ascension' : 1182765688927043644,
    'sikeleton' : 973630846122745936,
    'neverforgive' : 937411461205090394,
    'inanilmaz' : 1134775445020229632,
    'turko' : 1008840666098446486,
    'sex' : 978375586110132325,
    'hekanka' : 1134771201810640956,
    'kemal' : 1205158569847029890,
    'ekmek' : 1205158420827734116,
    'hugefan' : 1009052968168996954,
    'fall' : 1134099889979129947,
    'unrelated' : 1134598995428249862
}
    

async def extract_message_data(message):
    attachments = ', '.join([attachment.url for attachment in message.attachments])
    reply_to_id = None

    if message.reference and message.reference.resolved and message.reference.resolved.id:
        reply_to_id = message.reference.resolved.id

    reaction_emojis_ids = ', '.join([str(reaction.emoji.id) if hasattr(reaction.emoji, 'id') else 'None' for reaction in message.reactions])

    # Add 3 hours to the message created_at time and convert back to string in the same format
    # new_time = message.created_at + timedelta(hours=3)
    # new_time_string = new_time.strftime('%Y-%m-%d %H:%M:%S')
    return(message.id, message.author.id, message.content, str(message.channel.id), str(message.created_at), str(message.edited_at), attachments, reply_to_id, reaction_emojis_ids)
    
            
async def save_messages(messages, requested_path):
    if not isSaving: return
    if not isinstance(messages, list):
        messages = [messages]

    async with aiosqlite.connect(requested_path) as conn:
        await conn.execute('''
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
        ''')

        data = []

        for message in messages:
            if message.author.bot:
                if any(url in message.content for url in ('http://', 'https://')):
                    data.append(await extract_message_data(message))
            else:
                data.append(await extract_message_data(message))
            
        if data:
            await conn.executemany('''INSERT OR REPLACE INTO Message 
                                (id, user_id, content, channel, date, last_edited, attachment_urls, reply_to_id, reaction_emojis_ids) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)

            await conn.commit()


async def get_messages(channel_id, requested_path):

    print(f"Getting channel for channel id: {channel_id}...")
    channel = bot.get_channel(int(channel_id))

    if channel and isinstance(channel, discord.TextChannel):
        # Check if the client has read permissions for the channel
        if not channel.permissions_for(channel.guild.me).read_messages:
            print("Bot does not have permission to read messages in this channel.")
            return

        print(f"Working on channel: {channel}...")
        limit = 100
        if channel_id == "942831492059512862" or channel_id == '1005549041817493534' and limit is not None:
            limit *= 2  # Double the limit for special channels
        messages_to_save = []  # Accumulator for messages to be saved in bulk
        try:
            requests_count = 0
            async for message in channel.history(limit=limit):  # Apply the modified limit
                requests_count += 1
                if requests_count % BULK_SAVE_THRESHOLD == 0:
                    print(f"Got {BULK_SAVE_THRESHOLD} messages.")
                messages_to_save.append(message)  # Accumulate messages

                # Check if it's time to save messages in bulk or if we reached a certain number of messages
                if len(messages_to_save) >= BULK_SAVE_THRESHOLD:
                    await save_messages(messages_to_save, requested_path)
                    messages_to_save = []  # Clear accumulator

            # Save any remaining messages
            if messages_to_save:
                await save_messages(messages_to_save, requested_path)

            print(f"Finished getting channel id {channel}")

        except Exception as e:
            print(f"An error occurred while fetching messages: {e}")

    else:
        print(f'Invalid channel ID: {channel_id}')



async def get_all_messages():

    print("Started getting all messages...")

    guild = bot.get_guild(LANDREBORN_ID)
    
    if guild is None:
        print("Guild not found.")
        return

    channels = guild.channels
    
    for channel in channels:
        await get_messages(channel.id, LANDREBORN_ID)
        

    


        
@bot.event
async def on_ready():

        
    clear_downloads_folder()
    
    #await save_avatars(bot.guilds)
    
    if not isSaving: return
    await get_all_messages()
    await bot.add_cog(SelfCog(bot))

    


@bot.event
async def on_message_edit(before, after):
    if not isSaving: return
    if before.guild.id is not LANDREBORN_ID:
        return

    # Message content has been changed
    print(f'Message with id {after.id} edited in {after.channel.name}:')
    print(f'Before: {before.content}')
    print(f'After: {after.content}')
    

    

    async with aiosqlite.connect(LANDREBORN_PATH) as conn:
        

        data = []
        if after.author.bot:
            # Check if the message contains URLs
            if any(url in after.content for url in ('http://', 'https://')):
                data = await extract_message_data(after)
        else:
            data = await extract_message_data(after)


        c = conn.cursor()
        # overwrite the message and update it
        await conn.execute('''INSERT OR REPLACE INTO Message 
                            (id, sender_id, content, channel, date, last_edited, attachment_urls, reply_to_id, reaction_emojis_ids) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)


            
class SelfCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        #emoji = payload.emoji
        
        attachments = ', '.join([attachment.url for attachment in message.attachments])
        reply_to_id = None

        if message.reference and message.reference.resolved.id:
            reply_to_id = message.reference.resolved.id
        
        reaction_emojis_ids = ', '.join([str(reaction.emoji.id) if hasattr(reaction.emoji, 'id') else 'None' for reaction in message.reactions])

        requested_path = LANDREBORN_PATH 
        
        async with aiosqlite.connect(requested_path) as conn:
            await conn.execute('INSERT OR REPLACE INTO Message (id, sender_id, content, channel, date, last_edited, attachment_urls, reply_to_id, reaction_emojis_ids) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (message.id, message.author.id, message.content, str(message.channel.id), str(message.created_at), str(message.edited_at), attachments, reply_to_id, reaction_emojis_ids))
            await conn.commit()




    

@bot.event
async def on_message_delete(message):
    if not isSaving: return
    if message.guild.id is not LANDREBORN_ID: return
    print(f'Message deleted in {message.channel.name}:')
    print(f'Content: {message.content}')
    strid = str(message.id)
    

    with sqlite3.connect(LANDREBORN_PATH) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM Message WHERE id = ?', (strid,))

@bot.event
async def on_raw_reaction_add(payload):
    if not isSaving: return
    # Check if the reaction is added in a guild (server)
    if payload.server_id is None or not payload.server_id in server_ids:
        return

    # Fetch the message using the message ID from the payload
    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.NotFound:
        return  # Message not found

    # Add the reaction using the message object
    emoji = bot.get_emoji(payload.emoji.id)
    if emoji is not None:
        await message.add_reaction(emoji)

@bot.event
async def on_raw_reaction_remove(payload):
    # Check if the reaction is removed in a guild (server)
    if payload.server_id is None or not payload.server_id in server_ids:
        print(f"guild {payload.server_id} is none")
        return

    # Fetch the message using the message ID from the payload
    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        print(f"channel is none for {payload.channel_id}")
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.NotFound:
        print(f"message not found {payload.message_id}")
        return  # Message not found

    # Get the bot's reaction emoji from the message
    for reaction in message.reactions:
        if reaction.me and reaction.emoji == payload.emoji:
            bot_emoji = reaction
            break
    else:
        bot_emoji = None

    # If the bot's emoji is found, remove it from the message
    if bot_emoji:
        await bot_emoji.remove(bot.user)

        # Optionally, you can log a message indicating the removal
        print(f"Removed bot's reaction {payload.emoji.name} from message ID {message.id}")




async def remove_reaction(reaction, client):
    # Check if the reaction's owner is the bot itself
    if reaction.message.author == client.user:
        await reaction.message.remove_reaction(reaction.emoji, client.user)
        
Wooperid = 763454684702048318
reeyukiid = 452491822871085066
Woopermoney = '200000000000'
reeyukimoney = '900000000000'
defaultmoney = '-999999999! İflas ettin!'

avatar_change_cooldown = 60*5 + 5  # Cooldown duration in seconds
last_avatar_change_time = 0  # Initialize the last avatar change time
last_banner_change_time = 0


@bot.event
async def on_message(message):

    global last_avatar_change_time

    

    await our_server(message)
    if not message.author == bot.user:
        if isDm(message):
            user = bot.get_user(452491822871085066)

            if user and message:
                await user.send(message.content)
        
        isLiventMode = False
        if isLiventMode and message.author.id == 452491822871085066:
            contentcached = message.content
            channelcached = message.channel
            await message.delete()
            await channelcached.send(contentcached)
        
        

                
        

        
        


        if message.content.startswith('#avatar'):
            mention = message.mentions[0] if message.mentions else message.author
            avatar_url = mention.avatar.url
            embed = discord.Embed(title=f"{mention.display_name} {'is online' if mention.status == discord.Status.online else 'is offline'}",
                                color=discord.Color.green())
            embed.set_image(url=avatar_url)
            await message.channel.send(embed=embed)
            
        elif message.content.startswith("#ui"):
            mention = message.mentions[0] if message.mentions else None
            if mention:
                user = mention
                user_name = user.name
                user_id = user.id
                user_created_at = user.created_at.strftime("%Y-%m-%d")
                #user_badges = "bravery"  # Example badge
                user_is_bot = "🟢" if user.bot else "🔴"
                #user_dm_status = "🟢"  # Example DM status
                user_status = "🟢" if str(user.status) == "online" else "🔴"

                member = message.guild.get_member(user.id)
                nickname = member.nick if member.nick else user_name
                join_date = member.joined_at.strftime("%Y-%m-%d")
                roles = [role.name for role in member.roles if role.name != "@everyone"]
                highest_role = roles[-1] if roles else "None"
                lowest_role = roles[0] if roles else "None"
                admin_status = "🟢" if member.guild_permissions.administrator else "🔴"

                roles_text = ", ".join(roles) if roles else "None"

                embed = Embed(title=f"{user_name} isimli kullanıcının profili", color=0x00ff00)
        
                embed.add_field(name="KULLANICI", value=(
                    "\n"
                    f"📝 **KULLANICI:**\n"
                    "\n"
                    "\n"
                    f"📝 **Kullanıcı Adı:** {user_name}\n"
                    "\n"
                    f"🆔 **Kullanıcı ID:** {user_id}\n"
                    "\n"
                    f"📅 **Oluşturma Tarihi:** {user_created_at}\n"
                    "\n"
                    f"🤖 **Bot:** {user_is_bot}\n"
                    "\n"
                    f"👤 **Durum:** {user_status}\n"
                    "\n"
                ), inline=False)
                
                embed.add_field(name="SUNUCU", value=(
                    "\n"
                    f"📝 **Takma Ad:** {nickname}\n"
                    "\n"
                    f"🗓 **Katılma Tarihi:** {join_date}\n"
                    "\n"
                    f"🎭 **Roller:** {roles_text}\n"
                    "\n"
                    f"🔼 **En Yüksek Rol:** {highest_role}\n"
                    "\n"
                    f"🔽 **En Düşük Rol:** {lowest_role}\n"
                    "\n"
                    f"🛠️ **Admin:** {admin_status}"
                ), inline=False)
                await message.channel.send(embed=embed)
        elif message.content.startswith('#chat'):
            question = message.content[len('#chat'):].strip()  
            api_url = f"https://tilki.dev/api/hercai?soru={question}"
            response = requests.get(api_url)

            if response.status_code == 200:
                try:
                    data = response.json()
                    await message.channel.send(data['cevap'])  
                except ValueError:  # Handle JSON decoding error
                    await message.channel.send("Error: Invalid JSON format in the API response.")
            else:
                await message.channel.send(f"Failed to get response from the API {response.status_code}")
            # Check if the message starts with the command and the user has attached an image
        elif message.content.startswith('#ping'):
            latency = f'{round(bot.latency * 1000)}ms'
            await message.reply(f"Pong! Latency: {latency}")
        elif message.content.lower().startswith('#changeavatar') and message.attachments:
            # Get the current time
            current_time = time.time()

            # Check if the cooldown period has passed since the last avatar change
            if current_time - last_avatar_change_time >= avatar_change_cooldown:
                # Get the first attachment or URL from the message
                attachment_url = message.attachments[0].url if message.attachments else message.content.split()[1]

                # Check if the URL lacks the "http://" prefix
                if attachment_url.startswith('http'):
                    url_with_http = attachment_url
                else:
                    url_with_http = f'http://{attachment_url}'

                # Download the image from the URL
                response = requests.get(url_with_http)
                if response.status_code == 200:
                    # Save the image as avatar.png
                    with open('avatar.png', 'wb') as file:
                        file.write(response.content)
                    # Change the bot's avatar
                    with open('avatar.png', 'rb') as avatar_file:
                        await bot.user.edit(avatar=avatar_file.read())
                    await message.channel.send("Avatar changed successfully!")
                    # Update the last avatar change time
                    last_avatar_change_time = current_time
                else:
                    await message.channel.send("Failed to download the image.")
            else:
                # Calculate the remaining time until cooldown ends
                remaining_time = int(avatar_change_cooldown - (current_time - last_avatar_change_time))
                await message.channel.send(f"Avatar change cooldown is active. Please wait {remaining_time} seconds.")
        elif message.content.lower().startswith('#status'):
            # Split the message content to get the nickname
            split_content = message.content.split()
            if len(split_content) >= 2:
                nickname = ' '.join(split_content[1:])  # Join the nickname parts
                await updateselfstatus(nickname)
                await message.channel.send("Status updated successfully!")
            else:
                await message.channel.send("Invalid command. Usage: #status <nickname>")
        elif message.content.startswith(MONEY_COMMAND) or message.content.startswith(MONEY_COMMAND_2):
            def get_money(author_id):
                if author_id == Wooperid:
                    return Woopermoney
                elif author_id == reeyukiid:
                    return reeyukimoney
                else:
                    return defaultmoney

            author_id = message.author.id
            embed = Embed(title=f'{message.author.name} isimli kullanıcının bakiyesi:', color=0x0000FF)
            embed.set_thumbnail(url=message.author.avatar.url)
            money = get_money(author_id)
            money_prefix = f'{money}₽'
            embed.add_field(name='Bakiye', value=money_prefix, inline=False)
            embed.set_footer(text='₽ kazanamazsın >:)', icon_url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR4iVS2O8C1JprHqbgjHjLtwnI433lTUtZ8wfUL1nj76rmQZMKqyv6Yq-IH&s=10')
            await message.channel.send(embed=embed)

            
            
        elif message.content.startswith(ME_COMMAND):
            await me_mimic(message)
        
        elif message.content.startswith(DELETE_COMMAND):
            await delete_messages(message)
        elif message.content.lower().startswith(YOUTUBE_COMMAND):
            await youtube_search(message,YOUTUBE_COMMAND)
        elif message.content.lower().startswith(YT_CMD):
            await youtube_search(message,YT_CMD)

        elif message.content.lower().startswith(SAY_COMMAND):
            text = message.content[len(SAY_COMMAND):].strip()  
            if message.reference and message.reference.resolved:
                await message.reference.resolved.reply(text)
            else:
                await message.channel.send(text)
            if(not isDm(message)):
                if message:
                    await message.delete()
        elif message.content.lower().startswith(WARN_COMMAND):
            await warn(message)
        elif message.content.lower().startswith(RATE_COMMAND):
            await rate(message)
        elif message.content.lower().startswith(REGIONAL_COMMAND):
            await regionalconvert(message,True)
        elif message.content.lower().startswith(SEARCH_COMMAND1) or message.content.startswith(SEARCH_COMMAND2):
            command = SEARCH_COMMAND1 if message.content.startswith(SEARCH_COMMAND1) else SEARCH_COMMAND2
            await process_image_search_command(message, command)
        elif message.content.startswith('-url'):
            content_parts = message.content.split()
            if len(content_parts) == 2:
                try:
                    message_id = int(content_parts[1])

                    # Search for the message across all channels in the server
                    target_message = await find_message_in_channels(message.guild, message_id)

                    if target_message:
                        # Check if the found message has embeds
                        if target_message.embeds:
                            for embed in target_message.embeds:
                                if embed.thumbnail:
                                    # Get the thumbnail URL from the embed
                                    thumbnail_url = embed.thumbnail.url
                                    await send_image_from_url(message.channel, thumbnail_url)

                                if embed.footer and embed.footer.icon_url:
                                    # Get the footer icon URL from the embed
                                    footer_icon_url = embed.footer.icon_url
                                    await send_image_from_url(message.channel, footer_icon_url)

                                if embed.image:
                                    # Get the image URL from the embed
                                    image_url = embed.image.url
                                    await send_image_from_url(message.channel, image_url)

                                if embed.url:
                                    # Get the URL from the embed
                                    embed_url = embed.url
                                    await message.channel.send(f'Embed URL: {embed_url}')
                                if embed.author and embed.author.icon_url:
                                    # Get the author icon URL from the embed
                                    author_icon_url = embed.author.icon_url
                                    await send_image_from_url(message.channel, author_icon_url)
                        else:
                            await message.channel.send('No embeds found in the message.')

                    else:
                        await message.channel.send('Message not found.')

                except ValueError:
                    await message.channel.send('Invalid message ID provided.')
        
    await bot.process_commands(message)  
    
    if not isinstance(message.channel, discord.DMChannel) and not  isinstance(message.channel, discord.Thread ):
        await forward_message(message)
            
async def find_message_in_channels(guild, message_id):
    for channel in guild.text_channels:
        try:
            message = await channel.fetch_message(message_id)
            return message
        except discord.NotFound:
            pass
    return None


async def updateselfstatus(nickname):

    await bot.change_presence(activity=discord.Game(name=f"{nickname}"))




async def send_image_from_url(channel, url):
    # Download the image using requests
    response = requests.get(url)
    if response.status_code == 200:
        # Open the image with Pillow
        image = Image.open(BytesIO(response.content))
        # Save the enhanced image to a BytesIO object
        image_bytes = BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)

        # Send the enhanced image in Discord
        await channel.send(file=discord.File(image_bytes, filename='image.jpg'))
    else:
        await channel.send('Failed to download the image.')

async def save_avatars(guilds):
    print("Saving avatars...")

    for guild in guilds:
        if not 'Emoji' in guild.name:
            members = await get_all_members(guild.id)
            for member in members :
                if member.avatar is not None:

                    name = member.display_name
                    print(f"Saving user {name}'s avatar: {member.avatar.url}")
                    
                    avatar_url = str(member.avatar.url)
                    download_avatar(name,avatar_url)
                

            print("done a guild")
    
    print("exit")


async def get_all_members(guildid):
    guild = bot.get_guild(guildid)
    print('getting members...')
    members = []
    async for member in guild.fetch_members(limit=None):
        members.append(member)
    return members



def isDm(message):
    return isinstance(message.channel, discord.DMChannel)

def construct_server_path(server_id):
    return DATABASE_PATH + f"Server_{server_id}_database.db"

async def forward_message(message):
    if message.guild.id != LANDREBORN_ID :      return
    URL = 'http://localhost:5005/messagediscordbot'
    

    data = await extract_message_data(message) 
    
    _json = {
        'id':  data[0],
        'user_id':  data[1],
        'content': data[2],
        'channel_id': data[3],
        'date':  data[4],
        'last_edited': data[5],
        'attachment_urls': data[6],
        'reply_to_id': data[7],
        'reaction_emojis_ids': data[8],
        'server_id': message.guild.id,
        'channel_name' : message.channel.name,
        'password' : '281354LC'
    }
    
    requested_path = construct_server_path(message.guild.id)
    try:
        
        response = requests.post(URL, json=_json)
        response.raise_for_status()
        print("Message sent to server successfully.")
    except RequestException as e:
        if isinstance(e, requests.ConnectionError) or 'WinError 10061' in str(e):
            current_time = datetime.now()
            log_message = f"[{current_time}] Couldn't connect to the server. Saving to database instead."
            print(log_message)
            await save_messages(message, requested_path)
        else:
            current_time = datetime.now()
            print(f"[{current_time}] Error occurred while checking server or sending message to server. Saving to database: {str(e)}")
            await save_messages(message, requested_path) 

async def delete_messages(message):
# Extract the amount from the message content
    amount = int(message.content.split()[1])
    # Check if the user has provided a valid number of messages to delete
    if amount <= 0 or amount > 100:
        await message.channel.send('You can only delete between 1 and 100 messages at a time.')
        return
    # Delete the specified number of messages
    try:
        deleted = await message.channel.purge(limit=amount + 1)  # +1 to include the command message
        count_deleted = len(deleted) - 1  # Excluding the command message itself
        delete_msg = await message.channel.send(f'Deleted {count_deleted} messages.')
        await delete_msg.delete(delay=10)  # Delete the deletion confirmation message after 10 seconds
    except Exception as e:
        print(e)
        await message.channel.send('There was an error while trying to delete messages.')

async def me_mimic(message):
    parts = message.content.split()

    try:
        # Check if the command format is #me #<WebhookAvatarUrl> #<WebhookNick> <TextToSendByWebhook>
        if parts[1].startswith("#") and parts[2].startswith("#"):
            avatar_url = parts[1][1:]  # Remove the leading "#"
            nickname = parts[2][1:]
            content = ' '.join(parts[3:])
            
            # Check if the URL is a Tenor URL
            if "media1.tenor.com/m/" in avatar_url or "c.tenor.com/" in avatar_url:
                tenor_url = avatar_url
            elif avatar_url.startswith("tenor.com") or avatar_url.startswith("https://tenor.com"):
                # Check if the URL ends with an image extension, if not, append ".gif"
                tenor_url = avatar_url if avatar_url.endswith((".gif", ".jpg", ".jpeg", ".png")) else avatar_url + ".gif"
            else:
                tenor_url = avatar_url  # Use the original URL if not a Tenor URL
                
            await message.delete()
            webhook = await message.channel.create_webhook(name=nickname)
            try:
                await webhook.send(content, username=nickname, avatar_url=tenor_url)
                await asyncio.sleep(10)
            finally:
                await webhook.delete()

        # Check if the command format is #me @MentionHere <TextToSendByWebhook>
        elif parts[1].startswith("<@"):
            mentioned_user_id = int(parts[1].strip('<@!>'))
            content = ' '.join(parts[2:])
            await message.delete()
            mentioned_user = message.guild.get_member(mentioned_user_id)
            mentioned_avatar = mentioned_user.avatar.url if mentioned_user.avatar else None
            member = message.guild.get_member(mentioned_user.id)
            nickname = member.nick if member.nick else member.name
            webhook = await message.channel.create_webhook(name=nickname)
            try:
                await webhook.send(content, username=nickname, avatar_url=mentioned_avatar)
                await asyncio.sleep(10)
            finally:
                await webhook.delete()

    except (IndexError, ValueError):
        # Handle any index error or value error, e.g., if parts[1] is not found or if the ID conversion fails
        pass

async def youtube_search(message, command):
    text = message.content[len(command):].strip()
    parts = text.split('#')
    query = parts[0].strip()
    number = int(parts[-1].strip()) if len(parts) > 1 else 1
    search_results = Search(query)
    results = search_results.results[:number]
    response = "Search results:\n"
    for index, result in enumerate(results, start=1):
        response += f"{index}. {result.title}\n"
        response += f"   URL: {result.watch_url}\n\n"

    await message.channel.send(result.watch_url)
    

async def our_server(message):
    def canReact(message):
        if message.channel.guild:
            if message.channel.guild.id in server_ids:
                return True
            else:
                return False
        else: # Non guild channel
            return True
        
    if canReact(message):


        if message:
            m_emoji_ids = re.findall(r'<(a?):[a-zA-Z0-9_]+:([0-9]+)>', message.content)
            m_emoji_ids = [emoji[1] for emoji in m_emoji_ids]
            messagelower = message.content.lower()
            
            
            
            #if message and message.reference and message.reference.resolved:
            #    now_utc = datetime.now(timezone.utc)
            #    time_diff = now_utc - message.reference.resolved.created_at
            #    if time_diff.total_seconds() > 900:  # 15 minutes in seconds
            #        jack_emoji = bot.get_emoji(1182769822455562270)
            #        await message.add_reaction(jack_emoji)
            
            
            def hasemoji(emojiname):
                try:
                    return emoji_ids[emojiname] in m_emoji_ids
                except:
                    return False
                    
            if messagelower.startswith(HORSE_COMMAND):  
                await horse_contest(message)
            if "trash" in messagelower:
                await message.add_reaction(bot.get_emoji(emoji_ids['everything']))
            
            if message.reference and message.reference.resolved and message.reference.resolved.id == BOT_SELF_ID:
                if 'yya' in messagelower or hasemoji('jack'):
                    await message.reply('Yia')

            if "maybe i am a monster" in messagelower or 'https://tenor.com/view/vision-monster-maybe-maybe-i-am-a-monster-marvel-gif-16321436' in messagelower :
                await message.reply('Yya')
            if 'melt' in messagelower or hasemoji('ahegao'):
                await message.add_reaction(bot.get_emoji(emoji_ids['yes']))
            if hasemoji('gn'):
                await message.add_reaction(bot.get_emoji(emoji_ids['gn_dog']))
            if hasemoji('brainlet') or 'brainlet' in messagelower:
                await message.reply('Yta')
            if hasemoji('napim') or 'napim' in messagelower:
                await message.add_reaction(bot.get_emoji(emoji_ids['suckmydick']))
            if hasemoji('headout') or 'headout' in messagelower:
                await message.add_reaction(bot.get_emoji(emoji_ids['shiza']))
            if hasemoji('elysia') or hasemoji('rita'):
                await message.reply('Yya')
            if hasemoji('shiza') or 'shiza' in messagelower:
                await message.add_reaction(bot.get_emoji(emoji_ids['noo']))
            if hasemoji('allah') or 'allah' in messagelower:
                await message.add_reaction(bot.get_emoji(emoji_ids['ducks']))
            if hasemoji('slap'):
                await message.add_reaction(bot.get_emoji(emoji_ids['slap']))
            if 'never forgive' in messagelower or hasemoji('neverforgive'):
                await message.add_reaction(bot.get_emoji(emoji_ids['neverforgive']))
            if "ascension" in messagelower or hasemoji('ascension'):
                await message.add_reaction(bot.get_emoji(emoji_ids['yes']))
               
            keywords = ['wait', 'matthew', 'matte']
            words = messagelower.split()  # Split the message into a list of words
            for word in words:
                if word in keywords:
                    await message.add_reaction(bot.get_emoji(emoji_ids['sikeleton']))
                    break  # Add break statement to stop after the first match

            if message.author.id == emoji_ids['mudae_user']:
                #if "you just won" in messagelower or "you won" in messagelower or "you got" in messagelower:
                #    await message.reply("Trash")
                if 'uncommon nothing' in messagelower:
                    await message.add_reaction(bot.get_emoji(emoji_ids['fall']))
                    await message.add_reaction(bot.get_emoji(emoji_ids['neverforgive']))
            if len(message.content) > 200 and not message.author.bot:
                await message.add_reaction(bot.get_emoji(emoji_ids['inanilmaz']))
        
            if 'jojo' in messagelower:
                await message.add_reaction(bot.get_emoji(emoji_ids['ahegao']))
            if 'izzet' in messagelower:
                await message.add_reaction(bot.get_emoji(emoji_ids['neverforgive']))
                
            turko_words = ['dolar', 'fiyat', 'ekonomi', 'tl']
            words = messagelower.split()  # Split the message into a list of words
            for word in words:
                if word in turko_words:
                    await message.add_reaction(bot.get_emoji(emoji_ids['turko']))
                    break  # Add break statement to stop after the first match
                
                
            if hasemoji('hekanka'):
                await message.add_reaction(bot.get_emoji(emoji_ids['hekanka']))
                
            if hasemoji('kemal'):
                await message.add_reaction(bot.get_emoji(emoji_ids['ekmek']))
                await message.add_reaction('\U0001F35E')
            if hasemoji('ekmek'):
                await message.add_reaction(bot.get_emoji(emoji_ids['kemal']))
                await message.add_reaction('\U0001F35E')
                
            if hasemoji('hugefan'):
                await message.add_reaction(bot.get_emoji(emoji_ids['hugefan']))
            if hasemoji('fall'):
                await message.add_reaction(bot.get_emoji(emoji_ids['fall']))
            if 'melt' in messagelower or hasemoji('ahegao'):
                await message.add_reaction(bot.get_emoji(emoji_ids['unrelated']))
            
            
            ## Get the current time
            #current_time = datetime.now()

            ## Check if the user sent a message before
            #if message.author.id in last_message_content and not message.author.bot and message.content != '':
            #    # Check if the current message content is the same as the last message content
            #    if message.content == last_message_content[message.author.id]:
            #        # Calculate the time difference between the current message and the last message sent by the user
            #        time_diff = current_time - last_message_time[message.author.id]
            #        
            #        # Check if the time difference is less than 5 minutes
            #        if time_diff.total_seconds() < 300:
            #            await message.add_reaction(bot.get_emoji(emoji_ids['ascension']))

            ## Update the last message content and time for the user
            #last_message_content[message.author.id] = message.content
            #last_message_time[message.author.id] = current_time

            
        
        
        
def extract_command_parts(message, command):
    return list(filter(lambda x: x.strip(), message.content[len(command):].split('#')))

async def warn(message):
    parts = message.content.split(maxsplit=1)  # İlk boşlukta ayır, sadece bir kez ayır
    reason = ' '.join(parts[1].split()[1:]) if len(parts) > 1 else ""  # Komutu ve kullanıcı etiketini atladıktan sonra kalan kısım neden olacak
    
    user_mention = message.mentions[0].mention if message.mentions else ""  # Kullanıcının etiketini al
    await message.delete()
    
    await message.channel.send(f'''{user_mention}, be well-behaved or you will get banned!
Your warning reason is: {reason}
warned by {message.author.name}
''')




    
async def regionalconvert(message,isStripping):
    char_with_regional = []
    text =  message.content[len(REGIONAL_COMMAND):].strip() if isStripping else message

    for i, char in enumerate(text):
        if char.isalpha():
            char_with_regional.append(f":regional_indicator_{char.lower()}:")
            # Kontrol edilen karakterden önceki ve sonraki karakterler boşluksa, boşluk ekleyin
            if i < len(text) - 1 and text[i+1].isspace():
                char_with_regional.append("   ")
        elif char.isspace():
            char_with_regional.append(char)


    result = "".join(char_with_regional)

    # Truncate the result if it exceeds Discord's maximum character limit
    if len(result) > 2000:
        result = result[:1997] + "..."
    
    if(len(result) > 0):
        if isStripping :
            await message.channel.send(result)
        else:
            return result
    
async def rate(message):
    user_mention = message.mentions[0] if message.mentions else None
    user = user_mention or message.author

    # Placeholder for the actual win rate calculation logic
    gay_rate = calculate_win_rate()  # You need to implement this function

    output_message = f"**Gay Rate\n{user.name} is {gay_rate}% Gay :rainbow_flag:\nRequested by {message.author.name}**"

    await message.reply(output_message)
    
async def horse_contest(message):
    user_mention = message.mentions[0] if message.mentions else None
    user = user_mention or message.author
    
    players = [
        'Lusamine', 'May', 'Misty', 'Dawn', 'Cynthia', 'Hilda', 'Serena',
        'Elesa', 'Skyla', 'Iris', 'Rosa', 'Leaf', 'Shauna', 'Bianca',
        'Nessa', 'Marnie', 'Bea', 'Mallow', 'Melony', user.name
    ]
    
    win_rates = {player: calculate_win_rate() for player in players}
    
    top_winners = sorted(win_rates, key=win_rates.get, reverse=True)[:3]
    winner = max(win_rates, key=win_rates.get)
    
    await message.channel.send(
        f"**Lusamine, Misty, May, Dawn, Cynthia, Hilda, Serena, Elesa, Skyla, Iris, Rosa, Leaf, Shauna, Bianca, Nessa, Marnie, Bea, Mallow, Melony, and {user.name} had a contest!**\n"
        f"**Win Rates**:\n"
        + "\n".join([f"  **{winner}**: {win_rates[winner]}%" for winner in top_winners]) +
        f"\n\nWinner is: {top_winners[0]}\n"
        #f"\nRequested by {message.author.name}"
    )


    searchterm = f"{winner} pokemon hentai dd reddit"
    folder_name = f"{DOWNLOADPATH}_{searchterm}_{1}_{message.id}"

    thumbnails = await search_images(searchterm, folder_name, 1)
    for thumbnail in thumbnails:
        await send_image_or_resized(message.channel, thumbnail)

    remove_folder(os.path.join(DOWNLOADPATH, folder_name))


def calculate_win_rate():
    return random.randint(0, 100)




async def send_image_or_resized(channel, image_path, max_file_size=18, max_width=800, max_height=600):
    with Image.open(image_path) as img:
        if len(img.tobytes()) / (1024 * 1024) > max_file_size:
            img.thumbnail((max_width, max_height))
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            await channel.send(file=discord.File(buffer, filename='image.png'))
        else:
            await channel.send(file=discord.File(image_path, filename='image.png'))

def remove_folder(folder_path):
    time.sleep(15)
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
    except Exception as e:
        print(f"Error removing folder {folder_path}: {e}")


async def process_image_search_command(message, command):
    try:
        parts = extract_command_parts(message, command)

        if len(parts) > 0:
            search_term = parts[0].strip()
            number = int(parts[1].strip()) if len(parts) > 1 else 1

            folder_name = f"{DOWNLOADPATH}_{search_term}_{number}_{message.id}"

            thumbnails = await search_images(search_term, folder_name, number)

            # Batch images into groups of 10 for attachment limit
            batches = [thumbnails[i:i + 10] for i in range(0, len(thumbnails), 10)]
            for batch in batches:
                await send_images_in_batch(message.channel, batch)

            remove_folder(os.path.join(DOWNLOADPATH, folder_name))
        else:
            await message.channel.send(f"Invalid command format. Usage: {command} {{search_term}} #{{number}}")
    except Exception as e:
        print("Max retries reached. Unable to get a valid response.")

async def send_images_in_batch(channel, images):
    files = []
    for image_path in images:
        with open(image_path, "rb") as file:
            files.append(discord.File(file, filename=image_path))

    if len(files) > 0:
        await channel.send(files=files)

async def search_images(search_term, folder_name, count):
    if count > MAX_IMAGES_COUNT:
        count = MAX_IMAGES_COUNT
    folder_path = os.path.join(DOWNLOADPATH, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    google_crawler = GoogleImageCrawler(storage={"root_dir": folder_path})
    google_crawler.crawl(keyword=search_term, max_num=count)


    thumbnails = [os.path.join(folder_path, filename) for filename in os.listdir(folder_path) if filename.endswith((".jpg", ".png"))]
    return thumbnails


def clear_downloads_folder():
    if(os.path.exists(DOWNLOADPATH)):
        for filename in os.listdir(DOWNLOADPATH):
            file_path = os.path.join(DOWNLOADPATH, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted temp: {DOWNLOADPATH}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")


bot.run(os.getenv('DISCORD_TOKEN'))

#channels = [
#    "1013013271969804349", # mod
#    "916548826024796190"   # main
#    "942831492059512862"   # general
#    "991804736103780423"   # memes
#    "1169660616219295935"  # announcement
#    "1005553530486128700"  # welcome
#    "1018944264031457353"  # rules
#    "983786551924387880",  # questions
#    "918780185908764692",  # faq
#    "983800541245222933",  # suggestions
#    "942831026613395578",  # recommendations
#    "954450218286477392",  # discussion
#    "954450052561133568",  # music
#    "954450138288492614",  # art
#    "954450153987801120",  # videos
#    "989269628599537765",  # gamedev
#    "954450163638886440",  # yobaz
#    "999917560067797062",  # code
#    "954450174246273114",  # shitpost
#    "983800445334085703",  # textforvoice
#    "1001440945880965120"  # spam
#]


