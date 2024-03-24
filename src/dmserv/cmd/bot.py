import argparse
import os
import discord
import sqlalchemy

from discord.ext.bridge import AutoShardedBot
from dmserv.cogs.FronterList import FronterListCog
from dmserv.cogs.main import MainCog


def register_bot_subcommand(parser: argparse.ArgumentParser):
    parser.set_defaults(func=main)


def main(args: argparse.Namespace, engine: sqlalchemy.Engine) -> int:
    bot = AutoShardedBot(
        intents=discord.Intents.all(),
        command_prefix="dm!",
    )
    bot.add_cog(MainCog(bot, engine))
    bot.add_cog(FronterListCog(bot, engine))
    bot.run(os.getenv("DMSERV_BOT_TOKEN"))

    return 0
