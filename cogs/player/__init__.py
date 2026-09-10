import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import shutil
import time
import os
import yt_dlp
from database import supabase

class Track:
    def __init__(self, url, title, thumbnail, duration, duration_str, provider="desconhecido"):
        self.url = url
        self.title = title
        self.thumbnail = thumbnail
        self.duration = duration
        self.duration_str = duration_str
        self.provider = provider

def formatDuration(seconds):
    if not seconds:
        return "0:00"
    secs = int(seconds)
    mins = secs // 60
    remaining = secs % 60
    return f"{mins}:{remaining:02d}"

def formatDurationFull(seconds):
    if not seconds:
        return "0:00"
    secs = int(seconds)
    hours = secs // 3600
    mins = (secs % 3600) // 60
    remaining = secs % 60
    if hours > 0:
        return f"{hours}:{mins:02d}:{remaining:02d}"
    return f"{mins}:{remaining:02d}"

def progress_bar(position, duration, length=20):
    if not duration or duration <= 0:
        return "[ — ]"
    ratio = min(position / duration, 1.0)
    filled = int(ratio * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"


class _NullLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


_COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cookies.txt")


def _yt_opts():
    opts = BASE_YDL_OPTIONS.copy()
    if os.path.exists(_COOKIES_FILE):
        opts['cookiefile'] = _COOKIES_FILE
    return opts

BASE_YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'noprogress': True,
    'ignoreerrors': True,
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
    'socket_timeout': 15,
    'concurrent_fragment_downloads': 1,
    'js_runtimes': {'node': {}},
    'logger': _NullLogger(),
}

async def search_and_extract_stream(query):
    loop = asyncio.get_running_loop()

    if query.startswith("http"):
        configs = [{'opts': _yt_opts(), 'target': query, 'name': 'Link Direto'}]
    else:
        yt_mobile_opts = _yt_opts()
        yt_mobile_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'ios']}}

        yt_tv_opts = _yt_opts()
        yt_tv_opts['extractor_args'] = {'youtube': {'player_client': ['tvhtml5', 'web_embedded']}}

        sc_opts = _yt_opts()

        configs = [
            {'opts': yt_mobile_opts, 'target': f"ytsearch1:{query}", 'name': 'YouTube (Mobile)'},
            {'opts': yt_tv_opts, 'target': f"ytsearch1:{query}", 'name': 'YouTube (TV)'},
            {'opts': sc_opts, 'target': f"scsearch1:{query}", 'name': 'SoundCloud'},
        ]

    for config in configs:
        opts = config['opts']
        target = config['target']
        provider_name = config['name']

        def _try_extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(target, download=False)
                if not info:
                    return None

                entries = info.get('entries', [info])
                for entry in entries:
                    if not entry:
                        continue

                    stream_url = entry.get('url')
                    webpage_url = entry.get('webpage_url') or target
                    title = entry.get('title', 'Música')
                    duration = entry.get('duration', 0)
                    thumbnail = entry.get('thumbnail', '')

                    if not stream_url:
                        continue

                    if not stream_url.startswith("http"):
                        stream_url = ydl.url_or_none(stream_url) or entry.get('url')

                    if stream_url and stream_url.startswith("http"):
                        entry_id = entry.get('id', '')
                        if entry_id and ('youtube.com' in webpage_url or 'youtu.be' in webpage_url):
                            canonical_url = f"https://youtu.be/{entry_id}"
                        elif 'soundcloud.com' in (webpage_url or ''):
                            canonical_url = webpage_url
                        else:
                            canonical_url = webpage_url or target
                        return {
                            'stream_url': stream_url,
                            'webpage_url': canonical_url,
                            'title': title,
                            'duration': duration,
                            'duration_str': formatDuration(duration),
                            'thumbnail': thumbnail,
                            'provider': provider_name
                        }
                return None

        try:
            result = await loop.run_in_executor(None, _try_extract)
            if result:
                print(f"[MUSICA] Sucesso via: {provider_name}")
                return result
        except Exception as e:
            print(f"[MUSICA] Falha em {provider_name}, a tentar próxima fonte... ({e})")
            continue

    return None


def check_ffmpeg():
    if not shutil.which("ffmpeg"):
        print("🚨 [MUSICA] FFmpeg não encontrado no PATH! Os comandos de música não irão funcionar.")
        return False
    return True


def ler_config(guild_id):
    try:
        db = supabase.table("musica_config").select("*").eq("guilda_id", str(guild_id)).execute()
        return db.data[0] if db.data else {}
    except Exception:
        return {}


class MusicPlayer:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.queue = []
        self.current_track = None
        self.volume = 1.0
        self.voice_client = None
        self.audio_source = None
        self.dj_id = None
        self.loop_current = False
        self.funk_mode = False
        self._suppress_after = False
        self.play_started_at = None
        self._paused_at = None

    def add_track(self, track):
        self.queue.append(track)

    def get_next_track(self):
        if len(self.queue) > 0:
            self.current_track = self.queue.pop(0)
            return self.current_track
        self.current_track = None
        return None

    def clear(self):
        self.queue.clear()
        self.current_track = None
        self.funk_mode = False


class Musica(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def cog_unload(self):
        for player in self.players.values():
            try:
                coro = player.voice_client.disconnect()
                if coro:
                    asyncio.ensure_future(coro)
            except Exception:
                pass

    def get_player(self, guild_id):
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(guild_id)
        return self.players[guild_id]

    def _music_channel(self, guild):
        cfg = ler_config(guild.id)
        canal_id = cfg.get("canal_comandos") if cfg else None
        if canal_id and str(canal_id).isdigit():
            return guild.get_channel(int(canal_id))
        return None

    def _is_management(self, interaction):
        if interaction.user.id == interaction.guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        cfg = ler_config(interaction.guild_id)
        cargo_id = cfg.get("cargo_musica_id") if cfg else None
        if cargo_id and str(cargo_id).isdigit():
            role = interaction.guild.get_role(int(cargo_id))
            if role and role in interaction.user.roles:
                return True
        return False

    def _is_dj(self, interaction):
        player = self.get_player(interaction.guild_id)
        if player.dj_id and interaction.user.id == player.dj_id:
            return True
        return self._is_management(interaction)

    async def _check_canal(self, interaction):
        cfg = ler_config(interaction.guild_id)
        if not cfg or str(cfg.get("canal_comandos")) == "None":
            return True

        canal_comandos = cfg.get("canal_comandos")
        if not canal_comandos:
            return True

        if str(interaction.channel_id) == str(canal_comandos):
            return True

        if self._is_management(interaction):
            return True

        canal = None
        if str(canal_comandos).isdigit():
            canal = interaction.guild.get_channel(int(canal_comandos))

        nome_canal = canal.mention if canal else "canal de música configurado"
        await self._responder(
            interaction,
            content=f"❌ Usa os comandos de música em {nome_canal}.",
            ephemeral=True
        )
        return False

    async def _check_dj(self, interaction):
        player = self.get_player(interaction.guild_id)
        if not player.voice_client or not player.voice_client.is_connected():
            await self._responder(
                interaction,
                content="❌ O bot não está conectado a nenhum canal de voz.",
                ephemeral=True
            )
            return False

        if not self._is_dj(interaction):
            await self._responder(
                interaction,
                content="⛔ Apenas o DJ, dono, admin ou cargo de música podem usar este comando.",
                ephemeral=True
            )
            return False
        return True

    async def _responder(self, interaction, *, content=None, embed=None, view=None, ephemeral=True):
        def _kwargs():
            kw = {"ephemeral": ephemeral}
            if content is not None:
                kw["content"] = content
            if embed is not None:
                kw["embed"] = embed
            if view is not None:
                kw["view"] = view
            return kw

        def _m_kwargs():
            kw = {}
            if content is not None:
                kw["content"] = content
            if embed is not None:
                kw["embed"] = embed
            if view is not None:
                kw["view"] = view
            return kw

        # Respostas efêmeras (erros/confirmações) SEMPRE vão para o canal onde o comando foi usado
        if ephemeral:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(**_kwargs())
                else:
                    await interaction.followup.send(**_kwargs())
            except discord.HTTPException:
                pass
            return

        # Respostas públicas (embeds) → roteia para o canal de música se configurado
        guild = interaction.guild
        music_channel = self._music_channel(guild)

        if music_channel and music_channel.id != interaction.channel_id:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("✅ Mensagem publicada no canal de música.", ephemeral=True)
                else:
                    await interaction.followup.send("✅ Mensagem publicada no canal de música.", ephemeral=True)
            except Exception:
                pass
            try:
                await music_channel.send(**_m_kwargs())
            except Exception as e:
                print(f"[MUSICA] Erro ao postar no canal de música: {e}")
            return

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(**_kwargs())
            else:
                await interaction.followup.send(**_kwargs())
        except discord.HTTPException:
            pass

    async def _anunciar_dj(self, interaction, reason="took over"):
        player = self.get_player(interaction.guild_id)
        guild = interaction.guild
        music_channel = self._music_channel(guild)
        if not music_channel or not player.dj_id:
            return
        dj_member = guild.get_member(player.dj_id)
        if dj_member:
            try:
                await music_channel.send(f"🎵 **DJ atual: {dj_member.mention}** (assumiu via `{reason}`)", delete_after=60)
            except Exception:
                pass

    async def connect_voice(self, interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await self._responder(interaction, content="❌ Tens de estar num canal de voz!", ephemeral=True)
            return None

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        if vc:
            if vc.channel.id != channel.id:
                await vc.move_to(channel)
        else:
            try:
                vc = await channel.connect(reconnect=True, timeout=30.0, self_deaf=True)
            except discord.ClientException:
                vc = interaction.guild.voice_client

        player = self.get_player(interaction.guild_id)
        player.voice_client = vc
        return vc

    async def start_playing(self, guild_id):
        player = self.get_player(guild_id)
        vc = player.voice_client

        if not player.current_track or not vc:
            return

        media_data = await search_and_extract_stream(player.current_track.url)
        if not media_data:
            print(f"[MUSICA] Nenhuma fonte extraiu: {player.current_track.title}. Passando à próxima...")
            await self.play_next(guild_id)
            return

        stream_url = media_data['stream_url']

        ffmpeg_options = {
            'before_options': '-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        try:
            raw_source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options)
            transformer = discord.PCMVolumeTransformer(raw_source, volume=player.volume)
            player.audio_source = transformer

            guild = self.bot.get_guild(int(guild_id))
            music_channel = self._music_channel(guild) if guild else None

            def after_playing(error):
                if error:
                    print(f"[MUSICA] Erro na reprodução: {error}")
                if player._suppress_after:
                    player._suppress_after = False
                    return
                try:
                    fut = asyncio.run_coroutine_threadsafe(self.on_track_end(guild_id), self.bot.loop)
                    fut.result(timeout=5)
                except Exception as ex:
                    print(f"[MUSICA] Erro no after callback: {ex}")

            if vc.is_playing() or vc.is_paused():
                player._suppress_after = True
                vc.stop()

            vc.play(transformer, after=after_playing)
            player.play_started_at = time.time()
            player._paused_at = None
            print(f"[MUSICA] A tocar [{media_data['provider']}]: {player.current_track.title}")

            embed = discord.Embed(
                title="🎵 A Tocar Agora",
                description=f"[{player.current_track.title}]({player.current_track.url})",
                color=discord.Color.green()
            )
            embed.add_field(name="Fonte", value=player.current_track.provider, inline=True)
            embed.add_field(name="Duração", value=player.current_track.duration_str, inline=True)
            dj_display = "ninguém"
            g_obj = self.bot.get_guild(int(guild_id))
            if player.dj_id and g_obj:
                dj_m = g_obj.get_member(player.dj_id)
                if dj_m:
                    dj_display = dj_m.mention
            embed.add_field(name="🎧 DJ Atual", value=dj_display, inline=True)
            if player.current_track.thumbnail:
                embed.set_thumbnail(url=player.current_track.thumbnail)
            embed.set_footer(text=f"S.art Engine • Música • Volume: {int(player.volume * 100)}%")

            if music_channel:
                await music_channel.send(embed=embed)
            elif vc and vc.channel:
                guild = self.bot.get_guild(int(guild_id))
                if guild:
                    for ch in guild.text_channels:
                        if ch.permissions_for(guild.me).send_messages:
                            await ch.send(embed=embed)
                            break

        except Exception as e:
            print(f"[MUSICA] Erro FFmpeg: {e}")
            player._suppress_after = False
            await self.play_next(guild_id)

    async def on_track_end(self, guild_id):
        player = self.get_player(guild_id)
        if player.loop_current and player.current_track:
            await self.start_playing(guild_id)
        elif player.funk_mode:
            await self._play_next_funk(guild_id)
        else:
            await self.play_next(guild_id)

    async def _play_next_funk(self, guild_id):
        player = self.get_player(guild_id)
        vc = player.voice_client
        if not vc or not vc.is_connected():
            player.funk_mode = False
            return

        guild = self.bot.get_guild(int(guild_id))
        searches = player.funk_searches or []

        for attempt in range(3):
            query = random.choice(searches) if searches else None
            if not query:
                break
            results = await search_and_extract_stream(query)
            if results:
                track = Track(
                    url=results['webpage_url'],
                    title=results['title'],
                    thumbnail=results['thumbnail'],
                    duration=results['duration'],
                    duration_str=results['duration_str'],
                    provider=results['provider']
                )
                player.current_track = track
                try:
                    await self.start_playing(guild_id)
                except Exception as e:
                    print(f"[MUSICA] Erro ao tocar próximo funk: {e}")
                    continue
                music_channel = self._music_channel(guild) if guild else None
                if music_channel:
                    embed = discord.Embed(
                        title="🎧 Próximo Funk",
                        description=f"▶️ **{track.title}** — no ar!",
                        color=discord.Color.dark_red()
                    )
                    try:
                        await music_channel.send(embed=embed)
                    except Exception:
                        pass
                return

        player.funk_mode = False
        try:
            if vc and vc.is_connected():
                await vc.disconnect()
        except Exception:
            pass
        player.voice_client = None
        player.current_track = None
        player.dj_id = None
        print(f"[MUSICA] Funk mode encerrado (pesquisas esgotadas).")

    async def play_next(self, guild_id):
        player = self.get_player(guild_id)
        next_track = player.get_next_track()

        if next_track:
            await self.start_playing(guild_id)
        else:
            vc = player.voice_client
            if vc and vc.is_connected():
                try:
                    await vc.disconnect()
                except Exception:
                    pass
            player.voice_client = None
            player.current_track = None
            player.funk_mode = False
            player.dj_id = None
            print(f"[MUSICA] Fila esgotada. Desconectado do servidor {guild_id}.")

    # --- COMANDOS (/) ---

    @app_commands.command(name="play", description="Toca uma música imediatamente (troca a atual se estiver a tocar)")
    async def play_cmd(self, interaction: discord.Interaction, pesquisa: str):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return

        vc = await self.connect_voice(interaction)
        if not vc:
            return

        player = self.get_player(interaction.guild_id)

        is_active = vc.is_playing() or vc.is_paused()
        if is_active:
            if not self._is_dj(interaction):
                await self._responder(
                    interaction,
                    content="⛔ Apenas o DJ ou cargo de música pode trocar de faixa enquanto algo toca.",
                    ephemeral=True
                )
                return

        player.dj_id = interaction.user.id
        if is_active:
            await self._anunciar_dj(interaction, reason="play")

        results = await search_and_extract_stream(pesquisa)

        if not results:
            await self._responder(interaction, content="❌ Não encontrei a música em nenhuma plataforma!", ephemeral=True)
            return

        track = Track(
            url=results['webpage_url'],
            title=results['title'],
            thumbnail=results['thumbnail'],
            duration=results['duration'],
            duration_str=results['duration_str'],
            provider=results['provider']
        )

        player.clear()
        player.current_track = track
        await self.start_playing(interaction.guild_id)
        if self._is_outside_channel(interaction):
            await self._responder(interaction, content="✅ A música foi iniciada no canal de música.", ephemeral=True)

    @app_commands.command(name="add_fila", description="Adiciona uma música à fila sem parar a atual")
    async def add_fila_cmd(self, interaction: discord.Interaction, pesquisa: str):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return

        vc = await self.connect_voice(interaction)
        if not vc:
            return

        player = self.get_player(interaction.guild_id)
        results = await search_and_extract_stream(pesquisa)

        if not results:
            await self._responder(interaction, content="❌ Não encontrei a música!", ephemeral=True)
            return

        track = Track(
            url=results['webpage_url'],
            title=results['title'],
            thumbnail=results['thumbnail'],
            duration=results['duration'],
            duration_str=results['duration_str'],
            provider=results['provider']
        )

        is_active = vc.is_playing() or vc.is_paused()
        if not is_active:
            player.dj_id = interaction.user.id
            player.current_track = track
            await self.start_playing(interaction.guild_id)
            await self._anunciar_dj(interaction, reason="add_fila")
            if self._is_outside_channel(interaction):
                await self._responder(interaction, content="✅ Música iniciada no canal de música.", ephemeral=True)
            return

        player.add_track(track)
        embed = discord.Embed(
            title="📥 Adicionado à Fila",
            description=f"[{track.title}]({track.url})",
            color=discord.Color.blue()
        )
        embed.add_field(name="Posição na Fila", value=f"#{len(player.queue)}", inline=True)
        await self._responder(interaction, embed=embed, ephemeral=False)

    @app_commands.command(name="funk", description="Toca um funk imediatamente")
    async def funk_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return

        vc = await self.connect_voice(interaction)
        if not vc:
            return

        player = self.get_player(interaction.guild_id)

        is_active = vc.is_playing() or vc.is_paused()
        if is_active:
            if not self._is_dj(interaction):
                await self._responder(
                    interaction,
                    content="⛔ Apenas o DJ ou cargo de música pode trocar de faixa enquanto algo toca.",
                    ephemeral=True
                )
                return

        player.dj_id = interaction.user.id

        pesquisas_funk = [
            # --- Funk SP & Mandelão ---
            "set funk sp 2026",
            "funk mandelão ritmado",
            "mandelão pesado 2026",
            "funk automotivo sp",
            "funk grave forte bass",
            "funk sp lançamento 2026",
            "funk de bh vs sp",
            "set dj boy 2026",
            "set dj victor 2026",
            "set dj blake 2026",
            "funk paulista pesado",
            "mandelão 150bpm sp",
            "funk 200bpm pesado",
            "funk pancadão grave",
            "funk subwoofers automotivo",
            "funk para rachar som",
            "set mandelão zika",
            "funk pesado de quebrada",
            "mandelão rave funk",
            "funk fluxo de rua",

            # --- Funk RJ, MTG & 150BPM ---
            "funk rj mtg 2026",
            "mtg funk rj tik tok",
            "funk 150bpm rj relíquia",
            "funk tamborzinho rj",
            "mtg bh rj misturado",
            "funk proibidão rj relíquia",
            "set mtg rj 2026",
            "funk baile da gaiola",
            "funk baile da penha",
            "mtg viral 2026",
            "funk mtg montagem rj",
            "mtg viciante tik tok",
            "funk rj ritmado 2026",
            "funk descalço 150bpm",
            "montagem rj funk grave",
            "funk acelerado 150bpm",
            "funk rj clássico relíquia",
            "set mtg funk brasil",
            "funk rj melody clássico",
            "funk charme rj",

            # --- Funk BH & Ritmadas ---
            "funk ritmada bh 2026",
            "set funk bh ritmado",
            "funk bh som de mala",
            "funk bh grave estourado",
            "set dj arana bh",
            "funk ritmo louco bh",
            "funk bh montagem rave",
            "funk ritmada agressiva",
            "set funk bh 2026",
            "funk bh viral reels",
            "funk beat bh ritmado",
            "funk bh automotivo mala",
            "funk minas gerais ritmada",
            "funk bh caixa de som",
            "set ritmada dos crias",
            "funk bh de quebrada",
            "funk bh bass boosted",
            "funk bh bruxaria",
            "funk bh sequência de vuc vuc",
            "set bh funk estourado",

            # --- Funk Consciente & Visão ---
            "funk consciente 2026",
            "funk visão de cria",
            "set funk consciente 2026",
            "funk mc hariel visão",
            "funk mc ryan sp consciente",
            "funk mc ig visão 2026",
            "funk mc paulin da capital",
            "funk superação e fé",
            "funk consciente relíquia",
            "funk história de vida",
            "set visão de futuro funk",
            "funk motivacional 2026",
            "funk letras fortes visão",
            "funk mc leozinho zsh",
            "funk consciente sp rj",
            "set mc nego do borel visao",
            "funk de quebrada superação",
            "funk mc marks consciente",
            "funk mensagem de fé",
            "set consciente os melhores",

            # --- Eletrofunk & Rave Funk ---
            "eletrofunk automotivo 2026",
            "rave funk 2026",
            "funk bruxaria sp",
            "eletrofunk som de mala",
            "funk psytrance remix",
            "rave funk grave forte",
            "eletrofunk goiânia 2026",
            "funk bruxaria ritmado",
            "set eletrofunk 2026",
            "rave funk tiktok viral",
            "funk fritação rave",
            "eletrofunk bassboosted",
            "funk eletrónico automotivo",
            "funk grave rave sp",
            "set bruxaria mandelão",
            "funk eletro grave pesado",
            "eletrofunk car audio",
            "funk alok remix estilo",
            "funk beat rave alucinante",
            "set eletrorave funk",

            # --- Funk Relíquia & Nostalgia ---
            "funk relíquia anos 2000",
            "funk ostentação 2014",
            "funk das antigas rj",
            "set funk relíquia zika",
            "funk mc daleste relíquia",
            "funk mc zói de gato",
            "funk mc guimé ostentação",
            "funk furacão 2000 clássicos",
            "funk antigos sucessos",
            "funk nostalgico 2012",
            "funk mc rodolfinho relíquia",
            "funk mc lon relíquia",
            "funk mc pedrinho antigo",
            "funk mc kevin relíquia",
            "funk passinho do romano",
            "set nostalgia funk sp",
            "funk furacão 2000 prisioneiro",
            "funk antigamente rj sp",
            "funk baile de corredor",
            "funk clássicos dos anos 2000",

            # --- Funk Tiktok, MTG Viral & TrapFunk ---
            "funk viral tiktok 2026",
            "mtg tiktok funk de cria",
            "funk trap br 2026",
            "trapfunk pesado bass",
            "funk slowed and reverb",
            "funk phonk brasil",
            "funk de biqueira ritmado",
            "set mtg tik tok brasil",
            "funk remix sertanejo mtg",
            "funk trend tiktok 2026",
            "funk remix piseiro mtg",
            "funk novidades do mês",
            "set funk bombando agora",
            "funk dancinha tiktok 2026",
            "funk montagem agressiva",
            "funk beat rj viral",
            "funk automotivo montagem",
            "set trap funk insano",
            "funk estourado nas redes",
            "funk hit do momento 2026"
        ]

        query = random.choice(pesquisas_funk)
        results = await search_and_extract_stream(query)

        if not results:
            await self._responder(interaction, content="❌ Não consegui carregar o funk!", ephemeral=True)
            return

        track = Track(
            url=results['webpage_url'],
            title=results['title'],
            thumbnail=results['thumbnail'],
            duration=results['duration'],
            duration_str=results['duration_str'],
            provider=results['provider']
        )

        player.clear()
        player.current_track = track
        player.funk_mode = True
        player.loop_current = False
        player.funk_searches = pesquisas_funk
        await self.start_playing(interaction.guild_id)
        await self._anunciar_dj(interaction, reason="funk")
        if self._is_outside_channel(interaction):
            await self._responder(interaction, content="✅ O funk foi iniciado no canal de música.", ephemeral=True)

    @app_commands.command(name="pular", description="Pula a música atual para a próxima da fila")
    async def pular_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return
        if not await self._check_dj(interaction):
            return

        player = self.get_player(interaction.guild_id)
        vc = player.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await self._responder(interaction, content="⏭️ Música pulada!", ephemeral=True)
        else:
            await self._responder(interaction, content="❌ Não há nenhuma música a tocar para pular.", ephemeral=True)

    @app_commands.command(name="pause", description="Pausa a música atual")
    async def pause_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return
        if not await self._check_dj(interaction):
            return

        player = self.get_player(interaction.guild_id)
        vc = player.voice_client
        if vc and vc.is_playing():
            vc.pause()
            player._paused_at = time.time()
            await self._responder(interaction, content="⏸️ Música pausada!", ephemeral=True)
        else:
            await self._responder(interaction, content="❌ Não há nenhuma música a tocar.", ephemeral=True)

    @app_commands.command(name="resume", description="Retoma a música pausada")
    async def resume_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return
        if not await self._check_dj(interaction):
            return

        player = self.get_player(interaction.guild_id)
        vc = player.voice_client
        if vc and vc.is_paused():
            vc.resume()
            if player.play_started_at and player._paused_at:
                player.play_started_at += (time.time() - player._paused_at)
            player._paused_at = None
            await self._responder(interaction, content="▶️ Música retomada!", ephemeral=True)
        else:
            await self._responder(interaction, content="❌ A música não está pausada.", ephemeral=True)

    @app_commands.command(name="volume", description="Define o volume (1-100)")
    async def volume_cmd(self, interaction: discord.Interaction, percent: int):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return
        if not await self._check_dj(interaction):
            return

        if percent < 0 or percent > 100:
            await self._responder(interaction, content="❌ Volume deve ser entre 0 e 100.", ephemeral=True)
            return

        player = self.get_player(interaction.guild_id)
        player.volume = percent / 100.0
        if player.audio_source:
            player.audio_source.volume = player.volume

        await self._responder(interaction, content=f"🔊 Volume definido para **{percent}%**.", ephemeral=True)

    @app_commands.command(name="np", description="Mostra a música atual")
    async def np_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return

        player = self.get_player(interaction.guild_id)
        if not player.current_track or not player.voice_client:
            await self._responder(interaction, content="📭 Nenhuma música a tocar agora.", ephemeral=True)
            return

        vc = player.voice_client
        if vc and vc.is_playing() and player.play_started_at:
            position = time.time() - player.play_started_at
        elif player.play_started_at and player._paused_at:
            position = player._paused_at - player.play_started_at
        else:
            position = 0
        bar = progress_bar(int(position), player.current_track.duration)
        elapsed = formatDurationFull(int(position))
        total = player.current_track.duration_str

        embed = discord.Embed(
            title="🎧 Agora a Tocar",
            description=f"[{player.current_track.title}]({player.current_track.url})",
            color=discord.Color.green()
        )
        embed.add_field(name="Progresso", value=f"{bar}\n`{elapsed}` / `{total}`", inline=False)
        embed.add_field(name="Fonte", value=player.current_track.provider, inline=True)
        embed.add_field(name="Volume", value=f"{int(player.volume * 100)}%", inline=True)
        if player.loop_current:
            embed.add_field(name="Loop", value="🔁 Ativado", inline=True)
        if player.funk_mode:
            embed.add_field(name="Modo", value="🎷 Funk Loop Ativo", inline=True)
        if player.current_track.thumbnail:
            embed.set_thumbnail(url=player.current_track.thumbnail)
        embed.set_footer(text="S.art Engine • Música")
        await self._responder(interaction, embed=embed, ephemeral=False)

    @app_commands.command(name="fila", description="Mostra a lista de músicas na fila")
    async def fila_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return

        player = self.get_player(interaction.guild_id)
        if not player.queue and not player.current_track:
            await self._responder(interaction, content="📭 A fila está vazia!", ephemeral=True)
            return

        desc = ""
        if player.current_track:
            desc += f"**A Tocar:** [{player.current_track.title}]({player.current_track.url})\n"
            if player.loop_current:
                desc += "🔁 *(Loop ativado)*\n"
            desc += "\n"

        if player.queue:
            desc += "**Próximas Músicas:**\n"
            for idx, track in enumerate(player.queue[:10], start=1):
                desc += f"`{idx}.` [{track.title}]({track.url})\n"
            if len(player.queue) > 10:
                desc += f"\n*...e mais {len(player.queue) - 10} músicas.*"

        embed = discord.Embed(title="📜 Fila de Músicas", description=desc, color=discord.Color.purple())
        if player.current_track and player.current_track.thumbnail:
            embed.set_thumbnail(url=player.current_track.thumbnail)
        embed.set_footer(text=f"S.art Engine • Fila • {len(player.queue)} na lista")
        await self._responder(interaction, embed=embed, ephemeral=False)

    @app_commands.command(name="stop", description="Para a música, limpa a fila e desconecta")
    async def stop_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return
        if not await self._check_dj(interaction):
            return

        player = self.get_player(interaction.guild_id)
        player.clear()
        if player.voice_client:
            try:
                await player.voice_client.disconnect()
            except Exception:
                pass
            player.voice_client = None
        player.dj_id = None
        await self._responder(interaction, content="⏹️ Música parada e fila limpa!", ephemeral=True)

    @app_commands.command(name="disconnect", description="Desconecta o bot do canal de voz")
    async def disconnect_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return
        if not await self._check_dj(interaction):
            return

        player = self.get_player(interaction.guild_id)
        player.clear()
        if player.voice_client:
            try:
                await player.voice_client.disconnect()
            except Exception:
                pass
            player.voice_client = None
        player.dj_id = None
        await self._responder(interaction, content="👋 Desconectado do canal de voz.", ephemeral=True)

    @app_commands.command(name="clear", description="Limpa a fila mantendo a música atual")
    async def clear_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return
        if not await self._check_dj(interaction):
            return

        player = self.get_player(interaction.guild_id)
        player.queue.clear()
        await self._responder(interaction, content="🧹 Fila limpa! (música atual preservada).", ephemeral=True)

    @app_commands.command(name="loop", description="Ativa/desativa a repetição da música atual")
    async def loop_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return
        if not await self._check_dj(interaction):
            return

        player = self.get_player(interaction.guild_id)
        if not player.current_track:
            await self._responder(interaction, content="❌ Nenhuma música a tocar para fazer loop.", ephemeral=True)
            return

        player.loop_current = not player.loop_current
        status = "ativado 🔁" if player.loop_current else "desativado"
        await self._responder(interaction, content=f"🔁 Loop **{status}** para: `{player.current_track.title}`", ephemeral=True)

    @app_commands.command(name="shuffle", description="Embaralha a fila de músicas")
    async def shuffle_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=self._is_outside_channel(interaction))

        if not await self._check_canal(interaction):
            return
        if not await self._check_dj(interaction):
            return

        player = self.get_player(interaction.guild_id)
        if len(player.queue) < 2:
            await self._responder(interaction, content="❌ Necessário 2+ músicas na fila para embaralhar.", ephemeral=True)
            return

        random.shuffle(player.queue)
        await self._responder(interaction, content="🔀 Fila embaralhada!", ephemeral=True)

    # --- LISTENER: limpeza de estado de voz ---

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        try:
            guild = member.guild
            player = self.players.get(guild.id)
            if not player:
                return

            # Bot left or was moved
            if member.id == self.bot.user.id:
                if after.channel is None:
                    player.voice_client = None
                    player.current_track = None
                    player.queue.clear()
                    player.funk_mode = False
                    player.dj_id = None
                    player.play_started_at = None
                    player._paused_at = None
                    print(f"[MUSICA] Bot desconectado de {guild.name}.")
                else:
                    player.voice_client = guild.voice_client
                return

            vc = player.voice_client
            if not vc or not vc.is_connected() or not vc.channel:
                return

            # Member left a VC where the bot was present
            if before.channel and before.channel.id == vc.channel.id and after.channel != vc.channel:
                human_members = [
                    m for m in vc.channel.members
                    if not m.bot and m.id != self.bot.user.id
                ]

                if not human_members:
                    player.dj_id = None
                    player.clear()
                    try:
                        await vc.disconnect()
                    except Exception:
                        pass
                    player.voice_client = None
                    print(f"[MUSICA] VC vazio em {guild.name}. Bot desconectado.")
                    return

                if member.id == player.dj_id:
                    player.dj_id = human_members[0].id
                    music_channel = self._music_channel(guild)
                    if music_channel:
                        embed = discord.Embed(
                            title="🎵 Novo DJ",
                            description=f"**{human_members[0].display_name}** é o novo líder da música.",
                            color=discord.Color.gold()
                        )
                        try:
                            await music_channel.send(embed=embed)
                        except Exception:
                            pass
        except Exception as e:
            print(f"[MUSICA] Erro no on_voice_state_update: {e}")

    def _is_outside_channel(self, interaction):
        """True se o comando foi usado fora do canal de música configurado (para defer ephemeral)."""
        cfg = ler_config(interaction.guild_id)
        if not cfg:
            return False
        canal_comandos = cfg.get("canal_comandos")
        if not canal_comandos:
            return False
        if str(interaction.channel_id) == str(canal_comandos):
            return False
        return True


async def setup(bot):
    check_ffmpeg()
    await bot.add_cog(Musica(bot))
