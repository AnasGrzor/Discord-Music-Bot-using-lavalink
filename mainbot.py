import discord
from discord.ext import commands
import wavelink

client = commands.Bot(command_prefix="!", intents=discord.Intents.all())


class CustomPlayer(wavelink.Player):
#sets up the queue function 
    def __init__(self):
        super().__init__()
        self.queue = wavelink.Queue()


# HTTPS and websocket operations
@client.event
async def on_ready():
    client.loop.create_task(connect_nodes())


async def connect_nodes(): # helper function
    await client.wait_until_ready()

    node: wavelink.Node = wavelink.Node(uri='http://localhost:2333/', password='youshallnotpass')

    await wavelink.NodePool.connect(client=client, nodes=[node])
    wavelink.Player.autoplay=True
    wavelink.Player.auto_queue=True
    await client.change_presence(status=discord.Status.idle,activity=discord.Activity(type = discord.ActivityType.listening, name = "\help" ))


embedred = "#FF0000"

# commands

#join command
@client.command(name="connect",aliases = ["join","summon"])
async def connect(ctx):
    vc = ctx.voice_client # represents a discord voice connection
    try:
        channel = ctx.author.voice.channel
    except AttributeError:
        return await ctx.send("Please join a voice channel to connect.")

    if not vc:
        await ctx.author.voice.channel.connect(cls=CustomPlayer())
        mbed=discord.Embed(title=f"Bot has landed in {channel}",color=discord.Color.from_str(embedred))
        mbed.set_author(name = ctx.author.display_name)
        return await ctx.send(embed=mbed)
    else:
        await ctx.send("The bot is already connected to a voice channel")

#disconnect command
@client.command(name="disconnect",aliases = ["leave"])
async def disconnect(ctx):
    vc = ctx.voice_client
    if vc:
        channel = ctx.author.voice.channel
        await vc.disconnect()
        mbed=discord.Embed(title=f"Bot has departed from {channel}",color=discord.Color.from_rgb(255,255,255))
        mbed.set_author(name = ctx.author.display_name)
        return await ctx.send(embed=mbed) 
    else:
        await ctx.send("The bot is not connected to a voice channel.")

#play command
@client.command()
async def play(ctx, *, search: wavelink.YouTubeTrack):
    vc = ctx.voice_client
    if not vc:
        custom_player = CustomPlayer()
        vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)

    if vc.is_playing():

        vc.queue.put(item=search)
        vc.auto_queue
        mbed=discord.Embed(title=f"Queued {search} in {vc.channel}",color=discord.Color.blue())
        return await ctx.send(embed=mbed)  
        
    else:
        await vc.play(search)
        mbed=discord.Embed(title=f"Now Playing {search} ",description=f"Added By {ctx.author.display_name}" ,color=discord.Color.from_rgb(255,255,255))
        mbed.set_thumbnail(url=f"{search.thumbnail}")
        return await ctx.send(embed=mbed)
        
#skip command
@client.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc:
        if not vc.is_playing():
            return await ctx.send("Nothing is playing.")
        if vc.queue.is_empty:
            return await vc.stop()

        await vc.stop()
        await ctx.send("Song Skipped")
        if vc.is_paused():
            await vc.resume()
    else:
        await ctx.send("The bot is not connected to a voice channel.")

#pause command
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

#resume command
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
         
#stop command
@client.command()
async def stop(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.is_playing():
            await vc.stop()
            mbed=discord.Embed(title=f"Playback Stopped ",color=discord.Color.from_rgb(255,255,255))
            return await ctx.send(embed=mbed) 
        else:
            await ctx.send("Nothing is paused.")
    else:
        await ctx.send("The bot is not connected to a voice channel")


# error handling

@play.error
async def play_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Could not find a track.")
    else:
        await ctx.send("Please join a voice channel.")


client.run("Your Token here")
