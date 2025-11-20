import discord
from discord.ext import commands
import aiosqlite
import os
import time
from typing import Optional
from utils.Tools import *

black1 = 0
black2 = 0
black3 = 0

DB_PATH = "db/afk.db"

class BasicView(discord.ui.View):
    def __init__(self, ctx: commands.Context, timeout: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(embed=discord.Embed(description=f"Only **{self.ctx.author}** can use this command. Use {self.ctx.prefix}**{self.ctx.command}** to run the command", color=self.ctx.author.color), ephemeral=True)
            return False
        return True

class OnOrOff(BasicView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx, timeout=None)
        self.value = None

    @discord.ui.button(label="DM me", emoji="✅", custom_id='Yes', style=discord.ButtonStyle.green)
    async def dare(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = 'Yes'
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Don't DM", emoji="❌", custom_id='No', style=discord.ButtonStyle.danger)
    async def truth(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = 'No'
        await interaction.response.defer()
        self.stop()

class afk(commands.Cog):

    def __init__(self, client, *args, **kwargs):
        self.client = client
        self.client.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS afk (
                    user_id INTEGER PRIMARY KEY,
                    AFK TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    time INTEGER NOT NULL,
                    mentions INTEGER NOT NULL,
                    dm TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS afk_guild (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            await db.commit()

    async def cog_after_invoke(self, ctx):
        ctx.command.reset_cooldown(ctx)

    async def update_data(self, user, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO afk (user_id, AFK, reason, time, mentions, dm) VALUES (?, 'False', 'None', 0, 0, 'False')", (user.id,))
            await db.execute("INSERT OR IGNORE INTO afk_guild (user_id, guild_id) VALUES (?, ?)", (user.id, guild_id))
            await db.commit()

    async def time_formatter(self, seconds: float):
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        tmp = ((str(days) + " days, ") if days else "") + \
              ((str(hours) + " hours, ") if hours else "") + \
              ((str(minutes) + " minutes, ") if minutes else "") + \
              ((str(seconds) + " seconds, ") if seconds else "")
        return tmp[:-2]

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if message.author.bot:
                return

            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute("SELECT AFK, time, mentions, reason FROM afk WHERE user_id = ?", (message.author.id,))
                afk_data = await cursor.fetchone()
                await cursor.close()

                if afk_data and afk_data[0] == 'True':
                    cursor = await db.execute("SELECT guild_id FROM afk_guild WHERE user_id = ?", (message.author.id,))
                    guild_ids = [row[0] for row in await cursor.fetchall()]
                    await cursor.close()

                    if message.guild.id in guild_ids:
                        meth = int(time.time()) - int(afk_data[1])
                        been_afk_for = await self.time_formatter(meth)
                        mentionz = afk_data[2]
                        await db.execute("UPDATE afk SET AFK = 'False', reason = 'None' WHERE user_id = ?", (message.author.id,))
                        await db.execute("DELETE FROM afk_guild WHERE user_id = ? AND guild_id = ?", (message.author.id, message.guild.id))
                        await db.commit()
                        wlbat = discord.Embed(title=f'{message.author.display_name} Welcome Back!',
                                              description=f'I removed your AFK\nTotal Mentions: **{mentionz}**\nAFK Timing: **{been_afk_for}**', color=0x0c0606)
                        try:
                            await message.reply(embed=wlbat)
                        except discord.Forbidden:
                            print(f"(AFK module) Missing permissions to send messages in channel: {message.channel.id}")

            if message.mentions:
                async with aiosqlite.connect(DB_PATH) as db:
                    for user_mention in message.mentions:
                        cursor = await db.execute("SELECT AFK, reason, time, mentions, dm FROM afk WHERE user_id = ?", (user_mention.id,))
                        afk_data = await cursor.fetchone()
                        await cursor.close()

                        if afk_data and afk_data[0] == 'True':
                            cursor = await db.execute("SELECT guild_id FROM afk_guild WHERE user_id = ?", (user_mention.id,))
                            guild_ids = [row[0] for row in await cursor.fetchall()]
                            await cursor.close()

                            if message.guild.id in guild_ids:
                                reason = afk_data[1]
                                ok = afk_data[2]
                                wl = discord.Embed(description=f'**<@{user_mention.id}>** went AFK <t:{ok}:R> for the following reason:\n**{reason}**', color=0x0c0606)
                                try:
                                    await message.reply(embed=wl)
                                except discord.Forbidden:
                                    print(f"(AFK module) Missing permissions to send messages to user: {user_mention.id}")

                                new_mentions = afk_data[3] + 1
                                await db.execute("UPDATE afk SET mentions = ? WHERE user_id = ?", (new_mentions, user_mention.id))
                                await db.commit()

                                embed = discord.Embed(description=f'You were mentioned in **{message.guild.name}** by **{message.author}**', color=discord.Color.from_rgb(black1, black2, black3))
                                embed.add_field(name="Total mentions:", value=new_mentions, inline=False)
                                embed.add_field(name="Message:", value=message.content, inline=False)
                                embed.add_field(name="Jump Message:", value=f"[Jump to message]({message.jump_url})", inline=False)

                                if afk_data[4] == 'True':
                                    try:
                                        await user_mention.send(embed=embed)
                                    except discord.Forbidden:
                                        print(f"(AFK module) Missing permissions to send DMs to user: {user_mention.id}")

            if not message.author.bot:
                await self.update_data(message.author, message.guild.id)
        except Exception as e:
            print(f"Ignoring exception in on_message: {e}")

    @commands.hybrid_command(description="Shows an AFK status when you're mentioned")
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def afk(self, ctx, *, reason=None):
        if not reason:
            reason = "I am afk :)"

        if any(invite in reason.lower() for invite in ['discord.gg', 'gg/']):
            emd = discord.Embed(description="🔔 | You can't advertise Serve Invite in the AFK reason", color=0x0c0606)
            return await ctx.send(embed=emd)

        view = OnOrOff(ctx)
        em = discord.Embed(description="Should I DM you on mentions?", color=0x000000)
        try:
            em.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
        except:
            em.set_author(name=str(ctx.author))
        test = await ctx.reply(embed=em, view=view)
        await view.wait()

        async with aiosqlite.connect(DB_PATH) as db:
            if not view.value:
                return await test.edit(content="Timed Out, please try again.", view=None)
            dm_status = 'True' if view.value == 'Yes' else 'False'

            await db.execute("INSERT OR REPLACE INTO afk (user_id, AFK, reason, time, mentions, dm) VALUES (?, 'True', ?, ?, 0, ?)", 
                             (ctx.author.id, reason, int(time.time()),dm_status))
            await db.commit()
            await db.execute("INSERT OR IGNORE INTO afk_guild (user_id, guild_id) VALUES (?, ?)", (ctx.author.id, ctx.guild.id))
            await db.commit()

            await test.delete()
            af = discord.Embed(title='✅ Success', 
                 description=f'{ctx.author.mention}, You are now marked as AFK due to: **{reason}**', 
                 color=0x000000)
            await ctx.reply(embed=af)

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
from utils.Tools import *


class Antinuke(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.bot.loop.create_task(self.initialize_db())

  async def initialize_db(self):
    self.db = await aiosqlite.connect('db/anti.db')
    await self.db.execute('''
        CREATE TABLE IF NOT EXISTS antinuke (
            guild_id INTEGER PRIMARY KEY,
            status BOOLEAN
        )
    ''')
    await self.db.commit()

    
  async def enable_limit_settings(self, guild_id):
    default_limits = DEFAULT_LIMITS
    for action, limit in default_limits.items():
      await self.db.execute('INSERT OR REPLACE INTO limit_settings (guild_id, action_type, action_limit, time_window) VALUES (?, ?, ?, ?)', (guild_id, action, limit, TIME_WINDOW))
      await self.db.commit()

  async def disable_limit_settings(self, guild_id):
    await self.db.execute('DELETE FROM limit_settings WHERE guild_id = ?', (guild_id,))
    await self.db.commit()


  @commands.hybrid_command(name='antinuke', aliases=['antiwizz', 'anti'], help="Enables/Disables Anti-Nuke Module in the server")
  
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 4, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  async def antinuke(self, ctx, option: str = None):
    guild_id = ctx.guild.id
    pre=ctx.prefix

    async with self.db.execute('SELECT status FROM antinuke WHERE guild_id = ?', (guild_id,)) as cursor:
      row = await cursor.fetchone()

    async with self.db.execute(
            "SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?",
            (ctx.guild.id, ctx.author.id)
        ) as cursor:
            check = await cursor.fetchone()

    is_owner = ctx.author.id == ctx.guild.owner_id
    if not is_owner and not check:
      embed = discord.Embed(title="❌ Access Denied",
                color=0x000000,
                description="Only Server Owner or Extra Owner can Run this Command!"
            )
      return await ctx.send(embed=embed)

    is_activated = row[0] if row else False

    if option is None:
      embed = discord.Embed(
        title='__**Antinuke**__',
        description="Boost your server security with Antinuke! It automatically bans any admins involved in suspicious activities, ensuring the safety of your whitelisted members. Strengthen your defenses – activate Antinuke today!",
        color=0x000000
      )
      embed.add_field(name='__**Antinuke Enable**__', value=f'To Enable Antinuke, Use - `{pre}antinuke enable`')
      embed.add_field(name='__**Antinuke Disable**__', value=f'To Disable Antinuke, Use - `{pre}antinuke disable`')
      

      embed.set_thumbnail(url=self.bot.user.avatar.url)
      await ctx.send(embed=embed)

    elif option.lower() == 'enable':
      if is_activated:
        embed = discord.Embed(
          description=f'**Security Settings For {ctx.guild.name}**\nYour server __**already has Antinuke enabled.**__\n\nCurrent Status: ✅ Enabled\nTo Disable use `antinuke disable`',
          color=0x000000
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)
      else:
        
        setup_embed = discord.Embed(
          title="Antinuke Setup ⚙️",
          description="✅ | Initializing Quick Setup!",
          color=0x000000
        )
        setup_message = await ctx.send(embed=setup_embed)

        
        if not ctx.guild.me.guild_permissions.administrator:
          setup_embed.description += "\n⚠️ | Setup failed: Missing **Administrator** permission."
          await setup_message.edit(embed=setup_embed)
          return

        await asyncio.sleep(1)
        setup_embed.description += "\n✅ | Checking Tempest's role position for optimal configuration..."
        await setup_message.edit(embed=setup_embed)

        await asyncio.sleep(1)
        setup_embed.description += "\n✅ | Crafting and configuring the Tempest Supreme role..."
        await setup_message.edit(embed=setup_embed)
        
        try:
          role = await ctx.guild.create_role(
            name="Tempest Supreme™",
            color=0xdc143c,
            permissions=discord.Permissions(administrator=True),
            hoist=False,
            mentionable=False,
            reason="Antinuke setup Role Creation"
          )
          await ctx.guild.me.add_roles(role)
        except discord.Forbidden:
          setup_embed.description += "\n⚠️ | Setup failed: Insufficient permissions to create role."
          await setup_message.edit(embed=setup_embed)
          return
        except discord.HTTPException as e:
          setup_embed.description += f"\n⚠️ | Setup failed: HTTPException: {e}\nCheck Guild **Audit Logs**."
          await setup_message.edit(embed=setup_embed)
          return

        await asyncio.sleep(1)
        setup_embed.description += "\n✅ | Ensuring precise placement of the Tempest Supreme role..."
        await setup_message.edit(embed=setup_embed)
        try:
          await ctx.guild.edit_role_positions(positions={role: 1})
        except discord.Forbidden:
          setup_embed.description += "\n⚠️ | Setup failed: Insufficient permissions to move role."
          await setup_message.edit(embed=setup_embed)
          return
        except discord.HTTPException as e:
          setup_embed.description += f"\n⚠️ | Setup failed: HTTPException: {e}."
          await setup_message.edit(embed=setup_embed)
          return

        await asyncio.sleep(1)
        setup_embed.description += "\n✅ | Safeguarding your changes..."
        await setup_message.edit(embed=setup_embed)

        await asyncio.sleep(1)
        setup_embed.description += "\n✅ | Activating the Antinuke Modules for enhanced security...!!"
        await setup_message.edit(embed=setup_embed)

        await self.db.execute('INSERT OR REPLACE INTO antinuke (guild_id, status) VALUES (?, ?)', (guild_id, True))
        await self.db.commit()

        await asyncio.sleep(1)
        await setup_message.delete()

        embed = discord.Embed(
          description=f"**Security Settings For {ctx.guild.name} 🛡️**\n\nTip: For optimal functionality of the AntiNuke Module, please ensure that my role has **Administration** permissions and is positioned at the **Top** of the roles list\n\n⚙️ __**Modules Enabled**__\n>>> ✅ **Anti Ban**\n✅ **Anti Kick**\n✅ **Anti Bot**\n✅ **Anti Channel Create**\n✅ **Anti Channel Delete**\n✅ **Anti Channel Update**\n✅ **Anti Everyone/Here**\n✅ **Anti Role Create**\n✅ **Anti Role Delete**\n✅ **Anti Role Update**\n✅ **Anti Member Update**\n✅ **Anti Guild Update**\n✅ **Anti Integration**\n✅ **Anti Webhook Create**\n✅ **Anti Webhook Delete**\n✅ **Anti Webhook Update**",
          color=0x000000
        )

        embed.add_field(name='', value="✅ **Anti Prune**\n✅ **Auto Recovery**")

        embed.set_author(name="Tempest Antinuke", icon_url=self.bot.user.avatar.url)

        embed.set_footer(text="Successfully Enabled Antinuke for this server | Powered by Tempest Federation™", icon_url=self.bot.user.avatar.url)
        embed.set_thumbnail(url=self.bot.user.avatar.url)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Show Punishment Type", custom_id="show_punishment"))

        await ctx.send(embed=embed, view=view)

    elif option.lower() == 'disable':
      if not is_activated:
        embed = discord.Embed(
          description=f'**Security Settings For {ctx.guild.name}**\nUhh, looks like your server hasn\'t enabled Antinuke.\n\nCurrent Status: ❌ Disabled\n\nTo Enable use `antinuke enable`',
          color=0x000000
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
      else:
        await self.db.execute('DELETE FROM antinuke WHERE guild_id = ?', (guild_id,))
        await self.db.commit()
        embed = discord.Embed(
          description=f'**Security Settings For {ctx.guild.name}**\nSuccessfully disabled Antinuke for this server.\n\nCurrent Status: ❌ Disabled\n\nTo Enable use `antinuke enable`',
          color=0x000000
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
      await ctx.send(embed=embed)
    else:
      embed = discord.Embed(
        description='Invalid option. Please use `enable` or `disable`.',
        color=0x000000
      )
      await ctx.send(embed=embed)


  @commands.Cog.listener()
  async def on_interaction(self, interaction: discord.Interaction):
    if interaction.data.get('custom_id') == 'show_punishment':
    
      embed = discord.Embed(
        title="Punishment Types for Changes Made by Unwhitelisted Admins/Mods",
        description=(
          "**Anti Ban:** Ban\n"
          "**Anti Kick:** Ban\n"
          "**Anti Bot:** Ban the bot Inviter\n"
          "**Anti Channel Create/Delete/Update:** Ban\n"
          "**Anti Everyone/Here:** Remove the message & 1 hour timeout\n"
          "**Anti Role Create/Delete/Update:** Ban\n"
          "**Anti Member Update:** Ban\n"
          "**Anti Guild Update:** Ban\n"
          "**Anti Integration:** Ban\n"
          "**Anti Webhook Create/Delete/Update:** Ban\n"
          "**Anti Prune:** Ban\n"
          "**Auto Recovery:** Automatically recover damaged channels, roles, and settings\n\n"
          "Note: In the case of member updates, action will be taken only if the role contains dangerous permissions such as Ban Members, Administrator, Manage Guild, Manage Channels, Manage Roles, Manage Webhooks, or Mention Everyone"
        ),
        color=0x000000
      )
      embed.set_footer(text="These punishment types are fixed and assigned as required to ensure guild security/protection", icon_url=self.bot.user.avatar.url)
      await interaction.response.send_message(embed=embed, ephemeral=True)

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
import aiosqlite
from utils.Tools import *


class Unwhitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize_db())

    #@commands.Cog.listener()
    async def initialize_db(self):
        self.db = await aiosqlite.connect('db/anti.db')

    @commands.hybrid_command(name='unwhitelist', aliases=['unwl'], help="Unwhitelist a user from antinuke")
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def unwhitelist(self, ctx, member: discord.Member = None):
        if ctx.guild.member_count < 2:
            embed = discord.Embed(
                color=0x000000,
                description="❌ | Your Server Doesn't Meet My 30 Member Criteria"
            )
            return await ctx.send(embed=embed)

        async with self.db.execute(
            "SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?",
            (ctx.guild.id, ctx.author.id)
        ) as cursor:
            check = await cursor.fetchone()

        async with self.db.execute(
            "SELECT status FROM antinuke WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cursor:
            antinuke = await cursor.fetchone()

        is_owner = ctx.author.id == ctx.guild.owner_id
        if not is_owner and not check:
            embed = discord.Embed(title="❌ Access Denied",
                color=0x000000,
                description="Only Server Owner or Extra Owner can Run this Command!"
            )
            return await ctx.send(embed=embed)

        if not antinuke or not antinuke[0]:
            embed = discord.Embed(
                color=0x000000,
                description=(
                    f"**{ctx.guild.name} Security Settings 🛡️\n"
                    "Ohh NO! looks like your server doesn't enabled security\n\n"
                    "Current Status : ❌\n\n"
                    "To enable use `antinuke enable` **"
                )
            )
            return await ctx.send(embed=embed)

        if not member:
            embed = discord.Embed(
                color=0x000000,
                title="__**Unwhitelist Commands**__",
                description="**Removes user from whitelisted users which means that the antinuke module will now take actions on them if they trigger it.**"
            )
            embed.add_field(name="__**Usage**__", value="🔴 `unwhitelist @user/id`\n🔴 `unwl @user`")
            return await ctx.send(embed=embed)

        async with self.db.execute(
            "SELECT * FROM whitelisted_users WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id)
        ) as cursor:
            data = await cursor.fetchone()

        if not data:
            embed = discord.Embed(title="❌ Error",
                color=0x000000,
                description=f"<@{member.id}> is not a whitelisted member."
            )
            return await ctx.send(embed=embed)

        await self.db.execute(
            "DELETE FROM whitelisted_users WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id)
        )
        await self.db.commit()

        embed = discord.Embed(title="✅ Success",
            color=0x000000,
            description=f"User <@!{member.id}> has been removed from the whitelist."
        )
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
from utils.Tools import *


class Whitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize_db())

    
    #@commands.Cog.listener()
    async def initialize_db(self):
        self.db = await aiosqlite.connect('db/anti.db')
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS whitelisted_users (
                guild_id INTEGER,
                user_id INTEGER,
                ban BOOLEAN DEFAULT FALSE,
                kick BOOLEAN DEFAULT FALSE,
                prune BOOLEAN DEFAULT FALSE,
                botadd BOOLEAN DEFAULT FALSE,
                serverup BOOLEAN DEFAULT FALSE,
                memup BOOLEAN DEFAULT FALSE,
                chcr BOOLEAN DEFAULT FALSE,
                chdl BOOLEAN DEFAULT FALSE,
                chup BOOLEAN DEFAULT FALSE,
                rlcr BOOLEAN DEFAULT FALSE,
                rlup BOOLEAN DEFAULT FALSE,
                rldl BOOLEAN DEFAULT FALSE,
                meneve BOOLEAN DEFAULT FALSE,
                mngweb BOOLEAN DEFAULT FALSE,
                mngstemo BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')
        await self.db.commit()

    @commands.hybrid_command(name='whitelist', aliases=['wl'], help="Whitelists a user from antinuke for a specific action.")

    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)

    async def whitelist(self, ctx, member: discord.Member = None):
        if ctx.guild.member_count < 2:
            embed = discord.Embed(
                color=0x000000,
                description="❌ | Your Server Doesn't Meet My 30 Member Criteria"
            )
            return await ctx.send(embed=embed)

        prefix=ctx.prefix

        async with self.db.execute(
            "SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?",
            (ctx.guild.id, ctx.author.id)
        ) as cursor:
            check = await cursor.fetchone()

        async with self.db.execute(
            "SELECT status FROM antinuke WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cursor:
            antinuke = await cursor.fetchone()

        is_owner = ctx.author.id == ctx.guild.owner_id
        if not is_owner and not check:
            embed = discord.Embed(title="❌ Access Denied",
                color=0x000000,
                description="Only Server Owner or Extra Owner can Run this Command!"
            )
            return await ctx.send(embed=embed)

        if not antinuke or not antinuke[0]:
            embed = discord.Embed(
                color=0x000000,
                description=(
                    f"**{ctx.guild.name} Security Settings 🛡️\n"
                    "Ohh No! looks like your server doesn't enabled Antinuke\n\n"
                    "Current Status : ❌\n\n"
                    f"To enable use `{prefix}antinuke enable` **"
                )
            )
            embed.set_thumbnail(url=ctx.bot.user.avatar.url)
            return await ctx.send(embed=embed)

        if not member:
            embed = discord.Embed(
                color=0x000000,
                title="__**Whitelist Commands**__",
                description="**Adding a user to the whitelist means that no actions will be taken against them if they trigger the Anti-Nuke Module.**"
            )
            embed.add_field(name="__**Usage**__", value=f"🔴 `{prefix}whitelist @user/id`\n🔴 `{prefix}wl @user`")
            embed.set_thumbnail(url=ctx.bot.user.avatar.url)
            return await ctx.send(embed=embed)

        async with self.db.execute(
            "SELECT * FROM whitelisted_users WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id)
        ) as cursor:
            data = await cursor.fetchone()

        if data:
            embed = discord.Embed(title="❌ Error",
                color=0x000000,
                description=f"<@{member.id}> is already a whitelisted member, **Unwhitelist** the user and try again."
            )
            return await ctx.send(embed=embed)

        await self.db.execute(
            "INSERT INTO whitelisted_users (guild_id, user_id) VALUES (?, ?)",
            (ctx.guild.id, member.id)
        )
        await self.db.commit()

        options = [
            discord.SelectOption(label="Ban", description="Whitelist a member with ban permission", value="ban"),
            discord.SelectOption(label="Kick", description="Whitelist a member with kick permission", value="kick"),
            discord.SelectOption(label="Prune", description="Whitelist a member with prune permission", value="prune"),
            discord.SelectOption(label="Bot Add", description="Whitelist a member with bot add permission", value="botadd"),
            discord.SelectOption(label="Server Update", description="Whitelist a member with server update permission", value="serverup"),
            discord.SelectOption(label="Member Update", description="Whitelist a member with member update permission", value="memup"),
            discord.SelectOption(label="Channel Create", description="Whitelist a member with channel create permission", value="chcr"),
            discord.SelectOption(label="Channel Delete", description="Whitelist a member with channel delete permission", value="chdl"),
            discord.SelectOption(label="Channel Update", description="Whitelist a member with channel update permission", value="chup"),
            discord.SelectOption(label="Role Create", description="Whitelist a member with role create permission", value="rlcr"),
            discord.SelectOption(label="Role Update", description="Whitelist a member with role update permission", value="rlup"),
            discord.SelectOption(label="Role Delete", description="Whitelist a member with role delete permission", value="rldl"),
            discord.SelectOption(label="Mention Everyone", description="Whitelist a member with mention everyone permission", value="meneve"),
            discord.SelectOption(label="Manage Webhook", description="Whitelist a member with manage webhook permission", value="mngweb")
        ]

        select = discord.ui.Select(placeholder="Choose Your Options", min_values=1, max_values=len(options), options=options, custom_id="wl")
        button = discord.ui.Button(label="Add This User To All Categories", style=discord.ButtonStyle.primary, custom_id="catWl")

        view = discord.ui.View()
        view.add_item(select)
        view.add_item(button)

        embed = discord.Embed(
            title=ctx.guild.name,
            color=0x000000,
            description=(
                f"❌✅ : **Ban**\n"
                f"❌✅ : **Kick**\n"
                f"❌✅ : **Prune**\n"
                f"❌✅ : **Bot Add**\n"
                f"❌✅ : **Server Update**\n"
                f"❌✅ : **Member Update**\n"
                f"❌✅ : **Channel Create**\n"
                f"❌✅ : **Channel Delete**\n"
                f"❌✅ : **Channel Update**\n"
                f"❌✅ : **Role Create**\n"
                f"❌✅ : **Role Delete**\n"
                f"❌✅ : **Role Update**\n"
                f"❌✅ : **Mention** @everyone\n"
                f"❌✅ : **Webhook Management**"
                
            )
        )
        embed.add_field(name="**Executor**", value=f"<@!{ctx.author.id}>", inline=True)
        embed.add_field(name="**Target**", value=f"<@!{member.id}>", inline=True)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text=f"Developed by Tempest Federation™")

        msg = await ctx.send(embed=embed, view=view)

        def check(interaction):
            return interaction.user.id == ctx.author.id and interaction.message.id == msg.id

        try:
            interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
            if interaction.data["custom_id"] == "catWl":
                
                await self.db.execute(
                    "UPDATE whitelisted_users SET ban = ?, kick = ?, prune = ?, botadd = ?, serverup = ?, memup = ?, chcr = ?, chdl = ?, chup = ?, rlcr = ?, rldl = ?, rlup = ?, meneve = ?, mngweb = ?, mngstemo = ? WHERE guild_id = ? AND user_id = ?",
                    (True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, ctx.guild.id, member.id)
                )
                await self.db.commit()

                
                embed = discord.Embed(
                    title=ctx.guild.name,
                    color=0x000000,
                    description=(
                        f"❌✅ : **Ban**\n"
                        f"❌✅ : **Kick**\n"
                        f"❌✅ : **Prune**\n"
                        f"❌✅ : **Bot Add**\n"
                        f"❌✅ : **Server Update**\n"
                        f"❌✅ : **Member Update**\n"
                        f"❌✅ : **Channel Create**\n"
                        f"❌✅ : **Channel Delete**\n"
                        f"❌✅ : **Channel Update**\n"
                        f"❌✅ : **Role Create**\n"
                        f"❌✅ : **Role Delete**\n"
                        f"❌✅ : **Role Update**\n"
                        f"❌✅ : **Mention** @everyone\n"
                        f"❌✅ : **Webhook Management**"
                        
                    )
                )
                embed.add_field(name="**Executor**", value=f"<@!{ctx.author.id}>", inline=True)
                embed.add_field(name="**Target**", value=f"<@!{member.id}>", inline=True)
                embed.set_thumbnail(url=self.bot.user.avatar.url)
                embed.set_footer(text=f"Developed by Tempest Federation™")

                await interaction.response.edit_message(embed=embed, view=None)
            else:
                
                fields = {
                    'ban': 'Ban',
                    'kick': 'Kick',
                    'prune': 'Prune',
                    'botadd': 'Bot Add',
                    'serverup': 'Server Update',
                    'memup': 'Member Update',
                    'chcr': 'Channel Create',
                    'chdl': 'Channel Delete',
                    'chup': 'Channel Update',
                    'rlcr': 'Role Create',
                    'rldl': 'Role Delete',
                    'rlup': 'Role Update',
                    'meneve': 'Mention Everyone',
                    'mngweb': 'Manage Webhooks'
                }

                
                embed_description = "\n".join(f"❌✅ : **{name}**" for key, name in fields.items())

                
                for value in interaction.data["values"]:
                    await self.db.execute(
                        f"UPDATE whitelisted_users SET {value} = ? WHERE guild_id = ? AND user_id = ?",
                        (True, ctx.guild.id, member.id)
                    )
                    embed_description = embed_description.replace(f"❌✅ : **{fields[value]}**", f"❌✅ : **{fields[value]}**")

                await self.db.commit()

                
                embed = discord.Embed(
                    title=ctx.guild.name,
                    color=0x000000,
                    description=embed_description
                )
                embed.add_field(name="**Executor**", value=f"<@!{ctx.author.id}>", inline=True)
                embed.add_field(name="**Target**", value=f"<@!{member.id}>", inline=True)
                embed.set_thumbnail(url=self.bot.user.avatar.url)
                embed.set_footer(text=f"Developed by Tempest Federation™")

                await interaction.response.edit_message(embed=embed, view=None)
        except TimeoutError:
            await msg.edit(view=None)


    @commands.hybrid_command(name='whitelisted', aliases=['wlist'], help="Shows the list of whitelisted users.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def whitelisted(self, ctx):
        if ctx.guild.member_count < 2:
            embed = discord.Embed(
                color=0x000000,
                description="❌ | Your Server Doesn't Meet My 30 Member Criteria"
            )
            return await ctx.send(embed=embed)

        pre=ctx.prefix

        async with self.db.execute(
            "SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?",
            (ctx.guild.id, ctx.author.id)
        ) as cursor:
            check = await cursor.fetchone()

        async with self.db.execute(
            "SELECT status FROM antinuke WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cursor:
            antinuke = await cursor.fetchone()

        is_owner = ctx.author.id == ctx.guild.owner_id
        if not is_owner and not check:
            embed = discord.Embed(title="❌ Access Denied",
                color=0x000000,
                description="Only Server Owner or Extra Owner can Run this Command!"
            )
            return await ctx.send(embed=embed)

        if not antinuke or not antinuke[0]:
            embed = discord.Embed(
                color=0x000000,
                description=(
                    f"**{ctx.guild.name} security settings 🛡️\n"
                    "Ohh NO! looks like your server doesn't enabled security\n\n"
                    "Current Status : ❌\n\n"
                    f"To enable use `{pre}antinuke enable` **"
                )
            )
            return await ctx.send(embed=embed)


        async with self.db.execute(
            "SELECT user_id FROM whitelisted_users WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cursor:
            data = await cursor.fetchall()

        if not data:
            embed = discord.Embed(title="❌ Error",
                color=0x000000,
                description="No whitelisted users found."
            )
            return await ctx.send(embed=embed)

        whitelisted_users = [self.bot.get_user(user_id[0]) for user_id in data]
        whitelisted_users_str = ", ".join(f"<@!{user.id}>" for user in whitelisted_users if user)

        embed = discord.Embed(
            color=0x000000,
            title=f"__Whitelisted Users for {ctx.guild.name}__",
            description=whitelisted_users_str
        )
        await ctx.send(embed=embed)


    @commands.hybrid_command(name="whitelistreset", aliases=['wlreset'], help="Resets the whitelisted users.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def whitelistreset(self, ctx):
        if ctx.guild.member_count < 2:
            embed = discord.Embed(
                color=0x000000,
                description="❌ | Your Server Doesn't Meet My 30 Member Criteria"
            )
            return await ctx.send(embed=embed)

        pre=ctx.prefix

        async with self.db.execute(
            "SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?",
            (ctx.guild.id, ctx.author.id)
        ) as cursor:
            check = await cursor.fetchone()

        async with self.db.execute(
            "SELECT status FROM antinuke WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cursor:
            antinuke = await cursor.fetchone()

        is_owner = ctx.author.id == ctx.guild.owner_id
        if not is_owner and not check:
            embed = discord.Embed(title="❌ Access Denied",
                color=0x000000,
                description="Only Server Owner or Extra Owner can Run this Command!"
            )
            return await ctx.send(embed=embed)

        if not antinuke or not antinuke[0]:
            embed = discord.Embed(
                color=0x000000,
                description=(
                    f"**{ctx.guild.name} Security Settings 🛡️\n"
                    "Ohh NO! looks like your server doesn't enabled security\n\n"
                    "Current Status : ❌\n\n"
                    f"To enable use `{pre}antinuke enable` **"
                )
            )
            return await ctx.send(embed=embed)

        async with self.db.execute(
            "SELECT user_id FROM whitelisted_users WHERE guild_id = ?",
            (ctx.guild.id,)
        ) as cursor:
            data = await cursor.fetchall()


        if not data:
            embed = discord.Embed(title="❌ Error",
                color=0x000000,
                description="No whitelisted users found."
            )
            return await ctx.send(embed=embed)

        await self.db.execute("DELETE FROM whitelisted_users WHERE guild_id = ?", (ctx.guild.id,))
        await self.db.commit()
        embed = discord.Embed(title="✅ Success",
            color=0x000000,
            description=f"Removed all whitelisted members from {ctx.guild.name}"
        )
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
from utils.Tools import *

class ShowRules(discord.ui.View):
    def __init__(self, author, selected_events):
        super().__init__(timeout=60)
        self.author = author
        self.selected_events = selected_events

    @discord.ui.button(label="Show Rules", style=discord.ButtonStyle.secondary)
    async def show_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
            return

        rules = {
            "Anti NSFW link": "__**Anti NSFW Link**__:\n• Takes action if the message contains a NSFW link.\n• Default punishment: Block message (unchangeable)",
            "Anti caps": "__**Anti Caps**__:\n• Takes action if the message contains >70% caps.\n• Messages under 45 characters are bypassed\n• Default punishment: Mute (1 minutes)",
            "Anti link": "__**Anti Link**__:\n• Takes action if the message contains a link.\n• Server invites, Spotify Music and GIF links are bypassed\n• Default punishment: Mute (7 minutes)",
            "Anti invites": "__**Anti Invites**__:\n• Takes action if the message contains a Discord server invite.\n• Invites from the current server are bypassed\n• Default punishment: Mute (12 minutes)",
            "Anti emoji spam": "__**Anti Emoji Spam**__:\n• Takes action if a message contains more than 5 emojis.\n• Default punishment: Mute (1 minute)",
            "Anti mass mention": "__**Anti Mass Mention**__:\n• Takes action if a message contains more than 4 mentions.\n• Default punishment: Mute (3 minutes)",
            "Anti spam": "__**Anti Spam**__:\n• Takes action if more than 5 messages are sent rapidly in a short time.\n• Default punishment: Mute (12 minutes)",
        }

        enabled_rules = "\n\n".join([rules[event] for event in self.selected_events])

        embed = discord.Embed(title="Enabled Automod Rules", description=enabled_rules, color=0xff0000)
        embed.set_footer(text="Punishment type of each event is changeable except for Anti NSFW.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        

class ConfirmDisable(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=30)
        self.author = author
        self.value = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
            return
        self.value = True
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
            return
        self.value = False
        self.stop()


        
class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.default_punishment = "Mute"
        self.bot.loop.create_task(self.init_db())

    async def get_exempt_roles_channels(self, guild_id):
        async with aiosqlite.connect("db/automod.db") as db:
            roles_cursor = await db.execute("SELECT id FROM automod_ignored WHERE guild_id = ? AND type = 'role'", (guild_id,))
            channels_cursor = await db.execute("SELECT id FROM automod_ignored WHERE guild_id = ? AND type = 'channel'", (guild_id,))
            
            exempt_roles = [discord.Object(id) for (id,) in await roles_cursor.fetchall()]
            exempt_channels = [discord.Object(id) for (id,) in await channels_cursor.fetchall()]
            
            return exempt_roles, exempt_channels
            

    async def is_automod_enabled(self, guild_id):
        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT enabled FROM automod WHERE guild_id = ?", (guild_id,))
            result = await cursor.fetchone()
            return result is not None and result[0] == 1

    async def update_punishments(self, guild_id, event, punishment):
        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("INSERT OR REPLACE INTO automod_punishments (guild_id, event, punishment) VALUES (?, ?, ?)", (guild_id, event, punishment))
            await db.commit()

    async def get_current_punishments(self, guild_id):
        async with aiosqlite.connect("db/automod.db") as db:
            async with db.execute(
                "SELECT event, punishment FROM automod_punishments WHERE guild_id = ? AND event != 'Anti NSFW link'", 
                (guild_id,)
            ) as cursor:
                return await cursor.fetchall()

    async def is_anti_nsfw_enabled(self, guild_id):
        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT punishment FROM automod_punishments WHERE guild_id = ? AND event = 'Anti NSFW link'", (guild_id,))
            result = await cursor.fetchone()
            return result is not None

                

    async def init_db(self):
        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod (
                    guild_id INTEGER PRIMARY KEY,
                    enabled INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod_punishments (
                    guild_id INTEGER,
                    event TEXT,
                    punishment TEXT,
                    PRIMARY KEY (guild_id, event)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod_ignored (
                    guild_id INTEGER,
                    type TEXT,
                    id INTEGER,
                    PRIMARY KEY (guild_id, type, id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod_logging (
                    guild_id INTEGER,
                    log_channel INTEGER,
                    PRIMARY KEY (guild_id)
                )
            """)
            await db.commit()

    @commands.hybrid_group(invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def automod(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @automod.command(name="enable", help="Enable Automod on the server.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_guild=True)
    async def enable(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        if await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"**🚫 Your Server already has Automoderation Enabled.**\n\nCurrent Status: ✅ Enabled\nTo Disable use `{ctx.prefix}automod disable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        events = [
            "Anti spam",
            "Anti caps",
            "Anti link",
            "Anti invites",
            "Anti mass mention",
            "Anti emoji spam",
            "Anti NSFW link",
        ]

        embed = discord.Embed(title=f"{ctx.guild.name}'s Automod Setup", color=0x000000)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.description = "\n".join([f"❌✅ : {event}" for event in events])

        select_menu = discord.ui.Select(placeholder="Select events to enable", min_values=1, max_values=len(events), options=[
            discord.SelectOption(label=event, value=event) for event in events
        ])

        async def select_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not allowed to interact with this menu.", ephemeral=True)
                return
            selected_events = select_menu.values
            await self.enable_automod(ctx, guild_id, selected_events, interaction)
        select_menu.callback = select_callback

        enable_all_button = discord.ui.Button(label="Enable for All Events", style=discord.ButtonStyle.primary)

        async def enable_all_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
                return
                
            await self.enable_automod(ctx, guild_id, events, interaction)

        enable_all_button.callback = enable_all_callback

        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger)

        async def cancel_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
                return
                
            select_menu.disabled = True
            enable_all_button.disabled = True
            cancel_button.disabled = True
            await interaction.response.edit_message(content="Automod Setup Cancelled", embed=embed, view=view)

        cancel_button.callback = cancel_callback

        view = discord.ui.View()
        view.add_item(select_menu)
        view.add_item(enable_all_button)
        view.add_item(cancel_button)

        await ctx.send(embed=embed, view=view)
        

    async def enable_automod(self, ctx, guild_id, selected_events, interaction):

        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("INSERT OR REPLACE INTO automod (guild_id, enabled) VALUES (?, 1)", (guild_id,))
            for event in selected_events:
                await db.execute("INSERT OR REPLACE INTO automod_punishments (guild_id, event, punishment) VALUES (?, ?, ?)", (guild_id, event, self.default_punishment))
            await db.commit()

        
        if "Anti NSFW link" in selected_events:
            exempt_roles, exempt_channels = await self.get_exempt_roles_channels(guild_id)
            nsfw_keywords = ["porn", "xxx", "adult", "sex", "nsfw", "xnxx", "onlyfans", "brazzers", "xhamster", "xvideos", "pornhub", "redtube", "livejasmin", "youporn" , "tube8", "pornhat", "swxvid", "ixxx", "pornhat"]

            try:
                await interaction.guild.create_automod_rule(
                    name="Anti NSFW Links",
                    event_type=discord.AutoModRuleEventType.message_send,
                    trigger=discord.AutoModTrigger(
                        type=discord.AutoModRuleTriggerType.keyword,
                        keyword_filter=nsfw_keywords,
                    ),
                    actions=[
                        discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message),
                    ],
                    enabled=True,
                    exempt_roles=exempt_roles,
                    exempt_channels=exempt_channels,
                    reason="Automod - Anti NSFW Link setup"
                )
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                print(f"Automod rule-create error: {e}")

        embed = discord.Embed(title="Automod Enabled Successfully", color=0x000000)
        embed.description = "\n".join([f"❌✅ : {event}" for event in selected_events] +
                                       [f"❌✅ : {event}" for event in ["Anti spam", "Anti caps", "Anti link", "Anti invites", "Anti mass mention", "Anti emoji spam", "Anti NSFW link"] if event not in selected_events])

        enable_logging_button = discord.ui.Button(label="Enable Automod Logging", style=discord.ButtonStyle.success)

        async def enable_logging_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not allowed to interact with this button.", ephemeral=True)
                return

            if not interaction.guild.me.guild_permissions.manage_channels:
                await interaction.response.send_message("I do not have permission to create channels.", ephemeral=True)
                return

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True)
            }

            try:
                for channel in interaction.guild.channels:
                    if channel.name == "olympus-automod":
                        await interaction.response.send_message(f"A logging channel with the name \"olympus-automod\" already exists.", ephemeral=True)
                        return
                log_channel = await interaction.guild.create_text_channel("olympus-automod", overwrites=overwrites)
                guild_id = interaction.guild.id

                async with aiosqlite.connect("db/automod.db") as db:
                    await db.execute("INSERT OR REPLACE INTO automod_logging (guild_id, log_channel) VALUES (?, ?)", (guild_id, log_channel.id))
                    await db.commit()

                await interaction.response.send_message(f"Logging channel {log_channel.mention} created and set successfully.", ephemeral=True)

            except discord.HTTPException as e:
                await interaction.response.send_message(f"Failed to create logging channel: {e}", ephemeral=True)

        enable_logging_button.callback = enable_logging_callback


        view = ShowRules(ctx.author, selected_events)
        view.add_item(enable_logging_button)

        
        await interaction.response.edit_message(content="Setup Completed.", embed=embed, view=view)


    

    @automod.command(name="punishment", aliases=["punish"], help="Set the punishment for automod events.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def punishment(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: ❌ Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        current_punishments = await self.get_current_punishments(guild_id)
        embed = discord.Embed(title=f"Current Automod Punishments for {ctx.guild.name}", color=0x000000)
        punishment_map = {}
        for event, punishment in current_punishments:
            punishment_map[event] = punishment or "None"
            embed.add_field(name=event, value=punishment or "None", inline=False)
            embed.set_footer(text="Keep the default punishment (Mute) to prevent server raids without kicking or banning raiders", icon_url=self.bot.user.avatar.url)
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        events = [event for event, _ in current_punishments]
        select = discord.ui.Select(placeholder="Select events to update punishment", options=[
            discord.SelectOption(label=event) for event in events
        ], min_values=1, max_values=len(events))

        async def select_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
                return

            selected_events = select.values
            await interaction.response.send_message("You selected: " + ", ".join(selected_events))

            punishment_buttons = discord.ui.View()
            for punishment in ["Mute", "Kick", "Ban"]:
                button = discord.ui.Button(label=punishment, style=discord.ButtonStyle.danger)

                async def punishment_callback(button_interaction, selected_events=selected_events, punishment=punishment):
                    if button_interaction.user != ctx.author:
                        await button_interaction.response.send_message("You cannot interact with this button.", ephemeral=True)
                        return

                    
                    for event in selected_events:
                        await self.update_punishments(guild_id, event, punishment)

                    updated_punishments = await self.get_current_punishments(guild_id)
                    updated_embed = discord.Embed(title=f"Updated Automod Punishments for {ctx.guild.name}", color=0x000000)
                    for event, punishment in updated_punishments:
                        updated_embed.add_field(name=event, value=punishment or "None", inline=False)
                        updated_embed.set_footer(text="You can modify the punishments by running the command again.", icon_url=self.bot.user.avatar.url)
                        updated_embed.set_thumbnail(url=self.bot.user.avatar.url)

                    
                    await button_interaction.response.edit_message(embed=updated_embed, view=None)

                button.callback = punishment_callback
                punishment_buttons.add_item(button)

            await interaction.edit_original_response(view=punishment_buttons)

        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)

        await ctx.send(embed=embed, view=view)




    @automod.group(name="ignore", aliases=["exempt", "whitelist", "wl"], help="Manage whitelisted roles and channels for Automod.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def ignore(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)
            

    @ignore.command(name="channel", help="Add a channel to the whitelist.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ignore_channel(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: ❌ Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT 1 FROM automod_ignored WHERE guild_id = ? AND type = 'channel' AND id = ?", (guild_id, channel.id))
            if await cursor.fetchone() is not None:
                embed = discord.Embed(title="__Channel Already Whitelisted!__", description=f"🚫 The channel {channel.mention} is already in the ignore list.\n\n➜ Use **{ctx.prefix}automod unignore channel {channel.mention}** to remove it.", color=0x000000)
                
                embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                await ctx.send(embed=embed)
                return
                
            count_cursor = await db.execute("SELECT COUNT(*) FROM automod_ignored WHERE guild_id = ? AND type = 'channel'", (guild_id,))
            count = await count_cursor.fetchone()

            if count[0] >= 10:
                await ctx.send("You can only ignore up to 10 channels.")
                return

            await db.execute("INSERT OR REPLACE INTO automod_ignored (guild_id, type, id) VALUES (?, 'channel', ?)", (guild_id, channel.id))
            await db.commit()
            
            if await self.is_anti_nsfw_enabled(guild_id):
                try:
                    rules = await ctx.guild.fetch_automod_rules()
                    for rule in rules:
                        if rule.name == "Anti NSFW Links":
                            exempt_channels = list(rule.exempt_channels)  
                            exempt_channels.append(channel) 
                            await rule.edit(
                                exempt_channels=exempt_channels,
                                reason="Channel exempted from Anti NSFW Links via automod ignore command"
                            )
                            break
                except discord.HTTPException:
                    pass

                    
            success = discord.Embed(title="✅ Channel Whitelisted", description=f"The channel {channel.mention} has been added to the ignore list \n\n➜ Use `{ctx.prefix}automod ignore show` to view the ignore list.", color=0x000000)
            success.set_thumbnail(url=self.bot.user.avatar.url)
            success.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)

        await ctx.send(embed=success)

    @ignore.command(name="role", help="Add a role to the whitelist.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ignore_role(self, ctx, role: discord.Role):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: ❌ Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT 1 FROM automod_ignored WHERE guild_id = ? AND type = 'role' AND id = ?", (guild_id, role.id))
            
            if await cursor.fetchone() is not None:
                embed = discord.Embed(title="__Role Already Whitelisted!__", description=f"🚫 The role {role.mention} is already in the ignore list.\n\n➜ Use **{ctx.prefix}automod unignore role {role.mention}** to remove it.", color=0x000000)
                embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                await ctx.send(embed=embed)
                return
                
            count_cursor = await db.execute("SELECT COUNT(*) FROM automod_ignored WHERE guild_id = ? AND type = 'role'", (guild_id,))
            count = await count_cursor.fetchone()


            if count[0] >= 10:
                await ctx.send("You can only ignore up to 10 roles.")
                return

            await db.execute("INSERT OR REPLACE INTO automod_ignored (guild_id, type, id) VALUES (?, 'role', ?)", (guild_id, role.id))
            await db.commit()

            if await self.is_anti_nsfw_enabled(guild_id):
                try:
                    rules = await ctx.guild.fetch_automod_rules()
                    for rule in rules:
                        if rule.name == "Anti NSFW Links":
                            exempt_roles = list(rule.exempt_roles)  
                            exempt_roles.append(role) 
                            await rule.edit(
                                exempt_roles=exempt_roles,
                                reason="Role exempted from Anti NSFW Links via automod ignore command"
                            )
                            break
                except discord.HTTPException:
                    pass
                    
                    
            success = discord.Embed(title="✅ Role Whitelisted", description=f"The role {role.mention} has been added to the ignore list \n\n➜ Use `{ctx.prefix}automod ignore show` to view the ignore list.", color=0x000000)
            success.set_thumbnail(url=self.bot.user.avatar.url)
            success.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)

        await ctx.send(embed=success)

    @ignore.command(name="show", aliases=["view", "list", "config"], help="Show the whitelisted roles and channels.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ignore_show(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: ❌ Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            

        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT type, id FROM automod_ignored WHERE guild_id = ?", (guild_id,))
            ignored_items = await cursor.fetchall()

        if not ignored_items:
            await ctx.reply("No ignored channels or roles found.")
            return

        ignored_channels = []
        ignored_roles = []

        for item_type, item_id in ignored_items:
            if item_type == "channel":
                channel = ctx.guild.get_channel(item_id)
                if channel:
                    ignored_channels.append(f"{channel.mention} (ID: {channel.id})")
                else:
                    ignored_channels.append(f"Deleted Channel (ID: {item_id})")
            elif item_type == "role":
                role = ctx.guild.get_role(item_id)
                if role:
                    ignored_roles.append(f"{role.mention} (ID: {role.id})")
                else:
                    ignored_roles.append(f"Deleted Role (ID: {item_id})")

        embed = discord.Embed(title="Ignored Channels & Roles for Automod", color=0x000000)

        if ignored_channels:
            embed.add_field(name="__Ignored Channels:__", value="\n".join(ignored_channels), inline=False)
        else:
            embed.add_field(name="__Ignored Channels:__", value="None", inline=False)

        if ignored_roles:
            embed.add_field(name="__Ignored Roles:__", value="\n".join(ignored_roles), inline=False)
        else:
            embed.add_field(name="__Ignored Roles:__", value="None", inline=False)

        await ctx.send(embed=embed)


    @ignore.command(name="reset", help="Reset the whitelist.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ignore_reset(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: ❌ Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("DELETE FROM automod_ignored WHERE guild_id = ?", (guild_id,))
            await db.commit()
        embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"** ✅ | All ignored channels and roles have been reset!**\n\nTo view current Automod settings use `{ctx.prefix}automod config`", color=0x000000)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=embed)
        

    @automod.group(name="unignore", aliases=["unwhitelist", "unwl"], invoke_without_command=True, help="Remove channels and roles from the whitelist.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unignore(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @unignore.command(name="channel", help="Remove a channel from the whitelist.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def unignore_channel(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: ❌ Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if await self.is_anti_nsfw_enabled(guild_id):
            try:
                rules = await ctx.guild.fetch_automod_rules()
                for rule in rules:
                    if rule.name == "Anti NSFW Links":
                        exempt_channels = list(rule.exempt_channels)  
                        exempt_channels = [ch for ch in exempt_channels if ch.id != channel.id]
                        await rule.edit(
                            exempt_channels=exempt_channels,
                            reason="Channel removed from Anti NSFW Links exemption via automod unignore command"
                        )
                        break
            except discord.HTTPException:
                pass
        
        async with aiosqlite.connect("db/automod.db") as db:
            result = await db.execute("DELETE FROM automod_ignored WHERE guild_id = ? AND type = 'channel' AND id = ?", (guild_id, channel.id))
            await db.commit()

        if result.rowcount > 0:
            embed = discord.Embed(title="✅ Success", description=f"{channel.mention} has been removed from the automod ignore list.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="❌ Error", description=f"{channel.mention} is not in the automod ignore list.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            

    @unignore.command(name="role", help="Remove a role from the whitelist.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def unignore_role(self, ctx, role: discord.Role):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: ❌ Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        if await self.is_anti_nsfw_enabled(guild_id):
            try:
                rules = await ctx.guild.fetch_automod_rules()
                for rule in rules:
                    if rule.name == "Anti NSFW Links":
                        exempt_roles = list(rule.exempt_roles)  
                        exempt_roles = [ch for ch in exempt_roles if ch.id != role.id]
                        await rule.edit(
                            exempt_roles=exempt_roles,
                            reason="Role removed from Anti NSFW Links exemption via automod unignore command"
                        )
                        break
            except discord.HTTPException:
                pass

        
        async with aiosqlite.connect("db/automod.db") as db:
            result = await db.execute("DELETE FROM automod_ignored WHERE guild_id = ? AND type = 'role' AND id = ?", (guild_id, role.id))
            await db.commit()

        if result.rowcount > 0:
            embed = discord.Embed(title="✅ Success", description=f"{role.mention} has been removed from the automod ignore list.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="❌ Error", description=f"{role.mention} is not in the automod ignore list.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
    

    @automod.command(name="disable", help="Disable Automod in the server.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: ❌ Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="Disable Automod Confirmation",
            description="**Are you sure you want to disable Automod?**\n\nThis will remove all custom event settings, punishments, ignored roles/channels, & logging channel data.",
            color=0x0000000
        )
        embed.set_footer(text="Click 'Yes' to disable Automod or 'No' to cancel.")
        embed.set_thumbnail(url=self.bot.user.avatar.url)

        view = ConfirmDisable(ctx.author)
        message = await ctx.send(embed=embed, view=view)

        await view.wait()

        if view.value is None:
            embed.title = "Automod Disable Cancelled"
            embed.description = "You took too long to respond. Automod disable process has been canceled."
            embed.color = 0x000000
            
            await message.edit(embed=embed, view=None)

        elif view.value:
            
            async with aiosqlite.connect("db/automod.db") as db:
                await db.execute("DELETE FROM automod WHERE guild_id = ?", (guild_id,))
                await db.execute("DELETE FROM automod_punishments WHERE guild_id = ?", (guild_id,))
                await db.execute("DELETE FROM automod_ignored WHERE guild_id = ?", (guild_id,))
                await db.execute("DELETE FROM automod_logging WHERE guild_id = ?", (guild_id,))
                await db.commit()

            rules = await ctx.guild.fetch_automod_rules()
            for rule in rules:
                if rule.name == "Anti NSFW Links":
                    try:
                        await rule.delete(reason="Automod disabled - removing Anti NSFW Link rule")
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass


            embed.title = "✅ Automod Disabled"
            embed.description = f"Automod has been successfully disabled for **{ctx.guild.name}.** \nAll settings, punishments, and logs have been removed.\n\nCurrent Status:❌ Disabled\n➜ To Re-enable use `{ctx.prefix}automod enable`."
            embed.color = 0x000000
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await message.edit(embed=embed, view=None)
            

        else:
            embed.title = "Automod Disable Cancelled"
            embed.description = "Automod disable process has been canceled."
            embed.color = 0x00000
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await message.edit(embed=embed, view=None)

        

    @automod.command(name="config", aliases=["settings", "show", "view"], help="View Automod settings.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def config(self, ctx):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: ❌ Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return

        current_punishments = await self.get_current_punishments(guild_id)
        embed = discord.Embed(title=f"Enabled Automod Events & their punishment type for {ctx.guild.name}", color=0x000000)
        embed.set_footer(text="Manage punishment type for events by executing “automod punishment” command.", icon_url=self.bot.user.avatar.url)

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        else:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        for event, punishment in current_punishments:
            embed.add_field(name=event, value=punishment or "None", inline=False)

        if await self.is_anti_nsfw_enabled(guild_id):
            embed.add_field(name="Anti NSFW Links", value="Block Message", inline=False)

        async with aiosqlite.connect("db/automod.db") as db:
            cursor = await db.execute("SELECT log_channel FROM automod_logging WHERE guild_id = ?", (guild_id,))
            log_channel_id = await cursor.fetchone()

        if log_channel_id and log_channel_id[0]:
            log_channel = ctx.guild.get_channel(log_channel_id[0])
            if log_channel:
                embed.add_field(name="Logging Channel", value=f"{log_channel.mention}", inline=False)
            else:
                embed.add_field(name="Logging Channel", value="Deleted Channel", inline=False)
        else:
            embed.add_field(name="Logging Channel", value="No logging channel", inline=False)

        await ctx.send(embed=embed)


    @automod.command(name="logging", help="Set the logging channel for Automod events.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def logging(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id
        if ctx.author != ctx.guild.owner and ctx.author.top_role.position < ctx.guild.me.top_role.position:
            embed = discord.Embed(title="🚫 Access Denied", description="Your top role must be at the **same** position or **higher** than my top role.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
        if not await self.is_automod_enabled(guild_id):
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"Uhh, looks like your server hasn't enabled Automoderation.\n\nCurrent Status: ❌ Disabled\nTo Enable use `{ctx.prefix}automod enable`", color=0x000000)
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=embed)
            return
            
        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("INSERT OR REPLACE INTO automod_logging (guild_id, log_channel) VALUES (?, ?)", (guild_id, channel.id))
            await db.commit()
            embed=discord.Embed(title=f"Automod Settings for {ctx.guild.name}", description=f"**✅ | Automoderation Logging channel set to {channel.mention}.**\n\n➜ Use `{ctx.prefix}automod config` to view current Automod settings.", color=0x000000)
            embed.set_footer(text=f"“{ctx.command.qualified_name}” Command executed by {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        guild_id = guild.id

        async with aiosqlite.connect("db/automod.db") as db:
            await db.execute("DELETE FROM automod WHERE guild_id = ?", (guild_id,))
            await db.execute("DELETE FROM automod_punishments WHERE guild_id = ?", (guild_id,))
            await db.execute("DELETE FROM automod_ignored WHERE guild_id = ?", (guild_id,))
            await db.execute("DELETE FROM automod_logging WHERE guild_id = ?", (guild_id,))
            await db.commit()

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
import aiosqlite
import re
from utils.Tools import *

class AutoReaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'db/autoreact.db'
        self.bot.loop.create_task(self.setup_database())

    async def setup_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS autoreact (
                    guild_id INTEGER,
                    trigger TEXT,
                    emojis TEXT
                )
            """)
            await db.commit()

    async def get_triggers(self, guild_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT trigger, emojis FROM autoreact WHERE guild_id = ?", (guild_id,))
            return await cursor.fetchall()

    async def trigger_exists(self, guild_id, trigger):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT 1 FROM autoreact WHERE guild_id = ? AND trigger = ?", (guild_id, trigger))
            return await cursor.fetchone()

    @commands.group(name="react", aliases=["autoreact"], help="Lists all subcommands of autoreact group.", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def react(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @react.command(name="add", aliases=["set", "create"], help="Adds a trigger and its emojis to the autoreact.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def add(self, ctx, trigger: str, *, emojis: str):
        if len(trigger.split()) > 1:
            embed = discord.Embed(
                title="❌ Invalid Trigger",
                description="Triggers can only be one word.",
                color=0x000000
            )
            embed.set_footer(text=f"Requested By {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            return await ctx.reply(embed=embed)

        
        emoji_list = re.findall(r"<a?:\w+:\d+>|[\u263a-\U0001f645]", emojis)
        if len(emoji_list) > 10:
            embed = discord.Embed(
                title="❌ Too Many Emojis",
                description="You can only set up to **10** emojis per trigger.",
                color=0x000000
            )
            embed.set_footer(text=f"Requested By {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            return await ctx.reply(embed=embed)

        triggers = await self.get_triggers(ctx.guild.id)
        if len(triggers) >= 10:
            embed = discord.Embed(
                title="🔔 Trigger Limit Reached",
                description="You can only set up to 10 triggers for auto-reactions in this guild.",
                color=0x000000
            )
            embed.set_footer(text=f"Requested By {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            return await ctx.reply(embed=embed)

        if await self.trigger_exists(ctx.guild.id, trigger):
            embed = discord.Embed(
                title="🔔 Trigger Exists",
                description=f"The trigger '{trigger}' already exists. Remove it before adding it again.",
                color=0x000000
            )
            embed.set_footer(text=f"Requested By {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            return await ctx.reply(embed=embed)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO autoreact (guild_id, trigger, emojis) VALUES (?, ?, ?)", 
                             (ctx.guild.id, trigger, " ".join(emoji_list)))
            await db.commit()

        embed = discord.Embed(
            title="✅ Trigger Added",
            description=f"Successfully added trigger '{trigger}' with emojis {', '.join(emoji_list)}.",
            color=0x000000
        )
        embed.set_footer(text=f"Requested By {ctx.author}",
               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.reply(embed=embed)

    @react.command(name="remove", aliases=["clear", "delete"], help="Removes a trigger and its emojis from the autoreact.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx, trigger: str):
        if not await self.trigger_exists(ctx.guild.id, trigger):
            embed = discord.Embed(
                title="❌ Trigger Not Found",
                description=f"The trigger '{trigger}' does not exist.",
                color=0x000000
            )
            embed.set_footer(text=f"Requested By {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            return await ctx.reply(embed=embed)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM autoreact WHERE guild_id = ? AND trigger = ?", (ctx.guild.id, trigger))
            await db.commit()

        embed = discord.Embed(
            title="✅ Trigger Removed",
            description=f"Successfully removed trigger '{trigger}'.",
            color=0x000000
        )
        embed.set_footer(text=f"Requested By {ctx.author}",
               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.reply(embed=embed)

    @react.command(name="list", aliases=["show", "config"], help="Lists all the triggers and their emojis in the autoreact module.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def list(self, ctx):
        triggers = await self.get_triggers(ctx.guild.id)
        if not triggers:
            embed = discord.Embed(
                title="No Triggers Set",
                description="There are no auto-reaction triggers set in this guild.",
                color=0x000000
            )
            return await ctx.reply(embed=embed)

        trigger_list = "\n".join([f"{t[0]}: {t[1]}" for t in triggers])
        embed = discord.Embed(
            title="Auto-Reaction Triggers",
            description=trigger_list,
            color=0x000000
        )
        embed.set_footer(text=f"Requested By {ctx.author}",
               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.reply(embed=embed)

    @react.command(name="reset", help="Resets all the triggers and their emojis in the autoreact module.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def reset(self, ctx):
        triggers = await self.get_triggers(ctx.guild.id)
        if not triggers:
            embed = discord.Embed(
                title="❌ No Triggers Set",
                description="There are no auto-reaction triggers set to reset.",
                color=0x000000
            )
            embed.set_footer(text=f"Requested By {ctx.author}",
                   icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            return await ctx.reply(embed=embed)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM autoreact WHERE guild_id = ?", (ctx.guild.id,))
            await db.commit()

        embed = discord.Embed(
            title="✅ All Triggers Reset",
            description="Successfully removed all auto-reaction triggers.",
            color=0x000000
        )
        embed.set_footer(text=f"Requested By {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(AutoReaction(bot))

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out support or DM me.
"""
import discord
from discord.ext import commands
import aiosqlite
import os
from utils.Tools import *


DB_PATH = "db/autoresponder.db"

class AutoResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        if not os.path.exists(os.path.dirname(DB_PATH)):
            os.makedirs(os.path.dirname(DB_PATH))
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS autoresponses (
                    guild_id INTEGER,
                    name TEXT,
                    message TEXT,
                    PRIMARY KEY (guild_id, name)
                )
            ''')
            await db.commit()

    @commands.group(name="autoresponder", invoke_without_command=True, aliases=['ar'], help="Manage autoresponders in the server.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _ar(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @_ar.command(name="create", help="Create a new autoresponder.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def _create(self, ctx, name, *, message):
        name_lower = name.lower()
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM autoresponses WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                count = (await cursor.fetchone())[0]
                if count >= 20:
                    return await ctx.reply(embed=discord.Embed(title="❌ Error!",
                        description=f"You can't add more than 20 autoresponses in {ctx.guild.name}",
                        color=0x000000
                    ))

            async with db.execute("SELECT 1 FROM autoresponses WHERE guild_id = ? AND LOWER(name) = ?", (ctx.guild.id, name_lower)) as cursor:
                if await cursor.fetchone():
                    return await ctx.reply(embed=discord.Embed(title="❌ Error!",
                        description=f"The autoresponse with the name `{name}` already exists in {ctx.guild.name}",
                        color=0x000000
                    ))

            await db.execute("INSERT INTO autoresponses (guild_id, name, message) VALUES (?, ?, ?)", (ctx.guild.id, name_lower, message))
            await db.commit()
            await ctx.reply(embed=discord.Embed(title="✅ Success",
                description=f"Created autoresponder `{name}` in {ctx.guild.name}",
                color=0x000000
            ))

    @_ar.command(name="delete", help="Delete an existing autoresponder.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def _delete(self, ctx, name):
        name_lower = name.lower()
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM autoresponses WHERE guild_id = ? AND LOWER(name) = ?", (ctx.guild.id, name_lower)) as cursor:
                if not await cursor.fetchone():
                    return await ctx.reply(embed=discord.Embed(title="❌ Error!",
                        description=f"No autoresponder found with the name `{name}` in {ctx.guild.name}",
                        color=0x000000
                    ))

            await db.execute("DELETE FROM autoresponses WHERE guild_id = ? AND LOWER(name) = ?", (ctx.guild.id, name_lower))
            await db.commit()
            await ctx.reply(embed=discord.Embed(title="✅ Success",
                description=f"Deleted autoresponder `{name}` in {ctx.guild.name}",
                color=0x000000
            ))

    @_ar.command(name="edit", help="Edit an existing autoresponder.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def _edit(self, ctx, name, *, message):
        name_lower = name.lower()
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM autoresponses WHERE guild_id = ? AND LOWER(name) = ?", (ctx.guild.id, name_lower)) as cursor:
                if not await cursor.fetchone():
                    return await ctx.reply(embed=discord.Embed(title="❌ Error!",
                        description=f"No autoresponder found with the name `{name}` in {ctx.guild.name}",
                        color=0x000000
                    ))

            await db.execute("UPDATE autoresponses SET message = ? WHERE guild_id = ? AND LOWER(name) = ?", (message, ctx.guild.id, name_lower))
            await db.commit()
            await ctx.reply(embed=discord.Embed(title="✅ Success",
                description=f"Edited autoresponder `{name}` in {ctx.guild.name}",
                color=0x000000
            ))

    @_ar.command(name="config", help="List all autoresponders in the server.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def _config(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT name FROM autoresponses WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                autoresponses = await cursor.fetchall()

        if not autoresponses:
            return await ctx.reply(embed=discord.Embed(
                description=f"🔔 | There are no autoresponders in {ctx.guild.name}",
                color=0x000000
            ))

        embed = discord.Embed(color=0x000000, title=f"Autoresponders in {ctx.guild.name}")
        for i, (name,) in enumerate(autoresponses, start=1):
            embed.add_field(name=f"Autoresponder [{i}]", value=name, inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT message FROM autoresponses WHERE guild_id = ? AND LOWER(name) = ?", (message.guild.id, message.content.lower())) as cursor:
                row = await cursor.fetchone()

        if row:
            await message.channel.send(row[0])

async def setup(bot):
    await bot.add_cog(AutoResponder(bot))



"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out support or DM me.
"""
from __future__ import annotations
import discord
import aiosqlite
import logging
from discord.ext import commands
from typing import List, Dict
from utils.Tools import *

logging.basicConfig(
    level=logging.INFO,
    format="\x1b[38;5;197m[\x1b[0m%(asctime)s\x1b[38;5;197m]\x1b[0m -> \x1b[38;5;197m%(message)s\x1b[0m",
    datefmt="%H:%M:%S",
)

DATABASE_PATH = 'db/autorole.db'

class BasicView(discord.ui.View):
    def __init__(self, ctx: commands.Context, timeout=60):
        super().__init__(timeout=timeout)
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id and interaction.user.id not in [246469891761111051]:
            await interaction.response.send_message("Uh oh! That message doesn't belong to you.\nYou must run this command to interact with it.", ephemeral=True)
            return False
        return True


class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.create_table())
        self.color = 0x000000

    async def create_table(self):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS autorole (
                guild_id INTEGER PRIMARY KEY,
                bots TEXT NOT NULL,
                humans TEXT NOT NULL
            )
            """)
            await db.commit()

    async def get_autorole(self, guild_id: int) -> Dict[str, List[int]]:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT bots, humans FROM autorole WHERE guild_id = ?", (guild_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    bots, humans = row
                    
                    bots = [int(role_id) for role_id in bots.replace('[', '').replace(']', '').replace(' ', '').split(',') if role_id]
                    humans = [int(role_id) for role_id in humans.replace('[', '').replace(']', '').replace(' ', '').split(',') if role_id]
                      
                    return {"bots": bots, "humans": humans}
                else:
                    return {"bots": [], "humans": []}

    

    async def update_autorole(self, guild_id: int, data: Dict[str, List[int]]):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            bots = ','.join(map(str, data['bots']))
            humans = ','.join(map(str, data['humans']))
            
            await db.execute("INSERT OR REPLACE INTO autorole (guild_id, bots, humans) VALUES (?, ?, ?)",
                             (guild_id, bots, humans))
            await db.commit()


        
                
    @commands.group(name="autorole", invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _autorole(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)
            

    @_autorole.command(name="config", help="Shows the current autorole configuration")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def _ar_config(self, ctx):
        
        data = await self.get_autorole(ctx.guild.id)
        if data:
            fetched_humans = [ctx.guild.get_role(role_id) for role_id in data["humans"] if ctx.guild.get_role(role_id)]
            fetched_bots = [ctx.guild.get_role(role_id) for role_id in data["bots"] if ctx.guild.get_role(role_id)]

            hums = "\n".join(role.mention for role in fetched_humans) or "None"
            bos = "\n".join(role.mention for role in fetched_bots) or "None"

            emb = discord.Embed(color=self.color, title=f"Autorole Configuration for {ctx.guild.name}")
            emb.add_field(name="• __Humans__", value=hums, inline=False)
            emb.add_field(name="• __Bots__", value=bos, inline=False)

            await ctx.send(embed=emb)
        else:
            emb = discord.Embed(color=self.color, description="No autorole configuration found in this Guild.")
            await ctx.reply(embed=emb)



    @_autorole.group(name="reset", help="Clear autorole config in the Guild")
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def _autorole_reset(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @_autorole_reset.command(name="humans", help="Clear autorole configuration for humans")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def _autorole_humans_reset(self, ctx):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT humans FROM autorole WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                data = await cursor.fetchone()

        if data and data[0]:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute("UPDATE autorole SET humans = ? WHERE guild_id = ?", ('[]', ctx.guild.id))
                await db.commit()
            embed = discord.Embed(title="✅ Success",
                                  description="Cleared all human autoroles in this Guild.",
                                  color=self.color)
        else:
            embed = discord.Embed(title="❌ Error",
                                  description="No Autoroles set for humans in this Guild.",
                                  color=self.color)

        await ctx.reply(embed=embed)

    @_autorole_reset.command(name="bots", help="Clear autorole configuration for bots")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def _autorole_bots_reset(self, ctx):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT bots FROM autorole WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                data = await cursor.fetchone()

        if data and data[0]:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute("UPDATE autorole SET bots = ? WHERE guild_id = ?", ('[]', ctx.guild.id))
                await db.commit()
            embed = discord.Embed(title="✅ Success",
                                  description="Cleared all bot autoroles in this Guild.",
                                  color=self.color)
        else:
            embed = discord.Embed(title="❌ Error",
                                  description="No Autoroles set for Bots in this Guild.",
                                  color=self.color)

        await ctx.reply(embed=embed)

    @_autorole_reset.command(name="all", help="Clear all autorole configuration in the Guild")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _autorole_reset_all(self, ctx):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT humans, bots FROM autorole WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                data = await cursor.fetchone()

        if data and (data[0] or data[1]):
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute("UPDATE autorole SET humans = ?, bots = ? WHERE guild_id = ?", ('[]', '[]', ctx.guild.id))
                await db.commit()
            embed = discord.Embed(title="✅ Success",
                                  description="Cleared all autoroles in this Gudild.",
                                  color=self.color)
        else:
            embed = discord.Embed(title="❌ Error",
                  description="No Autoroles set in this Guild.",
                  color=self.color)

        await ctx.reply(embed=embed)

    @_autorole.group(name="humans", help="Setup autoroles for human")
    @blacklist_check()
    @ignore_check()
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _autorole_humans(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @_autorole_humans.command(name="add", help="Add role to list of human Autoroles.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _autorole_humans_add(self, ctx, *, role: discord.Role):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT humans FROM autorole WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                data = await cursor.fetchone()
        
        if data:
            humans = eval(data[0])
            if role.id in humans:
                embed = discord.Embed(title="🔔 Access Denied",
                                    description=f"{role.mention} is already in human autoroles.",
                                    color=self.color)
            elif len(humans) >= 10:
                embed = discord.Embed(title="🔔 Access Denied",
                                    description="You can only add upto 10 human autoroles.",
                                    color=self.color)
            else:
                humans.append(role.id)
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    await db.execute("UPDATE autorole SET humans = ? WHERE guild_id = ?", (str(humans), ctx.guild.id))
                    await db.commit()
                embed = discord.Embed(title="✅ Success",
                                    description=f"{role.mention} has been added to human autoroles.",
                                    color=self.color)
        else:
            humans = [role.id]
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute("INSERT INTO autorole (guild_id, humans, bots) VALUES (?, ?, ?)", (ctx.guild.id, str(humans), '[]'))
                await db.commit()
            embed = discord.Embed(title="✅ Success",
                                  description=f"{role.mention} has been added to human autoroles.",
                                  color=self.color)

        await ctx.reply(embed=embed)

    @_autorole_humans.command(name="remove", help="Remove a role from human Autoroles.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _autorole_humans_remove(self, ctx, *, role: discord.Role):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT humans FROM autorole WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                data = await cursor.fetchone()

        if data:
            humans = eval(data[0])
            if role.id not in humans:
                embed = discord.Embed(title="❌ Error",
                                    description=f"{role.mention} is not in human autoroles.",
                                    color=self.color)
            else:
                humans.remove(role.id)
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    await db.execute("UPDATE autorole SET humans = ? WHERE guild_id = ?", (str(humans), ctx.guild.id))
                    await db.commit()
                embed = discord.Embed(title="✅ Success",
                                    description=f"{role.mention} has been removed from human autoroles.",
                                    color=self.color)
        else:
            embed = discord.Embed(title="❌ Error",
                                  description=f"No Autoroles set in this guild for humans.",
                                  color=self.color)

        await ctx.reply(embed=embed)

    @_autorole.group(name="bots", help="Setup autoroles for bots")
    @blacklist_check()
    @ignore_check()
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _autorole_bots(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @_autorole_bots.command(name="add", help="Add role to bot Autoroles.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _autorole_bots_add(self, ctx, *, role: discord.Role):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT bots FROM autorole WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                data = await cursor.fetchone()
        
        if data:
            bots = eval(data[0])
            if role.id in bots:
                embed = discord.Embed(title="🔔 Access Denied",
                                      description=f"{role.mention} is already in bot autoroles.",
                                      color=self.color)
            elif len(bots) >= 10:
                embed = discord.Embed(title="🔔 Access Denied",
                                    description="You can only add upto 10 bot autoroles",
                                    color=self.color)
            else:
                bots.append(role.id)
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    await db.execute("UPDATE autorole SET bots = ? WHERE guild_id = ?", (str(bots), ctx.guild.id))
                    await db.commit()
                embed = discord.Embed(title="✅ Success",
                                    description=f"{role.mention} has been added to bot autoroles.",
                                    color=self.color)
        else:
            bots = [role.id]
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute("INSERT INTO autorole (guild_id, humans, bots) VALUES (?, ?, ?)", (ctx.guild.id, '[]', str(bots)))
                await db.commit()
            embed = discord.Embed(title="✅ Success",
                                  description=f"{role.mention} has been added to bot autoroles.",
                                color=self.color)

        await ctx.reply(embed=embed)

    @_autorole_bots.command(name="remove", help="Remove a role from bot Autoroles.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _autorole_bots_remove(self, ctx, *, role: discord.Role):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT bots FROM autorole WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                data = await cursor.fetchone()

        if data:
            bots = eval(data[0])
            if role.id not in bots:
                embed = discord.Embed(title="❌ Error",
                                      description=f"{role.mention} is not in bot autoroles.",
                                      color=self.color)
            else:
                bots.remove(role.id)
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    await db.execute("UPDATE autorole SET bots = ? WHERE guild_id = ?", (str(bots), ctx.guild.id))
                    await db.commit()
                embed = discord.Embed(title="✅ Success",
                                      description=f"{role.mention} has been removed from bot autoroles.",
                                      color=self.color)
        else:
            embed = discord.Embed(title="❌ Error",
                                  description=f"No Autoroles set in this guild for bots.",
                                  color=self.color)

        await ctx.reply(embed=embed)
        

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out support or DM me.
"""
import discord
from discord.ext import commands
import os
import random
from typing import List, Tuple, Union
from PIL import Image
from utils.Tools import *

CARDS_PATH = 'data/cards/'

class Card:
    suits = ["clubs", "diamonds", "hearts", "spades"]

    def __init__(self, suit: str, value: int, down=False):
        self.suit = suit
        self.value = value
        self.down = down
        self.symbol = self.name[0].upper()

    @property
    def name(self) -> str:
        if self.value <= 10:
            return str(self.value)
        else:
            return {
                11: 'jack',
                12: 'queen',
                13: 'king',
                14: 'ace',
            }[self.value]

    @property
    def image(self):
        return (
            f"{self.symbol if self.name != '10' else '10'}" \
            f"{self.suit[0].upper()}.png" \
            if not self.down else "red_back.png"
        )

    def flip(self):
        self.down = not self.down
        return self

    def __str__(self) -> str:
        return f'{self.name.title()} of {self.suit.title()}'

    def __repr__(self) -> str:
        return str(self)


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def hand_to_images(hand: List[Card]) -> List[Image.Image]:
        return [Image.open(os.path.join(CARDS_PATH, card.image)) for card in hand]

    @staticmethod
    def center(*hands: Tuple[Image.Image]) -> Image.Image:
        bg: Image.Image = Image.open(os.path.join(CARDS_PATH, 'table.png'))
        bg_center_x = bg.size[0] // 2
        bg_center_y = bg.size[1] // 2

        img_w = hands[0][0].size[0]
        img_h = hands[0][0].size[1]

        start_y = bg_center_y - (((len(hands) * img_h) + ((len(hands) - 1) * 15)) // 2)

        for hand in hands:
            start_x = bg_center_x - (((len(hand) * img_w) + ((len(hand) - 1) * 10)) // 2)
            for card in hand:
                bg.alpha_composite(card, (start_x, start_y))
                start_x += img_w + 10
            start_y += img_h + 15

        return bg

    def output(self, name, *hands: Tuple[List[Card]]) -> None:
        self.center(*map(self.hand_to_images, hands)).save(f'data/{name}.png')

    @staticmethod
    def calc_hand(hand: List[Card]) -> int:
        non_aces = [c for c in hand if c.symbol != 'A']
        aces = [c for c in hand if c.symbol == 'A']
        total_sum = 0
        for card in non_aces:
            if not card.down:
                if card.symbol in 'JQK':
                    total_sum += 10
                else:
                    total_sum += card.value
        for card in aces:
            if not card.down:
                if total_sum <= 10:
                    total_sum += 11
                else:
                    total_sum += 1
        return total_sum

    @commands.command(aliases=['bj', 'blackjacks'], help="Play a simple game of blackjack.", usage="blackjack")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def blackjack(self, ctx: commands.Context):
        try:
            deck = [Card(suit, num) for num in range(2, 15) for suit in Card.suits]
            random.shuffle(deck)

            player_hand: List[Card] = []
            dealer_hand: List[Card] = []

            player_hand.append(deck.pop())
            dealer_hand.append(deck.pop())
            player_hand.append(deck.pop())
            dealer_hand.append(deck.pop())

            dealer_hand[1] = dealer_hand[1].flip() 

            player_score = self.calc_hand(player_hand)
            dealer_score = self.calc_hand(dealer_hand)

            async def out_table(**kwargs) -> discord.Message:
                self.output(ctx.author.id, dealer_hand, player_hand)
                embed = discord.Embed(**kwargs)
                file = discord.File(f"data/{ctx.author.id}.png", filename=f"{ctx.author.id}.png")
                embed.set_image(url=f"attachment://{ctx.author.id}.png")
                msg: discord.Message = await ctx.send(file=file, embed=embed)
                return msg

            def check(reaction: discord.Reaction, user: Union[discord.Member, discord.User]) -> bool:
                return all((
                    str(reaction.emoji) in ("🇸", "🇭"),
                    user == ctx.author,
                    user != self.bot.user,
                    reaction.message == msg
                ))

            standing = False

            while True:
                player_score = self.calc_hand(player_hand)
                dealer_score = self.calc_hand(dealer_hand)

                if player_score == 21:  
                    result = ("Blackjack!", 'won')
                    break

                elif player_score > 21: 
                    result = ("Player busts", 'lost')
                    break

                msg = await out_table(
                    title="Your Turn",
                    description=f"Your hand: {player_score}\nDealer's hand: {dealer_score}"
                )

                await msg.add_reaction("🇭")
                await msg.add_reaction("🇸")

                try:
                    reaction, _ = await self.bot.wait_for('reaction_add', timeout=60, check=check)
                except asyncio.TimeoutError:
                    await msg.delete()
                    return

                if str(reaction.emoji) == "🇭":
                    player_hand.append(deck.pop())
                    await msg.delete()
                    continue

                elif str(reaction.emoji) == "🇸":
                    standing = True
                    break

            if standing:
                dealer_hand[1] = dealer_hand[1].flip()  
                player_score = self.calc_hand(player_hand)
                dealer_score = self.calc_hand(dealer_hand)

                while dealer_score < 17:
                    dealer_hand.append(deck.pop())
                    dealer_score = self.calc_hand(dealer_hand)

                if dealer_score == 21:
                    result = ('Dealer blackjack', 'lost')
                elif dealer_score > 21:
                    result = ("Dealer busts", 'won')
                elif dealer_score == player_score:
                    result = ("Tie!", 'kept')
                elif dealer_score > player_score:
                    result = ("You lose!", 'lost')
                elif dealer_score < player_score:
                    result = ("You win!", 'won')

            color = (
                discord.Color.red() if result[1] == 'lost'
                else discord.Color.green() if result[1] == 'won'
                else discord.Color.blue()
            )
            try:
                await msg.delete()
            except:
                pass
            msg = await out_table(
                title=result[0],
                color=color,
                description=(
                    f"**You {result[1]}**\nYour hand: {player_score}\n" +
                    f"Dealer's hand: {dealer_score}"
                )
            )
            os.remove(f'data/{ctx.author.id}.png')
        except Exception as e:
            print(e)


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out support or DM me.
"""
import discord
from discord.ext import commands
import aiosqlite
import os
from utils.Tools import *
from typing import Union
from utils.paginator import Paginator as sonu

class BlacklistWordPaginator:
    def __init__(self, entries):
        self.entries = entries
        self.per_page = 4
        self.embeds = self.get_pages()

    def get_pages(self):
        pages = []
        total_pages = (len(self.entries) // self.per_page) + (1 if len(self.entries) % self.per_page else 0)

        for i in range(0, len(self.entries), self.per_page):
            embed = discord.Embed(
                title="Blacklist Word Commands",
                description="\n".join(self.entries[i:i + self.per_page]),
                color=0x000000
            )

            embed.set_footer(
                text=f'Page {i // self.per_page + 1}/{total_pages} | Users having Administrator can use Blacklisted Word',
                icon_url="https://cdn.discordapp.com/avatars/1144179659735572640/a_f061e6472786781e23bac32fa8d0a667.png?width=115&height=115"
            )
            pages.append(embed)

        return pages

DB_PATH = "db/blword.db"

 
async def create_blacklist_table():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blacklist (
                guild_id TEXT,
                word TEXT,
                PRIMARY KEY (guild_id, word)
            )
        """)
        await db.commit()


async def create_bypass_table():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bypass (
                guild_id TEXT,
                user_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await db.commit()


async def create_bypass_roles_table():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bypass_roles (
                guild_id TEXT,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        await db.commit()




class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(create_blacklist_table())
        self.bot.loop.create_task(create_bypass_table())
        self.bot.loop.create_task(create_bypass_roles_table())
        
############ FUNCTIONS ############
    async def is_word_blacklisted(self, guild_id, word):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM blacklist WHERE guild_id = ? AND word = ?", (guild_id, word)) as cursor:
                return await cursor.fetchone() is not None
                

    async def add_word_to_blacklist(self, guild_id, word):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO blacklist (guild_id, word) VALUES (?, ?)", (guild_id, word))
            await db.commit()
            

    async def remove_word_from_blacklist(self, guild_id, word):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM blacklist WHERE guild_id = ? AND word = ?", (guild_id, word))
            await db.commit()
            

    async def get_blacklisted_words(self, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT word FROM blacklist WHERE guild_id = ?", (guild_id,)) as cursor:
                return [row[0] async for row in cursor]
                

    async def is_user_bypassed(self, guild_id, user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM bypass WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                return await cursor.fetchone() is not None
                

    async def add_user_to_bypass(self, guild_id, user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO bypass (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))
            await db.commit()
            

    async def remove_user_from_bypass(self, guild_id, user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM bypass WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await db.commit()
            

    async def get_bypassed_users(self, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id FROM bypass WHERE guild_id = ?", (guild_id,)) as cursor:
                return [row[0] async for row in cursor]
                

    async def is_role_bypassed(self, guild_id, role_id):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM bypass_roles WHERE guild_id = ? AND role_id = ?", (guild_id, role_id)) as cursor:
                return await cursor.fetchone() is not None
                

    async def add_role_to_bypass(self, guild_id, role_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO bypass_roles (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
            await db.commit()
            

    async def remove_role_from_bypass(self, guild_id, role_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM bypass_roles WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
            await db.commit()
            

    async def get_bypassed_roles(self, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT role_id FROM bypass_roles WHERE guild_id = ?", (guild_id,)) as cursor:
                return [row[0] async for row in cursor]


    async def remove_all_words_from_blacklist(self, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM blacklist WHERE guild_id = ?", (guild_id,))
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_id = str(message.guild.id)
        words = await self.get_blacklisted_words(guild_id)
        bypassed_users = await self.get_bypassed_users(guild_id)
        bypassed_roles = await self.get_bypassed_roles(guild_id)

        if message.author.guild_permissions.administrator or message.author.id in bypassed_users:
            return

        for role in message.author.roles:
            if role.id in bypassed_roles:
                return

        for word in words:
            if word in message.content.lower():
                await message.delete()
                warning_message = await message.channel.send(
                    f"{message.author.mention} watch your language, your message contains a blacklisted word!"
                )
                await warning_message.delete(delay=3)
                break

    @commands.group(name="blacklistword", aliases=["blword"], invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def blacklistword(self, ctx):
        commands_list = [
            "➜ `blacklistword add <word>` - Add a word to the blacklist.\n",
            "➜ `blacklistword remove <word>` - Remove a word from the blacklist.\n",
            "➜ `blacklistword reset` - Clear all blacklisted words for the guild.\n",
            "➜ `blacklistword config` - Show the list of blacklisted words for the guild.\n",
            "➜ `blacklistword bypass add <role>/<user>` - Add a role/user to the bypass list.\n",
            "➜ `blacklistword bypass remove <role>/<user>` - Remove a role/user from the bypass list.\n",
            "➜ `blacklistword bypass list` - Show the list of bypassed roles/users."
        ]

        paginator = sonu(ctx, BlacklistWordPaginator(commands_list).embeds)
        await paginator.paginate()
    @blacklistword.command(name="add")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def add(self, ctx, word: str):
        guild_id = str(ctx.guild.id)
        if len(await self.get_blacklisted_words(guild_id)) >= 30:
            await ctx.reply("The blacklist is full. Maximum 30 words allowed.")
            return
        if await self.is_word_blacklisted(guild_id, word.lower()):
            embed = discord.Embed(title="🔔 Access Denied",
                description=f"`{word}` is already in the blacklist.",
                color=discord.Color.from_rgb(0, 0, 0)
            )
            await ctx.reply(embed=embed)
            return

        await self.add_word_to_blacklist(guild_id, word.lower())
        embed = discord.Embed(title="✅ Success",
            description=f"Added `{word}` to the blacklist.",
            color=discord.Color.from_rgb(0, 0, 0)
        )
        await ctx.reply(embed=embed)

    @blacklistword.command(name="remove")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx, word: str):
        guild_id = str(ctx.guild.id)
        if not await self.is_word_blacklisted(guild_id, word.lower()):
            embed = discord.Embed(title="❌ Error",
                description=f"`{word}` is not in the blacklist.",
                color=discord.Color.from_rgb(0, 0, 0)
            )
            await ctx.reply(embed=embed)
            return

        await self.remove_word_from_blacklist(guild_id, word.lower())
        embed = discord.Embed(title="✅ Success",
            description=f"Removed `{word}` from the blacklist.",
            color=discord.Color.from_rgb(0, 0, 0)
        )
        await ctx.reply(embed=embed)

    @blacklistword.command(name="reset")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def reset(self, ctx):
        guild_id = str(ctx.guild.id)
        words = await self.get_blacklisted_words(guild_id)

        if not words:
            embed = discord.Embed(title="❌ Error",
                description="No words are currently blacklisted.",
                color=discord.Color.from_rgb(0, 0, 0)
            )
            await ctx.reply(embed=embed)
            return

        await self.remove_all_words_from_blacklist(guild_id)

        embed = discord.Embed(title="✅ Success",
            description="Cleared all blacklisted words.",
            color=discord.Color.from_rgb(0, 0, 0)
        )
        await ctx.reply(embed=embed)


    @blacklistword.command(name="config")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def config(self, ctx):
        guild_id = str(ctx.guild.id)
        words = await self.get_blacklisted_words(guild_id)
        if not words:
            embed = discord.Embed(title="❌ Error",
                description="No words are currently blacklisted.",
                color=discord.Color.from_rgb(0, 0, 0)
            )
            await ctx.reply(embed=embed)
            return

        embed = discord.Embed(
            title=f"Blacklisted Words for {ctx.guild.name}",
            description="\n".join(words),
            color=discord.Color.from_rgb(0, 0, 0)
        )
        await ctx.reply(embed=embed)

    @blacklistword.group(name="bypass", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def bypass(self, ctx):
        embed = discord.Embed(
            title="Bypass User Commands",
            description=(
                "➜ `blacklistword bypass add <role>/<user>` - Add a role/user to the bypass list.\n\n"
                "➜ `blacklistword bypass remove <role>/<user>` - Remove a role/user from the bypass list.\n\n"
                "➜ `blacklistword bypass list` - Show the list of bypassed roles/users."
            ),
            color=discord.Color.from_rgb(0, 0, 0)
        )
        await ctx.send(embed=embed)


    @bypass.command(name="add")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def bypass_add(self, ctx, target: Union[discord.Member, discord.Role]):
        guild_id = str(ctx.guild.id)
        if isinstance(target, discord.Member):
            if len(await self.get_bypassed_users(guild_id)) >= 30:
                await ctx.reply("The bypass list for users is full. Maximum 30 users allowed.")
                return
            if await self.is_user_bypassed(guild_id, target.id):
                embed = discord.Embed(
                    description=f"❌ | `{target}` is already bypassed.",
                    color=discord.Color.from_rgb(0, 0, 0)
                )
                await ctx.reply(embed=embed)
                return
            await self.add_user_to_bypass(guild_id, target.id)
            embed = discord.Embed(title="✅ Success",
                description=f"Added `{target}` to the bypass list.",
                color=discord.Color.from_rgb(0, 0, 0)
            )
            await ctx.reply(embed=embed)

        elif isinstance(target, discord.Role):
            if len(await self.get_bypassed_roles(guild_id)) >= 30:
                await ctx.reply("The bypass list for roles is full. Maximum 30 roles allowed.")
                return
            if await self.is_role_bypassed(guild_id, target.id):
                embed = discord.Embed(title="❌ Error",
                    description=f"`{target}` is already bypassed.",
                    color=discord.Color.from_rgb(0, 0, 0)
                )
                await ctx.reply(embed=embed)
                return
            await self.add_role_to_bypass(guild_id, target.id)
            embed = discord.Embed(title="✅ Success",
                description=f"Added `{target}` to the bypass list.",
                color=discord.Color.from_rgb(0, 0, 0)
            )
            await ctx.reply(embed=embed)


    
    @bypass.command(name="remove")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def bypass_remove(self, ctx, target: Union[discord.Member, discord.Role]):
        guild_id = str(ctx.guild.id)
        if isinstance(target, discord.Member):
            if not await self.is_user_bypassed(guild_id, target.id):
                embed = discord.Embed(title="❌ Error",
                    description=f"`{target}` is not bypassed.",
                    color=discord.Color.from_rgb(0, 0, 0)
                )
                await ctx.reply(embed=embed)
                return
            await self.remove_user_from_bypass(guild_id, target.id)
            embed = discord.Embed(title="✅ Success",
                description=f"Removed `{target}` from the bypass list.",
                color=discord.Color.from_rgb(0, 0, 0)
            )
            await ctx.reply(embed=embed)

        elif isinstance(target, discord.Role):
            if not await self.is_role_bypassed(guild_id, target.id):
                embed = discord.Embed(title="❌ Error",
                    description=f"`{target}` is not bypassed.",
                    color=discord.Color.from_rgb(0, 0, 0)
                )
                await ctx.reply(embed=embed)
                return
            await self.remove_role_from_bypass(guild_id, target.id)
            embed = discord.Embed(title="✅ Success",
                description=f"Removed `{target}` from the bypass list.",
                color=discord.Color.from_rgb(0, 0, 0)
            )
            await ctx.reply(embed=embed)

    @bypass.command(name="list")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def bypass_list(self, ctx):
        guild_id = str(ctx.guild.id)
        users = await self.get_bypassed_users(guild_id)
        roles = await self.get_bypassed_roles(guild_id)

        if not users and not roles:
            embed = discord.Embed(title="❌ Error",
                description="No users or roles are currently bypassed.",
                color=discord.Color.from_rgb(0, 0, 0)
            )
            await ctx.send(embed=embed)
            return

        bypassed_users = [ctx.guild.get_member(user_id) for user_id in users if ctx.guild.get_member(user_id)]
        bypassed_roles = [ctx.guild.get_role(role_id) for role_id in roles if ctx.guild.get_role(role_id)]
        embed = discord.Embed(
            title=f"Bypassed Users and Roles for {ctx.guild.name}",
            color=discord.Color.from_rgb(0, 0, 0)
        )

        if bypassed_users:
            embed.add_field(name="Users", value=", ".join([user.name for user in bypassed_users]), inline=False)

        if bypassed_roles:
            embed.add_field(name="Roles", value=", ".join([role.name for role in bypassed_roles]), inline=False)

        await ctx.send(embed=embed)


    @add.error
    @remove.error
    @reset.error
    @config.error
    @bypass_add.error
    @bypass_remove.error
    async def command_error(self, ctx, error):
        if isinstance(error, commands.CommandError):
            if not isinstance(error, commands.CommandOnCooldown):
                embed = discord.Embed(
                    description="❌ | An error occurred while processing the command. Make sure you have **Administrator** permissios.",
                    color=discord.Color.from_rgb(0, 0, 0)
                )
                await ctx.reply(embed=embed)
import discord
from discord.ext import commands
import aiosqlite
from utils import Paginator, DescriptionEmbedPaginator

class Block(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.bot.loop.create_task(self.set_db())

  #@commands.Cog.listener()
  async def set_db(self):
    async with aiosqlite.connect('db/block.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_blacklist (
                user_id INTEGER PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS guild_blacklist (
                guild_id INTEGER PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()
      


  @commands.group(name="blacklist", aliases=["bl"], invoke_without_command=True)
  @commands.is_owner()
  async def blacklist(self, ctx):
    if ctx.subcommand_passed is None:
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)

  @blacklist.group(name="user", help="Add/Remove a user to the blacklist.", invoke_without_command=True)
  @commands.is_owner()
  async def user(self, ctx):
    if ctx.subcommand_passed is None:
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)

  @user.command(name="add", help="Adds a user to the blacklist.")
  @commands.is_owner()
  async def add_user(self, ctx, user: discord.User):
    async with aiosqlite.connect('db/block.db') as db:
      cursor = await db.execute('SELECT user_id FROM user_blacklist WHERE user_id = ?', (user.id,))
      if await cursor.fetchone():
        embed = discord.Embed(
          title="❌ User Already Blacklisted",
          description=f"{user.mention} is already blacklisted.",
          color=0x000000
        )
        await ctx.reply(embed=embed)
      else:
        await db.execute('INSERT INTO user_blacklist (user_id) VALUES (?)', (user.id,))
        await db.commit()
        embed = discord.Embed(
          title="✅ User Blacklisted",
          description=f"{user.mention} has been added to the blacklist.",
          color=0x000000
        )
        await ctx.reply(embed=embed)

  @user.command(name="remove", help="Remove a user from the blacklist.")
  @commands.is_owner()
  async def remove_user(self, ctx, user: discord.User):
    async with aiosqlite.connect('db/block.db') as db:
      cursor = await db.execute('SELECT user_id FROM user_blacklist WHERE user_id = ?', (user.id,))
      if not await cursor.fetchone():
        embed = discord.Embed(
          title="❌ User Not Blacklisted",
          description=f"{user.mention} is not in the blacklist.",
          color=0x000000
        )
        await ctx.reply(embed=embed)
      else:
        await db.execute('DELETE FROM user_blacklist WHERE user_id = ?', (user.id,))
        await db.commit()
        embed = discord.Embed(
          title="✅ User Unblacklisted",
          description=f"{user.mention} has been removed from the blacklist.",
          color=0x000000
        )
        await ctx.reply(embed=embed)

  @user.command(name="show", aliases=["list"], help="Shows all Blacklisted users.")
  @commands.is_owner()
  async def show_users(self, ctx):
    async with aiosqlite.connect('db/block.db') as db:
      cursor = await db.execute('SELECT user_id FROM user_blacklist')
      rows = await cursor.fetchall()
      if not rows:
        embed = discord.Embed(
          title="❌ No Blacklisted Users",
          description="There are no users in the blacklist.",
          color=0x000000
        )
        await ctx.reply(embed=embed)
        return

      blacklist = []
      for row in rows:
        user_id = row[0]
        try:
          user = await self.bot.fetch_user(user_id)
          username = user.name
          user_link = f"https://discord.com/users/{user_id}"
          #indexx = [""for index, user in enumerate(blacklist)]

          blacklist.append(f"**[{username}]({user_link})** - ({user_id})")
        except discord.NotFound:
          blacklist.append(f"User ID: {user_id} (User not found)")
      entries = [f"{index+1}. {user}" for index, user in enumerate(blacklist)]
      embeds = DescriptionEmbedPaginator(
        entries=entries,
        title=f"List of Blacklisted Users - {len(blacklist)}",
        description="",
        per_page=10,
        color=0x000000).get_pages()
      paginator = Paginator(ctx, embeds)
      await paginator.paginate()

  @blacklist.group(name="guild", help="Add/Remove a guild to the blacklist.", invoke_without_command=True)
  @commands.is_owner()
  async def guild(self, ctx):
    if ctx.subcommand_passed is None:
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)

  @guild.command(name="add", help="Adds a guild to the blacklist.")
  @commands.is_owner()
  async def add_guild(self, ctx, guild_id: int):
    async with aiosqlite.connect('db/block.db') as db:
      cursor = await db.execute('SELECT guild_id FROM guild_blacklist WHERE guild_id = ?', (guild_id,))
      if await cursor.fetchone():
        embed = discord.Embed(
          title="❌ Guild Already Blacklisted",
          description=f"Guild with ID `{guild_id}` is already blacklisted.",
          color=0x000000
        )
        await ctx.reply(embed=embed)
      else:
        await db.execute('INSERT INTO guild_blacklist (guild_id) VALUES (?)', (guild_id,))
        await db.commit()
        embed = discord.Embed(
          title="✅ Guild Blacklisted",
          description=f"Guild with ID `{guild_id}` has been added to the blacklist.",
          color=0x000000
        )
        await ctx.reply(embed=embed)

  @guild.command(name="remove", help="Remove a guild from the blacklist.")
  @commands.is_owner()
  async def remove_guild(self, ctx, guild_id: int):
    async with aiosqlite.connect('db/block.db') as db:
      cursor = await db.execute('SELECT guild_id FROM guild_blacklist WHERE guild_id = ?', (guild_id,))
      if not await cursor.fetchone():
        embed = discord.Embed(
          title="❌ Guild Not Blacklisted",
          description=f"Guild with ID `{guild_id}` is not in the blacklist.",
          color=0x000000
        )
        await ctx.reply(embed=embed)
      else:
        await db.execute('DELETE FROM guild_blacklist WHERE guild_id = ?', (guild_id,))
        await db.commit()
        embed = discord.Embed(
          title="✅ Guild Unblacklisted",
          description=f"Guild with ID `{guild_id}` has been removed from the blacklist.",
          color=0x000000
        )
        await ctx.reply(embed=embed)
        

  @guild.command(name="show", aliases=["list"], help="Shows the list of blacklisted guilds")
  @commands.is_owner()
  async def show_guilds(self, ctx):
    async with aiosqlite.connect('db/block.db') as db:
      cursor = await db.execute('SELECT guild_id FROM guild_blacklist')
      rows = await cursor.fetchall()
      if not rows:
        embed = discord.Embed(
          title="❌ No Blacklisted Guilds",
          description="There are no guilds in the blacklist.",
          color=0x000000
        )
        await ctx.reply(embed=embed)
        return

      blacklist = []
      for row in rows:
        guild_id = row[0]
        try:
          guild = await self.bot.fetch_guild(guild_id)
          guild_name = guild.name
          guild_link = f"https://discord.com/guilds/{guild_id}"
          blacklist.append(f"[{guild_name}]({guild_link}) - ({guild_id})")
        except discord.NotFound:
          blacklist.append(f"Guild ID: {guild_id} (Guild not found)")
      entries = [f"{index+1}. {guild}" for index, guild in enumerate(blacklist)]
      embeds = DescriptionEmbedPaginator(
        entries=entries,
        title=f"List of Blacklisted Guilds - {len(blacklist)}",
        description="",
        per_page=10,
        color=0x000000).get_pages()
      paginator = Paginator(ctx, embeds)
      await paginator.paginate()


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out support or DM me.
"""
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
import aiosqlite
import asyncio
from utils.Tools import *
from typing import List, Tuple

DATABASE_PATH = 'db/customrole.db'
DATABASE_PATH2 = 'db/np.db'


class Customrole(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.cooldown = {}
        self.rate_limit = {}
        self.rate_limit_timeout = 5


        self.bot.loop.create_task(self.create_tables())


    async def reset_rate_limit(self, user_id):
        await asyncio.sleep(self.rate_limit_timeout)
        self.rate_limit.pop(user_id, None)
        



    async def add_role(self, *, role_id: int, member: discord.Member):
        if member.guild.me.guild_permissions.manage_roles:
            role = discord.Object(id=role_id)
            await member.add_roles(role, reason="Olympus Customrole | Role Added")
        else:
            raise discord.Forbidden("Bot does not have permission to manage roles.")



    async def remove_role(self, *, role_id: int, member: discord.Member):
        if member.guild.me.guild_permissions.manage_roles:
            role = discord.Object(id=role_id)
            await member.remove_roles(role, reason="Olympus Customrole | Role Removed")
        else:
            raise discord.Forbidden("Bot does not have permission to manage roles.")
            


    async def add_role2(self, *, role: int, member: discord.Member):
        if member.guild.me.guild_permissions.manage_roles:
            role = discord.Object(id=int(role))
            await member.add_roles(role, reason="Olympus Customrole | Role Added ")

    async def remove_role2(self, *, role: int, member: discord.Member):
        if member.guild.me.guild_permissions.manage_roles:
            role = discord.Object(id=int(role))
            await member.remove_roles(role, reason="Olympus Customrole| Role Removed")

    

    async def handle_role_command(self, context: Context, member: discord.Member, role_type: str):
        async with aiosqlite.connect('db/customrole.db') as db:
            async with db.execute(f"SELECT reqrole, {role_type} FROM roles WHERE guild_id = ?", (context.guild.id,)) as cursor:
                data = await cursor.fetchone()
                if data:
                    reqrole_id, role_id = data
                    reqrole = context.guild.get_role(reqrole_id)
                    role = context.guild.get_role(role_id)

                    if reqrole:
                        if context.author == context.guild.owner or reqrole in context.author.roles:
                            if role:
                                if role not in member.roles:
                                    await self.add_role2(role=role_id, member=member)
                                    embed = discord.Embed(title="✅ Success",
                                        description=f"**Given** <@&{role.id}> To {member.mention}",
                                        color=0x000000)
                                else:
                                    await self.remove_role2(role=role_id, member=member)
                                    embed = discord.Embed(title="✅ Success",
                                        description=f"**Removed** <@&{role.id}> From {member.mention}",
                                        color=0x000000)
                                await context.reply(embed=embed)
                            else:
                                embed = discord.Embed(title="❌ Error",
                                    description=f"{role_type.capitalize()} role is not set up in {context.guild.name}",
                                    color=0x000000)
                                await context.reply(embed=embed)
                        else:
                            embed = discord.Embed(title="🔔 Access Denied",
                                description=f"You need {reqrole.mention} to run this command.",
                                color=0x000000)
                            await context.reply(embed=embed)
                    else:
                        embed = discord.Embed(title="🔔 Access Denied",
                            description=f"Required role is not set up in {context.guild.name}",
                            color=0x000000)
                        await context.reply(embed=embed)
                else:
                    embed = discord.Embed(title="❌ Error",
                        description=f"Roles configuration is not set up in {context.guild.name}",
                        color=0x000000)
                    await context.reply(embed=embed)

    


    async def create_tables(self):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS roles (
                    guild_id INTEGER PRIMARY KEY,
                    staff INTEGER,
                    girl INTEGER,
                    vip INTEGER,
                    guest INTEGER,
                    frnd INTEGER,
                    reqrole INTEGER
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS custom_roles (
                    guild_id INTEGER,
                    name TEXT,
                    role_id INTEGER,
                    PRIMARY KEY (guild_id, name)
                )
            ''')
            await db.commit()

    
    @commands.hybrid_group(name="setup",
                           description="Setups custom roles for the server.",
                           help="Setups custom roles for the server.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def set(self, context: Context):
        if context.subcommand_passed is None:
            await context.send_help(context.command)
            context.command.reset_cooldown(context)

    async def fetch_role_data(self, guild_id):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT staff, girl, vip, guest, frnd, reqrole FROM roles WHERE guild_id = ?", (guild_id,)) as cursor:
                return await cursor.fetchone()




    async def update_role_data(self, guild_id, column, value):
        try:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute(f"INSERT OR REPLACE INTO roles (guild_id, {column}) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET {column} = ?",
                                 (guild_id, value, value))
                await db.commit()
        except Exception as e:
            print(f"Error updating role data: {e}")
            

    async def fetch_custom_role_data(self, guild_id):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT name, role_id FROM custom_roles WHERE guild_id = ?", (guild_id,)) as cursor:
                return await cursor.fetchall()


    @set.command(name="staff",
                 description="Setup staff role in guild",
                 help="Setup staff role in Guild")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(role="Role to be added")
    async def staff(self, context: Context, role: discord.Role) -> None:
        if context.author == context.guild.owner or context.author.top_role.position > context.guild.me.top_role.position:
            await self.update_role_data(context.guild.id, 'staff', role.id)
            embed = discord.Embed(title="✅ Success",
                description=f"Added {role.mention} to `Staff` Role\n\n__**How to Use?**__\nUse `staff <user>` Command to **Add {role.mention}** role to User & use again to the same user to **Remove role**. ",
                color=0x000000)
            await context.reply(embed=embed)
        else:
            embed = discord.Embed(title="🔔 Access Denied",
                                  description="Your role should be above my top role.",
                                  color=0x000000)
            await context.reply(embed=embed)

    @set.command(name="girl",
                 description="Setup girl role in the Guild",
                 help="Setup girl role in the Guild")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(role="Role to be added")
    async def girl(self, context: Context, role: discord.Role) -> None:
        if context.author == context.guild.owner or context.author.top_role.position > context.guild.me.top_role.position:
            await self.update_role_data(context.guild.id, 'girl', role.id)
            embed = discord.Embed(title="✅ Success",
                description=f"Added {role.mention} to `Girl` Role\n\n__**How to Use?**__\nUse `girl <user>` Command to **Add {role.mention}** role to User & use again to the same user to **Remove role**.  ",
                color=0x000000)
            await context.reply(embed=embed)
        else:
            embed = discord.Embed(title="🔔 Access Denied",
                  description="Your role should be above my top role.",
                  color=0x000000)
            await context.reply(embed=embed)

    @set.command(name="vip",
                 description="Setups vip role in the Guild",
                 help="Setups vip role in the Guild")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(role="Role to be added")
    async def vip(self, context: Context, role: discord.Role) -> None:
        if context.author == context.guild.owner or context.author.top_role.position > context.guild.me.top_role.position:
            await self.update_role_data(context.guild.id, 'vip', role.id)
            embed = discord.Embed(
                description=f"Added {role.mention} to `VIP` Role\n\n__**How to Use?**__\nUse `vip <user>` Command to **Add {role.mention}** role to User & use again to the same user to **Remove role**. ",
                color=0x000000)
            await context.reply(embed=embed)
        else:
            embed = discord.Embed(title="🔔 Access Denied",
                                  description="Your role should be above my top role.",
                                  color=0x000000)
            await context.reply(embed=embed)

    @set.command(name="guest",
                 description="Setup guest role in the Guild",
                 help="Setup guest role in the Guild")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(role="Role to be added")
    async def guest(self, context: Context, role: discord.Role) -> None:
        if context.author == context.guild.owner or context.author.top_role.position > context.guild.me.top_role.position:
            await self.update_role_data(context.guild.id, 'guest', role.id)
            embed = discord.Embed(
                description=f"Added {role.mention} to `Guest` Role\n\n__**How to Use?**__\nUse `guest <user>` Command to **Add {role.mention}** role to User & use again to the same user to **Remove role**. ",
                color=0x000000)
            await context.reply(embed=embed)
        else:
            embed = discord.Embed(title="🔔 Access Denied",
                                  description="Your role should be above my top role.",
                                  color=0x000000)
            await context.reply(embed=embed)

    @set.command(name="friend",
                 description="Setup friend role in the Guild",
                 help="Setup friend role in the Guild")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(role="Role to be added")
    async def friend(self, context: Context, role: discord.Role) -> None:
        if context.author == context.guild.owner or context.author.top_role.position > context.guild.me.top_role.position:
            await self.update_role_data(context.guild.id, 'frnd', role.id)
            embed = discord.Embed(
                description=f"Added {role.mention} to `Friend` Role\n\n__**How to Use?**__\nUse `friend <user>` Command to **Add {role.mention}** role to User & use again to the same user to **Remove role**. ",
                color=0x000000)
            await context.reply(embed=embed)
        else:
            embed = discord.Embed(title="🔔 Access Denied",
                                  description="Your role should be above my top role.",
                                  color=0x000000)
            await context.reply(embed=embed)

    @set.command(name="reqrole",
                 description="Setup required role for custom role commands",
                 help="Setup required role for custom role commands")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(role="Role to be added")
    async def req_role(self, context: Context, role: discord.Role) -> None:
        if context.author == context.guild.owner or context.author.top_role.position > context.guild.me.top_role.position:
            await self.update_role_data(context.guild.id, 'reqrole', role.id)
            embed = discord.Embed(title="✅ Success",
                color=0x000000,
                description=f"Added {role.mention} for Required role to run custom role commands in {context.guild.name}"
            )
            await context.reply(embed=embed)
        else:
            embed = discord.Embed(title="🔔 Access Denied",
                                  description="Your role should be above my top role.",
                                  color=0x000000)
            await context.reply(embed=embed)

    

    @set.command(name="config",
                 description="Shows the current custom role configuration in the Guild.",
                 help="Shows the current custom role configuration in the Guild.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def config(self, context: Context) -> None:
        role_data = await self.fetch_role_data(context.guild.id)
        if role_data:
            embed = discord.Embed(
                title="Custom Role Configuration",
                color=0x000000
            )
            embed.add_field(name="Staff Role", value=context.guild.get_role(role_data[0]).mention if role_data[0] else "None", inline=False)
            embed.add_field(name="Girl Role", value=context.guild.get_role(role_data[1]).mention if role_data[1] else "None", inline=False)
            embed.add_field(name="VIP Role", value=context.guild.get_role(role_data[2]).mention if role_data[2] else "None", inline=False)
            embed.add_field(name="Guest Role", value=context.guild.get_role(role_data[3]).mention if role_data[3] else "None", inline=False)
            embed.add_field(name="Friend Role", value=context.guild.get_role(role_data[4]).mention if role_data[4] else "None", inline=False)
            embed.add_field(name="Required Role for Commands", value=context.guild.get_role(role_data[5]).mention if role_data[5] else "None", inline=False)
            embed.set_footer(text="Use Commands to assign role & use again to the same user to remove role.")
            
            await context.reply(embed=embed)
            
        else:
            embed = discord.Embed(title="❌ Error",
                description="No custom role configuration found in this Guild.",
                color=0x000000
            )
            
            await context.reply(embed=embed)



            


    @set.command(name="create",
                 description="Creates a custom role command.",
                 help="Creates a custom role command")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(name="Command name", role="Role to be assigned")
    async def create(self, context: Context, name: str, role: discord.Role) -> None:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM custom_roles WHERE guild_id = ?", (context.guild.id,)) as cursor:
                count = await cursor.fetchone()
                if count[0] >= 56:
                    embed = discord.Embed(title="🔔 Access Denied",
                        description="You have reached the maximum limit of 56 custom role commands for this guild.",
                        color=0x000000
                    )
                    await context.reply(embed=embed)
                    return

            async with db.execute("SELECT name FROM custom_roles WHERE guild_id = ?", (context.guild.id,)) as cursor:
                existing_role = await cursor.fetchall()
                if any(name == row[0] for row in existing_role):
                    embed = discord.Embed(title="❌ Error",
                        description=f"A custom role command with the name `{name}` already exists in this guild. Remove it before creating a new one.",
                        color=0x000000
                    )
                    await context.reply(embed=embed)
                    return

            await db.execute("INSERT INTO custom_roles (guild_id, name, role_id) VALUES (?, ?, ?)",
                             (context.guild.id, name, role.id))
            await db.commit()

        embed = discord.Embed(title="✅ Success",
            description=f"Custom role command `{name}` created to assign the role {role.mention}.\n\n__**How to Use?**__\nUse `{name} <user>` Command to Assign/Remove {role.mention} role to User.\n> This will work for the users having `Manage Roles` permissions.",
            color=0x000000
        )
        await context.reply(embed=embed)
        

    @set.command(name="delete", aliases=["remove"],
                 description="Deletes a custom role command.",
                 help="Deletes a custom role command.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(name="Command name to be deleted")
    async def delete(self, context: Context, name: str) -> None:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT name FROM custom_roles WHERE guild_id = ? AND name = ?", (context.guild.id, name)) as cursor:
                existing_role = await cursor.fetchone()

        if not existing_role:
            embed = discord.Embed(title="❌ Error",
                description=f"No custom role command with the name `{name}` was found in this guild.",
                color=0x000000
            )
            await context.reply(embed=embed)
            return

        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("DELETE FROM custom_roles WHERE guild_id = ? AND name = ?", (context.guild.id, name))
            await db.commit()

        embed = discord.Embed(title="✅ Success",
            description=f"Custom role command `{name}` has been deleted.",
            color=0x000000
        )
        await context.reply(embed=embed)
        

    @set.command(
        name="list",
        description="List all the custom roles setup for the server.",
        help="List all the custom roles setup for the server."
    )
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def list(self, context: Context) -> None:
        custom_roles = await self.fetch_custom_role_data(context.guild.id)

        if not custom_roles:
            embed = discord.Embed(
                title="❌ Error",
                description="No custom roles have been created for this server.",
                color=0x000000
            )
            await context.reply(embed=embed)
            return

        
        def chunk_list(data: List[Tuple[str, int]], chunk_size: int):
            """Yield successive chunks of `chunk_size` from `data`."""
            for i in range(0, len(data), chunk_size):
                yield data[i:i + chunk_size]

        
        chunks = list(chunk_list(custom_roles, 7))

        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title="Custom Roles",
                color=0x000000
            )
            for name, role_id in chunk:
                role = context.guild.get_role(role_id)
                if role:
                    embed.add_field(name=f"Name: {name}", value=f"Role: {role.mention}", inline=False)

            embed.set_footer(text=f"Page {i+1}/{len(chunks)} | These commands are usable by Members having Manage Role permissions.")
            await context.reply(embed=embed)


    @set.command(name="reset",
         description="Resets custom role configuration for the server.",
         help="Resets custom role configuration for the server.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def reset(self, context: Context) -> None:
        if context.author == context.guild.owner or context.author.top_role.position > context.guild.me.top_role.position:
            removed_roles = []
            role_data = await self.fetch_role_data(context.guild.id)
            if role_data:
                roles = ["staff", "girl", "vip", "guest", "frnd", "reqrole"]
                for i, role_name in enumerate(roles):
                    role_id = role_data[i]
                    if role_id:
                        role = context.guild.get_role(role_id)
                        if role:
                            removed_roles.append(f"**{role_name.capitalize()}:** {role.mention}")
                            await self.update_role_data(context.guild.id, role_name, None)
                            
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    await db.execute("DELETE FROM custom_roles WHERE guild_id = ?", (context.guild.id,))
                    await db.commit()
                    embed = discord.Embed(
            title="Custom Role Configuration Reset",
            description=f"Deleted All Custom Role commands ✅\n\n**Removed Roles:**\n" + "\n".join(removed_roles) if removed_roles else "No roles were previously set.",
            color=0x000000
        )
                    
                    await context.reply(embed=embed)
            else:
                embed = discord.Embed(description="No configuration found for this server.", color=0x000000)
                await context.reply(embed=embed)
        else:
            embed = discord.Embed(title="🔔 Access Denied",
                                  description="Your role should be above my top role.",
                                  color=0x000000)
            await context.reply(embed=embed)

        
            

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.bot or not message.content:
            return

        prefixes = await self.bot.get_prefix(message)

        
        if not prefixes:
            return

        
        if not any(message.content.startswith(prefix) for prefix in prefixes):
            return

        
        for prefix in prefixes:
            if message.content.startswith(prefix):
                command_name = message.content[len(prefix):].split()[0] 
                break
        else:
            return

        guild_id = message.guild.id

        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT role_id FROM custom_roles WHERE guild_id = ? AND name = ?", (guild_id, command_name)) as cursor:
                result = await cursor.fetchone()

        if result:
            role_id = result[0]
            role = message.guild.get_role(role_id)

            
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute("SELECT reqrole FROM roles WHERE guild_id = ?", (guild_id,)) as cursor:
                    reqrole_result = await cursor.fetchone()

            reqrole_id = reqrole_result[0] if reqrole_result else None
            reqrole = message.guild.get_role(reqrole_id) if reqrole_id else None

            
            if reqrole is None:
                await message.channel.send("⚠️ The required role is not set up in this server. Please set it up using `setup reqrole`.")
                return

            
            if reqrole not in message.author.roles:
                await message.channel.send(embed=discord.Embed(description=f"⚠️ You need the {reqrole.mention} role to use this command.", color=0x000000))
                return

            
            member = message.mentions[0] if message.mentions else None
            if not member:
                await message.channel.send("Please mention a user to assign the role.")
                return

            
            now = asyncio.get_event_loop().time()
            if guild_id not in self.cooldown or now - self.cooldown[guild_id] >= 10:
                self.cooldown[guild_id] = now
            else:
                await message.channel.send("You're on a cooldown of 5 seconds. Please wait before sending another command.", delete_after=5)
                return

            try:
                if role in member.roles:
                    await self.remove_role(role_id=role_id, member=member)
                    await message.channel.send(embed=discord.Embed(
                        title="✅ Success",
                        description=f"**Removed** the role {role.mention} from {member.mention}.",
                        color=0x000000
                    ))
                else:
                    await self.add_role(role_id=role_id, member=member)
                    await message.channel.send(embed=discord.Embed(
                        title="✅ Success",
                        description=f"**Added** the role {role.mention} to {member.mention}.",
                        color=0x000000
                    ))
            except discord.Forbidden as e:
                await message.channel.send("I do not have permission to manage this role to the given user.")
                print(f"Error: {e}")
        else:
            return

    

    @commands.hybrid_command(name="staff",
         description="Gives the staff role to the user.",
         aliases=['official'],
         help="Gives the staff role to the user.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    #@commands.has_permissions(manage_roles=True)
    async def _staff(self, context: Context, member: discord.Member) -> None:
        await self.handle_role_command(context, member, 'staff')

    @commands.hybrid_command(name="girl",
         description="Gives the girl role to the user.",
         aliases=['qt'],
         help="Gives the girl role to the user.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    #@commands.has_permissions(manage_roles=True)
    async def _girl(self, context: Context, member: discord.Member) -> None:
        await self.handle_role_command(context, member, 'girl')

    @commands.hybrid_command(name="vip",
         description="Gives the VIP role to the user.",
         help="Gives the VIP role to the user.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    #@commands.has_permissions(manage_roles=True)
    async def _vip(self, context: Context, member: discord.Member) -> None:
        await self.handle_role_command(context, member, 'vip')

    @commands.hybrid_command(name="guest",
         description="Gives the guest role to the user.",
         help="Gives the guest role to the user.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    #@commands.has_permissions(manage_roles=True)
    async def _guest(self, context: Context, member: discord.Member) -> None:
        await self.handle_role_command(context, member, 'guest')

    @commands.hybrid_command(name="friend",
         description="Gives the friend role to the user.",
         aliases=['frnd'],
         help="Gives the friend role to the user.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    #@commands.has_permissions(manage_roles=True)
    async def _friend(self, context: Context, member: discord.Member) -> None:
        await self.handle_role_command(context, member, 'frnd')


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out support or DM me.
"""
import os
import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import asyncio
from utils.Tools import *
import re

class Embed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = bot

    @commands.hybrid_command(name="embed")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 7, commands.BucketType.user)
    @commands.has_permissions(manage_messages=True)
    async def _embed(self, ctx):
        msgx = "Example embed. You can customize everything.\n*Respond within 30 seconds to avoid time out.*"
        embed = discord.Embed(title="Edit your Embed!", 
                              description="- Select Options what to edit from the below select menu.\n\nMust edit embed title & description to remove these instructions.", 
                              color=0x000000)
        interaction_user = ctx.author

        def chk(m):
            return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id and not m.author.bot

        async def select_callback(interaction):
            if interaction.user.id != interaction_user.id:
                await interaction.response.send_message("Uh oh! That message doesn't belong to you.\nYou must run this command to interact with it.", ephemeral=True)
                return

            await interaction.response.defer()

            value = select.values[0]

            if value == "Title":
                await ctx.send("Please enter the **Title of the embed**:")
                try:
                    tit = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    embed.title = tit.content
                    await msg.edit(content=msgx, embed=embed)
                except asyncio.TimeoutError:
                    await ctx.send("Timed Out")
            elif value == "Description":
                await ctx.send("Please enter the **Description of the embed**:")
                try:
                    desc = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    embed.description = desc.content
                    await msg.edit(content=msgx, embed=embed)
                except asyncio.TimeoutError:
                    await ctx.send("Timed Out")
            elif value == "Color":
                await ctx.send("Please enter the color of the embed as a hexadecimal value (e.g., #FF0000 for red):")
                try:
                    col = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    color = discord.Colour(int(col.content.strip("#"), 16))  # hex se int
                    embed.color = color
                    await msg.edit(content=msgx, embed=embed)
                except ValueError:
                    await ctx.send("Invalid color format. Please retry with a valid hexadecimal color value.")
                except asyncio.TimeoutError:
                    await ctx.send("Timed Out")
            elif value == "Thumbnail":
                await ctx.send("Please enter the **URL of the thumbnail:**")
                try:
                    thumb = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    if not thumb.content.startswith("http"):
                        raise ValueError("Invalid URL format")
                    embed.set_thumbnail(url=thumb.content)
                    await msg.edit(content=msgx, embed=embed)
                except ValueError as e:
                    await ctx.send(str(e))
                except asyncio.TimeoutError:
                    await ctx.send("Timed Out")
            elif value == "Image":
                await ctx.send("Please enter the **URL of the image:**")
                try:
                    img = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    if not img.content.startswith("http"):
                        raise ValueError("Invalid URL format")
                    embed.set_image(url=img.content)
                    await msg.edit(content=msgx, embed=embed)
                except ValueError as e:
                    await ctx.send(str(e))
                except asyncio.TimeoutError:
                    await ctx.send("Timed Out")
            elif value == "Footer Text":
                await ctx.send("Please enter the **text of the footer:**")
                try:
                    foot = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    embed.set_footer(text=foot.content)
                    await msg.edit(content=msgx, embed=embed)
                except asyncio.TimeoutError:
                    await ctx.send("Timed Out")
            elif value == "Footer Icon":
                await ctx.send("Please enter the **URL of the footer icon:**")
                try:
                    foot_icon = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    if not foot_icon.content.startswith("http"):
                        raise ValueError("Invalid URL format")
                    embed.set_footer(text=embed.footer.text or "Footer", icon_url=foot_icon.content)
                    await msg.edit(content=msgx, embed=embed)
                except ValueError as e:
                    await ctx.send(str(e))
                except asyncio.TimeoutError:
                    await ctx.send("Timed Out")
            elif value == "Author Text":
                await ctx.send("Please enter the **author text:**")
                try:
                    auth_text = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    embed.set_author(name=auth_text.content)
                    await msg.edit(content=msgx, embed=embed)
                except asyncio.TimeoutError:
                    await ctx.send("Timed Out")
            elif value == "Author Icon":
                await ctx.send("Please enter the **URL of the author icon:**")
                try:
                    auth_icon = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    if not auth_icon.content.startswith("http"):
                        raise ValueError("Invalid URL format")
                    embed.set_author(name=embed.author.name or "Author", icon_url=auth_icon.content)
                    await msg.edit(content=msgx, embed=embed)
                except ValueError as e:
                    await ctx.send(str(e))
                except asyncio.TimeoutError:
                    await ctx.send("Timed Out")
            elif value == "Add Field":
                await ctx.send("**Enter Field title:**")
                try:
                    name = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    await ctx.send("**Enter Field value:**")
                    value = await ctx.bot.wait_for("message", timeout=30, check=chk)
                    embed.add_field(name=name.content, value=value.content, inline=False)
                    await msg.edit(content=msgx, embed=embed)
                except asyncio.TimeoutError:
                    await ctx.send("Timed Out")

        select = Select(
            placeholder="Choose an option to edit the Embed",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Title", description="Edit the title of the embed"),
                discord.SelectOption(label="Description", description="Edit the description of the embed"),
                discord.SelectOption(label="Add Field", description="Add a field to the embed"),
                discord.SelectOption(label="Color", description="Edit the color of the embed"),
                discord.SelectOption(label="Thumbnail", description="Edit the thumbnail of the embed"),
                discord.SelectOption(label="Image", description="Edit the image of the embed"),
                discord.SelectOption(label="Footer Text", description="Edit the footer text of the embed"),
                discord.SelectOption(label="Footer Icon", description="Edit the footer icon of the embed"),
                discord.SelectOption(label="Author Text", description="Edit the author text of the embed"),
                discord.SelectOption(label="Author Icon", description="Edit the author icon of the embed"),
                
            ]
        )
        select.callback = select_callback

        async def send_callback(interaction):
            if interaction.user.id != interaction_user.id:
                await interaction.response.send_message("Uh oh! That message doesn't belong to you.\nYou must run this command to interact with it.", ephemeral=True)
                return
            await interaction.response.defer()
            await ctx.send("Please mention the **channel** where you want to send this embed:")
            try:
                tit = await ctx.bot.wait_for("message", timeout=30, check=chk)
                chnl = tit.channel_mentions[0]
                await chnl.send(embed=embed)
                await ctx.send(embed=discord.Embed(title="✅ Success",
                                                   description="Sent the embed message to the mentioned channel",
                                                   color=0x000000))
            except asyncio.TimeoutError:
                await ctx.send("Timed Out")

        async def delete_callback(interaction):
            if interaction.user.id != interaction_user.id:
                await interaction.response.send_message("Uh oh! That message doesn't belong to you.\nYou must run this command to interact with it.", ephemeral=True)
                return
            await interaction.response.defer()
            await msg.delete()

        button_send = Button(label="Send Embed",  emoji="•", style=discord.ButtonStyle.success)
        button_send.callback = send_callback

        button_delete = Button(label="Cancel Setup",  emoji="•", style=discord.ButtonStyle.danger)
        button_delete.callback = delete_callback

        view = View(timeout=180)
        view.add_item(select)
        view.add_item(button_send)
        view.add_item(button_delete)

        msg = await ctx.send(embed=embed, content=msgx, view=view)
        ctx.message = msg



"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out support or DM me.
"""
import discord
from discord.ext import commands
import aiosqlite
from utils.Tools import *

class EmergencyRestoreView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Only the Server Owner can use this button.", ephemeral=True)
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Only the Server Owner can use this button.", ephemeral=True)
        self.value = False
        await interaction.response.defer()
        self.stop()



class Emergency(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db_path = "db/emergency.db"
        self.bot.loop.create_task(self.initialize_database())

    async def initialize_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS authorised_users (
                    guild_id INTEGER,
                    user_id INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS emergency_roles (
                    guild_id INTEGER,
                    role_id INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS restore_roles (
                    guild_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    disabled_perms TEXT NOT NULL,
                    PRIMARY KEY (guild_id, role_id)
                )
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS role_positions (
    guild_id INTEGER,
    role_id INTEGER,
    previous_position INTEGER
)
""")
            await db.commit()

    async def is_guild_owner(self, ctx):
        return ctx.guild and ctx.author.id == ctx.guild.owner_id

    async def is_guild_owner_or_authorised(self, ctx):
        if await self.is_guild_owner(ctx):
            return True
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM authorised_users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, ctx.author.id)) as cursor:
                return await cursor.fetchone() is not None

    @commands.group(name="emergency", aliases=["emg"], help="Lists all the commands in the emergency group.", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def emergency(self, ctx):
        embed = discord.Embed(
            title="__Emergency Situation__",
            description="The `emergency` command group is designed to protect your server from malicious activity or accidental damage. It allows server owners and authorized users to disable dangerous permissions from roles by executing `emergencysituation` or `emgs` command and prevent potential risks.\n\n__**The command group has several subcommands**__:",
            color=0x000000
        )
        embed.add_field(name=f"`{ctx.prefix}emergency enable`", value="> Enable emergency mode, it adds all roles with dangerous permissions in the emergency role list.", inline=False)
        embed.add_field(name=f"`{ctx.prefix}emergency disable`", value="> Disable emergency mode and clear the emergency role list.", inline=False)
        embed.add_field(name=f"`{ctx.prefix}emergency authorise`", value="> Manage authorized users for executing `emergencysituation` command.", inline=False)
        embed.add_field(name=f"`{ctx.prefix}emergency role`", value="> Manage roles added to the emergency list. You can add/remove/list roles by emergency role group.", inline=False)
        embed.add_field(name=f"`{ctx.prefix}emergency-situation` or `{ctx.prefix}emgs`", value="> Execute emergency situation which disables dangerous permissions from roles in the emergency list & move the role with maximum member to top position below the bot top role. Restore disabled permissions of role using `emgrestore`.", inline=False)
        embed.set_footer(text="Use \"help emergency <subcommand>\" for more information.", icon_url=self.bot.user.avatar.url)
        await ctx.reply(embed=embed)


    @emergency.command(name="enable", help="Enable emergency mode and add all roles with dangerous permissions.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def enable(self, ctx):
        Olympus = ['213347081799073793', '677952614390038559']
        if ctx.author.id != ctx.guild.owner_id and str(ctx.author.id) not in Olympus:
            embed = discord.Embed(title="❌ Error", description="Only the server owner can enable emergency mode.", color=0x000000)
            return await ctx.reply(embed=embed)

        dangerous_permissions = ["administrator", "ban_members", "kick_members", "manage_channels", "manage_roles", "manage_guild"]
        roles_added = []

        async with aiosqlite.connect(self.db_path) as db:
            for role in ctx.guild.roles:
                
                if role.managed or role.is_bot_managed():
                    continue

                if role.position >= ctx.guild.me.top_role.position:
                    continue
                
                
                if any(getattr(role.permissions, perm, False) for perm in dangerous_permissions):
                    async with db.execute("SELECT 1 FROM emergency_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id)) as cursor:
                        if not await cursor.fetchone():
                            await db.execute("INSERT INTO emergency_roles (guild_id, role_id) VALUES (?, ?)", (ctx.guild.id, role.id))
                            roles_added.append(role)

            await db.commit()

        
        if roles_added:
            description = "\n".join([f"{role.mention}" for role in roles_added])
            embed = discord.Embed(title="✅ Success", description=f"The following roles with dangerous permissions have been added to the **emergency list**:\n{description}", color=0x000000)
            embed.set_footer(text="Roles having greater or equal position than my top role is not added in the emergency list.", icon_url=self.bot.user.display_avatar.url)
        else:
            embed = discord.Embed(title="❌ Error", description="No new roles with dangerous permissions were found.", color=0x000000)
        
        await ctx.reply(embed=embed)
        

    @emergency.command(name="disable", help="Disable emergency mode and clear the emergency role list.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def disable(self, ctx):
        Olympus = ['213347081799073793', '677952614390038559']
        if ctx.author.id != ctx.guild.owner_id and str(ctx.author.id) not in Olympus:
            embed = discord.Embed(title="❌ Error", description="Only the server owner can disable emergency mode.", color=0x000000)
            return await ctx.reply(embed=embed)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM emergency_roles WHERE guild_id = ?", (ctx.guild.id,))
            await db.commit()

        embed = discord.Embed(title="✅ Success", description="Emergency mode has been disabled, and all emergency roles have been cleared.", color=0x000000)
        await ctx.reply(embed=embed)

    


    @emergency.group(name="authorise", aliases=["ath"], help="Lists all the commands in the emergency authorise group.", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def authorise(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @authorise.command(name="add", help="Adds a user to the authorised group.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def authorise_add(self, ctx, member: discord.Member):
        if not await self.is_guild_owner(ctx):
            embed = discord.Embed(title="❌ Error", description="Only the server owner can add authorised users for executing emergency situation.", color=0x000000)
            return await ctx.reply(embed=embed)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM authorised_users WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                count = (await cursor.fetchone())[0]
            if count >= 5:
                embed = discord.Embed(title="🔔 Access Denied", description="Only up to 5 authorised users can be added.", color=0x000000)
                return await ctx.reply(embed=embed)

            async with db.execute("SELECT 1 FROM authorised_users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, member.id)) as cursor:
                if await cursor.fetchone():
                    embed = discord.Embed(title="❌ Error", description="This user is already authorised.", color=0x000000)
                    return await ctx.reply(embed=embed)

            await db.execute("INSERT INTO authorised_users (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, member.id))
            await db.commit()

        embed = discord.Embed(title="✅ Success", description=f"**{member.display_name}** has been authorised to use `emergency-situation` command.", color=0x000000)
        await ctx.reply(embed=embed)

    @authorise.command(name="remove", help="Removes a user from the authorised group")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def authorise_remove(self, ctx, member: discord.Member):
        if not await self.is_guild_owner(ctx):
            embed = discord.Embed(title="🔔 Access Denied", description="Only the server owner can remove authorised users for emergency situation.", color=0x000000)
            return await ctx.reply(embed=embed)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM authorised_users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, member.id)) as cursor:
                if not await cursor.fetchone():
                    embed = discord.Embed(title="❌ Error", description="This user is not authorised.", color=0x000000)
                    return await ctx.reply(embed=embed)

            await db.execute("DELETE FROM authorised_users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, member.id))
            await db.commit()

        embed = discord.Embed(title="✅ Success", description=f"**{member.display_name}** has been removed from the authorised list and can no more use `emergency-situation` command.", color=0x000000)
        await ctx.reply(embed=embed)

    @authorise.command(name="list", aliases=["view", "config"], help="Lists all authorised users for emergency actions.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def list_authorized(self, ctx):
        if not await self.is_guild_owner(ctx):
            embed = discord.Embed(title="🔔 Access Denied", description="Only the server owner can view the list of authorised users for emergency situation.", color=0x000000)
            return await ctx.reply(embed=embed)

        
        async with aiosqlite.connect('db/emergency.db') as db:
            cursor = await db.execute("SELECT user_id FROM authorised_users WHERE guild_id = ?", (ctx.guild.id,))
            authorized_users = await cursor.fetchall()
            
        if not authorized_users:
            await ctx.reply(embed=discord.Embed(
                title="Authorized Users",
                description="No authorized users found.",
                color=0x000000))
            return
                
        description = "\n".join([f"{index + 1}. [{ctx.guild.get_member(user[0]).name}](https://discord.com/users/{user[0]}) - {user[0]}" for index, user in enumerate(authorized_users)])
        await ctx.reply(embed=discord.Embed(
            title="Authorized Users",
            description=description,
            color=0x000000))

    @emergency.group(name="role", help="Lists all the commands in the emergency role group.", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def role(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @role.command(name="add", help="Adds a role to the emergency role list")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def role_add(self, ctx, role: discord.Role):
        if not await self.is_guild_owner(ctx):
            embed = discord.Embed(title="🚫 Access Denied", description="Only the server owner can add role for emergency situation.", color=0x000000)
            return await ctx.reply(embed=embed)


        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM emergency_roles WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                count = (await cursor.fetchone())[0]
            if count >= 25:
                embed = discord.Embed(title="❌ Error", description="Only up to 25 roles can be added.", color=0x000000)
                return await ctx.reply(embed=embed)

            async with db.execute("SELECT 1 FROM emergency_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id)) as cursor:
                if await cursor.fetchone():
                    embed = discord.Embed(title="❌ Error", description="This role is already in the emergency list.", color=0x000000)
                    return await ctx.reply(embed=embed)

            await db.execute("INSERT INTO emergency_roles (guild_id, role_id) VALUES (?, ?)", (ctx.guild.id, role.id))
            await db.commit()

        embed = discord.Embed(title="✅ Success", description=f"**{role.name}** has been **added** to the emergency list.", color=0x000000)
        await ctx.reply(embed=embed)

    @role.command(name="remove", help="Removes a role from the emergency role list.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def role_remove(self, ctx, role: discord.Role):
        if not await self.is_guild_owner(ctx):
            embed = discord.Embed(title="🔔 Access Denied", description="Only the server owner can remove roles from emergency list.", color=0x000000)
            return await ctx.reply(embed=embed)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM emergency_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id)) as cursor:
                if not await cursor.fetchone():
                    embed = discord.Embed(title="❌ Error", description="This role is not in the emergency list.", color=0x000000)
                    return await ctx.reply(embed=embed)

            await db.execute("DELETE FROM emergency_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id))
            await db.commit()

        embed = discord.Embed(title="✅ Success", description=f"**{role.name}** has been removed from the emergency list.", color=0x000000)
        await ctx.reply(embed=embed)

    @role.command(name="list", aliases=["view", "config"], help="Lists all roles added to the emergency list.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def list_roles(self, ctx):
        if not await self.is_guild_owner_or_authorised(ctx):
            embed = discord.Embed(title="🔔 Access Denied", description="You are not authorised to view list of roles for emergency situation.", color=0x000000)
            return await ctx.reply(embed=embed)

        
        async with aiosqlite.connect('db/emergency.db') as db:
            cursor = await db.execute("SELECT role_id FROM emergency_roles WHERE guild_id = ?", (ctx.guild.id,))
            roles = await cursor.fetchall()

        if not roles:
            
            await ctx.reply(embed=discord.Embed(
                title="Emergency Roles",
                description="No roles added for emergency situation.",
                color=0x000000))
            return

        description = "\n".join([f"{index + 1}. <@&{role[0]}> - {role[0]}" for index, role in enumerate(roles)])

        await ctx.reply(embed=discord.Embed(
            title="Emergency Roles",
            description=description,
            color=0x000000))


    @commands.command(name="emergencysituation", help="Disable dangerous permissions from roles in the emergency list.", aliases=["..", "emergency-situation", "emgs"])
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 40, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def emergencysituation(self, ctx):
        Olympus = ['213347081799073793', '677952614390038559']
        guild_id = ctx.guild.id

        if not await self.is_guild_owner_or_authorised(ctx) and str(ctx.author.id) not in Olympus:
            return await ctx.reply(embed=discord.Embed(
                title="🚫 Access Denied", 
                description="You are not authorised to execute the emergency situation.", 
                color=0x000000))

        processing_message = await ctx.send(embed=discord.Embed(title="• Processing Emergency Situation, wait for a while...", color=0x000000))

        antinuke_enabled = False
        async with aiosqlite.connect('db/anti.db') as anti:
            async with anti.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild_id,)) as cursor:
                antinuke_status = await cursor.fetchone()
            if antinuke_status:
                antinuke_enabled = True
                await anti.execute('DELETE FROM antinuke WHERE guild_id = ?', (guild_id,))
                await anti.commit()
                
                
                

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM restore_roles WHERE guild_id = ?", (ctx.guild.id,))
            await db.commit()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT role_id FROM emergency_roles WHERE guild_id = ?", (ctx.guild.id,))
            emergency_roles = await cursor.fetchall()

        if not emergency_roles:
            await processing_message.delete()
            return await ctx.reply(embed=discord.Embed(
                title="❌ Error",
                description="No roles have been added for the emergency situation.",
                color=0x000000))

        bot_highest_role = ctx.guild.me.top_role
        dangerous_permissions = [
            "administrator", "ban_members", "kick_members", 
            "manage_channels", "manage_roles", "manage_guild"
        ]

        modified_roles = []
        unchanged_roles = []

        async with aiosqlite.connect(self.db_path) as db:
            for role_data in emergency_roles:
                role = ctx.guild.get_role(role_data[0])

                if not role:
                    continue

                if role.position >= bot_highest_role.position or role.managed:
                    unchanged_roles.append(role)
                    continue

                permissions_changed = False
                role_permissions = role.permissions
                disabled_perms = []

                for perm in dangerous_permissions:
                    if getattr(role_permissions, perm, False):
                        setattr(role_permissions, perm, False)
                        permissions_changed = True
                        disabled_perms.append(perm)

                if permissions_changed:
                    try:
                        await role.edit(permissions=role_permissions, reason="Emergency Situation: Disabled dangerous permissions")
                        modified_roles.append(role)

                        await db.execute("INSERT INTO restore_roles (guild_id, role_id, disabled_perms) VALUES (?, ?, ?)", 
                                         (ctx.guild.id, role.id, ','.join(disabled_perms)))
                        await db.commit()

                    except discord.Forbidden:
                        unchanged_roles.append(role)

        if modified_roles:
            success_message = "\n".join([f"{role.mention}" for role in modified_roles])
        else:
            success_message = "No roles were modified."

        if unchanged_roles:
            error_message = "\n".join([f"{role.mention}" for role in unchanged_roles])
        else:
            error_message = "No roles had permission errors."

        most_mem = max(
            [role for role in ctx.guild.roles if not role.managed and role.position < bot_highest_role.position and role != ctx.guild.default_role],
            key=lambda role: len(role.members),
            default=None
        )

        if most_mem:
            target_position = bot_highest_role.position - 1 
            try:
                await most_mem.edit(position=target_position, reason="Emergency Situation: Role moved for safety")
                await ctx.reply(embed=discord.Embed(
                    title="Emergency Situation",
                    description=f"**✅ Roles Modified (Denied Dangerous Permissions)**:\n{success_message}\n\n**⚠️ Role Moved**: {most_mem.mention} moved to a position below the bot's highest role.\n**Move back to its previous position soon after the server is not in risk.**\n\n**❌ Errors**:\n{error_message}",
                    color=0x000000))
            except discord.Forbidden:
                await ctx.reply(embed=discord.Embed(
                    title="Emergency Situation",
                    description=f"**✅ Roles Modified (Denied Dangerous Permissions)**:\n{success_message}\n\n**ℹ️ Role Couldn't Moved**: Failed to move the role {most_mem.mention} below the bot's highest role due to permissions error.\n**Move back to its previous position soon after the server is not in risk.**\n\n**❌ Errors**:\n{error_message}",
                    color=0x000000))

            except Exception as e:
                await ctx.reply(embed=discord.Embed(
                    title="Emergency Situation",
                    description=f"**✅ Roles Modified (Denied Dangerous Permissions)**:\n{success_message}\n\n**ℹ️ Role Couldn't Moved**: An unexpected error occurred while moving the role: {str(e)}.\n**Move back to its previous position soon after the server is not in risk.**\n\n**❌ Errors**:\n{error_message}",
                    color=0x000000)) 
        else:
            await ctx.reply(embed=discord.Embed(
                title="Emergency Situation",
                description=f"**✅ Roles Modified (Denied Dangerous Permissions)**:\n{success_message}\n\n**❌ Errors**:\n{error_message}",
                color=0x000000))

        if antinuke_enabled:
            async with aiosqlite.connect('db/anti.db') as anti:
                await anti.execute("INSERT INTO antinuke (guild_id, status) VALUES (?, 1)", (guild_id,))
                await anti.commit()

        await processing_message.delete()


    
    @commands.command(name="emergencyrestore", aliases=["...", "emgrestore", "emgsrestore", "emgbackup"], help="Restore disabled permissions to roles.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def emergencyrestore(self, ctx):
        Olympus = ['213347081799073793', '677952614390038559']
        if ctx.author.id != ctx.guild.owner_id and str(ctx.author.id) not in Olympus:
            return await ctx.reply(embed=discord.Embed(
                title="🚫 Access Denied", 
                description="Only the server owner can execute the emergency restore command.", 
                color=0x000000))

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT role_id, disabled_perms FROM restore_roles WHERE guild_id = ?", (ctx.guild.id,))
            restore_roles = await cursor.fetchall()

        if not restore_roles:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Error",
                description="No roles were found with disabled permissions for restore.",
                color=0x000000))

        confirmation_embed = discord.Embed(
            title="Confirm Restoration",
            description="This will restore previously disabled permissions for emergency roles. Do you want to proceed?",
            color=0x000000
        )
        view = EmergencyRestoreView(ctx)
        await ctx.send(embed=confirmation_embed, view=view)

        await view.wait()

        if view.value is None:
            return await ctx.reply(embed=discord.Embed(
                title="Restore Cancelled",
                description="The restore process timed out.",
                color=0x000000))

        if view.value is False:
            return await ctx.reply(embed=discord.Embed(
                title="Restore Cancelled",
                description="Restoring permissions to roles has been cancelled.",
                color=0x000000))

        modified_roles = []
        unchanged_roles = []

        async with aiosqlite.connect(self.db_path) as db:
            for role_id, disabled_perms in restore_roles:
                role = ctx.guild.get_role(role_id)

                if not role:
                    continue

                role_permissions = role.permissions
                permissions_restored = False

                for perm in disabled_perms.split(','):
                    if hasattr(role_permissions, perm):
                        setattr(role_permissions, perm, True)
                        permissions_restored = True

                if permissions_restored:
                    try:
                        await role.edit(permissions=role_permissions, reason="Emergency Restore: Restored permissions")
                        modified_roles.append(role)
                    except discord.Forbidden:
                        unchanged_roles.append(role)

            await db.execute("DELETE FROM restore_roles WHERE guild_id = ?", (ctx.guild.id,))
            await db.commit()

        if modified_roles:
            success_message = "\n".join([f"{role.mention}" for role in modified_roles])
        else:
            success_message = "No roles were restored."

        if unchanged_roles:
            error_message = "\n".join([f"{role.mention}" for role in unchanged_roles])
        else:
            error_message = "No roles had permission errors."

        await ctx.reply(embed=discord.Embed(
            title="Emergency Restore",
            description=f"**✅ Permissions Restored**:\n{success_message}\n\n**❌ Errors**:\n{error_message}\n\n• Database of previously disabled permissions has been cleared.",
            color=0x000000))

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import os 
import discord
from discord.ext import commands
import datetime
import sys
from discord.ui import Button, View
import psutil
import time
from utils.Tools import *
from discord.ext import commands
from discord.ext.commands import BucketType, cooldown
import requests
from typing import *
from utils import *
from utils.config import BotName, serverLink
from utils import Paginator, DescriptionEmbedPaginator, FieldPagePaginator, TextPaginator
from core import Cog, Tempest, Context
from typing import Optional
import aiosqlite 
import asyncio
import aiohttp


start_time = time.time()


def datetime_to_seconds(thing: datetime.datetime):
  current_time = datetime.datetime.fromtimestamp(time.time())
  return round(
    round(time.time()) +
    (current_time - thing.replace(tzinfo=None)).total_seconds())

tick = "✅"
cross = "❌"


class RoleInfoView(View):
  def __init__(self, role: discord.Role, author_id):
    super().__init__(timeout=180)
    self.role = role
    self.author_id = author_id

  @discord.ui.button(label='Show Permissions',  emoji="•", style=discord.ButtonStyle.secondary)
  async def show_permissions(self, interaction: discord.Interaction, button: Button):
    if interaction.user.id != self.author_id:
          await interaction.response.send_message("Uh oh! That message doesn't belong to you. You must run this command to interact with it.", ephemeral=True)
          return

    permissions = [perm.replace("_", " ").title() for perm, value in self.role.permissions if value]
    permission_text = ", ".join(permissions) if permissions else "None"
    embed = discord.Embed(title=f"Permissions for {self.role.name}", description=permission_text or "No permissions.", color=self.role.color)
    await interaction.response.send_message(embed=embed, ephemeral=True)

    
class OverwritesView(View):
  def __init__(self, channel, author_id):
      super().__init__(timeout=180)
      self.channel = channel
      self.author_id = author_id

  @discord.ui.button(label='Show Overwrites', style=discord.ButtonStyle.primary)
  async def show_overwrites(self, interaction: discord.Interaction, button: Button):
      if interaction.user.id != self.author_id:
          await interaction.response.send_message("Uh oh! That message doesn't belong to you. You must run this command to interact with it.", ephemeral=True)
          return

      overwrites = []
      for target, perms in self.channel.overwrites.items():
          permissions = {
              "View Channel": perms.view_channel,
              "Send Messages": perms.send_messages,
              "Read Message History": perms.read_message_history,
              "Manage Messages": perms.manage_messages,
              "Embed Links": perms.embed_links,
              "Attach Files": perms.attach_files,
              "Manage Channels": perms.manage_channels,
              "Manage Permissions": perms.manage_permissions,
              "Manage Webhooks": perms.manage_webhooks,
              "Create Instant Invite": perms.create_instant_invite,
              "Add Reactions": perms.add_reactions,
              "Mention Everyone": perms.mention_everyone,
              "Kick Members": perms.kick_members,
              "Ban Members": perms.ban_members,
              "Moderate Members": perms.moderate_members,
              "Send TTS Messages": perms.send_tts_messages,
              "Use External Emojis": perms.external_emojis,
              "Use External Stickers": perms.external_stickers,
              "View Audit Log": perms.view_audit_log,
              "Voice Mute Members": perms.mute_members,
              "Voice Deafen Members": perms.deafen_members,
              "Administrator": perms.administrator
          }

          overwrites.append(f"**For {target.name}**\n" +
                            "\n".join(f"  * **{perm}:** {'✅' if value else '❌' if value is False else '⛔'}" for perm, value in permissions.items()))

      embed = discord.Embed(title=f"Overwrites for {self.channel.name}", color=discord.Color.blurple())
      embed.description = "\n".join(overwrites) if overwrites else "No overwrites for this channel."
      embed.set_footer(text="✅ = Allowed, ❌ = Denied, ⛔ = None")
      await interaction.response.send_message(embed=embed, ephemeral=True)




class Extra(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.color = 0x000000
    self.start_time = datetime.datetime.now()

  @commands.hybrid_group(name="banner")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def banner(self, ctx):
    if ctx.invoked_subcommand is None:
      await ctx.send_help(ctx.command)

  @banner.command(name="server")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  async def server(self, ctx):
    if not ctx.guild.banner:
      await ctx.reply(f"{cross} This server doesn't have a banner.")
    else:
      webp = ctx.guild.banner.replace(format='webp')
      jpg = ctx.guild.banner.replace(format='jpg')
      png = ctx.guild.banner.replace(format='png')
      embed = discord.Embed(
        color=self.color,
        description=f"[`PNG`]({png}) | [`JPG`]({jpg}) | [`WEBP`]({webp})"
        if not ctx.guild.banner.is_animated() else
        f"[`PNG`]({png}) | [`JPG`]({jpg}) | [`WEBP`]({webp}) | [`GIF`]({ctx.guild.banner.replace(format='gif')})"
      )
      embed.set_image(url=ctx.guild.banner)
      embed.set_author(name=ctx.guild.name,
                       icon_url=ctx.guild.icon.url
                       if ctx.guild.icon else ctx.guild.default_icon.url)
      embed.set_footer(text=f"Requested By {ctx.author}",
                       icon_url=ctx.author.avatar.url
                       if ctx.author.avatar else ctx.author.default_avatar.url)
      await ctx.reply(embed=embed)

  
  @banner.command(name="user")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  async def _user(self,
                  ctx,
                  member: Optional[Union[discord.Member,
                                         discord.User]] = None):
    if member == None or member == "":
      member = ctx.author
    bannerUser = await self.bot.fetch_user(member.id)
    if not bannerUser.banner:
      await ctx.reply("{} | {} doesn't have a banner.".format(cross, member))
    else:
      webp = bannerUser.banner.replace(format='webp')
      jpg = bannerUser.banner.replace(format='jpg')
      png = bannerUser.banner.replace(format='png')
      embed = discord.Embed(
        color=self.color,
        description=f"[`PNG`]({png}) | [`JPG`]({jpg}) | [`WEBP`]({webp})"
        if not bannerUser.banner.is_animated() else
        f"[`PNG`]({png}) | [`JPG`]({jpg}) | [`WEBP`]({webp}) | [`GIF`]({bannerUser.banner.replace(format='gif')})"
      )
      embed.set_author(name=f"{member}",
                       icon_url=member.avatar.url
                       if member.avatar else member.default_avatar.url)
      embed.set_image(url=bannerUser.banner)
      embed.set_footer(text=f"Requested By {ctx.author}",
                       icon_url=ctx.author.avatar.url
                       if ctx.author.avatar else ctx.author.default_avatar.url)

      await ctx.send(embed=embed)


  
  

  @commands.command(name="uptime", description="Shows the Bot's Uptime.")
  @blacklist_check() 
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def uptime(self, ctx):
      pfp = ctx.author.display_avatar.url

      uptime_seconds = int(round(time.time() - start_time))
      uptime_timedelta = datetime.timedelta(seconds=uptime_seconds)

      uptime_string = f"Up since {datetime.datetime.utcfromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')} UTC"
      uptime_duration_string = f"{uptime_timedelta.days} days, {uptime_timedelta.seconds // 3600} hours, {(uptime_timedelta.seconds // 60) % 60} minutes, {uptime_timedelta.seconds % 60} seconds"

      embed = discord.Embed(title=f"Olympus Uptime", color=self.color)
      embed.add_field(name="__UTC__", value=f"• {uptime_string}\n\n", inline=False)
      embed.add_field(name="__Online Duration__", value=f"✅ {uptime_duration_string}", inline=False)
      embed.set_footer(text=f"Requested by {ctx.author}", icon_url=pfp)

      await ctx.send(embed=embed)

    

  @commands.hybrid_command(name="serverinfo",
                           aliases=["sinfo", "si"],
                           with_app_command=True)
  @blacklist_check() 
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def serverinfo(self, ctx):
        embed = discord.Embed(color=0x000000).set_author(
            name=f"{ctx.guild.name}'s Information",
            icon_url=ctx.guild.me.display_avatar.url if ctx.guild.icon is None else ctx.guild.icon.url
        ).set_footer(
            text=f"Requested By {ctx.author}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )

        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
            embed.timestamp = discord.utils.utcnow()

        c_at = ctx.guild.created_at.strftime("%Y-%m-%d %H:%M:%S")

        embed.add_field(
            name="**__About__**",
            value=f"**Name : ** {ctx.guild.name}\n**ID :** {ctx.guild.id}\n**Owner 👑 :** {ctx.guild.owner} (<@{ctx.guild.owner_id}>)\n**Created At : ** {c_at}\n**Members :** {len(ctx.guild.members)}",
            inline=False
        )

        if ctx.guild.description:
            embed.add_field(
                name="**__Description__**",
                value=ctx.guild.description,
                inline=False
            )

        embed.add_field(
            name="**__General Stats__**",
            value=f"**Verification Level :** {ctx.guild.verification_level}\n**Channels :** {len(ctx.guild.channels)}\n**Roles :** {len(ctx.guild.roles)}\n**Emojis :** {len(ctx.guild.emojis)}\n**Boost Status :** Level {ctx.guild.premium_tier} (Boosts: {ctx.guild.premium_subscription_count})",
            inline=False
        )

        if ctx.guild.features:
            features = "\n".join([f"✅: {feature[:1].upper() + feature[1:].lower().replace('_', ' ')}" for feature in ctx.guild.features])
            embed.add_field(
                name="**__Features__**",
                value=f"{features if len(features) <= 1024 else features[0:1000] + '...and more'}",
                inline=False
            )

        embed.add_field(
            name="**__Channels__**",
            value=f"**Total:** {len(ctx.guild.channels)}\nChannels: {len(ctx.guild.text_channels)} text, {len(ctx.guild.voice_channels)} voice",
            inline=False
        )

        regular_emojis = [emoji for emoji in ctx.guild.emojis if not emoji.animated]
        animated_emojis = [emoji for emoji in ctx.guild.emojis if emoji.animated]
        disabled_emojis = len(ctx.guild.emojis) - len(regular_emojis) - len(animated_emojis)

        embed.add_field(
            name="**__Emoji Info__**",
            value=f"Regular: {len(regular_emojis)}/100\nAnimated: {len(animated_emojis)}/100\nDisabled: {disabled_emojis} regular, {len(animated_emojis)} animated\nTotal Emoji: {len(ctx.guild.emojis)}/200",
            inline=False
        )

        embed.add_field(
            name="**__Boost Status__**",
            value=f"Level: {ctx.guild.premium_tier} [• {ctx.guild.premium_subscription_count} boosts]",
            inline=False
        )

        roles = ctx.guild.roles
        roles_list = [role.mention for role in roles]
        roles_count = len(roles_list)
        roles_display = "\n".join(roles_list[:10])

        if roles_count > 10:
            roles_display += f"\n...and {roles_count - 10} more"

        embed.add_field(
            name=f"**__Server Roles__ [ {roles_count} ]**",
            value=roles_display,
            inline=False
        )

        if ctx.guild.banner:
            embed.set_image(url=ctx.guild.banner)


        await ctx.send(embed=embed)
        

  
  @commands.hybrid_command(name="userinfo",
                           aliases=["whois", "ui"],
                           usage="Userinfo [user]",
                           with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  async def _userinfo(self,
                      ctx,
                      member: Optional[Union[discord.Member,
                                             discord.User]] = None):
    if member == None or member == "":
      member = ctx.author
    elif member not in ctx.guild.members:
      member = await self.bot.fetch_user(member.id)

    badges = ""
    if member.public_flags.hypesquad:
      badges += "HypeSquad Events, "
    if member.public_flags.hypesquad_balance:
      badges += "HypeSquad Balance, "
    if member.public_flags.hypesquad_bravery:
      badges += "HypeSquad Bravery, "
    if member.public_flags.hypesquad_brilliance:
      badges += "HypeSquad Brilliance, "
    if member.public_flags.early_supporter:
      badges += "Early Supporter, "
    if member.public_flags.active_developer:
      badges += "Active Developer, "
    if member.public_flags.verified_bot_developer:
      badges += "Early Verified Bot Developer, "
    if member.public_flags.discord_certified_moderator:
      badges += "Moderators Program Alumni, "
    if member.public_flags.staff:
      badges += "Discord Staff, "
    if member.public_flags.partner:
      badges += "Partnered Server Owner "
    if badges == None or badges == "":
      badges += f"{cross}"

    if member in ctx.guild.members:
      nickk = f"{member.nick if member.nick else 'None'}"
      joinedat = f"<t:{round(member.joined_at.timestamp())}:R>"
    else:
      nickk = "None"
      joinedat = "None"

    kp = ""
    if member in ctx.guild.members:
      if member.guild_permissions.kick_members:
        kp += "Kick Members"
      if member.guild_permissions.ban_members:
        kp += " , Ban Members"
      if member.guild_permissions.administrator:
        kp += " , Administrator"
      if member.guild_permissions.manage_channels:
        kp += " , Manage Channels"
        
      if  member.guild_permissions.manage_guild:
        kp += " , Manage Server"
        
      if member.guild_permissions.manage_messages:
        kp += " , Manage Messages"
      if member.guild_permissions.mention_everyone:
        kp += " , Mention Everyone"
      if member.guild_permissions.manage_nicknames:
        kp += " , Manage Nicknames"
      if member.guild_permissions.manage_roles:
        kp += " , Manage Roles"
      if member.guild_permissions.manage_webhooks:
        kp += " , Manage Webhooks"
      if member.guild_permissions.manage_emojis:
        kp += " , Manage Emojis"

      if kp is None or kp == "":
        kp = "None"

    if member in ctx.guild.members:
      if member == ctx.guild.owner:
        aklm = "Server Owner"
      elif member.guild_permissions.administrator:
        aklm = "Server Admin"
      elif member.guild_permissions.ban_members or member.guild_permissions.kick_members:
        aklm = "Server Moderator"
      else:
        aklm = "Server Member"

    bannerUser = await self.bot.fetch_user(member.id)
    embed = discord.Embed(color=self.color)
    embed.timestamp = discord.utils.utcnow()
    if not bannerUser.banner:
      pass
    else:
      embed.set_image(url=bannerUser.banner)
    embed.set_author(name=f"{member.name}'s Information",
                     icon_url=member.avatar.url
                     if member.avatar else member.default_avatar.url)
    embed.set_thumbnail(
      url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="__General Information__",
                    value=f"""
**Name:** {member}
**ID:** {member.id}
**Nickname:** {nickk}
**Bot?:** {'✅ Yes' if member.bot else '❌ No'}
**Badges:** {badges}
**Account Created:** <t:{round(member.created_at.timestamp())}:R>
**Server Joined:** {joinedat}
            """,
                    inline=False)
    if member in ctx.guild.members:
      r = (', '.join(role.mention for role in member.roles[1:][::-1])
           if len(member.roles) > 1 else 'None.')
      embed.add_field(name="__Role Info__",
                      value=f"""
**Highest Role:** {member.top_role.mention if len(member.roles) > 1 else 'None'}
**Roles [{f'{len(member.roles) - 1}' if member.roles else '0'}]:** {r if len(r) <= 1024 else r[0:1006] + ' and more...'}
**Color:** {member.color if member.color else '99aab5'}
                """,
                      inline=False)
    if member in ctx.guild.members:
      embed.add_field(
        name="__Extra__",
        value=
        f"**Boosting:** {f'<t:{round(member.premium_since.timestamp())}:R>' if member in ctx.guild.premium_subscribers else 'None'}\n**Voice •:** {'None' if not member.voice else member.voice.channel.mention}",
        inline=False)
    if member in ctx.guild.members:
      embed.add_field(name="__Key Permissions__",
                      value=", ".join([kp]),
                      inline=False)
    if member in ctx.guild.members:
      embed.add_field(name="__Acknowledgement__",
                      value=f"{aklm}",
                      inline=False)
    if member in ctx.guild.members:
      embed.set_footer(text=f"Requested by {ctx.author}",
                       icon_url=ctx.author.avatar.url
                       if ctx.author.avatar else ctx.author.default_avatar.url)
    else:
      if member not in ctx.guild.members:
        embed.set_footer(text=f"{member.name} not in this server.",
                         icon_url=ctx.author.avatar.url if ctx.author.avatar
                         else ctx.author.default_avatar.url)
    await ctx.send(embed=embed)



  @commands.hybrid_command(name='roleinfo', aliases=["ri"], help="Displays information about a specified role.")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def roleinfo(self, ctx, role: discord.Role):
    members = role.members
    created_at = role.created_at.strftime("%Y-%m-%d %H:%M:%S")

    embed = discord.Embed(
      title=f"Role Information - {role.name}",
      color=role.color,
      timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1205191291323940874.png")
    embed.add_field(name="__General Information__", value=f"**ID:** {role.id}\n**Name:** {role.name}\n**Mention:** <@&{role.id}>\n**Color:** {str(role.color)}\n**Total Member:** {len(role.members)}\n", inline=True)
    total_roles = len(ctx.guild.roles) - 0
    role_position = total_roles - role.position
    embed.add_field(name="Position", value=str(role_position), inline=True)
    embed.add_field(name="Mentionable", value=str(role.mentionable), inline=True)
    embed.add_field(name="Hoisted", value=str(role.hoist), inline=True)
    embed.add_field(name="Managed", value=str(role.managed), inline=True)
    embed.add_field(name="Created At", value=created_at, inline=True)
    embed.set_footer(text=f"Requested By {ctx.author}",
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)

    view = RoleInfoView(role, ctx.author.id)
    await ctx.send(embed=embed, view=view)





  @commands.command(name="boostcount",
                    help="Shows boosts count",
                    usage="boosts",
                    aliases=["bc"],
                    with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def boosts(self, ctx):
    await ctx.send(
      embed=discord.Embed(title=f"• Boosts Count Of {ctx.guild.name}",
                          description="**Total `%s` boosts**" %
                          (ctx.guild.premium_subscription_count),
                          color=self.color))

  @commands.hybrid_group(name="list",
                         invoke_without_command=True,
                         with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def __list_(self, ctx: commands.Context):
    if ctx.subcommand_passed is None:
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)

  @__list_.command(name="boosters",
                   aliases=["boost", "booster"],
                   usage="List boosters",
                   help="List of boosters in the Guild",
                   with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def list_boost(self, ctx):
    guild = ctx.guild
    entries = [
      f"`#{no}.` [{mem}](https://discord.com/users/{mem.id}) [{mem.mention}] - <t:{round(mem.premium_since.timestamp())}:R>"
      for no, mem in enumerate(guild.premium_subscribers, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=
      f"List of Boosters in {guild.name} - {len(guild.premium_subscribers)}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="bans", help= "List of all banned members in Guild", aliases=["ban"], with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(view_audit_log=True)
  @commands.bot_has_permissions(view_audit_log=True)
  async def list_ban(self, ctx):
    bans = [member async for member in ctx.guild.bans()]
    if len(bans) == 0:
      return await ctx.reply("There aren't any banned users in this guild.", mention_author=False)
    else:
      mems = ([
      member async for member in ctx.guild.bans()
    ])
      guild = ctx.guild
      entries = [
      f"`#{no}.` {mem}"
      for no, mem in enumerate(mems, start=1)
    ]
      embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"Banned Users in {guild.name} - {len(bans)}",
      description="",
      per_page=10).get_pages()
      paginator = Paginator(ctx, embeds)
      await paginator.paginate()

  @__list_.command(
    name="inrole",
    aliases=["inside-role"],
    help="List of members that are in the specified role",
    with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def list_inrole(self, ctx, role: discord.Role):
    guild = ctx.guild
    entries = [
      f"`#{no}.` [{mem}](https://discord.com/users/{mem.id}) [{mem.mention}] - <t:{int(mem.created_at.timestamp())}:D>"
      for no, mem in enumerate(role.members, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"List of Members in {role} - {len(role.members)}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="emojis",
                   aliases=["emoji"],
                   help="List of emojis in the Guild with ids",
                   with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def list_emojis(self, ctx):
    guild = ctx.guild
    entries = [
      f"`#{no}.` {e} - `{e}`"
      for no, e in enumerate(ctx.guild.emojis, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"List of Emojis in {guild.name} - {len(ctx.guild.emojis)}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="roles",
                   aliases=["role"],
                   help="List of all roles in the server with ids",
                   with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.has_permissions(manage_roles=True)
  async def list_roles(self, ctx):
    guild = ctx.guild
    entries = [
      f"`#{no}.` {e.mention} - `[{e.id}]`"
      for no, e in enumerate(ctx.guild.roles, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"List of Roles in {guild.name} - {len(ctx.guild.roles)}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="bots",
                   aliases=["bot"],
                   help="List of All Bots in a server",
                   with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def list_bots(self, ctx):
    guild = ctx.guild
    people = filter(lambda member: member.bot, ctx.guild.members)
    people = sorted(people, key=lambda member: member.joined_at)
    entries = [
      f"`#{no}.` [{mem}](https://discord.com/users/{mem.id}) [{mem.mention}]"
      for no, mem in enumerate(people, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"Bots in {guild.name} - {len(people)}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="admins",
                   aliases=["admin"],
                   help="List of all Admins of the Guild",
                   with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def list_admin(self, ctx):
    mems = ([
      mem for mem in ctx.guild.members
      if mem.guild_permissions.administrator
    ])
    mems = sorted(mems, key=lambda mem: not mem.bot)
    admins = len([
      mem for mem in ctx.guild.members
      if mem.guild_permissions.administrator
    ])
    guild = ctx.guild
    entries = [
      f"`#{no}.` [{mem}](https://discord.com/users/{mem.id}) [{mem.mention}] - <t:{int(mem.created_at.timestamp())}:D>"
      for no, mem in enumerate(mems, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"Admins in {guild.name} - {admins}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="invoice", help="List of all users in a voice channel", aliases=["invc"], with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def listusers(self, ctx):
    if not ctx.author.voice:
      return await ctx.send("You are not connected to a voice channel")
    members = ctx.author.voice.channel.members
    entries = [
      f"`[{n}]` | {member} [{member.mention}]"
      for n, member in enumerate(members, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      description="",
      title=f"Voice List of {ctx.author.voice.channel.name} - {len(members)}",
      color=self.color).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="moderators", help= "List of All Admins of a server", aliases=["mods"], with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def list_mod(self, ctx):
    membs = ([
      mem for mem in ctx.guild.members
      if mem.guild_permissions.ban_members
      or mem.guild_permissions.kick_members
    ])
    mems = filter(lambda member: member.bot, ctx.guild.members)
    mems = sorted(membs, key=lambda mem: mem.joined_at)
    admins = len([
      mem for mem in ctx.guild.members
      if mem.guild_permissions.ban_members
      or mem.guild_permissions.kick_members
    ])
    guild = ctx.guild
    entries = [
      f"`#{no}.` [{mem}](https://discord.com/users/{mem.id}) [{mem.mention}] - <t:{int(mem.created_at.timestamp())}:D>"
      for no, mem in enumerate(mems, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"Mods in {guild.name} - {admins}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="early", aliases=["sup"], help= "List of members that have Early Supporter badge.", with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def list_early(self, ctx):
    mems = ([
      memb for memb in ctx.guild.members
      if memb.public_flags.early_supporter
    ])
    mems = sorted(mems, key=lambda memb: memb.created_at)
    admins = len([
      memb for memb in ctx.guild.members
      if memb.public_flags.early_supporter
    ])
    guild = ctx.guild
    entries = [
      f"`#{no}.` [{mem}](https://discord.com/users/{mem.id})  [{mem.mention}] - <t:{int(mem.created_at.timestamp())}:D>"
      for no, mem in enumerate(mems, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"Early Supporters Id's in {guild.name} - {admins}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="activedeveloper", help= "List of members that have Active Developer badge.",
                   aliases=["activedev"],
                   with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def list_activedeveloper(self, ctx):
    mems = ([
      memb for memb in ctx.guild.members
      if memb.public_flags.active_developer
    ])
    mems = sorted(mems, key=lambda memb: memb.created_at)
    admins = len([
      memb for memb in ctx.guild.members
      if memb.public_flags.active_developer
    ])
    guild = ctx.guild
    entries = [
      f"`#{no}.` [{mem}](https://discord.com/users/{mem.id}) [{mem.mention}] - <t:{int(mem.created_at.timestamp())}:D>"
      for no, mem in enumerate(mems, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"Active Developer Id's in {guild.name} - {admins}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="createdat", help= "List of Account Creation Date of all Users", with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def list_cpos(self, ctx):
    mems = ([memb for memb in ctx.guild.members])
    mems = sorted(mems, key=lambda memb: memb.created_at)
    admins = len([memb for memb in ctx.guild.members])
    guild = ctx.guild
    entries = [
      f"`[{no}]` | [{mem}](https://discord.com/users/{mem.id}) - <t:{int(mem.created_at.timestamp())}:D>"
      for no, mem in enumerate(mems, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"Creation every id in {guild.name} - {admins}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()

  @__list_.command(name="joinedat", help= "List of Guild Joined date of all Users", with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def list_joinpos(self, ctx):
    mems = ([memb for memb in ctx.guild.members])
    mems = sorted(mems, key=lambda memb: memb.joined_at)
    admins = len([memb for memb in ctx.guild.members])
    guild = ctx.guild
    entries = [
      f"`#{no}.` [{mem}](https://discord.com/users/{mem.id}) Joined At - <t:{int(mem.joined_at.timestamp())}:D>"
      for no, mem in enumerate(mems, start=1)
    ]
    embeds = DescriptionEmbedPaginator(
      entries=entries,
      title=f"Join Position of every user in {guild.name} - {admins}",
      description="",
      per_page=10).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()




  @commands.command(name="joined-at",
                    help="Shows when a user joined",
                    usage="joined-at [user]",
                    with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def joined_at(self, ctx):
    joined = ctx.author.joined_at.strftime("%a, %d %b %Y %I:%M %p")
    await ctx.send(embed=discord.Embed(
      title="joined-at", description="**`%s`**" % (joined), color=self.color))

  @commands.command(name="github", usage="github [search]")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def github(self, ctx, *, search_query):
    json = requests.get(
      f"https://api.github.com/search/repositories?q={search_query}").json()

    if json["total_count"] == 0:
      await ctx.send(f"No matching repositories found with the name: {search_query}")
    else:
      await ctx.send(
        f"Found result for '{search_query}':\n{json['items'][0]['html_url']}")

  @commands.hybrid_command(name="vcinfo",
                           description="View information about a voice channel.",
                           help="View information about a voice channel.", 
                           usage="<VoiceChannel>",
                           with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def vcinfo(self, ctx, channel: discord.VoiceChannel = None):
    if channel is None:
      await ctx.reply(f"{cross} Please provide a valid voice channel.")
      return
    embed = discord.Embed(title=f"Voice Channel Info for: {channel.name}", color=self.color)
    embed.add_field(name="ID", value=channel.id, inline=True)
    embed.add_field(name="Members", value=len(channel.members), inline=True)
    embed.add_field(name="Bitrate", value=f"{channel.bitrate/1000} kbps", inline=True)
    embed.add_field(name="Created At", value=channel.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
    embed.add_field(name="Region", value=channel.rtc_region, inline=True)

    if channel.user_limit:
      embed.add_field(name="User Limit", value=channel.user_limit, inline=True)

    if channel.overwrites:
      overwrites = []
      for role, permissions in channel.overwrites.items():
        overwrites.append(f"**{role}**: {permissions}")
      embed.add_field(name="Overwrites", value="\n".join(overwrites), inline=False)

    view = View()
    view.add_item(Button(label="Join", style=discord.ButtonStyle.green, url=f"https://discord.com/channels/{ctx.guild.id}/{channel.id}"))
    view.add_item(Button(label="Invite", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{ctx.guild.id}/{channel.id}/invite"))

    await ctx.send(embed=embed, view=view)


  @commands.hybrid_command(name="channelinfo",
     aliases=['cinfo', 'ci'],
     description='Get information about a channel.',
     help='Get information about a channel.',
     usage="<Channel>",
     with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def channelinfo(self, ctx, channel: discord.TextChannel = None):
    if channel is None:
      channel = ctx.channel
      
    embed = discord.Embed(title=f"Channel Info - {channel.name}",
    color=0x000000)
    embed.add_field(name="ID", value=channel.id, inline=False)
    embed.add_field(name="Created At", value=channel.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=False)
    embed.add_field(name="Topic", value=channel.topic if channel.topic else "None", inline=False)
    embed.add_field(name="Slowmode", value=f"{channel.slowmode_delay} seconds" if channel.slowmode_delay else "None", inline=False)
    embed.add_field(name="NSFW", value=channel.is_nsfw(), inline=False)
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1205345282158501899.png")
    embed.set_footer(text=f"Requested By {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      
      
    view = OverwritesView(channel, ctx.author.id)
    view.add_item(Button(label="Redirect Channel", style=discord.ButtonStyle.green, url=f"https://discord.com/channels/{ctx.guild.id}/{channel.id}"))
      
    await ctx.send(embed=embed, view=view)


  @commands.command(name="ping", aliases=['latency'],
                      help="Checks the bot latency.",
                      with_app_command=True)
  @ignore_check()
  @blacklist_check()
  @commands.cooldown(1, 2, commands.BucketType.user)
  async def ping(self, ctx):
    msg = await ctx.reply(f"🏓 Pong **{round(self.bot.latency * 1000, 2)}ms**")
    
    db_latency = None
    try:
      async with aiosqlite.connect("db/afk.db") as db:
        start_time = time.perf_counter()
        await db.execute("SELECT 1")
        end_time = time.perf_counter()
        db_latency = (end_time - start_time) * 1000
        db_latency = round(db_latency, 2)
    except Exception as e:
      print(f"Error measuring database latency: {e}")
      db_latency = "N/A"

    await msg.edit(content=f"🏓 Pong **{round(self.bot.latency * 1000, 2)}ms** | Database: **{db_latency}ms**")



  
  @commands.command(name="permissions", aliases= ["perms"],
                           help="Check and list the key permissions of a specific user",
                           usage="perms <user>",
                           with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def keyperms(self, ctx, member: discord.Member):
    key_permissions = []

    if member.guild_permissions.create_instant_invite:
      key_permissions.append("Create Instant Invite")
    if member.guild_permissions.kick_members:
      key_permissions.append("Kick Members")
    if member.guild_permissions.ban_members:
      key_permissions.append("Ban Members")
    if member.guild_permissions.administrator:
      key_permissions.append("Administrator")
    if member.guild_permissions.manage_channels:
      key_permissions.append("Manage Channels")
    if member.guild_permissions.manage_messages:
      key_permissions.append("Manage Messages")
    if member.guild_permissions.mention_everyone:
      key_permissions.append("Mention Everyone")
    if member.guild_permissions.manage_nicknames:
      key_permissions.append("Manage Nicknames")
    if member.guild_permissions.manage_roles:
      key_permissions.append("Manage Roles")
    if member.guild_permissions.manage_webhooks:
      key_permissions.append("Manage Webhooks")
    if member.guild_permissions.manage_emojis:
      key_permissions.append("Manage Emojis")
    if member.guild_permissions.manage_guild:
      key_permissions.append("Manage Server")
    if member.guild_permissions.manage_permissions:
      key_permissions.append("Manage Permissions")
    if member.guild_permissions.manage_threads:
      key_permissions.append("Manage Threads")
    if member.guild_permissions.moderate_members:
      key_permissions.append("Moderate Members")
    if member.guild_permissions.move_members:
      key_permissions.append("Move Members")
    if member.guild_permissions.mute_members:
      key_permissions.append("Mute Members (VC)")
    if member.guild_permissions.deafen_members:
      key_permissions.append("Deafen Members")
    if member.guild_permissions.priority_speaker:
      key_permissions.append("Priority Speaker")
    if member.guild_permissions.stream:
      key_permissions.append("Stream")
    
    
    

    permissions_list = ", ".join(key_permissions) if key_permissions else "None"

    embed = discord.Embed(title=f"Key Permissions of {member}",
                          color=0x000000)
    embed.add_field(name="__**Key Permissions**__", value=permissions_list, inline=False)

    await ctx.reply(embed=embed)

  




  @commands.hybrid_command(name="report",
                           aliases=["bug"],
                           usage='Report <bug>',
                           description='Report a bug to the Development team.',
                           help='Report a bug to the Development team.',
                           with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 30, commands.BucketType.channel)
  async def report(self, ctx, *, bug):
    channel = self.bot.get_channel(1271825687438954557)
    embed = discord.Embed(title='Bug Reported',
                          description=bug,
                          color=0x000000)
    embed.add_field(name='Reported By',
                    value=f'{ctx.author.name}',
                    inline=True)
    embed.add_field(name="Server", value=ctx.guild.name, inline=False)
    embed.add_field(name="Channel", value=ctx.channel.name, inline=False)
    await channel.send(embed=embed)
    confirm_embed = discord.Embed(title="✅ Bug Reported",
      description="Thank you for reporting the bug. We will look into it.",
      color=0x000000)
    await ctx.reply(embed=confirm_embed)

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out support or DM me.
"""
import discord
from discord.ext import commands
from discord.ui import View, Button
import aiosqlite
from utils.Tools import *

class Extraowner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        self.db = await aiosqlite.connect('db/anti.db')
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS extraowners (
                guild_id INTEGER PRIMARY KEY,
                owner_id INTEGER
            )
        ''')
        await self.db.commit()

    @commands.hybrid_command(name='extraowner', aliases=["owner"], help="Adds Extraowner to the server")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def extraowner(self, ctx, option: str = None, user: discord.Member = None):
        guild_id = ctx.guild.id

        if ctx.guild.member_count < 2:
            embed = discord.Embed(
                description="❌ | Your Server Doesn't Meet My 30 Member Criteria",
                color=0x000000
            )
            await ctx.send(embed=embed)
            return

        Olympus = ['1070619070468214824', '677952614390038559']
        if ctx.author.id != ctx.guild.owner_id and str(ctx.author.id) not in Olympus:
            embed = discord.Embed(title="❌ Access Denied",
                                  description="Only Server Owner Can Run This Command",
                                  color=0x000000
            )
            await ctx.send(embed=embed)
            return

        if option is None:
            pre = ctx.prefix
            embed = discord.Embed(
                title="__**Extra Owner**__",
                description="Extraowners can adjust server antinuke settings & manage whitelist events, so careful consideration is essential before assigning it to someone.",
                color=0x000000
            )
            embed.add_field(name="__**Extraowner Set**__", value=f"To Set Extra Owner, Use - **{pre}extraowner set @user**")
            embed.add_field(name="__**Extraowner Reset**__", value=f"To Reset Extra Owner, Use - **{pre}extraowner reset**")
            embed.add_field(name="__**Extraowner View**__", value=f"To View Extra Owner, Use - **{pre}extraowner view**")
            embed.set_thumbnail(url=ctx.bot.user.avatar.url)
            await ctx.reply(embed=embed)
            return

        
        if option.lower() == 'set':
            if user is None or user.bot:
                embed = discord.Embed(title="❌ Error",
                    description="Please Provide a Valid User Mention or ID to Set as Extra Owner!",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
                return

            
            view = ConfirmView(ctx)
            embed = discord.Embed(
                title="Confirm Action",
                description=f"**Are you sure you want to set {user.mention} as the Extra Owner?**",
                color=0x000000
            )
            message = await ctx.reply(embed=embed, view=view)
            await view.wait()

            if view.value is None:
                await message.edit(content="⏳ Confirmation timed out.", embed=None, view=None)
            elif view.value:
                await self.db.execute('INSERT OR REPLACE INTO extraowners (guild_id, owner_id) VALUES (?, ?)', (guild_id, user.id))
                await self.db.commit()
                embed = discord.Embed(title="✅ Success",
                    description=f"Added {user.mention} As Extraowner",
                    color=0x000000
                )
                await message.edit(embed=embed, view=None)
            else:
                await message.edit(content="❌ Action cancelled.", embed=None, view=None)

        
        elif option.lower() == 'reset':
            async with self.db.execute('SELECT owner_id FROM extraowners WHERE guild_id = ?', (guild_id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                embed = discord.Embed(title="❌ Error",
                    description="No extra owner has been designated for this guild.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
            else:
                
                view = ConfirmView(ctx)
                embed = discord.Embed(
                    title="Confirm Action",
                    description="**Are you sure you want to reset the Extra Owner?**",
                    color=0x000000
                )
                message = await ctx.reply(embed=embed, view=view)
                await view.wait()

                if view.value is None:
                    await message.edit(content="⏳ Confirmation timed out.", embed=None, view=None)
                elif view.value:
                    await self.db.execute('DELETE FROM extraowners WHERE guild_id = ?', (guild_id,))
                    await self.db.commit()
                    embed = discord.Embed(title="✅ Success",
                        description="Disabled Extraowner Configuration!",
                        color=0x000000
                    )
                    await message.edit(embed=embed, view=None)
                else:
                    await message.edit(content="❌ Action canceled.", embed=None, view=None)

        elif option.lower() == 'view':
            async with self.db.execute('SELECT owner_id FROM extraowners WHERE guild_id = ?', (guild_id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                embed = discord.Embed(title="❌ Error",
                    description="No extra owner is currently assigned.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
            else:
                embed = discord.Embed(
                    description=f"Current Extraowner is <@{row[0]}>",
                    color=0x000000
                )
                await ctx.reply(embed=embed)

class ConfirmView(View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You cannot interact with this confirmation.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.value = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.value = False
        self.stop()

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from typing import Union
import wavelink
from utils.Tools import *

class FilterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_filters = {}

    async def apply_filter(self, ctx: commands.Context, filter_name: str):
        player: Union[wavelink.Player, None] = ctx.voice_client
        if not player or not player.playing:
            await ctx.send("I'm not playing anything.")
            return

        if ctx.author.voice is None or ctx.author.voice.channel != player.channel:
            await ctx.send("You need to be in the same voice channel as me.")
            return

        filters = wavelink.Filters()

        if filter_name == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.2, rate=1)
        elif filter_name == "bassboost":
            filters.equalizer.set(bands=[{"band": 0, "gain": 0.5}, {"band": 1, "gain": 0.5}, {"band": 2, "gain": 0.5}])
        elif filter_name == "vaporwave":
            filters.timescale.set(rate=0.85, pitch=0.85)
        elif filter_name == "karaoke":
            filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
        elif filter_name == "tremolo":
            filters.tremolo.set(depth=0.5, frequency=14.0)
        elif filter_name == "vibrato":
            filters.vibrato.set(depth=0.5, frequency=14.0)
        elif filter_name == "rotation":
            filters.rotation.set(rotation_hz=5.0)
        elif filter_name == "distortion":
            filters.distortion.set(
                sin_offset=0.0,
                sin_scale=1.0,
                cos_offset=0.0,
                cos_scale=1.0,
                tan_offset=0.0,
                tan_scale=1.0,
                offset=0.0,
                scale=1.0
            )
        elif filter_name == "channelmix":
            filters.channel_mix.set(left_to_left=0.5, left_to_right=0.5, right_to_left=0.5, right_to_right=0.5)

        await player.set_filters(filters)
        self.active_filters[ctx.guild.id] = filter_name
        await ctx.send(embed=discord.Embed(description=f"Filter set to **{filter_name}**.", color=discord.Color.green()))

    @commands.hybrid_group(invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def filter(self, ctx: commands.Context):
        await ctx.send("Use `filter enable` to enable a filter or `filter disable` to disable the current filter.")

    @filter.command(help="Enable a filter.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def enable(self, ctx: commands.Context):
        player: Union[wavelink.Player, None] = ctx.voice_client
        if not player or not player.playing:
            await ctx.send("I'm not connected to a voice channel.")
            return

        if ctx.author.voice is None or ctx.author.voice.channel != player.channel:
            await ctx.send("You need to be in the same voice channel as me.")
            return

        filter_options = [

            discord.SelectOption(label="Vaporwave", description="Apply vaporwave effect"),
            discord.SelectOption(label="Nightcore", description="Apply nightcore effect"),
            discord.SelectOption(label="Vibrato", description="Apply vibrato effect"),
            discord.SelectOption(label="Tremolo", description="Apply tremolo effect"),
            discord.SelectOption(label="Bassboost", description="Apply bass boost effect"),
            discord.SelectOption(label="Karaoke", description="Apply karaoke effect"),
            discord.SelectOption(label="Rotation", description="Apply rotation effect"),
            discord.SelectOption(label="Distortion", description="Apply distortion effect"),
            discord.SelectOption(label="Channelmix", description="Apply channel mix effect"),
        ]

        class FilterSelect(discord.ui.View):
            @discord.ui.select(placeholder="Choose a filter...", options=filter_options)
            async def select_filter(self, interaction: discord.Interaction, select: discord.ui.Select):
                await interaction.response.defer()
                selected_filter = select.values[0].lower()
                await self.cog.apply_filter(ctx, selected_filter)
                #await interaction.message.delete()  
                self.disable_all()  

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.message.delete()  
                self.disable_all()  
            def disable_all(self):
                for child in self.children:
                    child.disabled = True
                self.stop()  

        view = FilterSelect()
        view.cog = self

        current_filter = self.active_filters.get(ctx.guild.id, "None")
        embed = discord.Embed(title="Enable Filter", description="Choose a filter to apply:", color=discord.Color.blue())
        embed.add_field(name="Current Filter", value=current_filter, inline=False)
        await ctx.send(embed=embed, view=view)

    @filter.command(help="Disable the current filter.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def disable(self, ctx: commands.Context):
        player: Union[wavelink.Player, None] = ctx.voice_client
        if not player or not player.playing:
            await ctx.send("I'm not connected to a voice channel.")
            return

        if ctx.author.voice is None or ctx.author.voice.channel != player.channel:
            await ctx.send("You need to be in the same voice channel as me.")
            return

        filters = wavelink.Filters()
        await player.set_filters(filters)
        self.active_filters.pop(ctx.guild.id, None)
        await ctx.send(embed=discord.Embed(description="Filter disabled.", color=discord.Color.red()))

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
##################################
import discord
import requests
import aiohttp
import datetime
import random
import os
from discord.ext import commands
from random import randint
from utils.Tools import *
from core import Cog, Tempest, Context
from utils.config import *
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageOps
import io


def RandomColor():
  randcolor = discord.Color(random.randint(0x000000, 0xFFFFFF))
  return randcolor

RAPIDAPI_HOST = "truth-dare.p.rapidapi.com"
RAPIDAPI_KEY = "1cd7c71534msh2544b357ec07ad8p18fa0bjsn1358eef1f8e9"

class Fun(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.giphy_token = 'y3KcqQTdiS0RYcpNJrWn8hFGglKqX4is'
    self.google_api_key = 'AIzaSyA022fwm_TOQcYTg1N_ohqqIj_RUFUM9BY'
    self.search_engine_id = '2166875ec165a6c21' 


  async def download_avatar(self, url):
      async with aiohttp.ClientSession() as session:
          async with session.get(url) as resp:
              if resp.status != 200:
                  return None
              data = await resp.read()
              return Image.open(io.BytesIO(data)).convert("RGBA")

  def circle_avatar(self, avatar):
      mask = Image.new("L", avatar.size, 0)
      draw = ImageDraw.Draw(mask)
      draw.ellipse((0, 0) + avatar.size, fill=255)
      avatar = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
      avatar.putalpha(mask)
      return avatar
      
  async def add_role(self, *, role: int, member: discord.Member):
    if member.guild.me.guild_permissions.manage_roles:
      role = discord.Object(id=int(role))
      await member.add_roles(role, reason=f"{NAME} | Role Added ")

  async def remove_role(self, *, role: int, member: discord.Member):
    if member.guild.me.guild_permissions.manage_roles:
      role = discord.Object(id=int(role))
      await member.remove_roles(role, reason=f"{NAME} | Role Removed")


  async def fetch_data(self, endpoint):
        async with aiohttp.ClientSession() as session:
            headers = {
                "X-RapidAPI-Host": RAPIDAPI_HOST,
                "X-RapidAPI-Key": RAPIDAPI_KEY
            }
            async with session.get(f"https://{RAPIDAPI_HOST}{endpoint}", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
                    

  async def fetch_image(self, ctx, endpoint):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://nekos.life/api/v2/img/{endpoint}") as response:
            if response.status == 200:
                data = await response.json()
                return data["url"]
            else:
                await ctx.send("Failed to fetch image.")


    

  async def fetch_action_image(self, action):
        url = f"https://api.waifu.pics/sfw/{action}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json().get('url')
        except requests.exceptions.RequestException:
            return None

  @commands.command()
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def mydog(self, ctx, user: discord.User):
      processing= await ctx.reply("• Processing Image...")
      base_image_path = "data/pictures/mydog.jpg"
      base_image = Image.open(base_image_path).convert("RGBA")

      author_avatar_url = ctx.author.display_avatar.url
      user_avatar_url = user.display_avatar.url

      author_avatar = await self.download_avatar(author_avatar_url)
      user_avatar = await self.download_avatar(user_avatar_url)

      if author_avatar is None or user_avatar is None:
          await ctx.send("Failed to retrieve avatars.")
          return

      author_avatar = self.circle_avatar(author_avatar.resize((230, 230)))
      user_avatar = self.circle_avatar(user_avatar.resize((310, 310)))

      base_image.paste(author_avatar, (370, 0), author_avatar)
      base_image.paste(user_avatar, (0, 220), user_avatar)

      final_buffer = io.BytesIO()
      base_image.save(final_buffer, "PNG")
      final_buffer.seek(0)

      file = discord.File(fp=final_buffer, filename="mydog.png")
      await ctx.reply(file=file)
      await processing.delete()

    
  @commands.command(name="image", help="Search for an image and display a random one.", aliases=["img"], with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def image(self, ctx, *, search_query: str):
        if not ctx.channel.is_nsfw():
            await ctx.reply("This command can only be used in NSFW (age-restricted) channels.", ephemeral=True)
            return
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://www.googleapis.com/customsearch/v1?key={self.google_api_key}&cx={self.search_engine_id}&q={search_query}&searchType=image") as response:
                data = await response.json()
                if "items" in data:
                    image = discord.Embed(title=f"Random Image for '{search_query}'", color=discord.Color.random())
                    image.set_image(url=random.choice(data["items"])["link"])
                    await ctx.reply(embed=image)
                else:
                    await ctx.reply("No images found for that search query.")

  


  @commands.command(name="howgay",
                    aliases=['gay'],
                    help="check someone gay percentage",
                    usage="Howgay <person>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def howgay(self, ctx, *, person):
    embed = discord.Embed(title="• About your gayness", color=discord.Color.random())
    responses = random.randrange(1, 150)
    embed.description = f'**{person} is {responses}% Gay** :rainbow:'
    embed.set_footer(text=f'How gay are you? - {ctx.author.name}')
    await ctx.reply(embed=embed)


  @commands.command(name="lesbian",
                    aliases=['lesbo'],
                    help="check someone lesbian percentage",
                    usage="lesbian <person>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def lesbian(self, ctx, *, person):
    embed = discord.Embed(title="• Lesbian Meter", color=discord.Color.random())
    responses = random.randrange(1, 150)
    embed.description = f'**{person} is {responses}% Lesbian** •'
    embed.set_footer(text=f'How lesbian are you? - {ctx.author.name}')
    await ctx.reply(embed=embed)

  @commands.command(name="chutiya",
                    aliases=['chu'],
                    help="check someone chootiyapa percentage",
                    usage="Chutiya <person>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def chutiya(self, ctx, *, person):
    embed = discord.Embed(title="• About your Chumtiyapa", color=discord.Color.random())
    responses = random.randrange(1, 150)
    embed.description = f'**Abbe {person} to {responses}% Chootiya Ha** 😂'
    embed.set_footer(text=f'How chutiya are you? - {ctx.author.name}')
    await ctx.reply(embed=embed)

  @commands.command(name="tharki",
                    help="check someone tharkipan percentage",
                    usage="Tharki <person>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def tharki(self, ctx, *, person):
    embed = discord.Embed(title="• About your Tharkipan", color=discord.Color.random())
    responses = random.randrange(1, 150)
    embed.description = f'**Sala {person} to {responses}% Tharki Nikla** 😂'
    embed.set_footer(text=f'How tharki are you? - {ctx.author.name}')
    await ctx.reply(embed=embed)

  @commands.command(name="horny",
                    aliases=['horniness'],
                    help="check someone horniness percentage",
                    usage="Horny <person>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def horny(self, ctx, *, person):
    embed = discord.Embed(title="• About your horniness", color=discord.Color.random())
    responses = random.randrange(1, 150)
    embed.description = f'**{person} is {responses}% Horny** 😳'
    embed.set_footer(text=f'How horny are you? - {ctx.author.name}')
    await ctx.reply(embed=embed)

  @commands.command(name="cute",
                    aliases=['cuteness'],
                    help="check someone cuteness percentage",
                    usage="Cute <person>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def cute(self, ctx, *, person):
    embed = discord.Embed(title="• About your cuteness", color=discord.Color.random())
    responses = random.randrange(1, 150)
    embed.description = f'**{person} is {responses}% Cute** 🥰'
    embed.set_footer(text=f'How cute are you? - {ctx.author.name}')
    await ctx.reply(embed=embed)

  @commands.command(name="intelligence",
                    aliases=['iq'],
                    help="check someone intelligence percentage",
                    usage="Intelligence <person>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def intelligence(self, ctx, *, person):
    embed = discord.Embed(title="• About your intelligence", color=discord.Color.random())
    responses = random.randrange(1, 150)
    embed.description = f'**{person} has an IQ of {responses}%** •'
    embed.set_footer(text=f'How intelligent are you? - {ctx.author.name}')
    await ctx.reply(embed=embed)

  @commands.command(name="gif", help="Search for a gif and display a random one.", with_app_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 5, commands.BucketType.user)
  async def gif(self, ctx, *, search_query: str):
      async with aiohttp.ClientSession() as session:
          async with session.get(f"https://api.giphy.com/v1/gifs/search?api_key={self.giphy_token}&q={search_query}&limit=10") as response:
              data = await response.json()
              if "data" in data:
                  gif = discord.Embed(title=f"Random GIF for '{search_query}'", color=discord.Color.random())
                  gif.set_image(url=random.choice(data["data"])["images"]["original"]["url"])
                  await ctx.reply(embed=gif)
              else:
                  await ctx.reply("No GIFs found for that search query.")
                



  @commands.command(name="iplookup",
                    aliases=['ip'],
                    help="Get accurate IP info",
                    usage="iplookup [ip]")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def iplookup(self, ctx, *, ip):
    async with aiohttp.ClientSession() as session:
      try:
        async with session.get(f"http://ip-api.com/json/{ip}") as response:
          data = await response.json()

          if data['status'] == 'fail':
            embed = discord.Embed(
              description="Failed to retrieve data. Please check the IP address and try again.",
              color=0xFF0000)
            await ctx.send(embed=embed)
            return

          
          query = data.get('query', 'N/A')
          continent = data.get('continent', 'N/A')
          continent_code = data.get('continentCode', 'N/A')
          country = data.get('country', 'N/A')
          country_code = data.get('countryCode', 'N/A')
          region_name = data.get('regionName', 'N/A')
          region = data.get('region', 'N/A')
          city = data.get('city', 'N/A')
          district = data.get('district', 'N/A')
          zip_code = data.get('zip', 'N/A')
          latitude = data.get('lat', 'N/A')
          longitude = data.get('lon', 'N/A')
          timezone = data.get('timezone', 'N/A')
          offset = data.get('offset', 'N/A')
          isp = data.get('isp', 'N/A')
          organization = data.get('org', 'N/A')
          asn = data.get('as', 'N/A')
          asname = data.get('asname', 'N/A')
          mobile = data.get('mobile', 'N/A')
          proxy = data.get('proxy', 'N/A')
          hosting = data.get('hosting', 'N/A')

          embed = discord.Embed(
            title=f"IP: {query}",
            description=(
              f"\n"
              f"🌏 __**Location Info:**__ \n"
              f"IP: **{query}**\n"
              f"Continent: {continent} ({continent_code})\n"
              f"Country: {country} ({country_code})\n"
              f"Region: **{region_name}** ({region})\n"
              f"City: {city}\n"
              f"District: {district}\n"
              f"Zip: {zip_code}\n"
              f"Latitude: {latitude}\n"
              f"Longitude: {longitude}\n"
              f"Lat/Long: {latitude}, {longitude}\n"
              f"\n"
              f"📡 __**Timezone Info:**__\n"
              f"Timezone: {timezone}\n"
              f"Offset: {offset}\n"
              f"\n"
              f"🛜 __**Network Info:**__ \n"
              f"ISP: **{isp}**\n"
              f"Organization: {organization}\n"
              f"AS: **{asn}**\n"
              f"AS Name: **{asname}**\n"
              f"\n"
              f"⚠️ __**Miscellaneous Info:**__ \n"
              f"Mobile: {mobile}\n"
              f"Proxy: {proxy}\n"
              f"Hosting: {hosting}\n"
              f""
            ),
            color=0x000000
          )

          embed.set_footer(
            text=f'Made by Tempest Federation™',
            icon_url=self.bot.user.avatar
          )

          await ctx.reply(embed=embed)

      except Exception as e:
        embed = discord.Embed(
          description=f"An error occurred: {str(e)}",
          color=0xFF0000
        )
        await ctx.send(embed=embed)

############################

  @commands.command()
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def weather(self, ctx, *, city: str):
      api_key = "b81e2218c328686836ab6d9d31ce97d0"
      base_url = "http://api.openweathermap.org/data/2.5/weather?"
      city_name = city
      complete_url = f"{base_url}q={city_name}&APPID={api_key}"
      
      async with aiohttp.ClientSession() as session:
          async with session.get(complete_url) as response:
              data = await response.json()
              if data["cod"] != "404":
                  main = data['main']
                  temperature = main['temp']
                  temp_celsius = temperature - 273.15
                  humidity = main['humidity']
                  pressure = main['pressure']
                  report = data['weather']
                  weather_desc = report[0]['description']
                  
                  weather_embed = discord.Embed(
                      title=f"☁️ Weather in {city_name}",
                      color=0x000000
                  )
                  weather_embed.add_field(name="Description", value=weather_desc.capitalize(), inline=False)
                  weather_embed.add_field(name="Temperature (Celsius)", value=f"{temp_celsius:.2f} °C", inline=False)
                  weather_embed.add_field(name="Humidity", value=f"{humidity}%", inline=False)
                  weather_embed.add_field(name="Pressure", value=f"{pressure} hPa", inline=False)
                  weather_embed.set_footer(
                    text=f"Requested By {ctx.author}",
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
                  )
                  
                  await ctx.reply(embed=weather_embed)
              else:
                  await ctx.reply("City not found. Please enter a valid city name.")

  @commands.command(name="fakeban", aliases=['fban'], usage = "fakeban <member>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def fake_ban(self, ctx, user: discord.Member):
    embed = discord.Embed(
      title="Successfully Banned!",
      description=f"✅ | {user.mention} has been successfully banned",
      color=0x000000
    )
    embed.set_footer(
        text=f"Banned By {ctx.author}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
      )
    await ctx.reply(embed=embed)


  @commands.command(name="hug")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def hug(self, ctx, user: discord.Member = None):
      if user is None:
          user = ctx.author
          description = f"{ctx.author.mention} hugged themselves 🥺"
      else:
          description = f"{ctx.author.mention} hugged {user.mention} 🥰"

      image_url = await self.fetch_image(ctx, "hug")
      if image_url:
          embed = discord.Embed(description=description, color=RandomColor())
          embed.set_image(url=image_url)
          await ctx.reply(embed=embed)

  @commands.command(name="kiss")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def kiss(self, ctx, user: discord.Member = None):
      if user is None:
          user = ctx.author
          description = f"{ctx.author.mention} kissed someone in their dream 💀"
      else:
          description = f"{ctx.author.mention} kissed {user.mention} 😳"

      image_url = await self.fetch_image(ctx, "kiss")
      if image_url:
          embed = discord.Embed(description=description, color=RandomColor())
          embed.set_image(url=image_url)
          await ctx.reply(embed=embed)

  @commands.command(name="pat")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def pat(self, ctx, user: discord.Member = None):
      if user is None:
          user = ctx.author
          description = f"{ctx.author.mention} pats themselves 🥺"
      else:
          description = f"{ctx.author.mention} pats {user.mention} 🫠"

      image_url = await self.fetch_image(ctx, "pat")
      if image_url:
          embed = discord.Embed(description=description, color=RandomColor())
          embed.set_image(url=image_url)
          await ctx.reply(embed=embed)

  @commands.command(name="cuddle")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def cuddle(self, ctx, user: discord.Member = None):
      if user is None:
          user = ctx.author
          description = f"{ctx.author.mention} cuddles themselves 🥺"
      else:
          description = f"{ctx.author.mention} cuddles {user.mention} 🥰"

      image_url = await self.fetch_image(ctx, "cuddle")
      if image_url:
          embed = discord.Embed(description=description, color=RandomColor())
          embed.set_image(url=image_url)
          await ctx.reply(embed=embed)

  @commands.command(name="slap")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def slap(self, ctx, user: discord.Member = None):
      if user is None:
          await ctx.reply(f"{ctx.author.mention}, you can't slap the air! Find someone to slap.")
          return

      description = f"{ctx.author.mention} slaps {user.mention} 😡"
      image_url = await self.fetch_image(ctx, "slap")
      if image_url:
          embed = discord.Embed(description=description, color=RandomColor())
          embed.set_image(url=image_url)
          await ctx.reply(embed=embed)

  @commands.command(name="tickle")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def tickle(self, ctx, user: discord.Member = None):
      if user is None:
          user = ctx.author
          description = f"{ctx.author.mention} tickles themselves 🤪"
      else:
          description = f"{ctx.author.mention} tickles {user.mention} 😆"

      image_url = await self.fetch_image(ctx, "tickle")
      if image_url:
          embed = discord.Embed(description=description, color=RandomColor())
          embed.set_image(url=image_url)
          await ctx.reply(embed=embed)

  @commands.command(name="spank")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def spank(self, ctx, user: discord.Member = None):
      if not ctx.channel.is_nsfw():
            await ctx.reply("This command can only be used in NSFW (age-restricted) channels.")
            return
      if user is None:
          user = ctx.author
          description = f"{ctx.author.mention} spanked themselves 😵‍💫"
      else:
          description = f"{ctx.author.mention} spanked {user.mention} 😹"

      image_url = await self.fetch_image(ctx, "spank")
      if image_url:
          embed = discord.Embed(description=description, color=RandomColor())
          embed.set_image(url=image_url)
          await ctx.send(embed=embed)

  @commands.command(name="kill")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def kill(self, ctx, user: discord.Member = None):
      if user is None:
          await ctx.send(f"{ctx.author.mention}, you can't kill the air! Find someone to kill.")
          return

      description = f"{ctx.author.mention} kills {user.mention} ☠️"
      image_url = await self.fetch_action_image("kill")
      if image_url:
          embed = discord.Embed(description=description, color=discord.Color.random())
          embed.set_image(url=image_url)
          await ctx.reply(embed=embed)
          
  @commands.command(name="ngif")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def ngif(self, ctx):
      

      image_url = await self.fetch_image(ctx, "ngif")
      if image_url:
          embed = discord.Embed(color=RandomColor())
          embed.set_image(url=image_url)
          await ctx.reply(embed=embed)


    
  @commands.command(name="8ball", aliases=["8b"])
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def eight_ball(self, ctx, *, question: str = None):
      if question is None:
          await ctx.send("You need to ask a question!")
          return

      async with aiohttp.ClientSession() as session:
          async with session.get("https://nekos.life/api/v2/8ball") as response:
              data = await response.json()
              if "response" in data:
                  embed = discord.Embed(
                      description=f"🎱 {data['response']}",
                      color=discord.Color.random()
                  )
                  if "url" in data:
                      embed.set_image(url=data["url"])
                  await ctx.reply(embed=embed)
              else:
                  await ctx.reply("Couldn't retrieve a response from the magic 8ball.")



  @commands.command(name="truth", aliases=["t"])
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.max_concurrency(5, per=commands.BucketType.default, wait=False)
  async def truth(self, ctx):
      async with aiohttp.ClientSession() as session:
          async with session.get("https://api.truthordarebot.xyz/api/truth") as response:
              if response.status == 200:
                  data = await response.json()
                  question = data.get("question")
                  if question:
                      embed= discord.Embed(title="__**TRUTH**__",description=f"{question}", color=0x000000)
                      await ctx.reply(embed=embed)
                  else:
                      await ctx.send("Couldn't retrieve a truth question. Please try again.")
              else:
                  await ctx.send("Error fetching truth question. Please try again.")

  @commands.command(name="dare", aliases=["d"])
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  @commands.max_concurrency(5, per=commands.BucketType.default, wait=False)
  async def dare(self, ctx):
      async with aiohttp.ClientSession() as session:
          async with session.get("https://api.truthordarebot.xyz/api/dare") as response:
              if response.status == 200:
                  data = await response.json()
                  question = data.get("question")
                  if question:
                      embed= discord.Embed(title="__**DARE**__",description=f"{question}", color=0x000000)
                      await ctx.reply(embed=embed)
                  else:
                      await ctx.send("Couldn't retrieve a dare question. Please try again.")
              else:
                  await ctx.send("Error fetching dare question. Please try again.")




  @commands.command(name="translate", aliases=["tl"])
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 5, commands.BucketType.user)
  async def translate_command(self, ctx, *, message=None):
    
    if message is None:
      if ctx.message.reference:
        replied_msg = await ctx.fetch_message(ctx.message.reference.message_id)

        if replied_msg:
          message = replied_msg.content
        else:
          await ctx.reply("Error: No message found to translate.")
          return
      else:
        await ctx.reply("Error: Please provide a message to translate or reply to a message.")
        return

    processing_message = await ctx.send("Translating...")

    base_url = "https://translate.googleapis.com/translate_a/single"
    params = {
      "client": "gtx",
      "sl": "hi",      # Source language: Hindi
      "tl": "en",      # Target language: English
      "dt": "t",       # Data type: text
      "q": message     # Text to translate
    }

    try:
      response = requests.get(base_url, params=params)
      if response.status_code == 200:
        translation = response.json()[0][0][0]
        embed = discord.Embed(title="• **Translation Result:**", color=0x000000)
        embed.add_field(name="__Original:__", value=message, inline=False)
        embed.add_field(name="__Translated:__", value=translation, inline=False)
        embed.set_footer(text=f"Requested By {ctx.author}",
                       icon_url=ctx.author.avatar.url
                       if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.reply(embed=embed)
        await processing_message.delete()
      else:
        await ctx.send("Error: Translation failed. Please check your input and try again.")
    except Exception as e:
      await ctx.reply(f"An error occurred: {str(e)}")
      await processing_message.delete()

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
import os
from core import Cog, Tempest, Context
import games as games
from utils.Tools import *
from games import button_games as btn
import random
import asyncio



class Games(Cog):
    """Olympus Games"""

    def __init__(self, client: Tempest):
        self.client = client


    @commands.hybrid_command(name="chess",
                             help="Play Chess with a user.",
                             usage="Chess <user>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(5, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _chess(self, ctx: Context, player: discord.Member):
        if player == ctx.author:
            await ctx.send("You Cannot play game with yourself!",
                           mention_author=False)
        elif player.bot:
            await ctx.send("You cannot play with bots!")
        else:
            game = btn.BetaChess(white=ctx.author, black=player)
            await game.start(ctx)


    @commands.hybrid_command(name="rps",
                             help="Play Rock Paper Scissor with bot/user.",
                             aliases=["rockpaperscissors"],
                             usage="Rockpaperscissors")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(5, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _rps(self, ctx: Context, player: discord.Member = None):
        game = btn.BetaRockPaperScissors(player)
        await game.start(ctx, timeout=120)

    @commands.hybrid_command(name="tic-tac-toe",
                             help="play tic-tac-toe game with a user.",
                             aliases=["ttt", "tictactoe"],
                             usage="Ticktactoe <member>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(5, per=commands.BucketType.user, wait=False)
    @commands.guild_only()
    async def _ttt(self, ctx: Context, player: discord.Member):
        if player == ctx.author:
            await ctx.send("You Cannot play game with yourself!",
                           mention_author=False)
        elif player.bot:
            await ctx.send("You cannot play with bots!")
        else:
            game = btn.BetaTictactoe(cross=ctx.author, circle=player)
            await game.start(ctx, timeout=30)

    @commands.hybrid_command(name="wordle",
                             help="Wordle Game | Play with bot.",
                             usage="Wordle")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(3, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _wordle(self, ctx: Context):
        game = games.Wordle()
        await game.start(ctx, timeout=120)

    @commands.hybrid_command(name="2048",
                             help="Play 2048 game with bot.",
                             aliases=["twenty48"],
                             usage="2048")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(3, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _2048(self, ctx: Context):
        game = btn.BetaTwenty48()
        await game.start(ctx, win_at=2048)

    @commands.hybrid_command(name="memory-game",
                             help="How strong is your memory?",
                             aliases=["memory"],
                             usage="memory-game")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(3, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _memory(self, ctx: Context):
        game = btn.MemoryGame()
        await game.start(ctx)

    @commands.hybrid_command(name="number-slider",
                             help="slide numbers with bot",
                             aliases=["slider"],
                             usage="slider")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(3, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _number_slider(self, ctx: Context):
        game = btn.NumberSlider()
        await game.start(ctx)

    @commands.hybrid_command(name="battleship",
                             help="Play battleship game with your friend.",
                             aliases=["battle-ship"],
                             usage="battleship <user>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(3, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _battle(self, ctx: Context, player: discord.Member):
        game = btn.BetaBattleShip(player1=ctx.author, player2=player)
        await game.start(ctx)

    @commands.group(name="country-guesser",
                    help="Guess name of the country by flag.",
                    aliases=["guess", "guesser", "countryguesser"],
                    usage="country-guesser")
    @commands.guild_only()
    async def _country_guesser(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help("country-guesser")

    @_country_guesser.command(name="start",
                              help="Starts the country guesser game. It's a 100 Seconds Game so suggested to play in a SPECIFIC CHANNEL.")
    async def _start_country_guesser(self, ctx: Context):
        game = games.CountryGuesser(is_flags=True, hints=2)
        await game.start(ctx)

    """@_country_guesser.command(name="end",
                              help="Ends the country guesser game.")
    async def _end_country_guesser(self, ctx: Context):
        await self.country_guesser_game.end_game_manually(ctx)"""

    @commands.hybrid_command(name="connectfour",
                             help="Play Connect Four game with user.",
                             aliases=["c4", "connect-four", "connect4"],
                             usage="connectfour <user>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    @commands.guild_only()
    async def _connectfour(self, ctx: Context, player: discord.Member):
        if player == ctx.author:
            await ctx.send("You cannot play against yourself!")
        elif player.bot:
            await ctx.send("You cannot play with bots!")
        else:
            game = games.ConnectFour(red=ctx.author, blue=player)  
            await game.start(ctx, timeout=300)



    @commands.hybrid_command(name="lights-out",
                             help="Play Lights Show game with bot.",
                             aliases=["lightsout"],
                             usage="Lights-out")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(3, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _lights_show(self, ctx: Context):
        game = btn.LightsOut()
        await game.start(ctx)

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import asyncio
import discord
from discord.ext import commands, tasks
from discord.utils import get
import datetime
import random
import requests
import aiohttp
import re
from discord.ext.commands.errors import BadArgument
from discord.ext.commands import Cog
from discord.colour import Color
import hashlib
from utils.Tools import *
from traceback import format_exception
import discord
from discord.ext import commands
import datetime
from discord import ButtonStyle
from discord.ui import Button, View
import psutil
import time
from datetime import datetime, timezone, timedelta
import sqlite3
from typing import *
import string
#from cogs.commands.moderation import do_removal

lawda = [
  '8', '3821', '23', '21', '313', '43', '29', '76', '11', '9',
  '44', '470', '318' , '26', '69'
]



class AvatarView(View):
  def __init__(self, user, member, author_id, banner_url):
    super().__init__()
    self.user = user
    self.member = member
    self.author_id = author_id
    self.banner_url = banner_url

    if self.user.avatar.is_animated():
      self.add_item(Button(label='GIF', url=self.user.avatar.with_format('gif').url, style=discord.ButtonStyle.link))
    self.add_item(Button(label='PNG', url=self.user.avatar.with_format('png').url, style=discord.ButtonStyle.link))
    self.add_item(Button(label='JPEG', url=self.user.avatar.with_format('jpg').url, style=discord.ButtonStyle.link))
    self.add_item(Button(label='WEBP', url=self.user.avatar.with_format('webp').url, style=discord.ButtonStyle.link))

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user.id != self.author_id:
      await interaction.response.send_message(
        "Uh oh! That message doesn't belong to you. You must run this command to interact with it.",
        ephemeral=True
      )
      return False
    return True

  @discord.ui.button(label='Server Avatar', style=discord.ButtonStyle.success, custom_id='server_avatar_button')
  async def server_avatar(self, interaction: discord.Interaction, button: Button):
    if not self.member.guild_avatar:
      await interaction.response.send_message(
        "This user doesn't have a different guild avatar.",
        ephemeral=True
      )
    else:
      embed = interaction.message.embeds[0]
      embed.set_image(url=self.member.guild_avatar.url)
      await interaction.response.edit_message(embed=embed)

  @discord.ui.button(label='User Banner', style=discord.ButtonStyle.success, custom_id='banner_button')
  async def banner(self, interaction: discord.Interaction, button: Button):
    if not self.banner_url:
      await interaction.response.send_message(
        "This user doesn't have a banner.",
        ephemeral=True
      )
    else:
      embed = interaction.message.embeds[0]
      embed.set_image(url=self.banner_url)
      await interaction.response.edit_message(embed=embed)





class General(commands.Cog):

  def __init__(self, bot, *args, **kwargs):
    self.bot = bot

    self.aiohttp = aiohttp.ClientSession()
    self._URL_REGEX = r'(?P<url><[^: >]+:\/[^ >]+>|(?:https?|steam):\/\/[^\s<]+[^<.,:;\"\'\]\s])'
    self.color = 0x000000


  @commands.hybrid_command(
    usage="Avatar <member>",
    name='avatar',
    aliases=['av'],
    help="Get User avater/Guild avatar & Banner of a user."
  )
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def _user(self, ctx, member: Optional[Union[discord.Member, discord.User]] = None):
    try:
      if member is None:
        member = ctx.author
      user = await self.bot.fetch_user(member.id)

      banner_url = user.banner.url if user.banner else None

      description = f"[`PNG`]({user.avatar.with_format('png').url}) | [`JPG`]({user.avatar.with_format('jpg').url}) | [`WEBP`]({user.avatar.with_format('webp').url})"
      if user.avatar.is_animated():
        description += f" | [`GIF`]({user.avatar.with_format('gif').url})"
      if banner_url:
        description += f" | [`Banner`]({banner_url})"

      embed = discord.Embed(
        color=self.color,
        description=description
      )
      embed.set_author(name=f"{member}", icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
      embed.set_image(url=user.avatar.url)
      embed.set_footer(text=f"Requested By {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)

      view = AvatarView(user, member, ctx.author.id, banner_url)
      await ctx.send(embed=embed, view=view)
    except Exception as e:
      print(f"Error: {e}")
      
  @commands.hybrid_command(
    name="servericon",
    help="Get the server icon",
    usage="Servericon"
  )
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def servericon(self, ctx: commands.Context):
    server = ctx.guild
    if server.icon is None:
      await ctx.reply("This server does not have an icon.")
      return

    webp = server.icon.replace(format='webp')
    jpg = server.icon.replace(format='jpg')
    png = server.icon.replace(format='png')

    description = f"[`PNG`]({png}) | [`JPG`]({jpg}) | [`WEBP`]({webp})"
    if server.icon.is_animated():
      gif = server.icon.replace(format='gif')
      description += f" | [`GIF`]({gif})"

    avemb = discord.Embed(
      color=self.color,
      title=f"{server}'s Icon",
      description=description
    )
    avemb.set_image(url=server.icon.url)
    avemb.set_footer(
      text=f"Requested By {ctx.author}",
      icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    )

    view = discord.ui.View()
    view.add_item(Button(label="Download Icon", url=server.icon.url, style=ButtonStyle.link))

    await ctx.send(embed=avemb, view=view)



  @commands.hybrid_command(name="membercount",
                           help="Get total member count of the server",
                           usage="membercount",
                           aliases=["mc"])
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 2, commands.BucketType.user)
  async def membercount(self, ctx: commands.Context):
        total_members = len(ctx.guild.members)
        total_humans = len([member for member in ctx.guild.members if not member.bot])
        total_bots = len([member for member in ctx.guild.members if member.bot])

        online = len([member for member in ctx.guild.members if member.status == discord.Status.online])
        offline = len([member for member in ctx.guild.members if member.status == discord.Status.offline])
        idle = len([member for member in ctx.guild.members if member.status == discord.Status.idle])
        dnd = len([member for member in ctx.guild.members if member.status == discord.Status.do_not_disturb])



        embed = discord.Embed(title="Member Statistics",
                              color=0x000000)
        embed.add_field(name="__Count Stats:__",
                        value=f"• Total Members: {total_members}\n• Total Humans: {total_humans}\n• Total Bots: {total_bots}",
                        inline=False)

        embed.add_field(name="__Presence Stats:__", value=f"✅ Online: {online}\n• Dnd: {dnd}\n• Idle: {idle}\n❌ Offline: {offline}", inline=False)

        await ctx.send(embed=embed)

  @commands.hybrid_command(name="poll", usage="Poll <message>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def poll(self, ctx: commands.Context, *, message):
    author = ctx.author
    emp = discord.Embed(title=f"**Poll raised by {author}!**",
                        description=f"{message}",
                        color=self.color)
    msg = await ctx.send(embed=emp)
    await msg.add_reaction("•")
    await msg.add_reaction("•")

  
  @commands.command(name="hack",
    help="hack someone's discord account",
    usage="Hack <member>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def hack(self, ctx: commands.Context, member: discord.Member):
    stringi = member.name
    min_length = 2
    max_length = 12
    length = random.randint(min_length, max_length)
    stringg = member.name
    remaining_length = length - len(stringg)
    all_chars = string.ascii_letters + string.digits + string.punctuation
    random_chars = random.choices(all_chars, k=remaining_length)

    password = stringg + ''.join(random_chars)
    
    lund = await ctx.send(f"Processing to Hack {member.mention}...")
    await asyncio.sleep(2)
    random_pass = random.choice(lawda)
    
    random_pass2 = ''.join(random.choices(string.ascii_letters + string.digits, k=3))
    embed = discord.Embed(
  title=f"**Hacked {member.display_name}!**",
  description=(
  f"User - {member.mention}\n"
  f"E-Mail - {''.join(letter for letter in stringi if letter.isalnum())}{random_pass}@gmail.com\n"
  f"Account Password - {member.name}@{random_pass2}"
  ),
  color=0x000000
  )
    embed.set_footer(
  text=f"Hacked By {ctx.author}",
  icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
  )
    await ctx.send(embed=embed)
    await lund.delete()


  @commands.command(name="token", usage="Token <member>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 2, commands.BucketType.user)
  async def token(self, ctx: commands.Context, user: discord.Member = None):
    list = [
      "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N",
      "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "_"
      'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n',
      'ñ', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0',
      '1', '2', '3', '4', '5', '6', '7', '8', '9'
    ]
    token = random.choices(list, k=59)
    if user is None:
      user = ctx.author
      await ctx.send(user.mention + "'s token: " + ''.join(token))
    else:
      await ctx.send(user.mention + "'s token: " + "".join(token))

  @commands.command(name="users", help="checks total users of Olympus.")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def users(self, ctx: commands.Context):
    users = sum(g.member_count for g in self.bot.guilds
                if g.member_count != None)
    guilds = len(self.bot.guilds)
    embed = discord.Embed(
      title=f"**• Olympus Users**",
      description=f"❯ Total of __**{users}**__ Users in **{guilds}** Guilds",
      color=self.color)
    await ctx.send(embed=embed)


  @commands.command(name="wizz", usage="Wizz")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def wizz(self, ctx: commands.Context):
    message6 = await ctx.send(
      f"`Wizzing {ctx.guild.name}, will take 22 seconds to complete`")
    message7 = await ctx.send(f"Changing all guild settings...")
    message5 = await ctx.send(f"Deleting **{len(ctx.guild.roles)}** Roles...")
    await asyncio.sleep(1)
    message4 = await ctx.send(
      f"Deleting **{len(ctx.guild.channels)}** Channels...")
    await asyncio.sleep(1)
    message3 = await ctx.send(f"Deleting Webhooks...")
    message2 = await ctx.send(f"Deleting emojis")
    await asyncio.sleep(1)
    message1 = await ctx.send(f"Installing Ban Wave..")
    await asyncio.sleep(1)
    await message6.delete()
    await message7.delete()
    await message5.delete()
    await message4.delete()
    await message3.delete()
    await message2.delete()
    await message1.delete()
    embed = discord.Embed(
      title=f"{self.bot.user.name}",
      description=f"**⚠️ Successfully Wizzed {ctx.guild.name}**",
      color=self.color,
      timestamp=ctx.message.created_at)
    embed.set_footer(
      text=f"Wizzed By {ctx.author}",
      icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
      )
    await ctx.send(embed=embed)


  @commands.hybrid_command(
    name="urban",
    description="Searches for specified phrase on urbandictionary",
    help="Get meaning of specified phrase",
    usage="Urban <phrase>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def urban(self, ctx: commands.Context, *, phrase):
    async with self.aiohttp.get(
        "http://api.urbandictionary.com/v0/define?term={}".format(
          phrase)) as urb:
      urban = await urb.json()
      try:
        embed = discord.Embed(title=f"Meaning of \"{phrase}\"", color=self.color)
        embed.add_field(name="__Definition:__",
                        value=urban['list'][0]['definition'].replace(
                          '[', '').replace(']', ''))
        embed.add_field(name="__Example:__",
                        value=urban['list'][0]['example'].replace('[',
                                                                  '').replace(
                                                                    ']', ''))

        embed.add_field(name="__Author:__",
                        value=urban['list'][0]['author'].replace('[',
                                                                  '').replace(
                                                                    ']', ''))

        embed.add_field(name="__Written On:__",
                        value=urban['list'][0]['written_on'].replace('[',
                                                                  '').replace(
                                                                    ']', ''))
        embed.set_footer(
      text=f"Requested By {ctx.author}",
      icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
      )
        temp = await ctx.reply(embed=embed, mention_author=True)
        await asyncio.sleep(45)
        await temp.delete()
        await ctx.message.delete()
      except:
        pass

  @commands.command(name="rickroll",
                           help="Detects if provided url is a rick-roll",
                           usage="Rickroll <url>")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def rickroll(self, ctx: commands.Context, *, url: str):
    if not re.match(self._URL_REGEX, url):
      raise BadArgument("Invalid URL")

    phrases = [
      "rickroll", "rick roll", "rick astley", "never gonna give you up"
    ]
    source = str(await (await self.aiohttp.get(
      url, allow_redirects=True)).content.read()).lower()
    rickRoll = bool((re.findall('|'.join(phrases), source,
                                re.MULTILINE | re.IGNORECASE)))
    await ctx.reply(embed=discord.Embed(
      title="Rick Roll {} in webpage".format(
        "was found" if rickRoll is True else "was not found"),
      color=Color.red() if rickRoll is True else Color.green(),
    ),
                    mention_author=True)

  @commands.command(name="hash",
                           help="Hashes provided text with provided algorithm")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def hash(self, ctx: commands.Context, algorithm: str, *, message):
    algos: dict[str, str] = {
      "md5": hashlib.md5(bytes(message.encode("utf-8"))).hexdigest(),
      "sha1": hashlib.sha1(bytes(message.encode("utf-8"))).hexdigest(),
      "sha224": hashlib.sha224(bytes(message.encode("utf-8"))).hexdigest(),
      "sha3_224": hashlib.sha3_224(bytes(message.encode("utf-8"))).hexdigest(),
      "sha256": hashlib.sha256(bytes(message.encode("utf-8"))).hexdigest(),
      "sha3_256": hashlib.sha3_256(bytes(message.encode("utf-8"))).hexdigest(),
      "sha384": hashlib.sha384(bytes(message.encode("utf-8"))).hexdigest(),
      "sha3_384": hashlib.sha3_384(bytes(message.encode("utf-8"))).hexdigest(),
      "sha512": hashlib.sha512(bytes(message.encode("utf-8"))).hexdigest(),
      "sha3_512": hashlib.sha3_512(bytes(message.encode("utf-8"))).hexdigest(),
      "blake2b": hashlib.blake2b(bytes(message.encode("utf-8"))).hexdigest(),
      "blake2s": hashlib.blake2s(bytes(message.encode("utf-8"))).hexdigest()
    }
    embed = discord.Embed(color=0x000000,
                          title="Hashed \"{}\"".format(message))
    if algorithm.lower() not in list(algos.keys()):
      for algo in list(algos.keys()):
        hashValue = algos[algo]
        embed.add_field(name=algo, value="```{}```".format(hashValue))
    else:
      embed.add_field(name=algorithm,
                      value="```{}```".format(algos[algorithm.lower()]),
                      inline=False)
    await ctx.reply(embed=embed, mention_author=True)

  
  @commands.command(name="invite",
                           aliases=['invite-bot'],
                           description="Get Support & Bot invite link!")
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 3, commands.BucketType.user)
  async def invite(self, ctx: commands.Context):
    embed = discord.Embed(title="Olympus Invite & Support!",
      description=
      f"> • **[Olympus - Invite Bot](https://discord.com/oauth2/authorize?client_id=1144179659735572640&permissions=2113268958&scope=bot)**\n> • **[Olympus - Support](https://discord.gg/odx)**",
      color=0x000000)

    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1267667804048588992.png")
    embed.set_footer(text=f"Requested by {ctx.author.name}",
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    invite = Button(
      label='Invite',
      style=discord.ButtonStyle.link,
      url=
      'https://discord.com/oauth2/authorize?client_id=1144179659735572640&permissions=2113268958&scope=bot'
    )
    support = Button(label='Support',
                    style=discord.ButtonStyle.link,
                    url=f'https://discord.gg/odx')
    vote = Button(label='Vote',
                      style=discord.ButtonStyle.link,
                      url='https://top.gg/bot/1144179659735572640/vote')
    view = View()
    view.add_item(invite)
    view.add_item(support)
    view.add_item(vote)
    await ctx.send(embed=embed, view=view)

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
from discord.ext import commands, tasks
import datetime, pytz, time as t
from discord.ui import Button, Select, View
import aiosqlite, random, typing
import sqlite3
import asyncio
import discord, logging
from discord.utils import get
from utils.Tools import *
import os
import aiohttp

db_folder = 'db'
db_file = 'giveaways.db'
db_path = os.path.join(db_folder, db_file)
connection = sqlite3.connect(db_path)

cursor = connection.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS Giveaway (
                    guild_id INTEGER,
                    host_id INTEGER,
                    start_time TIMESTAMP,
                    ends_at TIMESTAMP,
                    prize TEXT,
                    winners INTEGER,
                    message_id INTEGER,
                    channel_id INTEGER,
                    PRIMARY KEY (guild_id, message_id)
                )''')

connection.commit()
connection.close()

def convert(time):
    pos = ["s","m","h","d"]
    time_dict = {"s" : 1, "m" : 60, "h" : 3600 , "d" : 86400 , "f" : 259200}
    unit = time[-1]
    if unit not in pos:
        return
    try:
        val = int(time[:-1])
    except ValueError:
        return
    return val * time_dict[unit]

def WinnerConverter(winner):
    try:
        int(winner)
    except ValueError:
        try:
           return int(winner[:-1])
        except:
            return -4
    return winner

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.connection = await aiosqlite.connect(db_path)
        self.cursor = await self.connection.cursor()
        await self.check_for_ended_giveaways() 
        self.GiveawayEnd.start()

    async def cog_unload(self) -> None:
        await self.connection.close()

    async def check_for_ended_giveaways(self):
        await self.cursor.execute("SELECT ends_at, guild_id, message_id, host_id, winners, prize, channel_id FROM Giveaway WHERE ends_at <= ?", (datetime.datetime.now().timestamp(),))
        ended_giveaways = await self.cursor.fetchall()
        for giveaway in ended_giveaways:
            await self.end_giveaway(giveaway)

    async def end_giveaway(self, giveaway):
        try:
            current_time = datetime.datetime.now().timestamp()
            guild = self.bot.get_guild(int(giveaway[1]))
            if guild is None:
                await self.cursor.execute("DELETE FROM Giveaway WHERE message_id = ? AND guild_id = ?", (giveaway[2], giveaway[1]))
                await self.connection.commit()
                return

            channel = self.bot.get_channel(int(giveaway[6]))
            if channel is not None:
                try:
                    retries = 3
                    for attempt in range(retries):
                        try:
                            message = await channel.fetch_message(int(giveaway[2]))
                            break
                        except discord.NotFound:
                            await self.cursor.execute("DELETE FROM Giveaway WHERE message_id = ? AND guild_id = ?", (giveaway[2], giveaway[1]))
                            await self.connection.commit()
                            return
                        except aiohttp.ClientResponseError as e:
                            if e.status == 503:
                                if attempt < retries - 1:
                                    await asyncio.sleep(2 ** attempt)
                                    continue
                                else:
                                    raise
                            else:
                                raise

                    users = [i.id async for i in message.reactions[0].users()]
                    if self.bot.user.id in users:
                        users.remove(self.bot.user.id)

                    if len(users) < 1:
                        await message.reply(f"No one won the **{giveaway[5]}** giveaway, due to Not enough participants.")
                        await self.cursor.execute("DELETE FROM Giveaway WHERE message_id = ? AND guild_id = ?", (message.id, message.guild.id))
                        await self.connection.commit()
                        return

                    winners_count = min(len(users), int(giveaway[4]))
                    winner = ', '.join(f'<@!{i}>' for i in random.sample(users, k=winners_count))

                    embed = discord.Embed(title=f"{giveaway[5]}",
                        description=f"Ended at <t:{int(current_time)}:R>\nHosted by <@{int(giveaway[3])}>\nWinner(s): {winner}",
                        color=0x000000)
                    embed.timestamp = discord.utils.utcnow()

                    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1267699529130709075.png")
                    embed.set_footer(text=f"Ended at")
                    await message.edit(content="🎁 **GIVEAWAY ENDED** 🎁", embed=embed)
                    await message.reply(f"💐 Congrats {winner}, you won **{giveaway[5]}!**, Hosted by <@{int(giveaway[3])}>")
                    await self.cursor.execute("DELETE FROM Giveaway WHERE message_id = ? AND guild_id = ?", (message.id, message.guild.id))
                    await self.connection.commit()

                except (discord.HTTPException, aiohttp.ClientResponseError) as e:
                    logging.error(f"Error ending giveaway: {e}")

        except IndexError:
            logging.error(f"Giveaway data is corrupted or missing: {giveaway}")
            await self.cursor.execute("DELETE FROM Giveaway WHERE message_id = ? AND guild_id = ?", (giveaway[2], giveaway[1]))
            await self.connection.commit()

    @tasks.loop(seconds=5)
    async def GiveawayEnd(self):
        await self.cursor.execute("SELECT ends_at, guild_id, message_id, host_id, winners, prize, channel_id FROM Giveaway WHERE ends_at <= ?", (datetime.datetime.now().timestamp(),))
        ends_raw = await self.cursor.fetchall()
        for giveaway in ends_raw:
            await self.end_giveaway(giveaway)




    @commands.hybrid_command(description="Starts a new giveaway.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_guild_permissions(manage_guild=True)
    async def gstart(self, ctx,
                      time,
                      winners: int,
                      *,
                      prize: str):

        await self.cursor.execute("SELECT message_id, channel_id FROM Giveaway WHERE guild_id = ?", (ctx.guild.id,))
        re = await self.cursor.fetchall()

        if winners >=  15:
            embed = discord.Embed(title="⚠️ Access Denied",
                                  description=f"Cannot exceed more than 15 winners.",
                                  color=0x000000)
            message = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await message.delete()
            return

        g_list = [i[0] for i in re]
        if len(g_list) >= 5:
            embed = discord.Embed(title="⚠️ Access Denied",
                                  description=f"You can only host upto 5 giveaways in this Guild.", color=0x000000)
            message = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await message.delete()
            return

        converted = self.convert(time)
        if converted / 60 >= 50400:
            embed = discord.Embed(title="⚠️ Access Denied",
                                  description=f"Time cannot exceed 31 days!", color=0x000000)
            message = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await message.delete()
            return

        if converted == -1:
            embed = discord.Embed(title="❌ Error",
                                  description=f"Invalid time format", color=0x000000)
            message = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await message.delete()
            return
        if converted == -2:
            embed = discord.Embed(title="❌ Error",
                                  description=f"Invalid time format. Please provide the time in numbers.",
                                  color=0x000000)
            message = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await message.delete()
            return

        ends = (datetime.datetime.now().timestamp() + converted)

        embed = discord.Embed(title=f"🎁 {prize}",
                              description=f"Winner(s): **{winners}**\nReact with 🎉 to participate!\nEnds <t:{round(ends)}:R> (<t:{round(ends)}:f>)\n\nHosted by {ctx.author.mention}", color=0x000000)

        ends1 = datetime.datetime.utcnow() + datetime.timedelta(seconds=converted)
        ends_utc = ends1.replace(tzinfo=datetime.timezone.utc)

        embed.timestamp = embed.timestamp = ends_utc
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1267699441394126940.png")
        embed.set_footer(text=f"Ends at", icon_url=ctx.bot.user.avatar.url)

        message = await ctx.send("🎁 **GIVEAWAY** 🎁", embed=embed)
        try:
           await ctx.message.delete()
        except:
            pass

        await self.cursor.execute("INSERT INTO Giveaway(guild_id, host_id, start_time, ends_at, prize, winners, message_id, channel_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", (ctx.guild.id, ctx.author.id, datetime.datetime.now(), ends, prize, winners, message.id, ctx.channel.id))

        await message.add_reaction("🎉")
        await self.connection.commit()

    
                                    

    @commands.Cog.listener("on_message_delete")
    async def GiveawayMessageDelete(self, message):
        await self.cursor.execute("SELECT message_id FROM Giveaway WHERE guild_id = ?", (message.guild.id,))
        re = await self.cursor.fetchone()

        if message.author != self.bot.user:
            return

        if re is not None:
            if message.id == int(re[0]):
                await self.cursor.execute("DELETE FROM Giveaway WHERE channel_id = ? AND message_id = ? AND guild_id = ?", (message.channel.id, message.id, message.guild.id))

                print(f"Giveaway message deleted in {message.guild.name} - {message.guild.id}")
                await self.connection.commit()

    @commands.hybrid_command(name="gend", description="Ends a giveaway before its ending time.", help="Ends a giveaway before its ending time.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_guild_permissions(manage_guild=True)
    async def gend(self, ctx, message_id = None):
        if message_id:
            try:
                int(message_id)
            except ValueError:
                embed = discord.Embed(title="⚠️ Access Denied",
                                      description="Invalid message ID provided.", color=0x000000)
                message = await ctx.send(embed=embed)
                await asyncio.sleep(5)
                await message.delete()
                return

        if message_id is not None:
            current_time = datetime.datetime.now().timestamp()
            await self.cursor.execute('SELECT ends_at, guild_id, message_id, host_id, winners, prize, channel_id FROM Giveaway WHERE message_id = ?', (int(message_id),))
            re = await self.cursor.fetchone()

            if re is None:
                embed = discord.Embed(title="❌ Error",
                                      description=f" The giveaway was not found.", color=0x000000)
                message = await ctx.send(embed=embed)
                await asyncio.sleep(5)
                await message.delete()
                return

            ch = self.bot.get_channel(int(re[6]))
            message = await ch.fetch_message(int(message_id))

            users = [i.id async for i in message.reactions[0].users()]
            users.remove(self.bot.user.id)

            if len(users) < 1:
                await ctx.send(f"✅ Successfully Ended the giveaway in <#{int(re[6])}>")
                await message.reply(f"No one won the **{re[5]}** giveaway, due to Not enough participants.")
                await self.cursor.execute("DELETE FROM Giveaway WHERE message_id = ? AND guild_id = ?", (message.id, message.guild.id))
                return

            winner = ', '.join(f'<@!{i}>' for i in random.sample(users, k=int(re[4])))

            embed = discord.Embed(title=f"🎁 {re[5]}",
                        description=f"Ended at <t:{int(current_time)}:R>\nHosted by <@{int(re[3])}>\nWinner(s): {winner}",
                        color=0x000000
                    )
            embed.timestamp = discord.utils.utcnow()

            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1267699529130709075.png")
            embed.set_footer(text=f"Ended")

            await message.edit(content="🎁 **GIVEAWAY ENDED** 🎁", embed=embed)

            if int(ctx.channel.id) != int(re[6]):
                await ctx.send(f"✅ Successfully ended the giveaway in <#{int(re[6])}>")

            await message.reply(f"💐 Congrats {winner}, you won **{re[5]}!**, Hosted by <@{int(re[3])}>")
            await self.cursor.execute("DELETE FROM Giveaway WHERE message_id = ? AND guild_id = ?", (message.id, message.guild.id))
            #print(f"[Gend] Giveaway Ended - {message.guild.name} ({message.guild.id}) - ({re[5]})")

        elif ctx.message.reference:
            await self.cursor.execute('SELECT ends_at, guild_id, message_id, host_id, winners, prize, channel_id FROM Giveaway WHERE message_id = ?', (ctx.message.reference.resolved.id,))
            re = await self.cursor.fetchone()

            if re is None:
                return await ctx.send(f"The giveaway was not found.")

            current_time = datetime.datetime.now().timestamp()

            message = await ctx.fetch_message(ctx.message.reference.message_id)

            users = [i.id async for i in message.reactions[0].users()]
            try: users.remove(self.bot.user.id)
            except: pass

            if len(users) < 1:
                await message.reply(f"No one won the **{re[5]}** giveaway, due to not enough participants.")
                await self.cursor.execute("DELETE FROM Giveaway WHERE message_id = ? AND guild_id = ?", (message.id, message.guild.id))
                return

            winner = ', '.join(f'<@!{i}>' for i in random.sample(users, k=int(re[4])))

            embed = discord.Embed(title=f"🎁 {re[5]}",
                        description=f"Ended <t:{int(current_time)}:R>\nHosted by <@{int(re[3])}>\nWinner(s): {winner}",
                        color=0x000000
                    )
            embed.timestamp = discord.utils.utcnow()

            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1267699529130709075.png")
            embed.set_footer(text=f"Ended at")

            await message.edit(content="🎁 **GIVEAWAY ENDED** 🎁", embed=embed)

            await message.reply(f"💐 Congrats {winner}, you won **{re[5]}!**, Hosted by <@{int(re[3])}>")
            await self.cursor.execute("DELETE FROM Giveaway WHERE message_id = ? AND guild_id = ?", (message.id, message.guild.id))
            #print(f"[Gend] Giveaway Ended - {message.guild.name} ({message.guild.id}) - ({re[5]})")

        else:
            await ctx.send("Please reply to the giveaway message or provide the giveaway ID.")
        await self.connection.commit()

    @commands.hybrid_command(description="Rerolls a giveaway on replying the giveaway message.", help="Rerolls a giveaway on replying the giveaway message.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_guild_permissions(manage_guild=True)
    async def greroll(self, ctx, message_id: typing.Optional[int] = None):
        if not ctx.message.reference:
            message = await ctx.reply("Reply this command with the Giveaway Ended message to reroll.")
            await asyncio.sleep(5)
            await message.delete()
            return

        if ctx.message.reference:
            message_id = ctx.message.reference.resolved.id

        message = await ctx.fetch_message(message_id)

        if ctx.message.reference.resolved.author.id != self.bot.user.id :
            embed = discord.Embed(title="⚠️ Access Denied",
                                  description=f"The giveaway was not found.", color=0x000000)
            message = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await message.delete()
            return


        await self.cursor.execute(f"SELECT message_id FROM Giveaway WHERE message_id = ?", (message.id,))
        re = await self.cursor.fetchone()

        if re is not None:
            embed = discord.Embed(title="⚠️ Access Denied",
                                  description=f"The giveaway is currently running. Please use the `gend` command instead to end the giveaway.", color=0x000000)
            message = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await message.delete()
            return

        users = [i.id async for i in message.reactions[0].users()]
        users.remove(self.bot.user.id)

        if len(users) < 1:
            await message.reply(f"No one won the **{re[5]}** giveaway, due to not enough participants.")
            return

        winners = random.sample(users, k=1)
        await message.reply(f"💐 The new winner is "+", ".join(f"<@{i}>" for i in winners)+". Congratulations!")
        await self.connection.commit()

    def convert(self, time):
        pos = ["s", "m", "h", "d"]
        time_dict = {"s": 1, "m": 60, "h": 3600, "d": 86400, "f": 259200}

        unit = time[-1]
        if unit not in pos:
            return -1

        try:
            val = int(time[:-1])
        except ValueError:
            return -2

        return val * time_dict[unit]


    @commands.hybrid_command(name="glist", description="Lists all ongoing giveaways.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_guild_permissions(manage_guild=True)
    async def glist(self, ctx):
        await self.cursor.execute("SELECT prize, ends_at, winners, message_id FROM Giveaway WHERE guild_id = ?", (ctx.guild.id,))
        giveaways = await self.cursor.fetchall()

        if not giveaways:
            embed = discord.Embed(description=" No ongoing giveaways.", color=0x000000)
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title="Ongoing Giveaways", color=0x000000)
        for giveaway in giveaways:
            prize, ends_at, winners, message_id = giveaway
            ends = datetime.datetime.fromtimestamp(ends_at)
            embed.add_field(
                name=prize,
                value=f"Ends: <t:{int(ends_at)}:R> (<t:{int(ends_at)}:f>)\nWinners: {winners}\n[Jump to Message](https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{message_id})",
                inline=False
            )

        await ctx.send(embed=embed)
import discord
from discord.ext import commands
from discord import app_commands, Interaction
from difflib import get_close_matches
from contextlib import suppress
from core import Context
from core.Tempest import Tempest
from core.Cog import Cog
from utils.Tools import getConfig
from itertools import chain
import json
from utils import help as vhelp
from utils import Paginator, DescriptionEmbedPaginator, FieldPagePaginator, TextPaginator
import asyncio
from utils.config import serverLink
from utils.Tools import *

color = 0x000000
client = Tempest()

class HelpCommand(commands.HelpCommand):

  async def send_ignore_message(self, ctx, ignore_type: str):

    if ignore_type == "channel":
      await ctx.reply(f"This channel is ignored.", mention_author=False)
    elif ignore_type == "command":
      await ctx.reply(f"{ctx.author.mention} This Command, Channel, or You have been ignored here.", delete_after=6)
    elif ignore_type == "user":
      await ctx.reply(f"You are ignored.", mention_author=False)


  async def on_help_command_error(self, ctx, error):
    errors = [
      commands.CommandOnCooldown, commands.CommandNotFound,
      discord.HTTPException, commands.CommandInvokeError
    ]
    if not type(error) in errors:
      await self.context.reply(f"Unknown Error Occurred\n{error.original}",
                               mention_author=False)
    else:
      if type(error) == commands.CommandOnCooldown:
        return

    return await super().on_help_command_error(ctx, error)

  
  async def command_not_found(self, string: str) -> None:
    ctx = self.context
    check_ignore = await ignore_check().predicate(ctx)
    check_blacklist = await blacklist_check().predicate(ctx)

    if not check_blacklist:
        return

    if not check_ignore:
        await self.send_ignore_message(ctx, "command")
        return

    cmds = (str(cmd) for cmd in self.context.bot.walk_commands())
    matches = get_close_matches(string, cmds)

    embed = discord.Embed(
        title="",
        description=f"Command not found with the name `{string}`.",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1275364856631005256.png")
    embed.set_author(name="Command Not Found", icon_url=self.context.bot.user.avatar.url)
    embed.set_footer(text=f"Requested By {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    if matches:
        match_list = "\n".join([f"{index}. `{match}`" for index, match in enumerate(matches, start=1)])
        embed.add_field(name="Did you mean:", value=match_list, inline=True)

    await ctx.reply(embed=embed)

  
  async def send_bot_help(self, mapping):
    ctx = self.context
    check_ignore = await ignore_check().predicate(ctx)
    check_blacklist = await blacklist_check().predicate(ctx)

    if not check_blacklist:
      return

    if not check_ignore:
      await self.send_ignore_message(ctx, "command")
      return

    
    embed = discord.Embed(description="• **Loading Help module...**", color=color)
    ok = await self.context.reply(embed=embed)          
    data = await getConfig(self.context.guild.id)
    prefix = data["prefix"]
    filtered = await self.filter_commands(self.context.bot.walk_commands(),
                                              sort=True)
    slash = len([
  cmd for cmd in self.context.bot.tree.get_commands() 
  if isinstance(cmd, app_commands.Command)
])
    
    embed = discord.Embed(
      title="", color=0x000000)

    embed.add_field(name="📜 __**General Info:**__", value= f"🔴 Server Prefix:  **{prefix}** \n🔴 Total Commands: **{len(set(self.context.bot.walk_commands()))}**\n🔴 Total Slash Commands: **{slash}**\n🔴 **[Get Olympus](https://discord.com/oauth2/authorize?client_id=1144179659735572640&permissions=2113268958&scope=bot)** | **[Support](https://discord.com/invite/odx)**\n\n❓ __**How do you use me?**__\n>>> `{prefix}help <command/module>` to get more info regarding that command/module\nFor example: `{prefix}help antinuke`\n\n")

    embed.add_field(name="⭐ __**My Features**__", value=">>> **50+ Systems, including:**\n 🛡️ Security\n 🚨 Automoderation\n 🔧 Utility\n 🎵 Music\n 🛠️ Moderation\n 🧩 Customrole\n 🎉 Giveaway\n 🎙️ Voice\n 🎮 Games\n 👋 Welcomer\n 🪩 Autoreact & responder\n 📋 Autorole & Invc\n 🎭 Fun & AI Image Gen\n   And much more!...")
    embed.add_field(name="➡️ __**How to get help?**__", value=">>> ♨️ Use the Buttons, to swap the Pages\n♨️ Use the Menu to select all Help Pages, you want to display\n♨️ For any queries/help Contact the **[Support Team](https://discord.com/invite/odx).**")
    embed.set_footer(
      text=f"Requested By {self.context.author}",
      icon_url=self.context.author.avatar.url if self.context.author.avatar else self.context.author.default_avatar.url
    )
    embed.set_author(name=self.context.author, icon_url=self.context.author.avatar.url if self.context.author.avatar else self.context.author.default_avatar.url)

    #embed.timestamp = discord.utils.utcnow()
    view = vhelp.View(mapping=mapping,
                          ctx=self.context,
                          homeembed=embed,
                          ui=2)
    await asyncio.sleep(0.5)
    await ok.edit(embed=embed,view=view)



  
  async def send_command_help(self, command):
    ctx = self.context
    check_ignore = await ignore_check().predicate(ctx)
    check_blacklist = await blacklist_check().predicate(ctx)

    if not check_blacklist:
      return

    if not check_ignore:
      await self.send_ignore_message(ctx, "command")
      return
    
    sonu = f">>> {command.help}" if command.help else '>>> No Help Provided...'
    embed = discord.Embed(
        description=
        f"""```xml
<[] = optional | ‹› = required\nDon't type these while using Commands>```\n{sonu}""",
        color=color)
    alias = ' | '.join(command.aliases)

    embed.add_field(name="**Aliases**",
                      value=f"{alias}" if command.aliases else "No Aliases",
                      inline=False)
    embed.add_field(name="**Usage**",
                      value=f"`{self.context.prefix}{command.signature}`\n")
    embed.set_author(name=f"{command.qualified_name.title()} Command",
                       icon_url=self.context.bot.user.display_avatar.url)
    await self.context.reply(embed=embed, mention_author=False)

  def get_command_signature(self, command: commands.Command) -> str:
    parent = command.full_parent_name
    if len(command.aliases) > 0:
      aliases = ' | '.join(command.aliases)
      fmt = f'[{command.name} | {aliases}]'
      if parent:
        fmt = f'{parent}'
      alias = f'[{command.name} | {aliases}]'
    else:
      alias = command.name if not parent else f'{parent} {command.name}'
    return f'{alias} {command.signature}'

  def common_command_formatting(self, embed_like, command):
    embed_like.title = self.get_command_signature(command)
    if command.description:
      embed_like.description = f'{command.description}\n\n{command.help}'
    else:
      embed_like.description = command.help or 'No help found...'

  async def send_group_help(self, group):
    ctx = self.context
    check_ignore = await ignore_check().predicate(ctx)
    check_blacklist = await blacklist_check().predicate(ctx)

    if not check_blacklist:
        return

    if not check_ignore:
        await self.send_ignore_message(ctx, "command")
        return

    entries = [
        (
            f"➜ `{self.context.prefix}{cmd.qualified_name}`\n",
            f"{cmd.short_doc if cmd.short_doc else ''}\n\u200b"
        )
        for cmd in group.commands
    ]

    count = len(group.commands)

    embeds = FieldPagePaginator(
        entries=entries,
        title=f"{group.qualified_name.title()} [{count}]",
        description="< > Duty | [ ] Optional\n",
        per_page=4
    ).get_pages()

    paginator = Paginator(ctx, embeds)
    await paginator.paginate()
    
  async def send_cog_help(self, cog):
    ctx = self.context
    check_ignore = await ignore_check().predicate(ctx)
    check_blacklist = await blacklist_check().predicate(ctx)

    if not check_blacklist:
      return

    if not check_ignore:
      await self.send_ignore_message(ctx, "command")
      return


    entries = [(
      f"➜ `{self.context.prefix}{cmd.qualified_name}`",
      f"{cmd.short_doc if cmd.short_doc else ''}"
      f"\n\u200b",
    ) for cmd in cog.get_commands()]
    embeds = FieldPagePaginator(
      entries=entries,
      title=f"{cog.qualified_name.title()} ({len(cog.get_commands())})",
      description="< > Duty | [ ] Optional\n\n",
      color=color,
      per_page=4).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()


class Help(Cog, name="help"):

  def __init__(self, client: Tempest):
    self._original_help_command = client.help_command
    attributes = {
      'name':
      "help",
      'aliases': ['h'],
      'cooldown':
      commands.CooldownMapping.from_cooldown(1, 5, commands.BucketType.user),
      'help':
      'Shows help about bot, a command or a category'
    }
    client.help_command = HelpCommand(command_attrs=attributes)
    client.help_command.cog = self

  async def cog_unload(self):
    self.help_command = self._original_help_command


    
from __future__ import annotations
import discord
from discord.ext import commands
from core import *
from utils.Tools import *
from typing import Optional
import aiosqlite

class Ignore(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.db_path = "db/ignore.db"
    self.color = 0x000000
    bot.loop.create_task(self.initialize_db())

  async def initialize_db(self):
    async with aiosqlite.connect(self.db_path) as db:
      await db.execute("CREATE TABLE IF NOT EXISTS ignored_commands (guild_id INTEGER, command_name TEXT)")
      await db.execute("CREATE TABLE IF NOT EXISTS ignored_channels (guild_id INTEGER, channel_id INTEGER)")
      await db.execute("CREATE TABLE IF NOT EXISTS ignored_users (guild_id INTEGER, user_id INTEGER)")
      await db.execute("CREATE TABLE IF NOT EXISTS bypassed_users (guild_id INTEGER, user_id INTEGER)")
      await db.commit()

  @commands.group(name="ignore", help="Manage ignored commands, channels, users, and bypassed users.", invoke_without_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 5, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  async def _ignore(self, ctx):
    if ctx.subcommand_passed is None:
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)

  @_ignore.group(name="command", help="Manage ignored commands in this guild.", invoke_without_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 5, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  async def _command(self, ctx):
      if ctx.subcommand_passed is None:
          await ctx.send_help(ctx.command)
          ctx.command.reset_cooldown(ctx)

  @_command.command(name="add", help="Adds a command to the ignore list.")
  @commands.has_permissions(administrator=True)
  @blacklist_check()
  async def command_add(self, ctx: commands.Context, command_name: str):
      command_name_normalized = command_name.strip().lower()
      command = self.bot.get_command(command_name_normalized)
      if not command:
          embed = discord.Embed(title="❌ Error", description=f"`{command_name}` is not a valid command.", color=self.color)
          await ctx.reply(embed=embed, mention_author=False)
          return
      async with aiosqlite.connect(self.db_path) as db:
          cursor = await db.execute("SELECT COUNT(*) FROM ignored_commands WHERE guild_id = ?", (ctx.guild.id,))
          count = await cursor.fetchone()
          if count[0] >= 25:
              embed = discord.Embed(description="You can only add up to 25 commands to the ignore list.", color=self.color)
              await ctx.reply(embed=embed)
              return
          cursor = await db.execute("SELECT command_name FROM ignored_commands WHERE guild_id = ? AND command_name = ?", (ctx.guild.id, command_name_normalized))
          result = await cursor.fetchone()
          if result:
              embed = discord.Embed(description=f"`{command_name}` is already in the ignore commands list.", color=self.color)
              await ctx.reply(embed=embed, mention_author=False)
          else:
              await db.execute("INSERT INTO ignored_commands (guild_id, command_name) VALUES (?, ?)", (ctx.guild.id, command_name_normalized))
              await db.commit()
              embed = discord.Embed(title="✅ Success", description=f"Successfully added `{command_name}` to the ignore commands list.", color=self.color)
              await ctx.reply(embed=embed)

  @_command.command(name="remove", help="Removes a command from the ignore list.")
  @commands.has_permissions(administrator=True)
  @blacklist_check()
  async def command_remove(self, ctx: commands.Context, command_name: str):
      command_name_normalized = command_name.strip().lower()
      async with aiosqlite.connect(self.db_path) as db:
          cursor = await db.execute("SELECT command_name FROM ignored_commands WHERE guild_id = ? AND command_name = ?", (ctx.guild.id, command_name_normalized))
          result = await cursor.fetchone()
          if not result:
              embed = discord.Embed(title="❌ Error", description=f"`{command_name}` is not in the ignore commands list.", color=self.color)
              await ctx.reply(embed=embed)
          else:
              await db.execute("DELETE FROM ignored_commands WHERE guild_id = ? AND command_name = ?", (ctx.guild.id, command_name_normalized))
              await db.commit()
              embed = discord.Embed(title="✅ Success", description=f"Successfully removed `{command_name}` from the ignore commands list.", color=self.color)
              await ctx.reply(embed=embed)

  @_command.command(name="show", help="Displays the list of ignored commands.")
  @blacklist_check()
  @ignore_check()
  @commands.has_permissions(administrator=True)
  async def command_show(self, ctx: commands.Context):
      async with aiosqlite.connect(self.db_path) as db:
          cursor = await db.execute("SELECT command_name FROM ignored_commands WHERE guild_id = ?", (ctx.guild.id,))
          commands = await cursor.fetchall()
          if not commands:
              embed = discord.Embed(description="No commands are currently ignored in this server.", color=self.color)
              await ctx.reply(embed=embed, mention_author=False)
          else:
              entries = [f"`{command[0]}`" for command in commands]
              description = "\n".join(entries)
              embed = discord.Embed(title="Ignored Commands", description=description, color=self.color)
              await ctx.reply(embed=embed, mention_author=False)

  @_ignore.group(name="channel", help="Manage ignored channels in this guild.", invoke_without_command=True)
  @blacklist_check()
  #@ignore_check()
  @commands.cooldown(1, 5, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  async def _channel(self, ctx):
    if ctx.subcommand_passed is None:
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)

  @_channel.command(name="add", help="Adds a channel to the ignore list.")
  @blacklist_check()
  #@ignore_check()
  @commands.has_permissions(administrator=True)
  async def channel_add(self, ctx: commands.Context, channel: discord.TextChannel):
    async with aiosqlite.connect(self.db_path) as db:
      cursor = await db.execute("SELECT COUNT(*) FROM ignored_channels WHERE guild_id = ?", (ctx.guild.id,))
      count = await cursor.fetchone()

      if count[0] >= 30:
        embed = discord.Embed(title="🔔 Access Denied", description="You can only add up to 30 channels to the ignore list.", color=self.color)
        await ctx.reply(embed=embed)
        return

      cursor = await db.execute("SELECT channel_id FROM ignored_channels WHERE guild_id = ? AND channel_id = ?", (ctx.guild.id, channel.id))
      result = await cursor.fetchone()

      if result:
        embed = discord.Embed(title="❌ Error", description=f"{channel.mention} is already in the ignore channels list.", color=self.color)
        await ctx.reply(embed=embed, mention_author=False)
      else:
        await db.execute("INSERT INTO ignored_channels (guild_id, channel_id) VALUES (?, ?)", (ctx.guild.id, channel.id))
        await db.commit()
        embed = discord.Embed(title="✅ Success", description=f"Successfully added {channel.mention} to the ignore channels list.", color=self.color)
        await ctx.reply(embed=embed)

  @_channel.command(name="remove", help="Removes a channel from the ignore list.")
  @blacklist_check()
  #@ignore_check()
  @commands.has_permissions(administrator=True)
  async def channel_remove(self, ctx: commands.Context, channel: discord.TextChannel):
    async with aiosqlite.connect(self.db_path) as db:
      cursor = await db.execute("SELECT channel_id FROM ignored_channels WHERE guild_id = ? AND channel_id = ?", (ctx.guild.id, channel.id))
      result = await cursor.fetchone()

      if not result:
        embed = discord.Embed(title="❌ Error", description=f"{channel.mention} is not in the ignore channels list.", color=self.color)
        await ctx.reply(embed=embed)
      else:
        await db.execute("DELETE FROM ignored_channels WHERE guild_id = ? AND channel_id = ?", (ctx.guild.id, channel.id))
        await db.commit()
        embed = discord.Embed(title="✅ Success", description=f"Successfully removed {channel.mention} from the ignore channels list.", color=self.color)
        await ctx.reply(embed=embed)

  @_channel.command(name="show", help="Displays the list of ignored channels.")
  @blacklist_check()
  @ignore_check()
  @commands.has_permissions(administrator=True)
  async def channel_show(self, ctx: commands.Context):
    async with aiosqlite.connect(self.db_path) as db:
      cursor = await db.execute("SELECT channel_id FROM ignored_channels WHERE guild_id = ?", (ctx.guild.id,))
      channels = await cursor.fetchall()

      if not channels:
        embed = discord.Embed(description="No channels are currently ignored in this server.", color=self.color)
        await ctx.reply(embed=embed, mention_author=False)
      else:
        channel_mentions = [ctx.guild.get_channel(channel_id).mention if ctx.guild.get_channel(channel_id) else f"Channel ID {channel_id}" for channel_id, in channels]
        description = "\n".join(channel_mentions)
        embed = discord.Embed(title="Ignored Channels", description=description, color=self.color)
        await ctx.reply(embed=embed, mention_author=False)

  @_ignore.group(name="user", help="Manage ignored users in this guild.", invoke_without_command=True)
  @blacklist_check()
  @ignore_check()
  @commands.cooldown(1, 5, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  async def _user(self, ctx):
    if ctx.subcommand_passed is None:
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)

  @_user.command(name="add", help="Adds a user to the ignore list.")
  @commands.has_permissions(administrator=True)
  @blacklist_check()

  async def user_add(self, ctx: commands.Context, user: discord.User):
    async with aiosqlite.connect(self.db_path) as db:
      cursor = await db.execute("SELECT COUNT(*) FROM ignored_users WHERE guild_id = ?", (ctx.guild.id,))
      count = await cursor.fetchone()

      if count[0] >= 30:
        embed = discord.Embed(title="🔔 Access Denied", description="You can only add up to 30 users to the ignore list.", color=self.color)
        await ctx.reply(embed=embed)
        return

      cursor = await db.execute("SELECT user_id FROM ignored_users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, user.id))
      result = await cursor.fetchone()

      if result:
        embed = discord.Embed(title="❌ Error", description=f"{user.mention} is already in the ignore users list.", color=self.color)
        await ctx.reply(embed=embed, mention_author=False)
      else:
        await db.execute("INSERT INTO ignored_users (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, user.id))
        await db.commit()
        embed = discord.Embed(title="✅ Success", description=f"Successfully added {user.mention} to the ignore users list.", color=self.color)
        await ctx.reply(embed=embed)

  @_user.command(name="remove", help="Removes a user from the ignore list.")
  @blacklist_check()

  @commands.has_permissions(administrator=True)
  async def user_remove(self, ctx: commands.Context, user: discord.User):
    async with aiosqlite.connect(self.db_path) as db:
      cursor = await db.execute("SELECT user_id FROM ignored_users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, user.id))
      result = await cursor.fetchone()

      if not result:
        embed = discord.Embed(title="❌ Error", description=f"{user.mention} is not in the ignore users list.", color=self.color)
        await ctx.reply(embed=embed)
      else:
        await db.execute("DELETE FROM ignored_users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, user.id))
        await db.commit()
        embed = discord.Embed(title="✅ Success", description=f"Successfully removed {user.mention} from the ignore users list.", color=self.color)
        await ctx.send(embed=embed)

  @_user.command(name="show", help="Displays the list of ignored users.")
  @blacklist_check()
  @ignore_check()
  @commands.has_permissions(administrator=True)
  async def user_show(self, ctx: commands.Context):
    async with aiosqlite.connect(self.db_path) as db:
      cursor = await db.execute("SELECT user_id FROM ignored_users WHERE guild_id = ?", (ctx.guild.id,))
      users = await cursor.fetchall()

      if not users:
        embed = discord.Embed(description="No users are currently ignored in this server.", color=self.color)
        await ctx.reply(embed=embed, mention_author=False)
      else:
        user_mentions = [ctx.guild.get_member(user_id).mention if ctx.guild.get_member(user_id) else f"User ID {user_id}" for user_id, in users]
        description = "\n".join(user_mentions)
        embed = discord.Embed(title="Ignored Users", description=description, color=self.color)
        await ctx.reply(embed=embed, mention_author=False)

  @_ignore.group(name="bypass", help="Manage bypassed users in this guild.", invoke_without_command=True)
  @commands.cooldown(1, 5, commands.BucketType.user)
  @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
  @commands.guild_only()
  @commands.has_permissions(administrator=True)
  async def _bypass(self, ctx):
    if ctx.subcommand_passed is None:
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)

  @_bypass.command(name="add", help="Adds a user to the bypass list.")
  @blacklist_check()
  @ignore_check()
  
  @commands.has_permissions(administrator=True)
  async def bypass_add(self, ctx: commands.Context, user: discord.User):
    async with aiosqlite.connect(self.db_path) as db:
      cursor = await db.execute("SELECT COUNT(*) FROM bypassed_users WHERE guild_id = ?", (ctx.guild.id,))
      count = await cursor.fetchone()

      if count[0] >= 30:
        embed = discord.Embed(description="You can only add up to 30 users to the bypass list.", color=self.color)
        await ctx.reply(embed=embed)
        return

      cursor = await db.execute("SELECT user_id FROM bypassed_users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, user.id))
      result = await cursor.fetchone()

      if result:
        embed = discord.Embed(title="❌ Error", description=f"{user.mention} is already in the bypass users list.", color=self.color)
        await ctx.reply(embed=embed, mention_author=False)
      else:
        await db.execute("INSERT INTO bypassed_users (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, user.id))
        await db.commit()
        embed = discord.Embed(title="✅ Success", description=f"Successfully added {user.mention} to the bypass users list.", color=self.color)
        await ctx.reply(embed=embed)

  @_bypass.command(name="remove", help="Removes a user from the bypass list.")
  @blacklist_check()
  @ignore_check()
  @commands.has_permissions(administrator=True)
  async def bypass_remove(self, ctx: commands.Context, user: discord.User):
    async with aiosqlite.connect(self.db_path) as db:
      cursor = await db.execute("SELECT user_id FROM bypassed_users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, user.id))
      result = await cursor.fetchone()

      if not result:
        embed = discord.Embed(description=f"{user.mention} is not in the bypass users list.", color=self.color)
        await ctx.reply(embed=embed)
      else:
        await db.execute("DELETE FROM bypassed_users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, user.id))
        await db.commit()
        embed = discord.Embed(title="✅ Success", description=f"Successfully removed {user.mention} from the bypass users list.", color=self.color)
        await ctx.reply(embed=embed)

  @_bypass.command(name="show", aliases=["list"], help="Displays the list of bypassed users.")
  @blacklist_check()
  @ignore_check()
  @commands.has_permissions(administrator=True)
  async def bypass_show(self, ctx: commands.Context):
    async with aiosqlite.connect(self.db_path) as db:
      cursor = await db.execute("SELECT user_id FROM bypassed_users WHERE guild_id = ?", (ctx.guild.id,))
      users = await cursor.fetchall()

      if not users:
        embed = discord.Embed(description="No users are currently bypassed in this server.", color=self.color)
        await ctx.reply(embed=embed, mention_author=False)
      else:
        user_mentions = [ctx.guild.get_member(user_id).mention if ctx.guild.get_member(user_id) else f"User ID {user_id}" for user_id, in users]
        description = "\n".join(user_mentions)
        embed = discord.Embed(title="Bypassed Users", description=description, color=self.color)
        await ctx.reply(embed=embed, mention_author=False)

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import random
import time
from utils.ai_utils import poly_image_gen, generate_image_prodia
from prodia.constants import Model
from utils.Tools import *

blacklisted_words = [
    "naked", "nude", "nudes", "teen", "gay", "lesbian", "porn", "xnxx",
    "bitch", "loli", "hentai", "explicit", "pornography", "adult", "XXX",
    "sex", "erotic", "dick", "vagina", "pussy", "gay", "lick", "creampie", "nsfw",
    "hardcore", "ass", "anal", "anus", "boobs", "tits", "cum", "cunnilingus", "squirt", "penis", "lick", "masturbate", "masturbation ", "orgasm", "orgy", "fap", "fapping", "fuck", "fucking", "handjob", "cowgirl", "doggystyle", "blowjob", "boobjob", "boobies", "horny", "nudity"
]

blocked=["minor", "minors", "kid", "kids", "child", "children", "baby", "babies", "toddler", "childporn", "todd", "underage"]

class CooldownManager:
    def __init__(self, rate: int, per: float):
        self.rate = rate
        self.per = per
        self.cooldowns = {}

    def check_cooldown(self, user_id: int):
        now = time.time()
        if user_id not in self.cooldowns:
            self.cooldowns[user_id] = [now]
            return None

        self.cooldowns[user_id] = [timestamp for timestamp in self.cooldowns[user_id] if now - timestamp < self.per]
        if len(self.cooldowns[user_id]) >= self.rate:
            retry_after = self.per - (now - self.cooldowns[user_id][0])
            return retry_after
        self.cooldowns[user_id].append(now)
        return None

cooldown_manager = CooldownManager(rate=1, per=60.0)

async def cooldown_check(interaction: discord.Interaction):
    retry_after = cooldown_manager.check_cooldown(interaction.user.id)
    if retry_after:
        await interaction.response.send_message(f"You are on cooldown. Try again in {retry_after:.2f} seconds.", ephemeral=True)
        return False
    return True





class AiStuffCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @app_commands.command(name="imagine", description="Generate an image using AI")

    #@app_commands.check(blacklist_check())
    #@app_commands.check(ignore_check())
    #@app_commands.check(cooldown_check)
    @discord.app_commands.choices(
        model=[
            discord.app_commands.Choice(name='✨ Elldreth vivid mix (Landscapes, Stylized characters, nsfw)', value='ELLDRETHVIVIDMIX'),
            discord.app_commands.Choice(name='💪 Deliberate v2 (Anything you want, nsfw)', value='DELIBERATE'),
            discord.app_commands.Choice(name='🔮 Dreamshaper (HOLYSHIT this so good)', value='DREAMSHAPER_6'),
            discord.app_commands.Choice(name='🎼 Lyriel', value='LYRIEL_V16'),
            discord.app_commands.Choice(name='💥 Anything diffusion (Good for anime)', value='ANYTHING_V4'),
            discord.app_commands.Choice(name='🌅 Openjourney (Midjourney alternative)', value='OPENJOURNEY'),
            discord.app_commands.Choice(name='🏞️ Realistic (Lifelike pictures)', value='REALISTICVS_V20'),
            discord.app_commands.Choice(name='👨‍🎨 Portrait (For headshots I guess)', value='PORTRAIT'),
            discord.app_commands.Choice(name='🌟 Rev animated (Illustration, Anime)', value='REV_ANIMATED'),
            discord.app_commands.Choice(name='🤖 Analog', value='ANALOG'),
            discord.app_commands.Choice(name='🌌 AbyssOrangeMix', value='ABYSSORANGEMIX'),
            discord.app_commands.Choice(name='🌌 Dreamlike v1', value='DREAMLIKE_V1'),
            discord.app_commands.Choice(name='🌌 Dreamlike v2', value='DREAMLIKE_V2'),
            discord.app_commands.Choice(name='🌌 Dreamshaper 5', value='DREAMSHAPER_5'),
            discord.app_commands.Choice(name='🌌 MechaMix', value='MECHAMIX'),
            discord.app_commands.Choice(name='🌌 MeinaMix', value='MEINAMIX'),
            discord.app_commands.Choice(name='🌌 Stable Diffusion v14', value='SD_V14'),
            discord.app_commands.Choice(name='🌌 Stable Diffusion v15', value='SD_V15'),
            discord.app_commands.Choice(name="🌌 Shonin's Beautiful People", value='SBP'),
            discord.app_commands.Choice(name="🌌 TheAlly's Mix II", value='THEALLYSMIX'),
            discord.app_commands.Choice(name='🌌 Timeless', value='TIMELESS')
        ],
        sampler=[
            discord.app_commands.Choice(name='📏 Euler (Recommended)', value='Euler'),
            discord.app_commands.Choice(name='📏 Euler a', value='Euler a'),
            discord.app_commands.Choice(name='📐 Heun', value='Heun'),
            discord.app_commands.Choice(name='💥 DPM++ 2M Karras', value='DPM++ 2M Karras'),
            discord.app_commands.Choice(name='💥 DPM++ SDE Karras', value='DPM++ SDE Karras'),
            discord.app_commands.Choice(name='🔍 DDIM', value='DDIM')
        ]
    )
    @discord.app_commands.describe(
        prompt="Write an amazing prompt for an image",
        model="Model to generate image",
        sampler="Sampler for denoising",
        negative="Prompt that specifies what you do not want the model to generate",
    )
    async def imagine(self, interaction: discord.Interaction, prompt: str, model: discord.app_commands.Choice[str], sampler: discord.app_commands.Choice[str], negative: str = None, seed: int = None):
        retry_after = cooldown_manager.check_cooldown(interaction.user.id)
        if retry_after:
            await interaction.response.send_message(f"You are on cooldown. Try again in {retry_after:.2f} seconds.", ephemeral=True)
            return

        await interaction.response.defer()

        is_nsfw = any(word in prompt.lower() for word in blacklisted_words)

        is_child = any(word in prompt.lower() for word in blocked)

        if is_child:
            await interaction.followup.send("Child porn is not allowed as it violates Discord ToS. Please try again with a different peompt.")
            return

        if is_nsfw and not interaction.channel.nsfw:
            await interaction.followup.send("You can create NSFW images in NSFW channels only. Please try in an appropriate channel.", ephemeral=True)
            return

        model_uid = Model[model.value].value[0]

        try:
            imagefileobj = await generate_image_prodia(prompt, model_uid, sampler.value, seed, negative)
        except aiohttp.ClientPayloadError:
            await interaction.followup.send("An error occurred while generating the image. Please try again later.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {e}", ephemeral=True)
            return

        if is_nsfw:
            img_file = discord.File(imagefileobj, filename="image.png", spoiler=True, description=prompt)
            prompt = f"||{prompt}||"
        else:
            img_file = discord.File(imagefileobj, filename="image.png", description=prompt)

        embed = discord.Embed(color=0xFF0000) if is_nsfw else discord.Embed(color=discord.Color.random())
        embed.title = f"Generated Image by {interaction.user.display_name}"
        embed.add_field(name='Prompt', value=f'- {prompt}', inline=False)
        embed.add_field(name='Image Details', value=f"- **Model:** {model.value}\n- **Sampler:** {sampler.value}\n- **Seed:**{seed}", inline=True)
        embed.set_footer(text=f"© Tempest Federation", icon_url=self.bot.user.avatar.url)
        #embed.set_thumbnail(url=img_file)
        if negative:
            embed.add_field(name='Negative Prompt', value=f'- {negative}', inline=False)
        if is_nsfw:
            embed.add_field(name='NSFW', value=f'- {str(is_nsfw)}', inline=True)
            


        await interaction.followup.send(embed=embed, file=img_file, ephemeral=True)


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
from utils.Tools import *

class Invcrole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'db/invc.db'
        self.bot.loop.create_task(self.create_table())

    async def create_table(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS vcroles (
                    guild_id INTEGER PRIMARY KEY,
                    role_id INTEGER NOT NULL
                )
            ''')
            await db.commit()

    @commands.group(name='vcrole', help="Vcrole Setup commands", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def vcrole(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @vcrole.command(name='add', help="Adds a role to the vcrole list")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def add(self, ctx, role: discord.Role):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT role_id FROM vcroles WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    embed = discord.Embed(title="🔔 Access Denied",
                                          description=f"VC role is already set in this guild with the role {ctx.guild.get_role(row[0]).mention}.\nPlease **remove** it to add another one.", color=0x000000)
                    await ctx.reply(embed=embed)
                    return
            await db.execute('INSERT INTO vcroles (guild_id, role_id) VALUES (?, ?)', (ctx.guild.id, role.id))
            await db.commit()
            embed = discord.Embed(title="✅ Success",
                                  description=f"VC role {role.mention} added for this guild.", color=0x000000)
            await ctx.reply(embed=embed)

    @vcrole.command(name='remove', aliases=["reset"], help="Removes the role from vcrole list")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx, role: discord.Role):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT role_id FROM vcroles WHERE guild_id = ? AND role_id = ?', (ctx.guild.id, role.id)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    embed = discord.Embed(title="❌ Error",
                                          description="Given role is not set in VC role.", color=0x000000)
                    await ctx.send(embed=embed)
                    return
            await db.execute('DELETE FROM vcroles WHERE guild_id = ? AND role_id = ?', (ctx.guild.id, role.id))
            await db.commit()
            embed = discord.Embed(title="✅ Success",
                                  description=f"VC role {role.mention} removed for this guild.", color=0x000000)
            await ctx.send(embed=embed)

    @vcrole.command(name='config', aliases=['view', 'show'], help="Shows the Current vcrole in this Guild")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def config(self, ctx):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT role_id FROM vcroles WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    embed = discord.Embed(title="❌ Error",
                                          description="VC role is not set in this guild.", color=0x000000)
                    await ctx.send(embed=embed)
                    return
                role = ctx.guild.get_role(row[0])
                embed = discord.Embed(title="VC Role Configuration",
                                      description=f"Current VC role in this guild is {role.mention}.", color=0x000000)
                embed.set_footer(text="Make sure to place My role above Vc role")
                await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT role_id FROM vcroles WHERE guild_id = ?', (member.guild.id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return
                    role = member.guild.get_role(row[0])

                    if after.channel and role not in member.roles:
                        await self.add_role_with_retry(member, role, reason="Member Joined VC | Olympus Invcrole")
                    elif not after.channel and role in member.roles:
                        await self.remove_role_with_retry(member, role, reason="Member Left VC | Olympus Invcrole")
        except discord.Forbidden:
            print(f"Bot lacks permissions to maange role in a guild during Invc Event .")
        except Exception as e:
            print(f"Error in on_voice_state_update: {e}")

    async def add_role_with_retry(self, member, role, reason, retries=5):
        attempt = 0
        while attempt < retries:
            try:
                await member.add_roles(role, reason=reason)
                break
            except discord.errors.RateLimited as e:
                retry_after = e.retry_after if hasattr(e, 'retry_after') else 1
                await asyncio.sleep(retry_after)
            except discord.HTTPException as e:
                print(f"Error adding role: {e}")
                break
            attempt += 1

    async def remove_role_with_retry(self, member, role, reason, retries=5):
        attempt = 0
        while attempt < retries:
            try:
                await member.remove_roles(role, reason=reason)
                break
            except discord.errors.RateLimited as e:
                retry_after = e.retry_after if hasattr(e, 'retry_after') else 1
                await asyncio.sleep(retry_after)
            except discord.HTTPException as e:
                print(f"Error removing role: {e}")
                break
            attempt += 1


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord import ui, ButtonStyle, SelectOption
import requests
import asyncio
from utils.Tools import *

class MapView(ui.View):
    def __init__(self, bot, location, ctx):
        super().__init__(timeout=None)
        self.bot = bot
        self.location = location
        self.ctx = ctx
        self.zoom_level = 14
        self.map_style = 'map'
        self.map_size = '1200,900'
        self.coordinates = self.get_coordinates(location)
        self.latitude, self.longitude = None, None
        if self.coordinates != (None, None):
            self.latitude, self.longitude = float(self.coordinates[0]), float(self.coordinates[1])
        self.update_map()

        self.add_item(MapStyleSelect(self))
        self.add_item(MapSizeSelect(self))

    def get_coordinates(self, location):
        
        try:
            headers = {'User-Agent': 'Olympus Bot (https://olyumpus.vercel.app)'}
            response = requests.get(f'https://nominatim.openstreetmap.org/search?q={location}&format=json', headers=headers)
            response.raise_for_status()
            data = response.json()[0]
            return data['lat'], data['lon']
        except (requests.RequestException, IndexError) as e:
            print(f"Failed to get coordinates: {e}")
            return None, None

    def update_map(self):
        if self.latitude is None or self.longitude is None:
            return
        self.map_url = f'https://www.mapquestapi.com/staticmap/v5/map?key=E2SaL3qiTpXQ43nxZFBp0wzEnBI6pqbG&center={self.latitude},{self.longitude}&zoom={self.zoom_level}&size={self.map_size}&type={self.map_style}'

    async def update_embed(self, interaction: discord.Interaction):
        if self.latitude is None or self.longitude is None:
            await interaction.response.send_message("Failed to retrieve map data. Please try again.", ephemeral=True)
            return
        embed = discord.Embed(title=f"• Map of {self.location}", color=0x000000)
        embed.add_field(name="🌐  Open in Webpage", value=f"➜  **[Click Here](https://www.openstreetmap.org/?mlat={self.latitude}&mlon={self.longitude}&zoom={self.zoom_level})**")
        embed.add_field(name="🔍  Current Zoom Level", value=f"➜  {str(self.zoom_level)}")
        embed.add_field(name="🗺️  Map Style", value=f"➜  {self.map_style}")
        embed.add_field(name="📏  Map Size", value=f"➜  {self.map_size}")
        embed.add_field(name="📍 Current Coordinates", value=f"➜  {self.latitude}, {self.longitude}")
        embed.set_image(url=self.map_url)
        embed.set_footer(text="Made by Tempest Federation™")
        try:
            await interaction.message.edit(embed=embed, view=self)
        except Exception as e:
            await interaction.response.send_message(f"Error updating message: {e}", ephemeral=True)


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                embed=discord.Embed(description="Sorry only the requested author can control this", color=0x000000),
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="", emoji="•", style=ButtonStyle.secondary)
    async def move_left(self, interaction: discord.Interaction, button: ui.Button):
        if self.longitude is not None:
            self.longitude -= 0.01
            self.update_map()
            await self.update_embed(interaction)
            await interaction.response.send_message(embed=discord.Embed(description="Moved left."), ephemeral=True)
    
    @discord.ui.button(label="",  emoji="•", style=ButtonStyle.secondary)
    async def move_up(self, interaction: discord.Interaction, button: ui.Button):
        if self.latitude is not None:
            self.latitude += 0.01
            self.update_map()
            await self.update_embed(interaction)
            await interaction.response.send_message(embed=discord.Embed(description="Moved up."), ephemeral=True)

    @discord.ui.button(label="", emoji="•", style=ButtonStyle.danger)
    async def delete_embed(self, interaction: discord.Interaction, button: ui.Button):
        try:
            await interaction.message.delete()
        except Exception as e:
            await interaction.response.send_message(f"Error deleting message: {e}", ephemeral=True)


    @discord.ui.button(label="", emoji="•", style=ButtonStyle.secondary)
    async def move_down(self, interaction: discord.Interaction, button: ui.Button):
        if self.latitude is not None:
            self.latitude -= 0.01
            self.update_map()
            await self.update_embed(interaction)
            await interaction.response.send_message(embed=discord.Embed(description="Moved down."), ephemeral=True)

    @discord.ui.button(label="", emoji="➡️", style=ButtonStyle.secondary)
    async def move_right(self, interaction: discord.Interaction, button: ui.Button):
        if self.longitude is not None:
            self.longitude += 0.01
            self.update_map()
            await self.update_embed(interaction)
            await interaction.response.send_message(embed=discord.Embed(description="Moved right."), ephemeral=True)
    
    @discord.ui.button(label="Zoom In", style=ButtonStyle.primary)
    async def zoom_in(self, interaction: discord.Interaction, button: ui.Button):
        print("Zooming in")
        self.zoom_level = min(self.zoom_level + 1, 18)
        self.update_map()
        await self.update_embed(interaction)
        await interaction.response.send_message(embed=discord.Embed(description="Zoomed in."), ephemeral=True)

    @discord.ui.button(label="Zoom Out", style=ButtonStyle.primary)
    async def zoom_out(self, interaction: discord.Interaction, button: ui.Button):
        print("Zooming out")
        self.zoom_level = max(self.zoom_level - 1, 0)
        self.update_map()
        await self.update_embed(interaction)
        await interaction.response.send_message(embed=discord.Embed(description="Zoomed Out."), ephemeral=True)


    @discord.ui.button(label="Enter Coordinates", style=ButtonStyle.primary)
    async def enter_coordinates(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Please enter the coordinates (latitude, longitude):", ephemeral=True)

        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel

        try:
            coords_msg = await self.bot.wait_for('message', check=check, timeout=60)
            coords = coords_msg.content.split(',')
            if len(coords) == 2:
                self.latitude, self.longitude = float(coords[0].strip()), float(coords[1].strip())
                self.update_map()
                await self.update_embed(interaction)
                await interaction.response.send_message(embed=discord.Embed(description="Coordinates updated."), ephemeral=True)
            else:
                await interaction.response.send_message("Invalid coordinates format. Please enter in the format 'latitude, longitude'.", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("You took too long to respond. Please try again.", ephemeral=True)

    @discord.ui.button(label="Enter Address", style=ButtonStyle.success)
    async def enter_address(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Please enter the address:", ephemeral=True)


        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel

        try:
            address_msg = await self.bot.wait_for('message', check=check, timeout=60)
            address = address_msg.content
            self.coordinates = self.get_coordinates(address)
            if self.coordinates == (None, None):
                await interaction.response.send_message("Failed to retrieve coordinates for the address. Please try again.", ephemeral=True)
            else:
                self.latitude, self.longitude = float(self.coordinates[0]), float(self.coordinates[1])
                self.update_map()
                await self.update_embed(interaction)
                await interaction.response.send_message(embed=discord.Embed(description="Address updated."), ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("You took too long to respond. Please try again.", ephemeral=True)


class MapStyleSelect(ui.Select):
    def __init__(self, map_view):
        super().__init__(placeholder='Select Map Style')
        self.map_view = map_view  
        options = [
            SelectOption(label='Map', value='map'),
            SelectOption(label='Satellite', value='sat'),
            SelectOption(label='Hybrid', value='hyb'),
            SelectOption(label='Light', value='light'),
            SelectOption(label='Dark', value='dark'),
        ]
        self.options = options

    async def callback(self, interaction: discord.Interaction):
        print(f"Changing map style to {self.values[0]}")
        self.map_view.map_style = self.values[0]
        self.map_view.update_map()
        await self.map_view.update_embed(interaction)
        await interaction.response.send_message("Map style updated successfully.", ephemeral=True)

class MapSizeSelect(ui.Select):
    def __init__(self, map_view):
        super().__init__(placeholder='Select Map Size')
        self.map_view = map_view  
        options = [
            SelectOption(label='400x300', value='400,300'),
            SelectOption(label='800x600', value='800,600'),
            SelectOption(label='1200x900', value='1200,900')
        ]
        self.options = options

    async def callback(self, interaction: discord.Interaction):
        print(f"Changing map size to {self.values[0]}")
        self.map_view.map_size = self.values[0]
        self.map_view.update_map()
        await self.map_view.update_embed(interaction)
        await interaction.response.send_message("Map size updated successfully.", ephemeral=True)


class Map(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="map", help="Shows a map of a location", usage="<location>", description="Shows a map of a location")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def map(self, ctx, *, location: str):
        view = MapView(self.bot, location, ctx)
        if view.coordinates == (None, None):
            await ctx.send("Failed to retrieve coordinates for the location. Please try again.")
            return
        embed = discord.Embed(title=f"• Map of {location}", color=0x000000)
        embed.add_field(name="🌐  Open in Webpage", value=f"➜  **[Click Here](https://www.openstreetmap.org/?mlat={view.coordinates[0]}&mlon={view.coordinates[1]}&zoom={view.zoom_level})**")
        embed.add_field(name="🔍  Current Zoom Level", value=f"➜  {str(view.zoom_level)}")
        embed.add_field(name="🗺️  Map Style", value=f"➜  {view.map_style}")
        embed.add_field(name="📏  Map Size", value=f"➜  {view.map_size}")
        embed.add_field(name="📍 Current Coordinates", value=f"➜  {view.coordinates[0]}, {view.coordinates[1]}")
        embed.set_image(url=view.map_url)
        embed.set_footer(text=f"Requested By {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=embed, view=view)




    """
    @Author: Sonu Jana
        + Discord: me.sonu
        + Community: https://discord.gg/odx (Tempest Federation)
        + for any queries reach out Community or DM me.
    """
import discord
import aiosqlite
from discord.ext import commands
from utils.Tools import blacklist_check, ignore_check
from collections import defaultdict
import time

class Media(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.infractions = defaultdict(list)
        

    async def set_db(self):
        async with aiosqlite.connect('db/media.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS media_channels (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS media_bypass (
                    guild_id INTEGER,
                    user_id INTEGER,
                    PRIMARY KEY (guild_id, user_id)
                )
            ''')
            await db.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.set_db()

    @commands.hybrid_group(name="media", help="Setup Media channel, Media channel will not allow users to send messages other than media files.", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def media(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @media.command(name="setup", aliases=["set", "add"], help="Sets up a media-only channel for the server")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx, *, channel: discord.TextChannel):
        async with aiosqlite.connect('db/media.db') as db:
            async with db.execute('SELECT channel_id FROM media_channels WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    embed = discord.Embed(
                        title="❌ Error",
                        description="A media channel is already set. Please remove it before setting a new one.",
                        color=0x000000
                    )
                    await ctx.reply(embed=embed)
                    return

            await db.execute('INSERT INTO media_channels (guild_id, channel_id) VALUES (?, ?)', (ctx.guild.id, channel.id))
            await db.commit()

        embed = discord.Embed(
            title="✅ Success",
            description=f"Successfully set {channel.mention} as the media-only channel.",
            color=0x000000
        )
        embed.set_footer(text="Make sure to grant me \"Manage Messages\" permission for functioning of media channel.")
        await ctx.reply(embed=embed)

    @media.command(name="remove", aliases=["reset", "delete"], help="Removes the current media-only channel")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx):
        async with aiosqlite.connect('db/media.db') as db:
            async with db.execute('SELECT channel_id FROM media_channels WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
                result = await cursor.fetchone()
                if not result:
                    embed = discord.Embed(
                        title="❌ Error",
                        description="There is no media-only channel set for this server.",
                        color=0x000000
                    )
                    await ctx.reply(embed=embed)
                    return

            await db.execute('DELETE FROM media_channels WHERE guild_id = ?', (ctx.guild.id,))
            await db.commit()

        embed = discord.Embed(
            title="✅ Success",
            description="Successfully removed the media-only channel.",
            color=0x000000
        )
        await ctx.reply(embed=embed)

    @media.command(name="config", aliases=["settings", "show"], help="Shows the configured media-only channel")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def config(self, ctx):
        async with aiosqlite.connect('db/media.db') as db:
            async with db.execute('SELECT channel_id FROM media_channels WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
                result = await cursor.fetchone()
                if not result:
                    embed = discord.Embed(
                        title="❌ Error",
                        description="There is no media-only channel set for this server.",
                        color=0x000000
                    )
                    await ctx.reply(embed=embed)
                    return

        channel = self.client.get_channel(result[0])
        embed = discord.Embed(
            title="Media Only Channel",
            description=f"The configured media-only channel is {channel.mention}.",
            color=0x000000
        )
        await ctx.reply(embed=embed)

    @media.group(name="bypass", help="Add/Remove user to bypass in Media only channel, Bypassed users can send messages in Media channel.", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def bypass(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @bypass.command(name="add", help="Adds a user to the bypass list")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def bypass_add(self, ctx, user: discord.Member):
        async with aiosqlite.connect('db/media.db') as db:
            async with db.execute('SELECT COUNT(*) FROM media_bypass WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
                count = await cursor.fetchone()
                if count[0] >= 25:
                    embed = discord.Embed(
                        title="❌ Error",
                        description="The bypass list can only hold up to 25 users.",
                        color=0x000000
                    )
                    await ctx.reply(embed=embed)
                    return

            async with db.execute('SELECT 1 FROM media_bypass WHERE guild_id = ? AND user_id = ?', (ctx.guild.id, user.id)) as cursor:
                result = await cursor.fetchone()
                if result:
                    embed = discord.Embed(
                        title="❌ Error",
                        description=f"{user.mention} is already in the bypass list.",
                        color=0x000000
                    )
                    await ctx.reply(embed=embed)
                    return

            await db.execute('INSERT INTO media_bypass (guild_id, user_id) VALUES (?, ?)', (ctx.guild.id, user.id))
            await db.commit()

        embed = discord.Embed(
            title="✅ Success",
            description=f"{user.mention} has been added to the bypass list.",
            color=0x000000
        )
        await ctx.reply(embed=embed)

    @bypass.command(name="remove", help="Removes a user from the bypass list")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def bypass_remove(self, ctx, user: discord.Member):
        async with aiosqlite.connect('db/media.db') as db:
            async with db.execute('SELECT 1 FROM media_bypass WHERE guild_id = ? AND user_id = ?', (ctx.guild.id, user.id)) as cursor:
                result = await cursor.fetchone()
                if not result:
                    embed = discord.Embed(
                        title="❌ Error",
                        description=f"{user.mention} is not in the bypass list.",
                        color=0x000000
                    )
                    await ctx.reply(embed=embed)
                    return

            await db.execute('DELETE FROM media_bypass WHERE guild_id = ? AND user_id = ?', (ctx.guild.id, user.id))
            await db.commit()

        embed = discord.Embed(
            title="✅ Success",
            description=f"{user.mention} has been removed from the bypass list.",
            color=0x000000
        )
        await ctx.reply(embed=embed)

    @bypass.command(name="show", aliases=["list", "view"], help="Shows the bypass list")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def bypass_show(self, ctx):
        async with aiosqlite.connect('db/media.db') as db:
            async with db.execute('SELECT user_id FROM media_bypass WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
                result = await cursor.fetchall()
                if not result:
                    embed = discord.Embed(
                        title="Bypass List",
                        description="There are no users in the bypass list.",
                        color=0x000000
                    )
                    await ctx.reply(embed=embed)
                    return

        users = [self.client.get_user(user_id).mention for user_id, in result]
        user_mentions = "\n".join(users)

        embed = discord.Embed(
            title="Bypass List",
            description=user_mentions,
            color=0x000000
        )
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        async with aiosqlite.connect('db/media.db') as db:
            async with db.execute('SELECT channel_id FROM media_channels WHERE guild_id = ?', (message.guild.id,)) as cursor:
                media_channel = await cursor.fetchone()

        if media_channel and message.channel.id == media_channel[0]:
            async with aiosqlite.connect('db/block.db') as block_db:
                async with block_db.execute('SELECT 1 FROM user_blacklist WHERE user_id = ?', (message.author.id,)) as cursor:
                    blacklisted = await cursor.fetchone()

            async with aiosqlite.connect('db/media.db') as db:
                async with db.execute('SELECT 1 FROM media_bypass WHERE guild_id = ? AND user_id = ?', (message.guild.id, message.author.id)) as cursor:
                    bypassed = await cursor.fetchone()

            if blacklisted or bypassed:
                return

            if not message.attachments:
                try:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention} This channel is configured for Media only. Please send only media files.",
                    delete_after=5
                )
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass
                except Exception:
                    pass

                current_time = time.time()
                self.infractions[message.author.id].append(current_time)

                
                self.infractions[message.author.id] = [
                    infraction for infraction in self.infractions[message.author.id]
                    if current_time - infraction <= 5
                ]

                if len(self.infractions[message.author.id]) >= 5:  
                    async with aiosqlite.connect('db/block.db') as block_db:
                        await block_db.execute('INSERT OR IGNORE INTO user_blacklist (user_id) VALUES (?)', (message.author.id,))
                        
                        await block_db.commit()

                    embed = discord.Embed(
                        title="You Have Been Blacklisted",
                        description=(
                            "⚠️ You are blacklisted from using my commands due to spamming in the media channel. "
                            "If you believe this is a mistake, please reach out to the support server with proof."
                        ),
                        color=0x000000
                    )
                    await message.channel.send(f"{message.author.mention}", embed=embed)
                    del self.infractions[message.author.id]

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
import aiosqlite
import os
from utils.Tools import *

# Database setup
db_folder = 'db'
db_file = 'anti.db'
db_path = os.path.join(db_folder, db_file)

class Nightmode(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize_db())
        self.ricky = ['1070619070468214824', '1087282349395411015', '858642338980954113']
        self.color = 0x000000  

    async def initialize_db(self):
        self.db = await aiosqlite.connect(db_path)
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS Nightmode (
                guildId TEXT,
                roleId TEXT,
                adminPermissions INTEGER
            )
        ''')
        await self.db.commit()

    async def is_extra_owner(self, user, guild):
        async with self.db.execute('''
            SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?
        ''', (guild.id, user.id)) as cursor:
            extra_owner = await cursor.fetchone()
        return extra_owner is not None

    @commands.hybrid_group(name="nightmode", aliases=[], help="Manages Nightmode feature", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def nightmode(self, ctx):
        nightmode_embed = discord.Embed(
            title='__**Nightmode**__',
            color=self.color,
            description=(
                'Nightmode swiftly disables dangerous permissions for roles, like stripping `ADMINISTRATION` rights, while preserving original settings for seamless restoration.\n\n**Make sure to keep my ROLE above all roles you want to protect.**'
            )
        )
        nightmode_embed.add_field(
            name="Usage",
            value="🔴 `nightmode enable`\n🔴 `nightmode disable`",
            inline=False
        )
        nightmode_embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.send(embed=nightmode_embed)

    @nightmode.command(name="enable", help="Enable nightmode")
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def enable_nightmode(self, ctx):
        if ctx.guild.member_count < 50:  
            return await ctx.send(embed=discord.Embed(title="❌ Access Denied",
                color=self.color,
                description='Your Server Doesn\'t Meet My 50 Member Criteria'
            ))

        own = ctx.author.id == ctx.guild.owner_id
        check = await self.is_extra_owner(ctx.author, ctx.guild)
        if not own and not check and ctx.author.id not in self.ricky:
            return await ctx.send(embed=discord.Embed(title="❌ Access Denied",
                color=self.color,
                description='Only Server Owner Or Extraowner Can Run This Command.!'
            ))

        if not own and not (
            ctx.guild.me.top_role.position <= ctx.author.top_role.position
        ) and ctx.author.id not in self.ricky:
            return await ctx.send(embed=discord.Embed(title="❌ Access Denied",
                color=self.color,
                description='Only Server Owner or Extraowner Having **Higher role than me can run this command**'
            ))

        bot_highest_role = ctx.guild.me.top_role
        manageable_roles = [
            role for role in ctx.guild.roles
            if role.position < bot_highest_role.position 
            and role.name != '@everyone' 
            and role.permissions.administrator
            and not role.managed  
        ]

        if not manageable_roles:
            return await ctx.send(embed=discord.Embed(title="❌  Error",
                color=self.color,
                description='No Roles Found With Admin Permissions'
            ))

        async with self.db.execute('SELECT guildId FROM Nightmode WHERE guildId = ?', (str(ctx.guild.id),)) as cursor:
            if await cursor.fetchone():
                return await ctx.send(embed=discord.Embed(title="❌  Error",
                    color=self.color,
                    description='Nightmode is already enabled.'
                ))

        async with self.db.cursor() as cursor:
            for role in manageable_roles:
                admin_permissions = discord.Permissions(administrator=True)
                if role.permissions.administrator:
                    permissions = role.permissions
                    permissions.administrator = False

                    await role.edit(permissions=permissions, reason='Nightmode ENABLED')

                    await cursor.execute('''
                    INSERT OR REPLACE INTO Nightmode (guildId, roleId, adminPermissions)
                    VALUES (?, ?, ?)
                    ''', (str(ctx.guild.id), str(role.id), int(admin_permissions.value)))
            await self.db.commit()

        await ctx.send(embed=discord.Embed(title="✅ Success",
            color=self.color,
            description='Nightmode enabled! Dangerous Permissions Disabled For Manageable Roles.'
        ))

    @nightmode.command(name="disable", help="Disable nightmode")
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def disable_nightmode(self, ctx):
        if ctx.guild.member_count < 50:  
            return await ctx.send(embed=discord.Embed(title="❌ Access Denied",
                color=self.color,
                description='Your Server Doesn\'t Meet My 50 Member Criteria'
            ))

        own = ctx.author.id == ctx.guild.owner_id
        check = await self.is_extra_owner(ctx.author, ctx.guild)
        if not own and not check and ctx.author.id not in self.ricky:
            return await ctx.send(embed=discord.Embed(title="❌ Access Denied",
                color=self.color,
                description='Only Server Owner Or Extraowner Can Run This Command.!'
            ))

        if not own and not (
            ctx.guild.me.top_role.position <= ctx.author.top_role.position
        ) and ctx.author.id not in self.ricky:
            return await ctx.send(embed=discord.Embed(title="❌ Access Denied",
                color=self.color,
                description='Only Server Owner or Extraowner Having **Higher role than me can run this command**'
            ))

        async with self.db.execute('SELECT roleId, adminPermissions FROM Nightmode WHERE guildId = ?', (str(ctx.guild.id),)) as cursor:
            stored_roles = await cursor.fetchall()

        if not stored_roles:
            return await ctx.send(embed=discord.Embed(title="❌  Error",
                color=self.color,
                description='Nightmode is not enabled.'
            ))

        async with self.db.cursor() as cursor:
            for role_id, admin_permissions in stored_roles:
                role = ctx.guild.get_role(int(role_id))
                if role:
                    permissions = discord.Permissions(administrator=bool(admin_permissions))
                    await role.edit(permissions=permissions, reason='Nightmode DISABLED')

                    await cursor.execute('DELETE FROM Nightmode WHERE guildId = ? AND roleId = ?', (str(ctx.guild.id), role_id))
            await self.db.commit()

        await ctx.send(embed=discord.Embed(title="✅ Success",
            color=self.color,
            description='Nightmode disabled! Restored Permissions For Manageable Roles.'
        ))

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
import aiosqlite
from utils.Tools import *

class NotifCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "db/notify.db"
        self.loop_task = self.bot.loop.create_task(self.setup_db())

    async def setup_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS notifications (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                type TEXT NOT NULL UNIQUE,
                                role_id INTEGER NOT NULL,
                                channel_id INTEGER NOT NULL)''')
            await db.commit()

    @commands.group(invoke_without_command=True)
    async def setnotif(self, ctx):
        embed = discord.Embed(title="Notification Commands", color=0x000000)
        embed.add_field(name="Subcommands", value="twitch, youtube, list, reset")
        await ctx.send(embed=embed)

    @setnotif.command()
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def twitch(self, ctx, role: discord.Role, channel: discord.TextChannel):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM notifications WHERE type = ?', ('twitch',)) as existing:
                row = await existing.fetchone()
                if row:
                    await ctx.reply(embed=discord.Embed(title="🚫 Access Denied", description="Twitch notification already set. Remove it first.", color=0x000000))
                    return

            await db.execute('INSERT INTO notifications (type, role_id, channel_id) VALUES (?, ?, ?)', ('twitch', role.id, channel.id))
            await db.commit()
            await ctx.reply(embed=discord.Embed(title="✅ Success", description=f"Twitch notifications set for {role.mention} in {channel.mention}.", color=0x000000))

    @setnotif.command()
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def youtube(self, ctx, role: discord.Role, channel: discord.TextChannel):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM notifications WHERE type = ?', ('youtube',)) as existing:
                row = await existing.fetchone()
                if row:
                    await ctx.reply(embed=discord.Embed(title="🚫 Access Denied", description="YouTube notification already set. Remove it first.", color=0x000000))
                    return

            await db.execute('INSERT INTO notifications (type, role_id, channel_id) VALUES (?, ?, ?)', ('youtube', role.id, channel.id))
            await db.commit()
            await ctx.reply(embed=discord.Embed(title="✅ Success", description=f"YouTube notifications set for {role.mention} in {channel.mention}.", color=0x000000))

    @setnotif.command()
    async def list(self, ctx):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM notifications') as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    await ctx.reply(embed=discord.Embed(description="No Twitch and YouTube notification channels set.", color=0xFF0000))
                    return

            embed = discord.Embed(title="Current Notification Settings", color=0x000000)
            for row in rows:
                notif_type = row[1].capitalize() 
                role = ctx.guild.get_role(row[2])
                channel = ctx.guild.get_channel(row[3])
                if role and channel:
                    embed.add_field(name=f"{notif_type} Notifications", value=f"Role: {role.mention} | Channel: {channel.mention}", inline=False)
                else:
                    embed.add_field(name=f"{notif_type} Notifications", value="Role or Channel not found", inline=False)

            await ctx.reply(embed=embed)

    @setnotif.command()
    async def reset(self, ctx):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM notifications WHERE type IN (?, ?)', ('twitch', 'youtube'))
            await db.commit()
            await ctx.send(embed=discord.Embed(title="✅ Success", description="Twitch and YouTube notifications have been reset.", color=0x00FF00))


    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        
        streaming = next((activity for activity in after.activities if isinstance(activity, discord.Streaming)), None)

        if streaming:
            stream_type = "twitch" if "twitch" in streaming.url.lower() else "youtube" if "youtube" in streaming.url.lower() else None
            if stream_type:
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute('SELECT role_id, channel_id FROM notifications WHERE type = ?', (stream_type,)) as cursor:
                        row = await cursor.fetchone()
                        if row:
                            role_id, channel_id = row
                            role = after.guild.get_role(role_id)
                            channel = after.guild.get_channel(channel_id)

                            if role and channel:
                                embed = discord.Embed(
                                    title=f"{after.display_name} is now live!",
                                    description=f"{after.mention} is now streaming on {stream_type.capitalize()}.",
                                    color=0x000000
                                )
                                embed.add_field(name="Stream Title", value=streaming.name, inline=False)
                                embed.add_field(name="Watch here", value=streaming.url, inline=False)
                                await channel.send(content=role.mention, embed=embed)

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
from discord.ext import commands, tasks
from discord import *
import discord
import aiosqlite
from typing import Optional
from datetime import datetime, timedelta
from discord.ui import View, Button, Select
from utils.config import OWNER_IDS
from utils import Paginator, DescriptionEmbedPaginator


def load_owner_ids():
    return OWNER_IDS


async def is_staff(user, staff_ids):
    return user.id in staff_ids


async def is_owner_or_staff(ctx):
    return await is_staff(ctx.author, ctx.cog.staff) or ctx.author.id in OWNER_IDS



class TimeSelect(Select):
    def __init__(self, user, db_path, author):
        super().__init__(placeholder="Select the duration")
        self.user = user
        self.db_path = db_path
        self.author = author

        
        self.options = [
            SelectOption(label="10 Minutes", description="Trial for 10 minutes", value="10m"),
            SelectOption(label="1 Week", description="No prefix for 1 week", value="1w"),
            SelectOption(label="3 Weeks", description="No prefix for 3 weeks", value="3w"),
            SelectOption(label="1 Month", description="No prefix for 1 Month", value="1m"),
            SelectOption(label="3 Months", description="No prefix for 3 Months.", value="3m"),
            SelectOption(label="6 Months", description="No prefix for 6 Months.", value="6m"),
            SelectOption(label="1 Year", description="No prefix for 1 Year.", value="1y"),
            SelectOption(label="3 Years", description="No prefix for 3 Years.", value="3y"),
            SelectOption(label="Lifetime", description="No prefix Permanently.", value="lifetime"),
        ]

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return await interaction.response.send_message("You can't select this option.", ephemeral=True)

        
        duration_mapping = {
            "10m": timedelta(minutes=10),
            "1w": timedelta(weeks=1),
            "3w": timedelta(weeks=3),
            "1m": timedelta(days=30),
            "3m": timedelta(days=90),
            "6m": timedelta(days=180),
            "1y": timedelta(days=365),
            "3y": timedelta(days=365 * 3),
            "lifetime": None
        }

        selected_duration = self.values[0]
        expiry_time = None

        if selected_duration != "lifetime":
            expiry_time = datetime.utcnow() + duration_mapping[selected_duration]
            expiry_str = expiry_time.isoformat()
        else:
            expiry_str = None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO np (id, expiry_time) VALUES (?, ?)", (self.user.id, expiry_str))
            await db.commit()

        expiry_text = "**Lifetime**" if selected_duration == "lifetime" else f"{expiry_time.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        expiry_timestamp = "None (Permanent)" if selected_duration == "lifetime" else f"<t:{int(expiry_time.timestamp())}:f>"

        
        guild = interaction.client.get_guild(699587669059174461)
        if guild:
            member = guild.get_member(self.user.id)
            if member:
                role = guild.get_role(1295883122902302771)
                if role:
                    await member.add_roles(role, reason="No prefix added")

            

        log_channel = interaction.client.get_channel(1299513569766805597)
        if log_channel:
            embed = discord.Embed(
                title="User Added to No Prefix",
                description=f"**• User**: [{self.user}](https://discord.com/users/{self.user.id})\n**✅ User Mention**: {self.user.mention}\n**• ID**: {self.user.id}\n\n**🛡️ Added By**: [{self.author.display_name}](https://discord.com/users/{self.author.id})\n• **Expiry Time**: {expiry_text}\n• **Timestamp**: {expiry_timestamp}\n\n• **Tier**: **{self.values[0].upper()}**",
                color=0x000000
            )
            embed.set_thumbnail(url=self.user.avatar.url if self.user.avatar else self.user.default_avatar.url)
            await log_channel.send("<@677952614390038559>, <@213347081799073793>",embed=embed)
            

        
        embed = discord.Embed(description=f"**Added Global No Prefix**:\n• **User**: **[{self.user}](https://discord.com/users/{self.user.id})**\n✅ **User Mention**: {self.user.mention}\n• **User ID**: {self.user.id}\n\n__**Additional Info**__:\n🛡️ **Added By**: **[{self.author.display_name}](https://discord.com/users/{self.author.id})**\n• **Expiry Time:** {expiry_text}\n• **Timestamp:** {expiry_timestamp}", color=0x000000)
        embed.set_author(name="Added No Prefix", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        embed.set_footer(text="DM will be sent to the user in case No prefix is expired.")
        await interaction.response.edit_message(embed=embed, view=None)

class TimeSelectView(View):
    def __init__(self, user, db_path, author):
        super().__init__()
        self.user = user
        self.db_path = db_path
        self.author = author
        self.add_item(TimeSelect(user, db_path, author))



class NoPrefix(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.staff = set()
        self.db_path = 'db/np.db'
        self.client.loop.create_task(self.load_staff())
        self.client.loop.create_task(self.setup_database())
        self.expiry_check.start()

    async def setup_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS np (
                    id INTEGER PRIMARY KEY
                )
            ''')
            

            
            async with db.execute("PRAGMA table_info(np);") as cursor:
                columns = [info[1] for info in await cursor.fetchall()]

            
            if "expiry_time" not in columns:
                await db.execute('''
                    ALTER TABLE np ADD COLUMN expiry_time TEXT NULL;
                ''')

            
            await db.execute('''
                UPDATE np
                SET expiry_time = NULL
                WHERE expiry_time IS NULL;
            ''')
            await db.execute('''
    CREATE TABLE IF NOT EXISTS autonp (
        guild_id INTEGER PRIMARY KEY
    )
    ''')

            await db.commit()


    async def load_staff(self):
        await self.client.wait_until_ready()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT id FROM staff') as cursor:
                self.staff = {row[0] for row in await cursor.fetchall()}

    @tasks.loop(minutes=10)
    async def expiry_check(self):
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.utcnow().isoformat()
            async with db.execute("SELECT id FROM np WHERE expiry_time IS NOT NULL AND expiry_time <= ?", (now,)) as cursor:
                expired_users = [row[0] for row in await cursor.fetchall()]

            if expired_users:
                async with db.execute("DELETE FROM np WHERE id IN ({})".format(",".join("?" * len(expired_users))), expired_users):
                    await db.commit()

                for user_id in expired_users:
                    user = self.client.get_user(user_id)
                    if user:
                        log_channel = self.client.get_channel(1299513624477306974)
                        if log_channel:
                            embed_log = discord.Embed(
                                title="No Prefix Expired",
                                description=(
                                    f"**• User**: [{user}](https://discord.com/users/{user.id})\n"
                                    f"**✅ User Mention**: {user.mention}\n"
                                    f"**• ID**: {user.id}\n\n"
                                    f"**🛡️ Removed By**: **[Tempest#9545](https://discord.com/users/1144179659735572640)**\n"
                                ),
                                color=0x000000
                            )
                            embed_log.set_thumbnail(url=user.display_avatar.url if user.avatar else user.default_avatar.url)
                            embed_log.set_footer(text="No Prefix Removal Log")
                            await log_channel.send("<@677952614390038559>, <@213347081799073793>", embed=embed_log)
                        bot = self.client
                        guild = bot.get_guild(699587669059174461)
                        if guild:
                            member = guild.get_member(user.id)
                            if member:
                                role = guild.get_role(1295883122902302771)
                                if role in member.roles:
                                    await member.remove_roles(role)

                        
                                    
                        embed = discord.Embed(
                            description=f"⚠️ Your No Prefix status has **Expired**. You will now require the prefix to use commands.",
                            color=0x000000
                        )
                        embed.set_author(name="No Prefix Expired", icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
                        
                        embed.set_footer(text="Tempest - No Prefix, Join support to regain access.")
                        support = Button(label='Support',
                    style=discord.ButtonStyle.link,
                    url=f'https://discord.gg/odx')
                        view = View()
                        view.add_item(support)

                        try:
                            await user.send(f"{user.mention}", embed=embed, view=view)
                        except discord.Forbidden:
                            pass
                        except discord.HTTPException:
                            pass

    @expiry_check.before_loop
    async def before_expiry_check(self):
        await self.client.wait_until_ready()

    @commands.group(name="np", help="Allows you to add someone to the no-prefix list (owner-only command)")
    @commands.check(is_owner_or_staff)
    async def _np(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @_np.command(name="list", help="List of no-prefix users")
    @commands.check(is_owner_or_staff)
    async def np_list(self, ctx):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id FROM np") as cursor:
                ids = [row[0] for row in await cursor.fetchall()]
                if not ids:
                    await ctx.reply(f"No users in the no-prefix list.", mention_author=False)
                    return
                entries = [
                    f"`#{no+1}`  [Profile URL](https://discord.com/users/{mem}) (ID: {mem})"
                    for no, mem in enumerate(ids, start=0)
                ]
                embeds = DescriptionEmbedPaginator(
                    entries=entries,
                    title=f"No Prefix Users [{len(ids)}]",
                    description="",
                    per_page=10,
                    color=0x000000).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

    

    @_np.command(name="add", help="Add user to no-prefix with time options")
    @commands.check(is_owner_or_staff)
    async def np_add(self, ctx, user: discord.User):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id FROM np WHERE id = ?", (user.id,)) as cursor:
                result = await cursor.fetchone()
            if result:
                embed = discord.Embed(description=f"**{user}** is Already in No prefix list\n\n🛡️ **Requested By**: [{ctx.author.display_name}](https://discord.com/users/{ctx.author.id})\n", color=0x000000)
                embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
                await ctx.reply(embed=embed)
                return

        view = TimeSelectView(user, self.db_path, ctx.author)
        embed = discord.Embed(title="Select No Prefix Duration", description="**Choose the duration for how long no-prefix should be enabled for this user:**", color=0x000000)
        await ctx.reply(embed=embed, view=view)
        

    @_np.command(name="remove", help="Remove user from no-prefix")
    @commands.check(is_owner_or_staff)
    async def np_remove(self, ctx, user: discord.User):
        async with aiosqlite.connect('db/np.db') as db:
            async with db.execute("SELECT id FROM np WHERE id = ?", (user.id,)) as cursor:
                result = await cursor.fetchone()
            if not result:
                embed = discord.Embed(description=f"**{user}** is Not in the No Prefix list\n\n🛡️ **Requested By**: [{ctx.author.display_name}](https://discord.com/users/{ctx.author.id})\n", color=0x000000)
                embed.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1204106928675102770.png")
                await ctx.reply(embed=embed)
                return

            
            await db.execute("DELETE FROM np WHERE id = ?", (user.id,))
            await db.commit()

        
        guild = ctx.bot.get_guild(699587669059174461)
        if guild:
            member = guild.get_member(user.id)
            if member:
                role = guild.get_role(1295883122902302771)
                if role in member.roles:
                    await member.remove_roles(role)

        
        embed = discord.Embed(
                description=(
                    f"**• User**: [{user}](https://discord.com/users/{user.id})\n"
                    f"**✅ User Mention**: {user.mention}\n"
                    f"**• User ID**: {user.id}\n\n"
                    f"**🛡️ Removed By**: [{ctx.author.display_name}](https://discord.com/users/{ctx.author.id})\n"
                ),
            color=0x000000
        )
        embed.set_author(name="Removed No Prefix", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        await ctx.reply(embed=embed)

        
        log_channel = ctx.bot.get_channel(1299513624477306974)
        if log_channel:
            embed_log = discord.Embed(
                title="No Prefix Removed",
                description=(
                    f"**• User**: [{user}](https://discord.com/users/{user.id})\n"
                    f"**✅ User Mention**: {user.mention}\n"
                    f"**• ID**: {user.id}\n\n"
                    f"**🛡️ Removed By**: [{ctx.author.display_name}](https://discord.com/users/{ctx.author.id})\n"
                ),
                color=0x000000
            )
            embed_log.set_thumbnail(url=user.display_avatar.url if user.avatar else user.default_avatar.url)
            embed_log.set_footer(text="No Prefix Removal Log")
            await log_channel.send("<@677952614390038559>, <@213347081799073793>", embed=embed_log)


    

    @_np.command(name="status", help="Check if a user is in the No Prefix list and show details.")
    @commands.check(is_owner_or_staff)
    async def np_status(self, ctx, user: discord.User):
        async with aiosqlite.connect('db/np.db') as db:
            async with db.execute("SELECT id, expiry_time FROM np WHERE id = ?", (user.id,)) as cursor:
                result = await cursor.fetchone()

            if not result:
                embed = discord.Embed(
                    title="No Prefix Status",
                    description=f"**{user}** is Not in the No Prefix list\n\n"
                                f"🛡️ **Requested By**: "
                                f"[{ctx.author.display_name}](https://discord.com/users/{ctx.author.id})\n",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
                return

            user_id, expires = result

            if expires and expires != "Null": 
                expire_time = datetime.fromisoformat(expires)
                expire_timestamp = f"<t:{int(expire_time.timestamp())}:F>"
            else:
                expire_time = "Lifetime"
                expire_timestamp = "Lifetime"

            embed = discord.Embed(
                title="No Prefix Status",
                description=(
                    f"**• User**: [{user}](https://discord.com/users/{user.id})\n"
                    f"**• User ID**: {user.id}\n\n"
                    f"**• Expiry**: {expire_time} ({expire_timestamp})"
                ),
                color=0x000000
            )

            embed.set_thumbnail(url=user.display_avatar.url if user.avatar else user.default_avatar.url)

        await ctx.reply(embed=embed)


    @commands.group(name="autonp", help="Manage auto no-prefix for partner guilds.")
    @commands.is_owner()
    async def autonp(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @autonp.group(name="guild", help="Manage partner guilds for auto no-prefix.")
    async def autonp_guild(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @autonp_guild.command(name="add", help="Add a guild to auto no-prefix.")
    async def add_guild(self, ctx, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM autonp WHERE guild_id = ?", (guild_id,)) as cursor:
                if await cursor.fetchone():
                    await ctx.reply("Guild is already added.")
                    return
            await db.execute("INSERT INTO autonp (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
        await ctx.reply(f"Guild {guild_id} added to auto no-prefix.")

    @autonp_guild.command(name="remove", help="Remove a guild from auto no-prefix.")
    async def remove_guild(self, ctx, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM autonp WHERE guild_id = ?", (guild_id,)) as cursor:
                if not await cursor.fetchone():
                    await ctx.reply("Guild is not in auto no-prefix.")
                    return
            await db.execute("DELETE FROM autonp WHERE guild_id = ?", (guild_id,))
            await db.commit()
        await ctx.reply(f"Guild {guild_id} removed from auto no-prefix.")

    @autonp_guild.command(name="list", help="List all guilds with auto no-prefix.")
    @commands.check(is_owner_or_staff)
    async def list_guilds(self, ctx):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT guild_id FROM autonp") as cursor:
                guilds = [row[0] for row in await cursor.fetchall()]
                if not guilds:
                    await ctx.reply("No guilds in auto no-prefix.", mention_author=False)
                    return
                await ctx.reply(f"Guilds in auto no-prefix:\n" + "\n".join(str(g) for g in guilds), mention_author=False)


    async def is_user_in_np(self, user_id):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM np WHERE id = ?", (user_id,)) as cursor:
                return await cursor.fetchone() is not None
            



    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.premium_since is None and after.premium_since is not None:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT 1 FROM autonp WHERE guild_id = ?", (after.guild.id,)) as cursor:
                    if not await cursor.fetchone():
                        return
            if not await self.is_user_in_np(after.id):
                await self.add_np(after, timedelta(days=60))
                log_channel = self.client.get_channel(1302312378578243765)
                embed = discord.Embed(
                    title="Added No prefix due to Boosting Partner Server",
                    description=f"**User**: **[{after}](https://discord.com/users/{after.id})** (ID: {after.id})\n**Server**: {after.guild.name}",
                    color=0x00FF00
                )
                message = await log_channel.send("<@677952614390038559>, <@213347081799073793>", embed=embed)
                await message.publish()

        elif before.premium_since is not None and after.premium_since is None:  
            await self.handle_boost_removal(after)

    #@commands.Cog.listener()
    #async def on_member_remove(self, member):
        #await self.handle_boost_removal(member)

    async def handle_boost_removal(self, user):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM autonp WHERE guild_id = ?", (user.guild.id,)) as cursor:
                if not await cursor.fetchone():
                    return
        if await self.is_user_in_np(user.id):
            await self.remove_np(user) 
            log_channel = self.client.get_channel(1302312616735281286)
            embed = discord.Embed(
                title="Removed No prefix due to Unboosting Partner Server",
                description=f"**User**: **[{user}](https://discord.com/users/{user.id})** (ID: {user.id})\n**Server**: {user.guild.name}",
                color=0xFF0000
            )
            message = await log_channel.send("<@677952614390038559>, <@213347081799073793>", embed=embed)
            await message.publish()


    async def add_np(self, user, duration):
        expiry_time = datetime.utcnow() + duration
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO np (id, expiry_time) VALUES (?, ?)", (user.id, expiry_time.isoformat()))
            await db.commit()
            
        embed = discord.Embed(
                            title="• Congratulations you got 2 months No Prefix!",
                            description=f"You've been credited 2 months of global No Prefix for boosting our Partnered Servers. You can now use my commands without prefix. If you wish to remove it, please reach out [Support Server](https://discord.gg/odx).",
                            color=0x000000
                        )
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass



        guild = self.client.get_guild(699587669059174461)
        if guild:
            member = guild.get_member(user.id)
            if member is not None:
                role = guild.get_role(1295883122902302771)
                if role:
                    await member.add_roles(role)


    async def remove_np(self, user):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT expiry_time FROM np WHERE id = ?", (user.id,)) as cursor:
                row = await cursor.fetchone()
                if row is None or row[0] is None:
                    return

            await db.execute("DELETE FROM np WHERE id = ?", (user.id,))
            await db.commit()
            
        embed= discord.Embed(title="⚠️ Global No Prefix Expired",
                        description=f"Hey {user.mention}, your global no prefix has expired!\n\n__**Reason:**__ Unboosting our partnered Server.\nIf you think this is a mistake then please reach out [Support Server](https://discord.gg/odx).",
                        color=0x000000)
            
            
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

        guild = self.client.get_guild(699587669059174461)
        if guild:
            member = guild.get_member(user.id)
            if member is not None: 
                role = guild.get_role(1295883122902302771)
                if role and role in member.roles:
                    await member.remove_roles(role)
from __future__ import annotations
from discord.ext import commands
from discord import *
from PIL import Image, ImageDraw, ImageFont
import discord
import json
import datetime
import asyncio
import aiosqlite
from typing import Optional
from utils import Paginator, DescriptionEmbedPaginator, FieldPagePaginator, TextPaginator
from utils.Tools import *
from utils.config import OWNER_IDS
from core import Cog, Tempest, Context
import sqlite3
import os
import requests
from io import BytesIO
from utils.config import OWNER_IDS
from discord.errors import Forbidden
from discord import Embed
from discord.ui import Button, View




BADGE_URLS = {
    "owner": "https://cdn.discordapp.com/emojis/1228227536207740989.png",
    "staff": "https://cdn.discordapp.com/emojis/1228227884481515613.png",
    "partner": "https://cdn.discordapp.com/emojis/1228228301089144976.png",
    "sponsor": "https://cdn.discordapp.com/emojis/1228246375180013678.png",
    "friend": "https://cdn.discordapp.com/emojis/1228229690376982549.png",
    "early": "https://cdn.discordapp.com/emojis/1228241490246111302.png",
    "vip": "https://cdn.discordapp.com/emojis/1228230884583276584.png",
    "bug": "https://cdn.discordapp.com/emojis/1228231513456382015.png"
}

BADGE_NAMES = {
    "owner": "Owner",
    "staff": "Staff",
    "partner": "Partner",
    "sponsor": "Sponsor",
    "friend": "Owner's Friend",
    "early": "Early Supporter",
    "vip": "VIP",
    "bug": "Bug Hunter"
}


db_folder = 'db'
db_file = 'badges.db'
db_path = os.path.join(db_folder, db_file)
FONT_PATH = os.path.join('utils', 'arial.ttf')


conn = sqlite3.connect(db_path)
c = conn.cursor()


c.execute('''CREATE TABLE IF NOT EXISTS badges (
    user_id INTEGER PRIMARY KEY,
    owner INTEGER DEFAULT 0,
    staff INTEGER DEFAULT 0,
    partner INTEGER DEFAULT 0,
    sponsor INTEGER DEFAULT 0,
    friend INTEGER DEFAULT 0,
    early INTEGER DEFAULT 0,
    vip INTEGER DEFAULT 0,
    bug INTEGER DEFAULT 0
)''')
conn.commit()

def add_badge(user_id, badge):
    c.execute(f"SELECT {badge} FROM badges WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result is None:
        c.execute(f"INSERT INTO badges (user_id, {badge}) VALUES (?, 1)", (user_id,))
    elif result[0] == 0:
        c.execute(f"UPDATE badges SET {badge} = 1 WHERE user_id = ?", (user_id,))
    else:
        return False
    conn.commit()
    return True

def remove_badge(user_id, badge):
    c.execute(f"SELECT {badge} FROM badges WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result and result[0] == 1:
        c.execute(f"UPDATE badges SET {badge} = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    return False


def convert_time_to_seconds(time_str):
    time_units = {
        "h": "hours",
        "d": "days",
        "m": "months"
    }
    num = int(time_str[:-1])
    unit = time_units.get(time_str[-1])
    return datetime.timedelta(**{unit: num})


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
      await ctx.send(f"✅ | Successfully removed {deleted} messages.", delete_after=3)
  else:
      await ctx.send(to_send, delete_after=3)

def load_owner_ids():
    return OWNER_IDS



async def is_staff(user, staff_ids):
    return user.id in staff_ids


async def is_owner_or_staff(ctx):
    return await is_staff(ctx.author, ctx.cog.staff) or ctx.author.id in OWNER_IDS


class Owner(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.staff = set()
        self.np_cache = []
        self.db_path = 'db/np.db'
        self.stop_tour = False
        self.bot_owner_ids = [213347081799073793, 677952614390038559]
        self.client.loop.create_task(self.setup_database())
        self.client.loop.create_task(self.load_staff())
        

    async def setup_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS staff (
                    id INTEGER PRIMARY KEY
                )
            ''')
            await db.commit()

    

    async def load_staff(self):
        await self.client.wait_until_ready()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT id FROM staff') as cursor:
                self.staff = {row[0] for row in await cursor.fetchall()}

    @commands.command(name="staff_add", aliases=["staffadd", "addstaff"], help="Adds a user to the staff list.")
    @commands.is_owner()
    async def staff_add(self, ctx, user: discord.User):
        if user.id in self.staff:
            sonu = discord.Embed(title="🔔 Access Denied", description=f"{user} is already in the staff list.", color=0x000000)
            await ctx.reply(embed=sonu, mention_author=False)
        else:
            self.staff.add(user.id)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('INSERT OR IGNORE INTO staff (id) VALUES (?)', (user.id,))
                await db.commit()
            sonu2 = discord.Embed(title="✅ Success", description=f"Added {user} to the staff list.", color=0x000000)
            await ctx.reply(embed=sonu2, mention_author=False)

    @commands.command(name="staff_remove", aliases=["staffremove", "removestaff"], help="Removes a user from the staff list.")
    @commands.is_owner()
    async def staff_remove(self, ctx, user: discord.User):
        if user.id not in self.staff:
            sonu = discord.Embed(title="🔔 Access Denied", description=f"{user} is not in the staff list.", color=0x000000)
            await ctx.reply(embed=sonu, mention_author=False)
        else:
            self.staff.remove(user.id)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM staff WHERE id = ?', (user.id,))
                await db.commit()
                sonu2 = discord.Embed(title="✅ Success", description=f"Removed {user} from the staff list.", color=0x000000)
            await ctx.reply(embed=sonu2, mention_author=False)

    @commands.command(name="staff_list", aliases=["stafflist", "liststaff", "staffs"], help="Lists all staff members.")
    @commands.is_owner()
    async def staff_list(self, ctx):
        if not self.staff:
            await ctx.send("The staff list is currently empty.")
        else:
            member_list = []
            for staff_id in self.staff:
                member = await self.client.fetch_user(staff_id)
                member_list.append(f"{member.name}#{member.discriminator} (ID: {staff_id})")
            staff_display = "\n".join(member_list)
            sonu = discord.Embed(title="• Olympus Staffs", description=f"\n{staff_display}", color=0x000000)
            await ctx.send(embed=sonu)

    @commands.command(name="slist")
    @commands.check(is_owner_or_staff)
    async def _slist(self, ctx):
        sonuop = sorted(self.client.guilds, key=lambda g: g.member_count, reverse=True)
        entries = [
            f"`#{i}` | [{g.name}](https://discord.com/guilds/{g.id}) - {g.member_count}"
            for i, g in enumerate(sonuop, start=1)
        ]
        embeds = DescriptionEmbedPaginator(
            entries=entries,
            description="",
            title=f"Guild List of Olympus [{len(self.client.guilds)}]",
            color=0x000000,
            per_page=10).get_pages()
        paginator = Paginator(ctx, embeds)
        await paginator.paginate()

    @commands.command(name="mutual", aliases=["mutuals"])
    @commands.is_owner()
    async def mutual_servers(self, ctx: Context, user: discord.User):
        
        if not user:
            await ctx.send("User not found.")
            return
        
        mutual_guilds = [guild for guild in self.client.guilds if user in guild.members]

        if mutual_guilds:
            entries = [
                f"`{no}` | [{guild.name}](https://discord.com/channels/{guild.id}) (ID: {guild.id})"
                for no, guild in enumerate(mutual_guilds, start=1)
            ]
            embeds = DescriptionEmbedPaginator(
                entries=entries,
                title=f"Mutual Guilds with {user.name} [{len(mutual_guilds)}]",
                description="",
                per_page=10,
                color=0x00ff00).get_pages()
            paginator = Paginator(ctx, embeds)
            await paginator.paginate()
        else:
            await ctx.send("No mutual guilds found.")

    @commands.command(name="getinvite", aliases=["gi", "getinvites"], help="Get invites for a guild or channel.")
    @commands.is_owner()
    async def getinvite(self, ctx, guild_id: int = None, channel_id: int = None):
        guild = None
        channel = None

        if guild_id:
            guild = self.client.get_guild(guild_id)
            if not guild:
                await ctx.send("Invalid guild ID.")
                return
            
        elif channel_id:
            channel = self.client.get_channel(channel_id)
            if not channel:
                await ctx.send("Invalid channel ID.")
                return
            guild = channel.guild 

        else:
            await ctx.send("Please provide a guild ID or channel ID.")
            return

        can_create_invites = guild.me.guild_permissions.create_instant_invite if guild else False

        try:
            if guild_id:
                invites = await guild.invites()
                if invites:
                    embed = discord.Embed(
                        title=f"Active Invites for {guild.name}",
                        color=0xff0000
                    )
                    invites_list = [f"{invite.url} - {invite.uses} uses" for invite in invites]
                    embeds = DescriptionEmbedPaginator(
                        entries=invites_list,
                        title=f"Active Invites for {guild.name}",
                        description="",
                        per_page=10,
                        color=0xff0000).get_pages()
                    paginator = Paginator(ctx, embeds)
                    await paginator.paginate()
                elif can_create_invites:
                    
                    channel = guild.system_channel or next(
                        (ch for ch in guild.text_channels if ch.permissions_for(guild.me).create_instant_invite),
                        None
                    )
                    if channel:
                        invite = await channel.create_invite(max_age=604800, max_uses=None, reason="No active invites found, creating a new one.")
                        await ctx.send(f"Created new invite: {invite.url}")
                    else:
                        await ctx.send("No suitable channel found to create an invite.")
                else:
                    await ctx.send("Bot lacks permission to create invites for the guild.")

            
            elif channel_id:
                if channel.permissions_for(guild.me).create_instant_invite:
                    invite = await channel.create_invite(max_age=604800, max_uses=None, reason="Creating invite for the specified channel.")
                    await ctx.send(f"Created new invite for the channel: {invite.url}")
                else:
                    await ctx.send("Bot lacks permission to create invites for the specified channel.")

        except discord.Forbidden:
            await ctx.send("Bot lacks permission to access or create invites.")

    @commands.command(name="getguild")
    @commands.is_owner()
    async def get_guild(self, ctx, channel_id: int):
        channel = self.client.get_channel(channel_id)

        if channel:
            guild = channel.guild
            embed = discord.Embed(
                title=f"Guild Information for {guild.name}",
                color=0x000000
            )
            embed.add_field(name="Guild Name", value=guild.name)
            embed.add_field(name="Guild ID", value=guild.id)
            embed.add_field(name="Member Count", value=guild.member_count)
            embed.add_field(name="Owner", value=guild.owner)
            embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"))
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("Invalid channel ID or bot has no access to the channel.")
            
    @commands.command(name="olympus.restart", help="Restarts the client.")
    @commands.is_owner()
    async def _restart(self, ctx: Context):
        await ctx.reply("Restarting Olympus...")
        restart_program()

    @commands.command(name="sync", help="Syncs all database.")
    @commands.is_owner()
    async def _sync(self, ctx):
        await ctx.reply("Syncing...", mention_author=False)
        with open('events.json', 'r') as f:
            data = json.load(f)
        for guild in self.client.guilds:
            if str(guild.id) not in data['guild']:
                data['guilds'][str(guild.id)] = 'on'
                with open('events.json', 'w') as f:
                    json.dump(data, f, indent=4)
            else:
                pass
        with open('config.json', 'r') as f:
            data = json.load(f)
        for op in data["guilds"]:
            g = self.client.get_guild(int(op))
            if not g:
                data["guilds"].pop(str(op))
                with open('config.json', 'w') as f:
                    json.dump(data, f, indent=4)


    @commands.command(name="owners")
    @commands.is_owner()
    async def own_list(self, ctx):
        nplist = OWNER_IDS
        npl = ([await self.client.fetch_user(nplu) for nplu in nplist])
        npl = sorted(npl, key=lambda nop: nop.created_at)
        entries = [
            f"`#{no}` | [{mem}](https://discord.com/users/{mem.id}) (ID: {mem.id})"
            for no, mem in enumerate(npl, start=1)
        ]
        embeds = DescriptionEmbedPaginator(
            entries=entries,
            title=f"Olympus Owners [{len(nplist)}]",
            description="",
            per_page=10,
            color=0x000000).get_pages()
        paginator = Paginator(ctx, embeds)
        await paginator.paginate()





    @commands.command()
    @commands.is_owner()
    async def dm(self, ctx, user: discord.User, *, message: str):
        """ DM the user of your choice """
        try:
            await user.send(message)
            await ctx.send(f"✅ | Successfully Sent a DM to **{user}**")
        except discord.Forbidden:
            await ctx.send("This user might be having DMs blocked or it's a bot account...")           



    @commands.group()
    @commands.is_owner()
    async def change(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))


    @change.command(name="nickname")
    @commands.is_owner()
    async def change_nickname(self, ctx, *, name: str = None):
        """ Change nickname. """
        try:
            await ctx.guild.me.edit(nick=name)
            if name:
                await ctx.send(f"✅ | Successfully changed nickname to **{name}**")
            else:
                await ctx.send("✅ | Successfully removed nickname")
        except Exception as err:
            await ctx.send(err) 


    @commands.command(name="ownerban", aliases=["forceban", "dna"])
    @commands.is_owner()
    async def _ownerban(self, ctx: Context, user_id: int, *, reason: str = "No reason provided"):
        
        member = ctx.guild.get_member(user_id)
        if member:
            try:
                await member.ban(reason=reason)
                embed = discord.Embed(
                    title="Successfully Banned",
                    description=f"✅ | **{member.name}** has been successfully banned from {ctx.guild.name} by the Bot Owner.",
                    color=0x000000)
                await ctx.reply(embed=embed, mention_author=False, delete_after=3)
                await ctx.message.delete()
            except discord.Forbidden:
                embed = discord.Embed(
                    title="Error!",
                    description=f"🔔 I do not have permission to ban **{member.name}** in this guild.",
                    color=0x000000
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=5)
                await ctx.message.delete()
            except discord.HTTPException:
                embed = discord.Embed(
                    title="Error!",
                    description=f"🔔 An error occurred while banning **{member.name}**.",
                    color=0x000000
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=5)
                await ctx.message.delete()
        else:
            await ctx.reply("User not found in this guild.", mention_author=False, delete_after=3)
            await ctx.message.delete()

    @commands.command(name="ownerunban", aliases=["forceunban"])
    @commands.is_owner()
    async def _ownerunban(self, ctx: Context, user_id: int, *, reason: str = "No reason provided"):
        user = self.client.get_user(user_id)
        if user:
            try:
                await ctx.guild.unban(user, reason=reason)
                embed = discord.Embed(
                    title="Successfully Unbanned",
                    description=f"✅ | **{user.name}** has been successfully unbanned from {ctx.guild.name} by the Bot Owner.",
                    color=0x000000
                )
                await ctx.reply(embed=embed, mention_author=False)
            except discord.Forbidden:
                embed = discord.Embed(
                    title="Error!",
                    description=f"🔔 I do not have permission to unban **{user.name}** in this guild.",
                    color=0x000000
                )
                await ctx.reply(embed=embed, mention_author=False)
            except discord.HTTPException:
                embed = discord.Embed(
                    title="Error!",
                    description=f"🔔 An error occurred while unbanning **{user.name}**.",
                    color=0x000000
                )
                await ctx.reply(embed=embed, mention_author=False)
        else:
            await ctx.reply("User not found.", mention_author=False)



    @commands.command(name="globalunban")
    @commands.is_owner()
    async def globalunban(self, ctx: Context, user: discord.User):
        success_guilds = []
        error_guilds = []

        for guild in self.client.guilds:
            bans = await guild.bans()
            if any(ban_entry.user.id == user.id for ban_entry in bans):
                try:
                    await guild.unban(user, reason="Global Unban")
                    success_guilds.append(guild.name)
                except discord.HTTPException:
                    error_guilds.append(guild.name)
                except discord.Forbidden:
                    error_guilds.append(guild.name)

        user_mention = f"{user.mention} (**{user.name}**)"

        success_message = f"Successfully unbanned {user_mention} from the following guild(s):\n{',     '.join(success_guilds)}" if success_guilds else "No guilds where the user was successfully unbanned."
        error_message = f"Failed to unban {user_mention} from the following guild(s):\n{',    '.join(error_guilds)}" if error_guilds else "No errors during unbanning."

        await ctx.reply(f"{success_message}\n{error_message}", mention_author=False)

    @commands.command(name="guildban")
    @commands.is_owner()
    async def guildban(self, ctx: Context, guild_id: int, user_id: int, *, reason: str = "No reason provided"):
        guild = self.client.get_guild(guild_id)
        if not guild:
            await ctx.reply("Bot is not present in the specified guild.", mention_author=False)
            return

        member = guild.get_member(user_id)
        if member:
            try:
                await guild.ban(member, reason=reason)
                await ctx.reply(f"Successfully banned **{member.name}** from {guild.name}.", mention_author=False)
            except discord.Forbidden:
                await ctx.reply(f"Missing permissions to ban **{member.name}** in {guild.name}.", mention_author=False)
            except discord.HTTPException as e:
                await ctx.reply(f"An error occurred while banning **{member.name}** in {guild.name}: {str(e)}", mention_author=False)
        else:
            await ctx.reply(f"User not found in the specified guild {guild.name}.", mention_author=False)

    @commands.command(name="guildunban")
    @commands.is_owner()
    async def guildunban(self, ctx: Context, guild_id: int, user_id: int, *, reason: str = "No reason provided"):
        guild = self.client.get_guild(guild_id)
        if not guild:
            await ctx.reply("Bot is not present in the specified guild.", mention_author=False)
            return
        #member = guild.get_member(user_id)

        try:
            user = await self.client.fetch_user(user_id)
        except discord.NotFound:
            await ctx.reply(f"User with ID {user_id} not found.", mention_author=False)
            return

        user = discord.Object(id=user_id)
        try:
            await guild.unban(user, reason=reason)
            await ctx.reply(f"Successfully unbanned user ID {user_id} from {guild.name}.", mention_author=False)
        except discord.Forbidden:
            await ctx.reply(f"Missing permissions to unban user ID {user_id} in {guild.name}.", mention_author=False)
        except discord.HTTPException as e:
            await ctx.reply(f"An error occurred while unbanning user ID {user_id} in {guild.name}: {str(e)}", mention_author=False)


    @commands.command(name="leaveguild")
    @commands.is_owner()
    async def leave_guild(self, ctx, guild_id: int):
        guild = self.client.get_guild(guild_id)
        if guild is None:
            await ctx.send(f"Guild with ID {guild_id} not found.")
            return

        await guild.leave()
        await ctx.send(f"Left the guild: {guild.name} ({guild.id})")

    @commands.command(name="guildinfo")
    @commands.check(is_owner_or_staff)
    async def guild_info(self, ctx, guild_id: int):
        guild = self.client.get_guild(guild_id)
        if guild is None:
            await ctx.send(f"Guild with ID {guild_id} not found.")
            return

        embed = discord.Embed(
            title=guild.name,
            description=f"Information for guild ID {guild.id}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Owner", value=str(guild.owner), inline=True)
        embed.add_field(name="Member Count", value=str(guild.member_count), inline=True)
        embed.add_field(name="Text Channels", value=len(guild.text_channels), inline=True)
        embed.add_field(name="Voice Channels", value=len(guild.voice_channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        if guild.icon is not None:
                embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"Created at: {guild.created_at}")

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def servertour(self, ctx, time_in_seconds: int, member: discord.Member):
        guild = ctx.guild

        if time_in_seconds > 3600:
            await ctx.send("Time cannot be greater than 3600 seconds (1 hour).")
            return

        if not member.voice:
            await ctx.send(f"{member.display_name} is not in a voice channel.")
            return

        voice_channels = [ch for ch in guild.voice_channels if ch.permissions_for(guild.me).move_members]

        if len(voice_channels) < 2:
            await ctx.send("Not enough voice channels to move the user.")
            return

        self.stop_tour = False

        class StopButton(discord.ui.View):
            def __init__(self, outer_self):
                super().__init__(timeout=time_in_seconds)
                self.outer_self = outer_self

            @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
            async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id not in self.outer_self.bot_owner_ids:
                    await interaction.response.send_message("Only the bot owner can stop this process.", ephemeral=True)
                    return
                self.outer_self.stop_tour = True
                await interaction.response.send_message("Server tour has been stopped.", ephemeral=True)
                self.stop()

        view = StopButton(self)
        message = await ctx.send(f"Started moving {member.display_name} for {time_in_seconds} seconds. Click the button to stop.", view=view)

        end_time = asyncio.get_event_loop().time() + time_in_seconds

        while asyncio.get_event_loop().time() < end_time and not self.stop_tour:
            for ch in voice_channels:
                if self.stop_tour:
                    await ctx.send("Tour stopped.")
                    return
                if not member.voice:
                    await ctx.send(f"{member.display_name} left the voice channel.")
                    return
                try:
                    await member.move_to(ch)
                    await asyncio.sleep(1)
                except Forbidden:
                    await ctx.send(f"Missing permissions to move {member.display_name}.")
                    return
                except Exception as e:
                    await ctx.send(f"Error: {str(e)}")
                    return

        if not self.stop_tour:
            await message.edit(content=f"Finished moving {member.display_name} after {time_in_seconds} seconds.", view=None)




    


    @commands.group()
    @commands.check(is_owner_or_staff)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def bdg(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(description='Invalid `bdg` command passed. Use `add` or `remove`.', color=0x000000)
            await ctx.send(embed=embed)

    @bdg.command()
    @commands.check(is_owner_or_staff)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def add(self, ctx, member: discord.Member, badge: str):
        badge = badge.lower()
        user_id = member.id
        if badge in BADGE_URLS or badge == 'bug' or badge == 'all':
            if badge == 'all':
                for b in BADGE_URLS.keys():
                    add_badge(user_id, b)
                add_badge(user_id, 'bug')
                embed = discord.Embed(description=f"All badges added to {member.mention}.", color=0x000000)
                await ctx.send(embed=embed)
            else:
                success = add_badge(user_id, badge)
                if success:
                    embed = discord.Embed(description=f"Badge `{badge}` added to {member.mention}.", color=0x000000)
                else:
                    embed = discord.Embed(description=f"{member.mention} already has the badge `{badge}`.", color=0x000000)
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description=f"Invalid badge: `{badge}`", color=0x000000)
            await ctx.send(embed=embed)

    @bdg.command()
    @commands.check(is_owner_or_staff)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def remove(self, ctx, member: discord.Member, badge: str):
        badge = badge.lower()
        user_id = member.id
        if badge in BADGE_URLS or badge == 'bug' or badge == 'all':
            if badge == 'all':
                for b in BADGE_URLS.keys():
                    remove_badge(user_id, b)
                remove_badge(user_id, 'bug')
                embed = discord.Embed(description=f"All badges removed from {member.mention}.", color=0x000000)
                await ctx.send(embed=embed)
            else:
                success = remove_badge(user_id, badge)
                if success:
                    embed = discord.Embed(description=f"Badge `{badge}` removed from {member.mention}.", color=0x000000)
                else:
                    embed = discord.Embed(description=f"{member.mention} does not have the badge `{badge}`.", color=0x000000)
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description=f"Invalid badge: `{badge}`", color=0x000000)
            await ctx.send(embed=embed)


    @commands.command(name="forcepurgebots",
        aliases=["fpb"],
        help="Clear recently bot messages in channel (Bot owner only)")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.is_owner()
    @commands.bot_has_permissions(manage_messages=True)
    async def _purgebot(self, ctx, prefix=None, search=100):
        
        await ctx.message.delete()
        
        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix))
        
        await do_removal(ctx, search, predicate)


    @commands.command(name="forcepurgeuser",
        aliases=["fpu"],
        help="Clear recent messages of a user in channel (Bot owner only)")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.is_owner()
    @commands.bot_has_permissions(manage_messages=True)
    async def purguser(self, ctx, member: discord.Member, search=100):
        
        await ctx.message.delete()
        
        await do_removal(ctx, search, lambda e: e.author == member)


    @commands.command(name="owner.help", aliases=['ownerhelp', 'owner-help'], hidden=True)
    @commands.is_owner()
    async def _owner_help(self, ctx):
        
        embed = Embed(title="Owner Commands",
                      description="`staffadd` ,   `staffremove` ,   `stafflist` , `slist` ,   `getinvite <guild-id>` ,   `getguild <channel-id>` ,   `mutual <user>` ,   `guildban <guild_id> <user_id>` ,   `guildunban <guild_id> <user_id>` ,   `olympus.restart` ,   `servertour` ,   `forcepurgebots` , `forcepurgeuser` ,   `ownerban` , `bdg add <user> <badge>` ,   `bdg remove <user> <badge>` ,   `global <subcommand>` ,   `np <subcommand>` ,   `autonp <subcommand>`",
                      color=0x000000)
        await ctx.send(embed=embed)


class Badges(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'db/np.db'

        
    @commands.hybrid_command(aliases=['profile', 'pr'])
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def badges(self, ctx, member: discord.Member = None):

        processing_message = await ctx.send("⌛ Loading your profile...")

        member = member or ctx.author
        user_id = member.id

        
        c.execute("SELECT * FROM badges WHERE user_id = ?", (user_id,))
        badges = c.fetchone()

        if badges:
            badges = dict(zip([column[0] for column in c.description], badges))
        else:
            badges = {k: 0 for k in BADGE_URLS.keys()}

        
        badge_size = 120
        padding = 80
        num_columns = 4
        image_width = 960
        image_height = 540



        def calculate_text_dimensions(badge_name, font, padding=1):
            text_bbox = draw.textbbox((0, 0), badge_name, font=font)
            text_width = (text_bbox[2] - text_bbox[0]) + 2 * padding
            text_height = (text_bbox[3] - text_bbox[1]) + 2 * padding
            return text_width, text_height

        
        def draw_badges(badges, draw, img):

            
            upper_y = (image_height // 4) - (badge_size // 2)
            lower_y = (3 * image_height // 4) - (badge_size // 2)
            
            x_positions = [padding + i * ((image_width - 2 * padding) // (num_columns - 1)) for i in range(num_columns)]

            badge_positions = []
            for badge in BADGE_URLS.keys():
                if badges[badge]:
                    badge_positions.append(badge)

            for i, badge in enumerate(badge_positions):
                y = upper_y if i < num_columns else lower_y
                x = x_positions[i % num_columns]
                response = requests.get(BADGE_URLS[badge])
                badge_img = Image.open(BytesIO(response.content)).resize((badge_size, badge_size))
                img.paste(badge_img, (x - badge_size // 2, y), badge_img)
                text_width, text_height = calculate_text_dimensions(BADGE_NAMES[badge], font)
                draw.text((x - text_width // 2, y + badge_size + 5), BADGE_NAMES[badge], fill=(255, 0, 0), font=font)  

        
        has_badges = any(value == 1 for value in badges.values())

        if has_badges:
            
            img = Image.new('RGBA', (image_width, image_height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype(FONT_PATH, 25)  

            
            draw_badges(badges, draw, img)

            with BytesIO() as image_binary:
                img.save(image_binary, 'PNG')
                image_binary.seek(0)
                file = discord.File(fp=image_binary, filename='badge.png')

            embed = discord.Embed(title=f"{member.display_name}'s Profile", color=0x000000)

            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed.set_thumbnail(url=member.default_avatar.url)
            embed.add_field(name="__**Account Created At**__", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=True)
            embed.add_field(name="__**Joined This Guild At**__", value=f"<t:{int(member.joined_at.timestamp())}:F>", inline=True)



            # User Badges
            user_flags = member.public_flags
            user_badges = []

            badge_mapping = {
              "staff": "• Discord Employee",
              "partner": "• Partnered Server Owner",
              "discord_certified_moderator": "🛡️ Moderator Programs Alumni",
              "hypesquad_balance": "• House Balance Member",
              "hypesquad_bravery": "• House Bravery Member",
              "hypesquad_brilliance": "• House Brilliance Member",
              "hypesquad": "• HypeSquad Events Member",
              "early_supporter": "• Early Supporter",
              "bug_hunter": "• Bug Hunter Level 1",
              "bug_hunter_level_2": "• Bug Hunter Level 2",
              "verified_bot": "• Verified Bot",
              "verified_bot_developer": "• Verified Bot Developer",
              "active_developer": "• Active Developer",
              "early_verified_bot_developer": "• Early Verified Bot Developer",
              "system": "• System User",
              "team_user": "👷 User is a [Team](https://discord.com/developers/docs/topics/teams)",
              "spammer": "• Marked as Spammer",
              "bot_http_interactions": "✅ Bot uses only [HTTP interactions](https://discord.com/developers/docs/interactions/receiving-and-responding#receiving-an-interaction) and is shown in the online member list."
            }

            for flag, value in badge_mapping.items():
              if getattr(user_flags, flag):
                user_badges.append(value)

            
            user = await self.bot.fetch_user(member.id)
            wtf = bool(user.avatar and user.avatar.is_animated())
            omg = bool(user.banner)
            if not member.bot:
                if omg or wtf:
                    user_badges.append("• Nitro Subscriber")
                for guild in self.bot.guilds:
                    if member in guild.members:
                        if guild.premium_subscription_count > 0 and member in guild.premium_subscribers:
                            user_badges.append("• Server Booster Badge")
                            
            if user_badges:
              embed.add_field(name="__**User Badges**__", value="\n".join(user_badges), inline=False)
            else:
              embed.add_field(name="__**User Badges**__", value="None", inline=False)

            # Bot Badges
            embed.add_field(name="__**Bot Badges**__", value="Below", inline=False)
            embed.set_image(url="attachment://badge.png")
            embed.set_footer(text=f"Requested by {ctx.author} | Nitro badge if banner/animated avatar; Booster badge if boosting a mutual guild with bot.", icon_url=ctx.author.avatar.url
                               if ctx.author.avatar else ctx.author.default_avatar.url)

            await ctx.send(embed=embed, file=file)
            await processing_message.delete()
        else:
            embed = discord.Embed(title=f"{member.display_name}'s Profile", color=0x000000)

            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed.set_thumbnail(url=member.default_avatar.url)
            embed.add_field(name="__**Account Created At**__", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=True)
            embed.add_field(name="__**Joined This Guild At**__", value=f"<t:{int(member.joined_at.timestamp())}:F>", inline=True)




            # User Badges
            user_flags = member.public_flags
            user_badges = []

            badge_mapping = {
              "staff": "• Discord Employee",
              "partner": "• Partnered Server Owner",
              "discord_certified_moderator": "🛡️ Moderator Programs Alumni",
              "hypesquad_balance": "• House Balance Member",
              "hypesquad_bravery": "• House Bravery Member",
              "hypesquad_brilliance": "• House Brilliance Member",
              "hypesquad": "• HypeSquad Events Member",
              "early_supporter": "• Early Supporter",
              "bug_hunter": "• Bug Hunter Level 1",
              "bug_hunter_level_2": "• Bug Hunter Level 2",
              "verified_bot": "• Verified Bot",
              "verified_bot_developer": "• Verified Bot Developer",
              "active_developer": "• Active Developer",
              "early_verified_bot_developer": "• Early Verified Bot Developer",
              "system": "• System User",
              "team_user": "👷 User is a [Team](https://discord.com/developers/docs/topics/teams)",
              "spammer": "• Marked as Spammer",
              "bot_http_interactions": "✅ Bot uses only [HTTP interactions](https://discord.com/developers/docs/interactions/receiving-and-responding#receiving-an-interaction) and is shown in the online member list."
            }

            for flag, value in badge_mapping.items():
              if getattr(user_flags, flag):
                user_badges.append(value)

            user = await self.bot.fetch_user(member.id)
            wtf = bool(user.avatar and user.avatar.is_animated())
            omg = bool(user.banner)
            if not member.bot:
                if omg or wtf:
                    user_badges.append("• Nitro Subscriber")
                for guild in self.bot.guilds:
                    if member in guild.members:
                        if guild.premium_subscription_count > 0 and member in guild.premium_subscribers:
                            user_badges.append("• Server Booster Badge")

            if user_badges:
              embed.add_field(name="__**User Badges**__", value="\n".join(user_badges), inline=False)
            else:
              embed.add_field(name="__**User Badges**__", value="None", inline=False)

            # Bot Badges
            embed.add_field(name="__**Bot Badges**__", value="No bot badges", inline=False)
            embed.set_footer(text=f"Requested by {ctx.author} | Nitro badge if banner/animated avatar; Booster badge if boosting a mutual guild with bot.", icon_url=ctx.author.avatar.url
                               if ctx.author.avatar else ctx.author.default_avatar.url)

            await ctx.send(embed=embed)
            await processing_message.delete()
import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import Member
from utils import Paginator, DescriptionEmbedPaginator
from datetime import timedelta
import asyncio

class Global(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.local_frozen_nicks = {}  
        self.client.frozen_nicknames = {}

    @commands.group(name="global", invoke_without_command=True)
    @commands.is_owner()
    async def global_command(self, ctx: commands.Context):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @commands.command(name="globalban",help="Bans the user from all mutual guilds.")
    @commands.is_owner()
    async def global_ban(self, ctx: commands.Context, user: discord.User, reason: str = "Severe violations of Discord's terms of service."):
        mutual_guilds = [guild for guild in self.client.guilds if guild.get_member(user.id)]
        mutual_count = len(mutual_guilds)

        confirm_embed = discord.Embed(
            title=f"Are you sure to Ban {user.display_name} Globally?",
            description=f"The user is in **{mutual_count}** mutual guilds with the bot.\n\nGlobal Ban Requestor: {ctx.author.mention}",
            color=0x000000
        )
        yes_button = Button(label="Yes", style=discord.ButtonStyle.green)
        no_button = Button(label="No", style=discord.ButtonStyle.red)
        view = View()
        view.add_item(yes_button)
        view.add_item(no_button)

        async def confirm(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            view.clear_items()
            await interaction.response.edit_message(view=view)
            await ctx.send(f"Processing global ban for {user.name}...")
            success, failure = [], []
            for guild in mutual_guilds:
                try:
                    await guild.ban(user, reason=reason)
                    success.append(guild.name)
                except:
                    failure.append(guild.name)
            embed = discord.Embed(
                title="Success",
                description=f"Banned the user in {len(success)} of {mutual_count} mutual guilds.",
                color=0x000000
            )
            embed.add_field(name="Success Count", value=f"{len(success)} Guilds")
            embed.add_field(name="Failure Count", value=f"{len(failure)} Guilds")
            success_button = Button(label="List Successful", style=discord.ButtonStyle.green)
            failure_button = Button(label="List Unsuccessful", style=discord.ButtonStyle.red)
            new_view = View()
            new_view.add_item(success_button)
            new_view.add_item(failure_button)

            async def list_success(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(success)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Successful Bans [{len(success)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            async def list_failure(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(failure)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Unsuccessful Bans [{len(failure)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            success_button.callback = list_success
            failure_button.callback = list_failure
            await ctx.send(embed=embed, view=new_view)

        async def cancel(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            await interaction.message.delete()

        yes_button.callback = confirm
        no_button.callback = cancel
        await ctx.send(embed=confirm_embed, view=view)

    @global_command.command(name="kick", help="Kicks the user from all mutual guilds.")
    @commands.is_owner()
    async def global_kick(self, ctx: commands.Context, user: discord.User, reason: str = "Severe violations of Discord's terms of service."):
        mutual_guilds = [guild for guild in self.client.guilds if guild.get_member(user.id)]
        mutual_count = len(mutual_guilds)

        confirm_embed = discord.Embed(
            title=f"Are you sure to Kick {user.display_name} Globally?",
            description=f"The user is in **{mutual_count}** mutual guilds with the bot.\n\nGlobal Kick Requestor: {ctx.author.mention}",
            color=0x000000
        )
        yes_button = Button(label="Yes", style=discord.ButtonStyle.green)
        no_button = Button(label="No", style=discord.ButtonStyle.red)
        view = View()
        view.add_item(yes_button)
        view.add_item(no_button)

        async def confirm(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            view.clear_items()
            await interaction.response.edit_message(view=view)
            await ctx.send(f"Processing global kick for {user.name}...")
            success, failure = [], []
            for guild in mutual_guilds:
                try:
                    await guild.kick(user, reason=reason)
                    success.append(guild.name)
                except:
                    failure.append(guild.name)
            embed = discord.Embed(
                title="Success",
                description=f"Kicked the user in {len(success)} of {mutual_count} mutual guilds.",
                color=0x000000
            )
            embed.add_field(name="Success Count", value=f"{len(success)} Guilds")
            embed.add_field(name="Failure Count", value=f"{len(failure)} Guilds")
            success_button = Button(label="List Successful", style=discord.ButtonStyle.green)
            failure_button = Button(label="List Unsuccessful", style=discord.ButtonStyle.red)
            new_view = View()
            new_view.add_item(success_button)
            new_view.add_item(failure_button)

            async def list_success(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(success)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Successful Kicks [{len(success)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            async def list_failure(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(failure)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Unsuccessful Kicks [{len(failure)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            success_button.callback = list_success
            failure_button.callback = list_failure
            await ctx.send(embed=embed, view=new_view)

        async def cancel(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            await interaction.message.delete()

        yes_button.callback = confirm
        no_button.callback = cancel
        await ctx.send(embed=confirm_embed, view=view)

    @global_command.command(name="timeout", help="Timeouts the user for 28 days in all mutual guilds.")
    @commands.is_owner()
    async def global_timeout(self, ctx: commands.Context, user: discord.User, reason: str = "Severe violations of Discord's terms of service."):
        mutual_guilds = [guild for guild in self.client.guilds if guild.get_member(user.id)]
        mutual_count = len(mutual_guilds)

        confirm_embed = discord.Embed(
            title=f"Are you sure  to Timeout {user.display_name} Globally for 28 days?",
            description=f"The user is in **{mutual_count}** mutual guilds with the bot.\n\nGlobal Timeout Requestor: {ctx.author.mention}",
            color=0x000000
        )
        yes_button = Button(label="Yes", style=discord.ButtonStyle.green)
        no_button = Button(label="No", style=discord.ButtonStyle.red)
        view = View()
        view.add_item(yes_button)
        view.add_item(no_button)

        async def confirm(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            view.clear_items()
            await interaction.response.edit_message(view=view)
            await ctx.send(f"Processing global timeout for {user.name}...")
            success, failure = [], []
            
            for guild in mutual_guilds:
                member = guild.get_member(user.id)
                time_delta =  (timedelta(days=28))
                if member:
                    try:
                        await member.edit(timed_out_until=discord.utils.utcnow() + time_delta, reason=reason)
                        success.append(guild.name)
                    except:
                        failure.append(guild.name)
            embed = discord.Embed(
                title="Success",
                description=f"Timed out the user in {len(success)} of {mutual_count} mutual guilds.",
                color=0x000000
            )
            embed.add_field(name="Success Count", value=f"{len(success)} Guilds")
            embed.add_field(name="Failure Count", value=f"{len(failure)} Guilds")
            success_button = Button(label="List Successful", style=discord.ButtonStyle.green)
            failure_button = Button(label="List Unsuccessful", style=discord.ButtonStyle.red)
            new_view = View()
            new_view.add_item(success_button)
            new_view.add_item(failure_button)

            async def list_success(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(success)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Successful Timeouts [{len(success)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            async def list_failure(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(failure)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Unsuccessful Timeouts [{len(failure)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            success_button.callback = list_success
            failure_button.callback = list_failure
            await ctx.send(embed=embed, view=new_view)

        async def cancel(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            await interaction.message.delete()

        yes_button.callback = confirm
        no_button.callback = cancel
        await ctx.send(embed=confirm_embed, view=view)


    @global_command.command(name="nick", help="Changes the nickname of a user in all mutual guilds.")
    @commands.is_owner()
    async def global_nick(self, ctx: commands.Context, user: discord.User, *, name: str):
        if len(name) > 32:
            return await ctx.send("Nickname cannot exceed 32 characters. Please provide a shorter nickname.")

        mutual_guilds = [guild for guild in self.client.guilds if guild.get_member(user.id)]
        mutual_count = len(mutual_guilds)

        confirm_embed = discord.Embed(
            title=f"Are you sure to Change {user.display_name}'s Nickname Globally?",
            description=f"The user is in **{mutual_count}** mutual guilds with the bot.\n\nGlobal Nick Requestor: {ctx.author.mention}",
            color=0x000000
        )
        yes_button = Button(label="Yes", style=discord.ButtonStyle.green)
        no_button = Button(label="No", style=discord.ButtonStyle.red)
        view = View()
        view.add_item(yes_button)
        view.add_item(no_button)

        async def confirm(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            view.clear_items()
            await interaction.response.edit_message(view=view)
            await ctx.send(f"Processing global nickname change for {user.name}...")
            success, failure = [], []
            for guild in mutual_guilds:
                try:
                    member = guild.get_member(user.id)
                    if member:
                        await member.edit(nick=name)
                        success.append(guild.name)
                except:
                    failure.append(guild.name)
            embed = discord.Embed(
                title="Success",
                description=f"Set the nickname for {user.name} in {len(success)} of {mutual_count} mutual guilds.",
                color=0x000000
            )
            embed.add_field(name="Success Count", value=f"{len(success)} Guilds")
            embed.add_field(name="Failure Count", value=f"{len(failure)} Guilds")
            success_button = Button(label="List Successful", style=discord.ButtonStyle.green)
            failure_button = Button(label="List Unsuccessful", style=discord.ButtonStyle.red)
            new_view = View()
            new_view.add_item(success_button)
            new_view.add_item(failure_button)

            async def list_success(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(success)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Successful Nickname Change [{len(success)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            async def list_failure(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(failure)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Unsuccessful Nickname Change [{len(failure)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            success_button.callback = list_success
            failure_button.callback = list_failure
            await ctx.send(embed=embed, view=new_view)

        async def cancel(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            await interaction.message.delete()

        yes_button.callback = confirm
        no_button.callback = cancel
        await ctx.send(embed=confirm_embed, view=view)


    @global_command.command(name="clearnick", help="Clears the nickname of a user in all mutual guilds.")
    @commands.is_owner()
    async def global_clearnick(self, ctx: commands.Context, user: discord.User):
        mutual_guilds = [guild for guild in self.client.guilds if guild.get_member(user.id)]
        mutual_count = len(mutual_guilds)

        confirm_embed = discord.Embed(
            title=f"Are you sure to Clear {user.display_name}'s Nickname Globally?",
            description=f"The user is in **{mutual_count}** mutual guilds with the bot.\n\nGlobal Clearnick Requestor: {ctx.author.mention}",
            color=0x000000
        )
        yes_button = Button(label="Yes", style=discord.ButtonStyle.green)
        no_button = Button(label="No", style=discord.ButtonStyle.red)
        view = View()
        view.add_item(yes_button)
        view.add_item(no_button)

        async def confirm(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            view.clear_items()
            await interaction.response.edit_message(view=view)
            await ctx.send(f"Processing global nickname clear for {user.name}...")
            success, failure = [], []
            for guild in mutual_guilds:
                try:
                    member = guild.get_member(user.id)
                    if member:
                        await member.edit(nick=None)
                        success.append(guild.name)
                except:
                    failure.append(guild.name)
            embed = discord.Embed(
                title="Success",
                description=f"Cleared the nickname for {user.name} in {len(success)} of {mutual_count} mutual guilds.",
                color=0x000000
            )
            embed.add_field(name="Success Count", value=f"{len(success)} Guilds")
            embed.add_field(name="Failure Count", value=f"{len(failure)} Guilds")
            success_button = Button(label="List Successful", style=discord.ButtonStyle.green)
            failure_button = Button(label="List Unsuccessful", style=discord.ButtonStyle.red)
            new_view = View()
            new_view.add_item(success_button)
            new_view.add_item(failure_button)

            async def list_success(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(success)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Successful Nickname Clear [{len(success)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            async def list_failure(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(failure)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Unsuccessful Nickname Clear [{len(failure)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            success_button.callback = list_success
            failure_button.callback = list_failure
            await ctx.send(embed=embed, view=new_view)

        async def cancel(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            await interaction.message.delete()

        yes_button.callback = confirm
        no_button.callback = cancel
        await ctx.send(embed=confirm_embed, view=view)


    @global_command.command(name="freezenick", help="Freezes a user's nickname in all mutual guilds.")
    @commands.is_owner()
    async def global_freezenick(self, ctx: commands.Context, user: discord.User, *, name: str):
        if len(name) > 32:
            return await ctx.send("Nickname cannot exceed 32 characters. Please provide a shorter nickname.")

        if not hasattr(self.client, "frozen_nicknames"):
            self.client.frozen_nicknames = {}

        mutual_guilds = [guild for guild in self.client.guilds if guild.get_member(user.id)]
        mutual_count = len(mutual_guilds)

        confirm_embed = discord.Embed(
            title=f"Are you sure to Freeze {user.display_name}'s Nickname Globally?",
            description=f"The user is in {mutual_count} mutual guilds with the bot.\n\nGlobal Freezenick Requestor: {ctx.author.mention}",
            color=0x000000
        )
        yes_button = Button(label="Yes", style=discord.ButtonStyle.green)
        no_button = Button(label="No", style=discord.ButtonStyle.red)
        view = View()
        view.add_item(yes_button)
        view.add_item(no_button)

        async def confirm(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            view.clear_items()
            await interaction.response.edit_message(view=None)

            self.client.frozen_nicknames[user.id] = {
                "name": name,
                "guild_ids": [guild.id for guild in mutual_guilds],
            }

            success, failure = [], []
            for guild in mutual_guilds:
                try:
                    member = guild.get_member(user.id)
                    if member:
                        await member.edit(nick=name)
                        success.append(guild.name)
                except:
                    failure.append(guild.name)

            embed = discord.Embed(
                title="Results",
                description=f"Frozen nickname for {user.name} in {len(success)} of {mutual_count} mutual guilds.",
                color=0x000000
            )
            embed.add_field(name="Success Count", value=f"{len(success)} Guilds")
            embed.add_field(name="Failure Count", value=f"{len(failure)} Guilds")

            success_button = Button(label="List Successful", style=discord.ButtonStyle.green)
            failure_button = Button(label="List Unsuccessful", style=discord.ButtonStyle.red)
            stop_button = Button(label="Stop Freezing", style=discord.ButtonStyle.red)
            result_view = View()
            result_view.add_item(success_button)
            result_view.add_item(failure_button)
            result_view.add_item(stop_button)

            async def list_success(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(success)]
                embeds= DescriptionEmbedPaginator(entries=entries, description="", title=f"Successful Freezes [{len(success)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            async def list_failure(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                entries = [f"{i+1}. {name}" for i, name in enumerate(failure)]
                embeds = DescriptionEmbedPaginator(entries=entries, description="", title=f"Unsuccessful Freezes [{len(failure)}]", color=0x000000, per_page=10).get_pages()
                paginator = Paginator(ctx, embeds)
                await paginator.paginate()

            async def stop_freeze(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                self.client.frozen_nicknames.pop(user.id, None)
                await interaction.response.send_message(f"Nickname freezing stopped for {user.name}.", ephemeral=True)

            success_button.callback = list_success
            failure_button.callback = list_failure
            stop_button.callback = stop_freeze

            await ctx.send(embed=embed, view=result_view)
            self.client.loop.create_task(self.nickname_freeze_task(user.id))

        async def cancel(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
            await interaction.message.delete()
            await ctx.send("Nickname freezing cancelled.")

        yes_button.callback = confirm
        no_button.callback = cancel
        await ctx.send(embed=confirm_embed, view=view)

    async def nickname_freeze_task(self, user_id: int):
        while user_id in self.client.frozen_nicknames:
            user_data = self.client.frozen_nicknames[user_id]
            frozen_name = user_data["name"]
            guild_ids = user_data["guild_ids"]

            for guild_id in guild_ids:
                guild = self.client.get_guild(guild_id)
                if not guild:
                    continue
                member = guild.get_member(user_id)
                if member and member.nick != frozen_name:
                    try:
                        await member.edit(nick=frozen_name)
                    except:
                        pass

            await asyncio.sleep(10)

 

    @global_command.command(name="unfreezenick", help="Unfreezes a user's nickname in all mutual guilds.")
    @commands.is_owner()
    async def global_unfreezenick(self, ctx: commands.Context, user: discord.User):
        if not hasattr(self.client, "frozen_nicknames"):
            self.client.frozen_nicknames = {}

        if user.id not in self.client.frozen_nicknames:
            return await ctx.send(f"❌ | {user.name}'s nickname is not being frozen.")

        del self.client.frozen_nicknames[user.id]
        await ctx.send(f"✅ | Nickname freezing stopped for {user.name}.")


    @commands.command(name="freezenick", help="Freezes a member's nickname in the current server.")
    @commands.has_permissions(manage_nicknames=True)
    async def freeze_nickname(self, ctx: commands.Context, member: Member, *, nickname: str):
        guild_id = ctx.guild.id
        if guild_id not in self.local_frozen_nicks:
            self.local_frozen_nicks[guild_id] = {}

        if member.id in self.local_frozen_nicks[guild_id]:
            return await ctx.send(f"{member.mention}'s nickname is already being frozen.")

        
        try:
            await member.edit(nick=nickname)
            self.local_frozen_nicks[guild_id][member.id] = nickname
            await ctx.send(f"Freezing {member.mention}'s nickname as '{nickname}'.")
        except:
            return await ctx.send(f"Could not change {member.mention}'s nickname due to insufficient permissions.")

        async def monitor_nickname():
            while member.id in self.local_frozen_nicks.get(guild_id, {}):
                if member.nick != nickname:
                    try:
                        await member.edit(nick=nickname)
                    except:
                        self.local_frozen_nicks[guild_id].pop(member.id, None)
                        await ctx.send(f"Stopped monitoring {member.mention}'s nickname due to insufficient permissions.")
                        break
                await asyncio.sleep(10)

            if not self.local_frozen_nicks[guild_id]:
                del self.local_frozen_nicks[guild_id]

        self.client.loop.create_task(monitor_nickname())

    @commands.command(name="unfreezenick", help="Unfreezes a member's nickname in the current server.")
    @commands.has_permissions(manage_nicknames=True)
    async def unfreeze_nickname(self, ctx: commands.Context, member: Member):
        guild_id = ctx.guild.id
        if guild_id in self.local_frozen_nicks and member.id in self.local_frozen_nicks[guild_id]:
            self.local_frozen_nicks[guild_id].pop(member.id, None)
            if not self.local_frozen_nicks[guild_id]:
                del self.local_frozen_nicks[guild_id]
            await ctx.send(f"✅ | Stopped freezing {member.mention}'s nickname.")
        else:
            await ctx.send(f"❌ | {member.mention}'s nickname is not currently being frozen.")
import os
import io
import random
import discord
import datetime
import requests
from discord.ext import commands
from discord.ext.commands import errors
from PIL import Image, ImageFont, ImageDraw
from utils.Tools import *

class Ship(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.special_users = [213347081799073793, 1144179659735572640, 677952614390038559, 839060566759702548]

    @commands.hybrid_command(pass_context=True, help="Ship two users together.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def ship(self, ctx, user1: discord.Member = None, user2: discord.Member = None):
        

        if user1 is None:  
            user1 = ctx.author
            guild = ctx.guild
            members = guild.members
            user2 = random.choice(members)
        elif user2 is None:  
            user2 = user1
            user1 = ctx.author

        author_id = float(user1.id)
        user_id = float(user2.id)

        if user1.id in self.special_users and user2.id in self.special_users:
            rate = 100
        else:
            now = datetime.datetime.now()
            day_seed = (now.day + now.month + now.year) / 3
            seed = (author_id + user_id) / day_seed
            random.seed(seed)
            rate = random.randint(1, 99)

        user_avatar = await get_avatar(user2)
        author_avatar = await get_avatar(user1)

        if user_avatar and author_avatar:
            self.make_image(author_avatar, user_avatar, user1.name, user2.name, rate)
            await self.img_ship(ctx, user1.mention, user2.mention, rate)
        else:
            await self.text_ship(ctx, user1.mention, user2.mention, rate)

    async def img_ship(self, ctx, author, user, rate):
        msg = "**Love rate between {0} & {1} is:**\n`{3}` {2}%"
        progress_bar = self.create_progress_bar(rate)
        try:
            b = discord.Embed(color=discord.Color(0xeb1818), description=msg.format(author, user, rate, progress_bar))
            f = discord.File("./data/ship/tmp_ship.png")
            b.set_image(url="attachment://tmp_ship.png")
            await ctx.send(file=f, embed=b)
        except errors.BadArgument:
            await ctx.send("Oops, something went wrong! Try again later!")

    def make_image(self, author_avatar, user_avatar, author, user, rate):
        red = (191, 15, 0, 255)
        white = (255, 255, 255, 255)
        blank = (255, 255, 255, 0)
        tmpl = Image.open("./data/ship/Template.png", "r").convert('RGBA')
        fill = Image.open("./data/ship/Tmpl_fill.png", "r").convert('RGBA')
        blank = Image.new('RGBA', tmpl.size, blank)
        fnt = ImageFont.truetype("./data/ship/font.ttf", 34)
        draw = ImageDraw.Draw(blank)
        author_avatar = author_avatar.resize((150, 150), Image.Resampling.LANCZOS)
        user_avatar = user_avatar.resize((150, 150), Image.Resampling.LANCZOS)
        tmpl.paste(author_avatar, (20, 50))
        tmpl.paste(user_avatar, (20, 312))
        offset = (100 - rate) * 2
        fill = fill.crop((0, offset, fill.width, fill.height))
        blank.paste(fill, (tmpl.width - fill.width - 1, 154 + offset))
        draw.text((20, 10), str(author), font=fnt, fill=red)
        draw.text((20, 460), str(user), font=fnt, fill=red)
        fnt = ImageFont.truetype("./data/ship/font.ttf", 80)
        draw.text((330, 192), str(rate) + "%", font=fnt, fill=white)
        tmpl = Image.alpha_composite(tmpl, blank)
        tmpl.save("./data/ship/tmp_ship.png", "PNG")

    async def text_ship(self, ctx, author, user, rate):
        msg = "**Love rate between {0} & {1} is:**\n`{3}` {2}%"
        progress_bar = self.create_progress_bar(rate)
        try:
            b = discord.Embed(color=discord.Color(0xeb1818), description=msg.format(author, user, rate, progress_bar))
            await ctx.send(embed=b)
        except errors.BadArgument:
            await ctx.send("Oops, something went wrong! Try again later!")

    def create_progress_bar(self, rate):
        filled_length = int(20 * rate // 100)
        bar = '█' * filled_length + ' ' * (20 - filled_length)
        return bar


async def get_avatar(user):
    try:
        user_url = user.display_avatar.replace(format="png").url
        response = requests.get(user_url + "?size=256")
        avatar = Image.open(io.BytesIO(response.content)).convert('RGBA')
        tmp = Image.new('RGBA', avatar.size, (255, 255, 255, 255))
        tmp = Image.alpha_composite(tmp, avatar)
        return tmp
    except Exception as e:
        print(f"Error fetching avatar: {e}")
        return None


def setup(bot):
    bot.add_cog(Ship(bot))




"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out support or DM me.
"""
import discord
from discord.ext import commands
import random
import os
import uuid
from PIL import Image
import bisect
from utils.Tools import *


class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['slot'])
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def slots(self, ctx: commands.Context):
        try:
            path = os.path.join('data/pictures/')
            facade = Image.open(f'{path}slot-face.png').convert('RGBA')
            reel = Image.open(f'{path}slot-reel.png').convert('RGBA')

            rw, rh = reel.size
            item = 180
            items = rh // item

            s1 = random.randint(1, items - 1)
            s2 = random.randint(1, items - 1)
            s3 = random.randint(1, items - 1)

            win_rate = 25 / 100

            if random.random() < win_rate:
                symbols_weights = [3.5, 7, 15, 25, 55]
                x = round(random.random() * 100, 1)
                pos = bisect.bisect(symbols_weights, x)
                s1 = pos + (random.randint(1, (items // 6) - 1) * 6)
                s2 = pos + (random.randint(1, (items // 6) - 1) * 6)
                s3 = pos + (random.randint(1, (items // 6) - 1) * 6)
                s1 = s1 - 6 if s1 == items else s1
                s2 = s2 - 6 if s2 == items else s2
                s3 = s3 - 6 if s3 == items else s3

            images = []
            speed = 6
            for i in range(1, (item // speed) + 1):
                bg = Image.new('RGBA', facade.size, color=(255, 255, 255))
                bg.paste(reel, (25 + rw * 0, 100 - (speed * i * s1)))
                bg.paste(reel, (25 + rw * 1, 100 - (speed * i * s2)))
                bg.paste(reel, (25 + rw * 2, 100 - (speed * i * s3)))
                bg.alpha_composite(facade)
                images.append(bg)

            unique_filename = str(uuid.uuid4()) + '.gif'
            fp = os.path.join('data/pictures/', unique_filename)

            images[0].save(
                fp,
                save_all=True,
                append_images=images[1:],
                duration=50
            )

            file = discord.File(fp, filename=unique_filename)
            message = await ctx.reply(file=file)

            if (1 + s1) % 6 == (1 + s2) % 6 == (1 + s3) % 6:
                result = 'won'
            else:
                result = 'lost'

            embed = discord.Embed(
                title=f'{ctx.author.display_name}, You {result}!',
                color=discord.Color.green() if result == "won" else discord.Color.red()
            )

            embed.set_image(url=f"attachment://{unique_filename}")
            await message.edit(content=None, embed=embed)

            os.remove(fp)
        except Exception as e:
            print(e)


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
import psutil
import sys
import os
import time
import aiosqlite
import platform
import pkg_resources
import datetime
from discord import Embed, ButtonStyle
from discord.ui import Button, View
from discord.ext import commands
from utils.Tools import *
import aiosqlite 
import wavelink

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.total_songs_played = 0
        self.bot.loop.create_task(self.setup_database())

    
    async def setup_database(self):
        async with aiosqlite.connect("db/stats.db") as db:
           # await db.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER)")
           # await db.commit()  
            async with db.execute("SELECT value FROM stats WHERE key = 'total_songs_played'") as cursor:
                row = await cursor.fetchone()
                self.total_songs_played = row[0] if row else 0

    async def update_total_songs_played(self):
        async with aiosqlite.connect("db/stats.db") as db:
            await db.execute("INSERT OR REPLACE INTO stats (key, value) VALUES ('total_songs_played', ?)", (self.total_songs_played,))
            await db.commit()

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        self.total_songs_played += 1
        await self.update_total_songs_played()

    def count_code_stats(self, file_path):
        total_lines = 0
        total_words = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    stripped_line = line.strip()
                    if stripped_line and not stripped_line.startswith(('〇')):
                        total_lines += 1
                        total_words += len(stripped_line.split())
        except (UnicodeDecodeError, IOError):
            pass
        return total_lines, total_words

    def gather_file_stats(self, directory):
        total_files = 0
        total_lines = 0
        total_words = 0
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if file.endswith('.py') and '.local' not in root:
                    total_files += 1
                    file_lines, file_words = self.count_code_stats(file_path)
                    total_lines += file_lines
                    total_words += file_words
        return total_files, total_lines, total_words

    @commands.hybrid_command(name="stats", aliases=["botinfo", "botstats", "bi", "statistics"], help="Shows the bot's information.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def stats(self, ctx):
        processing_message = await ctx.send("• Loading Tempest information...")
        
        guild_count = len(self.bot.guilds)
        user_count = sum(g.member_count for g in self.bot.guilds if g.member_count is not None)
        bot_count = sum(sum(1 for m in g.members if m.bot) for g in self.bot.guilds)
        human_count = user_count - bot_count
        channel_count = len(set(self.bot.get_all_channels()))
        blahh = human_count + bot_count
        text_channel_count = len([c for c in self.bot.get_all_channels() if isinstance(c, discord.TextChannel)])
        voice_channel_count = len([c for c in self.bot.get_all_channels() if isinstance(c, discord.VoiceChannel)])
        category_channel_count = len([c for c in self.bot.get_all_channels() if isinstance(c, discord.CategoryChannel)])
        slash_commands = len([cmd for cmd in self.bot.tree.get_commands()])
        commands_count = len(set(self.bot.walk_commands()))
        uptime_seconds = int(round(time.time() - self.start_time))
        uptime_timedelta = datetime.timedelta(seconds=uptime_seconds)
        uptime = f"{uptime_timedelta.days} days, {uptime_timedelta.seconds // 3600} hours, {(uptime_timedelta.seconds // 60) % 60} minutes, {uptime_timedelta.seconds % 60} seconds"

        total_files, total_lines, total_words = self.gather_file_stats('.')

        cpu_info = psutil.cpu_freq()
        memory_info = psutil.virtual_memory()
        
        total_libraries = sum(1 for _ in pkg_resources.working_set)
        channels_connected = sum(1 for vc in self.bot.voice_clients if vc)
        playing_tracks = sum(1 for vc in self.bot.voice_clients if vc.playing)

        embed = Embed(title="Tempest Statistics: General", color=0x000000)
        embed.add_field(name="• Channels", value=f"Total: **{channel_count}**\nText: **{text_channel_count}**   |   Voice: **{voice_channel_count}**   |   Category: **{category_channel_count}**", inline=False)
        embed.add_field(name="• Uptime", value=f"{uptime}", inline=False)
        embed.add_field(name="• User Count", value=f"Humans: **{human_count}**   |   Bots: **{bot_count}**", inline=False)
        embed.add_field(name="• Commands", value=f"Total: **{commands_count}**   |   Slash: **{slash_commands}**", inline=False)
        embed.add_field(name="✅ Libraries Used", value=f"Discord Library: **[discord.py](https://discordpy.readthedocs.io/en/stable/)**\nTotal Libraries: **{total_libraries}**", inline=False)
        embed.add_field(name="• Codebase Stats", value=f"Total Python Files: **{total_files}**\nTotal Lines: **{total_lines}**\nTotal Words: **{total_words}**", inline=False)
        embed.add_field(
    name="• Music Stats",
    value=f"Currently Connected: **[{channels_connected}](https://discord.gg/odx)**\n"
          f"Currently Playing: **[{playing_tracks}](https://discord.gg/odx)**\n"
          f"Total Songs Played: **[{self.total_songs_played}](https://discord.gg/odx)**",
    inline=False
        )
        embed.set_footer(text="Powered by Tempest Federation™", icon_url=self.bot.user.display_avatar.url)

        view = View()
        

        general_button = Button(label="General", style=ButtonStyle.gray)
        async def general_button_callback(interaction):
            if interaction.user == ctx.author:
                await interaction.response.edit_message(embed=embed, view=view)
        general_button.callback = general_button_callback
        view.add_item(general_button)

        system_button = Button(label="System", style=ButtonStyle.gray)
        async def system_button_callback(interaction):
            if interaction.user == ctx.author:
                system_embed = Embed(title="Tempest Statistics: System", color=0x000000)

                system_embed.add_field(name="• System Info", value=f"• Discord.py: **{discord.__version__}**\n• Python: **{platform.python_version()}**\n• Architecture: **{platform.machine()}**\n• Platform: **{platform.system()}**", inline=False)

                system_embed.add_field(name="• Memory Info", value=f"• Total Memory: **{memory_info.total / (1024 ** 2):,.2f} MB**\n• Memory Left: **{memory_info.available / (1024 ** 2):,.2f} MB**\n• Heap Total: **{memory_info.used / (1024 ** 2):,.2f} MB**", inline=False)
                system_embed.add_field(name="• CPU Info", value=f"• CPU: **{psutil.cpu_freq().max}' GHz**\n• CPU Usage: **{psutil.cpu_percent()}%**\n• CPU Cores: **{psutil.cpu_count(logical=False)}**\n• CPU Speed: **{cpu_info.current:.2f} MHz**", inline=False)
                system_embed.set_footer(text="Powered by Tempest Federation™", icon_url=self.bot.user.display_avatar.url)
                
                await interaction.response.edit_message(embed=system_embed, view=view)
        system_button.callback = system_button_callback
        view.add_item(system_button)


        ping_button = Button(label="Ping", style=ButtonStyle.green)
        async def ping_button_callback(interaction):
            if interaction.user == ctx.author:
                s_id = ctx.guild.shard_id
                sh = self.bot.get_shard(s_id)

                db_latency = None
                try:
                    async with aiosqlite.connect("db/afk.db") as db:
                        start_time = time.perf_counter()
                        await db.execute("SELECT 1")
                        end_time = time.perf_counter()
                        db_latency = (end_time - start_time) * 1000
                        db_latency = round(db_latency, 2)
                except Exception as e:
                    db_latency = "N/A"

                wsping = round(self.bot.latency * 1000, 2)

                ping_embed = Embed(title="Bot Statistic: Ping", color=0x000000)
                ping_embed.add_field(name="✅ Bot Latency", value=f"{round(sh.latency * 800)} ms", inline=False)
                ping_embed.add_field(name="• Database Latency", value=f"{db_latency} ms", inline=False)
                ping_embed.add_field(name="• Websocket Latency", value=f"{wsping} ms", inline=False)
                ping_embed.set_footer(text="Powered by Tempest Federation™", icon_url=self.bot.user.display_avatar.url)
                await interaction.response.edit_message(embed=ping_embed, view=view)
        ping_button.callback = ping_button_callback
        view.add_item(ping_button)

        

        """team_button = Button(label="Team", style=ButtonStyle.primary)
        async def team_button_callback(interaction):
            if interaction.user == ctx.author:
                team_embed = Embed(title="Tempest Team", color=0x000000)
                team_embed.add_field(name="**👑 Bot Owner(s)**", value=">>> **[Sonu](https://discord.com/users/1070619070468214824)**,   **[!⌁𓆩ζ͜͡𝘿𝙉𝘼 𝙎𝙚𝙧𝙞𝙚𝙨ㄚㄒᥫ᭡](https://discord.com/users/677952614390038559)**,   **[Pritam](https://discord.com/users/1087282349395411015)**,   **[CuTeBoY.Ly](https://discord.com/users/995898882607292506)**", inline=False)
                team_embed.add_field(name="**• Bot Developer(s)**", value="> **[Sonu!?](https://discord.com/users/213347081799073793)** (Lead Developer)", inline=False)
                team_embed.add_field(name="**• Web Developer(s)**", value="> **[Love](https://discord.com/users/773755998665441280)** (Lead Web Developer)", inline=False)
                team_embed.add_field(name="**• Tester(s)**", value="> **[! Lucifer](https://discord.com/users/1113040686686674987)**", inline=False)
                team_embed.add_field(name="**• Team(s)**", value="> **[Tempest Federation™](https://discord.gg/odx)**", inline=False)
                team_embed.add_field(name="**• Partner(s)**", value="> **[Endercloud](https://endercloud.in/)**", inline=False)
                team_embed.set_footer(text="Powered by Tempest Federation™", icon_url=self.bot.user.display_avatar.url)
                await interaction.response.edit_message(embed=team_embed, view=view)
        team_button.callback = team_button_callback
        view.add_item(team_button)"""

        
        delete_button = Button(label="🗑️", style=ButtonStyle.red)
        async def delete_button_callback(interaction):
            if interaction.user == ctx.author:
                await interaction.message.delete()
        delete_button.callback = delete_button_callback
        view.add_item(delete_button)
        

        server_count_button = Button(label=f"Servers: {guild_count}    |    Users: {blahh}", style=ButtonStyle.success, disabled=True)
        view.add_item(server_count_button)
        

        await ctx.reply(embed=embed, view=view)
        await processing_message.delete()

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import os
from utils.Tools import *

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="status", help="Shows the status of the user in detail.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def status(self, ctx, user: discord.User = None):
        user = user or ctx.author
        processing = await ctx.send("• Loading Status...")
        embed = discord.Embed(title=f"{user.display_name}'s Status", color=0x000000)

        status_emoji = {
            "online": "✅ Online",
            "idle": "• Idle",
            "dnd": "• Do Not Disturb",
            "offline": "❌ Offline"
        }

        member = None
        for guild in self.bot.guilds:
            member = guild.get_member(user.id)
            if member:
                break

        if member:
            status = status_emoji.get(str(member.status), "❌ Offline")
            embed.add_field(name="Status:", value=status, inline=False)

            avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
            embed.set_thumbnail(url=avatar_url)

            platform = self.get_platform(member)
            embed.add_field(name="Platform:", value=platform, inline=False)

            custom_status = self.get_custom_status(member)
            if custom_status:
                embed.add_field(name="Custom Status:", value=custom_status, inline=False)

            activity_text = self.get_activity_text(member.activities)
            if activity_text:
                embed.add_field(name="__Activity__:", value=activity_text, inline=False)

            for activity in member.activities:
                if isinstance(activity, discord.Spotify):
                    song_name = activity.title
                    album_cover_url = str(activity.album_cover_url)

                    album_image_path = 'data/pictures/album_image.png'

                    async with aiohttp.ClientSession() as session:
                        async with session.get(album_cover_url) as resp:
                            if resp.status == 200:
                                album_data = await resp.read()
                                with open(album_image_path, 'wb') as f:
                                    f.write(album_data)

                    card_image_path = self.create_spotify_card(song_name, album_image_path)

                    if os.path.exists(card_image_path):
                        file = discord.File(card_image_path, filename="spotify_card.png")
                        embed.set_image(url="attachment://spotify_card.png")
                    else:
                        await ctx.send("Failed to generate the Spotify card image.")
        else:
            try:
                user = await self.bot.fetch_user(user.id)
                embed.add_field(name="Status:", value="❌ Offline", inline=False)
                avatar_url = user.default_avatar.url
                embed.set_thumbnail(url=avatar_url)
            except discord.NotFound:
                await ctx.send("User not found.")
                return

        requester_avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=requester_avatar_url)

        await ctx.send(embed=embed, file=file if 'file' in locals() else None)
        await processing.delete()

    def create_spotify_card(self, song_name, album_image_path):
        card_path = 'data/pictures/spotify.png'
        output_path = 'data/pictures/spotify_card_output.png'

        base_img = Image.open(card_path).convert("RGBA")
        draw = ImageDraw.Draw(base_img)

        album_img = Image.open(album_image_path).convert("RGBA")
        album_img = album_img.resize((160, 160))

        mask = Image.new("L", album_img.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 160, 160), fill=255)

        base_img.paste(album_img, (30, 30), mask) 

        font_path = 'utils/arial.ttf'
        font = ImageFont.truetype(font_path, 40)

        truncated_song_name = song_name if len(song_name) <= 60 else song_name[:57] + "..."
        song_name_position = (220, 70) 
        draw.text(song_name_position, truncated_song_name, font=font, fill="white")

        base_img.save(output_path)
        return output_path

    def get_platform(self, member):
        if member.desktop_status != discord.Status.offline:
            return "• Desktop"
        elif member.mobile_status != discord.Status.offline:
            return "• Mobile"
        elif member.web_status != discord.Status.offline:
            return "✅ Browser"
        return "Unknown"

    def get_custom_status(self, member):
        for activity in member.activities:
            if isinstance(activity, discord.CustomActivity):
                status_text = activity.name or ""
                if activity.name == "Custom Status":
                    status_text = "‎ "
                status_emoji = str(activity.emoji) if activity.emoji else ""

                if status_emoji and not status_text:
                    return status_emoji
                elif status_emoji and status_text:
                    return f"{status_emoji} {status_text}"
                elif status_text:
                    return status_text
        return None

    def get_activity_text(self, activities):
        activity_list = []
        for activity in activities:
            if isinstance(activity, discord.Game):
                activity_list.append(f"Playing {activity.name}")
            elif isinstance(activity, discord.Streaming):
                activity_list.append(f"Streaming {activity.name} on **[Twitch]({activity.url})**")
            elif isinstance(activity, discord.Spotify):
                activity_list.append(f"**[Listening to Spotify](https://open.spotify.com/track/{activity.track_id})**")
            elif isinstance(activity, discord.Activity):
                activity_list.append(f"{activity.type.name.capitalize()} {activity.name}")
        return "\n".join(activity_list) if activity_list else None

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord.ui import View, Button
import requests
from io import BytesIO
import re
from utils.Tools import *

class Steal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



    @commands.hybrid_command(name="steal", help="Steal an emoji or sticker", usage="steal <emoji>", aliases=["eadd"], with_app_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.has_permissions(manage_emojis=True)
    async def steal(self, ctx, emote=None):
        if ctx.message.reference:
            ref_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            attachments = ref_message.attachments
            stickers = ref_message.stickers
            emojis = [emote for emote in ref_message.content.split() if emote.startswith('<:') or emote.startswith('<a:')]

            if attachments or stickers or emojis:
                await self.create_buttons(ctx, attachments, stickers, emojis)
                return

        if emote:
            await self.process_emoji(ctx, emote)
        else:
            await ctx.send(embed=discord.Embed(title="Steal", description="No emoji or sticker found", color=0x000000))

    async def process_emoji(self, ctx, emote):
        try:
            if emote[0] == '<':
                name = emote.split(':')[1]
                emoji_id = emote.split(':')[2][:-1]
                anim = emote.split(':')[0]
                if anim == '<a':
                    url = f'https://cdn.discordapp.com/emojis/{emoji_id}.gif'
                else:
                    url = f'https://cdn.discordapp.com/emojis/{emoji_id}.png'
                await self.add_emoji(ctx, url, name, animated=(anim == '<a'))
            else:
                await ctx.send(embed=discord.Embed(title="Steal", description="Invalid emoji", color=0x000000))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="Steal", description=f"Failed to add emoji: {str(e)}", color=0x000000))

    async def add_emoji(self, ctx, url, name, animated):
        try:
            if not self.has_emoji_slot(ctx.guild, animated):
                await ctx.send(embed=discord.Embed(title="Steal", description="No more emoji slots available", color=0x2f3136))
                return

            sanitized_name = self.sanitize_name(name)
            response = requests.get(url)
            img = response.content
            emote = await ctx.guild.create_custom_emoji(name=sanitized_name, image=img)
            await ctx.send(embed=discord.Embed(title="Steal", description=f"Added emoji \"**{emote}**\"!", color=0x000000))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="Steal", description=f"Failed to add emoji: {str(e)}", color=0x2f3136))

    async def add_sticker(self, ctx, url, name):
        try:
            if len(ctx.guild.stickers) >= self.get_max_sticker_count(ctx.guild):
                await ctx.send(embed=discord.Embed(title="Steal", description="No more sticker slots available", color=0x000000))
                return

            sanitized_name = self.sanitize_name(name)
            response = requests.get(url)
            img = BytesIO(response.content)
            emoji = "⭐"  
            await ctx.guild.create_sticker(name=sanitized_name, description="Added by bot", file=discord.File(img, filename="sticker.png"), emoji=emoji)
            await ctx.send(embed=discord.Embed(title="Steal", description=f"Added sticker \"**{sanitized_name}**\"!", color=0x000000))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="Steal", description=f"Failed to add sticker: {str(e)}", color=0x000000))

    def sanitize_name(self, name):
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        return sanitized[:32]  

    def has_emoji_slot(self, guild, animated):
        normal_emojis = [emoji for emoji in guild.emojis if not emoji.animated]
        animated_emojis = [emoji for emoji in guild.emojis if emoji.animated]
        max_normal, max_animated = self.get_max_emoji_count(guild)

        if animated:
            return len(animated_emojis) < max_animated
        else:
            return len(normal_emojis) < max_normal

    def get_max_emoji_count(self, guild):
        if guild.premium_tier == 3:
            return 250, 250
        elif guild.premium_tier == 2:
            return 150, 150
        elif guild.premium_tier == 1:
            return 100, 100
        else:
            return 50, 50

    def get_max_sticker_count(self, guild):
        if guild.premium_tier == 3:
            return 60
        elif guild.premium_tier == 2:
            return 30
        elif guild.premium_tier == 1:
            return 15
        else:
            return 5

    async def create_buttons(self, ctx, attachments, stickers, emojis):
        class StealView(View):
            def __init__(self, bot, ctx, attachments, stickers, emojis):
                super().__init__()
                self.bot = bot
                self.ctx = ctx
                self.attachments = attachments
                self.stickers = stickers
                self.emojis = emojis

            @discord.ui.button(label="Steal as Emoji", style=discord.ButtonStyle.primary)
            async def steal_as_emoji(self, interaction: discord.Interaction, button: discord.ui.Button):
                
                if interaction.user.id != self.ctx.author.id:
                    await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                    return
                await interaction.response.defer()
                for sticker in self.stickers:
                    
                    if sticker.format in [discord.StickerFormatType.png, discord.StickerFormatType.apng, discord.StickerFormatType.lottie]:
                        animated = sticker.format == discord.StickerFormatType.apng
                        await self.bot.cogs['Steal'].add_emoji(self.ctx, sticker.url, sticker.name.replace(' ', '_'), animated=animated)
                    else:
                        await self.ctx.send(embed=discord.Embed(title="Steal", description=f"Unsupported sticker format for {sticker.name}", color=0x000000))
                for attachment in self.attachments:
                    await self.bot.cogs['Steal'].add_emoji(self.ctx, attachment.url, attachment.filename.split('.')[0].replace(' ', '_'), animated=False)
                for emote in self.emojis:
                    name = emote.split(':')[1]
                    emoji_id = emote.split(':')[2][:-1]
                    anim = emote.split(':')[0]
                    if anim == '<a':
                        url = f'https://cdn.discordapp.com/emojis/{emoji_id}.gif'
                    else:
                        url = f'https://cdn.discordapp.com/emojis/{emoji_id}.png'
                    await self.bot.cogs['Steal'].add_emoji(self.ctx, url, name, animated=(anim == '<a'))

            @discord.ui.button(label="Steal as Sticker", style=discord.ButtonStyle.success)
            async def steal_as_sticker(self, interaction: discord.Interaction, button: discord.ui.Button):
                
                if interaction.user.id != self.ctx.author.id:
                    await interaction.response.send_message("This interaction is not for you.", ephemeral=True)
                    return
                await interaction.response.defer()
                for sticker in self.stickers:
                    await self.bot.cogs['Steal'].add_sticker(self.ctx, sticker.url, sticker.name)
                for attachment in self.attachments:
                    await self.bot.cogs['Steal'].add_sticker(self.ctx, attachment.url, attachment.filename.split('.')[0])
                for emote in self.emojis:
                    name = emote.split(':')[1]
                    emoji_id = emote.split(':')[2][:-1]
                    anim = emote.split(':')[0]
                    if anim == '<a':
                        url = f'https://cdn.discordapp.com/emojis/{emoji_id}.gif'
                    else:
                        url = f'https://cdn.discordapp.com/emojis/{emoji_id}.png'
                    await self.bot.cogs['Steal'].add_sticker(self.ctx, url, name)

        embed = discord.Embed(description="Choose what to steal:", color=0x000000)
        if attachments:
            embed.set_image(url=attachments[0].url)
        elif stickers:
            embed.set_image(url=stickers[0].url)
        elif emojis:
            for emote in emojis:
                emoji_id = emote.split(':')[2][:-1]
                url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
                embed.set_image(url=url)

        view = StealView(self.bot, ctx, attachments, stickers, emojis)
        await ctx.send(embed=embed, view=view)



"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import time
import discord
from discord.ext import commands
import asyncio
from utils.Tools import *
from datetime import datetime

class Timer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="timer", aliases=['tstart'], description="Starts a timer")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def _timer(self, ctx, times, *, title: str = None):
        if title is None:
            title = 'Timer'

        try:
            try:
                time = int(times)
            except:
                convertTimeList = {'s':1, 'm':60, 'h':3600, 'd':86400, 'S':1, 'M':60, 'H':3600, 'D':86400}
                time = int(times[:-1]) * convertTimeList[times[-1]]
            if time > 86400:
                await ctx.send("Timers should not exceed a day in duration.")
                return
            if time <= 0:
                await ctx.send("Timers do not go into negatives.")
                return
            if time >= 3600:
                embed = discord.Embed(
                    title=f'{title}',
                    description=f"**{time//3600}** hours, **{time%3600//60}** minutes, **{time%60}** seconds",
                    color=0x000000
                )
                embed.set_footer(text=f'Requested by {ctx.author.name}')
                message = await ctx.send(embed=embed)
                await message.add_reaction('⏱️')
            elif time >= 60:
                embed = discord.Embed(
                    title=f'{title}',
                    description=f"**{time//60}** minutes, **{time%60}** seconds",
                    color=0x000000
                )
                embed.set_footer(text=f'Requested by {ctx.author.name}')
                message = await ctx.send(embed=embed)
                await message.add_reaction('⏱️')
            elif time < 60:
                embed = discord.Embed(
                    title=f'{title}',
                    description=f'**{time}** seconds',
                    color=0x000000
                )
                embed.set_footer(text=f'Requested by {ctx.author.name}')
                message = await ctx.send(embed=embed)
                await message.add_reaction('⏱️')
            while True:
                try:
                    await asyncio.sleep(6)
                    time -= 6
                    if time >= 3600:
                        embed = discord.Embed(
                            title=f'{title}',
                            description=f"**{time//3600}** hours, **{time%3600//60}** minutes, **{time%60}** seconds",
                            color=0x000000
                        )
                        embed.set_footer(text=f'Requested by {ctx.author.name}')
                        await message.edit(embed=embed)
                    elif time >= 60:
                        embed = discord.Embed(
                            title=f'{title}',
                            description=f"**{time//60}** minutes, **{time%60}** seconds",
                            color=0x000000
                        )
                        embed.set_footer(text=f'Requested by {ctx.author.name}')
                        await message.edit(embed=embed)
                    elif time < 60:
                        embed = discord.Embed(
                            title=f'{title}',
                            description=f"**{time}** seconds",
                            color=0x000000
                        )
                        embed.set_footer(text=f'Requested by {ctx.author.name}')
                        await message.edit(embed=embed)
                    if time <= 0:
                        embed = discord.Embed(
                            title=f'{title}',
                            description='Time is up!',
                            color=0x000000
                        )
                        content= ctx.author.mention
                        await message.edit(content=content, embed=embed)
                        m = await ctx.channel.get_message(message.id)
                        list_thingy = []
                        output_list_thingy = []
                        reactants = await m.reactions[0].users().flatten()
                        reactants.pop(reactants.index(self.client.user))
                        for user in reactants:
                            list_thingy.append(user.id)
                            x = '<@!' + str(user.id) + '>' 
                            output_list_thingy.append(x)
                        if output_list_thingy != []:
                            final = ', '.join(map(str, output_list_thingy))
                            return await ctx.send(f'The timer for **{title}** has ended!\n{final}')
                        else:
                            return await ctx.send(f'The timer for **{title}** has ended!')
                except:
                    break
        except ValueError:
            await ctx.send(f"Invalid time input.", delete_after=5)

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord.utils import get
import os
from utils.Tools import *
from typing import Optional, Union
from discord.ext.commands import Context
from utils import Paginator, DescriptionEmbedPaginator, FieldPagePaginator, TextPaginator
from utils import *


class Voice(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.color = 0x000000

    @commands.group(name="voice", invoke_without_command=True, aliases=['vc'])
    @blacklist_check()
    @ignore_check()
    async def vc(self, ctx: commands.Context):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @vc.command(name="kick",
                help="Removes a user from the voice channel.",
                usage="voice kick <member>")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _kick(self, ctx, *, member: discord.Member):
        if member.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is not connected to any voice channel",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        ch = member.voice.channel.mention
        await member.edit(voice_channel=None,
                          reason=f"Disconnected by {str(ctx.author)}")
        embed2 = discord.Embed(title="✅ Success",

            description=f"{str(member)} has been disconnected from {ch}",
            color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

    @vc.command(name="kickall",
                help="Disconnect all members from the voice channel.",
                usage="voice kick all")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    #@commands.bot_has_permissions(move_members=True)
    
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _kickall(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any voice channels.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        count = 0
        ch = ctx.author.voice.channel.mention
        for member in ctx.author.voice.channel.members:
            await member.edit(
                voice_channel=None,
                reason=f"Disconnect All Command Executed By: {str(ctx.author)}")
            count += 1
        embed2 = discord.Embed(title="✅ Success",

            description=f"Disconnected {count} members from {ch}",
            color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

    @vc.command(name="mute",
                help="mute a member in voice channel .",
                usage="voice mute <member>")
    @commands.has_guild_permissions(mute_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _mute(self, ctx, *, member: discord.Member = None):
        if member is None:
            embed = discord.Embed(
                title="❌ Error",
                description="You need to mention a member to mute.",
                color=self.color
            )
            embed.set_footer(
                text=f"Requested by: {ctx.author}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )
            return await ctx.reply(embed=embed)

        if member.voice is None:
            embed = discord.Embed(
                title="❌ Error",
                description=f"{str(member)} is not connected to any voice channels.",
                color=self.color
            )
            embed.set_footer(
                text=f"Requested by: {ctx.author}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )
            return await ctx.reply(embed=embed)

        if member.voice.mute:
            embed = discord.Embed(
                title="❌ Error",
                description=f"{str(member)} is already muted in the voice channel.",
                color=self.color
            )
            embed.set_footer(
                text=f"Requested by: {ctx.author}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            )
            return await ctx.reply(embed=embed)

        await member.edit(mute=True)
        embed = discord.Embed(
            title="✅ Success",
            description=f"{str(member)} has been muted in {member.voice.channel.mention}.",
            color=self.color
        )
        embed.set_footer(
            text=f"Requested by: {ctx.author}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )
        return await ctx.reply(embed=embed)

    @vc.command(name="unmute",
                help="Unmute a member in the voice channel.",
                usage="voice unmute <member>")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(mute_members=True)
    #@commands.bot_has_permissions(mute_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def vcunmute(self, ctx, *, member: discord.Member):
        if member.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is not connected to any voice channel.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        if member.voice.mute == False:
            embed2 = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is already unmuted in the voice channel.",
                color=self.color)
            embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed2)
        ch = member.voice.channel.mention
        embed3 = discord.Embed(title="✅ Success",

            description=f"{str(member)} has been unmuted in {ch}",
            color=self.color)
        embed3.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed3.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        await member.edit(mute=False, reason=f"Unmuted by {str(ctx.author)}")
        return await ctx.reply(embed=embed3)

    @vc.command(name="muteall",
                help="Mute all members in a voice channel.",
                usage="voice muteall")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    #@commands.bot_has_permissions(mute_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _muteall(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any voice channel.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        count = 0
        ch = ctx.author.voice.channel.mention
        for member in ctx.author.voice.channel.members:
            if member.voice.mute == False:
                await member.edit(
                    mute=True,
                    reason=
                    f"voice muteall Command Executed by {str(ctx.author)}")
                count += 1
        embed2 = discord.Embed(title="✅ Success",
                               description=f"Muted {count} members in {ch}",
                               color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

    @vc.command(name="unmuteall",
                help="Unmute all members in a voice channel.",
                usage="voice unmuteall")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    #@commands.bot_has_permissions(mute_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _unmuteall(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any of the voice channel",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        count = 0
        ch = ctx.author.voice.channel.mention
        for member in ctx.author.voice.channel.members:
            if member.voice.mute == True:
                await member.edit(
                    mute=False,
                    reason=
                    f"Voice unmuteall Command Executed by: {str(ctx.author)}")
                count += 1
        embed2 = discord.Embed(title="✅ Success",
                               description=f"Unmuted {count} members in {ch}",
                               color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

    @vc.command(name="deafen",
                help="Deafen a user in a voice channel.",
                usage="voice deafen <member>")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(deafen_members=True)
    #@commands.bot_has_permissions(deafen_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _deafen(self, ctx, *, member: discord.Member):
        if member.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is not connected to any of the voice channel",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        if member.voice.deaf == True:
            embed2 = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is already deafened in the voice channel",
                color=self.color)
            embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed2)
        ch = member.voice.channel.mention
        embed3 = discord.Embed(title="✅ Success",

            description=f"{str(member)} has been Deafened in {ch}",
            color=self.color)
        embed3.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed3.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        await member.edit(deafen=True, reason=f"Deafen by {str(ctx.author)}")
        return await ctx.reply(embed=embed3)

    @vc.command(name="undeafen",
                help="Undeafen a User in a voice channel .",
                usage="voice undeafen <member>")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(deafen_members=True)
    #@commands.bot_has_permissions(deafen_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _undeafen(self, ctx, *, member: discord.Member):
        if member.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is not connected to any of the voice channel",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        if member.voice.deaf == False:
            embed2 = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is already undeafened in the voice channel",
                color=self.color)
            embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed2)
        ch = member.voice.channel.mention
        embed3 = discord.Embed(title="✅ Success",

            description=f"{str(member)} has been undeafened in {ch}",
            color=self.color)
        embed3.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed3.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        await member.edit(deafen=False,
                          reason=f"Undeafen by {str(ctx.author)}")
        return await ctx.reply(embed=embed3)

    @vc.command(name="deafenall",
                help="Deafen all Ussr in a voice channel.",
                usage="voice deafenall")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    #@commands.bot_has_permissions(deafen_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _deafenall(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any of the voice channel",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        count = 0
        ch = ctx.author.voice.channel.mention
        for member in ctx.author.voice.channel.members:
            if member.voice.deaf == False:
                await member.edit(
                    deafen=True,
                    reason=
                    f"voice deafenall Command Executed by {str(ctx.author)}")
                count += 1
        embed2 = discord.Embed(title="✅ Success",
                               description=f"Deafened {count} members in {ch}",
                               color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                           icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

    @vc.command(name="undeafenall",
                help="undeafen all member in a voice channel .",
                usage="voice undeafenall")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    #@commands.bot_has_permissions(deafen_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _undeafall(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected in any of the voice channel",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        count = 0
        ch = ctx.author.voice.channel.mention
        for member in ctx.author.voice.channel.members:
            if member.voice.deaf == True:
                await member.edit(
                    deafen=False,
                    reason=
                    f"Voice undeafenall Command Executed by: {str(ctx.author)}")
                count += 1
        embed2 = discord.Embed(title="✅ Success",

            description=f"Undeafened {count} members in {ch}",
            color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                           icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

    @vc.command(name="moveall",
                help="Move all members from the voice channel to the specified voice channel.",
                usage="voice moveall <voice channel>")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    #@commands.bot_has_permissions(move_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _moveall(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any of the voice channel",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        try:
            ch = ctx.author.voice.channel.mention
            nch = channel.mention
            count = 0
            for member in ctx.author.voice.channel.members:
                await member.edit(
                    voice_channel=channel,
                    reason=
                    f"voice moveall Command Executed by: {str(ctx.author)}")
                count += 1
            embed2 = discord.Embed(title="✅ Success",

                description=f"{count} Members moved from {ch} to {nch}",
                color=self.color)
            embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            await ctx.reply(embed=embed2)
        except:
            embed3 = discord.Embed(title="❌ Error",

                description=f"Invalid Voice channel provided",
                color=self.color)
            embed3.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed3.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            await ctx.reply(embed=embed3)

    

    @vc.command(name="pullall",
                help="Move all members of ALL voice channels to a specified voice channel.",
                usage="voice pullall <channel>")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    #@commands.bot_has_permissions(move_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _pullall(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any of the voice channel",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        count = 0
        for vc in ctx.guild.voice_channels:
            for member in vc.members:
                if member != ctx.author:
                    try:
                        await member.edit(
                            voice_channel=channel,
                            reason=f"Pullall Command Executed by: {str(ctx.author)}")
                        count += 1
                    except:
                        pass
        embed2 = discord.Embed(title="✅ Success",
                               description=f"Moved {count} members to {channel.mention}",
                               color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)


    @vc.command(name="move",
                help="Move a member from one voice channel to another.",
                usage="voice move <member> <channel>")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    #@commands.bot_has_permissions(move_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _move(self, ctx, member: discord.Member, channel: discord.VoiceChannel):
        if member.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is not connected to any voice channel.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        if channel == member.voice.channel:
            embed = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is already in {channel.mention}.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        await member.edit(voice_channel=channel,
                          reason=f"Moved by {str(ctx.author)}")
        embed2 = discord.Embed(title="✅ Success",

            description=f"{str(member)} has been moved to {channel.mention}",
            color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)
        

    @vc.command(name="pull",
                help="Pull a member from one voice channel to yours.",
                usage="voice pull <member>")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    #@commands.bot_has_permissions(move_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _pull(self, ctx, member: discord.Member):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any voice channel.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        if member.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is not connected to any voice channel.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        if member.voice.channel == ctx.author.voice.channel:
            embed = discord.Embed(title="❌ Error",

                description=
                f"{str(member)} is already in your voice channel.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        await member.edit(voice_channel=ctx.author.voice.channel,
                          reason=f"Pulled by {str(ctx.author)}")
        embed2 = discord.Embed(title="✅ Success",

            description=f"{str(member)} has been pulled to your voice channel.",
            color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

    @vc.command(name="lock",
                help="Locks the voice channel so no one can join.",
                usage="voice lock")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _lock(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any voice channel.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        ch = ctx.author.voice.channel.mention
        await ctx.author.voice.channel.set_permissions(ctx.guild.default_role,
                                                       connect=False,
                                                       reason=f"Locked by {str(ctx.author)}")
        embed2 = discord.Embed(title="✅ Success",

            description=f"{ch} has been locked.",
            color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

    @vc.command(name="unlock",
                help="Unlocks the voice channel so anyone can join.",
                usage="voice unlock")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _unlock(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any voice channel.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        ch = ctx.author.voice.channel.mention
        await ctx.author.voice.channel.set_permissions(ctx.guild.default_role,
                                                       connect=True,
                                                       reason=f"Unlocked by {str(ctx.author)}")
        embed2 = discord.Embed(title="✅ Success",

            description=f"{ch} has been unlocked.",
            color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

    @vc.command(name="private",
                help="Makes the voice channel private.",
                usage="voice private")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _private(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any voice channel.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        ch = ctx.author.voice.channel.mention
        await ctx.author.voice.channel.set_permissions(ctx.guild.default_role,
                                                       connect=False,
                                                       view_channel=False,
                                                       reason=f"Made private by {str(ctx.author)}")
        embed2 = discord.Embed(title="✅ Success",

            description=f"{ch} has been made private.",
            color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

    @vc.command(name="unprivate",
                help="Makes the voice channel public.",
                usage="voice unprivate")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def _unprivate(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(title="❌ Error",

                description=
                "You are not connected to any voice channel.",
                color=self.color)
            embed.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
            return await ctx.reply(embed=embed)
        ch = ctx.author.voice.channel.mention
        await ctx.author.voice.channel.set_permissions(ctx.guild.default_role,
                                                       connect=True,
                                                       view_channel=True,
                                                       reason=f"Made public by {str(ctx.author)}")
        embed2 = discord.Embed(title="✅ Success",

            description=f"{ch} has been made public.",
            color=self.color)
        embed2.set_footer(text=f"Requested by: {ctx.author}",
                               icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed2.set_thumbnail(url="https://cdn.discordapp.com/emojis/1279464563150032991.png")
        return await ctx.reply(embed=embed2)

"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import aiosqlite
import asyncio
import re
import json
from utils.Tools import *

class VariableButton(Button):
    def __init__(self, author):
        super().__init__(label="Variables", style=discord.ButtonStyle.secondary)
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Only the command author can use this button.", ephemeral=True)
            return

        variables = {
            "{user}": "Mentions the user (e.g., @UserName).",
            "{user_avatar}": "The user's avatar URL.",
            "{user_name}": "The user's username.",
            "{user_id}": "The user's ID number.",
            "{user_nick}": "The user's nickname in the server.",
            "{user_joindate}": "The user's join date in the server (formatted as Day, Month Day, Year).",
            "{user_createdate}": "The user's account creation date (formatted as Day, Month Day, Year).",
            "{server_name}": "The server's name.",
            "{server_id}": "The server's ID number.",
            "{server_membercount}": "The server's total member count.",
            "{server_icon}": "The server's icon URL."
        }
        

        embed = discord.Embed(
            title="Available Placeholders",
            description="Use these placeholders in your welcome message:",
            color=discord.Color(0x000000)
        )

        for var, desc in variables.items():
            embed.add_field(name=var, value=desc, inline=False)

        embed.set_footer(text="Add placeholders directly in the welcome message or embed fields.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class Welcomer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self._create_table())

    async def _create_table(self):
        async with aiosqlite.connect("db/welcome.db") as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS welcome (
                guild_id INTEGER PRIMARY KEY,
                welcome_type TEXT,
                welcome_message TEXT,
                channel_id INTEGER,
                embed_data TEXT,
                auto_delete_duration INTEGER
            )
            """)
            await db.commit()

    @commands.hybrid_group(invoke_without_command=True, name="greet", help="Shows all the greet commands.")
    @blacklist_check()
    @ignore_check()
    async def greet(self, ctx: commands.Context):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @greet.command(name="setup", help="Configures a welcome message for new members joining the server. ")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 6, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def greet_setup(self, ctx):
        async with aiosqlite.connect("db/welcome.db") as db:
            async with db.execute("SELECT * FROM welcome WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()
        
        if row:
            error = discord.Embed(description=f"A welcome message has already been set in {ctx.guild.name}. Use `{ctx.prefix}greet reset` to reconfigure.", color=0x000000)
            error.set_author(name="Error", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            return await ctx.send(embed=error)
            
        options_view = View(timeout=600)

        async def option_callback(interaction: discord.Interaction, button: Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You cannot interact with this setup.", ephemeral=True)
                return
            await interaction.response.defer()

            if button.custom_id == "simple":
                await interaction.message.delete()
                await self.simple_setup(ctx)
                
            elif button.custom_id == "embed":
                await interaction.message.delete()
                await self.embed_setup(ctx)
            elif button.custom_id == "cancel":
                await interaction.message.delete()

        button_simple = Button(label="Simple", style=discord.ButtonStyle.success, custom_id="simple")
        button_simple.callback = lambda interaction: option_callback(interaction, button_simple)
        options_view.add_item(button_simple)

        button_embed = Button(label="Embed", style=discord.ButtonStyle.success, custom_id="embed")
        button_embed.callback = lambda interaction: option_callback(interaction, button_embed)
        options_view.add_item(button_embed)

        button_cancel = Button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel")
        button_cancel.callback = lambda interaction: option_callback(interaction, button_cancel)
        options_view.add_item(button_cancel)

        embed = discord.Embed(
            title="Welcome Message Setup",
            description="Choose the type of welcome message you want to create:",
            color=0x000000
        )

        embed.add_field(
            name="• Simple",
            value="Send a plain text welcome message. You can use placeholders to personalize it.\n\n",
            inline=False
        )
        embed.add_field(
            name="• Embed",
            value="Send a welcome message in an embed format. You can customize the embed with a title, description, image, etc.",
            inline=False
        )

        embed.set_footer(text="Click the buttons below to choose the welcome message type.", icon_url=self.bot.user.display_avatar.url)
        

        await ctx.send(embed=embed, view=options_view)

    async def simple_setup(self, ctx):
        setup_view = View(timeout=600)
        first = View(timeout=600)
        message_content = []

        placeholders = {
            "user": ctx.author.mention,
            "user_avatar": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url,
            "user_name": ctx.author.name,
            "user_id": ctx.author.id,
            "user_nick": ctx.author.display_name,
            "user_joindate": ctx.author.joined_at.strftime("%a, %b %d, %Y"),
            "user_createdate": ctx.author.created_at.strftime("%a, %b %d, %Y"),
            "server_name": ctx.guild.name,
            "server_id": ctx.guild.id,
            "server_membercount": ctx.guild.member_count,
            "server_icon": ctx.guild.icon.url if ctx.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png",
            "timestamp": discord.utils.format_dt(ctx.message.created_at)
        }

        def safe_format(text):
            placeholders_lower = {k.lower(): v for k, v in placeholders.items()}

            def replace_var(match):
                var_name = match.group(1).lower()
                return str(placeholders_lower.get(var_name, f"{{{var_name}}}"))

            return re.sub(r"\{(\w+)\}", replace_var, text or "")
            

        async def update_preview(content):
            preview = safe_format(content)
            await preview_message.edit(content=f"**Preview:** {preview}", view=setup_view)

        first.add_item(VariableButton(ctx.author))

        preview_message = await ctx.send("__**Simple Message Setup**__ \nEnter your welcome message here:", view=first)

        async def submit_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You cannot interact with this setup.", ephemeral=True)
                return
            if message_content:
                await self._save_welcome_data(ctx.guild.id, "simple", message_content[0])
                await interaction.response.send_message("✅ Welcome message setup completed!")
                for item in setup_view.children:
                    item.disabled = True
                await preview_message.edit(view=setup_view)
            else:
                await interaction.response.send_message("No message entered to submit.", ephemeral=True)

        async def edit_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You cannot interact with this setup.", ephemeral=True)
                return
            await interaction.response.defer()
            await ctx.send("Enter the updated welcome message:")
            try:
                msg = await self.bot.wait_for("message", timeout=600, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                message_content.clear()
                message_content.append(msg.content)
                await update_preview(msg.content)
            except asyncio.TimeoutError:
                await ctx.send("Editing timed out.")

        async def cancel_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You cannot interact with this setup.", ephemeral=True)
                return
            await preview_message.delete()

        submit_button = Button(label="Submit", style=discord.ButtonStyle.success)
        submit_button.callback = submit_callback
        setup_view.add_item(submit_button)

        edit_button = Button(label="Edit", style=discord.ButtonStyle.primary)
        edit_button.callback = edit_callback
        setup_view.add_item(edit_button)
        setup_view.add_item(VariableButton(ctx.author))

        cancel_button = Button(emoji="•", style=discord.ButtonStyle.secondary)
        cancel_button.callback = cancel_callback
        setup_view.add_item(cancel_button)

        try:
            msg = await self.bot.wait_for("message", timeout=600, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            message_content.append(msg.content)
            await update_preview(msg.content)
        except asyncio.TimeoutError:
            await ctx.send("Setup timed out.")

    
    async def _save_welcome_data(self, guild_id, welcome_type, message, embed_data=None):
        async with aiosqlite.connect("db/welcome.db") as db:
            await db.execute("""
            INSERT OR REPLACE INTO welcome (guild_id, welcome_type, welcome_message, embed_data)
            VALUES (?, ?, ?, ?)
            """, (guild_id, welcome_type, message, json.dumps(embed_data) if embed_data else None))
            await db.commit()

    


    async def embed_setup(self, ctx):
        setup_view = View(timeout=600)
        embed_data = {
            "message": None,
            "title": None,
            "description": None,
            "color": None,
            "footer_text": None,
            "footer_icon": None,
            "author_name": None,
            "author_icon": None,
            "thumbnail": None,
            "image": None,
        }

        placeholders = {
            "user": ctx.author.mention,
            "user_avatar": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url,
            "user_name": ctx.author.name,
            "user_id": ctx.author.id,
            "user_nick": ctx.author.display_name,
            "user_joindate": ctx.author.joined_at.strftime("%a, %b %d, %Y"),
            "user_createdate": ctx.author.created_at.strftime("%a, %b %d, %Y"),
            "server_name": ctx.guild.name,
            "server_id": ctx.guild.id,
            "server_membercount": ctx.guild.member_count,
            "server_icon": ctx.guild.icon.url if ctx.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png",
            "timestamp": discord.utils.format_dt(ctx.message.created_at)
        }

        def safe_format(text):
            placeholders_lower = {k.lower(): v for k, v in placeholders.items()}  

            def replace_var(match):
                var_name = match.group(1).lower()
                return str(placeholders_lower.get(var_name, f"{{{var_name}}}"))

            return re.sub(r"\{(\w+)\}", replace_var, text or "")
            

        async def update_preview():
            content = safe_format(embed_data["message"]) or "Message Content."
            embed = discord.Embed(
    title=safe_format(embed_data["title"]) or "",
    description=safe_format(embed_data["description"]) or "```Customize your welcome embed, take help of variables.```",
    color=discord.Color(embed_data["color"]) if embed_data["color"] else discord.Color(0x2f3136)
            )

            
            if embed_data["footer_text"]:
                embed.set_footer(text=safe_format(embed_data["footer_text"]), icon_url=safe_format(embed_data["footer_icon"]) or None)
            if embed_data["author_name"]:
                embed.set_author(name=safe_format(embed_data["author_name"]), icon_url=safe_format(embed_data["author_icon"]) or None)
            if embed_data["thumbnail"]:
                embed.set_thumbnail(url=safe_format(embed_data["thumbnail"]))
            if embed_data["image"]:
                embed.set_image(url=safe_format(embed_data["image"]))

            await preview_message.edit(content="**Embed Preview:** " + content, embed=embed, view=setup_view)

        preview_message = await ctx.send("Configuring embed welcome message...")

        async def handle_selection(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You cannot interact with this setup.", ephemeral=True)
                return

            selected_option = select_menu.values[0]
            await interaction.response.defer()

            try:
                if selected_option == "message":
                    await ctx.send("Enter the welcome message content:")
                    msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                    embed_data["message"] = msg.content

                elif selected_option == "title":
                    await ctx.send("Enter the embed title:")
                    msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                    embed_data["title"] = msg.content

                elif selected_option == "description":
                    await ctx.send("Enter the embed description:")
                    msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                    embed_data["description"] = msg.content

                elif selected_option == "color":
                    await ctx.send("Enter a hex color (e.g., #3498db or 3498db):")
                    msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                    color_code = msg.content.lstrip("#")
                    if all(c in "0123456789abcdefABCDEF" for c in color_code) and len(color_code) in {3, 6}:
                        embed_data["color"] = int(color_code.lstrip("#"), 16)
                    else:
                        await ctx.send("Invalid color code. Please enter a valid hex color.")

                elif selected_option in ["footer_text", "footer_icon", "author_name", "author_icon", "thumbnail", "image"]:
                    await ctx.send(f"Enter the URL or text for {selected_option.replace('_', ' ')}:")
                    msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                    url_or_text = msg.content
                    if selected_option in ["footer_icon", "author_icon", "thumbnail", "image"]:
                        if url_or_text.startswith("http") or url_or_text in ["{user_avatar}", "{server_icon}"]:
                            embed_data[selected_option] = url_or_text
                        else:
                            await ctx.send("Invalid URL. Please enter a valid image URL or a supported placeholder ({user_avatar} or {server_icon}).")
                    else:
                        embed_data[selected_option] = url_or_text

                await update_preview()
                await interaction.followup.send(f"{selected_option.capitalize()} updated.", ephemeral=True)
            except asyncio.TimeoutError:
                await ctx.send("You took too long to respond. Please try again.")
            except Exception as e:
                await ctx.send(f"An error occurred: {e}")

        select_menu = Select(
            placeholder="Choose an option to edit the Embed",
            options=[
                discord.SelectOption(label="Message Content", value="message"),
                discord.SelectOption(label="Title", value="title"),
                discord.SelectOption(label="Description", value="description"),
                discord.SelectOption(label="Color", value="color"),
                discord.SelectOption(label="Footer Text", value="footer_text"),
                discord.SelectOption(label="Footer Icon", value="footer_icon"),
                discord.SelectOption(label="Author Name", value="author_name"),
                discord.SelectOption(label="Author Icon", value="author_icon"),
                discord.SelectOption(label="Thumbnail", value="thumbnail"),
                discord.SelectOption(label="Image", value="image")
            ]
        )
        select_menu.callback = handle_selection
        setup_view.add_item(select_menu)

        async def submit_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You cannot interact with this setup.", ephemeral=True)
                return
            if not any(embed_data[key] for key in ["title", "description"]):
                await interaction.response.send_message("Please provide at least a title or an description before submitting.", ephemeral=True)
                return

            await self._save_welcome_data(ctx.guild.id, "embed", embed_data["message"] or "", embed_data)
            await interaction.response.send_message("✅ Embed welcome message setup completed!")

            for item in setup_view.children:
                item.disabled = True
            await preview_message.edit(view=setup_view)

        submit_button = Button(label="Submit", style=discord.ButtonStyle.success)
        submit_button.callback = submit_callback
        setup_view.add_item(submit_button)
        setup_view.add_item(VariableButton(ctx.author))

        async def cancel_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You cannot interact with this setup.", ephemeral=True)
                return
            await preview_message.delete()
            await interaction.response.send_message("Embed setup cancelled.", ephemeral=True)

        cancel_button = Button(label="Cancel", style=discord.ButtonStyle.danger)
        cancel_button.callback = cancel_callback
        setup_view.add_item(cancel_button)

        await update_preview()

    

    @greet.command(name="reset", aliases=["disable"], help="Resets and deletes the current welcome configuration for the server.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 6, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def greet_reset(self, ctx):
        async with aiosqlite.connect("db/welcome.db") as db:
            cursor = await db.execute("SELECT 1 FROM welcome WHERE guild_id = ?", (ctx.guild.id,))
            is_set_up = await cursor.fetchone()

        if not is_set_up: 
            error = discord.Embed(description=f"No welcome message has been set for {ctx.guild.name}! Please set a welcome message first using `{ctx.prefix}greet setup`", color=0x000000)
            error.set_author(name="Greet is not configured!", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            return await ctx.send(embed=error)
            
        embed = discord.Embed(
            title="Are you sure?",
            description="This will remove all welcome configurations & data related to welcome messages for this server!",
            color=0x000000
        )

        yes_button = Button(label="Confirm", style=discord.ButtonStyle.danger)
        no_button = Button(label="Cancel", style=discord.ButtonStyle.secondary)

        async def yes_button_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Only the command author can confirm this action.", ephemeral=True)
                return

            async with aiosqlite.connect("db/welcome.db") as db:
                await db.execute("DELETE FROM welcome WHERE guild_id = ?", (ctx.guild.id,))
                await db.commit()

            embed.color = discord.Color(0x000000)
            embed.title = "✅ Success"
            embed.description = "Welcome message configuration has been successfully reset."
            await interaction.message.edit(embed=embed, view=None)

        async def no_button_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Only the command author can cancel this action.", ephemeral=True)
                return

            embed.color = discord.Color(0x000000)
            embed.title = "Cancelled"
            embed.description = "Greet Reset operation has been cancelled."
            await interaction.message.edit(embed=embed, view=None)

        yes_button.callback = yes_button_callback
        no_button.callback = no_button_callback

        view = View()
        view.add_item(yes_button)
        view.add_item(no_button)

        await ctx.send(embed=embed, view=view)
        

    @greet.command(name="channel", help="Sets the channel where welcome messages will be sent.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 6, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def greet_channel(self, ctx):
        async with aiosqlite.connect("db/welcome.db") as db:
            async with db.execute("SELECT welcome_type, channel_id FROM welcome WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                result = await cursor.fetchone()
                welcome_message = result[0] if result else None
                welcome_channel = ctx.guild.get_channel(result[1]) if result and result[1] else None

        if not welcome_message:
            error = discord.Embed(description=f"No welcome message has been set for {ctx.guild.name}! Please set a welcome message first using `{ctx.prefix}greet setup`", color=0x000000)
            error.set_author(name="Greet is not configured!", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            await ctx.send(embed=error)
            return

        channels = ctx.guild.text_channels
        chunk_size = 25
        chunks = [channels[i:i + chunk_size] for i in range(0, len(channels), chunk_size)]
        current_page = 0

        def generate_view(page):
            select_menu = Select(
                placeholder="Select a channel for welcome messages",
                options=[
                    discord.SelectOption(label=channel.name, emoji="•", value=str(channel.id))
                    for channel in chunks[page]
                ]
            )

            async def select_callback(interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized to set the welcome channel.", ephemeral=True)
                    return

                selected_channel_id = int(select_menu.values[0])
                selected_channel = ctx.guild.get_channel(selected_channel_id)

                async with aiosqlite.connect("db/welcome.db") as db:
                    await db.execute("UPDATE welcome SET channel_id = ? WHERE guild_id = ?", (selected_channel_id, ctx.guild.id))
                    await db.commit()

                embed.description = f"Current Welcome Channel: {selected_channel.mention}"
                await interaction.response.edit_message(embed=embed, view=None)
                await ctx.send(f"✅ Welcome channel has been set to {selected_channel.mention}")

            select_menu.callback = select_callback

            next_button = Button(label="Next List of Channels", style=discord.ButtonStyle.secondary, disabled=page >= len(chunks) - 1)
            previous_button = Button(label="Previous", style=discord.ButtonStyle.secondary, disabled=page <= 0)

            async def next_callback(interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized to navigate these menus.", ephemeral=True)
                    return
                nonlocal current_page
                current_page += 1
                await interaction.response.edit_message(embed=embed, view=generate_view(current_page))

            async def previous_callback(interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized to navigate these menus.", ephemeral=True)
                    return
                nonlocal current_page
                current_page -= 1
                await interaction.response.edit_message(embed=embed, view=generate_view(current_page))

            next_button.callback = next_callback
            previous_button.callback = previous_callback

            view = View()
            view.add_item(select_menu)
            view.add_item(previous_button)
            view.add_item(next_button)
            return view

        embed = discord.Embed(
            title=f"Welcome Channel for {ctx.guild.name}",
            description=f"Current Welcome Channel: {welcome_channel.mention if welcome_channel else 'None'}",
            color=0x000000
        )
        embed.set_footer(text="Use the dropdown menu to select a channel. Navigate pages if needed.")

        await ctx.send(embed=embed, view=generate_view(current_page))



    @greet.command(name="test", help="Sends a test welcome message to preview the setup.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 6, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def greet_test(self, ctx):
        async with aiosqlite.connect("db/welcome.db") as db:
            async with db.execute("SELECT welcome_type, welcome_message, channel_id, embed_data FROM welcome WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()

        if row is None:
            error = discord.Embed(description=f"No welcome message has been set for {ctx.guild.name}! Please set a welcome message first using `{ctx.prefix}greet setup`", color=0x000000)
            error.set_author(name="Greet is not configured!", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            await ctx.send(embed=error)
            return

        welcome_type, welcome_message, channel_id, embed_data = row
        welcome_channel = self.bot.get_channel(channel_id)

        if not welcome_channel:
            error2 = discord.Embed(description=f"Welcome channel not set or invalid. Use `{ctx.prefix}greet channel` to set one.", color=0x000000)
            error2.set_author(name="Channel not set", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            await ctx.send(embed=error2)
            return

        placeholders = {
            "user": ctx.author.mention,
            "user_avatar": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url,
            "user_name": ctx.author.name,
            "user_id": ctx.author.id,
            "user_nick": ctx.author.display_name,
            "user_joindate": ctx.author.joined_at.strftime("%a, %b %d, %Y"),
            "user_createdate": ctx.author.created_at.strftime("%a, %b %d, %Y"),
            "server_name": ctx.guild.name,
            "server_id": ctx.guild.id,
            "server_membercount": ctx.guild.member_count,
            "server_icon": ctx.guild.icon.url if ctx.guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png",
            "timestamp": discord.utils.format_dt(ctx.message.created_at)
        }

        def safe_format(text):
            placeholders_lower = {k.lower(): v for k, v in placeholders.items()}  

            def replace_var(match):
                var_name = match.group(1).lower()  
                return str(placeholders_lower.get(var_name, f"{{{var_name}}}"))

            return re.sub(r"\{(\w+)\}", replace_var, text or "")
            

        if welcome_type == "simple" and welcome_message:
            await welcome_channel.send(safe_format(welcome_message))

        elif welcome_type == "embed" and embed_data:
            try:
                embed_info = json.loads(embed_data) 
                color_value = embed_info.get("color", None)

                
                embed_color = 0x2f3136

                
                if color_value and isinstance(color_value, str) and color_value.startswith("#"):
                    embed_color = discord.Color(int(color_value.lstrip("#"), 16))
                elif isinstance(color_value, int): 
                    embed_color = discord.Color(color_value)

            except (ValueError, SyntaxError, json.JSONDecodeError):
                await ctx.send("Invalid embed data format. Please reconfigure.")
                return

            content = safe_format(embed_info.get("message", "")) or None
            embed = discord.Embed(
                title=safe_format(embed_info.get("title", "")),
                description=safe_format(embed_info.get("description", "")),
                color=embed_color
            )
            embed.timestamp = discord.utils.utcnow()


            if embed_info.get("footer_text"):
                embed.set_footer(
                    text=safe_format(embed_info["footer_text"]),
                    icon_url=safe_format(embed_info.get("footer_icon", ""))
                )
            if embed_info.get("author_name"):
                embed.set_author(
                    name=safe_format(embed_info["author_name"]),
                    icon_url=safe_format(embed_info.get("author_icon", ""))
                )
            if embed_info.get("thumbnail"):
                embed.set_thumbnail(url=safe_format(embed_info["thumbnail"]))
            if embed_info.get("image"):
                embed.set_image(url=safe_format(embed_info["image"]))

            await welcome_channel.send(content=content, embed=embed)



    @greet.command(name="config", help="Shows the current welcome configuration.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 6, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def greet_config(self, ctx):
        async with aiosqlite.connect("db/welcome.db") as db:
            async with db.execute("SELECT * FROM welcome WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()

        if row:
            _, welcome_type, welcome_message, channel_id, embed_data, auto_delete_duration = row
            response_type = "Simple" if welcome_type == "simple" else "Embed"

            embed = discord.Embed(
                title=f"Greet Configuration for {ctx.guild.name}",
                color=0x000000
            )

            embed.add_field(name="Response Type", value=response_type, inline=False)

            if welcome_type == "simple":
                details = f"Message Content: {welcome_message or 'None'}"
                embed.add_field(name="Details", value=details[:1024], inline=False)
            else:
                embed_details = json.loads(embed_data) if embed_data else {}
                formatted_embed_data = "\n".join(
                    f"{key.replace('_', ' ').title()}: {value or 'None'}" for key, value in embed_details.items()
                ) or "None"

                for i, chunk in enumerate([formatted_embed_data[i:i+1024] for i in range(0, len(formatted_embed_data), 1024)]):
                    embed.add_field(name=f"Embed Data Part {i+1}", value=chunk, inline=False)

            greet_channel = self.bot.get_channel(channel_id)
            channel_display = greet_channel.mention if greet_channel else "None"
            auto_delete_duration = f"{auto_delete_duration} seconds" if auto_delete_duration else "None"

            embed.add_field(name="Greet Channel", value=channel_display, inline=False)
            embed.add_field(name="Auto Delete Duration", value=auto_delete_duration, inline=False)
            await ctx.send(embed=embed)
        else:
            error = discord.Embed(
                description=f"No welcome message has been set for {ctx.guild.name}! Please set a welcome message first using `{ctx.prefix}greet setup`",
                color=0x000000
            )
            error.set_author(name="Greet is not configured!", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            await ctx.send(embed=error)


    @greet.command(name="autodelete", aliases=["autodel"], help="Sets the auto-delete duration for the welcome message.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 6, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def greet_autodelete(self, ctx, time: str):
        
        if time.endswith("s"):
            seconds = int(time[:-1])
            if 3 <= seconds <= 300:
                auto_delete_duration = seconds
            else:
                await ctx.send("Auto delete time should be between 3 seconds and 300 seconds.")
                return
        elif time.endswith("m"):
            minutes = int(time[:-1])
            if 1 <= minutes <= 5:
                auto_delete_duration = minutes * 60  
            else:
                await ctx.send("Auto delete time should be between 1 minute and 5 minutes.")
                return
        else:
            await ctx.send("Invalid time format. Please use 's' for seconds and 'm' for minutes.")
            return

        
        async with aiosqlite.connect("db/welcome.db") as db:
            await db.execute("""
            UPDATE welcome
            SET auto_delete_duration = ?
            WHERE guild_id = ?
            """, (auto_delete_duration, ctx.guild.id))
            await db.commit()

        await ctx.send(f"✅ Auto delete duration has been set to **{auto_delete_duration}** seconds.")



    @greet.command(name="edit", help="Edits the current welcome message settings for the server.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 6, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def greet_edit(self, ctx):
        async with aiosqlite.connect("db/welcome.db") as db:
            async with db.execute("SELECT welcome_type, welcome_message, embed_data FROM welcome WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()

        if row is None:
            error = discord.Embed(description=f"No welcome message has been set for {ctx.guild.name}! Please set a welcome message first using `{ctx.prefix}greet setup`", color=0x000000)
            error.set_author(name="Greet is not configured!", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            await ctx.send(embed=error)
            return

        welcome_type, welcome_message, embed_data = row

        cancel_flag = False  

        if welcome_type == "simple":
            embed = discord.Embed(
                title="Edit Welcome Message",
                description=f"**Response Type:** Simple\n**Message Content:** {welcome_message or 'None'}",
                color=0x000000
            )
            edit_button = Button(label="Edit", style=discord.ButtonStyle.primary)
            cancel_button = Button(label="Cancel", style=discord.ButtonStyle.danger)

            async def cancel_button_callback(interaction):
                nonlocal cancel_flag
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized to cancel the setup.", ephemeral=True)
                    return
                await interaction.response.send_message("Setup has been canceled.", ephemeral=True)
                cancel_flag = True  
                view.clear_items()  
                await interaction.message.edit(embed=embed, view=view)

            cancel_button.callback = cancel_button_callback

            async def edit_button_callback(interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized to edit the welcome message.", ephemeral=True)
                    return

                await interaction.response.send_message("Please provide the new welcome message:", ephemeral=True)
                try:
                    new_message = await self.bot.wait_for(
                        "message",
                        check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                        timeout=600
                    )
                    if cancel_flag:  
                        await ctx.send("Setup was canceled. No changes were made.")
                        return
                    await new_message.delete()
                    async with aiosqlite.connect("db/welcome.db") as db:
                        await db.execute("UPDATE welcome SET welcome_message = ? WHERE guild_id = ?", (new_message.content, ctx.guild.id))
                        await db.commit()

                    embed.description = f"**Response Type:** Simple\n**Message Content:** {new_message.content}"
                    edit_button.disabled = True
                    cancel_button.disabled = True
                    await interaction.message.edit(embed=embed, view=view)
                    await ctx.send("Welcome message has been successfully updated.")
                except asyncio.TimeoutError:
                    await ctx.send("You took too long to respond.")
                except Exception as e:
                    await ctx.send(f"An error occurred: {e}")

            edit_button.callback = edit_button_callback
            view = View()
            view.add_item(edit_button)
            view.add_item(VariableButton(ctx.author))
            view.add_item(cancel_button)
            
            await ctx.send(embed=embed, view=view)

        elif welcome_type == "embed":
            embed_data_json = json.loads(embed_data) if embed_data else {}
            formatted_embed_data = "\n".join(
                f"{key.replace('_', ' ').title()}: {value or 'None'}" for key, value in embed_data_json.items()
            ) or "None"
            embed = discord.Embed(
                title="Edit Welcome Message",
                description=f"**Response Type:** Embed\n**Embed Data:**\n```{formatted_embed_data}```",
                color=0x000000
            )

            select_menu = Select(
                placeholder="Select an embed field to edit",
                options=[
                    discord.SelectOption(label=field.replace('_', ' ').title(), value=field)
                    for field in embed_data_json.keys()
                ]
            )

            cancel_button = Button(label="Cancel", style=discord.ButtonStyle.danger)

            async def cancel_button_callback(interaction):
                nonlocal cancel_flag
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized to cancel the setup.", ephemeral=True)
                    return
                await interaction.response.send_message("Setup has been canceled.", ephemeral=True)
                cancel_flag = True  
                view.clear_items()  
                await interaction.message.edit(embed=embed, view=view)

            cancel_button.callback = cancel_button_callback

            async def select_callback(interaction):
                nonlocal cancel_flag
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized to edit this embed.", ephemeral=True)
                    return

                selected_option = select_menu.values[0]
                await interaction.response.defer()

                while not cancel_flag:  
                    try:
                        if selected_option == "message":
                            await ctx.send("Enter the welcome message content:")
                            msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                            embed_data_json["message"] = msg.content

                        elif selected_option == "title":
                            await ctx.send("Enter the embed title:")
                            msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                            embed_data_json["title"] = msg.content

                        elif selected_option == "description":
                            await ctx.send("Enter the embed description:")
                            msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                            embed_data_json["description"] = msg.content

                        elif selected_option == "color":
                            await ctx.send("Enter a hex color (e.g., #3498db or 3498db):")
                            msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                            color_code = msg.content.lstrip("#")
                            if all(c in "0123456789abcdefABCDEF" for c in color_code) and len(color_code) in {3, 6}:
                                embed_data_json["color"] = int(color_code.lstrip("#"), 16)
                            else:
                                await ctx.send("Invalid color code. Please enter a valid hex color.")
                                continue  

                        elif selected_option in ["footer_text", "footer_icon", "author_name", "author_icon", "thumbnail", "image"]:
                            await ctx.send(f"Enter the URL or text for {selected_option.replace('_', ' ')}:")
                            msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                            url_or_text = msg.content
                            if selected_option in ["footer_icon", "author_icon", "thumbnail", "image"]:
                                if url_or_text.startswith("http") or url_or_text in ["{user_avatar}", "{server_icon}"]:
                                    embed_data_json[selected_option] = url_or_text
                                else:
                                    await ctx.send("Invalid URL. Please enter a valid image URL or a supported placeholder ({user_avatar} or {server_icon}).")
                                    continue  
                            else:
                                embed_data_json[selected_option] = url_or_text

                        async with aiosqlite.connect("db/welcome.db") as db:
                            await db.execute("UPDATE welcome SET embed_data = ? WHERE guild_id = ?", (json.dumps(embed_data_json), ctx.guild.id))
                            await db.commit()

                        embed.description = f"**Response Type:** Embed\n**Embed Data:**\n```{json.dumps(embed_data_json, indent=4)}```"
                        await interaction.message.edit(embed=embed, view=None)
                        await ctx.send("Embed data has been successfully updated.")
                        break 
                    except asyncio.TimeoutError:
                        await ctx.send("You took too long to respond.")
                        break
                    except Exception as e:
                        await ctx.send(f"An error occurred: {e}")
                        break

            select_menu.callback = select_callback
            view = View()
            view.add_item(select_menu)
            view.add_item(VariableButton(ctx.author))
            view.add_item(cancel_button)
            
            await ctx.send(embed=embed, view=view)


"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/odx (Tempest Federation)
    + for any queries reach out Community or DM me.
"""
