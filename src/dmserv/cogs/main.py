import logging
import pluralkit

from discord import Member, errors
from discord.ext import bridge, commands
from pluralkit.v2.models import colour
from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from dmserv.db.models import GuildSettingsRepo

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


async def get_display_names(pk: pluralkit.Client) -> list[str]:
    return [member.display_name or member.name async for member in pk.get_members()]


def alter_color_to_int(color: colour.Color | None) -> int | None:
    if color is None:
        return color

    return int(color.get_hex_l().replace("#", "0x"), 16)


class MainCog(commands.Cog):
    def __init__(self, bot: bridge.AutoShardedBot, sess: sessionmaker[Session]):
        self.bot = bot
        self.sess = sess

    @commands.Cog.listener()
    async def on_ready(self):
        log.info(f"{self.bot.user} is ready and online!")

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

        role_dict = {
            r.name: r for r in ctx.guild.roles if r.name.lower().endswith(" (alter)")
        }
        # TODO: Don't do basic bitch splitting to remove pronouns but something more robust
        alter_dict: dict[str, pluralkit.Member] = {
            (a.display_name or a.name).split(" (")[0] + " (Alter)": a
            async for a in pk.get_members()
        }

        desired_alter_roles = set(alter_dict.keys())
        current_alter_roles = set(role_dict.keys())

        delete_roles = current_alter_roles - desired_alter_roles
        create_roles = desired_alter_roles - current_alter_roles
        update_roles = current_alter_roles & desired_alter_roles

        for role_name in delete_roles:
            log.info(f"deleting role '{role_name}' in '{ctx.guild.name}'")
            try:
                await role_dict[role_name].delete()
            except errors.Forbidden as e:
                if e.code == 50013:
                    await ctx.respond(
                        "Couldn't delete some roles, please make sure DMServ's role is listed above your alter roles"
                    )
                    break
                else:
                    raise

        for role_name in create_roles:
            log.info(f"creating role '{role_name}' in '{ctx.guild.name}'")
            role = await ctx.guild.create_role(
                name=role_name,
                mentionable=True,
                color=alter_color_to_int(alter_dict[role_name].color),
            )
            log.info(
                f"assigning role '{role_name}' ({role.id}) to '@{ctx.guild.owner.name}' in '{ctx.guild.name}'"
            )
            await ctx.guild.owner.add_roles(role)

        for role_name in update_roles:
            new_color = alter_color_to_int(alter_dict[role_name].color)
            if role_dict[role_name].color.value == new_color or new_color is None:
                continue

            await role_dict[role_name].edit(color=new_color)
            log.info(f"updated role '{role_name}' in '{ctx.guild.name}'")

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
