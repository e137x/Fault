from discord.ext import commands
from discord.ext import tasks
import discord
import os
import wavelink
import pymongo
import aiosqlite
import credentials
from tools import context
from settings.config import *  

cache_flags = member_cache = discord.MemberCacheFlags(voice=True, joined=False)

class Fault(commands.AutoShardedBot):
    def __init__(self):

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.voice_states = True
        intents.dm_messages = True
        intents.guild_messages = True
        intents.guild_reactions = True
        intents.guild_scheduled_events = True
        intents.guild_typing = True
        intents.reactions = True

        super().__init__(
            command_prefix=self.get_prefix,  
            case_insensitive=True,
            intents=intents,
            max_messages=100,
            help_command=None,
            allowed_mentions=discord.AllowedMentions.none(),
            cache_flags=cache_flags, 
            chunk_guilds_at_startup=False
        )
        self.db_ready = False

    async def setup_hook(self):
        self.config = await aiosqlite.connect('database/prefix.db')
        
        await self.config.execute("CREATE TABLE IF NOT EXISTS config (guild INTEGER PRIMARY KEY, prefix TEXT)")
        await self.config.execute("CREATE TABLE IF NOT EXISTS Np (users INTEGER)")  
        await self.config.execute("CREATE TABLE IF NOT EXISTS Owner (user_id INTEGER PRIMARY KEY)")  
        await self.config.commit()
        
        self.db_ready = True

        await self.load_extension('jishaku')
        self.owner_ids = [1135190440744865802, 1212431696381612132]
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'[Loaded] `{filename}`')
                except Exception as e:
                    print(f'Failed to load {filename}: {e}')
        await self.tree.sync()


    async def get_prefix(client, message):
        async with client.config.execute("SELECT prefix FROM config WHERE guild = ?", (message.guild.id,)) as cursor:
            guild_row = await cursor.fetchone()

        async with client.config.execute("SELECT users FROM Np") as cursor:
            NP = await cursor.fetchall()

        prefix = guild_row[0] if guild_row else "."  

        if message.author.id in [int(i[0]) for i in NP]: 
            return sorted(commands.when_mentioned_or('', prefix)(client, message), reverse=True)
        else:
            return commands.when_mentioned_or(prefix)(client, message)


client = Fault()
client.cluster = pymongo.MongoClient(credentials.mongo_db_url)
client.db = client.cluster["Fault"]

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/help"))
    await node_connect()
    cache_sweeper.start()

async def node_connect():
    await client.wait_until_ready()
    try:
        nodes = [wavelink.Node(uri=credentials.wavelink_uri, password=credentials.wavelink_password)]
        await wavelink.Pool.connect(nodes=nodes, client=client)
        print("Successfully connected to Lavalink node.")
    except Exception as e:
        print(f"Failed to connect to Lavalink node: {e}")

@tasks.loop(minutes=60)
async def cache_sweeper():
    client._connection._private_channels.clear()
    client._connection._users.clear()
    client._connection._messages.clear()
    print("Cleared Cache")

@client.event
async def on_command_completion(context: commands.Context) -> None:
    full_command_name = context.command.qualified_name
    split = full_command_name.split("\n")
    executed_command = str(split[0])
    karma = discord.SyncWebhook.from_url(credentials.commandlog_URL)  

    if not context.message.content.startswith("."):
        pcmd = f"`.{context.message.content}`"
    else:
        pcmd = f"`{context.message.content}`"
        
    if context.guild is not None:
        try:
            embed = discord.Embed(color=0x2F3136)
            embed.set_author(
                name=f"Executed {executed_command} Command By: {context.author}",
                icon_url=context.author.avatar.url
            )
            embed.set_thumbnail(url=context.author.avatar.url)
            embed.add_field(
                name="Command Name:", value=f"{executed_command}", inline=False
            )
            embed.add_field(
                name="Command Content:", value="{}".format(pcmd), inline=False
            )
            embed.add_field(
                name="Command Executed By:",
                value=f"{context.author} | ID: [{context.author.id}](https://discord.com/users/{context.author.id})",
                inline=False,
            )
            embed.add_field(
                name="Command Executed In:",
                value=f"{context.guild.name} | ID: [{context.guild.id}](https://discord.com/guilds/{context.guild.id})",
                inline=False,
            )
            embed.add_field(
                name="Command Executed In Channel:",
                value=f"{context.channel.name} | ID: [{context.channel.id}](https://discord.com/channel/{context.channel.id})",
                inline=False,
            )
            embed.set_footer(
                text=f"Thank you for choosing {client.user.name}",
                icon_url=client.user.display_avatar.url,
            )
            karma.send(embed=embed)
        except Exception as e:
            print(f"Error occurred: {e}")
    else:
        try:
            embed1 = discord.Embed(color=0x2F3136)
            embed1.set_author(
                name=f"Executed {executed_command} Command By: {context.author}",
                icon_url=context.author.avatar.url
            )
            embed1.set_thumbnail(url=context.author.avatar.url)
            embed1.add_field(
                name="Command Name:", value=f"{executed_command}", inline=False
            )
            embed1.add_field(
                name="Command Executed By:",
                value=f"{context.author} | ID: [{context.author.id}](https://discord.com/users/{context.author.id})",
                inline=False,
            )
            embed1.set_footer(
                text=f"Thank you for choosing {client.user.name}",
                icon_url=client.user.display_avatar.url,
            )
            karma.send(embed=embed1)
        except Exception as e:
            print(f"Error occurred: {e}")

import logging
logging.basicConfig(level=logging.INFO)

if __name__=="__main__":
    client.run(credentials.token)
    if KeyboardInterrupt:
        os._exit(0)
