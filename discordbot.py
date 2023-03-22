import discord
import os
import datetime
import re
from collections import defaultdict


guild_id_to_channel_id = {
    597316369989632002:739749926057017356,  # botテスト鯖
    589468743214563343:599530740148994050,  # ゆずぽん
    698397334274310174:739760013568114708   # MIKUMARI
}

token = os.environ['DISCORD_BOT_TOKEN']
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
intents = discord.Intents.all()
client = discord.Client(intents=intents)

last_update = ""


def get_current_timestamp():
    dt_now = datetime.datetime.now(JST)
    return dt_now.strftime("[%m/%d %H:%M:%S]")


@client.event
async def on_ready():
    global last_update

    last_update = get_current_timestamp()
    print(f"Bot is ready. Last update: {last_update}")


async def send_voice_state_update_message(member, message):
    channel_id = guild_id_to_channel_id[member.guild.id]
    bot_channel = client.get_channel(channel_id)
    await bot_channel.send(message)


async def read_voice_history(guild_id):
    channel_id = guild_id_to_channel_id[guild_id]
    bot_channel = client.get_channel(channel_id)

    now = datetime.datetime.now(JST)
    seven_days_ago = now - datetime.timedelta(days=7)

    voice_history = defaultdict(list)
    async for message in bot_channel.history(after=seven_days_ago, oldest_first=True):
        if message.author == client.user:
            match = re.match(r"(?::blue_circle: IN|:red_circle: OUT) : \[\*\*(.+?)\*\*\] \|\|(\[\d{2}/\d{2} \d{2}:\d{2}:\d{2}\])\|\|", message.content)
            if match:
                action, member_name, timestamp = match.group(1), match.group(2), match.group(3)
                voice_history[member_name].append((action, timestamp))
    return voice_history


def generate_gantt_chart(voice_history):
    gantt_chart = "```\n"
    for member_name, actions in voice_history.items():
        gantt_chart += f"{member_name}:\n"
        for action, timestamp in actions:
            gantt_chart += f"{action} {timestamp}\n"
        gantt_chart += "\n"
    gantt_chart += "```"
    return gantt_chart


@client.event   # VC入退室通知
async def on_voice_state_update(member, before, after):
    member_name = member.display_name
    before_channel = before.channel
    after_channel = after.channel
    timestamp = get_current_timestamp()

    if before_channel != after_channel:  # 入退室および移動のみ検知、ミュートなどの状態変更は除く
        if before_channel is None:  # 入室
            message = f":blue_circle: IN : [**{member_name}**] ||{timestamp}||"
        elif after_channel is None:  # 退室
            message = f":red_circle: OUT : [**{member_name}**] ||{timestamp}||"
        await send_voice_state_update_message(member, message)


@client.event   # メッセージ投稿検知イベント
async def on_message(message):
    # ボット自身の発言を検知しないよう判別
    if client.user != message.author:
        if message.content == "/info":
            channel_id = guild_id_to_channel_id[message.guild.id]
            bot_channel = client.get_channel(channel_id)
            info_message = f"ボット発言チャンネル：{bot_channel}\n最終アップデート {last_update}\n"
            await message.channel.send(info_message)
        elif message.content == "/gantt":
            voice_history = await read_voice_history(message.guild.id)
            gantt_chart = generate_gantt_chart(voice_history)
            await message.channel.send(gantt_chart)


client.run(token)
