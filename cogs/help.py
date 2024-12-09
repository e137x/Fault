import discord
from discord.ext import commands
from settings.config import color

class Xd(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.hybrid_command(name="help", description="Show the help panel or specific command help")
    async def help_command(self, ctx, command_name:str = None):
        if command_name:
            command = self.client.get_command(command_name)
            if command:
                embed = discord.Embed(
                    color=color,
                    description=f"{command.help or 'No description available.'}"
                )
                embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Command `{command_name}` not found.")
        else:
            embed = discord.Embed(
                color=color,
                description="I'm Fault, a bot made by [.gg/jsk Developers.](https://discord.gg/jsk)\n### Features\n- Music | Filter | Voice | Settings\n- You can use the buttons below to explore the commands of each module."
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)

            view = Xdd(ctx.author.id, self.client)
            await ctx.send(embed=embed, view=view)

class Xdd(discord.ui.View):
    def __init__(self, command_runner_id, client):
        super().__init__()
        self.command_runner_id = command_runner_id
        self.client = client

        self.add_item(Button(label="Music", style=discord.ButtonStyle.primary, category="music", command_runner_id=command_runner_id, client=client))
        self.add_item(Button(label="Filter", style=discord.ButtonStyle.primary, category="filter", command_runner_id=command_runner_id, client=client))
        self.add_item(Button(label="Voice", style=discord.ButtonStyle.primary, category="voice", command_runner_id=command_runner_id, client=client))
        self.add_item(Button(label="Settings", style=discord.ButtonStyle.primary, category="Settings", command_runner_id=command_runner_id, client=client))

class Button(discord.ui.Button):
    def __init__(self, label, style, category, command_runner_id, client):
        super().__init__(label=label, style=style)
        self.category = category
        self.command_runner_id = command_runner_id
        self.client = client

    async def callback(self, interaction:discord.Interaction):
        if interaction.user.id != self.command_runner_id:
            await interaction.response.send_message("You can't use this.", ephemeral=True)
            return

        embed = discord.Embed(color=color)

        if self.category == "music":
            embed.description = "</autoplay:1308415390606692418>, </clearqueue:1308415390837375062>, </forward:1311353844789416027>, </history:1308415390606692419>, </join:1308415390837375061>, </leave:1308415390837375059>, </loop:1308415390837375064>, </move:1311353844789416030>, </nowplaying:1311353844294225951>, </pause:1308415390606692420>, </play:1308092636141322302>, </queue:1308415390606692417>, </remove:1308415390606692422>, </resume:1308415390606692421>, </rewind:1311353844789416028>, </seek:1311353844789416029>, </shuffle:1308415390837375063>, </skip:1308415390606692414>,  </stop:1308415390606692415>, </volume:1308415390606692416>"
            author_text = "Music"
        elif self.category == "filter":
            embed.description = "</filter distortion:1311360297063284736>, </filter karaoke:1311360297063284736>, </filter lofi:1311360297063284736>, </filter lowpass:1311360297063284736>, </filter nightcore:1311360297063284736>, </filter reset:1311360297063284736>, </filter slowed:1311360297063284736>, </filter stereo:1311360297063284736>, </filter tremolo:1311360297063284736>, </filter vaporwave:1311360297063284736>, </filter vibrato:1311360297063284736>"
            author_text = "Filter"
        elif self.category == "voice":
            embed.description = "</voice mute:1307650372541612065>, </voice unmute:1307650372541612065>, </voice deafen:1307650372541612065>, </voice undeafen:1307650372541612065>, </voice muteall:1307650372541612065>, </voice unmuteall:1307650372541612065>, </voice deafenall:1307650372541612065>, </voice undeafenall:1307650372541612065>"
            author_text = "Voice"
        elif self.category == "Settings":
            embed.description = "</avatar:1306874758822105131>, </banner user:1306874758822105133>, </banner server:1306874758822105133>, </help:1305541065830301697>, </membercount:1306874758822105132>,</ping:1308394980527706192>, </setprefix:1302545358856912979>, </stats:1306874758822105137>, </uptime:1308394980527706193>"
            author_text = "Settings"

        embed.set_author(name=author_text, icon_url=self.client.user.avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(client):
    await client.add_cog(Xd(client))
