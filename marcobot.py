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
                "description": "Envoyer des messages dans les salons du serveur.", 
                "recompense_or": 50
            },
            {
                "titre": "🎮 Jouer avec la communauté", 
                "description": "Participer à une session vocale.", 
                "recompense_or": 100
            }
        ]
        
        self.quiz_list = [
            {
                "question": "Quel est le langage principal utilisé pour coder marcobot ?",
                "options": ["Python", "JavaScript", "C++", "HTML"],
                "reponse": "Python"
            }
        ]

        # Base de données des cartes avec liens d'images
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

        self.user_inventories = {}
        self.dernier_tirage = {}
        self.user_money = {}
        self.dernier_work = {}
        self.quetes_validees = {} # user_id -> liste des quêtes accomplies

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
# 1. GESTION DES QUÊTES (AJOUT, SUPPRESSION, BOUTONS)
# ==========================================

class DynamicQueteView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot_instance = bot_instance

        for index, quete in enumerate(self.bot_instance.quetes_list):
            button = discord.ui.Button(
                label=f"🎁 Réclamer : {quete['titre']}", 
                style=discord.ButtonStyle.green, 
                custom_id=f"quete_dyn_{index}"
            )
            button.callback = self.create_callback(index)
            self.add_item(button)

    def create_callback(self, index):
        async def button_callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            
            if index >= len(self.bot_instance.quetes_list):
                await interaction.response.send_message("❌ Cette quête n'existe plus.", ephemeral=True)
                return

            quete = self.bot_instance.quetes_list[index]

            if user_id not in self.bot_instance.quetes_validees:
                self.bot_instance.quetes_validees[user_id] = []

            aujourdhui = datetime.now().strftime("%Y-%m-%d")
            cle_quete = f"{index}_{aujourdhui}"

            if cle_quete in self.bot_instance.quetes_validees[user_id]:
                await interaction.response.send_message("⏳ Tu as déjà validé cette quête aujourd'hui ! Reviens demain.", ephemeral=True)
                return

            self.bot_instance.quetes_validees[user_id].append(cle_quete)
            
            recompense = quete["recompense_or"]
            if user_id not in self.bot_instance.user_money:
                self.bot_instance.user_money[user_id] = 0
            self.bot_instance.user_money[user_id] += recompense

            embed = discord.Embed(
                title="🎉 Quête validée avec succès !",
                description=f"Tu as accompli la quête : **{quete['titre']}** !\nTu remportes **{recompense} pièces d'or**.",
                color=discord.Color.gold()
            )
            embed.add_field(name="Nouveau solde", value=f"**{self.bot_instance.user_money[user_id]} pièces d'or**", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        return button_callback

@bot.tree.command(name="quetes_journalieres", description="Voir les quêtes journalières et récupérer tes récompenses.")
async def quetes_journalieres(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌟 Quêtes Journalières",
        description="Accomplis les objectifs ci-dessous et clique sur le bouton correspondant pour récupérer ton or !",
        color=discord.Color.gold()
    )
    
    if not bot.quetes_list:
        embed.add_field(name="Aucune quête", value="Reviens plus tard !", inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        for i, q in enumerate(bot.quetes_list, start=1):
            embed.add_field(
                name=f"Quête #{i} : {q['titre']}", 
                value=f"**Objectif :** {q['description']}\n**Récompense :** {q['recompense_or']} pièces d'or", 
                inline=False
            )
        
        view = DynamicQueteView(bot)
        await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="ajouter_quete", description="[Admin] Ajouter une nouvelle quête journalière.")
@app_commands.describe(titre="Titre de la quête", description="Description", recompense_or="Montant en pièces d'or")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_quete(interaction: discord.Interaction, titre: str, description: str, recompense_or: int):
    bot.quetes_list.append({"titre": titre, "description": description, "recompense_or": recompense_or})
    await interaction.response.send_message(f"✅ Quête **{titre}** ajoutée avec succès !", ephemeral=True)

@bot.tree.command(name="supprimer_quete", description="[Admin] Supprimer une quête via son numéro.")
@app_commands.describe(numero="Numéro de la quête (ex: 1, 2...)")
@app_commands.checks.has_permissions(administrator=True)
async def supprimer_quete(interaction: discord.Interaction, numero: int):
    index = numero - 1
    if 0 <= index < len(bot.quetes_list):
        quete_supprimee = bot.quetes_list.pop(index)
        await interaction.response.send_message(f"🗑️ Quête **#{numero} - {quete_supprimee['titre']}** supprimée avec succès !", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Numéro de quête invalide. Vérifie le numéro avec `/quetes_journalieres`.", ephemeral=True)


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
# 3. CARTES POKÉMON & TIRAGE 24H
# ==========================================

@bot.tree.command(name="ajouter_carte", description="[Admin] Ajouter une carte avec son image.")
@app_commands.describe(nom="Nom", rarete="Commun/Rare/Épique/Légendaire", description="Description", lien_image="Lien direct de l'image")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_carte(interaction: discord.Interaction, nom: str, rarete: str, description: str, lien_image: str):
    bot.cartes_list.append({"nom": nom, "rarete": rarete.capitalize(), "description": description, "image": lien_image})
    await interaction.response.send_message(f"🃏 Carte **{nom}** ajoutée !", ephemeral=True)

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

@bot.tree.command(name="inventaire", description="Voir ton inventaire de cartes.")
async def inventaire(interaction: discord.Interaction):
    user_inv = bot.user_inventories.get(interaction.user.id, [])
    if not user_inv:
        await interaction.response.send_message("❌ Ton inventaire est vide.", ephemeral=True)
        return
    embed = discord.Embed(title=f"🎒 Inventaire de {interaction.user.name}", color=discord.Color.blurple())
    for idx, c in enumerate(user_inv, start=1):
        embed.add_field(name=f"#{idx} - {c['nom']} ({c['rarete']})", value=c['description'], inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 4. ÉCONOMIE (/work, /solde, /pile_ou_face)
# ==========================================

@bot.tree.command(name="solde", description="Voir ton solde de pièces d'or.")
async def solde(interaction: discord.Interaction, membre: discord.Member = None):
    cible = membre or interaction.user
    or_actuel = bot.user_money.get(cible.id, 0)
    embed = discord.Embed(title=f"💰 Portefeuille de {cible.name}", description=f"**{or_actuel} pièces d'or**", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="work", description="Travailler pour gagner de l'or (toutes les 4h).")
async def work(interaction: discord.Interaction):
    user_id = interaction.user.id
    maintenant = datetime.now()
    if user_id in bot.dernier_work and maintenant < bot.dernier_work[user_id] + timedelta(hours=4):
        restant = (bot.dernier_work[user_id] + timedelta(hours=4)) - maintenant
        h, m = int(restant.total_seconds() // 3600), int((restant.total_seconds() % 3600) // 60)
        await interaction.response.send_message(f"⏳ Tu es fatigué. Reviens dans {h}h et {m}min.", ephemeral=True)
        return

    bot.dernier_work[user_id] = maintenant
    gain = random.randint(20, 100)
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


TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Erreur : Token introuvable.")
