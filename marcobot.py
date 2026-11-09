import discord
from discord.ext import commands
from discord import app_commands
import os
import random

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Nécessaire pour les MP et la gestion des membres

class MarcoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
        # 1. Quêtes journalières
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
        
        # 2. Quiz
        self.quiz_list = [
            {
                "question": "Quel est le langage principal utilisé pour coder marcobot ?",
                "options": ["Python", "JavaScript", "C++", "HTML"],
                "reponse": "Python"
            }
        ]

        # 3. Base de données globale des cartes du serveur
        self.cartes_list = [
            {"nom": "Pikachu", "rarete": "Commun", "description": "Une souris électrique pleine d'énergie."},
            {"nom": "Bulbizarre", "rarete": "Commun", "description": "Il a une graine plantée sur son dos."},
            {"nom": "Dracaufeu", "rarete": "Légendaire", "description": "Un dragon de feu surpuissant et redouté."},
            {"nom": "Mewtwo", "rarete": "Épique", "description": "Un Pokémon créé par manipulation génétique."},
            {"nom": "Arcanin", "rarete": "Rare", "description": "Un Pokémon chien majestueux et très rapide."}
        ]

        # 4. Inventaires personnels des utilisateurs (Dictionnaire : user_id -> liste de cartes)
        self.user_inventories = {}

    async def setup_hook(self):
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
                                admin_embed = discord.Embed(
                                    title="🔔 Bonne réponse à un Quiz !",
                                    description=f"Un membre a trouvé la bonne réponse sur **{guild.name}**.",
                                    color=discord.Color.gold()
                                )
                                admin_embed.add_field(name="Membre", value=f"{interaction.user.mention} ({interaction.user.name})", inline=False)
                                admin_embed.add_field(name="Question", value=self.question, inline=False)
                                admin_embed.add_field(name="Bonne réponse", value=self.bonne_reponse, inline=False)
                                await member.send(embed=admin_embed)
                            except discord.HTTPException:
                                pass
            else:
                await interaction.response.send_message(f"❌ Mauvaise réponse ! Vérifie tes messages privés.", ephemeral=True)
                try:
                    perdu_embed = discord.Embed(
                        title="❌ Raté pour le Quiz !",
                        description=f"Tu as donné une mauvaise réponse à la question sur le serveur **{interaction.guild.name}**.",
                        color=discord.Color.red()
                    )
                    perdu_embed.add_field(name="Question", value=self.question, inline=False)
                    perdu_embed.add_field(name="Ton choix", value=option_choisie, inline=False)
                    perdu_embed.set_footer(text="Le quiz est toujours actif dans le salon, tu peux retenter ta chance !")
                    await interaction.user.send(embed=perdu_embed)
                except discord.HTTPException:
                    pass

        return button_callback

@bot.tree.command(name="ajouter_quiz", description="[Admin] Crée une nouvelle question de quiz.")
@app_commands.describe(question="La question", opt1="Option 1", opt2="Option 2", opt3="Option 3", opt4="Option 4", bonne_reponse="La bonne réponse exacte")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_quiz(interaction: discord.Interaction, question: str, opt1: str, opt2: str, opt3: str, opt4: str, bonne_reponse: str):
    options = [opt1, opt2, opt3, opt4]
    if bonne_reponse not in options:
        await interaction.response.send_message("❌ La bonne réponse doit correspondre exactement à l'une des 4 options !", ephemeral=True)
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

@bot.tree.command(name="quiz", description="[Utilisateur] Lance une question de quiz interactive !")
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


# ==========================================
# 3. GESTION DES CARTES, TIRAGE (AVEC DOUBLE DROP FAIBLE) & ÉCHANGES
# ==========================================

@bot.tree.command(name="ajouter_carte", description="[Admin] Ajouter une carte Pokémon avec sa rareté.")
@app_commands.describe(nom="Nom du Pokémon", rarete="Commun, Rare, Épique ou Légendaire", description="Courte description")
@app_commands.checks.has_permissions(administrator=True)
async def ajouter_carte(interaction: discord.Interaction, nom: str, rarete: str, description: str):
    rarete_clean = rarete.capitalize()
    raretés_valides = ["Commun", "Rare", "Épique", "Légendaire"]
    
    if rarete_clean not in raretés_valides:
        await interaction.response.send_message("❌ Rareté invalide ! Choisis parmi : Commun, Rare, Épique, Légendaire.", ephemeral=True)
        return

    bot.cartes_list.append({
        "nom": nom,
        "rarete": rarete_clean,
        "description": description
    })

    embed = discord.Embed(
        title="🃏 Nouvelle carte Pokémon ajoutée !",
        description=f"La carte **{nom}** a été enregistrée dans la base du serveur.",
        color=discord.Color.green()
    )
    embed.add_field(name="Rareté", value=rarete_clean, inline=True)
    embed.add_field(name="Description", value=description, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="voir_cartes", description="Afficher toutes les cartes Pokémon disponibles sur le serveur.")
async def voir_cartes(interaction: discord.Interaction):
    if not bot.cartes_list:
        await interaction.response.send_message("❌ Aucune carte Pokémon enregistrée pour le moment.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📦 Catalogue des Cartes du Serveur",
        description="Voici toutes les cartes existantes, classées par rareté :",
        color=discord.Color.gold()
    )

    raretés_ordre = ["Légendaire", "Épique", "Rare", "Commun"]
    for rarete in raretés_ordre:
        cartes_filtrees = [c for c in bot.cartes_list if c["rarete"] == rarete]
        if cartes_filtrees:
            texte_cartes = ""
            for c in cartes_filtrees:
                texte_cartes += f"• **{c['nom']}** : *{c['description']}*\n"
            
            emoji = "🌟" if rarete == "Légendaire" else "🔥" if rarete == "Épique" else "✨" if rarete == "Rare" else "⚪"
            embed.add_field(name=f"{emoji} Rareté : {rarete}", value=texte_cartes, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tirer_carte", description="Tirer une carte aléatoire (avec une chance infime d'en obtenir deux) !")
async def tirer_carte(interaction: discord.Interaction):
    if not bot.cartes_list:
        await interaction.response.send_message("❌ Aucune carte disponible pour le tirage.", ephemeral=True)
        return

    user_id = interaction.user.id
    if user_id not in bot.user_inventories:
        bot.user_inventories[user_id] = []

    # FAIBLE PROBABILITÉ DE DOUBLON (ex: 10% de chance d'obtenir 2 cartes au lieu d'1)
    # Tu peux baisser à 0.05 pour 5% ou 0.01 pour 1%
    obtient_deux_cartes = random.random() < 0.10  

    if obtient_deux_cartes and len(bot.cartes_list) >= 2:
        cartes_tirees = random.sample(bot.cartes_list, 2) # Pioche 2 cartes différentes
    else:
        cartes_tirees = [random.choice(bot.cartes_list)]

    # Ajout des cartes dans l'inventaire de l'utilisateur
    for carte in cartes_tirees:
        bot.user_inventories[user_id].append(carte)

    # Création de l'affichage de l'embed
    if len(cartes_tirees) == 2:
        titre_embed = f"✨ DOUBLE CHANCE ! 2 cartes pour {interaction.user.name} !"
        desc_embed = f"Coup de bol incroyable ! Tu as obtenu deux cartes d'un coup :\n• **{cartes_tirees[0]['nom']}** (*{cartes_tirees[0]['rarete']}*)\n• **{cartes_tirees[1]['nom']}** (*{cartes_tirees[1]['rarete']}*)"
        couleur = discord.Color.gold()
    else:
        carte = cartes_tirees[0]
        titre_embed = f"🎴 Tirage de Carte pour {interaction.user.name}"
        desc_embed = f"Tu as tiré et gagné la carte **{carte['nom']}** !"
        
        couleurs = {
            "Légendaire": discord.Color.gold(),
            "Épique": discord.Color.purple(),
            "Rare": discord.Color.blue(),
            "Commun": discord.Color.light_grey()
        }
        couleur = couleurs.get(carte["rarete"], discord.Color.default())

    embed = discord.Embed(
        title=titre_embed,
        description=desc_embed,
        color=couleur
    )
    if len(cartes_tirees) == 1:
        embed.add_field(name="Rareté", value=cartes_tirees[0]["rarete"], inline=True)
        embed.add_field(name="Description", value=cartes_tirees[0]["description"], inline=False)
    
    embed.set_footer(text="Utilise /inventaire pour voir tes cartes possédées.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="inventaire", description="Afficher ton inventaire personnel de cartes Pokémon.")
async def inventaire(interaction: discord.Interaction):
    user_id = interaction.user.id
    user_inv = bot.user_inventories.get(user_id, [])

    if not user_inv:
        await interaction.response.send_message("❌ Ton inventaire est vide ! Utilise `/tirer_carte` pour en obtenir.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🎒 Inventaire de {interaction.user.name}",
        description="Voici les cartes Pokémon que tu possèdes :",
        color=discord.Color.blurple()
    )

    for idx, c in enumerate(user_inv, start=1):
        embed.add_field(name=f"#{idx} - {c['nom']} ({c['rarete']})", value=c['description'], inline=False)

    embed.set_footer(text="Utilise /echanger pour proposer un échange à un autre membre !")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Système d'échange interactif avec boutons ---
class TradeView(discord.ui.View):
    def __init__(self, bot_instance, emetteur, receveur, carte_offerte, carte_demandee, idx_offert):
        super().__init__(timeout=60.0)
        self.bot_instance = bot_instance
        self.emetteur = emetteur
        self.receveur = receveur
        self.carte_offerte = carte_offerte
        self.carte_demandee = carte_demandee
        self.idx_offert = idx_offert
        self.traite = False

    @discord.ui.button(label="Accepter l'échange", style=discord.ButtonStyle.green)
    async def accepter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receveur.id:
            await interaction.response.send_message("❌ Cet échange ne t'est pas destiné !", ephemeral=True)
            return

        if self.traite:
            await interaction.response.send_message("❌ Cet échange a déjà été traité.", ephemeral=True)
            return

        self.traite = True

        receveur_inv = self.bot_instance.user_inventories.get(self.receveur.id, [])
        carte_trouvee = None
        idx_demande = -1
        for i, c in enumerate(receveur_inv):
            if c['nom'].lower() == self.carte_demandee.lower():
                carte_trouvee = c
                idx_demande = i
                break

        if not carte_trouvee:
            await interaction.response.edit_message(content=f"❌ Échange annulé : {self.receveur.mention} ne possède plus la carte **{self.carte_demandee}** dans son inventaire.", view=None)
            return

        emetteur_inv = self.bot_instance.user_inventories.get(self.emetteur.id, [])
        if self.idx_offert >= len(emetteur_inv) or emetteur_inv[self.idx_offert]['nom'] != self.carte_offerte['nom']:
            await interaction.response.edit_message(content=f"❌ Échange annulé : {self.emetteur.mention} ne possède plus cette carte.", view=None)
            return

        c_offerte = emetteur_inv.pop(self.idx_offert)
        emetteur_inv.append(carte_trouvee)

        receveur_inv.pop(idx_demande)
        receveur_inv.append(c_offerte)

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="🤝 Échange réussi !",
            description=f"L'échange entre **{self.emetteur.name}** et **{self.receveur.name}** a été effectué avec succès.",
            color=discord.Color.green()
        )
        embed.add_field(name=f"Carte reçue par {self.emetteur.name}", value=f"**{carte_trouvee['nom']}**", inline=True)
        embed.add_field(name=f"Carte reçue par {self.receveur.name}", value=f"**{c_offerte['nom']}**", inline=True)

        await interaction.response.edit_message(content="", embed=embed, view=self)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.red)
    async def refuser(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receveur.id:
            await interaction.response.send_message("❌ Cet échange ne t'est pas destiné !", ephemeral=True)
            return

        if self.traite:
            await interaction.response.send_message("❌ Cet échange a déjà été traité.", ephemeral=True)
            return

        self.traite = True
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(content=f"❌ {self.receveur.mention} a refusé l'échange.", embed=None, view=self)

@bot.tree.command(name="echanger", description="Proposer d'échanger une carte de ton inventaire contre une carte d'un autre membre.")
@app_commands.describe(membre="Le membre avec qui échanger", numero_carte="Le numéro de ta carte dans /inventaire", nom_carte_voulue="Le nom exact de la carte que tu veux")
async def echanger(interaction: discord.Interaction, membre: discord.Member, numero_carte: int, nom_carte_voulue: str):
    if membre.id == interaction.user.id:
        await interaction.response.send_message("❌ Tu ne peux pas faire d'échange avec toi-même !", ephemeral=True)
        return

    if membre.bot:
        await interaction.response.send_message("❌ Tu ne peux pas échanger avec un bot !", ephemeral=True)
        return

    user_id = interaction.user.id
    emetteur_inv = bot.user_inventories.get(user_id, [])
    idx = numero_carte - 1

    if not (0 <= idx < len(emetteur_inv)):
        await interaction.response.send_message("❌ Numéro de carte invalide dans ton inventaire. Utilise `/inventaire` pour vérifier tes numéros.", ephemeral=True)
        return

    carte_offerte = emetteur_inv[idx]
    destinataire_inv = bot.user_inventories.get(membre.id, [])
    possede_carte = any(c['nom'].lower() == nom_carte_voulue.lower() for c in destinataire_inv)

    if not possede_carte:
        await interaction.response.send_message(f"❌ {membre.mention} ne possède pas la carte **{nom_carte_voulue}** dans son inventaire.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🤝 Proposition d'échange de cartes",
        description=f"{interaction.user.mention} souhaite faire un échange avec toi !",
        color=discord.Color.gold()
    )
    embed.add_field(name=f"Il te propose :", value=f"**{carte_offerte['nom']}** (*{carte_offerte['rarete']}*)", inline=False)
    embed.add_field(name=f"Il veut en échange ta carte :", value=f"**{nom_carte_voulue}**", inline=False)
    embed.set_footer(text="Clique sur un bouton ci-dessous pour accepter ou refuser.")

    view = TradeView(bot, interaction.user, membre, carte_offerte, nom_carte_voulue, idx)
    await interaction.response.send_message(content=f"{membre.mention}, tu as une proposition d'échange !", embed=embed, view=view)


# Gestion des erreurs de permissions admin
@ajouter_quete.error
@supprimer_quete.error
@gerer_quetes.error
@ajouter_quiz.error
@ajouter_carte.error
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
