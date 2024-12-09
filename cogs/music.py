import asyncio
import logging
from typing import cast
import re
import discord
from discord.ext import commands, tasks
import credentials
import wavelink
import pymongo
from tools.definitions import *
from settings.config import *
from wavelink.filters import Equalizer


class QueueButtons(discord.ui.View):
    def __init__(self, ctx, pages):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.pages = pages
        self.current_page = 0

    async def show_current_page(self, interaction):
        tracks_info = [f'**[[{num}] {track.title}]({support_link})**' if track.title and not track.title.isspace() else f"**[[{num}] No Title Provided]({support_link})**" for num, track in enumerate(self.pages[self.current_page], start=self.current_page * 10 + 1)]
        embed = discord.Embed(title=f'Queue - Page {self.current_page + 1}/{len(self.pages)}', color=color)
        embed.description = '\n'.join(tracks_info)
        await interaction.response.edit_message(embed=embed, view=self)


    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.ctx.author.id:
            return True
        else:
            return await interaction.response.send_message(embed=discord.Embed(description="You Can Not Use This Interaction.", color=color), ephemeral=True)

    async def on_timeout(self) -> None:
        return self.clear_items()
    

    @discord.ui.button(emoji="◀", style=discord.ButtonStyle.grey)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.interaction_check(interaction):
            self.current_page = max(0, self.current_page - 1)
            await self.show_current_page(interaction)
    @discord.ui.button(emoji="▶", style=discord.ButtonStyle.grey)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.interaction_check(interaction):
            self.current_page = min(len(self.pages) - 1, self.current_page + 1)
            await self.show_current_page(interaction)
    @discord.ui.button(label='Delete', style=discord.ButtonStyle.red)
    async def exit_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.interaction_check(interaction):
            await interaction.message.delete()
    





class PlayerButtons(discord.ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user not in self.player.channel.members:
            return await interaction.response.send_message(
                "You are not in the voice channel", ephemeral=True
            )

        return True
    
    @discord.ui.button(emoji="⏮", style=discord.ButtonStyle.grey)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.voice and interaction.user.voice.channel != interaction.guild.voice_client.channel:
                return await interaction.response.send_message(
                    embed=discord.Embed(description="You are not in the same voice channel as the bot.", color=color),
                    ephemeral=True
                )

            if len(self.player.queue.history) < 2:
                if len(self.player.queue.history) == 1:
                    track_to_replay = self.player.queue.history[0]
                else:
                    return await interaction.response.send_message(embed=discord.Embed(description="No History Available.", color=color), ephemeral=True)
            else:
                track_to_replay = self.player.queue.history[-2]
            
            await self.player.stop()
            await self.player.play(track_to_replay)
            await interaction.response.send_message(embed=discord.Embed(description=f"Replaying:\n{track_to_replay.title}", color=color), ephemeral=True)
        except Exception as e:
            print(e)

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.grey)
    async def rewind(self, interaction: discord.Interaction, button:discord.ui.Button):
        try:
            if interaction.user.voice and interaction.user.voice.channel != interaction.guild.voice_client.channel:
                return await interaction.response.send_message(
                    embed=discord.Embed(description="You are not in the same voice channel as the bot.", color=color),
                    ephemeral=True
                )
            
            await self.player.seek(self.player.position - 10000)
            await interaction.response.send_message(embed=discord.Embed(description=f"Rewinded 10 Seconds!", color=color), ephemeral=True)
        except Exception as e:
            print(e)
          
    @discord.ui.button(emoji="⏸", style=discord.ButtonStyle.grey)
    async def pause_resume(self, interaction: discord.Interaction, button:discord.ui.Button):
        try:
            if interaction.user.voice and interaction.user.voice.channel != interaction.guild.voice_client.channel:
                return await interaction.response.send_message(
                    embed=discord.Embed(description="You are not in the same voice channel as the bot.", color=color),
                    ephemeral=True
                )
            
            if self.player.paused:
                await self.player.pause(False)
                await interaction.response.send_message(embed=discord.Embed(description="Resumed The Current Song.", color=color), ephemeral=True)
            else:
                await self.player.pause(True)
                await interaction.response.send_message(embed=discord.Embed(description="Paused The Current Song.", color=color), ephemeral=True)
        except Exception as e:
            print(e)
    
    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.grey)
    async def forward(self, interaction: discord.Interaction, button:discord.ui.Button):
        try:
            if interaction.user.voice and interaction.user.voice.channel != interaction.guild.voice_client.channel:
                return await interaction.response.send_message(
                    embed=discord.Embed(description="You are not in the same voice channel as the bot.", color=color),
                    ephemeral=True
                )
            
            await self.player.seek(self.player.position + 10000)
            await interaction.response.send_message(embed=discord.Embed(description=f"Forwarded 10 Seconds!", color=color), ephemeral=True)
        except Exception as e:
            print(e)
    
    @discord.ui.button(emoji="⏭", style=discord.ButtonStyle.grey)
    async def skip_track(self, interaction: discord.Interaction, button:discord.ui.Button):
        try:
            if interaction.user.voice and interaction.user.voice.channel != interaction.guild.voice_client.channel:
                return await interaction.response.send_message(
                    embed=discord.Embed(description="You are not in the same voice channel as the bot.", color=color),
                    ephemeral=True
                )

            await self.player.skip(force=True)
            await interaction.response.send_message(embed=discord.Embed(description="Skipped The Current Song.", color=color), ephemeral=True)
        except Exception as e:
            print(e)


        




class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.color = color
    
    async def reset_filters(self, player):
        filters = wavelink.Filters()
        await player.set_filters(filters)


    @commands.Cog.listener()
    async def on_ready(self):
        print("Music is Ready")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        print(f"Node is ready!")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            return
        
        try:
            original: wavelink.Playable | None = payload.original
            track: wavelink.Playable = payload.track
            length_seconds = round(track.length) / 1000
            hours, remainder = divmod(length_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{int(minutes):02d}:{int(seconds):02d}"
            autoplay_mode = "Enabled" if player.autoplay == wavelink.AutoPlayMode.enabled else "Disabled"
            embed = discord.Embed(color=self.color)
            embed.description = f"> [{track.title}]({track.uri}) - [{track.author}]({support_link})\n **Duration**: [{duration_str}]({support_link}) ㅤ**Autoplay**: [{autoplay_mode}]({support_link})"
            if track.artwork:
                embed.set_thumbnail(url=track.artwork)

            embed.set_author(name="Now Playing", icon_url=self.client.user.avatar.url)
            embed.set_footer(text=f"Volume: {player.volume}", icon_url=track.artwork)
            player.ctx = await player.home.send(embed=embed, view=PlayerButtons(player))
            await self.update_channel_status(player, f"🎶 | {track.title} - {track.author}")
        except Exception as e:
            print(e)
    


    @commands.Cog.listener()
    async def on_wavelink_player_update(
        self, payload: wavelink.PlayerUpdateEventPayload
    ):
        if not payload.player or not payload.player.connected:
            return
        if payload.player.current is None:
            return
        
      
        track = payload.player.current
        try:
            if payload.player.paused:
                await payload.player.channel.edit(
                    status=f"▶️ **{track.title}** - {track.author}"
                )
            else:
                await payload.player.channel.edit(
                    status=f"🎶 | **{track.title}** - {track.author}"
                )
        except Exception as e:
            pass

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            return
        try:
            await player.ctx.delete()
        except:
            pass
        await self.update_channel_status(player, "Fault Music")


    async def update_channel_status(self, player: wavelink.Player, status: str):
        """Update the status of the channel."""
        try:
            await player.channel.edit(status=status)
        except Exception:
            pass

    @commands.hybrid_command(
        name="play", 
        aliases=["p"], 
        usage="/play <query>"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        """
        Play a song or playlist in the voice channel.

        This command allows users to play any track or playlist. Additionally, it ensures that the user is in the same 
        voice channel as the bot and that a track is currently playing.

        Arguments:
        - <query>

        Usage:
        - `.play <query>`: Play any song.
        """
        if not ctx.guild:
            return



        player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
            except AttributeError:
                await ctx.send(embed=discord.Embed(description="You Are Not In A Voice Channel!", color=self.color))
                return
            except discord.ClientException:
                await ctx.send(embed=discord.Embed(description="I Can't Join That Channel!", color=self.color))
                return

        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)

        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)

        if not hasattr(player, "home"):
            player.home = ctx.channel

        if not player.playing:
            mode = await get_default_autoplay(ctx.guild.id)
            if mode:
                if mode == "disabled":
                    player.autoplay = wavelink.AutoPlayMode.partial
                else:
                    player.autoplay = wavelink.AutoPlayMode.enabled
            else:
                player.autoplay = wavelink.AutoPlayMode.partial

        tracks: wavelink.Search = await wavelink.Playable.search(query)
        if not tracks:
            await ctx.send(embed=discord.Embed(description="I Can Not Find Any Songs With That Query!", colour=self.color))
            return

        if isinstance(tracks, wavelink.Playlist):
            added: int = await player.queue.put_wait(tracks)
            await ctx.send(embed=discord.Embed(description=f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.", colour=self.color))
        else:
            track: wavelink.Playable = tracks[0]
            await player.queue.put_wait(track)
            await ctx.send(embed=discord.Embed(description=f"Added [{track}]({support_link}) To Queue!", colour=self.color))

        if not player.playing:
            volume = await get_default_volume(ctx.guild.id)
            await player.play(player.queue.get(), volume=int(volume))
    



    @commands.hybrid_command(
        name="skip", 
        usage="/skip"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def skip(self, ctx: commands.Context) -> None:
        """
        Skip the currently playing song in the voice channel.
        
        Arguments:
        - None: This command skips the currently playing song in the voice channel.
        
        This command will skip the song that is currently playing in the voice channel. 
        It ensures that the user is in the same voice channel as the bot, and that something is playing.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)      
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.",colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)        
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False) 
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing anything.",colour=self.color)
            await ctx.reply(embed=embed4, mention_author=False)
            return        
        else:
            await player.skip(force=True)
            await ctx.send(embed=discord.Embed(description="Successfully Skipped The Current Track", color=self.color))


    @commands.hybrid_command(
        name="stop", 
        usage="/stop"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stop(self, ctx: commands.Context) -> None:
        """
        Stop the currently playing song and disconnect the bot from the voice channel.
        
        Arguments:
        - None: This command stops the current song and disconnects the bot from the voice channel.
        
        This command stops the current song being played, disconnects the bot from the voice channel,
        and ensures that the user is in the same voice channel as the bot.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)      
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)        
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False) 
        else:
            await player.stop(force=True)
            await ctx.send(embed=discord.Embed(description="Successfully Stopped The Player!", color=self.color))


    @commands.hybrid_command(
        name="volume", 
        aliases=["vol"], 
        usage="/volume <int>"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def volume(self, ctx: commands.Context, volume: int = None) -> None:
        """
        Set the volume for the currently playing audio in the voice channel.
        
        Arguments:
        - volume (int): The desired volume level (between 0 and 200).
        
        This command allows the user to adjust the bot's playback volume. The user needs to provide
        an integer value for the volume, and it will be set within the range of 0 to 200. If no volume
        is provided or if the volume is out of range, an error message will be returned.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if volume is None:
            embed4 = discord.Embed(description="Provide A Integer Value For The Volume!", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False) 
        
        if not 0 <= volume <= 200:
            embed4 = discord.Embed(description="Please provide a volume to set between 0 and 200!", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False) 
        
        if not player.playing:
            embed4 = discord.Embed(description="I am Not Playing Anything.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False) 
        
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)      
        
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)        
        
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False) 
        
        else:
            await player.set_volume(volume)
            await ctx.send(embed=discord.Embed(description=f"Volume Has Been Set To {volume}!", color=self.color))



    @commands.hybrid_command(
        name="queue",
        aliases=['q'],
        usage="/queue"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def queue(self, ctx):
        """
        Display the current song queue in the voice channel.
        
        Arguments:
        - None: This command displays the list of songs currently in the queue.
        
        This command shows the list of songs in the queue for the current voice channel.
        If the queue is empty, it will notify the user. The list is shown in pages of 10 songs each.
        Users can navigate through the pages to view the entire queue.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)

        queue_tracks = [track for track in player.queue]
        if not queue_tracks:
            return await ctx.send(embed=discord.Embed(description="The queue is empty.", color=self.color))

        pages = [queue_tracks[i:i + 10] for i in range(0, len(queue_tracks), 10)]
        current_page = 0

        formatted_tracks = []
        for num, track in enumerate(pages[current_page], start=current_page * 10 + 1):
            title = track.title if track.title and not track.title.isspace() else f"[[{num}] No Title Provided]({support_link})"
            formatted_tracks.append(f'**[[{num}] {title}]({support_link})**')

        embed = discord.Embed(title=f'Queue - Page {current_page + 1}/{len(pages)}', color=self.color)
        embed.description = '\n'.join(formatted_tracks)
        queue_view = QueueButtons(ctx, pages)
        message = await ctx.send(embed=embed, view=queue_view)







    @commands.hybrid_command(
        name="autoplay", 
        aliases=["ap"], 
        usage="/autoplay"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def autoplay(self, ctx):
        """
        Toggle the autoplay feature for the currently playing song.
        
        Arguments:
        - None: This command enables or disables autoplay for the current track.
        
        This command toggles the autoplay feature for the bot. When enabled, the bot will automatically
        play the next song in the queue once the current song finishes. If autoplay is already enabled,
        using this command will disable it, and vice versa.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player.playing:
            embed4 = discord.Embed(description="I am Not Playing Anything.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False) 
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)      
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)        
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False) 
        if player.autoplay == wavelink.AutoPlayMode.partial:
            player.autoplay = wavelink.AutoPlayMode.enabled
            return await ctx.send(embed=discord.Embed(description="Autoplay is Enabled!", color=self.color))
        else:
            player.autoplay = wavelink.AutoPlayMode.partial
            return await ctx.send(embed=discord.Embed(description="Autoplay is Disabled!", color=self.color))



    @commands.hybrid_command(
        name="history", 
        aliases=["old"], 
        usage="/history"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def history(self, ctx):
        """
        Show the playback history of the bot in the voice channel.
        
        Arguments:
        - None: This command displays the list of previously played songs.
        
        This command shows the list of songs that have been played in the current voice channel.
        If there is no playback history, it will notify the user. It also shows the current track
        that is playing (if any), at the top of the list.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)      
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)        
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False) 
        
        history = player.queue.history
        if not history:
            return await ctx.send(embed=discord.Embed(description="No History Available.", color=self.color))
        
        history_list = []
        for idx, track in enumerate(reversed(history), start=0):
            if player.current and idx == 0:
                continue
            history_list.append(f"{idx}. [{track.title}]({support_link})")
        if not history_list:
            return await ctx.send(embed=discord.Embed(description="No History Available.", color=self.color))
        
        embed = discord.Embed(title="Playback History", color=self.color)
        if player.current:
            embed.description = f"Now Playing: [{player.current.title}]({support_link})\n"
        embed.description += "\n".join(history_list)
        
        await ctx.send(embed=embed)





    @commands.hybrid_command(
        name="pause", 
        usage="/pause"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pause(self, ctx):
        """
        Pause the currently playing song in the voice channel.
        
        Arguments:
        - None: This command pauses the song that is currently playing.
        
        This command allows the user to pause the current song that the bot is playing in the voice channel.
        If the song is already paused, it will notify the user that the song is already paused.
        If no song is currently playing, it will notify the user accordingly.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)      
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)        
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False) 
        if not player.playing:
            embed4 = discord.Embed(description="I am Not Playing Anything.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False) 
        else:
            if player.paused:
                return await ctx.send(embed=discord.Embed(description="The Song is Already Paused.", color=self.color))
            else:
                await player.pause(True)
            await ctx.send(embed=discord.Embed(description="Paused The Current Song.", color=self.color))
            



    @commands.hybrid_command(
        name="resume", 
        usage="/resume"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def resume(self, ctx):
        """
        Resume the currently paused song in the voice channel.
        
        Arguments:
        - None: This command resumes the song that is currently paused.
        
        This command allows the user to resume a song that has been paused in the voice channel.
        If the song is not paused, it will notify the user that the song is already playing.
        If no song is currently playing, it will notify the user accordingly.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)      
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.",colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)        
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False) 
        if not player.playing:
            embed4 = discord.Embed(description="I am Not Playing Anything.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False) 
        else:
            if player.paused:
                await player.pause(False)
            else:
                return await ctx.send(embed=discord.Embed(description="The Song is Not Paused.", color=self.color))
            await ctx.send(embed=discord.Embed(description="Resumed The Current Song.", color=self.color))


    @commands.group(name="default", invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def default(self, ctx):
        """
        Display information about configuring default settings for the server.
        
        Arguments:
        - mode (str): The autoplay mode to set. Accepts `enabled` or `disabled`.
        - mode (str): The 24/7 mode to set. Accepts `enabled` or `disabled`.
        - vol (int): The volume level to set (between 0 and 200).
        
        This command provides information on how to set the default volume,
        autoplay mode, and 24/7 mode for the server. It helps users manage
        their server's music settings.
        """
        embed = discord.Embed(
            description="**Default Volume** - Set's A Default Volume For The Server.\n**Default Autoplay** - Set's A Default Autplay Mode For The Server.\n**Default 247** - Set's A Default 247 Mode For The Server.",
            color=self.color
        )
        await ctx.send(embed=embed)


    @default.command(name="autoplay")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def aplay(self, ctx, mode: str = None):
        """
        Set the default autoplay mode for the server.

        Arguments:
        - mode (str): The autoplay mode to set. Accepts `enabled` or `disabled`.

        This command sets the default autoplay mode for the server. If the mode
        is enabled, the bot will automatically play the next track when the current
        track finishes. If disabled, autoplay will be turned off.
        """
        if mode==None:
            return await ctx.send(embed=discord.Embed(description="Please Provide A Default Autoplay Mode `enabled` or `disabled`.", color=self.color))
        if mode.lower() == "enabled" or mode.lower() == "enable":
            collection = self.client.db["Autoplays"]
            found = collection.find_one(
                {
                    "id": ctx.guild.id
                }
            )
            if found:
                if found["autoplay"] == "enabled":
                    return await ctx.send(embed=discord.Embed(description="Default Autoplay is Already Set To Enabled!", color=self.color))
                collection.update_one(
                    {
                        "id": ctx.guild.id
                    },
                    {"$set":
                        {
                        "autoplay": "enabled"
                        }
                    }
                )
                return await ctx.send(embed=discord.Embed(description="Successfully Updated The Default Autoplay Mode To Enabled!", color=self.color))
            else:
                collection.insert_one(
                    {
                        "id": ctx.guild.id,
                        "autoplay": "enabled"
                    }
                )
                return await ctx.send(embed=discord.Embed(description="Successfully Enabled The Default Autoplay Mode!", color=self.color))
        if mode.lower() == "disabled" or mode.lower() == "disable":
            collection = self.client.db["Autoplays"]
            found = collection.find_one(
                {
                    "id": ctx.guild.id
                }
            )
            if found:
                if found["autoplay"] == "disabled":
                    return await ctx.send(embed=discord.Embed(description="Default Autoplay is Already Set To Disabled!", color=self.color))
                collection.update_one(
                    {
                        "id": ctx.guild.id
                    },
                    {"$set":
                        {
                        "autoplay": "disabled"
                        }
                    }
                )
                return await ctx.send(embed=discord.Embed(description="Successfully Updated The Default Autoplay Mode To Disabled!", color=self.color))
            else:
                collection.insert_one(
                    {
                        "id": ctx.guild.id,
                        "autoplay": "disabled"
                    }
                )
                return await ctx.send(embed=discord.Embed(description="Successfully Enabled The Default Autoplay Mode!", color=self.color))




    @default.command(name="247", aliases=["24/7"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def twenty_four_seven(self, ctx, mode: str = None):
        """
        Set the default 24/7 mode for the server.

        Arguments:
        - mode (str): The 24/7 mode to set. Accepts `enabled` or `disabled`.

        This command sets the default 24/7 mode for the server. If enabled, the bot
        will continue playing music 24/7 without stopping. If disabled, it will stop
        playing music when no one is listening.
        """
        if mode==None:
            return await ctx.send(embed=discord.Embed(description="Please Provide A Default 24/7 Mode `enabled` or `disabled`.", color=self.color))
        if mode.lower() == "enabled" or mode.lower() == "enable":
            collection = self.client.db["24/7"]
            found = collection.find_one(
                {
                    "id": ctx.guild.id
                }
            )
            if found:
                if found["24/7"] == "enabled":
                    return await ctx.send(embed=discord.Embed(description="Default 24/7 is Already Set To Enabled!", color=self.color))
                collection.update_one(
                    {
                        "id": ctx.guild.id
                    },
                    {"$set":
                        {
                        "24/7": "enabled"
                        }
                    }
                )
                return await ctx.send(embed=discord.Embed(description="Successfully Updated The Default 24/7 Mode To Enabled!", color=self.color))
            else:
                collection.insert_one(
                    {
                        "id": ctx.guild.id,
                        "24/7": "enabled"
                    }
                )
                return await ctx.send(embed=discord.Embed(description="Successfully Enabled The Default 24/7 Mode!", color=self.color))
        if mode.lower() == "disabled" or mode.lower() == "disable":
            collection = self.client.db["24/7"]
            found = collection.find_one(
                {
                    "id": ctx.guild.id
                }
            )
            if found:
                if found["24/7"] == "disabled":
                    return await ctx.send(embed=discord.Embed(description="Default 24/7 is Already Set To Disabled!", color=self.color))
                collection.update_one(
                    {
                        "id": ctx.guild.id
                    },
                    {"$set":
                        {
                        "24/7": "disabled"
                        }
                    }
                )
                return await ctx.send(embed=discord.Embed(description="Successfully Updated The Default 24/7 Mode To Disabled!", color=self.color))
            else:
                collection.insert_one(
                    {
                        "id": ctx.guild.id,
                        "24/7": "disabled"
                    }
                )
                return await ctx.send(embed=discord.Embed(description="Successfully Enabled The Default 24/7 Mode!", color=self.color))







    @default.command(name="volume")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def vol1me(self, ctx, vol: int = None):
        """
        Set the default volume for the server.

        Arguments:
        - vol (int): The volume level to set (between 0 and 200).

        This command sets the default volume for the server. The volume will apply
        to all tracks played in the future. If no value is provided, the bot will
        notify the user to specify a volume. It also checks if the volume is within
        the valid range (0-200).
        """
        if vol==None:
            return await ctx.send(embed=discord.Embed(description="Please Provide A Volume Amount For Default Volume.", color=self.color))
        if not 0 <= vol <= 200:
            embed4 = discord.Embed(description="Please provide a Default Volume in between 0 to 200!", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False) 
        collection = self.client.db["Volumes"]
        found = collection.find_one(
            {
                "id": ctx.guild.id
            }
        )
        if found:
            collection.update_one(
                    {
                        "id": ctx.guild.id
                    },
                    {"$set":
                        {
                        "volume": vol
                        }
                    }
                )
            return await ctx.send(embed=discord.Embed(description=f"Successfully Updated The Default Volume To {vol}!", color=self.color))
        else:
            collection.insert_one(
                    {
                        "id": ctx.guild.id,
                        "volume": vol
                    }
                )
            return await ctx.send(embed=discord.Embed(description=f"Successfully Saved The Default Volume `{vol}`!", color=self.color))
        


    @commands.hybrid_command(
        name="nowplaying", 
        usage="/nowplaying"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nowplaying(self, ctx):
        """
        Displays the currently playing track's information.

        This command retrieves information about the track currently playing in
        the voice channel, such as the track title, author, duration, and autoplay
        status. It also provides the volume and artwork of the track, if available.

        Arguments:
        - None

        If there is no track playing or the user is not in the same voice channel
        as the bot, the bot will send an appropriate message informing the user.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)      
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.",colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)        
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False) 
        if not player.playing:
            embed4 = discord.Embed(description="I am Not Playing Anything.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False) 
        else:
            length_seconds = round(player.current.length) / 1000
            hours, remainder = divmod(length_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            autoplay_mode = "Enabled" if player.autoplay == wavelink.AutoPlayMode.enabled else "Disabled"
            embed = discord.Embed(color=self.color)
            embed.description = f"> [{player.current.title}]({player.current.uri}) - [{player.current.author}]({support_link})\n **Duration**: [{duration_str}]({support_link}) ㅤ**Autoplay**: [{autoplay_mode}]({support_link})"
            embed.set_author(name="Now Playing", icon_url=self.client.user.avatar.url)
            embed.set_footer(text=f"Volume: {player.volume}", icon_url=player.current.artwork)
            if player.current.artwork:
                embed.set_image(url=player.current.artwork)
            await ctx.send(embed=embed)


    @commands.hybrid_command(
        name="forward", 
        usage="/forward"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def forward(self, ctx):
        """
        Skips the currently playing track by 10 seconds.

        This command allows users to skip forward by 10 seconds in the currently
        playing track. If the track is paused, it sends a message asking the user 
        to resume it first. Additionally, it ensures that the user is in the same 
        voice channel as the bot and that a track is currently playing.

        Arguments:
        - None

        Behavior:
        - If the track is paused or if no track is playing, the bot will inform the user.
        - The track position will be advanced by 10 seconds when the conditions are met.

        Usage:
        - `&forward`: Skips forward by 10 seconds in the track.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.",colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)       
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)              
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused please use `&resume`.",colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)        
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.",colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)       
        position = player.position + 10000
        await player.seek(position)
        embed6 = discord.Embed(description="Skipped the track by 10 seconds.", colour=self.color)
        await ctx.reply(embed=embed6, mention_author=False)

    @commands.hybrid_command(
        name="rewind", 
        usage="/rewind"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rewind(self, ctx):
        """
        Rewinds the currently playing track by 10 seconds.

        This command allows users to rewind the currently playing track by 10 seconds. It checks 
        several conditions, including whether the bot is connected to a voice channel, if the 
        user is in the same voice channel as the bot, and if a track is currently playing. 
        If the track is paused, it will notify the user to resume it first.

        Arguments:
        - None

        Behavior:
        - If no track is playing or if the bot is not connected to a voice channel, the bot will notify the user.
        - If the user is not in the same voice channel as the bot, it will notify the user.
        - If the track is paused, it will ask the user to resume it first.
        - Rewinds the track by 10 seconds when conditions are met.

        Usage:
        - `&rewind`: Rewinds the currently playing track by 10 seconds.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.",colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)       
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)              
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused please use `&resume`.",colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)        
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.",colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)       
        position = player.position - 10000
        await player.seek(position)
        embed6 = discord.Embed(description="Rewinded the track by 10 seconds.", colour=self.color)
        await ctx.reply(embed=embed6, mention_author=False)


    @commands.hybrid_command(
        name="seek", 
        usage="/seek <time_str>"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def seek(self, ctx, *, time_str):
        """
        Seeks to a specified time in the currently playing track.

        This command allows users to seek to a specified time in the currently playing track.
        The time is provided in `mm:ss` or `ss` format. The command checks if the user is in 
        the same voice channel as the bot, and if a track is playing. It also validates the time format.

        Arguments:
        - time_str: A string representing the time to seek to (e.g., '1:30' or '90').

        Behavior:
        - If no track is playing, or if the bot is not in a voice channel, the bot will notify the user.
        - If the time format is incorrect, it will prompt the user to use a valid format.
        - If valid, it will seek to the specified time in the current track.

        Usage:
        - `&seek 1:30`: Seeks to 1 minute and 30 seconds in the track.
        - `&seek 90`: Seeks to 90 seconds in the track.
        """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)  
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)       
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)         
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)       
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)        
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)       
        time_pattern = re.compile(r"(\d+:\d+|\d+)")
        match = time_pattern.match(time_str)
        if not match:
            embed6 = discord.Embed(description="Invalid time format. Please use either `mm:ss` or `ss`.", colour=self.color)
            return await ctx.reply(embed=embed6, mention_author=False)      
        time_seconds = 0
        if match.group(1):
            time_components = list(map(int, match.group(1).split(":")))
            time_seconds = sum(c * 60 ** i for i, c in enumerate(reversed(time_components)))         
            await player.seek(time_seconds * 1000)
            embed7 = discord.Embed(description=f"Successfully sought to {time_str}.", colour=self.color)
            await ctx.reply(embed=embed7, mention_author=False)


    @commands.hybrid_command(
        name="remove", 
        usage="/remove <int>"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def remove(self, ctx, index: int):
        """
    Removes a track from the queue.

    This command allows users to remove a track from the queue by its index. 
    It checks whether the user is in the same voice channel as the bot, 
    whether a track is playing, and whether the provided index is valid.

    Arguments:
    - index: The index of the track to remove from the queue.

    Behavior:
    - If the queue is empty or if the index is invalid, the bot will notify the user.
    - If the track is successfully removed, it provides details of the removed track.

    Usage:
    - `&remove 3`: Removes the 3rd track from the queue.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)  
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)       
        if not player.queue or index > len(player.queue) or index < 1:
            embed6 = discord.Embed(description=f"Invalid index. Must be between 1 and {len(player.queue)}", color=self.color)              
            return await ctx.reply(embed=embed6, mention_author=False)             
        removed = list(player.queue).pop(index - 1)
        player.queue = list(player.queue)[:index - 1] + list(player.queue)[index:]
        embed7 = discord.Embed(title="Removed From Queue", description=f"[{removed.title}]({support_link})", color=self.color)
        if removed.artwork:
            embed7.set_image(url=removed.artwork)
        length_seconds = round(removed.length) / 1000
        hours, remainder = divmod(length_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        embed7.add_field(name="Track Author", value=f"**[{removed.author}]({support_link})**")
        embed7.add_field(name="Duration", value=f"**[{duration_str}]({support_link})**")
        await ctx.reply(embed=embed7, mention_author=False)



    @commands.hybrid_command(
        name="leave", 
        aliases=["dc"], 
        usage="/leave"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leave(self, ctx: commands.Context):
        """
    Makes the bot leave the voice channel.

    This command disconnects the bot from the current voice channel. 
    It checks if the user is in the same voice channel as the bot, and whether the bot is connected.

    Arguments:
    - None

    Behavior:
    - If the user is not in the same voice channel as the bot, or if the bot is not in any voice channel, 
      the bot will notify the user.
    - If a track is playing, it will be stopped before leaving the voice channel.

    Usage:
    - `&leave`: Disconnects the bot from the voice channel.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not getattr(ctx.author.voice, "channel", None):
            embed = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False) 
        if not ctx.voice_client:
            embed2 = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)      
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)
        if player.playing:
            await player.stop(force=True)
        await ctx.voice_client.disconnect()
        embed4 = discord.Embed(description="Sucessfully Left voice channel.", colour=self.color)
        await ctx.reply(embed=embed4, mention_author=False)             


    @commands.hybrid_command(
        name="move", 
        usage="/move"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def move(self, ctx: commands.Context):
        """
    Moves the bot to the user's voice channel.

    This command makes the bot leave its current voice channel and join the user's voice channel.
    It checks if the user is in a voice channel, if the bot is already in a different channel, 
    and if a track is playing.

    Arguments:
    - None

    Behavior:
    - If the bot is already in the user's voice channel, it will notify the user.
    - If the bot is playing, it will not move unless the track is stopped.

    Usage:
    - `&move`: Moves the bot to the user's voice channel.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not getattr(ctx.author.voice, "channel", None):
            embed = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)       
        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                if player.playing:
                    embed2 = discord.Embed(description="I am currently playing in another voice channel.", colour=self.color)
                    return await ctx.reply(embed=embed2, mention_author=False)
                else:
                    await ctx.voice_client.disconnect()
                    await asyncio.sleep(1)           
                    player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
                    embed3 = discord.Embed(description=f"Successfully moved to **{ctx.author.voice.channel.name}**", colour=self.color)
                    await ctx.reply(embed=embed3, mention_author=False)
            else:
                embed4 = discord.Embed(description=f"I am already in your voice channel: {ctx.voice_client.channel.name}", colour=self.color)
                await ctx.reply(embed=embed4, mention_author=False)
        else:
            embed5 = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            await ctx.reply(embed=embed5, mention_author=False)

    @commands.hybrid_command(
        name="join", 
        aliases=["come"], 
        usage="/join"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def join(self, ctx: commands.Context):
        """
    Makes the bot join the user's voice channel.

    This command makes the bot join the user's voice channel if it is not already connected to one.
    It checks whether the user is in a voice channel, and if the bot is already in a different voice channel.

    Arguments:
    - None

    Behavior:
    - If the bot is already in the same voice channel as the user, it will notify the user.
    - If the bot is not in any voice channel, it will join the user's voice channel.

    Usage:
    - `&join`: Makes the bot join the user's voice channel.
    """
        if not getattr(ctx.author.voice, "channel", None):
            embed = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)
        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                embed2 = discord.Embed(description=f"I am already in another voice channel", colour=self.color)
                return await ctx.reply(embed=embed2, mention_author=False)
            else:
                embed3 = discord.Embed(description=f"Sucessfully Joined voice channel", colour=self.color)
                await ctx.reply(embed=embed3, mention_author=False)  
        else:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
            embed4 = discord.Embed(description=f"Successfully Joined your voice channel" , colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)
        

    @commands.hybrid_command(
        name="clearqueue", 
        aliases=["cq"], 
        usage="/clearqueue"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def clearqueue(self, ctx):
        """
    Clears all tracks from the queue.

    This command clears all tracks in the current queue. 
    It checks if the bot is connected to a voice channel and whether the user is in the same channel.

    Arguments:
    - None

    Behavior:
    - If the queue is empty, it will notify the user.
    - If the bot is not in a voice channel or the user is not in the same channel, it will notify the user.
    - Clears the queue and notifies the user of the number of tracks removed.

    Usage:
    - `&clearqueue`: Clears all tracks from the queue.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)
        else:
            if player.queue:
                number = len(player.queue)
                player.queue.clear()
                embed = discord.Embed(description=f"Successfully Cleared {number} Tracks From The Queue.", colour=self.color)
                return await ctx.reply(embed=embed, mention_author=False)
            else:
                embed = discord.Embed(description=f"There is Nothing To Clear In The Queue", colour=self.color)
                return await ctx.reply(embed=embed, mention_author=False)



    @commands.hybrid_command(
        name="shuffle", 
        usage="/shuffle"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shuffle(self, ctx: commands.Context) -> None:
        """
    Shuffles the tracks in the queue.

    This command shuffles the tracks in the current queue. It checks if the bot is connected 
    to a voice channel and if the user is in the same voice channel.

    Arguments:
    - None

    Behavior:
    - If the queue is empty, it will notify the user.
    - If the bot is not in a voice channel or the user is not in the same channel, it will notify the user.
    - Shuffles the queue and notifies the user.

    Usage:
    - `&shuffle`: Shuffles the tracks in the queue.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)

        if not player.queue:
            return await ctx.send(embed=discord.Embed(description="The queue is empty.", color=self.color))

        player.queue.shuffle()

        await ctx.send(embed=discord.Embed(description="Queue has been shuffled.", color=self.color))

    @commands.hybrid_command(
        name="loop", 
        usage="/loop <song/queue>"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def loop(self, ctx: commands.Context, mode: str = 'song') -> None:
        """
    Toggles loop mode for the current song or the entire queue.

    This command allows users to enable or disable loop mode for the current song or the entire queue. 
    It checks if the bot is in a voice channel and if the user is in the same channel.

    Arguments:
    - mode: The mode to toggle. Accepts 'song' or 'queue' (default is 'song').

    Behavior:
    - If no track is playing, it will notify the user.
    - Enables or disables looping for the specified mode (song or queue).

    Usage:
    - `&loop song`: Loops the current song.
    - `&loop queue`: Loops the entire queue.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            embed = discord.Embed(description="I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)
        elif not ctx.author.voice:
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed3 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)

        valid_modes = ['song', 'queue']
        if mode.lower() not in valid_modes:
            return await ctx.send(embed=discord.Embed(description=f"Invalid mode! Available modes are: {', '.join(valid_modes)}", color=self.color))

        if not player.playing:
            return await ctx.send(embed=discord.Embed(description="There's no track playing to loop.", color=self.color))

        if mode.lower() == 'song':
            if player.queue.mode == wavelink.QueueMode.loop:
                player.queue.mode = wavelink.QueueMode.normal
                loop_status = "disabled"
            else:
                player.queue.mode = wavelink.QueueMode.loop
                loop_status = "enabled"
            await ctx.send(embed=discord.Embed(description=f"Loop mode for the current song is now {loop_status}.", color=self.color))
        elif mode.lower() == 'queue':
            if player.queue.mode == wavelink.QueueMode.loop_all:
                player.queue.mode = wavelink.QueueMode.normal
                loop_status = "disabled"
            else:
                player.queue.mode = wavelink.QueueMode.loop_all
                loop_status = "enabled"
            await ctx.send(embed=discord.Embed(description=f"Loop mode for the queue is now {loop_status}.", color=self.color))


    @commands.hybrid_group(name="filter", description="Get available audio filters for the bot.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def filter(self, ctx):
        """
    Displays available audio filters for the bot.

    This command lists all the audio filters available to apply to the currently playing track.
    It provides a description of each filter that can be enabled, such as Lowpass, Nightcore, Slowed, etc.

    Arguments:
    - None

    Behavior:
    - Sends an embed with the list of available filters.

    Usage:
    - `&filter`: Displays a list of available audio filters.
    """
        embed = discord.Embed(
            description="**Filter Lowpass** - Enabled Lowpass Filter.\n"
                        "**Filter Nightcore** - Enabled Nightcore Filter.\n"
                        "**Filter Slowed** - Enabled Slowed Filter.\n"
                        "**Filter Distortion** - Enabled Distortion Filter.\n"
                        "**Filter Vibrato** - Enabled Vibrato Filter.\n"
                        "**Filter Tremolo** - Enabled Tremolo Filter.\n"
                        "**Filter 8D** - Enabled 8D Filter.\n"
                        "**Filter Lofi** - Enabled Lofi Filter.\n"
                        "**Filter Vaporwave** - Enabled Vaporwave Filter.\n"
                        "**Filter Karaoke** - Enabled Karaoke Filter.\n"
                        "**Filter Stereo** - Enabled Stereo Filter.\n"
                        "**Filter Reset** - Reset all filters to default."
,
            color=self.color
        )
        await ctx.send(embed=embed)




    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lowpass(self, ctx):
        """
    Applies a lowpass filter to the audio, reducing high frequencies.

    This command enables a lowpass filter on the currently playing track, which reduces
    high frequencies and creates a "muffled" or "darker" sound.

    Arguments:
    - None

    Behavior:
    - Applies a lowpass filter with smoothing effect to the audio.

    Usage:
    - `&lowpass`: Enables the lowpass filter on the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await self.reset_filters(player)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        filters: wavelink.Filters = player.filters
        filters.low_pass.set(smoothing=100)
        await player.set_filters(filters)
        embed6 = discord.Embed(description="Lowpass Filter Enabled.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)


    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nightcore(self, ctx):
        """
    Applies a nightcore filter to the audio, speeding up the track and increasing the pitch.

    This command enables the nightcore filter, making the song play faster and higher-pitched.

    Arguments:
    - None

    Behavior:
    - Increases speed by 1.25x and pitch by 1.3x.

    Usage:
    - `&nightcore`: Enables the nightcore filter on the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await self.reset_filters(player)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        filters: wavelink.Filters = player.filters
        filters.timescale.set(speed=1.25, pitch=1.3)
        await player.set_filters(filters)
        embed6 = discord.Embed(description="Nightcore Filter Enabled.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)

    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def slowed(self, ctx):
        """
    Applies a slowed filter to the audio, reducing the speed of the track.

    This command enables a slowed filter, making the song play slower.

    Arguments:
    - None

    Behavior:
    - Reduces the speed of the track by 10%.

    Usage:
    - `&slowed`: Enables the slowed filter on the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await self.reset_filters(player)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        filters: wavelink.Filters = player.filters
        filters.timescale.set(rate=0.9)
        await player.set_filters(filters)
        embed6 = discord.Embed(description="Slow Filter Enabled.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)

    sin_offset_value = 0.5 
    sin_scale_value = 0.75
    cos_offset_value = 0.2
    cos_scale_value = 0.9  
    tan_offset_value = 0.3
    tan_scale_value = 0.6  
    offset_value = 0.1    
    scale_value = 0.8        


    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def distortion(self, ctx):
        """
    Applies a distortion filter to the audio, adding various types of audio distortion effects.

    This command enables a distortion filter, modifying the audio to sound more rough or distorted.

    Arguments:
    - None

    Behavior:
    - Applies multiple distortion effects with customizable parameters such as offset and scale.

    Usage:
    - `&distortion`: Enables the distortion filter on the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await self.reset_filters(player)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        filters: wavelink.Filters = player.filters
        filters.distortion.set(
    sin_offset=self.sin_offset_value,
    sin_scale=self.sin_scale_value,
    cos_offset=self.cos_offset_value,
    cos_scale=self.cos_scale_value,
    tan_offset=self.tan_offset_value,
    tan_scale=self.tan_scale_value,
    offset=self.offset_value,
    scale=self.scale_value
)
        await player.set_filters(filters)
        embed6 = discord.Embed(description="Distortion Filter Enabled.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)



    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def vibrato(self, ctx):
        """
    Applies a vibrato filter to the audio, adding periodic pitch modulation.

    This command enables a vibrato effect on the audio, creating a wavering sound by modulating pitch.

    Arguments:
    - None

    Behavior:
    - Sets the vibrato frequency to 10 and depth to 1.

    Usage:
    - `&vibrato`: Enables the vibrato filter on the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await self.reset_filters(player)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        filters: wavelink.Filters = player.filters
        filters.vibrato.set(
            frequency=10,
            depth=1
        )
        await player.set_filters(filters)
        embed6 = discord.Embed(description="Vibrato Filter Enabled.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)

    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tremolo(self, ctx):
        """
    Applies a tremolo filter to the audio, adding periodic volume modulation.

    This command enables a tremolo effect, which modulates the volume at a set frequency.

    Arguments:
    - None

    Behavior:
    - Sets the tremolo frequency to 15 and depth to 1.

    Usage:
    - `&tremolo`: Enables the tremolo filter on the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await self.reset_filters(player)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        filters: wavelink.Filters = player.filters
        filters.tremolo.set(
            frequency=15,
            depth=1
        )
        await player.set_filters(filters)
        embed6 = discord.Embed(description="Tremolo Filter Enabled.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)


    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lofi(self, ctx):
        """
    Applies a lofi filter to the audio for a relaxed vibe.

    Reduces speed to 0.74x and pitch to 0.87x.

    Usage:
    - &lofi: Enables the lofi filter on the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await self.reset_filters(player)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        filters: wavelink.Filters = player.filters
        filters.timescale.set(speed=0.74, pitch=0.87, rate=1)
        await player.set_filters(filters)
        embed6 = discord.Embed(description="Lofi Filter Enabled.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)

    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def vaporwave(self, ctx):
        """
    Applies a vaporwave filter to the audio, altering the track for a retro-futuristic style.

    This command enables a vaporwave filter, slowing down the track and lowering its pitch for a nostalgic feel.

    Arguments:
    - None

    Behavior:
    - Reduces speed to 0.71x and pitch to 0.80x.

    Usage:
    - `&vaporwave`: Enables the vaporwave filter on the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await self.reset_filters(player)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        filters: wavelink.Filters = player.filters
        filters.timescale.set(speed=0.71, pitch=0.80, rate=1)
        await player.set_filters(filters)
        embed6 = discord.Embed(description="Vaporwave Filter Enabled.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)

    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def karaoke(self, ctx):
        """
    Applies a karaoke filter to the audio, reducing the volume of the vocals.

    This command enables a karaoke effect, ideal for playing instrumental versions of songs.

    Arguments:
    - None

    Behavior:
    - Reduces vocal levels while keeping the music instrumental.

    Usage:
    - `&karaoke`: Enables the karaoke filter on the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await self.reset_filters(player)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        filters: wavelink.Filters = player.filters
        filters.karaoke.set(level=0.8, mono_level=0.2, filter_band=100, filter_width=130)
        await player.set_filters(filters)
        embed6 = discord.Embed(description="Karaoke Filter Enabled.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)


    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reset(self, ctx):
        """
    Resets all filters applied to the audio, restoring it to the default state.

    This command removes all active filters and restores the audio to its original, unfiltered state.

    Arguments:
    - None

    Behavior:
    - Resets all active filters to the default state.

    Usage:
    - `&reset`: Resets all filters applied to the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        
        filters: wavelink.Filters = player.filters
        filters.reset()
        await player.set_filters(filters)
        embed6 = discord.Embed(description="All Filters Reset.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)

    @filter.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stereo(self, ctx):
        """
    Applies a stereo filter to the audio, enhancing the stereo effect.

    This command enables a stereo filter that enhances the left and right channel separation for a wider sound.

    Arguments:
    - None

    Behavior:
    - Increases the stereo effect on the audio.

    Usage:
    - `&stereo`: Enables the stereo filter on the current track.
    """
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await self.reset_filters(player)
        if ctx.voice_client is None:
            embed = discord.Embed(description="I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)            
        elif not getattr(ctx.author.voice, "channel", None):
            embed2 = discord.Embed(description="You are not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed2, mention_author=False)           
        if player.paused:
            embed3 = discord.Embed(description="I am currently paused, please use `&resume`.", colour=self.color)
            return await ctx.reply(embed=embed3, mention_author=False)          
        if not player.playing:
            embed4 = discord.Embed(description="I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed4, mention_author=False)          
        if ctx.author.voice.channel != ctx.voice_client.channel:
            embed5 = discord.Embed(description="You are not in the same voice channel.", colour=self.color)
            return await ctx.reply(embed=embed5, mention_author=False)
        
        filters: wavelink.Filters = player.filters
        filters.karaoke.set(level=0.8, mono_level=0, filter_band=100, filter_width=200)
        await player.set_filters(filters)
        embed6 = discord.Embed(description="Stereo Filter Enabled.", colour=self.color)
        embed6.set_footer(text="Note: Filters May Take Up To 5s To Apply!")
        await ctx.reply(embed=embed6, mention_author=False)
        
     



    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player) -> None:
        fetch = await get_guild_247(player.guild.id)
        if fetch=="enabled":
            return
        else:
            try:
                await player.home.send(embed=discord.Embed(description="Enable 247 mode in order to make me stay in vc", color=color))
            except:
                pass
            await player.disconnect()



                
                            


async def setup(client):
    await client.add_cog(Music(client))