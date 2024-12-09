import traceback
from typing import Optional
from discord.ext import commands
import discord
import aiohttp
import datetime
import credentials
from settings.config import color

class Errors(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, 'original', error)

        if isinstance(error, commands.MissingRequiredArgument):
            help_embed = discord.Embed(
                description=f"You are missing a required argument for the command `{ctx.command}`.",
                color=color
            )
            help_embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            help_embed.timestamp = datetime.datetime.utcnow()
            return await ctx.send(embed=help_embed)

        if isinstance(error, commands.BotMissingPermissions):
            permissions = ', '.join(perm for perm in error.missing_permissions)
            error_embed = discord.Embed(
                description=f"The bot needs {permissions} to execute this command.",
                color=color
            )
            error_embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            error_embed.timestamp = datetime.datetime.utcnow()
            return await ctx.send(embed=error_embed)

        if isinstance(error, commands.CommandOnCooldown):
            cooldown_embed = discord.Embed(
                description=f"You're on cooldown. Try again in {round(error.retry_after, 2)} seconds.",
                color=color
            )
            cooldown_embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            cooldown_embed.timestamp = datetime.datetime.utcnow()
            return await ctx.send(embed=cooldown_embed)

        if isinstance(error, commands.UserNotFound):
            user_not_found_embed = discord.Embed(
                description="The specified user was not found.",
                color=color
            )
            user_not_found_embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            user_not_found_embed.timestamp = datetime.datetime.utcnow()
            return await ctx.send(embed=user_not_found_embed)

        if isinstance(error, commands.MemberNotFound):
            member_not_found_embed = discord.Embed(
                description="The specified member was not found.",
                color=color
            )
            member_not_found_embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            member_not_found_embed.timestamp = datetime.datetime.utcnow()
            return await ctx.send(embed=member_not_found_embed)

        if isinstance(error, commands.RoleNotFound):
            role = error.argument
            role_not_found_embed = discord.Embed(
                description=f"The role `{role}` was not found.",
                color=color
            )
            role_not_found_embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            role_not_found_embed.timestamp = datetime.datetime.utcnow()
            return await ctx.send(embed=role_not_found_embed)

        if isinstance(error, commands.ChannelNotFound):
            channel = error.argument
            channel_not_found_embed = discord.Embed(
                description=f"The channel '{channel}' was not found.",
                color=color
            )
            channel_not_found_embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            channel_not_found_embed.timestamp = datetime.datetime.utcnow()
            return await ctx.send(embed=channel_not_found_embed)

        if isinstance(error, commands.MaxConcurrencyReached):
            max_concurrency_embed = discord.Embed(
                description=f"{ctx.author} {error}",
                color=color
            )
            max_concurrency_embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            max_concurrency_embed.timestamp = datetime.datetime.utcnow()
            return await ctx.send(embed=max_concurrency_embed)

        if isinstance(error, commands.CheckAnyFailure):
            for err in error.errors:
                if isinstance(err, commands.MissingPermissions):
                    permissions_embed = discord.Embed(
                        description=f"You don't have enough permissions to run the command `{ctx.command.qualified_name}`",
                        color=color
                    )
                    permissions_embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
                    permissions_embed.timestamp = datetime.datetime.utcnow()
                    return await ctx.send(embed=permissions_embed, delete_after=5)
                
        if isinstance(error, commands.CommandNotFound):
            return
        error_message = f"An error occurred in `{ctx.command}`:\n{error}"
        async with aiohttp.ClientSession() as session:
            webhook_data = {"content": error_message}
            async with session.post(credentials.error_url, json=webhook_data) as response:
                if response.status != 204:
                    print(f"Failed to send webhook: {response.status}")
            traceback.print_exc()

        if isinstance(error, commands.CheckFailure):
            return

async def setup(client):
    await client.add_cog(Errors(client))
