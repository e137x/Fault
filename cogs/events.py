import discord
from discord.ext import commands
import aiohttp
from settings.config import color
import credentials
from datetime import datetime, timedelta
from discord.utils import utcnow


class events(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: discord.Guild):
        if guild.id in [1239544756824969259]:
            return

        elif guild.member_count < 0:
            await guild.leave()
        else:
            invite = await guild.text_channels[0].create_invite(
                max_age=0, max_uses=0, unique=True
            )
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(
                    url=credentials.guild_join, session=session
                )
                embed = discord.Embed(
                    title="Joined A Guild",
                    description=f"**ID:** {guild.id}\n**Name:** {guild.name}\n**MemberCount:** {len(guild.members)}\n**Created:** <t:{int(guild.created_at.timestamp())}:R>",
                    color=color,
                )
                embed.add_field(name="Invite Link", value=invite.url)
                await webhook.send(embed=embed)
            try:
                owner = await self.client.fetch_user(guild.owner_id)
                thank_you_embed = discord.Embed(
                    title="Thank You for Adding Me!",
                    description=f"Hi {owner.name},\n\nThank you for adding me to **{guild.name}**! I'm here to assist you and your server. If you need any help or have any questions, feel free to ask.\n\nBest regards,\n**{self.client.user.name}**",
                    color=color,
                )
                thank_you_embed.set_thumbnail(url=self.client.user.display_avatar.url)
                invite_button = discord.ui.Button(
                label="Invite",
                style=discord.ButtonStyle.link,
                emoji="<:instance:1297151161601626122>",
                url=f"https://discord.com/oauth2/authorize?client_id={self.client.user.id}&permissions=8&scope=bot%20applications.commands",
                )
                support_button = discord.ui.Button(
                    label="Support",
                    style=discord.ButtonStyle.link,
                    emoji="<:management:1297151122888196096>",
                    url=credentials.support_url,  
                )
                view = discord.ui.View()
                view.add_item(support_button)
                view.add_item(invite_button)

                content = "https://discord.gg/jsk"
                await owner.send(embed=thank_you_embed, content=content, view=view)
            except Exception as e:
                pass

    @commands.Cog.listener("on_guild_remove")
    async def on_guild_remove(self, guild: discord.Guild):
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(url=credentials.guild_leave, session=session)
            embed = discord.Embed(
                title="Left A Guild",
                description=f"**ID:** {guild.id}\n**Name:** {guild.name}\n**MemberCount:** {len(guild.members)}\n**Created:** <t:{int(guild.created_at.timestamp())}:R>",
                color=color,
            )
            await webhook.send(embed=embed)

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: discord.Member):
        try:
            if member.bot:
                return

            account_creation_date = member.created_at
            one_month_ago = utcnow() - timedelta(days=30)  

            if account_creation_date > one_month_ago:
                return

            embed = discord.Embed(
                description=(f"- Thanks for joining **{member.guild.name}**! I'm **{self.client.user.name}**, "
                            f"the best music bot here. You can Add me to your server [click here](https://discord.com/oauth2/authorize?client_id={self.client.user.id}&permissions=8&scope=bot%20applications.commands)."),
                color=color,
            )
            embed.set_thumbnail(url=member.avatar.url)
            embed.set_author(name=member.name, icon_url=member.avatar.url)
            embed.set_footer(   
            text=f"You are the {member.guild.member_count}th member in this server!",
            icon_url=member.avatar.url 
            )

            invite_button = discord.ui.Button(
                label="Invite",
                style=discord.ButtonStyle.link,
                emoji="<:instance:1297151161601626122>",
                url=f"https://discord.com/oauth2/authorize?client_id={self.client.user.id}&permissions=8&scope=bot%20applications.commands",
            )
            support_button = discord.ui.Button(
                label="Support",
                style=discord.ButtonStyle.link,
                emoji="<:management:1297151122888196096>",
                url=credentials.support_url,  
            )

            view = discord.ui.View()
            view.add_item(support_button)
            view.add_item(invite_button)

            content = "https://discord.gg/jsk"

            try:
                await member.send(content=content, embed=embed, view=view)
            except discord.Forbidden:
                pass
        except Exception as e:
            pass


async def setup(client):
    await client.add_cog(events(client))
