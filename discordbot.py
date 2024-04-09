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
intents.messages = True
intents.voice_states = True
client = discord.Client(intents=intents)

# 日本標準時
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
restarted_at = ""

def fetch_channel_id(guild_id):
    """サーバーIDに基づいてチャンネルIDを取得する"""
    response = supabase.table('GuildID2ChannelID').select("channel_id").eq('guild_id', guild_id).execute()
    if response.data:
        return response.data[0]['channel_id']
    return None

@client.event
async def on_ready():
    """ボットが起動したときの処理"""
    global restarted_at
    restarted_at = datetime.datetime.now(JST).strftime("[%m/%d %H:%M:%S]")

@client.event   
async def on_voice_state_update(member, before, after):
    """ボイスチャンネルの状態が変化したときの処理"""
    if before.channel == after.channel or (before.channel and after.channel):
        return

    time = datetime.datetime.now(JST).strftime("||[%m/%d %H:%M:%S]||")
    action = ":blue_circle: IN : " if before.channel is None else ":red_circle: OUT : "
    message = f"{action}[**{member.display_name}**] {time}"
    
    channel_id = fetch_channel_id(member.guild.id)
    if channel_id:
        await client.get_channel(channel_id).send(message)

@client.event
async def on_message(message):
    """メッセージが投稿されたときの処理"""
    if message.author == client.user:
        return

    channel_id = fetch_channel_id(message.guild.id)
    if channel_id is None:
        return
    
    bot_channel = client.get_channel(channel_id)
    
    if message.content == "/info":
        info_message = f"ボット発言チャンネル：{bot_channel.name}\n最終アップデート {restarted_at}\n"
        await message.channel.send(info_message)

client.run(DISCORD_BOT_TOKEN)

