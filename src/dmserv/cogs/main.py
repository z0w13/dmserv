import logging
from discord import PermissionOverwrite, Permissions
import pluralkit

from discord.bot import Bot
from discord.ext import commands
from discord.ext import bridge
from discord.ext import tasks
from sqlalchemy.orm import Session, sessionmaker

from dmserv.db.models import GuildSettingsRepo

log = logging.getLogger(__name__)


async def get_display_names(pk: pluralkit.Client) -> set[str]:
    return {
        member.display_name if member.display_name is not None else member.name
        async for member in pk.get_members()
    }


class MainCog(commands.Cog):
    def __init__(self, bot: Bot, sess: sessionmaker[Session]):
        self.bot = bot
        self.sess = sess
        self.update.start()

    def cog_unload(self):
        self.update.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        log.info(f"{self.bot.user} is ready and online!")

    @tasks.loop(seconds=5)
    async def update(self):
        settings = GuildSettingsRepo(self.sess)
        guild_ids = [g.id for g in self.bot.guilds]
        guild_tokens = settings.get_multi(guild_ids, "token")

        for guild_id, token in guild_tokens.items():
            if not isinstance(token, str):
                log.info(f"token for guild {guild_id} is not a string, skipping")
                continue

            discord_guild = self.bot.get_guild(guild_id)
            if discord_guild is None:
                log.info(f"guild {guild_id} not found, skipping")
                continue

            fronter_cat = None
            for cat in discord_guild.categories:
                if cat.name == "Current Fronters":
                    fronter_cat = cat
                    break

            if fronter_cat is None:
                log.info(
                    f"guild {guild_id} has no category for current fronters, skipping"
                )
                continue

            pk = pluralkit.Client(token=token)
            fronters = pk.get_fronters()
            names: set[str] = {fronter.name.lower() async for fronter in fronters}
            discord_names = {chan.name.lower() for chan in fronter_cat.channels}

            delete_names = discord_names - names
            create_names = names - discord_names

            for name in delete_names:
                for chan in fronter_cat.channels:
                    if chan.name == name:
                        log.debug(
                            f"deleting channel {chan.name} ({chan.id}) in guild {guild_id}"
                        )
                        await chan.delete()

            for name in create_names:
                log.debug(f"creating channel {name} in guild {guild_id}")
                await discord_guild.create_voice_channel(
                    name=name,
                    category=fronter_cat,
                    overwrites={
                        discord_guild.default_role: PermissionOverwrite(connect=False)
                    },
                )

    @bridge.bridge_command(name="update-alter-roles")
    @bridge.guild_only()
    async def update_alter_roles(self, ctx: bridge.BridgeApplicationContext):
        if ctx.guild is None:
            return await ctx.reply(
                "Error: guild is None, this shouldn't happen as this is a guild only command."
            )

        if ctx.guild.owner is None:
            return await ctx.reply(
                "Error: guild.owner is None, this shouldn't happen as this is a guild only command."
            )

        settings = GuildSettingsRepo(self.sess)
        if not settings.has(ctx.guild.id, "token"):
            return await ctx.reply(
                "ERROR: PluralKit API token not set, please set it using /set-token"
            )

        token = settings.get(ctx.guild.id, "token")
        if not isinstance(token, str):
            return await ctx.reply(
                "ERROR: Somehow PluralKit API token isn't a string, try setting it again or contacting us."
            )

        await ctx.defer()

        pk = pluralkit.Client(token=token)

        role_dict = {r.name: r for r in ctx.guild.roles if r.name.endswith(" (Alter)")}

        desired_alter_roles = {n + " (Alter)" for n in await get_display_names(pk)}
        current_alter_roles = set(role_dict.keys())

        delete_roles = current_alter_roles - desired_alter_roles
        create_roles = desired_alter_roles - current_alter_roles

        for role_name in delete_roles:
            log.info(f"deleting role {role_name} in {ctx.guild.id}")
            await role_dict[role_name].delete()

        for role_name in create_roles:
            log.info(f"creating role {role_name} in {ctx.guild.id}")
            role = await ctx.guild.create_role(name=role_name)
            log.info(
                f"assigning role role {role_name} ({role.id}) to {ctx.guild.owner.name} in {ctx.guild.id}"
            )
            await ctx.guild.owner.add_roles(role)

        await ctx.respond("Roles created and assigned!")

    @bridge.bridge_command(name="set-token")
    @bridge.guild_only()
    async def set_token(self, ctx: bridge.BridgeApplicationContext, token: str):
        if ctx.guild_id is None:
            return await ctx.reply(
                "Error: no guild ID, this shouldn't happen as this is a guild only command."
            )

        settings = GuildSettingsRepo(self.sess)
        settings.set(ctx.guild_id, "token", token)

        await ctx.reply("PluralKit API token set!")
