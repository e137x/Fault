import discord
from discord.ext import commands
from discord import app_commands


class Voice(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.hybrid_group(name="voice", description="Voice channel moderation commands.")
    @app_commands.default_permissions(moderate_members=True)
    async def voice(self, ctx):
        if not ctx.invoked_subcommand:
            return

    @voice.command(name="mute", description="Mute a user in the voice channel.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mute(self, ctx, member: discord.Member, *, reason: str = None):
        reason = reason or "[No reason]"
        await member.edit(mute=True, reason=f"By {ctx.author}: {reason}")
        await ctx.send(f"**Voice muted {member.mention}**", allowed_mentions=discord.AllowedMentions.none())

    @voice.command(name="unmute", description="Unmute a user in the voice channel.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unmute(self, ctx, member: discord.Member, *, reason: str = None):
        reason = reason or "[No reason]"
        await member.edit(mute=False, reason=f"By {ctx.author}: {reason}")
        await ctx.send(f"**Voice unmuted {member.mention}**", allowed_mentions=discord.AllowedMentions.none())

    @voice.command(name="deafen", description="Deafen a user in the voice channel.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def deafen(self, ctx, member: discord.Member, *, reason: str = None):
        reason = reason or "[No reason]"
        await member.edit(deafen=True, reason=f"By {ctx.author}: {reason}")
        await ctx.send(f"**Voice deafened {member.mention}**", allowed_mentions=discord.AllowedMentions.none())

    @voice.command(name="undeafen", description="Undeafen a user in the voice channel.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def undeafen(self, ctx, member: discord.Member, *, reason: str = None):
        reason = reason or "[No reason]"
        await member.edit(deafen=False, reason=f"By {ctx.author}: {reason}")
        await ctx.send(f"**Voice undeafened {member.mention}**", allowed_mentions=discord.AllowedMentions.none())

    @voice.command(name="muteall", description="Mute all users in your voice channel.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def muteall(self, ctx, *, reason: str = None):
        reason = reason or "[No reason]"
        if not ctx.author.voice:
            await ctx.send("You're not in a voice channel.")
            return

        voice_channel = ctx.author.voice.channel
        muted_count = 0
        for member in voice_channel.members:
            if not member.voice.mute:
                await member.edit(mute=True, reason=f"By {ctx.author}: {reason}")
                muted_count += 1

        await ctx.send(f"**Voice muted {muted_count} users in {voice_channel.name}**")

    @voice.command(name="unmuteall", description="Unmute all users in your voice channel.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unmuteall(self, ctx, *, reason: str = None):
        reason = reason or "[No reason]"
        if not ctx.author.voice:
            await ctx.send("You're not in a voice channel.")
            return

        voice_channel = ctx.author.voice.channel
        unmuted_count = 0
        for member in voice_channel.members:
            if member.voice.mute:
                await member.edit(mute=False, reason=f"By {ctx.author}: {reason}")
                unmuted_count += 1

        await ctx.send(f"**Voice unmuted {unmuted_count} users in {voice_channel.name}**")

    @voice.command(name="deafenall", description="Deafen all users in your voice channel.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def deafenall(self, ctx, *, reason: str = None):
        reason = reason or "[No reason]"
        if not ctx.author.voice:
            await ctx.send("You're not in a voice channel.")
            return

        voice_channel = ctx.author.voice.channel
        deafened_count = 0
        for member in voice_channel.members:
            if not member.voice.deaf:
                await member.edit(deafen=True, reason=f"By {ctx.author}: {reason}")
                deafened_count += 1

        await ctx.send(f"**Voice deafened {deafened_count} users in {voice_channel.name}**")

    @voice.command(name="undeafenall", description="Undeafen all users in your voice channel.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def undeafenall(self, ctx, *, reason: str = None):
        reason = reason or "[No reason]"
        if not ctx.author.voice:
            await ctx.send("You're not in a voice channel.")
            return

        voice_channel = ctx.author.voice.channel
        undeafened_count = 0
        for member in voice_channel.members:
            if member.voice.deaf:
                await member.edit(deafen=False, reason=f"By {ctx.author}: {reason}")
                undeafened_count += 1

        await ctx.send(f"**Voice undeafened {undeafened_count} users in {voice_channel.name}**")


async def setup(client):
    await client.add_cog(Voice(client))
