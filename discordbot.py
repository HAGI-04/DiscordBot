import os
import datetime
import discord
from supabase import create_client

# 環境変数から設定を読み込む
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Supabaseクライアントを初期化
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Discordクライアントを初期化
intents = discord.Intents.default()
intents.guild_messages = True
intents.voice_states = True
intents.messages = True  # メッセージイベントを有効にする
client = discord.Client(intents=intents)

# 日本標準時
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
guild_id_2_channel_id = {}
restarted_at = ""

def fetch_DB():
    response = supabase.table('GuildID2ChannelID').select("*").execute()
    return {d['guild_id']: d['channel_id'] for d in response.data} if response.data else {}

def update_DB(guild_id, channel_id, guild_name):
    response = supabase.table('GuildID2ChannelID').upsert({'guild_id': guild_id, 'channel_id': channel_id, 'guild_name': guild_name}).execute()
    return response.status_code == 201

@client.event
async def on_ready():
    """ボットが起動したときの処理"""
    global restarted_at
    restarted_at = datetime.datetime.now(JST).strftime("[%m/%d %H:%M:%S]")

    global guild_id_2_channel_id
    guild_id_2_channel_id = fetch_DB()

@client.event   
async def on_voice_state_update(member, before, after):
    """ボイスチャンネルの状態が変化したときの処理"""
    if before.channel == after.channel or (before.channel and after.channel):
        return

    time = datetime.datetime.now(JST).strftime("||[%m/%d %H:%M:%S]||")
    action = ":blue_circle: IN : " if before.channel is None else ":red_circle: OUT : "
    message = f"{action}[**{member.display_name}**] {time}"
    
    channel_id = guild_id_2_channel_id.get(member.guild.id)
    if channel_id:
        await client.get_channel(channel_id).send(message)

@client.event
async def on_message(message):
    """メッセージが投稿されたときの処理"""
    if message.author == client.user:
        return

    global guild_id_2_channel_id
    channel_id = guild_id_2_channel_id.get(message.guild.id)
    if channel_id is None:
        return
    
    bot_channel = client.get_channel(channel_id)

    if message.content.startswith("/info"):
        info_message = f":white_check_mark: ボット発言チャンネル : {bot_channel.name}\n:white_check_mark: 最終アップデート : {restarted_at}\n"
        await message.channel.send(info_message)

    elif message.content.startswith("/set"):
        if update_DB(message.guild.id, message.channel.id, message.guild.name):
            guild_id_2_channel_id = fetch_DB()
            await message.channel.send(":white_check_mark: ボット投稿チャンネルをこのチャンネルにセットしました")
        else:
            await message.channel.send(":x: ボット投稿チャンネルの設定に失敗しました")
    
    elif message.content.startswith("/show"):
        list_message = ":white_check_mark: 登録済みサーバー : ボット発言チャンネル\n```\n"
        for guild_id, channel_id in guild_id_2_channel_id.items():
            list_message += f"{client.get_guild(guild_id).name} : {client.get_channel(channel_id).name}\n"
        list_message += "```"
        await message.channel.send(list_message)

client.run(DISCORD_BOT_TOKEN)

