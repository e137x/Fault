import discord
from discord.ext import commands
from discord.interactions import Interaction
from discord.ui import Button, View
import discord
import time
import aiosqlite

from settings.config import color
from tools.paginator import PaginatorView

DB_PATH = "database/autoresponder.db"

class AutoResponder(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.client.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        """Initializes the database and creates the necessary table if it doesn't exist."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS auto_res (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    name TEXT,
                    content TEXT,
                    time INTEGER
                )
            """)
            await db.commit()

    async def fetch_autoresponders(self, guild_id):
        """Fetches all auto-responders for a specific guild."""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT name, id, content FROM auto_res WHERE guild_id = ?", (guild_id,)) as cursor:
                return await cursor.fetchall()

    async def insert_autoresponder(self, guild_id, name, content):
        """Inserts a new auto-responder for a specific guild."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO auto_res (guild_id, name, content, time) VALUES (?, ?, ?, ?)",
                (guild_id, name, content, round(time.time()))
            )
            await db.commit()

    async def delete_autoresponder_by_name(self, guild_id, name):
        """Deletes an auto-responder by its name for a specific guild."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM auto_res WHERE guild_id = ? AND name = ?", (guild_id, name))
            await db.commit()

    async def delete_autoresponder_by_id(self, guild_id, responder_id):
        """Deletes an auto-responder by its ID for a specific guild."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM auto_res WHERE guild_id = ? AND id = ?", (guild_id, responder_id))
            await db.commit()

    def has_required_role(self, user):
        """Check if the user has the required role."""
        required_role_id = 1302275903912546335
        return any(role.id == required_role_id for role in user.roles)

    @commands.hybrid_group(description="Auto responder commands", aliases=['ar'])
    async def autoresponder(self, ctx):
        embed = discord.Embed(
            description=( 
                "autoresponder create <trigger> <response>\n-# To create an autoresponder.\n"
                "autoresponder delete <trigger>\n-# To delete an autoresponder.\n"
                "autoresponder list\n-# To get the list of autoresponder."
            ),
            color=color
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

    @autoresponder.command(name="create", description="Creates an auto responder.")
    async def ar_create(self, ctx, trigger, *, content: str):
        """Creates an autoresponder."""
        if not self.has_required_role(ctx.author):
            embed = discord.Embed(
                description=f"{ctx.author}, you do not have the required role to use this command.",
                color=color
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed, ephemeral=True)

        ar_list = [ar[0].lower() for ar in await self.fetch_autoresponders(ctx.guild.id)]

        if len(ar_list) == 5:
            embed = discord.Embed(
                description=f"{ctx.author} This server has reached the maximum limit.",
                color=color
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)

        if trigger.lower() in ar_list:
            embed = discord.Embed(
                description=f"{ctx.author} An auto responder with the same name already exists. Try a different name.",
                color=color
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed, delete_after=5)

        await self.insert_autoresponder(ctx.guild.id, trigger.lower(), content)
        embed = discord.Embed(
            description=f"Successfully created an autoresponder with the trigger: `{trigger}`",
            color=color
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @autoresponder.command(name="delete", description="Deletes an auto responder.")
    async def ar_delete(self, ctx, autoresponder):
        """Deletes an autoresponder."""
        if not self.has_required_role(ctx.author):
            embed = discord.Embed(
                description=f"{ctx.author}, you do not have the required role to use this command.",
                color=color
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed, ephemeral=True)

        ar_list = await self.fetch_autoresponders(ctx.guild.id)
        name_list = [ar[0] for ar in ar_list]
        id_list = [str(ar[1]) for ar in ar_list]

        if autoresponder.lower() in name_list:
            await self.delete_autoresponder_by_name(ctx.guild.id, autoresponder.lower())
            embed = discord.Embed(
                description=f"Successfully deleted an autoresponder: `{autoresponder}`",
                color=color
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        elif autoresponder.lower() in id_list:
            await self.delete_autoresponder_by_id(ctx.guild.id, int(autoresponder))
            embed = discord.Embed(
                description=f"Successfully deleted an autoresponder: `{autoresponder}`",
                color=color
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description=f"{ctx.author} Auto responder not found.",
                color=color
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed, delete_after=5)

    @autoresponder.command(name="list", description="Lists all auto responders.")
    async def ar_list(self, ctx):
        """Lists all autoresponders."""
        if not self.has_required_role(ctx.author):
            embed = discord.Embed(
                description=f"{ctx.author}, you do not have the required role to use this command.",
                color=color
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed, ephemeral=True)

        ar_list = await self.fetch_autoresponders(ctx.guild.id)
        if not ar_list:
            embed = discord.Embed(
                description="No auto responders have been created for this server.",
                color=color
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
            return

        embeds = []
        for chunk in discord.utils.as_chunks(list(enumerate(ar_list, start=1)), 20):
            embed = discord.Embed(color=color)
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.description = '\n'.join(f'`[{i}]` {name}   (ID - {id})' for i, (name, id, _) in chunk)
            embeds.append(embed)

        view = PaginatorView(embeds, self.bot, ctx.author)
        if len(embeds) > 1:
            await ctx.send(embed=view.initial, view=view)
        else:
            await ctx.send(embed=embeds[0])

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listens for messages to trigger an autoresponder."""
        if message.author.bot or not message.guild:
            return

        ar_list = await self.fetch_autoresponders(message.guild.id)
        for trigger, _, content in ar_list:
            if trigger.lower() == message.content.lower():
                await message.channel.send(content)
                break

async def setup(client):
    await client.add_cog(AutoResponder(client))
