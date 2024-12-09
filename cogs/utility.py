import discord
import typing
from discord.ext import commands
from settings.config import color
from discord.ui import Button, View
from typing import Optional, Union
import datetime
import requests
from credentials import token

class Utility(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.hybrid_command(aliases=['av'], description="Shows user's avatar")
    async def avatar(self, ctx, user: discord.User = None):
        if user is None:
            user = ctx.author
        if user.avatar is not None:
            embed = discord.Embed(color=color)
            embed.set_footer(text=f"Requested By {ctx.author}", icon_url=ctx.author.display_avatar.url)
            embed.set_image(url=user.avatar.url)
            embed.timestamp = datetime.datetime.utcnow()
            embed.set_author(name=user, icon_url=user.avatar.url)
            button = discord.ui.Button(label="Download", url=user.avatar.url)
            view = discord.ui.View().add_item(button)
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(f"This user doesn't have any avatar.")

    @commands.hybrid_command(aliases=['mc', 'members'], description="Shows member count in the server.")
    async def membercount(self, ctx):
        embed = discord.Embed(title="Member Count", description=f"{ctx.guild.member_count} Members", color=color)
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_group(invoke_without_command=True, description="Banner command for user and server.")
    async def banner(self, ctx):
        await ctx.send_help(ctx.command)

    @banner.command(description="Shows banner of a user.")
    async def user(self, ctx, user: discord.Member=None):
        if user is None:
            user = ctx.author
        user_info = await self.client.fetch_user(user.id)
        if user_info.banner is None:
            await ctx.send(f"This user doesn't have any banner.")
            return
        embed = discord.Embed(color=color)
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_image(url=user_info.banner.url)
        button = discord.ui.Button(label="Download", url=user_info.banner.url)
        view = discord.ui.View(timeout=None).add_item(button)
        await ctx.send(embed=embed, view=view)

    @banner.command(description="Shows banner of the server")
    async def server(self, ctx):
        if ctx.guild.banner is None:
            await ctx.send(f"This server doesn't have any banner.")
            return
        embed = discord.Embed(color=color)
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_image(url=ctx.guild.banner.url)
        button = discord.ui.Button(label="Download", url=ctx.guild.banner.url)
        view = discord.ui.View(timeout=None).add_item(button)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(aliases=["vanityinfo", "vi"], description="Get the information of a Vanity URL server.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def vanity(self, ctx, vanity: str = None):
        async def fetch_vanity_info(vanity):
            try:
                url = f"https://discord.com/api/v10/invites/{vanity}?with_counts=true&with_expiration=true"
                headers = {
                    "Authorization": f"Bot {token}"  
                }
                response = requests.get(url, headers=headers)
                return response.json() if response.status_code == 200 else None
            except Exception as error:
                print(f"Error fetching vanity info: {error}")
                return None

        def create_embed(data, ctx):
            embed = discord.Embed(
                title=data['guild']['name'],
                url=f"https://discord.gg/{data['code']}",
                color=color,
                description=data['guild'].get('description', '')
            )
            embed.set_thumbnail(
                url=f"https://cdn.discordapp.com/icons/{data['guild']['id']}/{data['guild']['icon']}.png?size=4096"
            )
            embed.set_footer(
                text=f"Requested By {ctx.author}",
                icon_url=ctx.author.display_avatar.url if ctx.author.display_avatar else ctx.author.default_avatar.url
            )
            embed.add_field(name="Vanity URL", value=f"discord.gg/{data['code']}", inline=True)
            embed.add_field(name="Guild ID", value=data['guild']['id'], inline=True)
            embed.add_field(name="Member Count", value=str(data['approximate_member_count']), inline=True)
            embed.add_field(name="Online Members", value=str(data['approximate_presence_count']), inline=True)
            embed.add_field(name="Boosts", value=str(data['guild']['premium_subscription_count']), inline=True)

            if 'channel' in data:
                embed.add_field(name="Invite Channel", value=data['channel']['name'], inline=True)

            if 'banner' in data['guild']:
                embed.set_image(
                    url=f"https://cdn.discordapp.com/banners/{data['guild']['id']}/{data['guild']['banner']}.png?size=4096"
                )

            if 'expires_at' in data:
                embed.add_field(
                    name="Expires At", 
                    value=str(data['expires_at']), 
                    inline=False
                )
            
            return embed

        if not vanity:
            if ctx.guild.vanity_url_code:
                vanity = ctx.guild.vanity_url_code
            else:
                await ctx.send("Please provide a vanity URL.")
                return

        data = await fetch_vanity_info(vanity)
        if not data:
            await ctx.send("Unable to fetch vanity info.")
            return
        embed = create_embed(data, ctx)
        await ctx.send(embed=embed)


    @commands.hybrid_command(name="purge", aliases=["pu"], description="Purges messages in the channel")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: Optional[int] = None, member: Optional[Union[discord.Member, discord.User]] = None):
        """Purges messages in the channel."""
        if amount is None and member is None:
            await ctx.send("Please specify the number of messages to purge or a specific user.")
            return

        if amount and amount < 1:
            await ctx.send("Please specify a valid number of messages to purge.")
            return

        def check(m):
            return m.author == member if member else True

        if amount:
            deleted = await ctx.channel.purge(limit=amount + 1, check=check)
            embed = discord.Embed(
                description=f"Successfully purged {len(deleted) - 1} messages.",
                color=self.color
            )
            await ctx.send(embed=embed, delete_after=5)
        else:
            deleted = await ctx.channel.purge(check=check)
            embed = discord.Embed(
                description=f"Successfully purged all messages from {member}.",
                color=self.color
            )
            await ctx.send(embed=embed, delete_after=5)


    @commands.hybrid_command(name="purge_bots", aliases=["purgebots", "pb"], description="Purges bot messages in the channel")
    @commands.has_permissions(manage_messages=True)
    async def purge_bots(self, ctx, amount: Optional[int] = None):
        """Purges bot messages in the channel."""
        if amount is None:
            await ctx.send("Please specify the number of bot messages to purge.")
            return

        if amount < 1:
            await ctx.send("Please specify a valid number of messages to purge.")
            return

        def check(m):
            return m.author.bot  

       
        deleted = await ctx.channel.purge(limit=amount + 1, check=check)
        embed = discord.Embed(
            description=f"Successfully purged {len(deleted) - 1} bot messages.",
            color=self.color
        )
        await ctx.send(embed=embed, delete_after=5)



    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild is None: 
            return
        if message.author.bot: 
            return
        if not message.content and not message.embeds and not message.attachments: 
            return
        self.sniped[message.channel.id] = message

    @commands.command(name="snipe", help="Snipes the most recent deleted message", usage="!snipe")
    async def snipe(self, ctx: commands.Context):
        message = self.sniped.get(ctx.channel.id)
        
        if message is None:
            return await ctx.send(embed=discord.Embed(
                title="Snipe",
                description="There are no recently deleted messages",
                color=discord.Color(0x2f3136)))  

        
        embed = discord.Embed(
            title=f"SNIPED MESSAGE SENT BY {message.author}",
            description=message.content or "This message had no text content.", 
            color=discord.Color(0x2f3136), 
            timestamp=message.created_at 
        )

       
        if message.attachments:
            embed.add_field(name="Attachments", value="\n".join([attachment.url for attachment in message.attachments]))

        await ctx.send(embed=embed) 



async def setup(client):
    await client.add_cog(Utility(client))
