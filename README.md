<h1 align="center">
 <br>
  <a href="https://github.com/Vibhanshusalve"><img src="https://cdn.discordapp.com/avatars/1144179659735572640/7af45040da87480e78a2424691753f4d.png?size=128"></a>
  <br>
  Tempest the Ultimate Discord Bot
  <br>
</h1>

<h3 align=center>An advanced multipurpose Discord bot built with 400+ commands & 15+ categories.</h3>

<div align=center>

  <a href="https://github.com/Rapptz/discord.py">
    <img src="https://img.shields.io/badge/discord.py-v2.4.0-blue.svg?&style=for-the-badge&logo=python" alt="discordpy">
  </a>
  
  <a href="https://github.com/EvieePy/Wavelink">
    <img src="https://img.shields.io/badge/Wavelink-v3.4.1-blue.svg?&style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==" alt="wavelink" style="color:yellow;">
  </a>

  <a href="https://github.com/omnilib/aiosqlite">
    <img src="https://img.shields.io/badge/aiosqlite-%23003B57.svg?&style=for-the-badge&logo=sqlite&logoColor=white" alt="aiosqlite">
  </a>


</div>

<p align="center">
  <a href="#about">About</a>
  •
  <a href="#features">Features</a>
  •
  <a href="#installation">Installation</a>
  •
  <a href="#setting-up">Setting Up</a>
  •
  <a href="#license">License</a>
  •
  <a href="#donate">Donate</a>
  •
  <a href="#credits">Credits</a>
</p>

## 🔗 [Invite the Public Bot (Tempest) by clicking here!](https://discord.com/oauth2/authorize?client_id=1144179659735572640&permissions=2113268958&scope=bot)

## About

Tempest is a powerful, easy-to-use Discord bot designed to enhance your server experience with an extensive suite of features. Built with advanced security, automoderation, moderation, music systems, welcoming features, and more at its core, Tempest ensures your community stays safe and well-managed, giving you peace of mind and control.

## Features

| Feature                 | Description                                                      |
|-------------------------|------------------------------------------------------------------|
| ![Security](https://img.shields.io/badge/Security-Antinuke%20%26%20Emergency-red?style=for-the-badge) | Protect your server with Antinuke and emergency features. |
| ![Automoderation](https://img.shields.io/badge/Automoderation-Advanced-red?style=for-the-badge) | Automatically moderate your server to prevent spam and abuse. |
| ![Moderation](https://img.shields.io/badge/Moderation-Essential%20Tools-red?style=for-the-badge) | Manage your community with powerful moderation commands. |
| ![Music System](https://img.shields.io/badge/Music%20System-High%20Quality-red?style=for-the-badge) | Stream music with advanced controls and great sound quality. |
| ![Welcoming](https://img.shields.io/badge/Welcoming-Customizable-red?style=for-the-badge) | Greet members with personalized welcome messages. |
| ![Utilities](https://img.shields.io/badge/Utilities-Efficient%20Tools-red?style=for-the-badge) | Access tools that simplify server management. |
| ![Giveaway](https://img.shields.io/badge/Giveaway-Easy%20Management-red?style=for-the-badge) | Host and manage giveaways effortlessly. |
| ![Games](https://img.shields.io/badge/Games-Fun%20%26%20Interactive-red?style=for-the-badge) | Enjoy interactive games with your community. |
| ![Customrole](https://img.shields.io/badge/Customrole-Role%20Management-red?style=for-the-badge) | Easily assign and manage custom roles. |
| ![Fun](https://img.shields.io/badge/Fun-Entertainment%20Commands-red?style=for-the-badge) | Liven up your server with engaging fun commands. |
| ![Voice](https://img.shields.io/badge/Voice-Channel%20Control-red?style=for-the-badge) | Manage voice channels with advanced utilities. |
| ![AI Image Generator](https://img.shields.io/badge/AI%20Image%20Generator-Stunning%20Visuals-red?style=for-the-badge) | Create AI-powered images directly from Discord. |


## Installation

1. First, clone the repository:  
   ```bash
   git clone https://github.com/Vibhanshusalve/tempest.git
   cd tempest
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. After installation, run the bot:
   ```bash
   python main.py
   ```

## Setting Up

1. **Bot Token & Owner ID:**
   - Create a `.env` file in the root directory and add your bot token:
     ```env
     TOKEN=YOUR_BOT_TOKEN_HERE
     ```
   - Update the Owner ID(s) in `utils/config.py` (line 7):
     ```python
     OWNER_IDS = [YOUR_USER_ID_HERE]
     ```

2. **Prefix:**
   - Default Prefix: `~`
   - You can change the default prefix in `utils/Tools.py` (line 84)
   - Server admins can change the prefix per server using the `prefix` command

3. **For Music:**  
   - A public Lavalink is used by default
   - Get a list of public lavalinks available [here](https://lavalinks-list.vercel.app/)
   - For better audio quality, it is recommended to set up your private Lavalink v4
   - Update your Lavalink URL, password, and other configurations in `cogs/commands/music.py`
   - Make sure your Lavalink server settings also match `application.yml`

4. **Logging & Notifications:**  
   - **Command Logs:** Update the channel ID in `main.py` (line 74):
     ```python
     command_logs_channel_id = YOUR_CHANNEL_ID_HERE
     ```
   - **Guild Joins:** Update the channel ID in `cogs/events/on_guild.py` (line 25):
     ```python
     ch = YOUR_CHANNEL_ID_HERE
     ```
   - **Guild Leaves:** Update the channel ID in `cogs/events/on_guild.py` (line 109):
     ```python
     ch = YOUR_CHANNEL_ID_HERE
     ```

5. **No Prefix Commands:**  
   There are several `np` commands like `np add`, `np remove`, `auto np add`, `auto np remove`, `auto np role`, etc. Check and modify them as needed in `cogs/commands/np.py`.

6. **Emojis:**  
   All emojis have been updated to use Unicode emojis for better compatibility. No custom Discord emoji IDs are required.

## Key Features

### Security & Protection
- **Anti-Nuke System**: Comprehensive protection against malicious admin actions
- **Auto-Moderation**: Advanced spam, caps, link, invite, and mention protection
- **Emergency System**: Server restoration and emergency lockdown features

### Moderation
- **Full Moderation Suite**: Ban, kick, mute, warn, timeout, and more
- **Role Management**: Advanced role assignment and management
- **Channel Control**: Lock, unlock, hide, unhide, and channel management

### Entertainment
- **Games**: Chess, Battleship, Connect Four, Tic-Tac-Toe, Wordle, and more
- **Fun Commands**: Memes, images, and entertainment features
- **AI Image Generation**: Create stunning images using AI (Prodia integration)

### Server Management
- **Welcome System**: Customizable welcome messages with placeholders
- **Auto-Role**: Automatic role assignment on join
- **Custom Roles**: Advanced role management system
- **Voice Control**: Voice channel management utilities

### Utilities
- **Statistics**: Server and bot statistics tracking
- **AFK System**: Away from keyboard status
- **Giveaways**: Easy giveaway creation and management
- **Timers**: Set and manage timers
- **No-Prefix Commands**: Special users can use commands without prefix

## License
This source code is protected under a custom Tempest License.

> 🚫 No commercial use  
> 🚫 No redistribution  
> 🚫 No modification allowed without a paid license  

To obtain a license or permission, [join our support server](https://discord.gg/odx).

## Donate
Coming Soon

## Requirements

- Python 3.12+
- discord.py 2.4.0+
- All dependencies listed in `requirements.txt`
- Discord Bot Token
- (Optional) Lavalink server for music features
- (Optional) Prodia API key for AI image generation

## Support

For support, questions, or to report issues:
- Join our [Discord Server](https://discord.gg/odx)
- Open an issue on [GitHub](https://github.com/Vibhanshusalve/tempest/issues)

## Credits

**Original Author:**  
Sonu Jana - *Head Developer* - **[GitHub](https://github.com/sonujana26)**

**Repository:**  
Maintained by [Vibhanshusalve](https://github.com/Vibhanshusalve)

**Team:**
<div align="center">
  <a href="https://discord.com/invite/odx">
    <img src="https://discordapp.com/api/guilds/699587669059174461/widget.png?style=banner2">
  </a>
</div>
