import time
import discord
import random
from discord.ext import commands
from quickchart import QuickChart
from settings.config import color  



async def generate_chart(ws_latency, msg_latency):
    qc = QuickChart()

    def gen(wsl, msg):
        rnd_wsl = random.uniform(-0.05, 0.05)
        rnd_msg = random.uniform(-0.02, 0.02)
        wsl = int(wsl + wsl * rnd_wsl)
        msg = int(msg + msg * rnd_msg)
        return [wsl, msg]

    data = []
    for _ in range(17):
        data.append(gen(ws_latency, msg_latency))
    data.append([ws_latency, msg_latency])

    qc.config = {
        "type": "line",
        "data": {
            "labels": ["_" for _ in range(17)],
            "datasets": [
                {
                    "label": "WebSocket Latency",
                    "yAxisID": "ws",
                    "data": [item[0] for item in data],
                    "fill": "start",
                    "borderColor": "#ff5500",
                    "borderWidth": 2,
                    "backgroundColor": "rgba(255, 85, 0, 0.5)",
                    "pointRadius": 5,
                    "pointBackgroundColor": "#ff5500",
                },
                {
                    "label": "Message Latency",
                    "yAxisID": "msg",
                    "data": [item[1] for item in data],
                    "fill": "start",
                    "borderColor": "#00d8ff",
                    "borderWidth": 2,
                    "backgroundColor": "rgba(0, 216, 255, 0.5)",
                    "pointRadius": 5,
                    "pointBackgroundColor": "#00d8ff",
                },
            ],
        },
        "options": {
            "scales": {
                "yAxes": [
                    {
                        "id": "msg",
                        "type": "linear",
                        "position": "right",
                        "ticks": {
                            "suggestedMin": 0,
                            "suggestedMax": min(max(msg_latency + 50, 100), 100),  # Set max to 100
                            "stepSize": 50,  # Set stepSize to 50
                        },
                    },
                    {
                        "id": "ws",
                        "type": "linear",
                        "position": "left",
                        "ticks": {
                            "suggestedMin": 0,
                            "suggestedMax": min(max(ws_latency + 50, 100), 100),  # Set max to 100
                            "stepSize": 50,  # Set stepSize to 50
                        },
                    },
                ]
            },
            "title": {"display": True, "text": "Latency Comparison", "fontSize": 16},
            "legend": {"display": True, "position": "top"},
            "elements": {"line": {"tension": 0.4}},
        },
    }

    qc.width = 600
    qc.height = 300
    qc.background_color = "transparent"

    uri = qc.get_url()
    return uri



class settings(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.start_time = time.time()

    @commands.hybrid_command(name="ping", description="Shows the bot's latency as a graph.")
    async def ping(self, ctx):
        """
    Check the bot's ping.

    No arguments are needed, and it responds with the bot's total uptime.

    Usage:
    - `/ping`: Returns the bot's ping in a human-readable format .
    """
        msg_latency = int(round(time.time() * 1000)) - int(
            round(ctx.message.created_at.timestamp() * 1000)
        )
        ws_latency = round(self.client.latency * 1000)
        uri = await generate_chart(ws_latency, msg_latency)

        embed = discord.Embed(color=color)
        embed.set_image(url=uri)
        embed.set_footer(text="Latency Graph")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="uptime", description="Check the bot's uptime")
    async def uptime(self, ctx):
        """
    Check the bot's uptime.

    This command checks how long the bot has been running since its start. The uptime is returned in days, hours, minutes, and seconds format. If the bot has been running for less than a day, only hours, minutes, and seconds are shown.

    No arguments are needed, and it responds with the bot's total uptime.

    Usage:
    - `/uptime`: Returns the bot's uptime in a human-readable format (e.g., "1 day, 2 hours, 10 minutes").
    """
        current_time = time.time()
        uptime_seconds = int(current_time - self.start_time)

        days = uptime_seconds // (24 * 3600)
        hours = (uptime_seconds % (24 * 3600)) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60

        uptime = []
        if days > 0:
            uptime.append(f"{days} day{'s' if days > 1 else ''}")
        if hours > 0:
            uptime.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes > 0:
            uptime.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        if seconds > 0:
            uptime.append(f"{seconds} second{'s' if seconds > 1 else ''}")

        uptime_str = ", ".join(uptime) if uptime else "0 seconds"

        embed = discord.Embed(
            description=f"Uptime: {uptime_str}",
            color=color
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)



async def setup(client):
    await client.add_cog(settings(client))
