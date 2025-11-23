import discord
from discord.ext import commands
from discord import ui
from utils.Tools import *

class BanView(ui.View):
    def __init__(self, user, author):
        super().__init__(timeout=120)
        self.user = user
        self.author = author
        self.message = None  
        self.color = discord.Color.from_rgb(0, 0, 0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @ui.button(label="Unban", style=discord.ButtonStyle.success)
    async def unban(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReasonModal(user=self.user, author=self.author, view=self)
        await interaction.response.send_modal(modal)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

class AlreadyBannedView(ui.View):
    def __init__(self, user, author):
        super().__init__(timeout=120)
        self.user = user
        self.author = author
        self.message = None  

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @ui.button(label="Unban", style=discord.ButtonStyle.success)
    async def unban(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReasonModal(user=self.user, author=self.author, view=self)
        await interaction.response.send_modal(modal)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

class ReasonModal(ui.Modal):
    def __init__(self, user, author, view):
        super().__init__(title="Unban Reason")
        self.user = user
        self.author = author
        self.view = view
        self.reason_input = ui.TextInput(label="Reason for Unbanning", placeholder="Provide a reason to unban or leave it blank for no reason.", required = False, max_length=2000, style=discord.TextStyle.paragraph)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value or "No reason provided"
        try:
            await self.user.send(f"✅ You have been Unbanned from **{self.author.guild.name}** by **{self.author}**. Reason: {reason or 'No reason provided'}")
            dm_status = "Yes"
        except discord.Forbidden:
            dm_status = "No"
        except discord.HTTPException:
            dm_status = "No"
            
        embed = discord.Embed(description=f"**• Target User:** [{self.user}](https://discord.com/users/{self.user.id})\n✅ **User Mention:** {self.user.mention}\n**• DM Sent:** {dm_status}\n**✅ Reason:** {reason}", color=0x000000)
        embed.set_author(name=f"Successfully Unbanned {self.user.name}", icon_url=self.user.avatar.url if self.user.avatar else self.user.default_avatar.url)
        embed.add_field(name="🛡️ Moderator:", value=interaction.user.mention, inline=False)
        embed.set_footer(text=f"Requested by {self.author}", icon_url=self.author.avatar.url if self.author.avatar else self.author.default_avatar.url)
        embed.timestamp = discord.utils.utcnow()

        try:
            await interaction.guild.unban(self.user, reason=f"Unban requested by {self.author}")
            
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

        try:
            await interaction.response.edit_message(embed=embed, view=self.view)
            for item in self.view.children:
                item.disabled = True
                await interaction.message.edit(view=self.view)
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass
        
        

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)

    def get_user_avatar(self, user):
        return user.avatar.url if user.avatar else user.default_avatar.url

    @commands.hybrid_command(
        name="ban",
        help="Bans a user from the Server",
        usage="ban <member>",
        aliases=["fuckban", "hackban"])
    @blacklist_check()
    @ignore_check()
    @top_check()
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.User, *, reason=None):
        await ctx.defer()

        member = ctx.guild.get_member(user.id)
        if not member:
            try:
                user = await self.bot.fetch_user(user.id)
            except discord.NotFound:
                await ctx.send(f"User with ID {user.id} not found.")
                return

        bans = [entry async for entry in ctx.guild.bans()]
        if any(ban_entry.user.id == user.id for ban_entry in bans):
            embed = discord.Embed(description=f"**Requested User is already banned in this server.**", color=self.color)
            embed.add_field(name="__Unban__:", value="Click on the `Unban` button to unban the mentioned user.")
            embed.set_author(name=f"{user.name} is Already Banned!", icon_url=self.get_user_avatar(user))
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            view = AlreadyBannedView(user=user, author=ctx.author)
            message = await ctx.send(embed=embed, view=view)
            view.message = message 
            return

        if member == ctx.guild.owner:
            error = discord.Embed(color=self.color, description="I can't ban the Server Owner!")
            error.set_author(name="Error Banning User", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            error.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            return await ctx.send(embed=error)

        if isinstance(member, discord.Member) and member.top_role >= ctx.guild.me.top_role:
            error = discord.Embed(color=self.color, description="I can't ban a user with a higher or equal role!")
            error.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            error.set_author(name="Error Banning User", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            return await ctx.send(embed=error)

        if isinstance(member, discord.Member):
            if ctx.author != ctx.guild.owner:
                if member.top_role >= ctx.author.top_role:
                    error = discord.Embed(color=self.color, description="You can't ban a user with a higher or equal role!")
                    error.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
                    error.set_author(name="Error Banning User", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
                    return await ctx.send(embed=error)

        try:
            await user.send(f"⚠️ You have been banned from **{ctx.guild.name}** by **{ctx.author}**. Reason: {reason or 'No reason provided'}")
            dm_status = "Yes"
        except discord.Forbidden:
            dm_status = "No"
        except discord.HTTPException:
            dm_status = "No"

        await ctx.guild.ban(user, reason=f"Ban requested by {ctx.author} for reason: {reason or 'No reason provided'}")

        reasonn = reason or "No reason provided"
        embed = discord.Embed(description=f"**• Target User:** [{user}](https://discord.com/users/{user.id})\n**✅ User Mention:** {user.mention}\n**• DM Sent:** {dm_status}\n**✅ Reason:** {reasonn}", color=self.color)
        embed.set_author(name=f"Successfully Banned {user.name}", icon_url=self.get_user_avatar(user))
        embed.add_field(name="🛡️ Moderator:", value=ctx.author.mention, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
        embed.timestamp = discord.utils.utcnow()

        view = BanView(user=user, author=ctx.author)
        message = await ctx.send(embed=embed, view=view)
        view.message = message



"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import ui

class HideUnhideView(ui.View):
    def __init__(self, channel, author, ctx):
        super().__init__(timeout=120)
        self.channel = channel
        self.author = author
        self.ctx = ctx 
        self.message = None  

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @ui.button(label="Unhide", style=discord.ButtonStyle.success)
    async def unhide(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.channel.set_permissions(interaction.guild.default_role, read_messages=True)
        await interaction.response.send_message(f"{self.channel.mention} has been unhidden.", ephemeral=True)

        embed = discord.Embed(
            description=f"• **Channel**: {self.channel.mention}\n✅ **Status**: Unhidden\n• **Reason:** Unhide request by {self.author}",
            color=0x000000
        )
        embed.add_field(name="• **Moderator:**", value=self.ctx.author.mention, inline=False)
        embed.set_author(name=f"Successfully Unhidden {self.channel.name}", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        await self.message.edit(embed=embed, view=self)

        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        await self.message.edit(view=self)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class Hide(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)

    @commands.hybrid_command(
        name="hide",
        help="Hides a channel from the default role (@everyone).",
        usage="hide <channel>",
        aliases=["hidechannel"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def hide_command(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel 
        if not channel.permissions_for(ctx.guild.default_role).read_messages:
            embed = discord.Embed(
                description=f"**• Channel**: {channel.mention}\n✅ **Status**: Already Hidden",
                color=self.color
            )
            embed.set_author(name=f"{channel.name} is Already Hidden", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
            view = HideUnhideView(channel=channel, author=ctx.author, ctx=ctx) 
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            return

        await channel.set_permissions(ctx.guild.default_role, read_messages=False)

        embed = discord.Embed(
            description=f"• **Channel**: {channel.mention}\n✅ **Status**: Hidden\n• **Reason:** Hide request by {ctx.author}",
            color=self.color
        )
        embed.add_field(name="• **Moderator:**", value=ctx.author.mention, inline=False)
        embed.set_author(name=f"Successfully Hidden {channel.name}", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        view = HideUnhideView(channel=channel, author=ctx.author, ctx=ctx) 
        message = await ctx.send(embed=embed, view=view)
        view.message = message


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import ui
from utils.Tools import *

class KickView(ui.View):
    def __init__(self, member):
        super().__init__(timeout=120)
        self.member = member
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

class Kick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)

    @commands.hybrid_command(
        name="kick",
        help="Kicks a member from the server.",
        usage="kick <member> [reason]",
        aliases=["kickmember"])
    @blacklist_check()
    @ignore_check()
    @top_check()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick_command(self, ctx, member: discord.Member, *, reason: str = None):
        reason = reason or "No reason provided"

        if member == ctx.author:
            return await ctx.reply("You cannot kick yourself.")

        if member == ctx.bot.user:
            return await ctx.reply("You cannot kick me.")

        if not ctx.author == ctx.guild.owner:
            if member == ctx.guild.owner:
                return await ctx.reply("I cannot kick the server owner.")

            if ctx.author.top_role <= member.top_role:
                return await ctx.reply("You cannot kick a member with a higher or equal role.")

        if ctx.guild.me.top_role <= member.top_role:
            return await ctx.reply("I cannot kick a member with a higher or equal role.")

        if member not in ctx.guild.members:
            embed = discord.Embed(
                description=f"**Member Not Found:** The specified member does not exist in this server.",
                color=self.color
            )
            view = KickView(member)
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            return

        
        dm_status = "Yes"
        try:
            await member.send(f"You have been kicked from **{ctx.guild.name}**. Reason: {reason}")
        except discord.Forbidden:
            dm_status = "No"
        except discord.HTTPException:
            dm_status = "No"

        
        await member.kick(reason=f"Kicked by {ctx.author} | Reason: {reason}")
        

        
        embed = discord.Embed(
            description=(
                f"**• Target User:** [{member}](https://discord.com/users/{member.id})\n"
                f"✅ **User Mention:** {member.mention}\n"
                f"✅ **Reason:** {reason}\n"
                f"• **DM Sent:** {dm_status}"
            ),
            color=self.color
        )
        embed.set_author(name=f"Successfully Kicked {member.name}", icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="🛡️ Moderator:", value=ctx.author.mention, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.timestamp = discord.utils.utcnow()

        view = KickView(member)
        message = await ctx.send(embed=embed, view=view)
        view.message = message


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import ui

class LockUnlockView(ui.View):
    def __init__(self, channel, author, ctx):
        super().__init__(timeout=120)
        self.channel = channel
        self.author = author
        self.ctx = ctx  
        self.message = None  

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @ui.button(label="Unlock", style=discord.ButtonStyle.success)
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message(f"{self.channel.mention} has been unlocked.", ephemeral=True)

        embed = discord.Embed(
            description=f"• **Channel**: {self.channel.mention}\n✅ **Status**: Unlocked\n• **Reason:** Unlock request by {self.author}",
            color=0x000000
        )
        embed.add_field(name="• **Moderator:**", value=self.ctx.author.mention, inline=False)
        embed.set_author(name=f"Successfully Unlocked {self.channel.name}", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        await self.message.edit(embed=embed, view=self)

        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        await self.message.edit(view=self)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class Lock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)

    @commands.hybrid_command(
        name="lock",
        help="Locks a channel to prevent sending messages.",
        usage="lock <channel>",
        aliases=["lockchannel"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def lock_command(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel 
        if channel.permissions_for(ctx.guild.default_role).send_messages is False:
            embed = discord.Embed(
                description=f"**• Channel**: {channel.mention}\n✅ **Status**: Already Locked",
                color=self.color
            )
            embed.set_author(name=f"{channel.name} is Already Locked", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
            view = LockUnlockView(channel=channel, author=ctx.author, ctx=ctx)  
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            return

        await channel.set_permissions(ctx.guild.default_role, send_messages=False)

        embed = discord.Embed(
            description=f"• **Channel**: {channel.mention}\n✅ **Status**: Locked\n• **Reason:** Lock request by {ctx.author}",
            color=self.color
        )
        embed.add_field(name="• **Moderator:**", value=ctx.author.mention, inline=False)
        embed.set_author(name=f"Successfully Locked {channel.name}", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        view = LockUnlockView(channel=channel, author=ctx.author, ctx=ctx)  
        message = await ctx.send(embed=embed, view=view)
        view.message = message


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import re
from typing import *
from utils.Tools import *
from discord.ui import Button, View
from typing import Union, Optional
from typing import Union, Optional
from io import BytesIO
import requests
import aiohttp
import time
from datetime import datetime, timezone, timedelta


time_regex = re.compile(r"(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}


def convert(argument):
  args = argument.lower()
  matches = re.findall(time_regex, args)
  time = 0
  for key, value in matches:
    try:
      time += time_dict[value] * float(key)
    except KeyError:
      raise commands.BadArgument(
        f"{value} is an invalid time key! h|m|s|d are valid arguments")
    except ValueError:
      raise commands.BadArgument(f"{key} is not a number!")
  return round(time)

async def do_removal(ctx, limit, predicate, *, before=None, after=None):
  if limit > 2000:
      return await ctx.error(f"Too many messages to search given ({limit}/2000)")

  if before is None:
      before = ctx.message
  else:
      before = discord.Object(id=before)

  if after is not None:
      after = discord.Object(id=after)

  try:
      deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
  except discord.Forbidden as e:
      return await ctx.error("I do not have permissions to delete messages.")
  except discord.HTTPException as e:
      return await ctx.error(f"Error: {e} (try a smaller search?)")

  spammers = Counter(m.author.display_name for m in deleted)
  deleted = len(deleted)
  messages = [f'✅ | {deleted} message{" was" if deleted == 1 else "s were"} removed.']
  if deleted:
      messages.append("")
      spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
      messages.extend(f"**{name}**: {count}" for name, count in spammers)

  to_send = "\n".join(messages)

  if len(to_send) > 2000:
      await ctx.send(f"✅ | Successfully removed {deleted} messages.", delete_after=7)
  else:
      await ctx.send(to_send, delete_after=7)
    

class Message(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.color = 0x000000


  @commands.group(invoke_without_command=True, aliases=["purge"], help="Clears the messages")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def clear(self, ctx, Choice: Union[discord.Member, int], Amount: int = None):
        await ctx.message.delete()

        if isinstance(Choice, discord.Member):
            search = Amount or 5
            return await do_removal(ctx, search, lambda e: e.author == Choice)

        elif isinstance(Choice, int):
            return await do_removal(ctx, Choice, lambda e: True)



  @clear.command(help="Clears the messages having embeds")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def embeds(self, ctx, search=100):
        await ctx.message.delete()
        await do_removal(ctx, search, lambda e: len(e.embeds))


  @clear.command(help="Clears the messages having files")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def files(self, ctx, search=100):

        await ctx.message.delete()
        await do_removal(ctx, search, lambda e: len(e.attachments))

  @clear.command(help="Clears the messages having images")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def images(self, ctx, search=100):

        await ctx.message.delete()
        await do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))


  @clear.command(name="all", help="Clears all messages")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def _remove_all(self, ctx, search=100):

        await ctx.message.delete()
        await do_removal(ctx, search, lambda e: True)

  @clear.command(help="Clears the messages of a specific user")
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def user(self, ctx, member: discord.Member, search=100):

        await ctx.message.delete()
        await do_removal(ctx, search, lambda e: e.author == member)



  @clear.command(help="Clears the messages containing a specifix string")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def contains(self, ctx, *, string: str):

        await ctx.message.delete()
        if len(string) < 3:
            await ctx.error("The substring length must be at least 3 characters.")
        else:
            await do_removal(ctx, 100, lambda e: string in e.content)

  @clear.command(name="bot", aliases=["bots","b"], help="Clears the messages sent by bot")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def _bot(self, ctx, prefix=None, search=100):

        await ctx.message.delete()

        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix))

        await do_removal(ctx, search, predicate)

  @clear.command(name="emoji", aliases=["emojis"], help="Clears the messages having emojis")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)

  async def _emoji(self, ctx, search=100):

        await ctx.message.delete()
        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>")

        def predicate(m):
            return custom_emoji.search(m.content)

        await do_removal(ctx, search, predicate)

  @clear.command(name="reactions", help="Clears the reaction from the messages")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def _reactions(self, ctx, search=100):

        await ctx.message.delete()

        if search > 2000:
            return await ctx.send(f"Too many messages to search for ({search}/2000)")

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()

        await ctx.success(f"✅ | Successfully removed {total_reactions} reactions.")
            



  @commands.command(name="purgebots",
                    aliases=["cleanup", "pb", "clearbot", "clearbots"],
                    help="Clear recently bot messages in channel")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def _purgebot(self, ctx, prefix=None, search=100):

    await ctx.message.delete()

    def predicate(m):
        return (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix))
      
    await do_removal(ctx, search, predicate)


  @commands.command(name="purgeuser",
                    aliases=["pu", "cu", "clearuser"],
                    help="Clear recent messages of a user in channel")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def purguser(self, ctx, member: discord.Member, search=100):
      
      await ctx.message.delete()
      await do_removal(ctx, search, lambda e: e.author == member)

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
import asyncio
import datetime
import re
import typing
import typing as t
from typing import *
from utils.Tools import *
from core import Cog, Tempest, Context
from discord.ext.commands import Converter
from discord.ext import commands, tasks
from discord.ui import Button, View
from typing import Union, Optional
from utils import Paginator, DescriptionEmbedPaginator, FieldPagePaginator, TextPaginator
from typing import Union, Optional
from io import BytesIO
import requests
import aiohttp
import time
from datetime import datetime, timezone, timedelta
import sqlite3
from typing import *
from discord.utils import utcnow



time_regex = re.compile(r"(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}


def convert(argument):
  args = argument.lower()
  matches = re.findall(time_regex, args)
  time = 0
  for key, value in matches:
    try:
      time += time_dict[value] * float(key)
    except KeyError:
      raise commands.BadArgument(
        f"{value} is an invalid time key! h|m|s|d are valid arguments")
    except ValueError:
      raise commands.BadArgument(f"{key} is not a number!")
  return round(time)

async def do_removal(ctx, limit, predicate, *, before=None, after=None):
    if limit > 2000:
        return await ctx.error(f"Too many messages to search given ({limit}/2000)")

    if before is None:
        before = ctx.message
    else:
        before = discord.Object(id=before)

    if after is not None:
        after = discord.Object(id=after)

    try:
        deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
    except discord.Forbidden as e:
        return await ctx.error("I do not have permissions to delete messages.")
    except discord.HTTPException as e:
        return await ctx.error(f"Error: {e} (try a smaller search?)")

    spammers = Counter(m.author.display_name for m in deleted)
    deleted = len(deleted)
    messages = [f'✅ | {deleted} message{" was" if deleted == 1 else "s were"} removed.']
    if deleted:
        messages.append("")
        spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
        messages.extend(f"**{name}**: {count}" for name, count in spammers)

    to_send = "\n".join(messages)

    if len(to_send) > 2000:
        await ctx.send(f"✅ | Successfully removed {deleted} messages.", delete_after=7)
    else:
        await ctx.send(to_send, delete_after=7)




class Moderation(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.color = 0x000000
    self.sniped = {}

  def convert(self, time):
    pos = ["s", "m", "h", "d"]

    time_dict = {"s": 1, "m": 60, "h": 3600, "d": 3600 * 24}
    unit = time[-1]
    if unit not in pos:
      return -1
    try:
      val = int(time[:-1])
    except:
      return -2
    return val * time_dict[unit]



  @commands.command()
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def enlarge(self, ctx,  emoji: Union[discord.Emoji, discord.PartialEmoji, str]):
    url = emoji.url
    await ctx.send(url)




  @commands.hybrid_command(name="unlockall",
                    help="Unlocks all channels in the Guild.",
                    usage="unlockall")
  @blacklist_check()
  @ignore_check()
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  @commands.cooldown(1, 15, commands.BucketType.channel)
  async def unlockall(self, ctx):
      if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
          button = Button(label="Confirm",
                    style=discord.ButtonStyle.green,
                    emoji="✅")
          button1 = Button(label="Cancel",
                     style=discord.ButtonStyle.red,
                     emoji="❌")
          async def button_callback(interaction: discord.Interaction):
              a = 0
              if interaction.user == ctx.author:
                  if interaction.guild.me.guild_permissions.manage_roles:
                      embed1 = discord.Embed(
                     color=self.color,
                    description=f"Unlocking all channels in {ctx.guild.name} .")
                      await interaction.response.edit_message(
                       embed=embed1, view=None)
                      for channel in interaction.guild.channels:
                          try:
                              await channel.set_permissions(
                                   ctx.guild.default_role,
                                overwrite=discord.PermissionOverwrite(send_messages=True,
                                                 read_messages=True),
                                         reason="Unlockall Command Executed By: {}".format(ctx.author))
                              a += 1  
                          except Exception as e:
                              print(e)
                      await interaction.channel.send(
                              content=f"✅ | Successfully Unlocked {a} Channels")   
                      return
                  else:
                    await interaction.response.edit_message(
                         content=
                           "🔔 | It seems I'm missing the necessary permissions. Please grant me the `manage roles` permissions and try again.",
                              embed=None,
                                  view=None)
              else:
                await interaction.response.send_message("Oops! It looks like that message isn't from you. You need to run the command yourself to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)

          async def button1_callback(interaction: discord.Interaction):   
              if interaction.user == ctx.author:  
                  embed2 = discord.Embed(
                     color=self.color,
                    description=f"Cancelled, I won't proceed with unlocking any channel.")
                  await interaction.response.edit_message(
                      embed=embed2, view=None)   
              else:
                  await interaction.response.send_message("Oops! It looks like that message isn't from you. You need to run the command yourself to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)
          embed = discord.Embed(
                  color=self.color,
                 description=f'**Do you really want to unlock all channels in {ctx.guild.name}**')
          view = View()
          button.callback = button_callback
          button1.callback = button1_callback
          view.add_item(button)
          view.add_item(button1)
          embed.set_footer(text="Please click either 'Confirm' or 'Cancel' to proceed. You have 30 seconds to decide!")
          await ctx.reply(embed=embed, view=view, mention_author=False,delete_after=30)     


      else:
          embed5 = discord.Embed(title="🚫 Access Denied",
                description="Your role should be above my top role.",
                color=0x000000)
          embed5.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
          await ctx.send(embed=embed5, mention_author=False)  



  @commands.hybrid_command(name="lockall",
                    help="locks all the channels in Guild.",
                    usage="lockall")
  @blacklist_check()
  @ignore_check()
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  @commands.cooldown(1, 15, commands.BucketType.channel)
  async def lockall(self, ctx):
      if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
          button = Button(label="Confirm",
                    style=discord.ButtonStyle.green,
                    emoji="✅")
          button1 = Button(label="Cancel",
                     style=discord.ButtonStyle.red,
                     emoji="❌")
          async def button_callback(interaction: discord.Interaction):
              a = 0
              if interaction.user == ctx.author:
                  if interaction.guild.me.guild_permissions.manage_roles:
                      embed1 = discord.Embed(
                     color=self.color,
                    description=f"Locking all channels in {ctx.guild.name}...")
                      await interaction.response.edit_message(
                       embed=embed1, view=None)
                      for channel in interaction.guild.channels:
                          try:
                              await channel.set_permissions(ctx.guild.default_role,
                                      overwrite=discord.PermissionOverwrite(
                                        send_messages=False,
                                        read_messages=True),
                                         reason="Lockall command executed by: {}".format(ctx.author))
                              a += 1  
                          except Exception as e:
                              print(e)
                      await interaction.channel.send(
                              content=f"✅ | Successfully locked {a} Channels")
                      return
                  else:
                    await interaction.response.edit_message(
                         content=
                           "🚫 | It seems I'm missing the necessary permissions. Please grant me the `manage roles` permissions and try again.",
                              embed=None,
                                  view=None)
              else:
                await interaction.response.send_message("Oops! It looks like that message isn't from you. You need to run the command yourself to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)

          async def button1_callback(interaction: discord.Interaction):   
              if interaction.user == ctx.author:  
                  embed2 = discord.Embed(
                     color=self.color,
                    description=f"Cancelled, I won't proceed with locking any channel.")
                  await interaction.response.edit_message(
                      embed=embed2, view=None)   
              else:
                  await interaction.response.send_message("Oops! It looks like that message isn't from you. You need to run the command yourself to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)
          embed = discord.Embed(
                  color=self.color,
                 description=f'**Do you really want to lock all channels in {ctx.guild.name}**')
          view = View()
          button.callback = button_callback
          button1.callback = button1_callback
          view.add_item(button)
          view.add_item(button1)
          embed.set_footer(text=f"Please click either 'Confirm' or 'Cancel' to proceed. You have 30 seconds to decide!")
          await ctx.reply(embed=embed, view=view, mention_author=False,delete_after=30)     

      else:
          denied = discord.Embed(title="🚫 Access Denied",
              description="Your role should be above my top role.",
              color=0x000000)
          denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
          await ctx.send(embed=denied, mention_author=False)
          

  @commands.hybrid_command(name="give",
                    help="Gives the mentioned user a role.",
                    usage="give <user> <role>",
                    aliases=["addrole"])
  @blacklist_check()
  @ignore_check()
  @top_check()
  @commands.cooldown(1, 10, commands.BucketType.user)
  @commands.has_permissions(manage_roles=True)
  @commands.bot_has_permissions(manage_roles= True)
  async def give(self, ctx, member: discord.Member, *, role: discord.Role):
    if not ctx.guild.me.guild_permissions.manage_roles:
        return await ctx.send("🚫 I don't have permission to manage roles!")

    if role >= ctx.guild.me.top_role:
        error = discord.Embed(
            color=self.color,
            description="I can't manage roles for a user with a higher or equal role!"
        )

        error.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        error.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=error)

    if ctx.author != ctx.guild.owner and ctx.author.top_role <= member.top_role:
        error = discord.Embed(
            color=self.color,
            description="You can't manage roles for a user with a higher or equal role than yours!"
        )
        error.set_author(name="Access Denied", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        error.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=error)

    try:
        if role not in member.roles:
            await member.add_roles(role, reason=f"Role added by {ctx.author} (ID: {ctx.author.id})")
            success = discord.Embed(
                color=self.color,
                description=f"Successfully **added** role {role.name} to {member.mention}."
            )
            success.set_author(name="Role Added", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
            success.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        else:
            await member.remove_roles(role, reason=f"Role removed by {ctx.author} (ID: {ctx.author.id})")
            success = discord.Embed(
                color=self.color,
                description=f"Successfully **removed** role {role.name} from {member.mention}."
            )
            success.set_author(name="Role Removed", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
            success.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=success)
    except discord.Forbidden:
        error = discord.Embed(
            color=self.color,
            description="🚫 I don't have permission to manage roles for this user!"
        )
        await ctx.send(embed=error)
    except Exception as e:
        error = discord.Embed(
            color=self.color,
            description=f"🚫 An unexpected error occurred: {str(e)}"
        )
        await ctx.send(embed=error)



  @commands.hybrid_command(name="hideall", help="Hides all the channels .",
                    usage="hideall")
  @blacklist_check()
  @ignore_check()
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  @commands.cooldown(1, 15, commands.BucketType.channel)
  async def hideall(self, ctx):
      if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
          button = Button(label="Confirm",
                    style=discord.ButtonStyle.green,
                    emoji="✅")
          button1 = Button(label="Cancel",
                     style=discord.ButtonStyle.red,
                     emoji="❌")
          async def button_callback(interaction: discord.Interaction):
              a = 0
              if interaction.user == ctx.author:
                  if interaction.guild.me.guild_permissions.manage_roles:
                      embed1 = discord.Embed(
                     color=self.color,
                    description=f"Hiding all channels in {ctx.guild.name} ...")
                      await interaction.response.edit_message(
                       embed=embed1, view=None)
                      for channel in interaction.guild.channels:
                          try:
                              await channel.set_permissions(ctx.guild.default_role, view_channel=False,
                                         reason="Hideall Executed by: {}".format(ctx.author))
                              a += 1  
                          except Exception as e:
                              print(e)
                      await interaction.channel.send(
                              content=f"✅ | Successfully Hidden {a} Channel(s) .")
                      return
                  else:
                    await interaction.response.edit_message(
                         content=
                           "🚫 | It seems I'm missing the necessary permissions. Please grant me the `manage channels` permissions and try again.",
                              embed=None,
                                  view=None)
              else:
                await interaction.response.send_message("Oops! It looks like that message isn't from you. You need to run the command yourself to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)

          async def button1_callback(interaction: discord.Interaction):   
              if interaction.user == ctx.author:  
                  embed2 = discord.Embed(
                     color=self.color,
                    description=f"Cancelled, I won't proceed with hiding any channel.")
                  await interaction.response.edit_message(
                      embed=embed2, view=None)   
              else:
                  await interaction.response.send_message("Oops! It looks like that message isn't from you. You need to run the command yourself to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)
          embed = discord.Embed(
                  color=self.color,
                 description=f'**Do you really want to hide all channels in {ctx.guild.name}**')
          view = View()
          button.callback = button_callback
          button1.callback = button1_callback
          view.add_item(button)
          view.add_item(button1)
          embed.set_footer(text=f"Please click either 'Confirm' or 'Cancel' to proceed. You have 30 seconds to decide!")
          await ctx.reply(embed=embed, view=view, mention_author=False,delete_after=30)

      else:
          denied = discord.Embed(title="🚫 Access Denied",
              description="Your role should be above my top role.",
              color=0x000000)
          denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
          await ctx.send(embed=denied, mention_author=False)

  @commands.hybrid_command(name="unhideall", help="Unhides all the channels in the server.",
                    usage="unhideall")
  @blacklist_check()
  @ignore_check()
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  @commands.cooldown(1, 15, commands.BucketType.channel)
  async def unhideall(self, ctx):
      if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
          button = Button(label="Confirm",
                    style=discord.ButtonStyle.green,
                    emoji="✅")
          button1 = Button(label="Cancel",
                     style=discord.ButtonStyle.red,
                     emoji="❌")
          async def button_callback(interaction: discord.Interaction):
              a = 0
              if interaction.user == ctx.author:
                  if interaction.guild.me.guild_permissions.manage_roles:
                      embed1 = discord.Embed(
                     color=self.color,
                    description=f"Unhiding all channels in {ctx.guild.name} .")
                      await interaction.response.edit_message(
                       embed=embed1, view=None)
                      for channel in interaction.guild.channels:
                          try:
                              await channel.set_permissions(ctx.guild.default_role, view_channel=True,
                                         reason="Unhideall Command Executed By: {}".format(ctx.author))
                              a += 1  
                          except Exception as e:
                              print(e)
                      await interaction.channel.send(
                              content=f"✅ | Successfully Unhidden {a} Channel(s) .")
                      return
                  else:
                    await interaction.response.edit_message(
                         content=
                           "🚫 | It seems I'm missing the necessary permissions. Please grant me the `manage channels` permissions and try again.",
                              embed=None,
                                  view=None)
              else:
                await interaction.response.send_message("Oops! It looks like that message isn't from you. You need to run the command yourself to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)

          async def button1_callback(interaction: discord.Interaction):   
              if interaction.user == ctx.author:  
                  embed2 = discord.Embed(
                     color=self.color,
                    description=f"Cancelled, I won't proceed with unhiding any channel.")
                  await interaction.response.edit_message(
                      embed=embed2, view=None)   
              else:
                  await interaction.response.send_message("Oops! It looks like that message isn't from you. You need to run the command yourself to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)
          embed = discord.Embed(
                  color=self.color,
                 description=f'**Do you really want to unhide all channels in {ctx.guild.name}**')
          view = View()
          button.callback = button_callback
          button1.callback = button1_callback
          view.add_item(button)
          view.add_item(button1)
          embed.set_footer(text=f"Please click either 'Confirm' or 'Cancel' to proceed. You have 30 seconds to decide!")
          await ctx.reply(embed=embed, view=view, mention_author=False,delete_after=30)     

      else:
          denied = discord.Embed(title="🚫 Access Denied",
              description="Your role should be above my top role.",
              color=0x000000)
          denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
          await ctx.send(embed=denied, mention_author=False)



  @commands.hybrid_command(
        name="prefix",
        aliases=["setprefix", "prefixset"],
        help="Allows you to change the prefix of the bot for this server"
    )
  @blacklist_check()
  @ignore_check()
  @commands.has_permissions(administrator=True)
  @commands.cooldown(1, 10, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  async def _prefix(self, ctx: commands.Context, prefix: str):
      if not prefix:
          await ctx.reply(embed=discord.Embed(title="❌ Error",
                description="Prefix cannot be empty. Please provide a valid prefix.",
                color=self.color
            ))
          return
          
      data = await getConfig(ctx.guild.id)
      if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
          data["prefix"] = str(prefix)
          await updateConfig(ctx.guild.id, data)
          embed1=discord.Embed(title="✅ Success",
                description=f"Changed Prefix For this guild to `{prefix}`\n\nNew Prefix for **{ctx.guild.name}** is : `{prefix}`\nUse `{prefix}help` For More.",
                color=self.color
                             )
          await ctx.reply(embed=embed1)
      else:
          denied = discord.Embed(title="🚫 Access Denied",
              description="Your role should be above my top role.",
              color=0x000000)
          denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
          await ctx.send(embed=denied, mention_author=False)
        


  @commands.hybrid_command(name="clone", help="Clones a channel.")
  @blacklist_check()
  @ignore_check()
  @commands.has_permissions(manage_channels=True)
  async def clone(self, ctx: commands.Context, channel: discord.TextChannel):
    
    if not ctx.guild.me.guild_permissions.manage_channels:
        error = discord.Embed(
            color=self.color,
            description="I don't have permission to manage channels!"
        )
        error.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        error.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=error)


    try:
        
        await channel.clone()
        success = discord.Embed(
            color=self.color,
            description=f"{channel.name} has been successfully cloned"
        )
        success.set_author(name="Success", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        success.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=success)
    except discord.Forbidden:
        error = discord.Embed(
            color=self.color,
            description="I don't have permission to clone channels!"
        )
        error.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        await ctx.send(embed=error)
    except Exception as e:
        error = discord.Embed(
            color=self.color,
            description=f"An error occurred while trying to clone the channel: {str(e)}"
        )
        error.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        await ctx.send(embed=error)
        

  @commands.hybrid_command(name="nick",
                           aliases=['setnick'],
                           help="To change someone's nickname.",
                           usage="nick [member]")
  @blacklist_check()
  @ignore_check()
  @commands.has_permissions(manage_nicknames=True)
  @commands.bot_has_permissions(manage_nicknames=True)
  async def changenickname(self, ctx: commands.Context, member: discord.Member, *, name: str = None):
    
    
    if member == ctx.guild.owner:
        error = discord.Embed(
            color=self.color,
            description="I can't change the nickname of the server owner!"
        )
        error.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        error.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=error)

    
    if member.top_role >= ctx.guild.me.top_role:
        error = discord.Embed(
            color=self.color,
            description="I can't change the nickname of a user with a higher or equal role than mine!"
        )
        error.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        error.set_footer(text=f"Requested by {ctx.author}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=error)

    
    if ctx.author != ctx.guild.owner and ctx.author.top_role <= member.top_role:
        error = discord.Embed(
            color=self.color,
            description="You can't change the nickname of a user with a higher or equal role than you!"
        )
        error.set_author(name="Access Denied", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        error.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=error)

    try:
        await member.edit(nick=name)
        if name:
            success = discord.Embed(
                color=self.color,
                description=f"Successfully changed nickname of {member.mention} to {name}."
            )
            success.set_author(name="Nickname Updated", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
            success.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        else:
            success = discord.Embed(
                color=self.color,
                description=f"Successfully cleared nickname of {member.mention}."
            )
            success.set_author(name="Nickname Cleared", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
            success.set_footer(text=f"Requested by {ctx.author}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=success)
    except discord.Forbidden:
        error = discord.Embed(
            color=self.color,
            description="🚫 | I don't have permission to manage this user's nickname!"
        )
        await ctx.send(embed=error)
    except Exception as e:
        error = discord.Embed(
            color=self.color,
            description=f"🚫 | An error occurred while trying to change the nickname: {str(e)}"
        )
        await ctx.send(embed=error)
        

  @commands.hybrid_command(name="nuke", help="Nukes a channel", usage="nuke")
  @blacklist_check()
  @ignore_check()
  @top_check()
  @commands.cooldown(1, 7, commands.BucketType.user)
  @commands.has_permissions(manage_channels=True)
  async def _nuke(self, ctx: commands.Context):
    button = Button(label="Confirm",
                    style=discord.ButtonStyle.green,
                    emoji="✅")
    button1 = Button(label="Cancel",
                     style=discord.ButtonStyle.red,
                     emoji="❌")

    async def button_callback(interaction: discord.Interaction):
      if interaction.user == ctx.author:
        if interaction.guild.me.guild_permissions.manage_channels:
          channel = interaction.channel
          newchannel = await channel.clone()
          await newchannel.edit(position=channel.position)

          await channel.delete()
          embed = discord.Embed(
            description="Channel has been Successfully nuked by **`%s`**" % (ctx.author),
            color=self.color)
          embed.set_author(name="Channel Nuked", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
          embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
          await newchannel.send(embed=embed)
        else:
          await interaction.response.edit_message(
            content=
            "🚫 | It seems I'm missing the necessary permissions. Please grant me the `manage channel` permissions and try again.",
            embed=None,
            view=None)
      else:
        await interaction.response.send_message("Oops! It looks like that message isn't from you. You need to run the command yourself to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)

    async def button1_callback(interaction: discord.Interaction):
      if interaction.user == ctx.author:
        await interaction.response.edit_message(
          content="Cancelled, I won't proceed with nuking channel.", embed=None, view=None)
      else:
        await interaction.response.send_message("Oops! It looks like that message isn't from you. You need to run the command yourself to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)

    embed = discord.Embed(
      color=self.color, description='**Do you really want to nuke the channel?**')

    view = View()
    button.callback = button_callback
    button1.callback = button1_callback
    view.add_item(button)
    view.add_item(button1)
    embed.set_footer(text="Please click either 'Confirm' or 'Cancel' to proceed. You have 30 seconds to decide!")
    await ctx.reply(embed=embed, view=view, mention_author=False,delete_after=30)



  @commands.hybrid_command(name="slowmode",
                           help="Changes the slowmode",
                           usage="slowmode [seconds]",
                           aliases=["slow"])
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 2, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  async def _slowmode(self, ctx: commands.Context, seconds: int = 0):
    if seconds > 120:
      embed=discord.Embed(description="Slowmode can not be over 2 minutes",
                            color=self.color)
      embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
      embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      return await ctx.send(embed=embed)
    if seconds == 0:
      await ctx.channel.edit(slowmode_delay=seconds)
      await ctx.send(embed=discord.Embed(
        title="Slowmode", description="Slowmode is disabled", color=self.color))
    else:
      await ctx.channel.edit(slowmode_delay=seconds)
      embed=discord.Embed(description="Successfully Set slowmode to **`%s`**" % (seconds),
                            color=self.color)
      embed.set_author(name="Slowmode Activated", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
      embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      await ctx.send(embed=embed)
      

  @commands.hybrid_command(name="unslowmode",
                           help="Disables slowmode",
                           usage="unslowmode",
                           aliases=["unslow"])
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 2, commands.BucketType.user)
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def _unslowmode(self, ctx: commands.Context):
    await ctx.channel.edit(slowmode_delay=0)
    embed=discord.Embed(description="Successfully Disabled slowmode", color=self.color)
    embed.set_author(name="Unslowmode", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
    embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    await ctx.send(embed=embed)



  @commands.command(aliases=["deletesticker", "removesticker"], description="Delete the sticker from the server")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_emojis=True)
  @commands.bot_has_permissions(manage_emojis=True)
  async def delsticker(self, ctx: commands.Context, *, name=None):
        if ctx.message.reference is None:
            return await ctx.reply("No replied message found")
        msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if len(msg.stickers) == 0:
            return await ctx.reply("No sticker found")
        try:
            name = ""
            for i in msg.stickers:
                name = i.name
                await ctx.guild.delete_sticker(i)
            await ctx.reply(f"✅ Sucessfully deleted sticker named `{name}`")
        except:
            await ctx.reply("Failed to delete the sticker")


  @commands.command(aliases=["deleteemoji", "removeemoji"], description="Deletes the emoji from the server")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_emojis=True)
  async def delemoji(self, ctx, emoji: str = None):
    init_message = await ctx.reply("Processing to delete emojis...", mention_author=False)
    message_content = None

    
    if ctx.message.reference is not None:
        referenced_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        message_content = str(referenced_message.content)
    else:
        message_content = str(ctx.message.content)

    
    if message_content:
        
        emoji_pattern = r"<a?:\w+:(\d+)>"
        found_emojis = re.findall(emoji_pattern, message_content)
        delete_count = 0

        if len(found_emojis) != 0:
            
            if len(found_emojis) > 15:
                await init_message.delete()
                return await ctx.reply("Maximum 15 emojis can be deleted at a time.")

            
            for emoji_id in found_emojis:
                try:
                    emoji_to_delete = await ctx.guild.fetch_emoji(int(emoji_id))
                    await emoji_to_delete.delete(reason=f"Deleted by {ctx.author}")
                    delete_count += 1
                except discord.NotFound:
                    continue  
                except discord.Forbidden:
                    continue  
            await init_message.delete()
            return await ctx.reply(f"✅ | Successfully deleted {delete_count}/{len(found_emojis)} emoji(s).")

    
    await init_message.delete()
    return await ctx.reply("No valid emoji found to delete.")



  
  @commands.command(description="Changes the icon for the role.")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(administrator=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def roleicon(self, ctx: commands.Context, role: discord.Role, *, icon: Union[discord.Emoji, discord.PartialEmoji, str] = None):
    
    if role.position >= ctx.guild.me.top_role.position:
        error_embed = discord.Embed(
            description=f"{role.mention} is higher than my role. Please move my role above it.",
            color=self.color
        )
        error_embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        error_embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )
        return await ctx.send(embed=error_embed)

    
    if ctx.author != ctx.guild.owner and ctx.author.top_role.position <= role.position:
        error_embed = discord.Embed(
            description=f"{role.mention} has the same or a higher position than your top role!",
            color=self.color
        )
        error_embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        error_embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )
        return await ctx.send(embed=error_embed)

    
    if icon is None:
        attachment_found = False
        attachment_url = None
        for attachment in ctx.message.attachments:
            attachment_url = attachment.url
            attachment_found = True

        if attachment_found:
            try:
                async with aiohttp.request("GET", attachment_url) as r:
                    image_data = await r.read()
                await role.edit(display_icon=image_data)
                success_embed = discord.Embed(
                    description=f"Successfully changed the icon of {role.mention}.",
                    color=self.color
                )
                success_embed.set_author(name="Icon Updated", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
                success_embed.set_footer(
                    text=f"Requested by {ctx.author}",
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
                )
                return await ctx.send(embed=success_embed)
            except Exception as e:
                print(e)
                return await ctx.reply("Failed to change the icon of the role.")
        else:
            await role.edit(display_icon=None)
            removal_embed = discord.Embed(
                description=f"Successfully removed the icon from {role.mention}.",
                color=self.color
            )
            removal_embed.set_author(name="Icon Removed", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
            removal_embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )
            return await ctx.reply(embed=removal_embed, mention_author=False)

    
    if isinstance(icon, discord.Emoji) or isinstance(icon, discord.PartialEmoji):
        emoji_url = f"https://cdn.discordapp.com/emojis/{icon.id}.png"
        try:
            async with aiohttp.request("GET", emoji_url) as r:
                image_data = await r.read()
            await role.edit(display_icon=image_data)
            success_embed = discord.Embed(
                description=f"Successfully changed the icon for {role.mention} to {icon}.",
                color=self.color
            )
            success_embed.set_author(name="Icon Updated", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
            success_embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )
            return await ctx.reply(embed=success_embed, mention_author=False)
        except Exception as e:
            print(e)
            return await ctx.reply("Failed to change the icon of the role.")

    
    else:
        if not icon.startswith("https://"):
            return await ctx.reply("Please provide a valid link.")
        try:
            async with aiohttp.request("GET", icon) as r:
                image_data = await r.read()
            await role.edit(display_icon=image_data)
            success_embed = discord.Embed(
                description=f"✅ | Successfully changed the icon for {role.mention}.",
                color=self.color
            )
            return await ctx.reply(embed=success_embed, mention_author=False)
        except Exception as e:
            print(e)
            return await ctx.reply("An error occurred while changing the icon for the role.")
  
  
      
  @commands.hybrid_command(name="unbanall",
                           help="Unbans Everyone In The Guild!",
                           aliases=['massunban'],
                           usage="Unbanall",
                           with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 30, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(ban_members=True)
  async def unbanall(self, ctx):
    button = Button(label="Confirm",
                    style=discord.ButtonStyle.green,
                    emoji="✅")
    button1 = Button(label="Cancel",
                     style=discord.ButtonStyle.red,
                     emoji="❌")

    async def button_callback(interaction: discord.Interaction):
      a = 0
      if interaction.user == ctx.author:
        if interaction.guild.me.guild_permissions.ban_members:
          await interaction.response.edit_message(
            content="Unbanning All Banned Members...", embed=None, view=None)
          async for idk in interaction.guild.bans(limit=None):
            await interaction.guild.unban(
              user=idk.user,
              reason="Unbanall Command Executed By: {}".format(ctx.author))
            a += 1
          await interaction.channel.send(
            content=f"✅ Successfully Unbanned {a} Members")
        else:
          await interaction.response.edit_message(
            content=
            "I am missing `ban members` in this Guil.",
            embed=None,
            view=None)
      else:
        await interaction.response.send_message("Uh oh! That message doesn't belong to you.\nYou must run this command to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)

    async def button1_callback(interaction: discord.Interaction):
      if interaction.user == ctx.author:
        await interaction.response.edit_message(
          content="Cancelled, I will Not unban anyone.", embed=None, view=None)
      else:
        await interaction.response.send_message("Uh oh! That message doesn't belong to you.\nYou must run this command to interact with it.",
                                                embed=None,
                                                view=None,
                                                ephemeral=True)

    embed = discord.Embed(
      color=self.color,
      description='**Are you sure you want to unban all members in this guild?**')

    view = View()
    button.callback = button_callback
    button1.callback = button1_callback
    view.add_item(button)
    view.add_item(button1)
    await ctx.reply(embed=embed, view=view, mention_author=False)
  
  @commands.hybrid_command(name="audit",
                           help="See recents audit log action in the server .")
  @blacklist_check()
  @ignore_check()
  @commands.has_permissions(view_audit_log=True)
  @commands.bot_has_permissions(view_audit_log=True)
  @commands.cooldown(1, 5, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  async def auditlog(self, ctx, limit: int):
    if limit >= 31:
      await ctx.reply(
        "Action rejected, you are not allowed to fetch more than `30` entries.",
        mention_author=False)
      return
    idk = []
    str = ""
    async for entry in ctx.guild.audit_logs(limit=limit):
      idk.append(f'''User: `{entry.user}`
Action: `{entry.action}`
Target: `{entry.target}`
Reason: `{entry.reason}`\n\n''')
    for n in idk:
      str += n
    str = str.replace("AuditLogAction.", "")
    embed = discord.Embed(title=f"Audit Logs Of {ctx.guild.name}",
                          description=f">>> {str}",
                          color=0x000000)
    embed.set_footer(text=f"Audit Log Actions For {ctx.guild.name}")
    await ctx.reply(embed=embed, mention_author=False)
      
"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import re
from typing import *
from utils.Tools import *
from discord.ui import Button, View
from typing import Union, Optional
from typing import Union, Optional
from io import BytesIO
import requests
import aiohttp
import time
from datetime import datetime, timezone, timedelta


time_regex = re.compile(r"(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}


def convert(argument):
  args = argument.lower()
  matches = re.findall(time_regex, args)
  time = 0
  for key, value in matches:
    try:
      time += time_dict[value] * float(key)
    except KeyError:
      raise commands.BadArgument(
        f"{value} is an invalid time key! h|m|s|d are valid arguments")
    except ValueError:
      raise commands.BadArgument(f"{key} is not a number!")
  return round(time)


class Role(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.color = 0x000000


  @commands.group(name="role",invoke_without_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 5, commands.BucketType.user)
  @commands.has_permissions(manage_roles=True)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @top_check()
  @blacklist_check()
  async def role(self, ctx, member: discord.Member, *, role: discord.Role):
    if not ctx.guild.me.guild_permissions.manage_roles:
        return await ctx.send("🚫 I don't have permission to manage roles!")

    if role >= ctx.guild.me.top_role:
        error = discord.Embed(
            color=self.color,
            description="I can't manage roles for a user with a higher or equal role!"
        )

        error.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        error.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=error)

    if ctx.author != ctx.guild.owner and ctx.author.top_role <= member.top_role:
        error = discord.Embed(
            color=self.color,
            description="You can't manage roles for a user with a higher or equal role than yours!"
        )
        error.set_author(name="Access Denied", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        error.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=error)

    try:
        if role not in member.roles:
            await member.add_roles(role, reason=f"Role added by {ctx.author} (ID: {ctx.author.id})")
            success = discord.Embed(
                color=self.color,
                description=f"Successfully **added** role {role.name} to {member.mention}."
            )
            success.set_author(name="Role Added", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
            success.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        else:
            await member.remove_roles(role, reason=f"Role removed by {ctx.author} (ID: {ctx.author.id})")
            success = discord.Embed(
                color=self.color,
                description=f"Successfully **removed** role {role.name} from {member.mention}."
            )
            success.set_author(name="Role Removed", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
            success.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=success)
    except discord.Forbidden:
        error = discord.Embed(
            color=self.color,
            description="🚫 I don't have permission to manage roles for this user!"
        )
        await ctx.send(embed=error)
    except Exception as e:
        error = discord.Embed(
            color=self.color,
            description=f"🚫 An unexpected error occurred: {str(e)}"
        )
        await ctx.send(embed=error)


  @role.command(help="Give role to member for particular time")
  @commands.bot_has_permissions(manage_roles=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 7, commands.BucketType.user)
  @commands.has_permissions(manage_roles=True)
  @commands.bot_has_permissions(manage_roles=True)
  async def temp(self, ctx, role: discord.Role, time, *, user: discord.Member):
    if ctx.author != ctx.guild.owner and role.position >= ctx.author.top_role.position:
        embed = discord.Embed(
              description=f"You can't manage a role that is higher or equal to your top role!",
              color=self.color
          )
        embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=embed)
          
    else:
      if role.position >= ctx.guild.me.top_role.position:
        embed1 = discord.Embed(
          description=
          f"{role} is higher than my top role, move my role above {role}.",
          color=self.color)
        embed1.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        embed1.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=embed1)
    seconds = convert(time)
    await user.add_roles(role, reason=None)
    success = discord.Embed(
      description=
      f"Successfully added {role.mention} to {user.mention} .",
      color=self.color)
    success.set_author(name="Success", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
    success.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    await ctx.send(embed=success)
    await asyncio.sleep(seconds)
    await user.remove_roles(role)

  
  @role.command(help="Delete a role in the guild")
  @blacklist_check()
  @ignore_check()
  @top_check()
  @commands.cooldown(1, 7, commands.BucketType.user)
  @commands.has_permissions(manage_roles=True)
  @commands.bot_has_permissions(manage_roles=True)
  async def delete(self, ctx, *, role: discord.Role):
    if ctx.author != ctx.guild.owner and role.position >= ctx.author.top_role.position:
        embed = discord.Embed(
            description=f"You cannot delete a role that is higher or equal to your top role!",
            color=self.color
        )
        embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=embed)

    if role.position >= ctx.guild.me.top_role.position:
        embed = discord.Embed(
            description=f"I cannot delete {role} because it is higher than my top role. Please move my role above {role}.",
            color=self.color
        )
        embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=embed)

    if role is None:
        embed = discord.Embed(
            description=f"No role named {role} found in this server.",
            color=self.color
        )
        embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=embed)

    await role.delete()
    
    embed = discord.Embed(
        description=f"Successfully deleted {role}.",
        color=self.color
    )
    embed.set_author(name="Success", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
    embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    await ctx.send(embed=embed)
      
  @role.command(help="Create a role in the guild")
  @blacklist_check()
  @ignore_check()
  @top_check()
  @commands.cooldown(1, 7, commands.BucketType.user)
  @commands.has_permissions(administrator=True)
  @commands.bot_has_permissions(manage_roles=True)
  async def create(self, ctx, *, name):
    embed = discord.Embed(
        description=f"Successfully created a role named {name}.",
        color=self.color
    )
    embed.set_author(name="Success", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
    embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    await ctx.guild.create_role(name=name, color=discord.Color.default())
    await ctx.send(embed=embed)


  @role.command(help="Renames a role in the server.")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 10, commands.BucketType.user)
  @commands.has_permissions(administrator=True)
  @commands.bot_has_permissions(manage_roles=True)
  async def rename(self, ctx, role: discord.Role, *, newname):
    
    if role.position >= ctx.author.top_role.position:
        embed = discord.Embed(
            description=f"You can't manage the role {role.mention} because it is higher or equal to your top role.",
            color=self.color
        )
        embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=embed)

    
    if role.position >= ctx.guild.me.top_role.position:
        embed = discord.Embed(
            description=f"I can't manage the role {role.mention} because it is higher than my top role.",
            color=self.color
        )
        embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
        embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        return await ctx.send(embed=embed)

    await role.edit(name=newname)
    embed = discord.Embed(
        description=f"Role {role.name} has been renamed to {newname}.",
        color=self.color
    )
    embed.set_author(name="Success", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
    embed.set_footer(text=f"Requested by {ctx.author}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    await ctx.send(embed=embed)                  

  @role.command(name="humans", help="Gives role to all humans in the guild")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 15, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  async def role_humans(self, ctx, *, role: discord.Role):
    if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
        button = Button(label="Confirm",
                        style=discord.ButtonStyle.green,
                        emoji="✅")
        button1 = Button(label="Cancel",
                         style=discord.ButtonStyle.red,
                         emoji="❌")

        async def button_callback(interaction: discord.Interaction):
            count = 0
            if interaction.user == ctx.author:
                if interaction.guild.me.guild_permissions.manage_roles:
                    embed1 = discord.Embed(
                        color=self.color,
                        description=f"Assigning {role.mention} to all humans...")
                    await interaction.response.edit_message(embed=embed1, view=None)
                    for member in interaction.guild.members:
                        if not member.bot and role not in member.roles:
                            try:
                                await member.add_roles(role, reason=f"Role Humans Command Executed By: {ctx.author}")
                                count += 1
                            except Exception as e:
                                print(e)

                    await interaction.channel.send(
                        content=f"✅ | Successfully assigned {role.mention} to {count} human(s).")
                else:
                    await interaction.response.edit_message(
                        content="🔔 I am missing the required permissions. Please grant the necessary permissions and try again.",
                        embed=None,
                        view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        async def button1_callback(interaction: discord.Interaction):
            if interaction.user == ctx.author:
                embed2 = discord.Embed(
                    color=self.color,
                    description=f"Action cancelled. No humans will be assigned the role {role.mention}.")
                await interaction.response.edit_message(embed=embed2, view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        members_without_role = [member for member in ctx.guild.members if not member.bot and role not in member.roles]
        if len(members_without_role) == 0:
            return await ctx.reply(embed=discord.Embed(description=f"🔔 | All humans already have the {role.mention} role.", color=self.color))
        else:
            embed = discord.Embed(
                color=self.color,
                description=f"Are you sure you want to assign {role.mention} to {len(members_without_role)} members?")
            view = View()
            button.callback = button_callback
            button1.callback = button1_callback
            view.add_item(button)
            view.add_item(button1)
            await ctx.reply(embed=embed, view=view, mention_author=False)

    else:
        denied = discord.Embed(title="🚫 Access Denied",
            description="Your role should be above my top role.",
            color=0x000000)
        denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=denied, mention_author=False)



  @role.command(name="bots", help="Gives role to all the bots in the guild")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 10, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  async def role_bots(self, ctx, *, role: discord.Role):
    if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
        button = Button(label="Confirm",
                        style=discord.ButtonStyle.green,
                        emoji="✅")
        button1 = Button(label="Cancel",
                         style=discord.ButtonStyle.red,
                         emoji="❌")

        async def button_callback(interaction: discord.Interaction):
            count = 0
            if interaction.user == ctx.author:
                if interaction.guild.me.guild_permissions.manage_roles:
                    embed1 = discord.Embed(
                        color=self.color,
                        description=f"Adding {role.mention} to all bots...")
                    await interaction.response.edit_message(embed=embed1, view=None)
                    for member in interaction.guild.members:
                        if member.bot and role not in member.roles:
                            try:
                                await member.add_roles(role, reason=f"Role Bots Command Executed By: {ctx.author}")
                                count += 1
                            except Exception as e:
                                print(e)

                    await interaction.channel.send(
                        content=f"✅ | Successfully added {role.mention} to {count} bot(s).")
                else:
                    await interaction.response.edit_message(
                        content="I am missing the required permission. Please grant the necessary permissions and try again.",
                        embed=None,
                        view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        async def button1_callback(interaction: discord.Interaction):
            if interaction.user == ctx.author:
                embed2 = discord.Embed(
                    color=self.color,
                    description=f"Action cancelled. No bots will be assigned the role {role.mention}.")
                await interaction.response.edit_message(embed=embed2, view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        bots_without_role = [member for member in ctx.guild.members if member.bot and role not in member.roles]
        if len(bots_without_role) == 0:
            return await ctx.reply(embed=discord.Embed(description=f"🔔 | All bots already have the {role.mention} role.", color=self.color))
        else:
            embed = discord.Embed(
                color=self.color,
                description=f"**Are you sure you want to give {role.mention} to {len(bots_without_role)} bots?**")
            view = View()
            button.callback = button_callback
            button1.callback = button1_callback
            view.add_item(button)
            view.add_item(button1)
            await ctx.reply(embed=embed, view=view, mention_author=False)

    else:
        denied = discord.Embed(title="🚫 Access Denied",
            description="Your role should be above my top role.",
            color=0x000000)
        denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=denied, mention_author=False)



  @role.command(name="unverified", help="Gives role to all the unverified members in the guild")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 10, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  async def role_unverified(self, ctx, *, role: discord.Role):
    if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
        button = Button(label="Confirm",
                        style=discord.ButtonStyle.green,
                        emoji="✅")
        button1 = Button(label="Cancel",
                         style=discord.ButtonStyle.red,
                         emoji="❌")

        async def button_callback(interaction: discord.Interaction):
            count = 0
            if interaction.user == ctx.author:
                if interaction.guild.me.guild_permissions.manage_roles:
                    embed1 = discord.Embed(
                        color=self.color,
                        description=f"Adding {role.mention} to all unverified members.")
                    await interaction.response.edit_message(embed=embed1, view=None)
                    for member in interaction.guild.members:
                        if member.avatar is None and role not in member.roles:
                            try:
                                await member.add_roles(role, reason=f"Role Unverified Command Executed By: {ctx.author}")
                                count += 1
                            except Exception as e:
                                print(e)

                    await interaction.channel.send(
                        content=f"✅ | Successfully added {role.mention} to {count} unverified member(s).")
                else:
                    await interaction.response.edit_message(
                        content="I am missing the required permission. Please grant the necessary permissions and try again.",
                        embed=None,
                        view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        async def button1_callback(interaction: discord.Interaction):
            if interaction.user == ctx.author:
                embed2 = discord.Embed(
                    color=self.color,
                    description=f"Action cancelled. No unverified members will be assigned the role {role.mention}.")
                await interaction.response.edit_message(embed=embed2, view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        embed = discord.Embed(
            color=self.color,
            description=f'**Are you sure you want to give {role.mention} to all unverified members in this guild?**')
        view = View()
        button.callback = button_callback
        button1.callback = button1_callback
        view.add_item(button)
        view.add_item(button1)
        await ctx.reply(embed=embed, view=view, mention_author=False)

    else:
        denied = discord.Embed(title="🚫 Access Denied",
            description="Your role should be above my top role.",
            color=0x000000)
        denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=denied, mention_author=False)


  @role.command(name="all", help="Gives role to all the members in the guild")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 15, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  async def role_all(self, ctx, *, role: discord.Role):
    if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
        button = Button(label="Confirm",
                        style=discord.ButtonStyle.green,
                        emoji="✅")
        button1 = Button(label="Cancel",
                         style=discord.ButtonStyle.red,
                         emoji="❌")

        async def button_callback(interaction: discord.Interaction):
            count = 0
            if interaction.user == ctx.author:
                if interaction.guild.me.guild_permissions.manage_roles:
                    embed1 = discord.Embed(
                        color=self.color,
                        description=f"Adding {role.mention} to all members.")
                    await interaction.response.edit_message(embed=embed1, view=None)
                    for member in interaction.guild.members:
                        try:
                            await member.add_roles(role, reason=f"Role All Command Executed By: {ctx.author}")
                            count += 1
                        except Exception as e:
                            print(e)

                    await interaction.channel.send(
                        content=f"✅ | Successfully added {role.mention} to {count} member(s).")
                else:
                    await interaction.response.edit_message(
                        content="I am missing the required permission. Please grant the necessary permissions and try again.",
                        embed=None,
                        view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        async def button1_callback(interaction: discord.Interaction):
            if interaction.user == ctx.author:
                embed2 = discord.Embed(
                    color=self.color,
                    description=f"Action cancelled. No members will be assigned the role {role.mention}.")
                await interaction.response.edit_message(embed=embed2, view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        members_without_role = [member for member in ctx.guild.members if role not in member.roles]
        if len(members_without_role) == 0:
            return await ctx.reply(embed=discord.Embed(description=f"🔔 | {role.mention} is already given to all the members of the server.", color=self.color))
        else:
            embed = discord.Embed(
                color=self.color,
                description=f'**Are you sure you want to give {role.mention} to {len(members_without_role)} members?**')
            view = View()
            button.callback = button_callback
            button1.callback = button1_callback
            view.add_item(button)
            view.add_item(button1)
            await ctx.reply(embed=embed, view=view, mention_author=False)
    else:
        denied = discord.Embed(title="🚫 Access Denied",
            description="Your role should be above my top role.",
            color=0x000000)
        denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=denied, mention_author=False)



  @commands.group(name="removerole",invoke_without_command=True,
                 aliases=['rrole'],
                   help="remove a role from all members .")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 5, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @blacklist_check()
  @commands.has_permissions(administrator=True)
  async def rrole(self,ctx):
    if ctx.subcommand_passed is None:
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)


  @rrole.command(name="humans", help="Removes a role from all the humans in the server.")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 10, commands.BucketType.user)
  @commands.has_permissions(administrator=True)
  async def rrole_humans(self, ctx, *, role: discord.Role):
    if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
        button = Button(label="Confirm",
                        style=discord.ButtonStyle.green,
                        emoji="✅")
        button1 = Button(label="Cancel",
                         style=discord.ButtonStyle.red,
                         emoji="❌")

        async def button_callback(interaction: discord.Interaction):
            count = 0
            if interaction.user == ctx.author:
                if interaction.guild.me.guild_permissions.manage_roles:
                    embed1 = discord.Embed(
                        color=self.color,
                        description=f"Removing {role.mention} from all humans.")
                    await interaction.response.edit_message(embed=embed1, view=None)
                    for member in interaction.guild.members:
                        if not member.bot and role in member.roles:
                            try:
                                await member.remove_roles(role, reason=f"Remove Role Humans Command Executed By: {ctx.author}")
                                count += 1
                            except Exception as e:
                                print(e)

                    await interaction.channel.send(
                        content=f"✅ | Successfully removed {role.mention} from {count} human(s).")
                else:
                    await interaction.response.edit_message(
                        content="I am missing the required permission. Please grant the necessary permissions and try again.",
                        embed=None,
                        view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        async def button1_callback(interaction: discord.Interaction):
            if interaction.user == ctx.author:
                embed2 = discord.Embed(
                    color=self.color,
                    description=f"Action cancelled. {role.mention} will not be removed from any humans.")
                await interaction.response.edit_message(embed=embed2, view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        humans_with_role = [member for member in ctx.guild.members if not member.bot and role in member.roles]
        if len(humans_with_role) == 0:
            return await ctx.reply(embed=discord.Embed(description=f"| Already no humans have {role.mention}.", color=self.color))
        else:
            embed = discord.Embed(
                color=self.color,
                description=f'**Are you sure you want to remove {role.mention} from {len(humans_with_role)} humans in this guild?**')
            view = View()
            button.callback = button_callback
            button1.callback = button1_callback
            view.add_item(button)
            view.add_item(button1)
            await ctx.reply(embed=embed, view=view, mention_author=False)
    else:
        denied = discord.Embed(title="🚫 Access Denied",
            description="Your role should be above my top role.",
            color=0x000000)
        denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=denied, mention_author=False)

        await ctx.send(embed=embed, mention_author=False)
        


  @rrole.command(name="bots", help="Removes a role from all the bots in the server.")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 10, commands.BucketType.user)
  @commands.has_permissions(administrator=True)
  async def rrole_bots(self, ctx, *, role: discord.Role):
    if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
        button = Button(label="Confirm",
                        style=discord.ButtonStyle.green,
                        emoji="✅")
        button1 = Button(label="Cancel",
                         style=discord.ButtonStyle.red,
                         emoji="❌")

        async def button_callback(interaction: discord.Interaction):
            count = 0
            if interaction.user == ctx.author:
                if interaction.guild.me.guild_permissions.manage_roles:
                    embed1 = discord.Embed(
                        color=self.color,
                        description=f"Removing {role.mention} from all bots...")
                    await interaction.response.edit_message(embed=embed1, view=None)
                    for member in interaction.guild.members:
                        if member.bot and role in member.roles:
                            try:
                                await member.remove_roles(role, reason=f"Remove Role Bots Command Executed By: {ctx.author}")
                                count += 1
                            except Exception as e:
                                print(e)

                    await interaction.channel.send(
                        content=f"✅ | Successfully removed {role.mention} from {count} bot(s).")
                else:
                    await interaction.response.edit_message(
                        content="I am missing the required permission. Please grant the necessary permissions and try again.",
                        embed=None,
                        view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        async def button1_callback(interaction: discord.Interaction):
            if interaction.user == ctx.author:
                embed2 = discord.Embed(
                    color=self.color,
                    description=f"Action cancelled. {role.mention} will not be removed from any bots.")
                await interaction.response.edit_message(embed=embed2, view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        bots_with_role = [member for member in ctx.guild.members if member.bot and role in member.roles]
        if len(bots_with_role) == 0:
            return await ctx.reply(embed=discord.Embed(description=f"| Already no bots have {role.mention}.", color=self.color))
        else:
            embed = discord.Embed(
                color=self.color,
                description=f'**Are you sure you want to remove {role.mention} from {len(bots_with_role)} bots in this guild?**')
            view = View()
            button.callback = button_callback
            button1.callback = button1_callback
            view.add_item(button)
            view.add_item(button1)
            await ctx.reply(embed=embed, view=view, mention_author=False)
    else:
        denied = discord.Embed(title="🚫 Access Denied",
            description="Your role should be above my top role.",
            color=0x000000)
        denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=denied, mention_author=False)

    



  @rrole.command(name="all", help="Removes a role from all members in the server.")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 10, commands.BucketType.user)
  @commands.has_permissions(administrator=True)
  async def rrole_all(self, ctx, *, role: discord.Role):
    if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
        button = Button(label="Confirm",
                        style=discord.ButtonStyle.green,
                        emoji="✅")
        button1 = Button(label="Cancel",
                         style=discord.ButtonStyle.red,
                         emoji="❌")

        async def button_callback(interaction: discord.Interaction):
            removed_count = 0
            if interaction.user == ctx.author:
                if interaction.guild.me.guild_permissions.manage_roles:
                    embed1 = discord.Embed(
                        color=self.color,
                        description=f"Removing {role.mention} from all members.")
                    await interaction.response.edit_message(embed=embed1, view=None)

                    for member in interaction.guild.members:
                        if role in member.roles:
                            try:
                                await member.remove_roles(role, reason=f"Remove Role All Command Executed By: {ctx.author}")
                                removed_count += 1
                            except Exception as e:
                                print(e)

                    await interaction.channel.send(
                        content=f"✅ | Successfully removed {role.mention} from {removed_count} member(s).")
                else:
                    await interaction.response.edit_message(
                        content="I am missing the required permission. Please grant the necessary permissions and try again.",
                        embed=None,
                        view=None)
            else:
                await interaction.response.send_message("This action is not for you!",
                                                        embed=None,
                                                        view=None,
                                                        ephemeral=True)

        async def button1_callback(interaction: discord.Interaction):
            if interaction.user == ctx.author:
                embed2 = discord.Embed(
                    color=self.color,
                    description=f"Action cancelled. {role.mention} will not be removed from anyone.")
                await interaction.response.edit_message(embed=embed2, view=None)
            else:
                await interaction.response.send_message("This action is not for you!",
                                                        embed=None,
                                                        view=None,
                                                        ephemeral=True)

        members_with_role = [member for member in ctx.guild.members if role in member.roles]
        if len(members_with_role) == 0:
            return await ctx.reply(embed=discord.Embed(description=f"| No members currently have {role.mention}.", color=self.color))
        else:
            embed = discord.Embed(
                color=self.color,
                description=f'**Are you sure you want to remove {role.mention} from {len(members_with_role)} members in this guild?**')
            view = View()
            button.callback = button_callback
            button1.callback = button1_callback
            view.add_item(button)
            view.add_item(button1)
            await ctx.reply(embed=embed, view=view, mention_author=False)
    else:
        denied = discord.Embed(title="🚫 Access Denied",
            description="Your role should be above my top role.",
            color=0x000000)
        denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=denied, mention_author=False)

    
    

  @rrole.command(name="unverified", help="Removes a role from all the unverified members in the server.")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 10, commands.BucketType.user)
  @commands.has_permissions(administrator=True)
  async def rrole_unverified(self, ctx, *, role: discord.Role):
    if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
        button = Button(label="Yes",
                        style=discord.ButtonStyle.green,
                        emoji="✅")
        button1 = Button(label="No",
                         style=discord.ButtonStyle.red,
                         emoji="❌")

        async def button_callback(interaction: discord.Interaction):
            count = 0
            if interaction.user == ctx.author:
                if interaction.guild.me.guild_permissions.manage_roles:
                    embed1 = discord.Embed(
                        color=self.color,
                        description=f"Removing {role.mention} from all unverified members.")
                    await interaction.response.edit_message(embed=embed1, view=None)

                    for member in interaction.guild.members:
                        if member.avatar is None and role in member.roles:
                            try:
                                await member.remove_roles(role, reason=f"Remove Role Unverified Command Executed By: {ctx.author}")
                                count += 1
                            except Exception as e:
                                print(e)

                    await interaction.channel.send(
                        content=f"✅ | Successfully removed {role.mention} from {count} unverified member(s).")
                else:
                    await interaction.response.edit_message(
                        content="I am missing the required permission. Please grant the necessary permissions and try again.",
                        embed=None,
                        view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        async def button1_callback(interaction: discord.Interaction):
            if interaction.user == ctx.author:
                embed2 = discord.Embed(
                    color=self.color,
                    description=f"Action cancelled. {role.mention} will not be removed from any unverified members.")
                await interaction.response.edit_message(embed=embed2, view=None)
            else:
                await interaction.response.send_message(
                    "This action is not for you!",
                    embed=None,
                    view=None,
                    ephemeral=True)

        unverified_members = [member for member in ctx.guild.members if member.avatar is None and role in member.roles]
        if len(unverified_members) == 0:
            return await ctx.reply(embed=discord.Embed(description=f"| Already no unverified members have {role.mention}.", color=self.color))
        else:
            embed = discord.Embed(
                color=self.color,
                description=f'**Are you sure you want to remove {role.mention} from {len(unverified_members)} unverified members in this guild?**')
            view = View()
            button.callback = button_callback
            button1.callback = button1_callback
            view.add_item(button)
            view.add_item(button1)
            await ctx.reply(embed=embed, view=view, mention_author=False)
    else:
        denied = discord.Embed(title="🚫 Access Denied",
            description="Your role should be above my top role.",
            color=0x000000)
        denied.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=denied, mention_author=False)

  

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from datetime import datetime
from utils.Tools import *

class SnipeView(discord.ui.View):
    def __init__(self, bot, snipes, user_id):
        super().__init__(timeout=120)
        self.bot = bot
        self.snipes = snipes
        self.index = 0
        self.user_id = user_id
        self.update_buttons()

    def update_buttons(self):
        self.first_button.disabled = self.index == 0 or len(self.snipes) == 1
        self.prev_button.disabled = self.index == 0 or len(self.snipes) == 1
        self.next_button.disabled = self.index == len(self.snipes) - 1 or len(self.snipes) == 1
        self.last_button.disabled = self.index == len(self.snipes) - 1 or len(self.snipes) == 1

    async def send_snipe_embed(self, interaction: discord.Interaction):
        snipe = self.snipes[self.index]
        embed = discord.Embed(color=0x000000)
        embed.set_author(name=f"Deleted Message {self.index + 1}/{len(self.snipes)}", icon_url=snipe['author_avatar'])
        uid = snipe['author_id']
        display_name = snipe['author_name']
        embed.description = (
            f"• **Author:** **[{display_name}](https://discord.com/users/{uid})**\n"
            f"• **Author ID:** `{snipe['author_id']}`\n"
            f"✅ **Author Mention:** <@{snipe['author_id']}>\n"
            f"• **Deleted:** <t:{snipe['deleted_at']}:R>\n"
        )

        if snipe['content']:
            embed.add_field(name="• **Content:**", value=snipe['content'])
        if snipe['attachments']:
            attachment_links = "\n".join([f"[{attachment['name']}]({attachment['url']})" for attachment in snipe['attachments']])
            embed.add_field(name="• **Attachments:**", value=attachment_links)

        embed.set_footer(text=f"Total Deleted Messages: {len(self.snipes)} | Requested by {interaction.user}", icon_url=interaction.user.avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(emoji="•", style=discord.ButtonStyle.secondary, custom_id="first")
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = 0
        self.update_buttons()
        await self.send_snipe_embed(interaction)

    @discord.ui.button(emoji="•", style=discord.ButtonStyle.secondary, custom_id="previous")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
        self.update_buttons()
        await self.send_snipe_embed(interaction)

    @discord.ui.button(emoji="•", style=discord.ButtonStyle.danger, custom_id="delete")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

    @discord.ui.button(emoji="•", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.snipes) - 1:
            self.index += 1
        self.update_buttons()
        await self.send_snipe_embed(interaction)

    @discord.ui.button(emoji="•", style=discord.ButtonStyle.secondary, custom_id="last")
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = len(self.snipes) - 1
        self.update_buttons()
        await self.send_snipe_embed(interaction)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)


class Snipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.snipes = {}

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.author.bot:
            return
        if message.channel.id not in self.snipes:
            self.snipes[message.channel.id] = []
        if len(self.snipes[message.channel.id]) >= 10:
            self.snipes[message.channel.id].pop(0)

        attachments = []
        if message.attachments:
            attachments = [{'name': attachment.filename, 'url': attachment.url} for attachment in message.attachments]

        self.snipes[message.channel.id].insert(0, {
            'author_name': message.author.name,
            'author_avatar': message.author.avatar.url,
            'author_id': message.author.id,
            'content': message.content or None,
            'deleted_at': int(datetime.utcnow().timestamp()),
            'attachments': attachments
        })

    @commands.hybrid_command(name='snipe', help="Shows the recently deleted messages in the channel.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(manage_messages=True)
    async def snipe(self, ctx):
        channel_snipes = self.snipes.get(ctx.channel.id, [])
        if not channel_snipes:
            await ctx.send("No recently deleted messages found in this channel.")
            return

        first_snipe = channel_snipes[0]
        embed = discord.Embed(color=0x000000)
        embed.set_author(name="Last Deleted Message", icon_url=first_snipe['author_avatar'])
        uid = first_snipe['author_id']
        display_name = first_snipe['author_name']
        embed.description = (
            f"• **Author:** **[{display_name}](https://discord.com/users/{uid})**\n"
            f"• **Author ID:** `{first_snipe['author_id']}`\n"
            f"✅ **Author Mention:** <@{first_snipe['author_id']}>\n"
            f"• **Deleted:** <t:{first_snipe['deleted_at']}:R>\n"
        )

        if first_snipe['content']:
            embed.add_field(name="• **Content:**", value=first_snipe['content'])
        if first_snipe['attachments']:
            attachment_links = "\n".join([f"[{attachment['name']}]({attachment['url']})" for attachment in first_snipe['attachments']])
            embed.add_field(name="• **Attachments:**", value=attachment_links)

        embed.set_footer(text=f"Total Deleted Messages: {len(channel_snipes)} | Requested by {ctx.author}", icon_url=ctx.author.avatar.url)

        view = SnipeView(self.bot, channel_snipes, ctx.author.id)

        if len(channel_snipes) > 1:
            message = await ctx.send(embed=embed, view=view)
            view.message = message
        else:
            view.first_button.disabled = True
            view.prev_button.disabled = True
            view.next_button.disabled = True
            view.last_button.disabled = True
            message = await ctx.send(embed=embed, view=view)
            view.message = message

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import ui
from datetime import timedelta
import re
from utils.Tools import *

class TimeoutView(ui.View):
    def __init__(self, user, author):
        super().__init__(timeout=120)
        self.user = user
        self.author = author
        self.message = None  
        self.color = discord.Color.from_rgb(0, 0, 0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @ui.button(label="Unmute", style=discord.ButtonStyle.success)
    async def unmute(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReasonModal(user=self.user, author=self.author, view=self)
        await interaction.response.send_modal(modal)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

class AlreadyTimedoutView(ui.View):
    def __init__(self, user, author):
        super().__init__(timeout=60)
        self.user = user
        self.author = author
        self.message = None  

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @ui.button(label="Unmute", style=discord.ButtonStyle.success)
    async def unmute(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReasonModal(user=self.user, author=self.author, view=self)
        await interaction.response.send_modal(modal)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

class ReasonModal(ui.Modal):
    def __init__(self, user, author, view):
        super().__init__(title="Unmute Reason")
        self.user = user
        self.author = author
        self.view = view
        self.reason_input = ui.TextInput(label="Reason for Unmuting", placeholder="Provide a reason to unmute or leave it blank.", required = False, max_length=2000, style=discord.TextStyle.paragraph)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value or "No reason provided"
        try:
            await self.user.send(f"You have been Unmuted in **{self.author.guild.name}** by **{self.author}**. Reason: {reason or 'No reason provided'}")
            dm_status = "Yes"
        except discord.Forbidden:
            dm_status = "No"
        except discord.HTTPException:
            dm_status = "No"

        embed = discord.Embed(description=f"**• Target User:** [{self.user}](https://discord.com/users/{self.user.id})\n✅ **User Mention:** {self.user.mention}\n**• DM Sent:** {dm_status}\n**✅ Reason:** {reason}", color=0x000000)
        embed.set_author(name=f"Successfully Unmuted {self.user.name}", icon_url=self.user.avatar.url if self.user.avatar else self.user.default_avatar.url)
        embed.add_field(name="🛡️ Moderator:", value=interaction.user.mention, inline=False)
        embed.set_footer(text=f"Requested by {self.author}", icon_url=self.author.avatar.url if self.author.avatar else self.author.default_avatar.url)
        embed.timestamp = discord.utils.utcnow()

        await self.user.edit(timed_out_until=None, reason=f"Unmute requested by {self.author}")
        await interaction.response.edit_message(embed=embed, view=self.view)
        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(view=self.view)

class Mute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)

    def get_user_avatar(self, user):
        return user.avatar.url if user.avatar else user.default_avatar.url

    def parse_time(self, time_str):
        time_pattern = r"(\d+)([mhd])"
        match = re.match(time_pattern, time_str)
        if match:
            time_value = int(match.group(1))
            time_unit = match.group(2)
            if time_unit == 'm' and 0 < time_value <= 60:
                return timedelta(minutes=time_value), f"{time_value} minutes"
            elif time_unit == 'h' and 0 < time_value <= 24:
                return timedelta(hours=time_value), f"{time_value} hours"
            elif time_unit == 'd' and 0 < time_value <= 28:
                return timedelta(days=time_value), f"{time_value} days"
        return None, None

    @commands.hybrid_command(
        name="mute",
        help="Mutes a user with optional time and reason",
        usage="mute <member> [time] [reason]",
        aliases=["timeout", "stfu"])
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, user: discord.Member, time: str = None, *, reason=None):

        if user.is_timed_out():
            embed = discord.Embed(description="**Requested User is already muted in this server.**", color=self.color)
            embed.add_field(name="__Unmute__:", value="Click on the `Unmute` button to remove the timeout from the user.")
            embed.set_author(name=f"{user.name} is Already Timed Out!", icon_url=self.get_user_avatar(user))
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            view = AlreadyTimedoutView(user=user, author=ctx.author)
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            return

        if user == ctx.guild.owner:
            error = discord.Embed(color=self.color, description="You can't timeout the Server Owner!")
            error.set_author(name="Error Timing Out User", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            error.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            return await ctx.send(embed=error)

        if ctx.author != ctx.guild.owner and user.top_role >= ctx.author.top_role:
            error = discord.Embed(color=self.color, description="You can't timeout users having higher or equal role than yours!")
            error.set_author(name="Error Timing Out User", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            error.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            return await ctx.send(embed=error)

        if user.top_role >= ctx.guild.me.top_role:
            error = discord.Embed(color=self.color, description="I can't timeout users having higher or equal role than mine.")
            error.set_author(name="Error Timing Out User", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            error.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            return await ctx.send(embed=error)

        time_delta, duration_text = self.parse_time(time) if time else (timedelta(hours=24), "24 hours")

        if not time_delta:
            error = discord.Embed(color=self.color, description="Invalid time format! Use `<number><m/h/d>` where `m` is minutes (max 60), `h` is hours (max 24), and `d` is days (max 28).")
            error.set_author(name="Error Timing Out User", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            error.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            return await ctx.send(embed=error)

        try:
            await user.send(f"⚠️ You have been muted in **{ctx.guild.name}** by **{ctx.author}** for {duration_text}. Reason: {reason or 'None'}")
            dm_status = "Yes"
        except discord.Forbidden:
            dm_status = "No"
        except discord.HTTPException:
            dm_status = "No"

        await user.edit(timed_out_until=discord.utils.utcnow() + time_delta, reason=f"Muted by {ctx.author} for {duration_text}. Reason: {reason or 'None'}")


        embed = discord.Embed(description=f"**• Target User:** [{user}](https://discord.com/users/{user.id})\n"
                                          f"✅ **User Mention:** {user.mention}\n"
                                          f"• **DM Sent:** {dm_status}\n"
                                          f"**✅ Reason:** {reason or 'None'}\n"
                                          f"**• Duration:** {duration_text}",
                              color=self.color)
        embed.set_author(name=f"Successfully Muted {user.name}", icon_url=self.get_user_avatar(user))
        embed.add_field(name="🛡️ Moderator:", value=ctx.author.mention, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
        embed.timestamp = discord.utils.utcnow()

        
        view = TimeoutView(user=user, author=ctx.author)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @mute.error
    async def mute_error(self, ctx, error):
        
        if isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(title="🚫 Access Denied", description="I don't have permission to mute members.", color=self.color)
            await ctx.send(embed=embed)
        elif isinstance(error, discord.Forbidden):
            embed = discord.Embed(title="🚫 Missing Permissions", description="I can't mute this user as they might have higher privileges (e.g., Admin).", color=self.color)
            await ctx.send(embed=embed)
            
        else:
            embed = discord.Embed(title="🚫 Unexpected Error", description=str(error), color=self.color)
            await ctx.send(embed=embed)

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
import aiosqlite
import asyncio

class TopCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "db/topcheck.db"
        self.bot.loop.create_task(self.setup())

    async def setup(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS topcheck (
                    guild_id INTEGER PRIMARY KEY,
                    enabled INTEGER
                )
            """)
            await db.commit()

    async def is_topcheck_enabled(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT enabled FROM topcheck WHERE guild_id = ?", (guild_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0] == 1
                return False

    async def enable_topcheck(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO topcheck (guild_id, enabled) VALUES (?, 1)", (guild_id,))
            await db.commit()

    async def disable_topcheck(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE topcheck SET enabled = 0 WHERE guild_id = ?", (guild_id,))
            await db.commit()

    @commands.group(
        name="topcheck",
        help="Manage topcheck settings for the server.",
        invoke_without_command=True)
    @commands.guild_only()
    async def topcheck(self, ctx):
        embed = discord.Embed(title="Top Check System",
                              description=(
        "This system ensures that the bot’s role is positioned higher than the user’s top role before executing specific commands.\n\n"
        "When topcheck is enabled, only users with roles above the bot's (Olympus) role can perform certain moderation actions. "
        "If topcheck is disabled, any user with the required permissions for a command can execute it.\n\n"
        "**Moderation actions affected by topcheck:**\n"
        "- BAN\n"
        "- KICK\n"
        "- ROLE DELETE\n"
        "- ROLE CREATE\n"
        "- MEMBER UPDATE\n\n"
        "__**Subcommands:**__\n"
        f"• `{ctx.prefix}topcheck enable` - Enables top check for the server.\n"
        f"• `{ctx.prefix}topcheck disable` - Disables top check for the server."
    ),
                              color=0x000000)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @topcheck.command(
        name="enable",
        help="Enable topcheck for the guild")
    @commands.guild_only()
    async def topcheck_enable(self, ctx):
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("🚫 Only the **Server Owner** can enable topcheck.")
        if await self.is_topcheck_enabled(ctx.guild.id):
            return await ctx.reply("🚫 Topcheck is already enabled for this server.")
        await self.enable_topcheck(ctx.guild.id)
        await ctx.reply("✅ Topcheck has been Successfully enabled for this server.")

    @topcheck.command(
        name="disable",
        help="Disable topcheck for the guild")
    @commands.guild_only()
    async def topcheck_disable(self, ctx):
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("Only the **Server Owner** can disable topcheck.")
        if not await self.is_topcheck_enabled(ctx.guild.id):
            return await ctx.reply("🚫 Topcheck is not enabled for this server.")
        await self.disable_topcheck(ctx.guild.id)
        await ctx.reply("✅ Topcheck has been Successfully disabled for this server.")

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import ui
from utils.Tools import *

class BanView(ui.View):
    def __init__(self, user, author):
        super().__init__(timeout=120)
        self.user = user
        self.author = author
        self.message = None  
        self.color = discord.Color.from_rgb(0, 0, 0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @ui.button(label="Ban", style=discord.ButtonStyle.danger)
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReasonModal(user=self.user, author=self.author, view=self)
        await interaction.response.send_modal(modal)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

class AlreadyUnbannedView(ui.View):
    def __init__(self, user, author):
        super().__init__(timeout=60)
        self.user = user
        self.author = author
        self.message = None  

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @ui.button(label="Ban", style=discord.ButtonStyle.danger)
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReasonModal(user=self.user, author=self.author, view=self)
        await interaction.response.send_modal(modal)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

class ReasonModal(ui.Modal):
    def __init__(self, user, author, view):
        super().__init__(title="Ban Reason")
        self.user = user
        self.author = author
        self.view = view
        self.reason_input = ui.TextInput(label="Reason for Banning", placeholder="Provide a reason for banning or leave it blank for no reason.", required = False, max_length=2000, style=discord.TextStyle.paragraph)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value or "No reason provided"
        try:
            await self.user.send(f"⚠️ You have been Banned from **{self.author.guild.name}** by **{self.author}**. Reason: {reason or 'No reason provided'}")
            dm_status = "Yes"
        except discord.Forbidden:
            dm_status = "No"
        except discord.HTTPException:
            dm_status = "No"

        embed = discord.Embed(description=f"**• Target User:** [{self.user}](https://discord.com/users/{self.user.id})\n✅ **User Mention:** {self.user.mention}\n**• DM Sent:** {dm_status}\n**✅ Reason:** {reason}", color=0x000000)
        embed.set_author(name=f"Successfully Banned {self.user.name}", icon_url=self.user.avatar.url if self.user.avatar else self.user.default_avatar.url)
        embed.add_field(name="🛡️ Moderator:", value=interaction.user.mention, inline=False)
        embed.set_footer(text=f"Requested by {self.author}", icon_url=self.author.avatar.url if self.author.avatar else self.author.default_avatar.url)
        embed.timestamp = discord.utils.utcnow()

        try:
            await interaction.guild.ban(self.user, reason=f"Ban requested by {self.author}")
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

        try:
            await interaction.response.edit_message(embed=embed, view=self.view)
            for item in self.view.children:
                item.disabled = True
            await interaction.message.edit(view=self.view)
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass
            

class Unban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)

    def get_user_avatar(self, user):
        return user.avatar.url if user.avatar else user.default_avatar.url

    @commands.hybrid_command(
        name="unban",
        help="Unbans a user from the Server",
        usage="unban <member>",
        aliases=["forgive", "pardon"])
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User, *, reason=None):
        bans = [entry async for entry in ctx.guild.bans()]
        if not any(ban_entry.user.id == user.id for ban_entry in bans):
            embed = discord.Embed(description="**Requested User is not banned in this server.**", color=self.color)
            embed.add_field(name="__Ban__:", value="Click on the `Ban` button to ban the mentioned user.")
            embed.set_author(name=f"{user.name} is Not Banned!", icon_url=self.get_user_avatar(user))
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            view = AlreadyUnbannedView(user=user, author=ctx.author)
            message = await ctx.send(embed=embed, view=view)
            view.message = message 
            return

        try:
            await user.send(f"✅ You have been unbanned from **{ctx.guild.name}** by **{ctx.author}**. Reason: {reason or 'No reason provided'}")
            dm_status = "Yes"
        except discord.Forbidden:
            dm_status = "No"
        except discord.HTTPException:
            dm_status = "No"

        await ctx.guild.unban(user, reason=f"Unban requested by {ctx.author} for reason: {reason or 'No reason provided'}")

        reasonn = reason or "No reason provided"
        embed = discord.Embed(description=f"**• Target User:** [{user}](https://discord.com/users/{user.id})\n**✅ User Mention:** {user.mention}\n**• DM Sent:** {dm_status}\n**✅ Reason:** {reasonn}", color=self.color)
        embed.set_author(name=f"Successfully Unbanned {user.name}", icon_url=self.get_user_avatar(user))
        embed.add_field(name="🛡️ Moderator:", value=ctx.author.mention, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
        embed.timestamp = discord.utils.utcnow()

        view = BanView(user=user, author=ctx.author)
        message = await ctx.send(embed=embed, view=view)
        view.message = message


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import ui

class HideUnhideView(ui.View):
    def __init__(self, channel, author, ctx):
        super().__init__(timeout=120)
        self.channel = channel
        self.author = author
        self.ctx = ctx  
        self.message = None  

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @ui.button(label="Hide", style=discord.ButtonStyle.danger)
    async def hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.channel.set_permissions(interaction.guild.default_role, read_messages=False)
        await interaction.response.send_message(f"{self.channel.mention} has been hidden.", ephemeral=True)

        embed = discord.Embed(
            description=f"• **Channel**: {self.channel.mention}\n✅ **Status**: Hidden\n• **Reason:** Hide request by {self.author}",
            color=0x000000
        )
        embed.add_field(name="• **Moderator:**", value=self.ctx.author.mention, inline=False)
        embed.set_author(name=f"Successfully Hidden {self.channel.name}", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        await self.message.edit(embed=embed, view=self)

        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        await self.message.edit(view=self)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class Unhide(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)

    @commands.hybrid_command(
        name="unhide",
        help="Unhides a channel to allow the default role (@everyone) to read messages.",
        usage="unhide <channel>",
        aliases=["unhidechannel"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unhide_command(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel 
        if channel.permissions_for(ctx.guild.default_role).read_messages:
            embed = discord.Embed(
                description=f"**• Channel**: {channel.mention}\n✅ **Status**: Already Unhidden",
                color=self.color
            )
            embed.set_author(name=f"{channel.name} is Already Unhidden", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
            view = HideUnhideView(channel=channel, author=ctx.author, ctx=ctx)  
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            return

        await channel.set_permissions(ctx.guild.default_role, read_messages=True)

        embed = discord.Embed(
            description=f"• **Channel**: {channel.mention}\n✅ **Status**: Unhidden\n• **Reason:** Unhide request by {ctx.author}",
            color=self.color
        )
        embed.add_field(name="• **Moderator:**", value=ctx.author.mention, inline=False)
        embed.set_author(name=f"Successfully Unhidden {channel.name}", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        view = HideUnhideView(channel=channel, author=ctx.author, ctx=ctx)  
        message = await ctx.send(embed=embed, view=view)
        view.message = message



"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import ui

class LockUnlockView(ui.View):
    def __init__(self, channel, author, ctx):
        super().__init__(timeout=120)
        self.channel = channel
        self.author = author
        self.ctx = ctx  
        self.message = None  

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass
            

    @ui.button(label="Lock", style=discord.ButtonStyle.danger)
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(f"{self.channel.mention} has been locked.", ephemeral=True)

        embed = discord.Embed(
            description=f"• **Channel**: {self.channel.mention}\n✅ **Status**: Locked\n• **Reason:** Lock request by {self.author}",
            color=0x000000
        )
        embed.add_field(name="• **Moderator:**", value=self.ctx.author.mention, inline=False)
        embed.set_author(name=f"Successfully Locked {self.channel.name}", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        await self.message.edit(embed=embed, view=self)

        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        await self.message.edit(view=self)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class Unlock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)

    @commands.hybrid_command(
        name="unlock",
        help="Unlocks a channel to allow sending messages.",
        usage="unlock <channel>",
        aliases=["unlockchannel"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unlock_command(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel 
        if channel.permissions_for(ctx.guild.default_role).send_messages is True:
            embed = discord.Embed(
                description=f"**• Channel**: {channel.mention}\n✅ **Status**: Already Unlocked",
                color=self.color
            )
            embed.set_author(name=f"{channel.name} is Already Unlocked", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
            view = LockUnlockView(channel=channel, author=ctx.author, ctx=ctx)  
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            return

        await channel.set_permissions(ctx.guild.default_role, send_messages=True)

        embed = discord.Embed(
            description=f"• **Channel**: {channel.mention}\n✅ **Status**: Unlocked\n• **Reason:** Unlock request by {ctx.author}",
            color=self.color
        )
        embed.add_field(name="• **Moderator:**", value=ctx.author.mention, inline=False)
        embed.set_author(name=f"Successfully Unlocked {channel.name}", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        view = LockUnlockView(channel=channel, author=ctx.author, ctx=ctx)  
        message = await ctx.send(embed=embed, view=view)
        view.message = message


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import ui
from utils.Tools import *
from datetime import timedelta

class MuteUnmuteView(ui.View):
    def __init__(self, user, author):
        super().__init__(timeout=120)
        self.user = user
        self.author = author
        self.message = None  

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @ui.button(label="Add Timeout", style=discord.ButtonStyle.danger)
    async def mute(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = MuteReasonModal(user=self.user, author=self.author, view=self)
        await interaction.response.send_modal(modal)

        
        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        await self.message.edit(view=self)

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class MuteReasonModal(ui.Modal):
    def __init__(self, user, author, view):
        super().__init__(title="Mute Information")
        self.user = user
        self.author = author
        self.view = view
        self.time_input = ui.TextInput(label="Duration (m/h/d)", placeholder="Leave blank for default 24h", required=False, max_length=5)
        self.reason_input = ui.TextInput(label="Reason", placeholder="Provide a reason or leave it blank.", required=False, max_length=2000, style=discord.TextStyle.paragraph)
        self.add_item(self.time_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value or "No reason provided"
        time_str = self.time_input.value or "24h"
        time_seconds = self.parse_duration(time_str)

        if time_seconds is None:
            await interaction.response.send_message(f"Invalid time format! Please provide in m (minutes), h (hours), or d (days).", ephemeral=True)
            return

        try:
            await self.user.edit(timed_out_until=discord.utils.utcnow() + timedelta(seconds=time_seconds))
        except discord.Forbidden:
            await interaction.response.send_message(f"Failed to mute {self.user.mention}. I lack the permissions.", ephemeral=True)
            return

        
        try:
            await self.user.send(f"⚠️ You have been muted in **{interaction.guild.name}** for {time_str}. Reason: {reason}")
            dm_status = "Yes"
        except discord.Forbidden:
            dm_status = "No"
        except discord.HTTPException:
            dm_status = "No"

        success_embed = discord.Embed(
            description=f"**• Target User:** [{self.user}](https://discord.com/users/{self.user.id})\n✅ **User Mention:** {self.user.mention}\n**✅ Reason:** {reason}\n• **DM Sent:** {dm_status}", 
            color=discord.Color.red()
        )
        success_embed.set_author(name=f"Muted {self.user.name}", icon_url=self.user.avatar.url if self.user.avatar else self.user.default_avatar.url)
        success_embed.add_field(name="🛡️ Moderator:", value=self.author.mention, inline=False)
        success_embed.add_field(name="Duration", value=f"{time_str}", inline=False)
        success_embed.set_footer(text=f"Requested by {self.author}", icon_url=self.author.avatar.url if self.author.avatar else self.author.default_avatar.url)
        success_embed.timestamp = discord.utils.utcnow()

        await interaction.response.edit_message(embed=success_embed, view=self.view)

        
        for item in self.view.children:
            if item.label != "Delete":
                item.disabled = True
        await self.view.message.edit(view=self.view)

    def parse_duration(self, duration_str: str) -> int:
        try:
            if duration_str.endswith("m"):
                duration = int(duration_str[:-1])
                return duration * 60
            elif duration_str.endswith("h"):
                duration = int(duration_str[:-1])
                return duration * 3600
            elif duration_str.endswith("d"):
                duration = int(duration_str[:-1])
                return duration * 86400
            else:
                
                duration = int(duration_str)
                if duration > 60:
                    return (duration // 60) * 3600  
                else:
                    return duration * 60  
        except ValueError:
            return None


class Unmute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)

    def get_user_avatar(self, user):
        return user.avatar.url if user.avatar else user.default_avatar.url

    @commands.hybrid_command(
        name="unmute",
        help="Unmutes a user from the Server",
        usage="unmute <member>",
        aliases=["untimeout"])
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx, user: discord.Member):
        if not user.timed_out_until or user.timed_out_until <= discord.utils.utcnow():
            embed = discord.Embed(description="**Requested User is not muted in this server.**", color=self.color)
            embed.add_field(name="__Mute__:", value="Click on the `Add Timeout` button to mute the mentioned user.")
            embed.set_author(name=f"{user.name} is Not Muted!", icon_url=self.get_user_avatar(user))
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            view = MuteUnmuteView(user=user, author=ctx.author)
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            return

        try:
            await user.edit(timed_out_until=None)

            
            try:
                await user.send(f"✅ You have been unmuted in **{ctx.guild.name}**.")
                dm_status = "Yes"
            except discord.Forbidden:
                dm_status = "No"
            except discord.HTTPException:
                dm_status = "No"

        except discord.Forbidden:
            error = discord.Embed(color=self.color, description="I can't unmute a user with higher permissions!")
            error.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            error.set_author(name="Error Unmuting User", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            return await ctx.send(embed=error)

        embed = discord.Embed(
            description=f"**• Target User:** [{user}](https://discord.com/users/{user.id})\n**✅ User Mention:** {user.mention}\n• **DM Sent:** {dm_status}",
            color=self.color
        )
        embed.set_author(name=f"Successfully Unmuted {user.name}", icon_url=self.get_user_avatar(user))
        embed.add_field(name="🛡️ Moderator:", value=ctx.author.mention, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
        embed.timestamp = discord.utils.utcnow()

        view = MuteUnmuteView(user=user, author=ctx.author)
        message = await ctx.send(embed=embed, view=view)
        view.message = message


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import ui
import aiosqlite
import asyncio
from utils.Tools import *


class WarnView(ui.View):
    def __init__(self, user, author):
        super().__init__(timeout=60)
        self.user = user
        self.author = author
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @ui.button(style=discord.ButtonStyle.gray, emoji="•")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class Warn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)
        self.db_path = "db/warn.db"

        
        asyncio.create_task(self.setup())

    def get_user_avatar(self, user):
        return user.avatar.url if user.avatar else user.default_avatar.url

    async def add_warn(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO warns (guild_id, user_id, warns) VALUES (?, ?, 0)", (guild_id, user_id))
            await db.execute("UPDATE warns SET warns = warns + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await db.commit()

    async def get_total_warns(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT warns FROM warns WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]
                return 0

    async def reset_warns(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE warns SET warns = 0 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await db.commit()

    async def setup(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                CREATE TABLE IF NOT EXISTS warns (
                    guild_id INTEGER,
                    user_id INTEGER,
                    warns INTEGER,
                    PRIMARY KEY (guild_id, user_id)
                )
                """)
                await db.commit()
        except Exception as e:
            print(f"Error during database setup: {e}")

    @commands.hybrid_command(
        name="warn",
        help="Warn a user in the server",
        usage="warn <user> [reason]",
        aliases=["warnuser"])
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    #@commands.bot_has_permissions(manage_messages=True)
    async def warn(self, ctx, user: discord.Member, *, reason=None):
        if user == ctx.author:
            return await ctx.reply("You cannot warn yourself.")

        if user == ctx.bot.user:
            return await ctx.reply("You cannot warn me.")

        if not ctx.author == ctx.guild.owner:
            if user == ctx.guild.owner:
                return await ctx.reply("I cannot warn the server owner.")

            if ctx.author.top_role <= user.top_role:
                return await ctx.reply("You cannot Warn a member with a higher or equal role.")

        if ctx.guild.me.top_role <= user.top_role:
            return await ctx.reply("I cannot Warn a member with a higher or equal role.")

        if user not in ctx.guild.members:
            return await ctx.reply("The user is not a member of this server.")
        try:
            
            await self.add_warn(ctx.guild.id, user.id)
            total_warns = await self.get_total_warns(ctx.guild.id, user.id)

            
            reason_to_send = reason or "No reason provided"
            try:
                await user.send(f"You have been warned in **{ctx.guild.name}** by **{ctx.author}**. Reason: {reason_to_send}")
                dm_status = "Yes"
            except discord.Forbidden:
                dm_status = "No"
            except discord.HTTPException:
                dm_status = "No"

            
            embed = discord.Embed(description=f"**• Target User:** [{user}](https://discord.com/users/{user.id})\n"
                                              f"**✅ User Mention:** {user.mention}\n"
                                              f"**• DM Sent:** {dm_status}\n"
                                              f"**• Reason:** {reason_to_send}\n"
                                              f"**• Total Warns:** {total_warns}",
                                              color=self.color)
            embed.set_author(name=f"Successfully Warned {user.name}", icon_url=self.get_user_avatar(user))
            embed.add_field(name="🛡️ Moderator:", value=ctx.author.mention, inline=False)
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            embed.timestamp = discord.utils.utcnow()

            view = WarnView(user=user, author=ctx.author)
            message = await ctx.send(embed=embed, view=view)
            view.message = message
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            print(f"Error during warn command: {e}")

    @commands.hybrid_command(
        name="clearwarns",
        help="Clear all warnings for a user",
        aliases=["clearwarn" , "clearwarnings"],
        usage="clearwarns <user>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def clearwarns(self, ctx, user: discord.Member):
        try:
            await self.reset_warns(ctx.guild.id, user.id)
            embed = discord.Embed(description=f"✅ | All warnings have been cleared for **{user}** in this guild.", color=self.color)
            embed.set_author(name=f"Warnings Cleared", icon_url=self.get_user_avatar(user))
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=self.get_user_avatar(ctx.author))
            embed.timestamp = discord.utils.utcnow()

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            print(f"Error during clearwarns command: {e}")


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
