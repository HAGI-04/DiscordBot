import discord
import os
import datetime


guildID2channelID = {
    597316369989632002:739749926057017356,  # botテスト鯖
    589468743214563343:599530740148994050,  # ゆずぽん
    698397334274310174:739760013568114708   # MIKUMARI
    }


token = os.environ['DISCORD_BOT_TOKEN']
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
client = discord.Client()

bot_channel = None
last_update = ""


@client.event
async def on_ready():
    global last_update

    dt_now = datetime.datetime.now(JST)
    last_update = dt_now.strftime("[%m/%d %H:%M:%S]")


@client.event   # VC入退室通知
async def on_voice_state_update(member, before, after):
    mem_name = member.display_name
    bef_cha = before.channel
    aft_cha = after.channel
    dt_now = datetime.datetime.now(JST)

    if bef_cha is not aft_cha:  # 入退室および移動のみ検知、ミュートなどの状態変更は除く
        if bef_cha is None:     # 入室
            m = ":blue_circle: IN : [**" + mem_name + "**] "
        elif aft_cha is None:   # 退室
            m = ":red_circle: OUT : [**" + mem_name + "**] "
        m += dt_now.strftime("||[%m/%d %H:%M:%S]||")  # 現在時刻付与
    
    # 通知するサーバーを特定
    channelID = guildID2channelID[member.guild.id]
    bot_channel = client.get_channel(channelID)

    await bot_channel.send(m)


@client.event   # メッセージ投稿検知イベント
async def on_message(message):
    if client.user != message.author:
        if message.content == "/info":

            # 情報を表示するサーバーを特定
            channelID = guildID2channelID[message.guild.id]
            bot_channel = client.get_channel(channelID)

            m = "ボット発言チャンネル：" + str(bot_channel) + "\n"
            m += "最終アップデート " + last_update + "\n"

            await message.channel.send(m)


client.run(token)
