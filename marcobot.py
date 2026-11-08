import discord
from discord.ext import commands
from discord import app_commands
import os
import random

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Nécessaire pour récupérer les rôles et les membres du serveur

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

@bot.tree.command(name="supprimer_quete", description="[Admin] Supprimer une quête journalière via son numéro.")
@app_commands.describe(numero="Le numéro de la quête (visible dans /gerer_quetes)")
@app_commands.checks.has_permissions(administrator=True)
async def supprimer_quete(interaction: discord.Interaction, numero: int):
    index = numero - 1
    if 0 <= index < len(bot.quetes_list):
        quete_supprimee = bot.quetes_list.pop(index)
        embed = discord.Embed(
            title="🗑️ Quête supprimée",
            description=f"La quête **{quete_supprimee['titre']}** a été retirée avec succès.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("❌ Numéro de quête invalide. Utilise `/gerer_quetes` pour voir les bons numéros.", ephemeral=True)

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
            embed.add_field(name=f"Quête #{index} : {q['titre']}", value=valeur_texte, inline=False)
            
    embed.set_footer(text="Reviens chaque jour pour de nouvelles quêtes !")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="gerer_quetes", description="[Admin] Gérer ou afficher le panneau de contrôle des quêtes.")
@app_commands.checks.has_permissions(administrator=True)
async def gerer_quetes(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Panneau de Gestion des Quêtes",
        description=f"Nombre total de quêtes actives : **{len(bot.quetes_list)}**\n\nUtilise `/ajouter_quete` pour en ajouter ou `/supprimer_quete` pour en retirer.",
        color=discord.Color.blue()
    )
    for i, q in enumerate(bot.quetes_list, start=1):
        embed.add_field(name=f"#{i} - {q['titre']}", value=f"Récompense: {q['recompense']}", inline=True)
        
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 2. GESTION DES QUIZ AVEC NOTIFICATION ADMIN EN MP
# ==========================================

class QuizView(discord.ui.View):
    def __init__(self, options, bonne_reponse, question):
        super().__init__(timeout=30.0)
        self.bonne_reponse = bonne_reponse
        self.question = question
        self.answered = False

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
            for child in self.children:
                child.disabled = True

            if option_choisie == self.bonne_reponse:
                await interaction.response.edit_message(content=f"🎉 Bravo {interaction.user.mention} ! C'était la bonne réponse (**{self.bonne_reponse}**) !", view=self)
                
                # Envoi d'un message privé à tous les administrateurs du serveur
                guild = interaction.guild
                if guild:
                    for member in guild.members:
                        # Vérifie si le membre est administrateur (et n'est pas un bot)
                        if member.guild_permissions.administrator and not member.bot:
                            try:
                                admin_embed = discord.Embed(
                                    title="🔔 Bonne réponse à un Quiz !",
                                    description=f"Un membre a trouvé la bonne réponse sur le serveur **{guild.name}**.",
                                    color=discord.Color.gold()
                                )
                                admin_embed.add_field(name="Membre", value=f"{member.mention} ({interaction.user.name})", inline=False)
                                admin_embed.add_field(name="Question", value=self.question, inline=False)
                                admin_embed.add_field(name="Bonne réponse", value=self.bonne_reponse, inline=False)
                                await member.send(embed=admin_embed)
                            except discord.HTTPException:
                                # Ignore si les MP sont fermés pour cet admin
                                pass
            else:
                await interaction.response.edit_message(content=f"❌ Dommage {interaction.user.mention}, ce n'était pas la bonne réponse. La bonne réponse était : **{self.bonne_reponse}**.", view=self)

        return button_callback

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
    
    view = QuizView(q_data["options"], q_data["reponse"], q_data["question"])
    await interaction.response.send_message(embed=embed, view=view)


# Gestion des erreurs de permissions
@ajouter_quete.error
@supprimer_quete.error
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
