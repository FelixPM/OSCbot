import discord
from discord.ext import commands
from google.cloud import secretmanager
from osc_aligulac import get_aligulac
from osc_challonge import get_players, get_ranking_data
from osc_battlefy import get_battlefy
import requests

def access_secret_version(project_id, secret_id, version_id):
    """
    Access the payload for the given secret version if one exists. The version
    can be a version number as a string (e.g. "5") or an alias (e.g. "latest").
    """
    client = secretmanager.SecretManagerServiceClient()
    name = client.secret_version_path(project_id, secret_id, version_id)
    request = secretmanager.AccessSecretVersionRequest(name=name)  # Create the request object
    response = client.access_secret_version(request)  # Pass the request object
    payload = response.payload.data.decode('UTF-8')
    return payload


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
project_id = 'oscbot-280922'
token = access_secret_version(project_id, 'bot_prod', 'latest')
chal_user = access_secret_version(project_id, 'challonge_user', 'latest')
chal_key = access_secret_version(project_id, 'challonge_key', 'latest')
ali_key = access_secret_version(project_id, 'aligulac_key', 'latest')


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


@bot.command(aliases=['t'])
async def tournament(ctx, name, display='False'):
    print('tournament ' + name)
    async with ctx.channel.typing():
        data = get_ranking_data(name, chal_user, chal_key, display)
    await ctx.send(data)


@bot.command(aliases=['a'])
async def aligulac(ctx, name):
    print('tournament ' + name)
    async with ctx.channel.typing():
        data = get_aligulac(name, ali_key)
    await ctx.send(data)


@bot.command(aliases=['b'])
async def battlefy(ctx, url):
    await ctx.send("Starting a long process... this may take a while.")
    try:
        data = await get_battlefy(url, ctx)
        await ctx.send("Processing complete.")
        if len(data) < 2000:
            await ctx.send(data)
        else:
            data_list = data.split('\n')
            len_data = len(data_list) // 2
            all_data = [data_list[:len_data], data_list[len_data:]]
            for data_chunk in all_data:
                await ctx.send('\n'.join(data_chunk))
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        return
    

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


bot.run(token)
