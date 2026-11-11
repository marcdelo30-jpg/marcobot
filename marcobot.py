@bot.tree.command(name="work", description="Travailler pour gagner un petit peu d'or (toutes les 6h).")
async def work(interaction: discord.Interaction):
    user_id = interaction.user.id
    maintenant = datetime.now()
    
    # On passe le cooldown à 6 heures par exemple
    if user_id in bot.dernier_work and maintenant < bot.dernier_work[user_id] + timedelta(hours=6):
        restant = (bot.dernier_work[user_id] + timedelta(hours=6)) - maintenant
        h, m = int(restant.total_seconds() // 3600), int((restant.total_seconds() % 3600) // 60)
        await interaction.response.send_message(f"⏳ Tu es fatigué. Reviens dans {h}h et {m}min pour retravailler.", ephemeral=True)
        return

    bot.dernier_work[user_id] = maintenant
    
    # Gain réduit entre 5 et 25 pièces d'or au lieu de 20 et 100
    gain = random.randint(5, 25)
    bot.user_money[user_id] = bot.user_money.get(user_id, 0) + gain

    embed = discord.Embed(
        title="💼 Journée de travail terminée", 
        description=f"Tu as accompli une petite tâche et gagné **{gain} pièces d'or** !", 
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)
