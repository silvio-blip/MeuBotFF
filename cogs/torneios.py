# cogs/torneios.py
import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime, timezone
from database import supabase

MODOS = {"solo": 1, "duo": 2, "trio": 3, "squad": 4}
MODOS_NOME = {"solo": "Solo (1v1)", "duo": "Duo (2v2)", "trio": "Trio (3v3)", "squad": "Squad (4v4)"}

# ============================================================
# MODAL CRIAR TORNEIO
# ============================================================
class ModalCriarTorneio(discord.ui.Modal, title='Criar Torneio'):
    nome = discord.ui.TextInput(label='Nome do Torneio', placeholder='Ex: Torneio S.art FF', required=True)
    data_inicio = discord.ui.TextInput(label='Data de Início (DD/MM/AAAA HH:MM)', placeholder='Ex: 25/12/2025 20:00', required=True)
    max_equipas = discord.ui.TextInput(label='Máximo de Equipas', placeholder='Ex: 8', required=True, default="8")
    premiacao = discord.ui.TextInput(label='Premiação', placeholder='Ex: 500 diamantes', required=True)
    modo = discord.ui.TextInput(label='Modo (solo/duo/trio/squad)', placeholder='Ex: duo', required=True, default="duo")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            data_obj = datetime.strptime(self.data_inicio.value.strip(), "%d/%m/%Y %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            return await interaction.response.send_message("❌ Formato de data inválido! Usa DD/MM/AAAA HH:MM.", ephemeral=True)
        
        modo = self.modo.value.strip().lower()
        if modo not in MODOS:
            return await interaction.response.send_message(f"❌ Modo inválido! Usa: {', '.join(MODOS.keys())}", ephemeral=True)
        
        try:
            max_e = int(self.max_equipas.value)
        except ValueError:
            return await interaction.response.send_message("❌ Número de equipas inválido!", ephemeral=True)
        
        if max_e < 2 or max_e > 32:
            return await interaction.response.send_message("❌ O máximo deve ser entre 2 e 32.", ephemeral=True)
        
        db_res = supabase.table("torneios").insert({
            "nome": self.nome.value,
            "data_inicio": data_obj.isoformat(),
            "formato": "single",
            "modo": modo,
            "max_participantes": max_e,
            "status": "inscrito",
            "criado_por": str(interaction.user.id),
            "guilda_id": str(interaction.guild_id),
            "premiacao": self.premiacao.value
        }).execute()
        
        torneio_id = db_res.data[0]["id"] if db_res.data else "?"
        tamanho = MODOS[modo]
        
        embed = discord.Embed(
            title=f"🏆 Torneio Criado: {self.nome.value}",
            description=(
                f"**ID:** `{torneio_id}`\n"
                f"**Modo:** {MODOS_NOME[modo]}\n"
                f"**Data:** <t:{int(data_obj.timestamp())}:F>\n"
                f"**Máximo:** {max_e} equipas\n"
                f"**Premiação:** {self.premiacao.value}\n\n"
                f"Para criar uma equipa:\n"
                f"`/torneio_equipa_criar {torneio_id} NomeEquipa @membro1 @membro2...`"
            ),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

# ============================================================
# VIEW APROVAÇÃO DE EQUIPA (DM)
# ============================================================
class ViewAprovacaoEquipa(discord.ui.View):
    def __init__(self, equipa_id: int, torneio_nome: str):
        super().__init__(timeout=None)
        self.equipa_id = equipa_id
        self.torneio_nome = torneio_nome

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success, custom_id="equipa_aprovar")
    async def btn_aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        db_membro = supabase.table("torneio_equipa_membros").select("*").eq("equipa_id", self.equipa_id).eq("usuario_id", user_id).execute()
        if not db_membro.data:
            return await interaction.response.send_message("❌ Não pertences a esta equipa.", ephemeral=True)
        
        if db_membro.data[0].get("aprovado"):
            return await interaction.response.send_message("✅ Já aprovaste anteriormente.", ephemeral=True)
        
        supabase.table("torneio_equipa_membros").update({"aprovado": True}).eq("equipa_id", self.equipa_id).eq("usuario_id", user_id).execute()
        
        # Verificar se todos aprovaram
        db_equipa = supabase.table("torneio_equipas").select("*").eq("id", self.equipa_id).execute()
        if db_equipa.data:
            capitao_id = db_equipa.data[0]["capitao_id"]
            nome_equipa = db_equipa.data[0]["nome_equipa"]
            
            db_todos = supabase.table("torneio_equipa_membros").select("*").eq("equipa_id", self.equipa_id).execute()
            todos_aprovaram = all(m.get("aprovado") for m in db_todos.data) if db_todos.data else False
            
            # Avisar capitão
            try:
                capitao = await interaction.client.fetch_user(int(capitao_id))
                if todos_aprovaram:
                    await capitao.send(f"✅ **{interaction.user.display_name}** aprovou! Equipa **{nome_equipa}** está completa!")
                else:
                    await capitao.send(f"✅ **{interaction.user.display_name}** aprovou! Faltam aprovações.")
            except:
                pass
        
        await interaction.response.send_message(f"✅ Aprovaste! Equipa **{db_equipa.data[0]['nome_equipa'] if db_equipa.data else '?'}** no torneio **{self.torneio_nome}**.", ephemeral=True)

    @discord.ui.button(label="❌ Rejeitar", style=discord.ButtonStyle.danger, custom_id="equipa_rejeitar")
    async def btn_rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        db_equipa = supabase.table("torneio_equipas").select("*").eq("id", self.equipa_id).execute()
        if not db_equipa.data:
            return await interaction.response.send_message("❌ Equipa não encontrada.", ephemeral=True)
        
        capitao_id = db_equipa.data[0]["capitao_id"]
        nome_equipa = db_equipa.data[0]["nome_equipa"]
        
        # Eliminar equipa
        supabase.table("torneio_equipa_membros").delete().eq("equipa_id", self.equipa_id).execute()
        supabase.table("torneio_equipas").delete().eq("id", self.equipa_id).execute()
        
        # Avisar capitão
        try:
            capitao = await interaction.client.fetch_user(int(capitao_id))
            await capitao.send(f"❌ **{interaction.user.display_name}** rejeitou! Equipa **{nome_equipa}** foi eliminada.")
        except:
            pass
        
        await interaction.response.send_message(f"❌ Rejeitaste! Equipa **{nome_equipa}** foi eliminada.", ephemeral=True)

# ============================================================
# COMANDOS DE TORNEIO
# ============================================================
class Torneios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="torneio_criar", description="Cria um novo torneio")
    async def torneio_criar(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Apenas admins podem criar torneios.", ephemeral=True)
        await interaction.response.send_modal(ModalCriarTorneio())

    @app_commands.command(name="torneio_equipa_criar", description="Cria uma equipa para o torneio")
    async def torneio_equipa_criar(self, interaction: discord.Interaction, torneio_id: int, nome_equipa: str, membro1: discord.Member, membro2: discord.Member = None, membro3: discord.Member = None, membro4: discord.Member = None):
        # Verificar torneio
        db_torneio = supabase.table("torneios").select("*").eq("id", torneio_id).execute()
        if not db_torneio.data:
            return await interaction.response.send_message("❌ Torneio não encontrado.", ephemeral=True)
        
        torneio = db_torneio.data[0]
        if torneio["status"] != "inscrito":
            return await interaction.response.send_message("❌ Este torneio já começou ou terminou.", ephemeral=True)
        
        modo = torneio.get("modo", "solo")
        tamanho = MODOS.get(modo, 1)
        
        # Recolher membros
        membros_raw = [membro1]
        if membro2: membros_raw.append(membro2)
        if membro3: membros_raw.append(membro3)
        if membro4: membros_raw.append(membro4)
        
        membros = [m for m in membros_raw if m is not None]
        
        if len(membros) != tamanho:
            return await interaction.response.send_message(f"❌ O modo **{MODOS_NOME[modo]}** precisa de **{tamanho}** jogador(es). Enviaste {len(membros)}.", ephemeral=True)
        
        # Verificar se todos são do servidor
        for m in membros:
            if m.guild.id != interaction.guild.id:
                return await interaction.response.send_message(f"❌ **{m.display_name}** não é membro deste servidor.", ephemeral=True)
        
        # Verificar se algum já está noutra equipa
        for m in membros:
            db_existe = supabase.table("torneio_equipa_membros").select("equipa_id").eq("usuario_id", str(m.id)).execute()
            if db_existe.data:
                for eq in db_existe.data:
                    db_eq = supabase.table("torneio_equipas").select("torneio_id").eq("id", eq["equipa_id"]).execute()
                    if db_eq.data and db_eq.data[0]["torneio_id"] == torneio_id:
                        return await interaction.response.send_message(f"❌ **{m.display_name}** já está noutra equipa neste torneio.", ephemeral=True)
        
        # Verificar capacidade
        db_equipas = supabase.table("torneio_equipas").select("*").eq("torneio_id", torneio_id).execute()
        if db_equipas.data and len(db_equipas.data) >= torneio["max_participantes"]:
            return await interaction.response.send_message("❌ Torneio cheio! Todas as vagas estão preenchidas.", ephemeral=True)
        
        # Criar equipa
        db_eq = supabase.table("torneio_equipas").insert({
            "torneio_id": torneio_id,
            "nome_equipa": nome_equipa,
            "capitao_id": str(interaction.user.id),
            "status": "pendente"
        }).execute()
        
        equipa_id = db_eq.data[0]["id"]
        
        # Adicionar membros (capitão já aprovado)
        for m in membros:
            supabase.table("torneio_equipa_membros").insert({
                "equipa_id": equipa_id,
                "usuario_id": str(m.id),
                "aprovado": str(m.id) == str(interaction.user.id)
            }).execute()
        
        # Enviar DMs de aprovação para membros (não capitão)
        for m in membros:
            if m.id != interaction.user.id:
                try:
                    dm_embed = discord.Embed(
                        title="🏆 Convite para Equipa",
                        description=(
                            f"O **{interaction.user.display_name}** convidou-te para a equipa **{nome_equipa}**\n"
                            f"no torneio **{torneio['nome']}** ({MODOS_NOME[modo]})\n\n"
                            f"**Membros da equipa:**\n" +
                            "\n".join(f"• {x.display_name}" for x in membros) +
                            f"\n\nClica num botão abaixo para aprovar ou rejeitar."
                        ),
                        color=discord.Color.blue()
                    )
                    await m.send(embed=dm_embed, view=ViewAprovacaoEquipa(equipa_id, torneio["nome"]))
                except discord.Forbidden:
                    pass
        
        # Economia: recompensa por participar no torneio
        try:
            cfg_economia = supabase.table("economia_config").select("*").eq("guilda_id", str(interaction.guild_id)).execute()
            if cfg_economia.data and cfg_economia.data[0].get("habilitado"):
                moedas = cfg_economia.data[0].get("moedas_torneio_participar", 20)
                for m in membros:
                    db_user = supabase.table("membros_verificados").select("moedas").eq("id_discord", str(m.id)).eq("id_servidor", str(interaction.guild_id)).execute()
                    saldo_atual = db_user.data[0]["moedas"] if db_user.data and db_user.data[0].get("moedas") is not None else 0
                    supabase.table("membros_verificados").update({"moedas": saldo_atual + int(moedas)}).eq("id_discord", str(m.id)).eq("id_servidor", str(interaction.guild_id)).execute()
        except Exception:
            pass
        
        await interaction.response.send_message(
            f"✅ Equipa **{nome_equipa}** criada!\n"
            f"**Modo:** {MODOS_NOME[modo]}\n"
            f"**Membros:** {', '.join(m.display_name for m in membros)}\n\n"
            f"⏳ Aguarda aprovação de todos os membros (DMs enviados).",
            ephemeral=True
        )

    @app_commands.command(name="torneio_equipa_ver", description="Mostra as equipas inscritas num torneio")
    async def torneio_equipa_ver(self, interaction: discord.Interaction, torneio_id: int):
        db_torneio = supabase.table("torneios").select("*").eq("id", torneio_id).execute()
        if not db_torneio.data:
            return await interaction.response.send_message("❌ Torneio não encontrado.", ephemeral=True)
        
        torneio = db_torneio.data[0]
        
        db_equipas = supabase.table("torneio_equipas").select("*").eq("torneio_id", torneio_id).execute()
        
        embed = discord.Embed(title=f"🏆 Equipas — {torneio['nome']}", color=discord.Color.gold())
        
        if not db_equipas.data:
            embed.description = "Nenhuma equipa inscrita ainda."
        else:
            for eq in db_equipas.data:
                db_membros = supabase.table("torneio_equipa_membros").select("*").eq("equipa_id", eq["id"]).execute()
                membros_text = ""
                if db_membros.data:
                    for m in db_membros.data:
                        membro = interaction.guild.get_member(int(m["usuario_id"]))
                        nome = membro.display_name if membro else "Desconhecido"
                        status = "✅" if m.get("aprovado") else "⏳"
                        capitao = " 👑" if m["usuario_id"] == eq["capitao_id"] else ""
                        membros_text += f"{status} {nome}{capitao}\n"
                
                status_eq = "✅ Aprovada" if eq["status"] == "aprovada" else "⏳ Pendente"
                embed.add_field(name=f"{eq['nome_equipa']} ({status_eq})", value=membros_text or "Sem membros", inline=False)
        
        embed.set_footer(text=f"Total: {len(db_equipas.data) if db_equipas.data else 0} equipas")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="torneio_iniciar", description="Inicia o torneio e gera os brackets")
    async def torneio_iniciar(self, interaction: discord.Interaction, torneio_id: int):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Apenas admins podem iniciar torneios.", ephemeral=True)
        
        db_torneio = supabase.table("torneios").select("*").eq("id", torneio_id).execute()
        if not db_torneio.data:
            return await interaction.response.send_message("❌ Torneio não encontrado.", ephemeral=True)
        
        torneio = db_torneio.data[0]
        if torneio["status"] != "inscrito":
            return await interaction.response.send_message("❌ Este torneio já foi iniciado ou finalizado.", ephemeral=True)
        
        # Verificar equipas aprovadas e membros no servidor
        db_equipas = supabase.table("torneio_equipas").select("*").eq("torneio_id", torneio_id).execute()
        if not db_equipas.data or len(db_equipas.data) < 2:
            return await interaction.response.send_message("❌ Precisa de pelo menos 2 equipas.")
        
        equipas_validas = []
        equipas_invalidas = []
        
        for eq in db_equipas.data:
            db_membros = supabase.table("torneio_equipa_membros").select("*").eq("equipa_id", eq["id"]).execute()
            
            if not db_membros.data:
                equipas_invalidas.append(f"{eq['nome_equipa']} (sem membros)")
                continue
            
            todos_aprovaram = all(m.get("aprovado") for m in db_membros.data)
            todos_no_servidor = all(interaction.guild.get_member(int(m["usuario_id"])) for m in db_membros.data)
            
            if not todos_aprovaram:
                equipas_invalidas.append(f"{eq['nome_equipa']} (aprovação pendente)")
                supabase.table("torneio_equipas").delete().eq("id", eq["id"]).execute()
            elif not todos_no_servidor:
                equipas_invalidas.append(f"{eq['nome_equipa']} (membro saiu do servidor)")
                supabase.table("torneio_equipas").delete().eq("id", eq["id"]).execute()
            else:
                equipas_validas.append(eq["id"])
        
        if len(equipas_validas) < 2:
            msg = "❌ Não há equipas válidas suficientes.\n"
            if equipas_invalidas:
                msg += "**Eliminadas:**\n" + "\n".join(f"• {x}" for x in equipas_invalidas)
            return await interaction.response.send_message(msg)
        
        # Gerar brackets
        random.shuffle(equipas_validas)
        
        # Se número ímpar, última equipa avança direto
        if len(equipas_validas) % 2 != 0:
            equipas_validas.append(None)
        
        rodada = 1
        for i in range(0, len(equipas_validas), 2):
            eq1 = equipas_validas[i]
            eq2 = equipas_validas[i + 1] if i + 1 < len(equipas_validas) else None
            
            if eq1 and eq2:
                supabase.table("torneio_partidas").insert({
                    "torneio_id": torneio_id,
                    "rodada": rodada,
                    "jogador1_id": str(eq1),
                    "jogador2_id": str(eq2),
                    "status": "pendente"
                }).execute()
            elif eq1 and not eq2:
                # Bye — equipa avança
                supabase.table("torneio_partidas").insert({
                    "torneio_id": torneio_id,
                    "rodada": rodada,
                    "jogador1_id": str(eq1),
                    "jogador2_id": None,
                    "vencedor_id": str(eq1),
                    "status": "concluida"
                }).execute()
        
        supabase.table("torneios").update({"status": "em_andamento"}).eq("id", torneio_id).execute()
        
        msg_erro = ""
        if equipas_invalidas:
            msg_erro = f"\n\n⚠️ **Eliminadas:** {', '.join(equipas_invalidas)}"
        
        await interaction.response.send_message(f"✅ Torneio **{torneio['nome']}** iniciado com **{len(equipas_validas)}** equipas!{msg_erro}\nUsa `/torneio_brackets {torneio_id}` para ver.")

    @app_commands.command(name="torneio_brackets", description="Mostra os brackets do torneio")
    async def torneio_brackets(self, interaction: discord.Interaction, torneio_id: int):
        db_torneio = supabase.table("torneios").select("*").eq("id", torneio_id).execute()
        if not db_torneio.data:
            return await interaction.response.send_message("❌ Torneio não encontrado.", ephemeral=True)
        
        torneio = db_torneio.data[0]
        
        db_partidas = supabase.table("torneio_partidas").select("*").eq("torneio_id", torneio_id).order("rodada").execute()
        
        if not db_partidas.data:
            return await interaction.response.send_message("📋 Nenhuma partida ainda. Usa `/torneio_iniciar`.", ephemeral=True)
        
        embed = discord.Embed(title=f"🏆 Brackets — {torneio['nome']}", color=discord.Color.gold())
        
        rodadas = {}
        for partida in db_partidas.data:
            rodada = partida.get("rodada", 1)
            if rodada not in rodadas:
                rodadas[rodada] = []
            rodadas[rodada].append(partida)
        
        for rodada, partidas in sorted(rodadas.items()):
            texto = ""
            for p in partidas:
                eq1_id = p.get("jogador1_id")
                eq2_id = p.get("jogador2_id")
                vencedor_id = p.get("vencedor_id")
                
                nome1 = self._get_nome_equipa(eq1_id)
                nome2 = self._get_nome_equipa(eq2_id) if eq2_id else "BYE"
                
                if p["status"] == "concluida" and vencedor_id:
                    nome_venc = self._get_nome_equipa(vencedor_id)
                    texto += f"**#{p['id']}** {nome1} vs {nome2} → 🏆 {nome_venc}\n"
                else:
                    texto += f"**#{p['id']}** {nome1} vs {nome2} ⏳\n"
            
            nome_rodada = f"Rodada {rodada}" if rodada < len(rodadas) else "🏆 Final"
            embed.add_field(name=nome_rodada, value=texto or "Nenhuma partida", inline=False)
        
        embed.set_footer(text="Usa /torneio_resultado [ID] @equipa_vencedora")
        await interaction.response.send_message(embed=embed)

    def _get_nome_equipa(self, equipa_id):
        if not equipa_id:
            return "BYE"
        try:
            db = supabase.table("torneio_equipas").select("nome_equipa").eq("id", int(equipa_id)).execute()
            if db.data:
                return db.data[0]["nome_equipa"]
        except:
            pass
        return f"Equipa#{equipa_id}"

    @app_commands.command(name="torneio_resultado", description="Regista o vencedor de uma partida")
    async def torneio_resultado(self, interaction: discord.Interaction, partida_id: int, vencedor: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Apenas admins podem registar resultados.", ephemeral=True)
        
        db_partida = supabase.table("torneio_partidas").select("*").eq("id", partida_id).execute()
        if not db_partida.data:
            embed_erro = discord.Embed(
                title="❌ Partida não encontrada",
                description=(
                    f"Usa `/torneio_brackets [ID_TORNEIO]` para ver os IDs.\n"
                    f"O ID da partida é o número antes do nome (ex: **#3**)."
                ),
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_erro, ephemeral=True)
        
        partida = db_partida.data[0]
        
        # Verificar se o vencedor é uma equipa da partida
        eq1_id = str(partida.get("jogador1_id", ""))
        eq2_id = str(partida.get("jogador2_id", ""))
        
        # Verificar se o membro pertence a uma das equipas
        db_membro_venc = supabase.table("torneio_equipa_membros").select("equipa_id").eq("usuario_id", str(vencedor.id)).execute()
        if not db_membro_venc.data:
            return await interaction.response.send_message(f"❌ **{vencedor.display_name}** não pertence a nenhuma equipa.", ephemeral=True)
        
        equipa_vencedora_id = str(db_membro_venc.data[0]["equipa_id"])
        
        if equipa_vencedora_id not in [eq1_id, eq2_id]:
            nome1 = self._get_nome_equipa(eq1_id)
            nome2 = self._get_nome_equipa(eq2_id)
            return await interaction.response.send_message(f"❌ A equipa de **{vencedor.display_name}** não participa nesta partida.\nParticipantes: **{nome1}** vs **{nome2}**", ephemeral=True)
        
        # Registar resultado
        supabase.table("torneio_partidas").update({
            "vencedor_id": equipa_vencedora_id,
            "status": "concluida"
        }).eq("id", partida_id).execute()
        
        nome_venc = self._get_nome_equipa(equipa_vencedora_id)
        
        # Auto-advance
        rodada = partida.get("rodada", 1)
        torneio_id_val = partida.get("torneio_id")
        
        db_rodada = supabase.table("torneio_partidas").select("*").eq("torneio_id", torneio_id_val).eq("rodada", rodada).execute()
        
        if db_rodada.data:
            todas_concluidas = all(p.get("status") == "concluida" for p in db_rodada.data)
            if todas_concluidas:
                vencedores = [p["vencedor_id"] for p in db_rodada.data if p.get("vencedor_id")]
                if len(vencedores) >= 2:
                    next_rodada = rodada + 1
                    for i in range(0, len(vencedores), 2):
                        eq_a = vencedores[i]
                        eq_b = vencedores[i + 1] if i + 1 < len(vencedores) else None
                        if eq_a and eq_b:
                            supabase.table("torneio_partidas").insert({
                                "torneio_id": torneio_id_val,
                                "rodada": next_rodada,
                                "jogador1_id": eq_a,
                                "jogador2_id": eq_b,
                                "status": "pendente"
                            }).execute()
                    await interaction.response.send_message(f"✅ **{nome_venc}** venceu! Próxima rodada criada!")
                elif len(vencedores) == 1:
                    # CAMPEÃO
                    campeao_eq_id = vencedores[0]
                    nome_campeao = self._get_nome_equipa(campeao_eq_id)
                    
                    # Buscar dados do torneio
                    db_torneio = supabase.table("torneios").select("*").eq("id", torneio_id_val).execute()
                    nome_torneio = db_torneio.data[0]["nome"] if db_torneio.data else "Torneio"
                    premiacao = db_torneio.data[0].get("premiacao", "—") if db_torneio.data else "—"
                    
                    # Economia: recompensa por vencer torneio
                    try:
                        cfg_economia = supabase.table("economia_config").select("*").eq("guilda_id", str(interaction.guild_id)).execute()
                        if cfg_economia.data and cfg_economia.data[0].get("habilitado"):
                            moedas = cfg_economia.data[0].get("moedas_torneio_vencer", 100)
                            for m in db_membros_campeao.data:
                                db_user = supabase.table("membros_verificados").select("moedas").eq("id_discord", str(m["usuario_id"])).eq("id_servidor", str(interaction.guild_id)).execute()
                                saldo_atual = db_user.data[0]["moedas"] if db_user.data and db_user.data[0].get("moedas") is not None else 0
                                supabase.table("membros_verificados").update({"moedas": saldo_atual + int(moedas)}).eq("id_discord", str(m["usuario_id"])).eq("id_servidor", str(interaction.guild_id)).execute()
                    except Exception:
                        pass
                    
                    # Enviar DM a todos da equipa campeã
                    db_membros_campeao = supabase.table("torneio_equipa_membros").select("usuario_id").eq("equipa_id", campeao_eq_id).execute()
                    if db_membros_campeao.data:
                        for m in db_membros_campeao.data:
                            try:
                                user = await self.bot.fetch_user(int(m["usuario_id"]))
                                dm_embed = discord.Embed(
                                    title="🏆 Parabéns, Campeões!",
                                    description=f"Venceste o torneio **{nome_torneio}**!\n\n**Premiação:** {premiacao}\n**Servidor:** {interaction.guild.name}",
                                    color=discord.Color.gold()
                                )
                                await user.send(embed=dm_embed)
                            except:
                                pass
                    
                    # Enviar para canal de vitórias
                    await self._enviar_vitoria(interaction.guild, torneio_id_val, nome_campeao, nome_torneio, premiacao)
                    
                    # Eliminar dados na ordem correta
                    supabase.table("torneio_partidas").delete().eq("torneio_id", torneio_id_val).execute()
                    supabase.table("torneio_inscritos").delete().eq("torneio_id", torneio_id_val).execute()
                    db_equipas_del = supabase.table("torneio_equipas").select("id").eq("torneio_id", torneio_id_val).execute()
                    if db_equipas_del.data:
                        for eq in db_equipas_del.data:
                            supabase.table("torneio_equipa_membros").delete().eq("equipa_id", eq["id"]).execute()
                    supabase.table("torneio_equipas").delete().eq("torneio_id", torneio_id_val).execute()
                    supabase.table("torneios").delete().eq("id", torneio_id_val).execute()
                    
                    await interaction.response.send_message(f"🏆 **CAMPEÃS: {nome_campeao}**! Torneio finalizado!")
                else:
                    await interaction.response.send_message(f"✅ **{nome_venc}** venceu!")
            else:
                await interaction.response.send_message(f"✅ **{nome_venc}** venceu! Aguarda as outras partidas.")
        else:
            await interaction.response.send_message(f"✅ **{nome_venc}** venceu!")

    async def _enviar_vitoria(self, guild, torneio_id, nome_campeao, nome_torneio, premiacao):
        try:
            db_config = supabase.table("torneios_config").select("*").eq("guilda_id", str(guild.id)).execute()
            if db_config.data and db_config.data[0].get("canal_vitorias"):
                canal = guild.get_channel(int(db_config.data[0]["canal_vitorias"]))
                if canal:
                    embed = discord.Embed(
                        title="🏆 Torneio Finalizado!",
                        description=f"**Torneio:** {nome_torneio}\n**Campeãs:** {nome_campeao}\n**Premiação:** {premiacao}",
                        color=discord.Color.gold()
                    )
                    await canal.send(embed=embed)
        except:
            pass

    @app_commands.command(name="torneio_finalizar", description="Finaliza um torneio manualmente")
    async def torneio_finalizar(self, interaction: discord.Interaction, torneio_id: int):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Apenas admins podem finalizar torneios.", ephemeral=True)
        
        db_torneio = supabase.table("torneios").select("*").eq("id", torneio_id).execute()
        if not db_torneio.data:
            return await interaction.response.send_message("❌ Torneio não encontrado.", ephemeral=True)
        
        # Eliminar dados na ordem correta (respeitar foreign keys)
        supabase.table("torneio_partidas").delete().eq("torneio_id", torneio_id).execute()
        supabase.table("torneio_inscritos").delete().eq("torneio_id", torneio_id).execute()
        
        db_equipas = supabase.table("torneio_equipas").select("id").eq("torneio_id", torneio_id).execute()
        if db_equipas.data:
            for eq in db_equipas.data:
                supabase.table("torneio_equipa_membros").delete().eq("equipa_id", eq["id"]).execute()
        supabase.table("torneio_equipas").delete().eq("torneio_id", torneio_id).execute()
        
        supabase.table("torneios").delete().eq("id", torneio_id).execute()
        
        embed = discord.Embed(
            title=f"🏆 Torneio Finalizado: {db_torneio.data[0]['nome']}",
            description="Todos os dados foram eliminados do banco.",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Torneios(bot))
