import argparse
import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dmserv.db.conn import create

from .admin import register_admin_subcommand
from .bot import register_bot_subcommand


def main() -> int:
    # Set up main parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", "-e", default=".env")

    subparsers = parser.add_subparsers(required=True)

    # Register subcommands
    register_admin_subcommand(subparsers.add_parser("admin"))
    register_bot_subcommand(subparsers.add_parser("bot"))

    # Parse arguments and load env vars
    args = parser.parse_args()
    load_dotenv(args.env_file)

    # Set up logging
    logging.basicConfig(level=getattr(logging, os.getenv("DMSERV_LOG_LEVEL", "INFO")))

    # Set up database
    engine = create(os.getenv("DMSERV_DB_URI", "sqlite+pysqlite:///:memory:"))
    sess = sessionmaker(engine)

    return args.func(args, sess)
