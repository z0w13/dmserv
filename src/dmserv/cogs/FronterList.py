import logging
import pluralkit

from discord import CategoryChannel, Guild, PermissionOverwrite
from discord.ext import commands
from discord.ext import tasks
from discord.ext.commands.bot import BotBase
from sqlalchemy.orm import Session, sessionmaker

from dmserv.db.models import GuildSettingsRepo

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class FronterListCog(commands.Cog):
    def __init__(self, bot: BotBase, sess: sessionmaker[Session]):
        self.bot = bot
        self.sess = sess
        self.update.start()

    def cog_unload(self):
        self.update.cancel()

    def get_guilds_to_process(self):
        settings = GuildSettingsRepo(self.sess)
        joined_guilds = {g.id: g for g in self.bot.guilds}
        guild_tokens = settings.get_multi(joined_guilds.keys(), "token")
        return [(joined_guilds[id], guild_tokens[id]) for id in guild_tokens.keys()]

    async def get_fronter_names(self, token: str):
        pk = pluralkit.Client(token=token)
        return [m.display_name or m.name async for m in pk.get_fronters()]

    def get_channels_grouped_by_name(self, cat: CategoryChannel):
        # Map channel names to channels
        return {chan.name: chan for chan in cat.channels}

    def get_fronter_category(self, guild: Guild) -> CategoryChannel | None:
        for cat in guild.categories:
            if cat.name == "Current Fronters":
                return cat

    async def update_guild(self, guild: Guild, token: str):
        fronter_cat = self.get_fronter_category(guild)
        if fronter_cat is None:
            log.info(f"guild '{guild.name}' has no category for fronters, skipping")
            return

        names = await self.get_fronter_names(token)

        # Create sets of current fronter and channel names
        discord_set = set(chan.name for chan in fronter_cat.channels)
        name_set = set(names)

        # Create map of names to positions in front list
        name_positions = {name: idx for idx, name in enumerate(names)}

        # Create sets for delete/create/position operations
        delete_names = discord_set - name_set
        create_names = name_set - discord_set
        position_names = name_set & discord_set

        # Map channel names to channels
        chan_map = self.get_channels_grouped_by_name(fronter_cat)

        for name in delete_names:
            log.debug(f"deleting channel '{name}' in guild '{guild.name}'")
            await chan_map[name].delete()
            del chan_map[name]

        for name in create_names:
            log.debug(
                f"creating channel '{name}' in guild '{guild.name}' at position {name_positions[name]}"
            )

            chan_map[name] = await fronter_cat.create_voice_channel(
                name=name,
                position=name_positions[name],
                overwrites={guild.default_role: PermissionOverwrite(connect=False)},
            )

        for name in position_names:
            if chan_map[name].position == name_positions[name]:
                continue

            log.debug(
                f"moving channel '{name}' in guild '{guild.name}' to position {name_positions[name]}"
            )
            await chan_map[name].edit(position=name_positions[name])

    @tasks.loop(seconds=5)
    async def update(self):
        for guild, token in self.get_guilds_to_process():
            if not isinstance(token, str):
                log.info(f"token for guild '{guild.name}' is not a string, skipping")
                return

            await self.update_guild(guild, token)
