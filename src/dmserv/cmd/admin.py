import argparse
import sqlalchemy


def register_admin_subcommand(parser: argparse.ArgumentParser):
    parser.set_defaults(func=main)


def main(args: argparse.Namespace, engine: sqlalchemy.Engine) -> int:
    return 0
