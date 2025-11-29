import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os
import asyncio

# -------------------------------
# CONFIGURATION
# -------------------------------

ADMIN_ID = os.getenv("TOKEN_JOUEUR")  # <- Remplace par ton ID Discord
DATA_FILE = "players.json"
CODES_FILE = "codes.json"
STARTING_BALANCE = 100  # Coins de départ pour nouveaux joueurs

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)


# -------------------------------
# GESTION DES DONNÉES
# -------------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=4, ensure_ascii=False)

def load_codes():
    if not os.path.exists(CODES_FILE):
        return {}
    with open(CODES_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_codes():
    with open(CODES_FILE, "w", encoding="utf-8") as f:
        json.dump(codes, f, indent=4, ensure_ascii=False)

players = load_data()
codes = load_codes()

def get_balance(user_id):
    user_id_str = str(user_id)
    if user_id_str not in players:
        players[user_id_str] = STARTING_BALANCE
        save_data()
    return players.get(user_id_str, STARTING_BALANCE)

def set_balance(user_id, amount):
    players[str(user_id)] = max(0, amount)  # Empêcher les soldes négatifs
    save_data()


# -------------------------------
# COMMANDES JOUEURS
# -------------------------------

@bot.event
async def on_ready():
    print(f"{bot.user} est en ligne !")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} commandes synchronisées avec succès.")
    except Exception as e:
        print(f"❌ Erreur de synchronisation : {e}")


@bot.tree.command(name="balance", description="Voir ton solde")
async def balance(interaction: discord.Interaction):
    money = get_balance(interaction.user.id)
    await interaction.response.send_message(f"💰 {interaction.user.name}, tu as **{money:,} coins**.")


@bot.tree.command(name="help", description="Affiche toutes les commandes disponibles")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎰 CASINO BOT - GUIDE COMPLET",
        description="Voici toutes les commandes disponibles :",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="💰 Informations",
        value=(
            "`/balance` - Voir ton argent\n"
            "`/top` - Classement des 10 joueurs les plus riches\n"
            "`/help` - Affiche ce message"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎮 Jeux de Casino",
        value=(
            "`/coinflip [mise]` - Pile ou face (x2)\n"
            "`/roulette [mise]` - Roulette européenne (couleur x2, numéro x36)\n"
            "`/slots [mise]` - Machine à sous (x5)\n"
            "`/blackjack [mise]` - Blackjack contre le croupier (x2 ou x2.5)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎟️ Codes Promo",
        value="`/redeem [code]` - Utiliser un code promo",
        inline=False
    )
    
    embed.add_field(
        name="📋 Règles",
        value=(
            "• Mise minimum : **100 coins**\n"
            "• Solde de départ : **0 coins**\n"
            "• Blackjack naturel : **x2.5**\n"
            "• Les codes promo sont utilisables **1 fois par joueur**"
        ),
        inline=False
    )
    
    embed.set_footer(text="🎲 Bonne chance au casino !")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="top", description="Classement des 10 joueurs les plus riches")
async def top(interaction: discord.Interaction):
    if not players:
        return await interaction.response.send_message("📭 Aucun joueur enregistré pour le moment.")
    
    sorted_players = sorted(players.items(), key=lambda x: x[1], reverse=True)[:10]
    
    embed = discord.Embed(
        title="🏆 TOP 10 JOUEURS LES PLUS RICHES",
        color=discord.Color.gold()
    )
    
    medals = ["🥇", "🥈", "🥉"]
    description = ""
    
    for i, (user_id, money) in enumerate(sorted_players):
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
    code = code.upper()
    
    if code not in codes:
        return await interaction.response.send_message("❌ Ce code n'existe pas.")
    
    code_data = codes[code]
    
    if not code_data["active"]:
        return await interaction.response.send_message("❌ Ce code a été désactivé.")
    
    user_id = str(interaction.user.id)
    
    if user_id in code_data["used_by"]:
        return await interaction.response.send_message("❌ Tu as déjà utilisé ce code.")
    
    amount = code_data["amount"]
    money = get_balance(interaction.user.id)
    set_balance(interaction.user.id, money + amount)
    
    codes[code]["used_by"].append(user_id)
    save_codes()
    
    usage_info = "♾️ (réutilisable par d'autres)" if code_data["infinite"] else "🔒 (usage unique)"
    await interaction.response.send_message(
        f"✅ Code **{code}** utilisé ! {usage_info}\n"
        f"💰 Tu as reçu **{amount:,} coins** !\n"
        f"💵 Nouveau solde : **{money + amount:,} coins**"
    )


@bot.tree.command(name="coinflip", description="Parie sur pile ou face")
@app_commands.describe(mise="Montant à miser")
async def coinflip(interaction: discord.Interaction, mise: int):
    if mise < 100:
        return await interaction.response.send_message("❌ La mise minimum est 100 coins.")
    
    money = get_balance(interaction.user.id)
    if mise > money:
        return await interaction.response.send_message(f"❌ Tu n'as que {money:,} coins.")
    
    view = discord.ui.View(timeout=30)
    
    async def coinflip_callback(button_interaction: discord.Interaction, choix: str):
        if button_interaction.user.id != interaction.user.id:
            return await button_interaction.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
        
        for item in view.children:
            item.disabled = True
        
        await button_interaction.response.edit_message(content="🪙 La pièce tourne... 🌀", view=view)
        await asyncio.sleep(1.5)
        
        resultat = random.choice(["pile", "face"])
        money_now = get_balance(interaction.user.id)
        
        if resultat == choix:
            set_balance(interaction.user.id, money_now + mise)
            await button_interaction.edit_original_response(
                content=f"🎉 **{resultat.upper()} !** Tu as gagné **{mise:,} coins** !\n💰 Nouveau solde : **{money_now + mise:,} coins**",
                view=view
            )
        else:
            set_balance(interaction.user.id, money_now - mise)
            await button_interaction.edit_original_response(
                content=f"💀 **{resultat.upper()} !** Tu as perdu **{mise:,} coins**...\n💰 Nouveau solde : **{money_now - mise:,} coins**",
                view=view
            )
    
    pile_button = discord.ui.Button(label="🟢 PILE", style=discord.ButtonStyle.primary)
    async def pile_callback(button_interaction: discord.Interaction):
        await coinflip_callback(button_interaction, "pile")
    pile_button.callback = pile_callback
    
    face_button = discord.ui.Button(label="🔴 FACE", style=discord.ButtonStyle.success)
    async def face_callback(button_interaction: discord.Interaction):
        await coinflip_callback(button_interaction, "face")
    face_button.callback = face_callback
    
    view.add_item(pile_button)
    view.add_item(face_button)
    
    await interaction.response.send_message(
        f"🎲 **COINFLIP** - Mise : {mise:,} coins\nChoisis **PILE** ou **FACE** :",
        view=view
    )


@bot.tree.command(name="roulette", description="Parie sur la roulette")
@app_commands.describe(mise="Montant à miser")
async def roulette(interaction: discord.Interaction, mise: int):
    if mise < 100:
        return await interaction.response.send_message("❌ La mise minimum est 100 coins.")
    
    money = get_balance(interaction.user.id)
    if mise > money:
        return await interaction.response.send_message(f"❌ Tu n'as que {money:,} coins.")

    view = discord.ui.View(timeout=60)
    
    select_menu = discord.ui.Select(
        placeholder="🎯 Choisis ton type de pari...",
        options=[
            discord.SelectOption(label="🔴 Rouge (x2)", value="rouge", emoji="🔴"),
            discord.SelectOption(label="⚫ Noir (x2)", value="noir", emoji="⚫"),
            discord.SelectOption(label="🟢 Zéro (x36)", value="0", emoji="🟢"),
            discord.SelectOption(label="➗ Pair (x2)", value="pair", emoji="2️⃣"),
            discord.SelectOption(label="➗ Impair (x2)", value="impair", emoji="1️⃣"),
            discord.SelectOption(label="🔢 Numéro 1-18 (x2)", value="low", emoji="🔉"),
            discord.SelectOption(label="🔢 Numéro 19-36 (x2)", value="high", emoji="🔈"),
        ]
    )
    
    async def select_callback(select_interaction: discord.Interaction):
        if select_interaction.user.id != interaction.user.id:
            return await select_interaction.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
        
        choice = select_menu.values[0]
        await play_roulette(select_interaction, choice)
    
    select_menu.callback = select_callback
    view.add_item(select_menu)
    
    async def play_roulette(button_interaction: discord.Interaction, choice: str):
        for item in view.children:
            item.disabled = True
        
        await button_interaction.response.edit_message(content="🎰 La roulette tourne... 🌀", view=None)
        await asyncio.sleep(1)
        await button_interaction.edit_original_response(content="🎰 La bille roule... 🔄")
        await asyncio.sleep(1)
        
        resultat_num = random.randint(0, 36)
        
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
            emoji = "⚫"
        
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
        
        if gagne:
            gain = mise * multiplicateur
            set_balance(interaction.user.id, money_now + gain)
            await button_interaction.edit_original_response(
                content=f"🎰 La bille s'arrête sur : {emoji} **{resultat_num}** {emoji}\n\n🎉 **GAGNÉ !** Tu remportes **{gain:,} coins** (x{multiplicateur}) !\n💰 Nouveau solde : **{money_now + gain:,} coins**"
            )
        else:
            set_balance(interaction.user.id, money_now - mise)
            await button_interaction.edit_original_response(
                content=f"🎰 La bille s'arrête sur : {emoji} **{resultat_num}** {emoji}\n\n💔 **Perdu !** Tu perds **{mise:,} coins**.\n💰 Nouveau solde : **{money_now - mise:,} coins**"
            )
    
    await interaction.response.send_message(
        f"🎰 **ROULETTE** - Mise : {mise:,} coins\n🎯 Choisis ton type de pari :",
        view=view
    )


@bot.tree.command(name="slots", description="Machine à sous")
@app_commands.describe(mise="Montant à miser")
async def slots(interaction: discord.Interaction, mise: int):
    if mise < 100:
        return await interaction.response.send_message("❌ La mise minimum est 100 coins.")
    
    money = get_balance(interaction.user.id)
    if mise > money:
        return await interaction.response.send_message(f"❌ Tu n'as que {money:,} coins.")

    symbols = ["🍒", "🍋", "⭐", "🔔", "7️⃣"]
    
    await interaction.response.send_message("🎰 Lancement des rouleaux...")
    await asyncio.sleep(0.5)
    
    r1 = random.choice(symbols)
    await interaction.edit_original_response(content=f"🎰 | {r1} | ❓ | ❓ |")
    await asyncio.sleep(0.7)
    
    r2 = random.choice(symbols)
    await interaction.edit_original_response(content=f"🎰 | {r1} | {r2} | ❓ |")
    await asyncio.sleep(0.7)
    
    r3 = random.choice(symbols)
    await interaction.edit_original_response(content=f"🎰 | {r1} | {r2} | {r3} |")
    await asyncio.sleep(1)

    if r1 == r2 == r3:
        gain = mise * 5
        set_balance(interaction.user.id, money + gain)
        await interaction.edit_original_response(
            content=f"🎰 | {r1} | {r2} | {r3} |\n\n🎉 **JACKPOT !** Tu gagnes **{gain:,} coins** !\n💰 Nouveau solde : **{money + gain:,} coins**"
        )
    else:
        set_balance(interaction.user.id, money - mise)
        await interaction.edit_original_response(
            content=f"🎰 | {r1} | {r2} | {r3} |\n\n💀 Perdu ! Tu perds **{mise:,} coins**.\n💰 Nouveau solde : **{money - mise:,} coins**"
        )


# -------------------------------
# BLACKJACK
# -------------------------------

class BlackjackGame:
    def __init__(self):
        self.deck = []
        self.player_hand = []
        self.dealer_hand = []
        self.create_deck()
    
    def create_deck(self):
        suits = ["♤", "♥️", "♦️", "♧"]
        values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        self.deck = [f"{value}{suit}" for suit in suits for value in values]
        random.shuffle(self.deck)
    
    def draw_card(self):
        if len(self.deck) == 0:
            self.create_deck()
        return self.deck.pop()
    
    def card_value(self, card):
        value = card[:-2] if len(card) == 3 else card[0]
        if value in ["J", "Q", "K"]:
            return 10
        elif value == "A":
            return 11
        else:
            return int(value)
    
    def calculate_hand(self, hand):
        total = sum(self.card_value(card) for card in hand)
        aces = sum(1 for card in hand if card[0] == "A")
        
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total
    
    def is_blackjack(self, hand):
        return len(hand) == 2 and self.calculate_hand(hand) == 21
    
    def dealer_play(self):
        while self.calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(self.draw_card())


@bot.tree.command(name="blackjack", description="Joue au Blackjack")
@app_commands.describe(mise="Montant à miser")
async def blackjack(interaction: discord.Interaction, mise: int):
    if mise < 100:
        return await interaction.response.send_message("❌ La mise minimum est 100 coins.")
    
    money = get_balance(interaction.user.id)
    if mise > money:
        return await interaction.response.send_message(f"❌ Tu n'as que {money:,} coins.")
    
    game = BlackjackGame()
    game.player_hand = [game.draw_card(), game.draw_card()]
    game.dealer_hand = [game.draw_card(), game.draw_card()]
    
    player_total = game.calculate_hand(game.player_hand)
    dealer_visible = game.card_value(game.dealer_hand[0])
    
    if game.is_blackjack(game.player_hand):
        gain = int(mise * 2.5)
        set_balance(interaction.user.id, money + gain)
        return await interaction.response.send_message(
            f"🃏 **BLACKJACK !**\n\n"
            f"Tes cartes : {' '.join(game.player_hand)} = **21**\n"
            f"Croupier : {' '.join(game.dealer_hand)} = {game.calculate_hand(game.dealer_hand)}\n\n"
            f"🎉 Tu gagnes **{gain:,} coins** (x2.5) !\n"
            f"💰 Nouveau solde : **{money + gain:,} coins**"
        )
    
    view = discord.ui.View(timeout=120)
    
    async def update_game_message(button_interaction: discord.Interaction):
        player_total = game.calculate_hand(game.player_hand)
        content = (
            f"🃏 **BLACKJACK** - Mise : {mise:,} coins\n\n"
            f"**Tes cartes :** {' '.join(game.player_hand)} = **{player_total}**\n"
            f"**Croupier :** {game.dealer_hand[0]} 🎴 = {dealer_visible}+?\n\n"
        )
        return content
    
    async def hit_callback(button_interaction: discord.Interaction):
        if button_interaction.user.id != interaction.user.id:
            return await button_interaction.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
        
        game.player_hand.append(game.draw_card())
        player_total = game.calculate_hand(game.player_hand)
        
        if player_total > 21:
            for item in view.children:
                item.disabled = True
            
            money_now = get_balance(interaction.user.id)
            set_balance(interaction.user.id, money_now - mise)
            
            await button_interaction.response.edit_message(
                content=(
                    f"🃏 **BLACKJACK** - Mise : {mise:,} coins\n\n"
                    f"**Tes cartes :** {' '.join(game.player_hand)} = **{player_total}** 💥\n"
                    f"**Croupier :** {' '.join(game.dealer_hand)} = {game.calculate_hand(game.dealer_hand)}\n\n"
                    f"💀 **BUST !** Tu as dépassé 21 !\n"
                    f"Tu perds **{mise:,} coins**.\n"
                    f"💰 Nouveau solde : **{money_now - mise:,} coins**"
                ),
                view=view
            )
        else:
            content = await update_game_message(button_interaction)
            await button_interaction.response.edit_message(content=content, view=view)
    
    async def stand_callback(button_interaction: discord.Interaction):
        if button_interaction.user.id != interaction.user.id:
            return await button_interaction.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
        
        for item in view.children:
            item.disabled = True
        
        game.dealer_play()
        
        player_total = game.calculate_hand(game.player_hand)
        dealer_total = game.calculate_hand(game.dealer_hand)
        
        money_now = get_balance(interaction.user.id)
        
        if dealer_total > 21:
            gain = mise * 2
            set_balance(interaction.user.id, money_now + gain)
            result = f"🎉 **LE CROUPIER BUST !**\nTu gagnes **{gain:,} coins** !\n💰 Nouveau solde : **{money_now + gain:,} coins**"
        elif player_total > dealer_total:
            gain = mise * 2
            set_balance(interaction.user.id, money_now + gain)
            result = f"🎉 **VICTOIRE !**\nTu gagnes **{gain:,} coins** !\n💰 Nouveau solde : **{money_now + gain:,} coins**"
        elif player_total == dealer_total:
            result = f"🤝 **ÉGALITÉ !**\nTu récupères ta mise de {mise:,} coins.\n💰 Solde : **{money_now:,} coins**"
        else:
            set_balance(interaction.user.id, money_now - mise)
            result = f"💔 **DÉFAITE !**\nTu perds **{mise:,} coins**.\n💰 Nouveau solde : **{money_now - mise:,} coins**"
        
        await button_interaction.response.edit_message(
            content=(
                f"🃏 **BLACKJACK** - Mise : {mise:,} coins\n\n"
                f"**Tes cartes :** {' '.join(game.player_hand)} = **{player_total}**\n"
                f"**Croupier :** {' '.join(game.dealer_hand)} = **{dealer_total}**\n\n"
                f"{result}"
            ),
            view=view
        )
    
    hit_button = discord.ui.Button(label="🎴 HIT (Tirer)", style=discord.ButtonStyle.success)
    hit_button.callback = hit_callback
    
    stand_button = discord.ui.Button(label="✋ STAND (Rester)", style=discord.ButtonStyle.danger)
    stand_button.callback = stand_callback
    
    view.add_item(hit_button)
    view.add_item(stand_button)
    
    content = await update_game_message(interaction)
    await interaction.response.send_message(content=content, view=view)


# -------------------------------
# COMMANDES ADMIN
# -------------------------------

def admin_only():
    def predicate(interaction: discord.Interaction):
        return interaction.user.id == ADMIN_ID
    return app_commands.check(predicate)


@bot.tree.command(name="admin_list", description="[ADMIN] Liste tous les joueurs")
@admin_only()
async def admin_list(interaction: discord.Interaction):
    if not players:
        return await interaction.response.send_message("Aucun joueur enregistré.")
    
    msg = "📜 **Liste des joueurs :**\n\n"
    for uid, money in players.items():
        try:
            user = await bot.fetch_user(int(uid))
            msg += f"**{user.name}** ({uid}) → {money:,} coins\n"
        except:
            msg += f"User {uid} → {money:,} coins\n"
    await interaction.response.send_message(msg)


@bot.tree.command(name="admin_add", description="[ADMIN] Ajouter de l'argent")
@app_commands.describe(member="Membre à créditer", amount="Montant")
@admin_only()
async def admin_add(interaction: discord.Interaction, member: discord.Member, amount: int):
    money = get_balance(member.id)
    set_balance(member.id, money + amount)
    await interaction.response.send_message(f"✔️ Ajouté {amount:,} coins à {member.name}.")


@bot.tree.command(name="admin_remove", description="[ADMIN] Retirer de l'argent")
@app_commands.describe(member="Membre à débiter", amount="Montant")
@admin_only()
async def admin_remove(interaction: discord.Interaction, member: discord.Member, amount: int):
    money = get_balance(member.id)
    set_balance(member.id, max(0, money - amount))
    await interaction.response.send_message(f"✔️ Retiré {amount:,} coins à {member.name}.")


@bot.tree.command(name="admin_reset", description="[ADMIN] Reset l'argent d'un joueur")
@app_commands.describe(member="Membre à reset")
@admin_only()
async def admin_reset(interaction: discord.Interaction, member: discord.Member):
    set_balance(member.id, STARTING_BALANCE)
    await interaction.response.send_message(f"♻️ Argent de {member.name} remis à {STARTING_BALANCE:,} coins.")


@bot.tree.command(name="admin_createcode", description="[ADMIN] Créer un code promo")
@app_commands.describe(
    code="Le code (ex: BIENVENUE)",
    amount="Montant de coins",
    infinite="Utilisable à l'infini ? (True/False)"
)
@admin_only()
async def admin_createcode(interaction: discord.Interaction, code: str, amount: int, infinite: bool):
    code = code.upper()
    
    if code in codes:
        return await interaction.response.send_message(f"❌ Le code **{code}** existe déjà.")
    
    codes[code] = {
        "amount": amount,
        "infinite": infinite,
        "active": True,
        "used_by": []
    }
    save_codes()
    
    usage_type = "♾️ infini" if infinite else "🔒 unique"
    await interaction.response.send_message(
        f"✅ Code **{code}** créé !\n"
        f"💰 Montant : {amount:,} coins\n"
        f"📋 Type : {usage_type}"
    )


@bot.tree.command(name="admin_deletecode", description="[ADMIN] Supprimer un code promo")
@app_commands.describe(code="Le code à supprimer")
@admin_only()
async def admin_deletecode(interaction: discord.Interaction, code: str):
    code = code.upper()
    
    if code not in codes:
        return await interaction.response.send_message(f"❌ Le code **{code}** n'existe pas.")
    
    del codes[code]
    save_codes()
    await interaction.response.send_message(f"🗑️ Code **{code}** supprimé.")


@bot.tree.command(name="admin_listcodes", description="[ADMIN] Liste tous les codes")
@admin_only()
async def admin_listcodes(interaction: discord.Interaction):
    if not codes:
        return await interaction.response.send_message("📭 Aucun code créé.")
    
    msg = "📜 **Liste des codes :**\n\n"
    for code_name, code_data in codes.items():
        status = "✅ Actif" if code_data["active"] else "❌ Désactivé"
        num_uses = len(code_data['used_by'])
        
        if code_data["infinite"]:
            usage_type = f"♾️ Infini ({num_uses} joueurs l'ont utilisé)"
        else:
            usage_type = f"🔒 Usage unique ({num_uses} utilisations)"
        
        msg += f"**{code_name}**\n"
        msg += f"  ├ Montant : {code_data['amount']:,} coins\n"
        msg += f"  ├ Type : {usage_type}\n"
        msg += f"  └ Statut : {status}\n\n"
    
    await interaction.response.send_message(msg)


@bot.tree.command(name="admin_togglecode", description="[ADMIN] Activer/désactiver un code")
@app_commands.describe(code="Le code à activer/désactiver")
@admin_only()
async def admin_togglecode(interaction: discord.Interaction, code: str):
    code = code.upper()
    
    if code not in codes:
        return await interaction.response.send_message(f"❌ Le code **{code}** n'existe pas.")
    
    codes[code]["active"] = not codes[code]["active"]
    save_codes()
    
    status = "activé ✅" if codes[code]["active"] else "désactivé ❌"
    await interaction.response.send_message(f"Le code **{code}** a été {status}.")


# -------------------------------
# LANCEMENT DU BOT
# -------------------------------
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")

    if TOKEN == 12:
        print("❌ ERREUR : Tu dois remplacer 'TON_TOKEN_ICI' par ton vrai token Discord !")
        print("👉 Récupère ton token sur : https://discord.com/developers/applications")
    else:
        bot.run(TOKEN)