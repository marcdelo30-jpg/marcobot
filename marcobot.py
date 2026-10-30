import os
import discord
from discord import app_commands

# Ton ID de serveur Discord
GUILD_ID = discord.Object(id=1359606058922017001)

# Liste stockant les questions créées dynamiquement par les admins
QUESTIONS_LIST = [
    {
        "question": "Quelle est la capitale de la France ?",
        "options": ["1️⃣ Paris", "2️⃣ Londres", "3️⃣ Berlin"],
        "correct": 0
    }
]

# Liste des ID Discord des membres du Staff
STAFF_IDS = [
    1532919042837315654, 
]

# Liste des ID Discord des Animateurs
ANIMATEURS_IDS = [
    1478789840270135406, 1524068660589625404, 1521936013017223408 
]

class QuizView(discord.ui.View):
    def __init__(self, correct_index):
        super().__init__(timeout=None)
        self.correct_index = correct_index

    @discord.ui.button(label="1️⃣ Choix 1", style=discord.ButtonStyle.primary)
    async def btn_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.check_answer(interaction, 0)

    @discord.ui.button(label="2️⃣ Choix 2", style=discord.ButtonStyle.primary)
    async def btn_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.check_answer(interaction, 1)

    @discord.ui.button(label="3️⃣ Choix 3", style=discord.ButtonStyle.primary)
    async def btn_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.check_answer(interaction, 2)

    async def check_answer(self, interaction: discord.Interaction, chosen_index):
        if chosen_index == self.correct_index:
            await interaction.response.send_message("Bravo ! C'est la bonne réponse 🎉", ephemeral=True)
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)

            message_alerte = f"🏆 **Alerte Quiz !** L'utilisateur **{interaction.user}** a réussi à trouver la bonne réponse sur le serveur **{interaction.guild.name}** !"
            tous_les_destinataires = STAFF_IDS + ANIMATEURS_IDS

            for user_id in tous_les_destinataires:
                try:
                    user_obj = await interaction.client.fetch_user(user_id)
                    if user_obj:
                        await user_obj.send(message_alerte)
                except Exception as e:
                    print(f"Erreur lors de l'envoi du MP à l'utilisateur {user_id} : {e}")
        else:
            await interaction.response.send_message("Dommage, ce n'est pas la bonne réponse ❌", ephemeral=True)

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Copie et synchronise les commandes pour qu'elles s'affichent sur le profil et sur le serveur
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)
        await self.tree.sync()  # Synchronisation globale pour le profil
        print(f"Commandes synchronisées pour {self.user}")

client = MyBot()

@client.event
async def on_ready():
    print(f"Connecté en tant que {client.user} (ID: {client.user.id})")

# 1. COMMANDE QUIZ (Réservée aux Administrateurs)
@client.tree.command(name="quiz", description="[Admin] Lance la question du quiz !", guild=GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def quiz(interaction: discord.Interaction):
    if not QUESTIONS_LIST:
        await interaction.response.send_message("Aucune question disponible pour le moment !", ephemeral=True)
        return

    q = QUESTIONS_LIST[-1]
    view = QuizView(correct_index=q["correct"])
    
    view.children[0].label = q["options"][0]
    view.children[1].label = q["options"][1]
    view.children[2].label = q["options"][2]

    await interaction.response.send_message(f"**Question :** {q['question']}", view=view)

@quiz.error
async def quiz_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Seuls les administrateurs peuvent lancer le quiz.", ephemeral=True)

# 2. COMMANDE AJOUTER QUIZ (Réservée aux Administrateurs)
@client.tree.command(name="ajouter_quiz", description="[Admin] Crée une nouvelle question de quiz", guild=GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_quiz(interaction: discord.Interaction, question: str, choix1: str, choix2: str, choix3: str, bonne_reponse_numero: int):
    if bonne_reponse_numero not in [1, 2, 3]:
        await interaction.response.send_message("Le numéro de la bonne réponse doit être 1, 2 ou 3 !", ephemeral=True)
        return

    QUESTIONS_LIST.append({
        "question": question,
        "options": [choix1, choix2, choix3],
        "correct": bonne_reponse_numero - 1
    })

    await interaction.response.send_message(f"✅ Question ajoutée avec succès !\n**{question}**", ephemeral=True)

@ajouter_quiz.error
async def ajouter_quiz_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Seuls les administrateurs peuvent créer de nouvelles questions.", ephemeral=True)

# 3. COMMANDE AJOUTER QUÊTE (Réservée aux Administrateurs)
@client.tree.command(name="ajouter_quete", description="[Admin] Écris et lance une quête sur le serveur !", guild=GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_quete(interaction: discord.Interaction, texte_de_la_quete: str):
    message_annonce = f"⚔️ **NOUVELLE QUÊTE !** ⚔️\n\n{texte_de_la_quete}"
    await interaction.response.send_message(message_annonce, ephemeral=False)

@ajouter_quete.error
async def ajouter_quete_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Seuls les administrateurs peuvent ajouter une quête.", ephemeral=True)

client.run(os.getenv("DISCORD_TOKEN"))
