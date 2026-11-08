import discord
from discord.ext import commands
from discord import app_commands
import os

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
        self.quiz_list = [
            {
                "question": "Quel est le langage principal utilisé pour coder marcobot ?",
                "reponse": "python"
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
# GESTION DES QUÊTES JOURNALIÈRES
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
# GESTION DES QUIZ
# ==========================================

@bot.tree.command(name="ajouter_quiz", description="[Admin] Crée une nouvelle question de quiz.")
@app_commands.describe(question="La question à poser", reponse="La bonne réponse attendue")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_quiz(interaction: discord.Interaction, question: str, reponse: str):
    bot.quiz_list.append({
        "question": question,
        "reponse": reponse.lower().strip()
    })
    
    embed = discord.Embed(
        title="❓ Quiz ajouté avec succès !",
        description=f"**Question :** {question}\n**Réponse :** {reponse}",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="quiz", description="[Admin/Utilisateur] Lance une question de quiz aléatoire !")
async def quiz(interaction: discord.Interaction):
    if not bot.quiz_list:
        await interaction.response.send_message("❌ Il n'y a aucun quiz disponible pour le moment.", ephemeral=True)
        return

    import random
    q_data = random.choice(bot.quiz_list)

    embed = discord.Embed(
        title="🧠 C'est l'heure du Quiz !",
        description=f"**{q_data['question']}**",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Réponds directement dans ce salon en écrivant ta réponse !")
    await interaction.response.send_message(embed=embed)

    def check(m):
        return m.channel == interaction.channel and not m.author.bot

    try:
        msg = await bot.wait_for('message', timeout=20.0, check=check)
        if msg.content.lower().strip() == q_data['reponse']:
            await msg.reply(f"🎉 Bravo {msg.author.mention} ! C'était la bonne réponse (`{q_data['reponse']}`) !")
        else:
            await msg.reply(f"❌ Dommage {msg.author.mention}, ce n'est pas la bonne réponse.")
    except asyncio.TimeoutError:
        await interaction.followup.send("⏰ Temps écoulé ! Personne n'a répondu à temps.")


# Gestion des erreurs de permissions pour les commandes admin
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
