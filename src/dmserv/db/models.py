from typing import Iterable
from sqlalchemy import JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


type JsonValue = dict | list | str | int | bool


class GuildSetting(Base):
    __tablename__ = "discord_guild_settings"
    __table_args__ = (UniqueConstraint("guild_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String)
    value: Mapped[JsonValue] = mapped_column(JSON)


class GuildSettingsRepo:
    def __init__(self, sess: sessionmaker[Session]):
        self.sess = sess

    def has(self, guild: int, setting: str) -> bool:
        with self.sess.begin() as sess:
            return (
                sess.query(GuildSetting)
                .filter(GuildSetting.guild_id == guild, GuildSetting.name == setting)
                .count()
                > 0
            )

    def get(self, guild: int, setting: str) -> JsonValue:
        with self.sess.begin() as sess:
            return (
                sess.query(GuildSetting)
                .filter(GuildSetting.guild_id == guild, GuildSetting.name == setting)
                .one()
                .value
            )

    def get_multi(self, guilds: Iterable[int], setting: str) -> dict[int, JsonValue]:
        with self.sess.begin() as sess:
            return {
                s.guild_id: s.value
                for s in sess.query(GuildSetting)
                .filter(GuildSetting.guild_id.in_(guilds), GuildSetting.name == setting)
                .all()
            }

    def get_all(self, setting: str) -> dict[int, JsonValue]:
        with self.sess.begin() as sess:
            return {
                s.guild_id: s.value
                for s in sess.query(GuildSetting)
                .filter(GuildSetting.name == setting)
                .all()
            }

    def set(self, guild: int, setting: str, value: JsonValue) -> None:
        with self.sess.begin() as sess:
            gs = (
                sess.query(GuildSetting)
                .filter(GuildSetting.guild_id == guild, GuildSetting.name == value)
                .one_or_none()
            )
            if gs is None:
                gs = GuildSetting(guild_id=guild, name=setting)

            gs.value = value
            sess.add(gs)
