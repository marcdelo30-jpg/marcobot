import discord
from discord.ext import commands
from discord import app_commands
import os
import random
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MarcoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
        self.quetes_list = [
            {
                "titre": "💬 Participer au chat", 
                "description": "Envoyer au moins 10 messages dans les salons textuels.", 
                "recompense": "50 pièces d'or"
            },
            {
                "titre": "🎮 Jouer avec la communauté", 
                "description": "Participer à une session vocale ou un jeu sur le serveur.", 
                "recompense": "100 pièces d'or + Rôle actif"
            }
        ]
        
        self.quiz_list = [
            {
                "question": "Quel est le langage principal utilisé pour coder marcobot ?",
                "options": ["Python", "JavaScript", "C++", "HTML"],
                "reponse": "Python"
            }
        ]

        # 3. Base de données des cartes AVEC les liens d'images (tu pourras remplacer les liens par les tiens)
        self.cartes_list = [
            {
                "nom": "Pikachu", 
                "rarete": "Commun", 
                "description": "Une souris électrique pleine d'énergie.",
                "image": "https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=500" # Exemple de lien d'image
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

        self.user_inventories = {}
        self.dernier_tirage = {}
        self.user_money = {}
        self.dernier_work = {}

    async def setup_hook(self):
        GUILD_ID = discord.Object(id=1359606058922017001)
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)
        print("Commandes synchronisées avec succès !")

bot = MarcoBot()

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")


# ==========================================
# 1. GESTION DES QUÊTES
# ==========================================

@bot.tree.command(name="ajouter_quete", description="[Admin] Ajouter une nouvelle quête journalière.")
@app_commands.describe(titre="Titre de la quête", description="Description de ce qu'il faut faire", recompense="Récompense à gagner")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_quete(interaction: discord.Interaction, titre: str, description: str, recompense: str):
    bot.quetes_list.append({"titre": titre, "description": description, "recompense": recompense})
    await interaction.response.send_message(f"✅ Quête **{titre}** ajoutée !", ephemeral=True)

@bot.tree.command(name="supprimer_quete", description="[Admin] Supprimer une quête journalière via son numéro.")
@app_commands.describe(numero="Numéro de la quête")
@app_commands.checks.has_permissions(administrator=True)
async def supprimer_quete(interaction: discord.Interaction, numero: int):
    index = numero - 1
    if 0 <= index < len(bot.quetes_list):
        supp = bot.quetes_list.pop(index)
        await interaction.response.send_message(f"🗑️ Quête **{supp['titre']}** supprimée.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Numéro invalide.", ephemeral=True)

@bot.tree.command(name="quetes_journalieres", description="Voir les quêtes journalières.")
async def quetes_journalieres(interaction: discord.Interaction):
    embed = discord.Embed(title="🌟 Quêtes Journalières", color=discord.Color.gold())
    if not bot.quetes_list:
        embed.add_field(name="Aucune quête", value="Reviens plus tard !", inline=False)
    else:
        for i, q in enumerate(bot.quetes_list, start=1):
            embed.add_field(name=f"Quête #{i} : {q['titre']}", value=f"**Objectif :** {q['description']}\n**Récompense :** {q['recompense']}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="gerer_quetes", description="[Admin] Panneau de gestion des quêtes.")
@app_commands.checks.has_permissions(administrator=True)
async def gerer_quetes(interaction: discord.Interaction):
    embed = discord.Embed(title="⚙️ Gestion des Quêtes", description=f"Total : {len(bot.quetes_list)} quêtes.", color=discord.Color.blue())
    for i, q in enumerate(bot.quetes_list, start=1):
        embed.add_field(name=f"#{i} - {q['titre']}", value=f"Récompense: {q['recompense']}", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)


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
                
                guild = interaction.guild
                if guild:
                    for member in guild.members:
                        if member.guild_permissions.administrator and not member.bot:
                            try:
                                admin_embed = discord.Embed(title="🔔 Bonne réponse à un Quiz !", description=f"Membre : {interaction.user.mention}\nQuestion : {self.question}", color=discord.Color.gold())
                                await member.send(embed=admin_embed)
                            except discord.HTTPException:
                                pass
            else:
                await interaction.response.send_message("❌ Mauvaise réponse ! Vérifie tes messages privés.", ephemeral=True)
                try:
                    perdu_embed = discord.Embed(title="❌ Raté !", description=f"Mauvaise réponse à la question sur **{interaction.guild.name}**.", color=discord.Color.red())
                    await interaction.user.send(embed=perdu_embed)
                except discord.HTTPException:
                    pass
        return button_callback

@bot.tree.command(name="ajouter_quiz", description="[Admin] Ajouter un quiz.")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_quiz(interaction: discord.Interaction, question: str, opt1: str, opt2: str, opt3: str, opt4: str, bonne_reponse: str):
    options = [opt1, opt2, opt3, opt4]
    if bonne_reponse not in options:
        await interaction.response.send_message("❌ La bonne réponse doit correspondre à l'une des options.", ephemeral=True)
        return
    bot.quiz_list.append({"question": question, "options": options, "reponse": bonne_reponse})
    await interaction.response.send_message("❓ Quiz ajouté avec succès !", ephemeral=True)

@bot.tree.command(name="quiz", description="Lancer une question de quiz.")
async def quiz(interaction: discord.Interaction):
    if not bot.quiz_list:
        await interaction.response.send_message("❌ Aucun quiz disponible.", ephemeral=True)
        return
    q_data = random.choice(bot.quiz_list)
    embed = discord.Embed(title="🧠 Quiz du serveur !", description=f"**{q_data['question']}**", color=discord.Color.blue())
    view = QuizView(q_data["options"], q_data["reponse"], q_data["question"])
    await interaction.response.send_message(embed=embed, view=view)


# ==========================================
# 3. CARTES POKÉMON (AVEC IMAGES) & TIRAGE 24H
# ==========================================

@bot.tree.command(name="ajouter_carte", description="[Admin] Ajouter une carte avec son image.")
@app_commands.describe(nom="Nom du Pokémon", rarete="Commun, Rare, Épique, Légendaire", description="Description", lien_image="Lien direct de l'image (.png ou .jpg)")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_carte(interaction: discord.Interaction, nom: str, rarete: str, description: str, lien_image: str):
    rarete_clean = rarete.capitalize()
    if rarete_clean not in ["Commun", "Rare", "Épique", "Légendaire"]:
        await interaction.response.send_message("❌ Rareté invalide (Commun, Rare, Épique, Légendaire).", ephemeral=True)
        return

    bot.cartes_list.append({
        "nom": nom,
        "rarete": rarete_clean,
        "description": description,
        "image": lien_image
    })

    embed = discord.Embed(title="🃏 Carte ajoutée !", description=f"**{nom}** ({rarete_clean}) a été créée.", color=discord.Color.green())
    embed.set_image(url=lien_image)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="voir_cartes", description="Voir toutes les cartes du serveur.")
async def voir_cartes(interaction: discord.Interaction):
    if not bot.cartes_list:
        await interaction.response.send_message("❌ Aucune carte disponible.", ephemeral=True)
        return

    embed = discord.Embed(title="📦 Catalogue des Cartes", color=discord.Color.gold())
    for c in bot.cartes_list:
        embed.add_field(name=f"{c['nom']} ({c['rarete']})", value=c['description'], inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tirer_carte", description="Tirer ta carte quotidienne (1 fois toutes les 24h) !")
async def tirer_carte(interaction: discord.Interaction):
    if not bot.cartes_list:
        await interaction.response.send_message("❌ Aucune carte dans la base.", ephemeral=True)
        return

    user_id = interaction.user.id
    maintenant = datetime.now()

    if user_id in bot.dernier_tirage:
        prochain = bot.dernier_tirage[user_id] + timedelta(hours=24)
        if maintenant < prochain:
            restant = prochain - maintenant
            h = int(restant.total_seconds() // 3600)
            m = int((restant.total_seconds() % 3600) // 60)
            await interaction.response.send_message(f"⏳ Prochain tirage dans **{h}h et {m}min**.", ephemeral=True)
            return

    bot.dernier_tirage[user_id] = maintenant
    if user_id not in bot.user_inventories:
        bot.user_inventories[user_id] = []

    # 10% de chance d'avoir 2 cartes
    cartes_tirees = random.sample(bot.cartes_list, 2) if random.random() < 0.10 and len(bot.cartes_list) >= 2 else [random.choice(bot.cartes_list)]

    for carte in cartes_tirees:
        bot.user_inventories[user_id].append(carte)

    # Affichage de la carte tirée avec son image
    carte = cartes_tirees[0] # On affiche la première (ou principale) carte avec son image
    couleurs = {"Légendaire": discord.Color.gold(), "Épique": discord.Color.purple(), "Rare": discord.Color.blue(), "Commun": discord.Color.light_grey()}
    
    embed = discord.Embed(
        title=f"🎴 Tirage de {interaction.user.name} : {carte['nom']}",
        description=f"**Rareté :** {carte['rarete']}\n{carte['description']}",
        color=couleurs.get(carte["rarete"], discord.Color.default())
    )
    embed.set_image(url=carte["image"]) # Affiche l'image de la carte en grand !
    embed.set_footer(text="Utilise /inventaire pour voir tes cartes.")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="inventaire", description="Voir ton inventaire de cartes.")
async def inventaire(interaction: discord.Interaction):
    user_inv = bot.user_inventories.get(interaction.user.id, [])
    if not user_inv:
        await interaction.response.send_message("❌ Ton inventaire est vide. Utilise `/tirer_carte` !", ephemeral=True)
        return

    embed = discord.Embed(title=f"🎒 Inventaire de {interaction.user.name}", color=discord.Color.blurple())
    for idx, c in enumerate(user_inv, start=1):
        embed.add_field(name=f"#{idx} - {c['nom']} ({c['rarete']})", value=c['description'], inline=False)
    
    # Met l'image de la dernière carte possédée en aperçu (ou enlève si tu préfères)
    embed.set_thumbnail(url=user_inv[-1]["image"])
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 4. ÉCHANGES ET ÉCONOMIE
# ==========================================

class TradeView(discord.ui.View):
    def __init__(self, bot_inst, emetteur, receveur, carte_offerte, carte_demandee, idx_offert):
        super().__init__(timeout=60.0)
        self.bot_inst = bot_inst
        self.emetteur = emetteur
        self.receveur = receveur
        self.carte_offerte = carte_offerte
        self.carte_demandee = carte_demandee
        self.idx_offert = idx_offert
        self.traite = False

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.green)
    async def accepter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receveur.id or self.traite:
            await interaction.response.send_message("❌ Action impossible.", ephemeral=True)
            return
        self.traite = True

        receveur_inv = self.bot_inst.user_inventories.get(self.receveur.id, [])
        idx_demande = next((i for i, c in enumerate(receveur_inv) if c['nom'].lower() == self.carte_demandee.lower()), -1)
        
        if idx_demande == -1:
            await interaction.response.edit_message(content="❌ Échange annulé : la carte demandée n'est plus disponible.", view=None)
            return

        emetteur_inv = self.bot_inst.user_inventories.get(self.emetteur.id, [])
        c_offerte = emetteur_inv.pop(self.idx_offert)
        c_demandee = receveur_inv.pop(idx_demande)

        emetteur_inv.append(c_demandee)
        receveur_inv.append(c_offerte)

        embed = discord.Embed(title="🤝 Échange réussi !", description=f"Entre {self.emetteur.name} et {self.receveur.name}.", color=discord.Color.green())
        await interaction.response.edit_message(content="", embed=embed, view=None)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.red)
    async def refuser(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receveur.id or self.traite:
            await interaction.response.send_message("❌ Action impossible.", ephemeral=True)
            return
        self.traite = True
        await interaction.response.edit_message(content="❌ Échange refusé.", embed=None, view=None)

@bot.tree.command(name="echanger", description="Proposer un échange de carte.")
@app_commands.describe(membre="Membre cible", numero_carte="Numéro dans ton inventaire", nom_carte_voulue="Nom de la carte voulue")
async def echanger(interaction: discord.Interaction, membre: discord.Member, numero_carte: int, nom_carte_voulue: str):
    if membre.id == interaction.user.id or membre.bot:
        await interaction.response.send_message("❌ Cible invalide.", ephemeral=True)
        return

    user_inv = bot.user_inventories.get(interaction.user.id, [])
    idx = numero_carte - 1
    if not (0 <= idx < len(user_inv)):
        await interaction.response.send_message("❌ Numéro de carte invalide dans ton inventaire.", ephemeral=True)
        return

    dest_inv = bot.user_inventories.get(membre.id, [])
    if not any(c['nom'].lower() == nom_carte_voulue.lower() for c in dest_inv):
        await interaction.response.send_message(f"❌ {membre.mention} ne possède pas cette carte.", ephemeral=True)
        return

    carte_offerte = user_inv[idx]
    embed = discord.Embed(title="🤝 Proposition d'échange", description=f"{interaction.user.mention} propose **{carte_offerte['nom']}** contre ta carte **{nom_carte_voulue}**.", color=discord.Color.gold())
    embed.set_thumbnail(url=carte_offerte["image"])

    view = TradeView(bot, interaction.user, membre, carte_offerte, nom_carte_voulue, idx)
    await interaction.response.send_message(content=f"{membre.mention}, tu as une proposition !", embed=embed, view=view)

@bot.tree.command(name="solde", description="Voir ton solde de pièces d'or.")
async def solde(interaction: discord.Interaction, membre: discord.Member = None):
    cible = membre or interaction.user
    or_actuel = bot.user_money.get(cible.id, 0)
    embed = discord.Embed(title=f"💰 Portefeuille de {cible.name}", description=f"**{or_actuel} pièces d'or**", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="donner_or", description="[Admin] Donner de l'or.")
@app_commands.checks.has_permissions(administrator=True)
async def donner_or(interaction: discord.Interaction, membre: discord.Member, montant: int):
    bot.user_money[membre.id] = max(0, bot.user_money.get(membre.id, 0) + montant)
    await interaction.response.send_message(f"🪙 Solde de {membre.mention} mis à jour : **{bot.user_money[membre.id]} pièces**.", ephemeral=True)

@bot.tree.command(name="work", description="Travailler pour gagner de l'or (toutes les 4h).")
async def work(interaction: discord.Interaction):
    user_id = interaction.user.id
    maintenant = datetime.now()
    if user_id in bot.dernier_work and maintenant < bot.dernier_work[user_id] + timedelta(hours=4):
        restant = (bot.dernier_work[user_id] + timedelta(hours=4)) - maintenant
        h, m = int(restant.total_seconds() // 3600), int((restant.total_seconds() % 3600) // 60)
