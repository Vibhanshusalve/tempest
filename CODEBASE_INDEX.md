# Tempest Bot - Quick Reference Index

## File-to-Feature Mapping

### Core Files
| File | Purpose |
|------|---------|
| `main.py` | Bot entry point, initialization, webhook logging |
| `core/Tempest.py` | Main bot class, prefix system, extension loading |
| `core/Context.py` | Custom context with typing, permission checks |
| `core/Cog.py` | Base cog class for all features |

### Command Files (`cogs/commands/`)
| File | Commands/Features |
|------|-------------------|
| `general.py` | avatar, serverinfo, userinfo, ping, invite |
| `antinuke.py` | antinuke enable/disable, configuration |
| `automod.py` | automod setup, configuration |
| `welcome.py` | greet setup, welcome message configuration |
| `fun.py` | Entertainment commands, memes, images |
| `Games.py` | Game command wrappers |
| `moderation.py` | Moderation command group |
| `music.py.disabled` | Music commands (currently disabled) |
| `voice.py` | Voice channel management |
| `afk.py` | AFK system commands |
| `autorole.py` | Auto-role configuration |
| `autoresponder.py` | Auto-responder setup |
| `autoreact.py` | Auto-reaction configuration |
| `customrole.py` | Custom role management |
| `giveaway.py` | Giveaway creation and management |
| `imagine.py` | AI image generation (Prodia) |
| `blacklist.py` | User/guild blacklist management |
| `block.py` | Block system |
| `ignore.py` | Ignore system (channels/users/commands) |
| `nightmode.py` | Night mode (channel hiding) |
| `stats.py` | Statistics tracking |
| `status.py` | Bot status management |
| `emergency.py` | Emergency server restoration |
| `np.py` | No-prefix user management |
| `filters.py` | Music filter commands |
| `owner.py` | Owner-only commands |
| `owner2.py` | Additional owner commands (Global) |
| `extra.py` | Extra utility commands |
| `extraown.py` | Extra owner commands |
| `anti_wl.py` | Whitelist management |
| `anti_unwl.py` | Unwhitelist management |
| `blackjack.py` | Blackjack game |
| `slots.py` | Slots game |
| `ship.py` | Ship calculator |
| `steal.py` | Emoji stealing |
| `timer.py` | Timer functionality |
| `Embed.py` | Embed creation tools |
| `Media.py` | Media manipulation |
| `Invc.py` | Invite creator role system |
| `map.py` | Map/image utilities |
| `help.py` | Help command system |
| `notify.py` | Notification commands |

### Event Listeners (`cogs/events/`)
| File | Events Handled |
|------|----------------|
| `Errors.py` | Command error handling |
| `on_guild.py` | Guild join/leave logging |
| `autorole.py` | Auto-role on member join |
| `auto.py` | Additional auto-role logic |
| `greet2.py` | Welcome message sending |
| `mention.py` | Bot mention responses |
| `autoblacklist.py` | Automatic blacklisting |
| `autoreact.py` | Auto-reaction listeners |
| `react.py` | Reaction event handling |

### Anti-Nuke System (`cogs/antinuke/`)
| File | Protection Type |
|------|-----------------|
| `antiban.py` | Ban protection |
| `antikick.py` | Kick protection |
| `antibotadd.py` | Bot addition protection |
| `antichcr.py` | Channel creation protection |
| `antichdl.py` | Channel deletion protection |
| `antichup.py` | Channel update protection |
| `antirlcr.py` | Role creation protection |
| `antirldl.py` | Role deletion protection |
| `antirlup.py` | Role update protection |
| `antieveryone.py` | @everyone spam protection |
| `antiguild.py` | Guild update protection |
| `antiIntegration.py` | Integration abuse protection |
| `antiprune.py` | Member prune protection |
| `anti_member_update.py` | Member update protection |
| `antiwebhook.py` | Webhook update protection |
| `antiwebhookcr.py` | Webhook creation protection |
| `antiwebhookdl.py` | Webhook deletion protection |

### Auto-Moderation (`cogs/automod/`)
| File | Moderation Type |
|------|-----------------|
| `antispam.py` | Spam detection and prevention |
| `anticaps.py` | Excessive caps prevention |
| `antilink.py` | Unauthorized link blocking |
| `anti_invites.py` | Discord invite blocking |
| `anti_mass_mention.py` | Mass mention prevention |
| `anti_emoji_spam.py` | Emoji spam prevention |

### Moderation Commands (`cogs/moderation/`)
| File | Command |
|------|---------|
| `ban.py` | Ban members |
| `unban.py` | Unban members |
| `kick.py` | Kick members |
| `timeout.py` | Timeout (mute) members |
| `unmute.py` | Remove timeout |
| `warn.py` | Warn system |
| `lock.py` | Lock channels |
| `unlock.py` | Unlock channels |
| `hide.py` | Hide channels |
| `unhide.py` | Unhide channels |
| `role.py` | Role management |
| `message.py` | Message management (purge, etc.) |
| `snipe.py` | Message snipe |
| `topcheck.py` | Top role check system |
| `moderation.py` | Moderation command group |

### Games (`games/`)
| File | Game |
|------|------|
| `chess_game.py` | Chess |
| `battleship.py` | Battleship |
| `connect_four.py` | Connect Four |
| `tictactoe.py` | Tic-Tac-Toe |
| `twenty_48.py` | 2048 |
| `typeracer.py` | TypeRacer |
| `rps.py` | Rock Paper Scissors |
| `reaction_test.py` | Reaction Test |
| `country_guess.py` | Country Guesser |
| `wordle.py` | Wordle |
| `button_games/` | Button-based game implementations |

### Utilities (`utils/`)
| File | Purpose |
|------|---------|
| `Tools.py` | Database helpers, checks, config utilities |
| `config.py` | Configuration constants (owner IDs, etc.) |
| `config_loader.py` | YAML/config file loading |
| `help.py` | Help command pagination system |
| `paginator.py` | Message pagination utilities |
| `paginators.py` | Additional pagination utilities |
| `ai_utils.py` | AI image generation, search utilities |

### Database Files (`db/`)
| File | Purpose |
|------|---------|
| `prefix.db` | Guild prefixes |
| `anti.db` | Anti-nuke settings, whitelists |
| `automod.db` | Auto-moderation settings |
| `welcome.db` | Welcome message configurations |
| `afk.db` | AFK user data |
| `ignore.db` | Ignored channels/users/commands |
| `block.db` | Blacklisted users/guilds |
| `np.db` | No-prefix users |
| `giveaways.db` | Giveaway data |
| `stats.db` | Statistics |
| `autoreact.db` | Auto-reaction settings |
| `autoresponder.db` | Auto-responder data |
| `autorole.db` | Auto-role settings |
| `customrole.db` | Custom role data |
| `emergency.db` | Emergency system data |
| `media.db` | Media settings |
| `nightmode.db` | Night mode settings |
| `notify.db` | Notification settings |
| `warn.db` | Warning records |
| `topcheck.db` | Top check settings |
| `badges.db` | User badges |
| `blword.db` | Blacklisted words |
| `cache.db` | Cache data |
| `invite.db` | Invite tracking |

### Configuration Files
| File | Purpose |
|------|---------|
| `config.yml` | Main configuration (AI, language, triggers) |
| `application.yml` | Lavalink server configuration |
| `lang/lang.en.json` | English language strings |
| `.env` | Environment variables (TOKEN, etc.) |

### Other Directories
| Directory | Purpose |
|-----------|---------|
| `data/` | Static assets (card images, fonts, templates) |
| `prodia/` | Prodia API constants |
| `top-gg/` | Top.gg voting integration |
| `plugins/` | Lavalink plugins (YouTube plugin) |

## Command Categories

### Security & Protection
- `antinuke` - Anti-nuke system
- `whitelist` / `unwhitelist` - Whitelist management
- `emergency` - Emergency restoration
- `blacklist` - Blacklist management

### Moderation
- `ban` / `unban` - Ban management
- `kick` - Kick members
- `timeout` / `unmute` - Timeout system
- `warn` - Warning system
- `lock` / `unlock` - Channel locking
- `hide` / `unhide` - Channel hiding
- `purge` - Message deletion
- `snipe` - Message snipe

### Auto-Moderation
- `automod` - Auto-moderation setup
- Auto-spam, auto-caps, auto-link protection
- Auto-invite, auto-mention protection

### Server Management
- `greet` - Welcome system
- `autorole` - Auto-role assignment
- `customrole` - Custom role system
- `voice` - Voice channel management
- `nightmode` - Scheduled channel hiding

### Entertainment
- `games` - Various games (chess, battleship, etc.)
- `fun` - Fun commands
- `ship` - Ship calculator
- `slots` / `blackjack` - Casino games

### Utilities
- `avatar` - User avatars
- `serverinfo` - Server information
- `userinfo` - User information
- `embed` - Embed creation
- `timer` - Timer functionality
- `afk` - AFK system
- `stats` - Statistics

### AI & Media
- `imagine` - AI image generation
- `steal` - Emoji stealing
- Media manipulation commands

### Owner Commands
- `owner` - Owner utilities
- `owner2` - Global owner commands
- `extraown` - Extra owner features
- `status` - Bot status management

## Database Schema Quick Reference

### anti.db
- `antinuke` - Guild antinuke status
- `whitelisted_users` - Whitelist per action
- `limit_settings` - Rate limit configurations

### automod.db
- `automod` - Auto-moderation enabled status
- `automod_punishments` - Punishment types
- `automod_ignored` - Ignored channels/roles
- `automod_logging` - Logging channels

### welcome.db
- `welcome` - Welcome message configurations

### prefix.db
- `prefixes` - Guild prefixes

### ignore.db
- `ignored_channels` - Ignored channels
- `ignored_users` - Ignored users
- `ignored_commands` - Ignored commands
- `bypassed_users` - Bypass users

### block.db
- `user_blacklist` - Blacklisted users
- `guild_blacklist` - Blacklisted guilds

## Key Functions & Classes

### Core Classes
- `Tempest` - Main bot class
- `Context` - Custom context
- `Cog` - Base cog class

### Utility Functions
- `getConfig(guildID)` - Get guild config
- `updateConfig(guildID, data)` - Update guild config
- `blacklist_check()` - Blacklist decorator
- `ignore_check()` - Ignore decorator
- `top_check()` - Top role check decorator
- `get_ignore_data(guild_id)` - Get ignore settings

### Database Helpers
- `Database` - Singleton database manager
- `setup_db()` - Database initialization

## Event Flow

1. **Message Received** → `on_message`
   - Check prefix → Get command → Check permissions
   - Execute command → Log execution

2. **Member Join** → `on_member_join`
   - Auto-role assignment → Welcome message

3. **Member Ban** → `on_member_ban`
   - Check anti-nuke → Verify whitelist → Ban executor if needed

4. **Channel Created** → `on_guild_channel_create`
   - Check anti-nuke → Verify whitelist → Take action

5. **Command Error** → `on_command_error`
   - Handle error type → Send appropriate response

## Configuration Points

### Bot Token
- Environment variable: `TOKEN`
- Required for bot operation

### Owner IDs
- File: `utils/config.py`
- Variable: `OWNER_IDS`

### Prefix
- Default: `$`
- Per-guild: `db/prefix.db`
- Change: `utils/Tools.py` line 84

### Lavalink
- Config: `application.yml`
- Music: `cogs/commands/music.py` line 339

### Webhooks
- Command logs: `main.py` line 75
- Guild joins: `cogs/events/on_guild.py` line 25
- Guild leaves: `cogs/events/on_guild.py` line 109

### No-Prefix Commands
- File: `cogs/commands/np.py`
- Database: `db/np.db`

## Quick Troubleshooting

### Bot Not Responding
1. Check token in `.env`
2. Check bot permissions
3. Check prefix configuration
4. Check blacklist status

### Anti-Nuke Not Working
1. Check antinuke enabled: `antinuke status`
2. Check bot has admin permissions
3. Check whitelist configuration
4. Check database: `db/anti.db`

### Commands Not Found
1. Check command name spelling
2. Check prefix
3. Check ignore settings
4. Check blacklist status

### Database Errors
1. Check file permissions
2. Check database file exists
3. Check WAL mode enabled
4. Check connection retries

