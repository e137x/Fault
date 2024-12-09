import discord
from discord.ext import commands
import wavelink
from discord.ui import View, Button


class NodeStats(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.hybrid_command(
        name="node", 
        aliases=["lavalink"], 
        usage="/node", 
        help="Get Lavalink Info."
    )
    async def node(self, ctx):
        """Fetch real-time Lavalink node statistics."""
        try:
            nodes = wavelink.Pool.nodes.values()
            if not nodes:
                await ctx.send("⚠️ No Lavalink nodes are connected!")
                return

            node = list(nodes)[0]

            stats = await node.fetch_stats()
            info = await node.fetch_info()

            node_status = "Connected"

            players = getattr(stats, "players", 0)
            uptime = getattr(stats, "uptime", 0)
            memory = getattr(stats, "memory", None)
            cpu = getattr(stats, "cpu", None)
            system_load = getattr(cpu, "systemLoad", 0.0) * 100
            lavalink_load = getattr(cpu, "lavalinkLoad", 0.0) * 100

            hours, remainder = divmod(uptime // 1000, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_formatted = f"{hours} hours, {minutes} minutes, {seconds} seconds"

            build_time = (
                info.build_time.strftime("%Y-%m-%d %H:%M:%S")
                if info.build_time
                else "Unknown"
            )
            jvm_version = info.jvm
            lavaplayer_version = info.lavaplayer
            source_managers = (
                ", ".join(info.source_managers) if info.source_managers else "None"
            )
            plugins = (
                "\n".join(
                    [f"{plugin.name} (v{plugin.version})" for plugin in info.plugins]
                )
                or "None"
            )

            version_info = info.version
            semver = version_info.semver
            branch = info.git.branch
            commit = info.git.commit
            commit_time = info.git.commit_time.strftime("%Y-%m-%d %H:%M:%S")

            if memory is not None:
                memory_used = getattr(memory, "used", 0) / (1024 * 1024)
                memory_free = getattr(memory, "free", 0) / (1024 * 1024)
                memory_allocated = getattr(memory, "allocated", 0) / (1024 * 1024)
                memory_reservable = getattr(memory, "reservable", 0) / (1024 * 1024)
            else:
                memory_used = memory_free = memory_allocated = memory_reservable = 0

            if cpu is not None:
                cpu_cores = getattr(cpu, "cores", 0)
            else:
                cpu_cores = 0

            node_embed = discord.Embed(
                title="Fault's Node Statistics",
                color=discord.Color.from_rgb(30, 30, 30),
            )
            node_embed.add_field(
                name="Lavalink Info",
                value=f"> -# **Status**: [{node_status}](https://discord.gg/jsk)\n"
                f"> -# **Players**: [{players}](https://discord.gg/jsk)\n"
                f"> -# **Uptime**: [{uptime_formatted}](https://discord.gg/jsk)\n"
                f"> -# **JVM Version**: [{jvm_version}](https://discord.gg/jsk)\n"
                f"> -# **Build Time**: [{build_time}](https://discord.gg/jsk)\n"
                f"> -# **Lavaplayer Version**: [{lavaplayer_version}](https://discord.gg/jsk)\n",
                inline=False,
            )
            node_embed.add_field(
                name="Lavalink Version Info",
                value=f"> -# **Version**: [{semver}](https://discord.gg/jsk)\n"
                f"> -# **Branch**: [{branch}](https://discord.gg/jsk)\n"
                f"> -# **Commit**: [{commit}](https://discord.gg/jsk)\n"
                f"> -# **Commit Time**: [{commit_time}](https://discord.gg/jsk)",
                inline=False,
            )
            node_embed.add_field(
                name="Memory Usage",
                value=f"> -# **Used**: [{memory_used:.2f} MB](https://discord.gg/jsk)\n"
                f"> -# **Free**: [{memory_free:.2f} MB](https://discord.gg/jsk)\n"
                f"> -# **Allocated**: [{memory_allocated:.2f} MB](https://discord.gg/jsk)\n"
                f"> -# **Reservable**: [{memory_reservable:.2f} MB](https://discord.gg/jsk)",
                inline=False,
            )
            node_embed.add_field(
                name="CPU Information",
                value=f"> -# **Cores**: [{cpu_cores}](https://discord.gg/jsk)\n"
                f"> -# **System Load**: [{system_load:.2f}%](https://discord.gg/jsk)\n"
                f"> -# **Lavalink Load**: [{lavalink_load:.2f}%](https://discord.gg/jsk)",
                inline=False,
            )
            node_embed.set_footer(
                text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url
            )

            plugins_embed = discord.Embed(
                title="Fault's Plugins and Source Managers",
                color=discord.Color.from_rgb(30, 30, 30),
            )
            plugins_embed.add_field(
                name="Source Managers",
                value=f"> -# **Source Managers**: [{source_managers}](https://discord.gg/jsk)\n",
                inline=False,
            )
            plugins_embed.add_field(
                name="Used Plugins",
                value=f"> -# **Plugins**:\n[{plugins}]](https://discord.gg/jsk)",
                inline=False,
            )
            plugins_embed.set_footer(
                text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url
            )

            class NodeView(View):
                def __init__(self):
                    super().__init__(timeout=None)

                @discord.ui.button(label="Node", style=discord.ButtonStyle.gray)
                async def node_info_button(
                    self, interaction: discord.Interaction, button: Button
                ):
                    await interaction.response.edit_message(embed=node_embed)

                @discord.ui.button(label="Plugins", style=discord.ButtonStyle.gray)
                async def plugins_info_button(
                    self, interaction: discord.Interaction, button: Button
                ):
                    await interaction.response.edit_message(embed=plugins_embed)

                @discord.ui.button(label="Delete", style=discord.ButtonStyle.gray)
                async def delete_button(
                    self, interaction: discord.Interaction, button: Button
                ):
                    await interaction.message.delete()

            await ctx.send(embed=node_embed, view=NodeView())

        except Exception as e:
            await ctx.send(
                "⚠️ Unable to fetch node statistics. Is the Lavalink node running?"
            )
            print(f"Error fetching node stats: {e}")


async def setup(client):
    await client.add_cog(NodeStats(client))
