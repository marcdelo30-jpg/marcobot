import discord
from discord.ext import commands
from discord import app_commands
import os
import random

intents = discord.Intents.default()
intents.message_content = True

class MarcoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        # Listes pour stocker les quêtes et les quiz
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
        # Quiz avec des choix de boutons (question, options, bonne réponse)
        self.quiz_list = [
            {
                "question": "Quel est le langage principal utilisé pour coder marcobot ?",
                "options": ["Python", "JavaScript", "C++", "HTML"],
                "reponse": "Python"
            }
        ]

    async def setup_hook(self):
        # Synchronisation des commandes sur ton serveur
        GUILD_ID = discord.Object(id=1359606058922017001)  # Ton ID de serveur
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)
        print("Commandes synchronisées avec succès !")

bot = MarcoBot()

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")

# ==========================================
# 1. GESTION DES QUÊTES JOURNALIÈRES
# ==========================================

@bot.tree.command(name="ajouter_quete", description="[Admin] Ajouter une nouvelle quête journalière.")
@app_commands.describe(titre="Titre de la quête", description="Description de ce qu'il faut faire", recompense="Récompense à gagner")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_quete(interaction: discord.Interaction, titre: str, description: str, recompense: str):
    bot.quetes_list.append({
        "titre": titre,
        "description": description,
        "recompense": recompense
    })
    
    embed = discord.Embed(
        title="✅ Quête journalière ajoutée !",
        description=f"La quête **{titre}** a été enregistrée avec succès.",
        color=discord.Color.green()
    )
    embed.add_field(name="Détails", value=description, inline=False)
    embed.add_field(name="Récompense", value=recompense, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="quetes_journalieres", description="Connaître et recevoir des récompenses des quêtes journalières.")
async def quetes_journalieres(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌟 Quêtes Journalières",
        description="Connaître et recevoir des récompenses des quêtes journalières. Accomplis ces missions pour progresser !",
        color=discord.Color.gold()
    )
    
    if not bot.quetes_list:
        embed.add_field(name="Aucune quête", value="Il n'y a pas de quête journalière active pour le moment.", inline=False)
    else:
        for index, q in enumerate(bot.quetes_list, start=1):
            valeur_texte = f"**Objectif :** {q['description']}\n**Récompense :** {q['recompense']}"
            embed.add_field(name=f"Quête {index} : {q['titre']}", value=valeur_texte, inline=False)
            
    embed.set_footer(text="Reviens chaque jour pour de nouvelles quêtes !")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="gerer_quetes", description="[Admin] Gérer ou afficher le panneau de contrôle des quêtes.")
@app_commands.checks.has_permissions(administrator=True)
async def gerer_quetes(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Panneau de Gestion des Quêtes",
        description=f"Nombre total de quêtes actives : **{len(bot.quetes_list)}**\n\nUtilise `/ajouter_quete` pour en rajouter de nouvelles.",
        color=discord.Color.blue()
    )
    for i, q in enumerate(bot.quetes_list, start=1):
        embed.add_field(name=f"#{i} - {q['titre']}", value=f"Récompense: {q['recompense']}", inline=True)
        
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 2. GESTION DES QUIZ AVEC BOUTONS INTERACTIFS
# ==========================================

class QuizView(discord.ui.View):
    def __init__(self, options, bonne_reponse):
        super().__init__(timeout=30.0)
        self.bonne_reponse = bonne_reponse
        self.answered = False

        # Création dynamique des boutons pour chaque option de réponse
        for option in options:
            button = discord.ui.Button(label=option, style=discord.ButtonStyle.blurple)
            button.callback = self.create_callback(option)
            self.add_item(button)

    def create_callback(self, option_choisie):
        async def button_callback(interaction: discord.Interaction):
            if self.answered:
                await interaction.response.send_message("❌ Quelqu'un a déjà répondu à ce quiz !", ephemeral=True)
                return

            self.answered = True
            # Désactiver tous les boutons après la réponse
            for child in self.children:
                child.disabled = True

            if option_choisie == self.bonne_reponse:
                await interaction.response.edit_message(content=f"🎉 Bravo {interaction.user.mention} ! C'était la bonne réponse (**{self.bonne_reponse}**) !", view=self)
            else:
                await interaction.response.edit_message(content=f"❌ Dommage {interaction.user.mention}, ce n'était pas la bonne réponse. La bonne réponse était : **{self.bonne_reponse}**.", view=self)

        return button_callback

    async def on_timeout(self):
        if not self.answered:
            for child in self.children:
                child.disabled = True
            try:
                # Désactive les boutons si le temps est écoulé
                pass
            except Exception:
                pass

@bot.tree.command(name="ajouter_quiz", description="[Admin] Crée une nouvelle question de quiz avec choix multiples.")
@app_commands.describe(question="La question", opt1="Option 1", opt2="Option 2", opt3="Option 3", opt4="Option 4", bonne_reponse="La bonne réponse exacte parmi les options")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_quiz(interaction: discord.Interaction, question: str, opt1: str, opt2: str, opt3: str, opt4: str, bonne_reponse: str):
    options = [opt1, opt2, opt3, opt4]
    if bonne_reponse not in options:
        await interaction.response.send_message("❌ La bonne réponse doit correspondre exactement à l'une des 4 options proposées !", ephemeral=True)
        return

    bot.quiz_list.append({
        "question": question,
        "options": options,
        "reponse": bonne_reponse
    })
    
    embed = discord.Embed(
        title="❓ Quiz à choix multiples ajouté !",
        description=f"**Question :** {question}\n**Bonne réponse :** {bonne_reponse}",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="quiz", description="[Utilisateur] Lance une question de quiz interactive avec boutons !")
async def quiz(interaction: discord.Interaction):
    if not bot.quiz_list:
        await interaction.response.send_message("❌ Il n'y a aucun quiz disponible pour le moment.", ephemeral=True)
        return

    q_data = random.choice(bot.quiz_list)

    embed = discord.Embed(
        title="🧠 C'est l'heure du Quiz !",
        description=f"**{q_data['question']}**\n\n*Clique sur l'un des boutons ci-dessous pour répondre !*",
        color=discord.Color.blue()
    )
    
    view = QuizView(q_data["options"], q_data["reponse"])
    await interaction.response.send_message(embed=embed, view=view)


# Gestion des erreurs de permissions
@ajouter_quete.error
@gerer_quetes.error
@ajouter_quiz.error
async def admin_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Tu n'as pas les permissions d'administrateur pour utiliser cette commande.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Une erreur est survenue.", ephemeral=True)

# Lancement du bot
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Erreur : Le token DISCORD_TOKEN est introuvable dans les variables d'environnement.")
