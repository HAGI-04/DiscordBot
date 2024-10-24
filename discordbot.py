import os
import datetime
import base64
import io
from PIL import Image
import discord
from openai import OpenAI
from supabase import create_client

# 環境変数から設定を読み込む
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# OpenAIクライアントを初期化
openai_client = OpenAI()

# Supabaseクライアントを初期化
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Discordクライアントを初期化
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# 日本標準時
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
guild_id_2_channel_id = {}
restarted_at = ""

@client.event
# ボットが起動したときの処理
async def on_ready():
    # 再起動時刻を取得
    global restarted_at
    restarted_at = datetime.datetime.now(JST).strftime("[%m/%d %H:%M:%S]")

    # サーバー：発言チャンネル対応表の取得
    global guild_id_2_channel_id
    response = supabase.table('GuildID2ChannelID').select("*").execute()
    guild_id_2_channel_id = {d['guild_id']: d['channel_id'] for d in response.data} if response.data else {}

@client.event
# ボイスチャンネルの状態が変化したときの処理
async def on_voice_state_update(member, before, after):
    # チャンネルの移動以外の検出は無視
    if before.channel == after.channel or (before.channel and after.channel):
        return

    time = datetime.datetime.now(JST).strftime("||[%m/%d %H:%M:%S]||")
    action = ":blue_circle: IN : " if before.channel is None else ":red_circle: OUT : "
    message = f"{action}[**{member.display_name}**] {time}"

    # メッセージの送信
    channel_id = guild_id_2_channel_id.get(member.guild.id)
    if channel_id:
        await client.get_channel(channel_id).send(message)

@client.event
# メッセージが投稿されたときの処理
async def on_message(message):
    # ボット自身の投稿を無視
    if message.author == client.user:
        return

    # メッセージの送信先チャンネルの取得
    global guild_id_2_channel_id
    channel_id = guild_id_2_channel_id.get(message.guild.id)
    if channel_id is None:
        return
    bot_channel = client.get_channel(channel_id)

    # ボット情報の表示
    if message.content.startswith("/vcbotinfo"):
        info_message = f":white_check_mark: ボット発言チャンネル : {bot_channel.name}\n:white_check_mark: 最終アップデート : {restarted_at}\n"
        await message.channel.send(info_message)

    # そのサーバにおけるボット投稿チャンネルの変更
    elif message.content.startswith("/vcbotset"):
        try:
            await message.channel.send(":thinking: ボット投稿チャンネルの変更を試みています...")
            supabase.table('GuildID2ChannelID').upsert({'guild_id': message.guild.id, 'channel_id': message.channel.id, 'guild_name': message.guild.name}).execute()
            guild_id_2_channel_id[message.guild.id] = message.channel.id
            await message.channel.send(":saluting_face: ボット投稿チャンネルをこのチャンネルにセットしました")
        except Exception as e:
            await message.channel.send(":tired_face: ボット投稿チャンネルの設定に失敗しました")
    
    # サーバー：発言チャンネル対応一覧の表示
    elif message.content.startswith("/vcbotshow"):
        list_message = ":white_check_mark: サーバー名 : チャンネル名\n```\n"
        for guild_id, channel_id in guild_id_2_channel_id.items():
            list_message += f"{client.get_guild(guild_id).name} : {client.get_channel(channel_id).name}\n"
        list_message += "```"
        await message.channel.send(list_message)
    
    # OW スクリーンショットのチャット欄文章翻訳機能
    elif message.content.startswith("/owocr"):
        if len(message.attachments) != 1:
            await message.channel.send("エラー: 画像を1枚だけ添付してください")
            return

        try:
            attachment = message.attachments[0]
            
            # 画像処理と切り抜き
            image_bytes = await attachment.read()
            image = Image.open(io.BytesIO(image_bytes))
            gray_image = image.convert('L')
            binary_image = gray_image.point(lambda x: 0 if x < 128 else 255, '1')
            cropped_img = binary_image.crop((44, 418, 44+448, 418+236))
            
            # 処理済み画像をバイト列に変換
            buffer = io.BytesIO()
            cropped_img.save(buffer, format="PNG")
            processed_image = buffer.getvalue()
            
            # 切り抜いた画像を送信
            await message.channel.send(file=discord.File(io.BytesIO(processed_image), filename="cropped_image.png"))
            
            # ChatGPTに画像を送信し、回答を取得
            for _ in range(3):
                response = ask_gpt(processed_image)
                if not response.startswith("```"):
                    await message.channel.send(f"```{response}```")
                    break
                else:
                    await message.channel.send("retrying...")
            else:
                await message.channel.send("エラー: 文字起こしに失敗しました")
        
        except Exception as e:
            await message.channel.send(f"エラー: 画像の処理中に問題が発生しました。{str(e)}")

# ChatGPTに画像の文字起こしを依頼
def ask_gpt(image):
    prompt = "この画像に表示された文字を文字起こししてください。回答以外の余計なものは一切出力しないでください。難しくても何度かトライしてください。あなたならできます。頑張ってください、応援しています。"
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(image).decode('utf-8')}",
                        }
                    }
                ],
            }
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content

client.run(DISCORD_BOT_TOKEN)

