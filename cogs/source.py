import discord
from discord.ext import commands
from discord import ui


class source(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.hybrid_command(aliases=['sc', 'code'], description="Shows the Source Code URL")
    async def source(self, ctx: commands.Context):
        """Source code button"""
        try:
            embed = discord.Embed(
                title="Bot Source Code",
                description="Click the button below to view the source code of this bot on GitHub.",
                color=discord.Color.blue(),
            )

            source_button = discord.ui.Button(
                label="View Source Code",
                style=discord.ButtonStyle.link,
                emoji="<:github:829998719046379048>",  
                url="https://github.com/e137x/fault",  
            )

            view = discord.ui.View()
            view.add_item(source_button)
            await ctx.send(embed=embed, view=view)

        except Exception as e:
            print(f"Error sending source button: {e}")
            await ctx.send("An error occurred while trying to send the source code button.")

async def setup(client):
    await client.add_cog(source(client))