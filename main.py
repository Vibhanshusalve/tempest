import os

os.system("pip install -r requirements.txt")
import asyncio
import traceback
from threading import Thread
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands


from core import Context
from core.Cog import Cog
from core.Tempest import Tempest
from utils.Tools import *
from utils.config import *

import jishaku
import cogs 



#Configuring Jishaku behavior
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "False"
os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"


client = Tempest()
tree = client.tree
TOKEN = os.getenv("TOKEN")




@client.event
async def on_ready():
    await client.wait_until_ready()
    
    print("""
           \033[1;35m

        ____   ___  _   _ _   _ 
       / ___| / _ \| \ | | | | |
       \___ \| | | |  \| | | | |
        ___) | |_| | |\  | |_| |
       |____/ \___/|_| \_| \___/ 

       \033[0m
           """)
    print("Loaded & Online!")
    print(f"Logged in as: {client.user}")
    print(f"Connected to: {len(client.guilds)} guilds")
    print(f"Connected to: {len(client.users)} users")
    try:
        synced = await client.tree.sync()
        all_commands = list(client.commands)
        print(f"Synced Total {len(all_commands)} Client Commands and {len(synced)} Slash Commands")
    except Exception as e:
        print(e)


@client.event
async def on_command_completion(context: commands.Context) -> None:
    if context.author.id == 1070619070468214824:
        return

    full_command_name = context.command.qualified_name
    split = full_command_name.split("\n")
    executed_command = str(split[0])
    command_logs_channel_id = 1437318990312767600
    
    try:
        log_channel = client.get_channel(command_logs_channel_id)
        if log_channel is None:
            # Try to fetch if not in cache
            try:
                log_channel = await client.fetch_channel(command_logs_channel_id)
            except:
                print(f"Command logs channel {command_logs_channel_id} not found")
                return

        if context.guild is not None:
            try:
                embed = discord.Embed(color=0x000000)
                avatar_url = context.author.avatar.url if context.author.avatar else context.author.default_avatar.url
                embed.set_author(
                    name=f"Executed {executed_command} Command By : {context.author}",
                    icon_url=avatar_url
                )
                embed.set_thumbnail(url=avatar_url)
                embed.add_field(name="➡️ Command Name :",
                                value=f"{executed_command}",
                                inline=False)
                embed.add_field(
                    name="➡️ Command Executed By :",
                    value=f"{context.author} | ID: [{context.author.id}](https://discord.com/users/{context.author.id})",
                    inline=False)
                embed.add_field(
                    name="➡️ Command Executed In :",
                    value=f"{context.guild.name} | ID: [{context.guild.id}](https://discord.com/guilds/{context.guild.id})",
                    inline=False)
                embed.add_field(
                    name="➡️ Command Executed In Channel :",
                    value=f"{context.channel.name} | ID: [{context.channel.id}](https://discord.com/channels/{context.guild.id}/{context.channel.id})",
                    inline=False)

                embed.timestamp = discord.utils.utcnow()
                embed.set_footer(text="Tempest Federation™ ❤️",
                                 icon_url=client.user.display_avatar.url)

                
                await log_channel.send(embed=embed)
            except Exception as e:
                print(f'Command log failed: {e}')
                traceback.print_exc()
        else:
            try:
                embed1 = discord.Embed(color=0x000000)
                avatar_url = context.author.avatar.url if context.author.avatar else context.author.default_avatar.url
                embed1.set_author(
                    name=f"Executed {executed_command} Command By : {context.author}",
                    icon_url=avatar_url
                )
                embed1.set_thumbnail(url=avatar_url)
                embed1.add_field(name="➡️ Command Name :",
                                 value=f"{executed_command}",
                                 inline=False)
                embed1.add_field(
                    name="➡️ Command Executed By :",
                    value=f"{context.author} | ID: [{context.author.id}](https://discord.com/users/{context.author.id})",
                    inline=False)
                embed1.set_footer(text=f"Powered by Tempest Federation™",
                                  icon_url=client.user.display_avatar.url)
                await log_channel.send(embed=embed1)
            except Exception as e:
                print(f'Command log failed: {e}')
                traceback.print_exc()


from flask import Flask
from threading import Thread

app = Flask(__name__)


@app.route('/')
def home():
    return f"© Tempest Federation 2024"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    server = Thread(target=run)
    server.start()


keep_alive()


async def main():
    async with client:
        os.system("clear")
        #await client.load_extension("cogs")
        await client.load_extension("jishaku")
        await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
