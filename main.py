import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import os
import asyncio
import time

token = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

queue = asyncio.Queue()
currentfile = None
currentTitle = None

def delete_file(path):
    time.sleep(5)
    # 再生が終了した後にファイルを削除する関数
    try:
        os.remove(path)
        print(f"Deleted file: {path}")
    except Exception as e:
        print(f"Error deleting file {path}: {e}")

@bot.event
async def on_ready():
    print(f'ログインしました。Bot名: {bot.user.name}')
    if not os.path.exists('tmp'):
        os.makedirs('tmp')

@bot.command()
async def search(ctx, *, search_query):
    # 検索して一番上の結果のURLを渡す
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'extract_flat': 'in_playlist'
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{search_query}", download=False)['entries'][0]
    
    if info:
        url = info['url']
        title = info.get('title', 'Unknown title')
        await ctx.send(f"🔍見つかったよ🔍\n☛ {title}\n{url}")
        await play(ctx, url)
    else:
        await ctx.send("🔍検索したけど見つからなかったよ🔍")

@bot.command()
async def play(ctx, url):
    # URLから音声をダウンロードして再生する
    global currentfile
    if not ctx.message.author.voice:
        await ctx.send('まずボイスチャンネルに参加してネ!!')
        return

    await queue.put(url)
    await ctx.send("➕キューに追加したよ➕")
    if not ctx.guild.voice_client or not ctx.guild.voice_client.is_playing():
        await play_next(ctx)

async def play_next(ctx):
    global currentfile
    global currentfile
    if not ctx.message.author.voice:
        await ctx.send('まずボイスチャンネルに参加してネ!!')
        return

    channel = ctx.message.author.voice.channel
    if voice_client := ctx.guild.voice_client:
        await voice_client.move_to(channel)
    else:
        voice_client = await channel.connect()

    if queue.empty():
        await ctx.send("再生キューは空っぽだよ")
        return

    url = await queue.get()
    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': 'tmp/%(id)s.%(ext)s',  # ダウンロードするファイルのパスとフォーマット
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  # 音声を抽出
            'preferredcodec': 'opus',
            'preferredquality': '96',  # 96kbpsのopusに変換
        }],
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        audio_path = os.path.join('tmp', f"{info['id']}.opus")  # ダウンロードしたファイルのパス
        currentTitle = info["title"]
        currentfile = audio_path

    def after_play(error):
        delete_file(audio_path)
        currentfile = None
        currentTitle = None
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    voice_client.play(discord.FFmpegPCMAudio(audio_path), after=lambda e: after_play(e))

    await ctx.send(f'▶ {info["title"]}')

@bot.command()
async def stop(ctx):
    global currentfile
    global currentTitle
    # 音声の再生を停止し、ボイスチャンネルから切断します。
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send('停止したよ')
        currentTitle = None
        currentfile = None
    else:
        await ctx.send('何も再生されてないよ')

@bot.command()
async def pause(ctx):
    # 一時停止/再開する
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send('一時停止したよ')
    elif voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send('再開したよ')
    else:
        await ctx.send('再生されてないよ')

@bot.command()
async def skip(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send('スキップしたよ')
        await play_next(ctx)
    else:
        await ctx.send('再生されてないよ')

@bot.event
async def on_voice_state_update(member, before, after):
    # ボイスチャンネルにBOT以外がいなくなったら抜ける
    # メンバーがボイスチャンネルから離れたか、別のチャンネルに移動した場合に実行
    if before.channel is not None and (after.channel is None or after.channel != before.channel):
        # before.channelには、メンバーが離れたボイスチャンネルの情報が含まれています
        # チャンネル内のメンバー数を確認
        if len(before.channel.members) == 1:
            # ボット自身がそのチャンネルに接続しているか確認
            voice_client = discord.utils.get(bot.voice_clients, channel=before.channel)
            if voice_client is not None:
                # チャンネルから抜ける
                await voice_client.disconnect()
                print(f"{before.channel.name}から抜けました。")

@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()

@bot.command()
async def cat(ctx):
    # playing NyanCat
    await play(ctx, 'https://www.youtube.com/watch?v=2yJgwwDcgV8')

@bot.command()
async def now_playing(ctx):
    # 現在再生中の曲の情報を表示する
    if currentfile:
        await ctx.send(f"なうぷれ: {currentTitle}")
    else:
        await ctx.send("再生中の曲はないよ")

bot.run(token=token)
