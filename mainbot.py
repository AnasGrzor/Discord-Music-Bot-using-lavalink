import discord
from discord.ext import commands
import wavelink
from wavelink.ext import spotify
import aiohttp
import asyncio
import typing as t
import config


client = commands.Bot(command_prefix="!", intents=discord.Intents.all())


class CustomPlayer(wavelink.Player):

    def __init__(self):
        super().__init__()
        self.queue = wavelink.Queue()
         
# HTTPS and websocket operations
@client.event
async def on_ready():
    client.loop.create_task(connect_nodes())
    # await connect_nodes()
    client.loop.create_task(check_voice_channels())
    print(f"Logged in as {client.user}")

async def connect_nodes(): # helper function
    await client.wait_until_ready()
    sc = spotify.SpotifyClient(
            client_id='',
            client_secret='',
        )
    # node: wavelink.Node = wavelink.Node(uri='lavalink.devamop.in', password='DevamOP')
    node: wavelink.Node = wavelink.Node(uri='http://localhost:2333/', password='youshallnotpass')

    await wavelink.NodePool.connect(client=client, nodes=[node], spotify=sc)
    await client.change_presence(status=discord.Status.idle,activity=discord.Activity(type = discord.ActivityType.listening, name = "\help" ))


async def check_voice_channels():
    while not client.is_closed():
        for vc in client.voice_clients:
            if len(vc.channel.members) <= 1:  # Only bot remains
                await asyncio.sleep(10)  # Wait for 5 seconds
                if len(vc.channel.members) <= 1:  # Still empty after waiting
                    await vc.disconnect()
        await asyncio.sleep(1) 

# events

@client.event
async def on_wavelink_node_ready(node: wavelink.Node):   
    print(f'Node: {node.id} is ready!')
    wavelink.Player.autoplay=True

# commands


@client.command(name="connect",aliases = ["join","summon","j"])
async def connect(ctx):
    vc = ctx.voice_client # represents a discord voice connection
    try:
        channel = ctx.author.voice.channel
    except AttributeError:
        return await ctx.send("Please join a voice channel to connect.")

    if not vc:
        await ctx.author.voice.channel.connect(cls=CustomPlayer())
        mbed=discord.Embed(title=f"Bot has landed in {channel}",color=discord.Color.teal())
        mbed.set_footer(text=f"Request made by {ctx.author}", icon_url=ctx.author.display_avatar)
        return await ctx.send(embed=mbed)
    else:
        await ctx.send("The bot is already connected to a voice channel")

#disconnects from the voice channel
@client.command(name="disconnect",aliases = ["leave","l"])
async def disconnect(ctx):
    vc = ctx.voice_client
    if vc:
        channel = ctx.author.voice.channel
        await vc.disconnect()
        mbed=discord.Embed(title=f"Bot has departed from {channel}",color=discord.Color.from_rgb(255,255,255))
        mbed.set_footer(text=f"Request made by {ctx.author}", icon_url=ctx.author.display_avatar)
        await ctx.send(embed=mbed)
    else:
        await ctx.send("The bot is not connected to a voice channel.")


@client.command() #pulls songs from youtube
async def play(ctx, *, search: str):
    vc = ctx.voice_client
    if not vc:
        custom_player = CustomPlayer()
        vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)
        vc.autoplay = True

    if not "https://www.youtube.com/playlist" in search:
            query = await wavelink.YouTubeMusicTrack.search(search)
            query = query[0]
    else:    
            print("YouTube playlist")
            playlist = await wavelink.YouTubePlaylist.search(search)
            tracks = playlist.tracks
            for track in tracks:
                    query = track
                    await vc.queue.put_wait(query)

                    if not vc.is_playing():
                        await vc.play(query)
                        await ctx.send("Playlist Added To Queue")

    # if isinstance(search, (wavelink.YouTubeTrack, wavelink.YouTubePlaylist, wavelink.YouTubeMusicTrack)):
    if vc.is_playing():
        vc.queue.put(query)
        mbed=discord.Embed(title=f"Queued {query} in {vc.channel}",color=discord.Color.blue(),url=query.uri,description=f"Queued \"{query.title}\"")
        mbed.set_thumbnail(url=f"{query.thumbnail}")
        mbed.set_footer(text=f"Request made by {ctx.author}", icon_url=ctx.author.display_avatar)
        return await ctx.send(embed=mbed)  
            
    else:
        await vc.play(query,populate=True)
        mbed=discord.Embed(title=f"Now Playing {query.title} ",color=discord.Color.purple(),url=query.uri,
                        description=f"Playing \"{query.title}\"" )
        mbed.set_thumbnail(url=f"{query.thumbnail}")
        mbed.set_footer(text=f"Request made by {ctx.author}", icon_url=ctx.author.display_avatar)
        return await ctx.send(embed=mbed)

@client.command() #pulls songs from soundclound
async def scplay(ctx, *, search: wavelink.SoundCloudTrack):
    vc = ctx.voice_client
    if not vc:
        custom_player = CustomPlayer()
        vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)
        vc.autoplay = True

    if vc.is_playing():

        vc.queue.put(item=search)
        mbed=discord.Embed(title=f"Queued {search} in {vc.channel}",color=discord.Color.blue(),url=search.uri,description=f"Queued \"{search.title}\"")
        mbed.set_footer(text=f"Request made by {ctx.author}", icon_url=ctx.author.display_avatar)
        return await ctx.send(embed=mbed)  
        
    else:
        await vc.play(search,populate=True)
        mbed=discord.Embed(title=f"Now Playing {search.title} ",color=discord.Color.purple(),url=search.uri,
                           description=f"Playing \"{search.title}\"" )
        mbed.set_footer(text=f"Request made by {ctx.author}", icon_url=ctx.author.display_avatar)
        return await ctx.send(embed=mbed)

@client.command(aliases = ["sp"]) #paste in a url from spotify can only use urls to search 
async def spotify_play(ctx: commands.Context, *, search: str):
    try:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    except discord.ClientException:
        vc: wavelink.Player = ctx.voice_client
        vc.autoplay = True
    if "https://open.spotify.com/playlist" in search or "https://open.spotify.com/album" in search:
                print("Playlist Detected")
                async for track in spotify.SpotifyTrack.iterator(query=search):
                   await vc.queue.put_wait(track)

                if not vc.is_playing():
                    await vc.play(track)
                
                await ctx.send("Playlist Added To Queue")
                return
                
    elif "https://open.spotify.com/track" in search:
                query = await spotify.SpotifyTrack.search(search)
                query = query[0]

    if not vc.is_playing():
        await vc.play(query, populate=True)
        mbed=discord.Embed(title=f"Now Playing {query.title} ",color=discord.Color.purple(),
                           description=f"Playing \"{query.title}\"")
        mbed.set_footer(text=f"Request made by {ctx.author}", icon_url=ctx.author.display_avatar)
        return await ctx.send(embed=mbed)
    else:
        await vc.queue.put_wait(query)
        mbed=discord.Embed(title=f"Queued {query} in {vc.channel}",color=discord.Color.blue(),description=f"Queued \"{search.title}\"")
        mbed.set_footer(text=f"Request made by {ctx.author}", icon_url=ctx.author.display_avatar)
        return await ctx.send(embed=mbed)  

#skips the current song
@client.command(aliases = ["Skip","SKIP"])
async def skip(ctx):
    vc = ctx.voice_client
    if vc:
        if not vc.is_playing():
            return await ctx.send("Nothing is playing.")
        if vc.queue.is_empty:
            return await vc.stop()

        await ctx.send(f"Skipped {vc.current}")
        await vc.stop()
        if vc.is_paused():
            await vc.resume()
    else:
        await ctx.send("The bot is not connected to a voice channel.")

#pause the current song
@client.command(name='pause' , aliases = ['p','PAUSE'])
async def pause(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.is_playing() and not vc.is_paused():
            await vc.pause()
            mbed=discord.Embed(title=f"Playback Paused",color=discord.Color.from_rgb(255,255,255))
            return await ctx.send(embed=mbed)  
        else:
            await ctx.send("Nothing is playing.")
    else:
        await ctx.send("The bot is not connected to a voice channel")

#resumes the current song
@client.command(name = "resume" , aliases = ['r','RESUME','Play'])
async def resume(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.is_paused():
            await vc.resume()
            mbed=discord.Embed(title=f"Playback Resumed ",color=discord.Color.from_rgb(255,255,255))
            return await ctx.send(embed=mbed)   
        else:
            await ctx.send("Nothing is paused.")
    else:
        await ctx.send("The bot is not connected to a voice channel")    
         
#stops the current song
@client.command()
async def stop(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.is_playing():
            await vc.stop()
            vc.autoplay = False
            mbed=discord.Embed(title=f"Playback Stopped ",color=discord.Color.from_rgb(255,255,255))
            return await ctx.send(embed=mbed) 
        else:
            await ctx.send("Nothing is paused.")
    else:
        await ctx.send("The bot is not connected to a voice channel")

#loops the current song
@client.command()
async def loop(ctx): 
    vc = ctx.voice_client
    if vc:
        if vc.is_playing():
            vc.queue.loop = True
            await ctx.send(f"Looped {vc.current}")
        else:
            await ctx.send("There is no audio playing to loop.")
    else:
        await ctx.send("I am not connected to a voice channel.")

#unloops the current song
@client.command()
async def dloop(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.is_playing():
            vc.queue.loop = False
            await ctx.send(f"Unlooped {vc.current}")
        else:
            await ctx.send("There is no audio playing to disable the loop for.")
    else:
        await ctx.send("I am not connected to a voice channel.")

# returns the current song playing
@client.command(name="nowPlaying" , aliases = ["np"])
async def nowPlaying(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.is_playing(): 
            mbed = discord.Embed(title=f"Now Playing {vc.current}",color=discord.Color.teal()) 
            mbed.set_thumbnail(url=f"{vc.current.thumbnail}")
            mbed.set_footer(text=f"Request made by {ctx.author}", icon_url=ctx.author.display_avatar)
            await ctx.send(embed=mbed)
        else:
            await ctx.send("There is no song playing.")
    else:
        await ctx.send("I am not connected to a voice channel.")

#disables autoplay     
@client.command(name="disableAutoplay", aliases = ["dauto"])
async def disableAutoplay(ctx): 
    vc = ctx.voice_client
    if vc:
        vc.autoplay = False
        mbed = discord.Embed(title="Autoplay disabled",color=discord.Color.red())
        return await ctx.send(embed=mbed)
    else:
        await ctx.send("I am not connected to a voice channel.")

#enables autoplay 
@client.command()
async def autoplay(ctx): 
    vc = ctx.voice_client
    if vc:
        vc.autoplay = True
        mbed = discord.Embed(title="Autoplay enabled",color=discord.Color.blue())
        return await ctx.send(embed=mbed)
    else:
        await ctx.send("I am not connected to a voice channel.")

@client.command()
async def shuffle(ctx): #shuffles the queue
    vc = ctx.voice_client
    if vc:
        vc.queue.shuffle()
        await ctx.send("Shuffle enabled")
    else:
        await ctx.send("I am not connected to a voice channel.")    

@client.command()
async def queue(ctx): # returns a list of the current queue
        vc = ctx.voice_client
        if vc:
            queue_summary = "\n".join([f"{index + 1}. {track.title}" for index, track in enumerate(vc.queue)])
            if queue_summary:
                for chunk in [queue_summary[i:i+2000] for i in range(0, len(queue_summary), 2000)]:
                    await ctx.send(chunk)
            else:
                await ctx.send("The queue is currently empty.")
            

@client.command()
async def clear(ctx): #clears the current queue
    vc = ctx.voice_client
    if vc:
        vc.queue.clear()
        await ctx.send("Queue Cleared")

@client.command()
async def volume(ctx, volume: int):
    if not 0 <= volume <= 100:
        await ctx.send("Volume must be between 0 and 100.")
        return

    player = ctx.voice_client
    if not player.is_connected:
        await ctx.send("I'm not connected to a voice channel.")
        return

    await player.set_volume(volume)
    await ctx.send(f"Volume set to {volume}.")

@client.command(aliases=['lyrc', 'lyric'])
async def lyrics(ctx, name: t.Optional[str]):
    vc = ctx.voice_client 
    name = name or vc.current.title
    lyrics_url = f"https://some-random-api.ml/lyrics?title={name}"  # Fix the URL
    async with ctx.typing():
        async with aiohttp.request("GET", lyrics_url) as r:
            if not 200 <= r.status <= 299:
                return await ctx.send(f"Error: Status code {r.status}")

            try:
                lyrics_data = await r.json()
                lyrics = lyrics_data.get("lyrics")

                if lyrics:
                    if len(lyrics) > 2000:
                        return await ctx.send("Lyrics are too long.")
                    await ctx.send(lyrics)
                else:
                    await ctx.send("Lyrics not found.")
            except Exception as e:
                await ctx.send(f"An error occurred: {e}")

@client.command()
async def jump(ctx, search: wavelink.YouTubeMusicTrack):
    vc = ctx.voice_client
    if vc:
        if vc.is_playing():
            await vc.stop()
            vc.queue.put(search)
            mbed=discord.Embed(title=f"Now Playing {search} in {vc.channel}",color=discord.Color.blue(),description=f"Playing \"{search.title}\"")
            mbed.set_thumbnail(url=f"{search.thumbnail}")
            mbed.set_footer(text=f"Request made by {ctx.author}", icon_url=ctx.author.display_avatar)
            return await ctx.send(embed=mbed)  

# error handling

@play.error
async def play_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Could not find a track.")
    else:
        await ctx.send(f"You encountered an error {error}")

@scplay.error
async def play_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Could not find a track.")
    else:
        await ctx.send(f"You encountered an error {error}")

@spotify_play.error
async def play_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Could not find a track.")
    else:
        await ctx.send(f"You encountered an error {error}")

client.run(config.token)
