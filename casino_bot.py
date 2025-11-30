import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import json
import os
import asyncio
import string
from threading import Thread
from flask import Flask
from pymongo import MongoClient
from datetime import datetime

# -------------------------------
# SITE WEB FACADE POUR RENDER
# -------------------------------

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# -------------------------------
# CONFIGURATION
# -------------------------------

ADMIN_ID_STR = os.getenv('ADMIN_ID', '634627605966094347')
ADMIN_ID = int(ADMIN_ID_STR)

MONGODB_URI = os.getenv('MONGODB_URI')
if not MONGODB_URI:
    print("❌ ERREUR : Variable MONGODB_URI manquante !")
    exit(1)

mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['casino_bot']
players_collection = db['players']
codes_collection = db['codes']

print("✅ Connecté à MongoDB Atlas")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# -------------------------------
# GESTION DES DONNÉES (MONGODB)
# -------------------------------

def get_balance(user_id):
    user_data = players_collection.find_one({"user_id": str(user_id)})
    return user_data.get("balance", 0) if user_data else 0

def set_balance(user_id, amount):
    players_collection.update_one(
        {"user_id": str(user_id)},
        {"$set": {"balance": max(0, amount), "last_updated": datetime.utcnow()}},
        upsert=True
    )

def get_all_players():
    return {doc["user_id"]: doc["balance"] for doc in players_collection.find()}

def get_code(code_name):
    return codes_collection.find_one({"code": code_name.upper()})

def create_code(code_name, amount, infinite=False):
    codes_collection.insert_one({
        "code": code_name.upper(),
        "amount": amount,
        "infinite": infinite,
        "active": True,
        "used_by": [],
        "created_at": datetime.utcnow()
    })

def update_code(code_name, updates):
    codes_collection.update_one({"code": code_name.upper()}, {"$set": updates})

def delete_code(code_name):
    codes_collection.delete_one({"code": code_name.upper()})

def get_all_codes():
    return list(codes_collection.find())

def add_code_user(code_name, user_id):
    codes_collection.update_one({"code": code_name.upper()}, {"$push": {"used_by": str(user_id)}})

# -------------------------------
# COMMANDES JOUEURS
# -------------------------------

@bot.event
async def on_ready():
    print(f"{bot.user} est en ligne !")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash commands synchronisées.")
    except Exception as e:
        print(f"❌ Erreur de sync: {e}")

@bot.tree.command(name="balance", description="Voir ton argent")
async def balance(interaction: discord.Interaction):
    money = get_balance(interaction.user.id)
    await interaction.response.send_message(f"💰 {interaction.user.name}, tu as **{money} coins**.")

@bot.tree.command(name="help", description="Affiche toutes les commandes disponibles")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎰 **CASINO BOT - GUIDE COMPLET**",
        description="Voici toutes les commandes disponibles :",
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 **Informations**", value="`/balance` - Voir ton argent\n`/top` - Classement des 10 joueurs les plus riches\n`/help` - Affiche ce message", inline=False)
    embed.add_field(name="🎮 **Jeux de Casino**", value="`/coinflip [mise]` - Pile ou face (x2)\n`/roulette [mise]` - Roulette européenne (couleur x2, numéro x36)\n`/slots [mise]` - Machine à sous (x5)\n`/blackjack [mise]` - Blackjack contre le croupier (x2 ou x2.5)", inline=False)
    embed.add_field(name="🎟️ **Codes Promo**", value="`/redeem [code]` - Utiliser un code promo pour recevoir des coins", inline=False)
    embed.add_field(name="📋 **Règles Importantes**", value="• Mise minimum : **100 coins**\n• Blackjack naturel : **x2.5**\n• Les codes promo ne peuvent être utilisés qu'**une seule fois par personne**\n• Timeout des jeux : **30-120 secondes**", inline=False)
    embed.set_footer(text="🎲 Bonne chance au casino !")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="top", description="Classement des 10 joueurs les plus riches")
async def top(interaction: discord.Interaction):
    # Optimisé : Tri côté MongoDB pour éviter de charger tout en mémoire
    top_players = list(players_collection.find().sort("balance", -1).limit(10))
    if not top_players:
        return await interaction.response.send_message("📭 Aucun joueur n'a encore d'argent.")
    
    embed = discord.Embed(title="🏆 **TOP 10 JOUEURS LES PLUS RICHES**", color=discord.Color.gold())
    medals = ["🥇", "🥈", "🥉"]
    description = ""
    for i, doc in enumerate(top_players):
        user_id = doc["user_id"]
        money = doc["balance"]
        try:
            user = await bot.fetch_user(int(user_id))
            username = user.name
        except:
            username = f"Joueur #{user_id[:4]}"
        medal = medals[i] if i < 3 else f"**{i+1}.**"
        description += f"{medal} **{username}** — {money:,} coins\n"
    embed.description = description
    embed.set_footer(text="💰 Continue à jouer pour grimper dans le classement !")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="redeem", description="Utiliser un code promo")
@app_commands.describe(code="Le code à utiliser")
async def redeem(interaction: discord.Interaction, code: str):
    await interaction.response.defer()  # Ajouté pour éviter timeout
    code = code.upper()
    code_data = get_code(code)
    if not code_data:
        return await interaction.followup.send("❌ Ce code n'existe pas.")
    if not code_data["active"]:
        return await interaction.followup.send("❌ Ce code a été désactivé.")
    user_id = str(interaction.user.id)
    if not code_data["infinite"] and len(code_data["used_by"]) > 0:
        return await interaction.followup.send("❌ Ce code a déjà été utilisé par quelqu'un.")
    if user_id in code_data["used_by"]:
        return await interaction.followup.send("❌ Tu as déjà utilisé ce code.")
    amount = code_data["amount"]
    money = get_balance(interaction.user.id)
    set_balance(interaction.user.id, money + amount)
    add_code_user(code, user_id)
    usage_info = "♾️ (réutilisable par d'autres)" if code_data["infinite"] else "🔒 (usage unique total)"
    await interaction.followup.send(f"✅ Code **{code}** utilisé ! {usage_info}\n💰 Tu as reçu **{amount:,} coins** !\n💵 Nouveau solde : **{money + amount:,} coins**")

@bot.tree.command(name="coinflip", description="Parie sur pile ou face")
@app_commands.describe(mise="Montant à miser")
async def coinflip(interaction: discord.Interaction, mise: int):
    await interaction.response.defer()
    if mise < 100:
        return await interaction.followup.send("❌ La mise minimum est 100 coins.")
    money = get_balance(interaction.user.id)
    if mise > money:
        return await interaction.followup.send("❌ Tu n'as pas assez de coins.")
    view = discord.ui.View(timeout=30)
    async def coinflip_callback(button_interaction: discord.Interaction, choix: str):
        if button_interaction.user.id != interaction.user.id:
            return await button_interaction.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
        for item in view.children:
            item.disabled = True
        await button_interaction.response.edit_message(content="🪙 La pièce tourne... 🌀", view=view)
        await asyncio.sleep(1.5)
        if random.random() < 0.42:
            resultat = choix
        else:
            resultat = "face" if choix == "pile" else "pile"
        money_now = get_balance(interaction.user.id)
        if resultat == choix:
            set_balance(interaction.user.id, money_now + mise)
            await button_interaction.edit_original_response(content=f"🎉 **{resultat.upper()} !** Tu as gagné **{mise:,} coins** !\n💰 Nouveau solde : **{money_now + mise:,} coins**", view=view)
        else:
            set_balance(interaction.user.id, money_now - mise)
            await button_interaction.edit_original_response(content=f"💀 **{resultat.upper()} !** Tu as perdu **{mise:,} coins**...\n💰 Nouveau solde : **{money_now - mise:,} coins**", view=view)
    pile_button = discord.ui.Button(label="🪙 PILE", style=discord.ButtonStyle.primary)
    pile_button.callback = lambda i: coinflip_callback(i, "pile")
    face_button = discord.ui.Button(label="🪙 FACE", style=discord.ButtonStyle.success)
    face_button.callback = lambda i: coinflip_callback(i, "face")
    view.add_item(pile_button)
    view.add_item(face_button)
    await interaction.followup.send(f"🎲 **COINFLIP** - Mise : {mise:,} coins\nChoisis **PILE** ou **FACE** :\n\n📊 *Chances de gagner : 50%* | Gain potentiel : x2", view=view)

@bot.tree.command(name="roulette", description="Parie sur la roulette (nombre, couleur, pair/impair)")
@app_commands.describe(mise="Montant à miser")
async def roulette(interaction: discord.Interaction, mise: int):
    await interaction.response.defer()  # Ajouté
    if mise < 100:
        return await interaction.followup.send("❌ La mise minimum est 100 coins.")
    money = get_balance(interaction.user.id)
    if mise > money:
        return await interaction.followup.send("❌ Tu n'as pas assez de coins.")
    view = discord.ui.View(timeout=60)
    select_menu = discord.ui.Select(placeholder="🎯 Choisis ton type de pari...", options=[
        discord.SelectOption(label="🔴 Rouge (x2)", value="rouge"),
        discord.SelectOption(label="⚪ Noir (x2)", value="noir"),
        discord.SelectOption(label="🟢 Zéro (x36)", value="0"),
        discord.SelectOption(label="➗ Pair (x2)", value="pair"),
        discord.SelectOption(label="➗ Impair (x2)", value="impair"),
        discord.SelectOption(label="🔢 Numéro 1-18 (x2)", value="low"),
        discord.SelectOption(label="🔢 Numéro 19-36 (x2)", value="high"),
    ])
    async def select_callback(select_interaction: discord.Interaction):
        if select_interaction.user.id != interaction.user.id:
            return await select_interaction.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
        choice = select_menu.values[0]
        await play_roulette(select_interaction, choice)
    select_menu.callback = select_callback
    view.add_item(select_menu)
    await interaction.followup.send(f"🎰 **ROULETTE** - Mise : {mise:,} coins\n🎯 Choisis ton type de pari :\n\n📊 *Chances : Rouge/Noir 48.6% | Numéro 2.7%* | Gains : x2 ou x36", view=view)

    async def play_roulette(button_interaction: discord.Interaction, choice: str):
        for item in view.children:
            item.disabled = True
        await button_interaction.response.edit_message(content="🎰 La roulette tourne... 🌀", view=None)
        await asyncio.sleep(1)
        await button_interaction.edit_original_response(content="🎰 La bille roule... 🔄")
        await asyncio.sleep(1)
        if random.random() < 0.06:
            resultat_num = 0
        else:
            resultat_num = random.randint(1, 36)
        rouges = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
        noirs = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
        if resultat_num == 0:
            resultat_couleur = "vert"
            emoji = "🟢"
        elif resultat_num in rouges:
            resultat_couleur = "rouge"
            emoji = "🔴"
        else:
            resultat_couleur = "noir"
            emoji = "⚪"
        money_now = get_balance(interaction.user.id)
        gagne = False
        multiplicateur = 0
        if choice == "rouge" and resultat_couleur == "rouge":
            gagne = True
            multiplicateur = 2
        elif choice == "noir" and resultat_couleur == "noir":
            gagne = True
            multiplicateur = 2
        elif choice == "0" and resultat_num == 0:
            gagne = True
            multiplicateur = 36
        elif choice == "pair" and resultat_num > 0 and resultat_num % 2 == 0:
            gagne = True
            multiplicateur = 2
        elif choice == "impair" and resultat_num % 2 == 1:
            gagne = True
            multiplicateur = 2
        elif choice == "low" and 1 <= resultat_num <= 18:
            gagne = True
            multiplicateur = 2
        elif choice == "high" and 19 <= resultat_num <= 36:
            gagne = True
            multiplicateur = 2
        elif choice.isdigit() and int(choice) == resultat_num:
            gagne = True
            multiplicate
