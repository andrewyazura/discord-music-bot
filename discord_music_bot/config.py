from environs import Env

env = Env()
env.read_env(override=True)


with env.prefixed("DISCORD_"):
    BOT_TOKEN: str = env.str("BOT_TOKEN")
    COMMAND_PREFIX: str = env.str("COMMAND_PREFIX")
    GUILD_IDS: list[int] = env.list("GUILD_IDS", subcast=int)

with env.prefixed("WAVELINK_NODE_"):
    WAVELINK_CONFIG: dict = {
        "host": env.str("HOST"),
        "port": env.int("PORT"),
        "password": env.str("PASSWORD"),
    }

with env.prefixed("SPOTIFY_"):
    SPOTIFY_CONFIG: dict = {
        "client_id": env.str("CLIENT_ID"),
        "client_secret": env.str("CLIENT_SECRET"),
    }

YOUTUBE_SEARCH_LIMIT = env.int("YOUTUBE_SEARCH_LIMIT")

LOGGING_CONFIG: dict = env.json("LOGGING_CONFIG")
