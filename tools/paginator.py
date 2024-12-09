from discord.ext import commands
import discord
from typing import List
from collections import deque


class PaginatorView(discord.ui.View):
    def __init__(
        self,
        embeds: List[discord.Embed],
        client: commands.AutoShardedBot,
        author) -> None:
        super().__init__(timeout=120)

        self._embeds = embeds
        self._queue = deque(embeds)
        self._initial = embeds[0]
        self._len = len(embeds)
        self._current_page = 1
        self.children[0].disabled = True
        self.children[1].disabled = True
        self.client = client
        self.author = author
        self._queue[0].set_footer(text=f"{client.user.name} • Page {self._current_page}/{self._len}",
                                  icon_url=client.user.display_avatar.url)

    async def update_button(self, interaction: discord.Interaction) -> None:
        for i in self._queue:
            i.set_footer(text=f"{interaction.client.user.name} • Page {self._current_page}/{self._len}", icon_url=interaction.client.user.display_avatar.url)
        
        if self._current_page == self._len:
            self.children[3].disabled = True
            self.children[4].disabled = True
        else:
            self.children[3].disabled = False
            self.children[4].disabled = False

        if self._current_page == 1:
            self.children[0].disabled = True
            self.children[1].disabled = True
        else:
            self.children[0].disabled = False
            self.children[1].disabled = False

        await interaction.message.edit(view=self)

    async def on_timeout(self):
        for button in self.children:
            button.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, _):
        if self.author != interaction.user:
            return await interaction.response.send_message("It's not your interaction.", ephemeral=True)
        
        self._queue.rotate(-self._current_page + 1)
        embed = self._queue[0]
        self._current_page = 1
        await self.update_button(interaction)
        self.message = await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, _):
        if self.author != interaction.user:
            return await interaction.response.send_message("It's not your interaction.", ephemeral=True)
        
        self._queue.rotate(-1)
        embed = self._queue[0]
        self._current_page -= 1
        await self.update_button(interaction)
        self.message = await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, _):
        if self.author != interaction.user:
            return await interaction.response.send_message("It's not your interaction.", ephemeral=True)
        
        await self.update_button(interaction)
        self.message = await interaction.message.delete()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _):
        if self.author != interaction.user:
            return await interaction.response.send_message("It's not your interaction.", ephemeral=True)
        
        self._queue.rotate(1)
        embed = self._queue[0]
        self._current_page += 1
        await self.update_button(interaction)
        self.message = await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="End", style=discord.ButtonStyle.primary)
    async def end(self, interaction: discord.Interaction, _):
        if self.author != interaction.user:
            return await interaction.response.send_message("It's not your interaction.", ephemeral=True)
            
        self._queue.rotate(self._len - 1)
        embed = self._queue[0]
        self._current_page = self._len
        await self.update_button(interaction)
        self.message = await interaction.response.edit_message(embed=embed)

    @property
    def initial(self) -> discord.Embed:
        return self._initiat
