import discord
from discord.ext import commands
from google.cloud import secretmanager

from osc_challonge import get_players, get_ranking_data
from osc_battlefy import get_standings

def access_secret_version(project_id, secret_id, version_id):
    """
    Access the payload for the given secret version if one exists. The version
    can be a version number as a string (e.g. "5") or an alias (e.g. "latest").
    """
    client = secretmanager.SecretManagerServiceClient()
    name = client.secret_version_path(project_id, secret_id, version_id)
    response = client.access_secret_version(name)
    payload = response.payload.data.decode('UTF-8')
    return payload


bot = commands.Bot(command_prefix='!')
project_id = 'oscbot-280922'
TOKEN = access_secret_version(project_id, 'bot_dev', 1)
chal_user = access_secret_version(project_id, 'challonge_user', 1)
chal_key = access_secret_version(project_id, 'challonge_key', 1)


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.command()
async def players(ctx, name):
    await ctx.channel.trigger_typing()
    await ctx.send(get_players(name, chal_user, chal_key))


@bot.command()
async def tournament(ctx, name, display='False'):
    print('tournament ' + name)
    await ctx.channel.trigger_typing()
    data = get_ranking_data(name, chal_user, chal_key, display)
    await ctx.send(data)

@bot.command()
async def battlefy(ctx):
    await ctx.channel.trigger_typing()
    data = get_standings()
    await ctx.send(data)


@bot.command()
async def info(ctx):
    embed = discord.Embed(title="OSCar", description="OSC esports helper bot.")

    # give info about you here
    embed.add_field(name="Author", value="Bryjolf")

    # Shows the number of servers the bot is member of.
    embed.add_field(name="Server count", value=f"{len(bot.guilds)}")
    embed.add_field(name="Version", value="2.0")
    embed.add_field(name="Host", value="Google Cloud Platform Compute Engine", inline=False)
    await ctx.send(embed=embed)


bot.remove_command('help')


@bot.command()
async def help(ctx):
    embed = discord.Embed(title="OSCar", description="OSC esports helper bot.")
    embed.add_field(name="!tournament [challonge link]", value="Returns preprocess tournament data", inline=False)
    embed.add_field(name="!players [challonge link]", value="Returns player list", inline=False)

    await ctx.send(embed=embed)


bot.run(TOKEN)
