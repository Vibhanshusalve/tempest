# Tempest Bot - Codebase Analysis & Index

## Project Overview

**Tempest** is a comprehensive Discord bot built with `discord.py` (v2.4.0) featuring 400+ commands across 15+ categories. It's designed as a multipurpose bot with advanced security, moderation, music, games, and utility features.

### Key Technologies
- **Framework**: discord.py v2.4.0
- **Database**: aiosqlite (SQLite with async support)
- **Music**: Wavelink v3.4.1 (Lavalink integration)
- **Language**: Python 3.12
- **Architecture**: Auto-sharded bot with 2 shards

---

## Project Structure

```
olympus-bot/
├── main.py                 # Entry point, bot initialization
├── core/                   # Core bot classes
│   ├── Tempest.py         # Main bot class (AutoShardedBot)
│   ├── Cog.py             # Base cog class
│   └── Context.py         # Custom context class
├── cogs/                   # Feature modules (cogs)
│   ├── commands/          # Command implementations
│   ├── events/            # Event listeners
│   ├── antinuke/          # Anti-nuke protection system
│   ├── automod/           # Auto-moderation features
│   ├── moderation/       # Manual moderation commands
│   └── olympus/           # Help system modules
├── db/                     # SQLite database files
├── utils/                  # Utility functions and helpers
├── games/                  # Game implementations
├── data/                   # Static assets (cards, images, fonts)
├── lang/                   # Language files (i18n)
├── top-gg/                 # Top.gg integration (voting)
└── prodia/                 # AI image generation constants
```

---

## Core Architecture

### 1. Bot Class (`core/Tempest.py`)
- **Type**: `commands.AutoShardedBot` with 2 shards
- **Intents**: All intents enabled (including presences and members)
- **Prefix System**: Dynamic per-guild prefixes stored in SQLite
- **No-Prefix System**: Special users can use commands without prefix
- **Command Sync**: Automatic slash command synchronization

**Key Features**:
- Custom prefix resolution with no-prefix support
- Message edit handling for command execution
- Extension loading system
- Custom help command integration

### 2. Context Class (`core/Context.py`)
- Extends `commands.Context` with additional functionality
- Auto-typing decorator for commands
- Permission checks before sending messages
- Help command integration

### 3. Database System (`db/_db.py`)
- **Singleton Pattern**: Database connection manager
- **Connection Pooling**: Async-safe connection handling
- **Retry Logic**: Automatic retry on database lock errors
- **WAL Mode**: Write-Ahead Logging for better concurrency

**Database Files**:
- `prefix.db` - Guild prefixes
- `anti.db` - Antinuke settings and whitelists
- `automod.db` - Auto-moderation configurations
- `welcome.db` - Welcome message settings
- `afk.db` - AFK user data
- `ignore.db` - Ignored channels/users/commands
- `block.db` - Blacklisted users/guilds
- `np.db` - No-prefix users
- `giveaways.db` - Giveaway data
- `stats.db` - Statistics tracking
- And more...

---

## Feature Categories

### 1. Security & Anti-Nuke (`cogs/antinuke/`)

**Purpose**: Protect servers from malicious admin actions

**Components**:
- `antiban.py` - Prevents unauthorized bans
- `antikick.py` - Prevents unauthorized kicks
- `antibotadd.py` - Prevents bot additions
- `antichcr.py` - Prevents channel creation spam
- `antichdl.py` - Prevents channel deletion
- `antichup.py` - Prevents channel updates
- `antirlcr.py` - Prevents role creation spam
- `antirldl.py` - Prevents role deletion
- `antirlup.py` - Prevents role updates
- `antieveryone.py` - Prevents @everyone spam
- `antiguild.py` - Prevents guild setting changes
- `antiwebhook*.py` - Prevents webhook abuse
- `antiIntegration.py` - Prevents integration abuse
- `antiprune.py` - Prevents member pruning
- `anti_member_update.py` - Prevents member update abuse

**How It Works**:
1. Monitors audit logs for suspicious activity
2. Checks if executor is whitelisted
3. Automatically bans unwhitelisted admins performing protected actions
4. Rate limiting to prevent audit log spam
5. Configurable per-guild with enable/disable

### 2. Auto-Moderation (`cogs/automod/`)

**Features**:
- **Anti-Spam** (`antispam.py`): Detects message spam, applies timeouts
- **Anti-Caps** (`anticaps.py`): Prevents excessive capitalization
- **Anti-Link** (`antilink.py`): Blocks unauthorized links
- **Anti-Invites** (`anti_invites.py`): Blocks Discord invite links
- **Anti-Mass Mention** (`anti_mass_mention.py`): Prevents mass mentions
- **Anti-Emoji Spam** (`anti_emoji_spam.py`): Prevents emoji spam

**Configuration**:
- Per-guild enable/disable
- Ignored channels and roles
- Customizable punishments (timeout, kick, ban)
- Logging channel support

### 3. Moderation (`cogs/moderation/`)

**Commands**:
- `ban.py` - Ban members
- `unban.py` - Unban members
- `kick.py` - Kick members
- `timeout.py` - Timeout (mute) members
- `unmute.py` - Remove timeout
- `warn.py` - Warn system with database tracking
- `lock.py` / `unlock.py` - Channel locking
- `hide.py` / `unhide.py` - Channel hiding
- `role.py` - Role management
- `message.py` - Message management (purge, etc.)
- `snipe.py` - Message snipe functionality
- `topcheck.py` - Top role check system

### 4. Music System (`cogs/commands/music.py.disabled`)

**Status**: Currently disabled (`.disabled` extension)

**Features** (when enabled):
- Lavalink integration via Wavelink
- Play, pause, resume, stop
- Queue management
- Loop and autoplay modes
- Audio filters (nightcore, bassboost, etc.)
- Spotify support (commented out)
- YouTube, SoundCloud, Bandcamp support

**Configuration**:
- Lavalink server settings in `application.yml`
- Public Lavalink by default (configurable)
- YouTube plugin support

### 5. Games (`games/`)

**Available Games**:
- **Chess** (`chess_game.py`) - Full chess implementation
- **Battleship** (`battleship.py`) - Naval battle game
- **Connect Four** (`connect_four.py`) - Classic connect four
- **Tic-Tac-Toe** (`tictactoe.py`) - Classic tic-tac-toe
- **2048** (`twenty_48.py`) - Number puzzle game
- **TypeRacer** (`typeracer.py`) - Typing speed game
- **Rock Paper Scissors** (`rps.py`) - RPS game
- **Reaction Test** (`reaction_test.py`) - Reaction time game
- **Country Guesser** (`country_guess.py`) - Geography game
- **Wordle** (`wordle.py`) - Word guessing game
- **Blackjack** (`cogs/commands/blackjack.py`) - Card game
- **Slots** (`cogs/commands/slots.py`) - Slot machine

**Button Games**: Modern button-based implementations in `games/button_games/`

### 6. Welcome System (`cogs/commands/welcome.py`)

**Features**:
- Simple and embed welcome messages
- Customizable placeholders:
  - `{user}`, `{user_name}`, `{user_id}`, `{user_avatar}`
  - `{server_name}`, `{server_id}`, `{server_membercount}`
  - `{user_joindate}`, `{user_createdate}`
- Auto-delete duration configuration
- Channel-specific welcome messages
- Database storage for persistence

### 7. AI Image Generation (`cogs/commands/imagine.py`)

**Integration**: Prodia API

**Features**:
- Multiple AI models (20+ options):
  - Elldreth Vivid Mix, Deliberate v2, Dreamshaper
  - Realistic, Portrait, Anime models
  - Stable Diffusion variants
- Sampler options (Euler, DPM++, DDIM, etc.)
- Negative prompt support
- Seed control for reproducibility
- NSFW filtering (only in NSFW channels)
- Content safety filters (blocks child-related content)
- Cooldown system (1 image per 60 seconds)

**Implementation**:
- Uses `utils/ai_utils.py` for image generation
- Async job polling for Prodia API
- Image upscaling enabled
- Square aspect ratio by default

### 8. General Commands (`cogs/commands/general.py`)

**Features**:
- User info (avatar, banner, userinfo)
- Server info (serverinfo, members, roles)
- Utility commands (ping, invite, support)
- Embed creation tools
- Image manipulation
- Color utilities

### 9. Fun Commands (`cogs/commands/fun.py`)

**Features**:
- Meme generation
- Image manipulation
- Random content (nekos, etc.)
- Ship calculator
- Various entertainment commands

### 10. Utility Commands

**AFK System** (`cogs/commands/afk.py`):
- Set AFK status with reason
- Auto-respond to mentions
- DM notifications option
- Per-guild AFK status

**Auto-Role** (`cogs/commands/autorole.py`):
- Automatic role assignment on join
- Multiple role support
- Human/bot distinction

**Auto-Responder** (`cogs/commands/autoresponder.py`):
- Custom trigger-response pairs
- Embed support
- Multiple responses per trigger

**Auto-React** (`cogs/commands/autoreact.py`):
- Automatic emoji reactions to messages
- Channel-specific reactions
- Keyword-based reactions

**Custom Roles** (`cogs/commands/customrole.py`):
- User-customizable roles
- Color and name customization

**Giveaways** (`cogs/commands/giveaway.py`):
- Create and manage giveaways
- Database tracking
- Winner selection

**Night Mode** (`cogs/commands/nightmode.py`):
- Scheduled channel hiding/showing
- Time-based automation

**Voice Utilities** (`cogs/commands/voice.py`):
- Voice channel management
- Channel creation/deletion
- User management in voice channels

**Invite Creator** (`cogs/commands/Invc.py`):
- Automatic role assignment on invite usage
- Invite tracking

---

## Command System

### Prefix System
- **Default**: `$`
- **Per-Guild**: Stored in `db/prefix.db`
- **No-Prefix**: Special users can use commands without prefix
- **Mention**: Bot can be mentioned as prefix
- **DM Support**: Limited command support in DMs

### Command Checks
1. **Blacklist Check** (`blacklist_check()`): Blocks blacklisted users/guilds
2. **Ignore Check** (`ignore_check()`): Respects ignored channels/users/commands
3. **Top Check** (`top_check()`): Requires user's top role > bot's top role
4. **Permission Checks**: Standard Discord permission checks

### Error Handling (`cogs/events/Errors.py`)
- Comprehensive error handling for:
  - Missing permissions
  - Command not found
  - Cooldowns
  - Missing arguments
  - Check failures
  - Bot missing permissions

---

## Event System

### Guild Events (`cogs/events/on_guild.py`)
- **Guild Join**: Logs to configured channel
- **Guild Leave**: Logs to configured channel

### Auto-Role Events (`cogs/events/autorole.py`)
- Automatic role assignment on member join
- Bot/human distinction

### Welcome Events (`cogs/events/greet2.py`)
- Sends welcome messages
- Handles placeholder replacement

### Mention Events (`cogs/events/mention.py`)
- Responds to bot mentions
- Customizable responses

### Auto-Blacklist (`cogs/events/autoblacklist.py`)
- Automatic blacklisting based on conditions

---

## Configuration System

### Files
1. **`config.yml`**: Main configuration
   - AI settings (Groq API)
   - Language settings
   - Trigger words
   - Presence settings
   - Blacklist words

2. **`utils/config.py`**: Python config
   - Owner IDs
   - Server links
   - Bot name

3. **`utils/config_loader.py`**: Config loader
   - YAML parsing
   - Language file loading
   - Instruction loading

### Environment Variables
- `TOKEN`: Discord bot token (required)

---

## Database Schema

### Key Tables

**antinuke** (`anti.db`):
```sql
guild_id INTEGER PRIMARY KEY
status BOOLEAN
```

**whitelisted_users** (`anti.db`):
```sql
guild_id INTEGER
user_id INTEGER
ban, kick, prune, botadd, serverup, memup, 
chcr, chdl, chup, rlcr, rlup, rldl, meneve, 
mngweb, mngstemo BOOLEAN
PRIMARY KEY (guild_id, user_id)
```

**prefixes** (`prefix.db`):
```sql
guild_id INTEGER PRIMARY KEY
prefix TEXT NOT NULL
```

**automod** (`automod.db`):
```sql
guild_id INTEGER PRIMARY KEY
enabled BOOLEAN
```

**welcome** (`welcome.db`):
```sql
guild_id INTEGER PRIMARY KEY
welcome_type TEXT
welcome_message TEXT
channel_id INTEGER
embed_data TEXT
auto_delete_duration INTEGER
```

---

## Utility Functions (`utils/`)

### `Tools.py`
- Database setup functions
- Config getters/updaters
- Blacklist/ignore checks
- Top check implementation
- JSON file operations

### `help.py`
- Custom help command implementation
- Paginated help system
- Category-based navigation
- Dropdown and button navigation

### `ai_utils.py`
- Prodia image generation
- DuckDuckGo search integration
- Text-to-speech utilities
- Image processing

### `paginator.py` / `paginators.py`
- Message pagination utilities
- Button-based navigation

---

## Security Features

1. **Anti-Nuke System**: Comprehensive protection against server raids
2. **Whitelist System**: Trusted users exempt from anti-nuke
3. **Auto-Moderation**: Prevents spam and abuse
4. **Blacklist System**: Global user/guild blacklisting
5. **Permission Checks**: Multiple layers of permission validation
6. **Rate Limiting**: Cooldowns and concurrency limits
7. **Content Filtering**: NSFW and safety filters for AI generation

---

## Integration Points

### Top.gg (`top-gg/`)
- Voting system integration
- Quart-based webhook server
- Vote tracking database

### Lavalink
- Music streaming (currently disabled)
- Configuration in `application.yml`
- Wavelink library integration

### Prodia API
- AI image generation
- Multiple model support
- Async job polling

### Groq API (Config)
- AI chatbot features (referenced in config)
- Not actively used in current codebase

---

## Command Categories

1. **General** - Basic utility commands
2. **Moderation** - Server management
3. **Automod** - Auto-moderation configuration
4. **Antinuke** - Security settings
5. **Music** - Music commands (disabled)
6. **Games** - Interactive games
7. **Fun** - Entertainment commands
8. **Welcome** - Welcome message setup
9. **Voice** - Voice channel management
10. **Extra** - Additional utilities
11. **Owner** - Bot owner commands
12. **Stats** - Statistics tracking
13. **Emergency** - Emergency server restoration
14. **Status** - Bot status management
15. **No-Prefix** - No-prefix user management

---

## Notable Features

### 1. No-Prefix System
- Special users can use commands without prefix
- Stored in `db/np.db`
- Expiry time support
- Auto-expiry cleanup

### 2. Emergency System
- Server restoration features
- Backup/restore capabilities
- Emergency lockdown

### 3. Custom Help System
- Category-based navigation
- Paginated display
- Interactive buttons/dropdowns
- Per-category help commands

### 4. Multi-Database Architecture
- Separate databases for different features
- Async-safe operations
- Connection pooling

### 5. Comprehensive Logging
- Command execution logging (webhook)
- Guild join/leave logging
- Error tracking

---

## Development Notes

### Dependencies
- See `requirements.txt` for full list
- Key: discord.py, wavelink, aiosqlite, pillow, etc.

### Setup Requirements
1. Python 3.12+
2. Discord bot token
3. Lavalink server (for music, optional)
4. Prodia API key (for image generation, optional)

### Code Style
- Uses `discord.ext.commands` framework
- Async/await throughout
- Type hints in some areas
- Custom cog base class

### Extension Loading
- Automatic extension loading in `core/Tempest.py`
- All cogs loaded in `cogs/__init__.py`
- Jishaku extension for debugging

---

## File Count Summary

- **Commands**: ~40+ command files
- **Events**: ~8 event listener files
- **Anti-Nuke**: ~15 protection modules
- **Auto-Mod**: ~6 auto-moderation modules
- **Moderation**: ~13 moderation command files
- **Games**: ~10+ game implementations
- **Database Files**: ~20+ SQLite databases

---

## Architecture Patterns

1. **Cog Pattern**: All features as separate cogs
2. **Singleton Pattern**: Database connection manager
3. **Decorator Pattern**: Command checks and cooldowns
4. **Observer Pattern**: Event listeners for Discord events
5. **Factory Pattern**: Help system command generation

---

## Security Considerations

1. **Token Management**: Uses environment variables
2. **Permission Validation**: Multiple check layers
3. **Rate Limiting**: Prevents abuse
4. **Content Filtering**: AI generation safety
5. **Audit Log Monitoring**: Anti-nuke system
6. **Whitelist System**: Trusted user management

---

## Performance Optimizations

1. **Async Database**: aiosqlite for non-blocking DB operations
2. **Connection Pooling**: Database singleton pattern
3. **WAL Mode**: Write-Ahead Logging for SQLite
4. **Retry Logic**: Handles database locks gracefully
5. **Auto-Sharding**: 2 shards for load distribution
6. **Caching**: Context caching, command caching

---

## Known Limitations

1. **Music Disabled**: Music system currently disabled
2. **No Centralized Emoji Config**: Emojis hardcoded in files
3. **No Centralized Color Config**: Colors hardcoded
4. **Limited i18n**: Only English language file
5. **Manual Config**: Some settings require code changes

---

## Future Enhancement Areas

1. Centralized configuration for emojis/colors
2. Multi-language support expansion
3. Music system re-enablement
4. More comprehensive error recovery
5. Enhanced logging system
6. API documentation
7. Unit tests
8. Docker containerization

---

## Summary

Tempest is a feature-rich Discord bot with:
- **400+ commands** across 15+ categories
- **Advanced security** with anti-nuke protection
- **Comprehensive moderation** tools
- **Entertainment features** (games, fun commands)
- **AI integration** for image generation
- **Robust database** architecture
- **Extensible architecture** with cog system

The codebase is well-organized with clear separation of concerns, making it maintainable and extensible for future development.

