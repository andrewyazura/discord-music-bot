import discord
import validators
import wavelink
from wavelink.ext import spotify

from discord_music_bot import config
from discord_music_bot.commands.base import BaseCog


class StreamingCommands(BaseCog):
    async def setup(self) -> None:
        await self.bot.wait_until_ready()

        await wavelink.NodePool.create_node(
            bot=self.bot,
            **config.WAVELINK_CONFIG,
            spotify_client=spotify.SpotifyClient(
                **config.SPOTIFY_CONFIG,
            ),
        )

    @discord.slash_command(
        name="yt",
        description="play audio from a YouTube video",
    )
    async def queue_youtube(
        self, ctx: discord.ApplicationContext, *, query: str
    ) -> None:
        player: wavelink.Player = ctx.voice_client

        if not validators.url(query):
            await self.search(ctx, query=query)
            return

        player.queue.put(
            await wavelink.YouTubeTrack.search(query=query, return_first=True)
        )

    async def search(
        self, ctx: discord.ApplicationContext, *, query: str
    ) -> None:
        embed = discord.Embed(
            title=f"Resuls for {query}:", colour=discord.Colour.random()
        )

        tracks = await wavelink.YouTubeTrack.search(query=query)
        for i, track in zip(range(config.YOUTUBE_SEARCH_LIMIT), tracks):
            embed.add_field(
                name=f"{i + 1}. **{track.title}**",
                value=f"by **{track.author}**",
            )

        await ctx.respond(embed=embed)

    @discord.slash_command(
        name="sp",
        description="play spotify tracks, playlists and albums from a URL",
    )
    async def queue_spotify(
        self, ctx: discord.ApplicationContext, *, url: str
    ) -> None:
        player: wavelink.Player = ctx.voice_client

        if not validators.url(url):
            await ctx.respond("Invalid URL provided")
            return

        decoded = spotify.decode_url(url)
        if decoded is None:
            await ctx.respond("Invalid URL provided")
            return

        search_type = decoded["type"]
        query = decoded["id"]

        if search_type in (
            spotify.SpotifySearchType.album,
            spotify.SpotifySearchType.playlist,
        ):
            await ctx.respond("Loading tracks into the queue")

            async for partial in spotify.SpotifyTrack.iterator(
                query=query, partial_tracks=True, type=search_type
            ):
                player.queue.put(partial)
                await ctx.send(f"**{partial.title}** added to queue")

            await ctx.send(
                f"Loading done. Items in queue: {len(player.queue)}"
            )

        elif search_type == spotify.SpotifySearchType.track:
            track = await spotify.SpotifyTrack.search(
                query=query, type=search_type, return_first=True
            )
            player.queue.put(track)
            await ctx.respond(f"**{track.title}** added to queue")

        else:
            self.logger.error(
                f"Couldn't play spotify track: "
                f"url={url}, search_type={search_type}, query={query}"
            )
            await ctx.respond("Something went wrong")

    @queue_youtube.before_invoke
    @queue_spotify.before_invoke
    async def ensure_voice_channel(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        author_voice = ctx.author.voice
        if not author_voice:
            raise discord.ApplicationCommandError(
                "User isn't in voice channel"
            )

        if not ctx.voice_client:
            await author_voice.channel.connect(cls=wavelink.Player)
            return

        if author_voice.channel != ctx.voice_client.channel:
            raise discord.ApplicationCommandError(
                "User is in a different channel"
            )

    @queue_youtube.after_invoke
    @queue_spotify.after_invoke
    async def start_playing(self, ctx: discord.ApplicationContext) -> None:
        player: wavelink.Player = ctx.voice_client

        if player.is_playing():
            return

        if player.queue.is_empty:
            return

        if next_item := player.queue.get():
            await player.play(next_item)
            await ctx.send(f"Playing **{next_item.title}**")

    @discord.Cog.listener()
    async def on_wavelink_track_end(
        self, player: wavelink.Player, track: wavelink.Track, reason: str
    ) -> None:
        self.logger.info(f"track {track} finished playing, because {reason}")

        if next_item := player.queue.get():
            await player.play(next_item)
