import discord
from discord.ext import commands
import aiosqlite
from settings.config import color

class SetPrefix(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def cog_load(self):
        self.config = await aiosqlite.connect('database/prefix.db')
        await self.config.execute("CREATE TABLE IF NOT EXISTS config (guild INTEGER PRIMARY KEY, prefix TEXT)")
        await self.config.commit()

    @commands.hybrid_command(
        name="setprefix", 
        aliases=["changeprefix", "prefix"], 
        usage="/setprefix <new_prefix>", 
        help="Change the bot's prefix for this server."
    )
    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(send_messages=True)
    async def set_prefix(self, ctx: commands.Context, new_prefix: str):
        """
    Change the bot's prefix for this server.

    This command allows server administrators to set a custom command prefix for the bot within their server. The prefix is stored in the bot's configuration for the server.

    Arguments:
    - `new_prefix`: The new prefix to be set for the bot in the current server.

    Behavior:
    - The prefix must not be empty or exceed 10 characters.
    - The user executing the command must have a role that is higher than the bot’s role to change the prefix.
    - The new prefix is stored in the bot's configuration for the server.
    - The bot responds with an embedded message confirming the change or providing an error if the conditions are not met.

    Permissions:
    - Requires the `administrator` permission for the user.
    - The bot must have the `send_messages` permission in the server.

    Cooldown:
    - 1 usage every 5 seconds per guild.

    Usage:
    - `/setprefix <new_prefix>`: Changes the bot's command prefix for the current server.
    - Aliases: `changeprefix`, `prefix`
    """
        embed = discord.Embed(color=color)
        embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.avatar.url)

        if not new_prefix:
            embed.description = "Prefix cannot be empty."
            await ctx.send(embed=embed, ephemeral=True)
            return

        if len(new_prefix) > 10:
            embed.description = "Prefix cannot be longer than 10 characters."
            await ctx.send(embed=embed, ephemeral=True)
            return

        if ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed.description = "You must have a role above me to change the prefix."
            await ctx.send(embed=embed, ephemeral=True)
            return

        await self.config.execute("INSERT OR REPLACE INTO config (guild, prefix) VALUES (?, ?)", (ctx.guild.id, new_prefix))
        await self.config.commit()

        embed.description = f"Changed Prefix To `{new_prefix}`"
        await ctx.send(embed=embed)

    async def cog_unload(self):
        await self.config.close()

async def setup(client):
    await client.add_cog(SetPrefix(client))
