import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import random
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

# ----------------------------------------------------
# CONFIGURATION DES IDS DE SALONS (À remplacer par les vôtres)
# ----------------------------------------------------
ID_SALON_LOGS_QUETES = 1234567890123456789, 1571278306655867081 # Salon où s'annoncent les réussites de quêtes
ID_SALON_BOUTIQUE = 9876543210987654321     # Salon réservé uniquement à la boutique

class MarcoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
        self.quetes_list = [
            {
                "titre": "💬 Participer au chat", 
                "description": "Envoyer 5 messages dans les salons du serveur.", 
                "recompense_or": 50,
                "objectif_messages": 5,
                "cooldown_heures": 24,
                "role_mention": None,
                "type": "chat"
            },
            {
                "titre": "🎮 Session Vocale", 
                "description": "Rejoindre un salon vocal du serveur.", 
                "recompense_or": 100,
                "cooldown_heures": 24,
                "role_mention": None,
                "type": "vocal"
            }
        ]
        
        self.quiz_list = [
            {
                "question": "Quel est le langage principal utilisé pour coder marcobot ?",
                "options": ["Python", "JavaScript", "C++", "HTML"],
                "reponse": "Python"
            }
        ]

        self.cartes_list = [
            {
                "nom": "Pikachu", 
                "rarete": "Commun", 
                "description": "Une souris électrique pleine d'énergie.",
                "image": "https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=500"
            },
            {
                "nom": "Bulbizarre", 
                "rarete": "Commun", 
                "description": "Il a une graine plantée sur son dos.",
                "image": "https://images.unsplash.com/photo-1642055698714-3d4411fb26fc?w=500"
            },
            {
                "nom": "Dracaufeu", 
                "rarete": "Légendaire", 
                "description": "Un dragon de feu surpuissant et redouté.",
                "image": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=500"
            },
            {
                "nom": "Mewtwo", 
                "rarete": "Épique", 
                "description": "Un Pokémon créé par manipulation génétique.",
                "image": "https://images.unsplash.com/photo-1563089145-599997674d42?w=500"
            },
            {
                "nom": "Arcanin", 
                "rarete": "Rare", 
                "description": "Un Pokémon chien majestueux et très rapide.",
                "image": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=500"
            }
        ]

        self.boutique_list = [
            {
                "nom": "Badge VIP Collector", 
                "description": "Un objet collector prestigieux dans ton inventaire.", 
                "prix": 250,
                "type_recompense": "objet",
                "role_id": None,
                "duree_totale_minutes": None,
                "duree_affichage": None,
                "bonus_or": 0
            }
        ]

        self.roles_temporaires = []
        self.user_inventories = {}
        self.dernier_tirage = {}
        self.user_money = {}
        self.dernier_work = {}
        self.dernieres_quetes = {}
        self.progression_messages = {}

    async def setup_hook(self):
        self.add_view(PanneauBoutiqueView(self))
        self.verifier_roles_expires.start()
        
        GUILD_ID = discord.Object(id=1359606058922017001)
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)
        print("Commandes, vues persistantes et tâches synchronisées avec succès !")

    @tasks.loop(minutes=1)
    async def verifier_roles_expires(self):
        """Vérifie chaque minute si un rôle temporaire acheté a expiré."""
        maintenant = datetime.now()
        a_conserver = []

        for item in self.roles_temporaires:
            if maintenant >= item["expiration"]:
                guild = self.get_guild(item["guild_id"])
                if guild:
                    member = guild.get_member(item["user_id"])
                    role = guild.get_role(item["role_id"])
                    if member and role and role in member.roles:
                        try:
                            await member.remove_roles(role, reason="Expiration du rôle temporaire (Boutique)")
                            await member.send(f"⏳ Ton rôle temporaire **{role.name}** sur **{guild.name}** vient d'expirer.")
                        except (discord.Forbidden, discord.HTTPException):
                            pass
            else:
                a_conserver.append(item)

        self.roles_temporaires = a_conserver

    @verifier_roles_expires.before_loop
    async def before_verifier_roles(self):
        await self.wait_until_ready()


# ==========================================
# VUES DE LA BOUTIQUE & ACHAT
# ==========================================

class AchatBoutiqueView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=120.0)
        self.bot_instance = bot_instance

        for index, article in enumerate(self.bot_instance.boutique_list):
            button = discord.ui.Button(
                label=f"Acheter #{index + 1} ({article['prix']} 🪙)",
                style=discord.ButtonStyle.green
            )
            button.callback = self.create_buy_callback(index)
            self.add_item(button)

    def create_buy_callback(self, index):
        async def buy_callback(interaction: discord.Interaction):
            if not (0 <= index < len(self.bot_instance.boutique_list)):
                await interaction.response.send_message("❌ Cet article n'est plus disponible.", ephemeral=True)
                return

            article = self.bot_instance.boutique_list[index]
            user_id = interaction.user.id
            solde_actuel = self.bot_instance.user_money.get(user_id, 0)

            if solde_actuel < article["prix"]:
                await interaction.response.send_message(
                    f"❌ Solde insuffisant ! Tu as **{solde_actuel} pièces**, mais **{article['nom']}** coûte **{article['prix']} pièces**.",
                    ephemeral=True
                )
                return

            self.bot_instance.user_money[user_id] -= article["prix"]
            type_rec = article.get("type_recompense", "objet")
            details_rec = ""

            # 1. Rôle à durée illimitée ou limitée
            if type_rec in ["role_illimite", "role_limite"] and article.get("role_id"):
                role = interaction.guild.get_role(article["role_id"])
                if role:
                    try:
                        await interaction.user.add_roles(role, reason=f"Achat boutique : {article['nom']}")
                        if type_rec == "role_limite" and article.get("duree_totale_minutes"):
                            minutes = article["duree_totale_minutes"]
                            affichage = article.get("duree_affichage", f"{minutes} min")
                            expiration = datetime.now() + timedelta(minutes=minutes)
                            self.bot_instance.roles_temporaires.append({
                                "guild_id": interaction.guild.id,
                                "user_id": user_id,
                                "role_id": role.id,
                                "expiration": expiration
                            })
                            details_rec = f"\n⏳ Le rôle **{role.name}** t'a été attribué pendant **{affichage}** !"
                        else:
                            details_rec = f"\n♾️ Le rôle **{role.name}** t'a été attribué de façon **illimitée** !"
                    except discord.Forbidden:
                        details_rec = f"\n⚠️ Le bot n'a pas la permission de donner le rôle **{role.name}** (place le rôle du bot tout en haut)."

            # 2. Bonus d'or
            elif type_rec == "or":
                gain_bonus = article.get("bonus_or", 0)
                self.bot_instance.user_money[user_id] += gain_bonus
                details_rec = f"\n💰 Tu as reçu un coffre contenant **{gain_bonus} pièces d'or** !"

            # 3. Ajout dans l'inventaire
            if user_id not in self.bot_instance.user_inventories:
                self.bot_instance.user_inventories[user_id] = []

            self.bot_instance.user_inventories[user_id].append({
                "nom": article["nom"],
                "rarete": "Boutique",
                "description": article["description"],
                "image": "https://images.unsplash.com/photo-1513151233558-d860c5398176?w=500"
            })

            await interaction.response.send_message(
                f"🎉 Achat validé : **{article['nom']}** pour **{article['prix']} pièces d'or** !{details_rec}",
                ephemeral=True
            )
        return buy_callback


class PanneauBoutiqueView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot_instance = bot_instance

    @discord.ui.button(label="🛒 Ouvrir la Boutique", style=discord.ButtonStyle.blurple, custom_id="persistent_open_boutique")
    async def open_boutique(self, interaction: discord.Interaction, button: discord.ui.Button):
        solde_user = self.bot_instance.user_money.get(interaction.user.id, 0)
        embed = discord.Embed(
            title="🏪 Boutique des Accessoires & Récompenses",
            description=f"💰 Ton solde actuel : **{solde_user} pièces d'or**\nClique sur un bouton vert ci-dessous pour acheter !",
            color=discord.Color.purple()
        )

        if not self.bot_instance.boutique_list:
            embed.add_field(name="Boutique vide", value="Aucun article disponible pour le moment.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        for idx, article in enumerate(self.bot_instance.boutique_list, start=1):
            type_rec = article.get("type_recompense", "objet")
            badge_recompense = ""

            if type_rec == "role_illimite" and article.get("role_id") and interaction.guild:
                role = interaction.guild.get_role(article["role_id"])
                if role:
                    badge_recompense = f"\n♾️ **Récompense :** Rôle {role.mention} (Illimité)"
            elif type_rec == "role_limite" and article.get("role_id") and interaction.guild:
                role = interaction.guild.get_role(article["role_id"])
                if role:
                    affichage = article.get("duree_affichage", f"{article.get('duree_totale_minutes')} min")
                    badge_recompense = f"\n⏳ **Récompense :** Rôle {role.mention} (Durée : **{affichage}**)"
            elif type_rec == "or":
                badge_recompense = f"\n💰 **Récompense :** +{article.get('bonus_or', 0)} pièces d'or"
            else:
                badge_recompense = "\n🎒 **Récompense :** Objet collector dans l'inventaire"

            embed.add_field(
                name=f"#{idx} - {article['nom']} (🪙 {article['prix']} or)",
                value=f"{article['description']}{badge_recompense}",
                inline=False
            )

        view = AchatBoutiqueView(self.bot_instance)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# CRÉATION DE L'OBJET BOT EN PREMIER
bot = MarcoBot()

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")


def get_log_channel(guild, fallback_channel=None):
    channel = guild.get_channel(ID_SALON_LOGS_QUETES)
    if channel:
        return channel
    return fallback_channel


# ==========================================
# 0A. ÉCOUTEUR DE MESSAGES (QUÊTE CHAT)
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id

    for index_quete, quete in enumerate(bot.quetes_list):
        if quete.get("type") == "chat":
            maintenant = datetime.now()
            cooldown = timedelta(hours=quete.get("cooldown_heures", 24))
            cle_suivi = (user_id, index_quete)

            if cle_suivi in bot.dernieres_quetes:
                if maintenant < bot.dernieres_quetes[cle_suivi] + cooldown:
                    continue

            if user_id not in bot.progression_messages:
                bot.progression_messages[user_id] = 0
            
            bot.progression_messages[user_id] += 1
            objectif = quete.get("objectif_messages", 5)

            if bot.progression_messages[user_id] >= objectif:
                bot.dernieres_quetes[cle_suivi] = maintenant
                bot.progression_messages[user_id] = 0

                recompense = quete["recompense_or"]
                bot.user_money[user_id] = bot.user_money.get(user_id, 0) + recompense

                target_channel = get_log_channel(message.guild, message.channel)
                await target_channel.send(
                    f"🎉 Bravo {message.author.mention} ! Tu as validé la quête **{quete['titre']}** et gagné **{recompense} pièces d'or** !"
                )
            break

    await bot.process_commands(message)


# ==========================================
# 0B. ÉCOUTEUR VOCAL (QUÊTE VOCAL)
# ==========================================
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    if before.channel is None and after.channel is not None:
        user_id = member.id
        maintenant = datetime.now()

        for index_quete, quete in enumerate(bot.quetes_list):
            if quete.get("type") == "vocal":
                cooldown = timedelta(hours=quete.get("cooldown_heures", 24))
                cle_suivi = (user_id, index_quete)

                if cle_suivi in bot.dernieres_quetes:
                    if maintenant < bot.dernieres_quetes[cle_suivi] + cooldown:
                        continue

                bot.dernieres_quetes[cle_suivi] = maintenant
                recompense = quete["recompense_or"]
                bot.user_money[user_id] = bot.user_money.get(user_id, 0) + recompense

                target_channel = get_log_channel(after.channel.guild, after.channel.guild.system_channel)
                if not target_channel:
                    for channel in after.channel.guild.text_channels:
                        if channel.permissions_for(after.channel.guild.me).send_messages:
                            target_channel = channel
                            break

                if target_channel:
                    await target_channel.send(
                        f"🎙️ Bravo {member.mention} ! En rejoignant le salon vocal **{after.channel.name}**, tu as validé la quête **{quete['titre']}** et gagné **{recompense} pièces d'or** !"
                    )
                break


# ==========================================
# 1. GESTION DES QUÊTES
# ==========================================

class DynamicQueteView(discord.ui.View):
    def __init__(self, bot_instance, user_id):
        super().__init__(timeout=None)
        self.bot_instance = bot_instance

        for index, quete in enumerate(self.bot_instance.quetes_list):
            cle_suivi = (user_id, index)
            maintenant = datetime.now()
            cooldown = timedelta(hours=quete.get("cooldown_heures", 24))
            
            est_en_cooldown = False
            if cle_suivi in self.bot_instance.dernieres_quetes:
                if maintenant < self.bot_instance.dernieres_quetes[cle_suivi] + cooldown:
                    est_en_cooldown = True

            label_texte = "✅ Déjà accomplie" if est_en_cooldown else f"📜 {quete['titre']}"
            
            button = discord.ui.Button(
                label=label_texte, 
                style=discord.ButtonStyle.secondary if est_en_cooldown else discord.ButtonStyle.blurple, 
                disabled=est_en_cooldown,
                custom_id=f"quete_info_{index}"
            )
            button.callback = self.create_callback(index)
            self.add_item(button)

    def create_callback(self, index):
        async def button_callback(interaction: discord.Interaction):
            if index >= len(self.bot_instance.quetes_list):
                await interaction.response.send_message("❌ Cette quête n'existe plus.", ephemeral=True)
                return

            quete = self.bot_instance.quetes_list[index]
            await interaction.response.send_message(
                f"ℹ️ **{quete['titre']}**\n{quete['description']}\nObjectif : accomplis cette action sur le serveur pour recevoir ta récompense automatiquement !", 
                ephemeral=True
            )
        return button_callback

@bot.tree.command(name="quetes_journalieres", description="Voir les quêtes journalières.")
@app_commands.describe(role_a_mentionner="Rôle optionnel à mentionner")
async def quetes_journalieres(interaction: discord.Interaction, role_a_mentionner: discord.Role = None):
    embed = discord.Embed(
        title="🌟 Quêtes Journalières",
        description="Accomplis les objectifs ci-dessous pour gagner de l'or automatiquement !",
        color=discord.Color.gold()
    )
    
    content_text = f"{role_a_mentionner.mention} 📢 **Nouvelles quêtes disponibles !**" if role_a_mentionner else None
    allowed = discord.AllowedMentions(roles=True, everyone=True)

    if not bot.quetes_list:
        embed.add_field(name="Aucune quête", value="Reviens plus tard !", inline=False)
        await interaction.response.send_message(content=content_text, embed=embed, allowed_mentions=allowed)
    else:
        for i, q in enumerate(bot.quetes_list, start=1):
            embed.add_field(
                name=f"Quête #{i} : {q['titre']}", 
                value=f"**Objectif :** {q['description']}\n**Récompense :** {q['recompense_or']} pièces d'or\n**Type :** {q.get('type', 'chat').upper()}", 
                inline=False
            )
        
        view = DynamicQueteView(bot, interaction.user.id)
        await interaction.response.send_message(content=content_text, embed=embed, view=view, allowed_mentions=allowed)

@bot.tree.command(name="ajouter_quete", description="[Admin] Ajouter une quête (chat ou vocal).")
@app_commands.describe(
    titre="Titre", 
    description="Description", 
    recompense_or="Pièces d'or", 
    type_quete="Choisis entre 'chat' ou 'vocal'",
    role_a_mentionner="Rôle à mentionner"
)
@app_commands.choices(type_quete=[
    app_commands.Choice(name="Chat (messages)", value="chat"),
    app_commands.Choice(name="Vocal (rejoindre un salon)", value="vocal")
])
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_quete(interaction: discord.Interaction, titre: str, description: str, recompense_or: int, type_quete: str = "chat", role_a_mentionner: discord.Role = None):
    bot.quetes_list.append({
        "titre": titre, 
        "description": description, 
        "recompense_or": recompense_or, 
        "objectif_messages": 5,
        "cooldown_heures": 24,
        "role_mention": role_a_mentionner,
        "type": type_quete
    })
    
    await interaction.response.send_message(f"✅ Quête de type **{type_quete}** ajoutée avec succès !", ephemeral=True)

@bot.tree.command(name="supprimer_quete", description="[Admin] Supprimer une quête.")
@app_commands.describe(numero="Numéro de la quête")
@app_commands.checks.has_permissions(administrator=True)
async def supprimer_quete(interaction: discord.Interaction, numero: int):
    index = numero - 1
    if 0 <= index < len(bot.quetes_list):
        quete_supprimee = bot.quetes_list.pop(index)
        await interaction.response.send_message(f"🗑️ Quête **#{numero} - {quete_supprimee['titre']}** supprimée !", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Numéro invalide.", ephemeral=True)


# ==========================================
# 2. GESTION DES QUIZ
# ==========================================

class QuizView(discord.ui.View):
    def __init__(self, options, bonne_reponse, question):
        super().__init__(timeout=60.0)
        self.bonne_reponse = bonne_reponse
        self.question = question
        self.quiz_fini = False

        for option in options:
            button = discord.ui.Button(label=option, style=discord.ButtonStyle.blurple)
            button.callback = self.create_callback(option)
            self.add_item(button)

    def create_callback(self, option_choisie):
        async def button_callback(interaction: discord.Interaction):
            if self.quiz_fini:
                await interaction.response.send_message("❌ Ce quiz est déjà terminé !", ephemeral=True)
                return

            if option_choisie == self.bonne_reponse:
                self.quiz_fini = True
                for child in self.children:
                    child.disabled = True
                await interaction.response.edit_message(content=f"🎉 Bravo {interaction.user.mention} ! C'était la bonne réponse (**{self.bonne_reponse}**) !", view=self)
            else:
                await interaction.response.send_message("❌ Mauvaise réponse !", ephemeral=True)
        return button_callback

@bot.tree.command(name="quiz", description="Lancer un quiz.")
@app_commands.describe(role_a_mentionner="Rôle optionnel à mentionner")
async def quiz(interaction: discord.Interaction, role_a_mentionner: discord.Role = None):
    if not bot.quiz_list:
        await interaction.response.send_message("❌ Aucun quiz disponible.", ephemeral=True)
        return

    q_data = random.choice(bot.quiz_list)
    embed = discord.Embed(title="🧠 Quiz du serveur !", description=f"**{q_data['question']}**", color=discord.Color.blue())
    view = QuizView(q_data["options"], q_data["reponse"], q_data["question"])

    content_text = f"{role_a_mentionner.mention} 🧠 **Nouveau Quiz disponible !**" if role_a_mentionner else None
    allowed = discord.AllowedMentions(roles=True, everyone=True)

    await interaction.response.send_message(content=content_text, embed=embed, view=view, allowed_mentions=allowed)


# ==========================================
# 3. CARTES POKÉMON & TIRAGE 24H
# ==========================================

@bot.tree.command(name="ajouter_carte", description="[Admin] Ajouter une carte.")
@app_commands.describe(nom="Nom", rarete="Rarete", description="Description", lien_image="Lien image")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_carte(interaction: discord.Interaction, nom: str, rarete: str, description: str, lien_image: str):
    bot.cartes_list.append({"nom": nom, "rarete": rarete.capitalize(), "description": description, "image": lien_image})
    await interaction.response.send_message(f"🃏 Carte **{nom}** ajoutée !", ephemeral=True)

@bot.tree.command(name="tirer_carte", description="Tirer ta carte quotidienne (24h).")
async def tirer_carte(interaction: discord.Interaction):
    if not bot.cartes_list:
        await interaction.response.send_message("❌ Aucune carte.", ephemeral=True)
        return

    user_id = interaction.user.id
    maintenant = datetime.now()

    if user_id in bot.dernier_tirage:
        prochain = bot.dernier_tirage[user_id] + timedelta(hours=24)
        if maintenant < prochain:
            restant = prochain - maintenant
            h, m = int(restant.total_seconds() // 3600), int((restant.total_seconds() % 3600) // 60)
            await interaction.response.send_message(f"⏳ Prochain tirage dans **{h}h et {m}min**.", ephemeral=True)
            return

    bot.dernier_tirage[user_id] = maintenant
    if user_id not in bot.user_inventories:
        bot.user_inventories[user_id] = []

    carte = random.choice(bot.cartes_list)
    bot.user_inventories[user_id].append(carte)

    embed = discord.Embed(title=f"🎴 Tirage de {interaction.user.name} : {carte['nom']}", description=f"**Rareté :** {carte['rarete']}\n{carte['description']}", color=discord.Color.gold())
    embed.set_image(url=carte["image"])
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="inventaire", description="Voir ton inventaire.")
async def inventaire(interaction: discord.Interaction):
    user_inv = bot.user_inventories.get(interaction.user.id, [])
    if not user_inv:
        await interaction.response.send_message("❌ Inventaire vide.", ephemeral=True)
        return
    embed = discord.Embed(title=f"🎒 Inventaire de {interaction.user.name}", color=discord.Color.blurple())
    for idx, c in enumerate(user_inv, start=1):
        embed.add_field(name=f"#{idx} - {c['nom']} ({c['rarete']})", value=c['description'], inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 4. ÉCONOMIE & BOUTIQUE AVEC DURÉE AU CHOIX
# ==========================================

@bot.tree.command(name="solde", description="Voir ton solde.")
async def solde(interaction: discord.Interaction, membre: discord.Member = None):
    cible = membre or interaction.user
    or_actuel = bot.user_money.get(cible.id, 0)
    embed = discord.Embed(title=f"💰 Portefeuille de {cible.name}", description=f"**{or_actuel} pièces d'or**", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="work", description="Travailler pour gagner un peu d'or (toutes les 6h).")
async def work(interaction: discord.Interaction):
    user_id = interaction.user.id
    maintenant = datetime.now()
    if user_id in bot.dernier_work and maintenant < bot.dernier_work[user_id] + timedelta(hours=6):
        restant = (bot.dernier_work[user_id] + timedelta(hours=6)) - maintenant
        h, m = int(restant.total_seconds() // 3600), int((restant.total_seconds() % 3600) // 60)
        await interaction.response.send_message(f"⏳ Tu es fatigué. Reviens dans {h}h et {m}min.", ephemeral=True)
        return

    bot.dernier_work[user_id] = maintenant
    gain = random.randint(5, 25)
    bot.user_money[user_id] = bot.user_money.get(user_id, 0) + gain

    embed = discord.Embed(title="💼 Travail accompli !", description=f"Tu as gagné **{gain} pièces d'or** !", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="pile_ou_face", description="Parier de l'or.")
@app_commands.choices(choix=[app_commands.Choice(name="Pile", value="Pile"), app_commands.Choice(name="Face", value="Face")])
async def pile_ou_face(interaction: discord.Interaction, choix: str, mise: int):
    user_id = interaction.user.id
    solde_actuel = bot.user_money.get(user_id, 0)
    if mise <= 0 or solde_actuel < mise:
        await interaction.response.send_message("❌ Mise invalide ou solde insuffisant.", ephemeral=True)
        return

    resultat = random.choice(["Pile", "Face"])
    if choix == resultat:
        bot.user_money[user_id] += mise
        embed = discord.Embed(title="🎉 Gagné !", description=f"C'était **{resultat}** ! Tu gagnes +{mise} pièces.", color=discord.Color.green())
    else:
        bot.user_money[user_id] -= mise
        embed = discord.Embed(title="😢 Perdu...", description=f"C'était **{resultat}**... Tu perds -{mise} pièces.", color=discord.Color.red())
    
    await interaction.response.send_message(embed=embed)


# --- COMMANDES ADMIN DE LA BOUTIQUE ---

@bot.tree.command(name="panneau_boutique", description="[Admin] Poster le message permanent avec le bouton de la boutique.")
@app_commands.checks.has_permissions(administrator=True)
async def panneau_boutique(interaction: discord.Interaction):
    if interaction.channel_id != ID_SALON_BOUTIQUE:
        await interaction.response.send_message(f"❌ Utilise cette commande dans le salon dédié : <#{ID_SALON_BOUTIQUE}>", ephemeral=True)
        return

    embed = discord.Embed(
        title="🏪 Boutique des Accessoires & Récompenses",
        description="Dépense tes pièces d'or pour obtenir des rôles exclusifs (temporaires ou permanents), des coffres d'or et des objets collectors !\n\nAppuie sur **🛒 Ouvrir la Boutique** ci-dessous.",
        color=discord.Color.gold()
    )
    await interaction.channel.send(embed=embed, view=PanneauBoutiqueView(bot))
    await interaction.response.send_message("✅ Panneau permanent de la boutique installé !", ephemeral=True)


@bot.tree.command(name="ajouter_objet_boutique", description="[Admin] Créer un objet, sa récompense et sa durée au choix.")
@app_commands.describe(
    nom="Nom de l'objet ou accessoire",
    description="Description affichée dans la boutique",
    prix="Prix en pièces d'or",
    type_recompense="Choisis le type de récompense accordé à l'achat",
    role_donne="Le rôle à donner (si rôle limité ou illimité)",
    duree_valeur="Nombre de minutes, d'heures ou de jours (ex: 30, 2, 7)",
    unite_duree="Choisis l'unité de temps (Minutes, Heures ou Jours)",
    bonus_or="Montant d'or gagné (si Bonus d'Or)"
)
@app_commands.choices(
    type_recompense=[
        app_commands.Choice(name="♾️ Rôle à durée illimitée", value="role_illimite"),
        app_commands.Choice(name="⏳ Rôle à durée limitée", value="role_limite"),
        app_commands.Choice(name="🎒 Objet Collector (Inventaire)", value="objet"),
        app_commands.Choice(name="💰 Bonus d'Or", value="or")
    ],
    unite_duree=[
        app_commands.Choice(name="Minutes", value="minutes"),
        app_commands.Choice(name="Heures", value="heures"),
        app_commands.Choice(name="Jours", value="jours")
    ]
)
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_objet_boutique(
    interaction: discord.Interaction,
    nom: str,
    description: str,
    prix: int,
    type_recompense: str,
    role_donne: discord.Role = None,
    duree_valeur: int = None,
    unite_duree: str = "heures",
    bonus_or: int = 0
):
    if prix <= 0:
        await interaction.response.send_message("❌ Le prix doit être supérieur à 0.", ephemeral=True)
        return

    if type_recompense in ["role_illimite", "role_limite"] and not role_donne:
        await interaction.response.send_message("❌ Tu dois sélectionner un rôle dans `role_donne` !", ephemeral=True)
        return

    duree_totale_minutes = None
    duree_affichage = None

    if type_recompense == "role_limite":
        if not duree_valeur or duree_valeur <= 0:
            await interaction.response.send_message("❌ Tu dois indiquer un nombre dans `duree_valeur` supérieur à 0 !", ephemeral=True)
            return
        
        if unite_duree == "minutes":
            duree_totale_minutes = duree_valeur
            duree_affichage = f"{duree_valeur} minute(s)"
        elif unite_duree == "heures":
            duree_totale_minutes = duree_valeur * 60
            duree_affichage = f"{duree_valeur} heure(s)"
        elif unite_duree == "jours":
            duree_totale_minutes = duree_valeur * 1440
            duree_affichage = f"{duree_valeur} jour(s)"

    if type_recompense == "or" and bonus_or <= 0:
        await interaction.response.send_message("❌ Tu dois indiquer un montant dans `bonus_or` supérieur à 0 !", ephemeral=True)
        return

    bot.boutique_list.append({
        "nom": nom,
        "description": description,
        "prix": prix,
        "type_recompense": type_recompense,
        "role_id": role_donne.id if role_donne else None,
        "duree_totale_minutes": duree_totale_minutes,
        "duree_affichage": duree_affichage,
        "bonus_or": bonus_or if type_recompense == "or" else 0
    })

    resume = ""
    if type_recompense == "role_illimite":
        resume = f"♾️ Rôle illimité : {role_donne.mention}"
    elif type_recompense == "role_limite":
        resume = f"⏳ Rôle temporaire : {role_donne.mention} pendant **{duree_affichage}**"
    elif type_recompense == "or":
        resume = f"💰 Bonus de **{bonus_or} pièces d'or**"
    else:
        resume = "🎒 Objet collector"

    await interaction.response.send_message(
        f"✅ Article **{nom}** ajouté à la boutique pour **{prix} pièces d'or** !\n**Récompense configurée :** {resume}",
        ephemeral=True
    )


@bot.tree.command(name="supprimer_objet_boutique", description="[Admin] Supprimer un article de la boutique.")
@app_commands.describe(numero="Numéro de l'article à retirer")
@app_commands.checks.has_permissions(administrator=True)
async def supprimer_objet_boutique(interaction: discord.Interaction, numero: int):
    index = numero - 1
    if 0 <= index < len(bot.boutique_list):
        objet_retire = bot.boutique_list.pop(index)
        await interaction.response.send_message(f"🗑️ L'article **{objet_retire['nom']}** a été retiré de la boutique.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Numéro d'article invalide.", ephemeral=True)


TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Erreur : Token introuvable.")
