import discord
from discord.ext import commands
import aiosqlite
import aiohttp
from settings.config import *
import credentials



def extraowner():
    async def predicate(ctx: commands.Context):
        async with aiosqlite.connect("database/prefix.db") as con:
            async with con.execute("SELECT user_id FROM Owner") as cursor:
                ids_ = await cursor.fetchall()
                if ctx.author.id in [i[0] for i in ids_]:
                    return True
                else:
                    return False

    return commands.check(predicate)


class owner(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.color = color

    @commands.Cog.listener()
    async def on_ready(self):
        print("Owner Is Ready")

    @commands.hybrid_group(hidden=True, invoke_without_command=True)
    @commands.is_owner()
    async def owner(self, ctx):
        await ctx.reply("Lund lele")

    @owner.command(name="add")
    @commands.is_owner()
    async def ownerkrdu(self, ctx, user: discord.User):
        async with aiosqlite.connect("database/prefix.db") as con:
            async with con.execute("SELECT user_id FROM Owner") as cursor:
                re = await cursor.fetchall()
                if re != []:
                    ids = [int(i[0]) for i in re]
                    if user.id in ids:
                        embed = discord.Embed(
                            description=f"That user is already in owner list.", color=self.color
                        )
                        await ctx.reply(embed=embed, mention_author=False)
                        return
            await con.execute("INSERT INTO Owner(user_id) VALUES(?)", (user.id,))
            embed = discord.Embed(
                description=f"Successfully added **{user}** in owner list.",
                color=self.color,
            )
            await ctx.reply(embed=embed, mention_author=False)
            await con.commit()

    @owner.command(name="remove")
    @commands.is_owner()
    async def ownerhatadu(self, ctx, user: discord.User):
        async with aiosqlite.connect("database/prefix.db") as con:
            async with con.execute("SELECT user_id FROM Owner") as cursor:
                re = await cursor.fetchall()
                if re == []:
                    embed = discord.Embed(
                        description=f"That user is not in owner list.", color=self.color
                    )
                    await ctx.reply(embed=embed, mention_author=False)
                    return
            ids = [int(i[0]) for i in re]
            if user.id not in ids:
                embed = discord.Embed(
                    description=f"That user is not in owner list.", color=self.color
                )
                await ctx.reply(embed=embed, mention_author=False)
                return
            await con.execute("DELETE FROM Owner WHERE user_id = ?", (user.id,))
            embed = discord.Embed(
                description=f"Successfully removed **{user}** from owner list.",
                color=self.color,
            )
            await ctx.reply(embed=embed, mention_author=False)
            await con.commit()

    @commands.hybrid_group(
        description="Noprefix Commands",
        aliases=["np"],
        invoke_without_command=True,
        hidden=True,
    )
    @commands.check_any(commands.is_owner(), extraowner())
    async def noprefix(self, ctx):
        await ctx.reply("")

    @noprefix.command(name="add", description="Adds a user to noprefix.")
    @commands.check_any(commands.is_owner(), extraowner())
    async def noprefix_add(self, ctx, user: discord.User):
        async with aiosqlite.connect("database/prefix.db") as con:
            async with con.execute("SELECT users FROM Np") as cursor:
                result = await cursor.fetchall()
                if user.id not in [int(i[0]) for i in result]:
                    await con.execute(f"INSERT INTO Np(users) VALUES(?)", (user.id,))
                    embed = discord.Embed(
                        description=f"Successfully added **{user}** to no prefix.",
                        color=self.color,
                    )
                    await ctx.reply(embed=embed, mention_author=False)
                    
                    async with aiohttp.ClientSession() as session:
                        webhook = discord.Webhook.from_url(url=credentials.np_hook, session=session)
                        embed = discord.Embed(
                            title="No Prefix Added",
                            description=f"**Action By:** {ctx.author} ({ctx.author.id})\n**User:** {user} ({user.id})",
                            color=self.color,
                        )
                        await webhook.send(embed=embed)
                else:
                    embed = discord.Embed(
                        description=f"That user is already in no prefix.", color=self.color
                    )
                    await ctx.reply(embed=embed, mention_author=False)
            await con.commit()

    @noprefix.command(name="remove", description="Removes a user from noprefix.")
    @commands.check_any(commands.is_owner(), extraowner())
    async def noprefix_remove(self, ctx, user: discord.User):
        async with aiosqlite.connect("database/prefix.db") as con:
            async with con.execute("SELECT users FROM Np") as cursor:
                result = await cursor.fetchall()
                if user.id in [int(i[0]) for i in result]:
                    await con.execute(f"DELETE FROM Np WHERE users = ?", (user.id,))
                    embed = discord.Embed(
                        description=f"Successfully removed **{user}** from no prefix.",
                        color=self.color,
                    )
                    await ctx.reply(embed=embed, mention_author=False)
                    
                    async with aiohttp.ClientSession() as session:
                        webhook = discord.Webhook.from_url(url=credentials.np_hook, session=session)
                        embed = discord.Embed(
                            title="No Prefix Removed",
                            description=f"**Action By:** {ctx.author} ({ctx.author.id})\n**User:** {user} ({user.id})",
                            color=self.color,
                        )
                        await webhook.send(embed=embed)
                else:
                    embed = discord.Embed(
                        description=f"That user isn't in no prefix.", color=self.color
                    )
                    await ctx.reply(embed=embed, mention_author=False)
            await con.commit()


    @commands.command(aliases=["guildleave"])
    @commands.check_any(commands.is_owner())
    async def gleave(self, ctx, guild_id: int):
            guild = self.client.get_guild(guild_id)
            if guild is None:
                guild = ctx.guild

            await guild.leave()
            await ctx.send(f"Left guild: {guild.name}")


    @commands.command(aliases=["link"])
    @commands.check_any(commands.is_owner())
    async def ginv(self, ctx, guild_id: int):
        guild = self.client.get_guild(guild_id)

        if guild is None:
            await ctx.send("Guild not found.")
            return

        if not ctx.me.guild_permissions.create_instant_invite:
            await ctx.send("I don't have permission to create invites in this guild.")
            return

        for channel in guild.text_channels:
            try:
                invite_link = await channel.create_invite(unique=False)
                await ctx.send(f"**Here is the Invite link:** \n {invite_link}")
                return  
            except Exception as e:
                await ctx.send(f"An error occurred: {e}")
                continue
        await ctx.send("Couldn't create an invite for this server.")


async def setup(client):
    await client.add_cog(owner(client))