import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os
import asyncio
import string
import string

# -------------------------------
# CONFIGURATION
# -------------------------------

ADMIN_ID = os.getenv("ADMIN_TOKEN")  # <- mets ton ID Discord ici
DATA_FILE = "players.json"
CODES_FILE = "codes.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)


# -------------------------------
# GESTION DES DONNÉES
# -------------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(players, f, indent=4)

def load_codes():
    if not os.path.exists(CODES_FILE):
        return {}
    with open(CODES_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_codes():
    with open(CODES_FILE, "w") as f:
        json.dump(codes, f, indent=4)

players = load_data()
codes = load_codes()

def get_balance(user_id):
    return players.get(str(user_id), 0)

def set_balance(user_id, amount):
    players[str(user_id)] = amount
    save_data()


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
    
    embed.add_field(
        name="💰 **Informations**",
        value=(
            "`/balance` - Voir ton argent\n"
            "`/top` - Classement des 10 joueurs les plus riches\n"
            "`/help` - Affiche ce message"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎮 **Jeux de Casino**",
        value=(
            "`/coinflip [mise]` - Pile ou face (x2)\n"
            "`/roulette [mise]` - Roulette européenne (couleur x2, numéro x36)\n"
            "`/slots [mise]` - Machine à sous (x5)\n"
            "`/blackjack [mise]` - Blackjack contre le croupier (x2 ou x2.5)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎟️ **Codes Promo**",
        value="`/redeem [code]` - Utiliser un code promo pour recevoir des coins",
        inline=False
    )
    
    embed.add_field(
        name="📋 **Règles Importantes**",
        value=(
            "• Mise minimum : **100 coins**\n"
            "• Blackjack naturel : **x2.5**\n"
            "• Les codes promo ne peuvent être utilisés qu'**une seule fois par personne**\n"
            "• Timeout des jeux : **30-120 secondes**"
        ),
        inline=False
    )
    
    embed.set_footer(text="🎲 Bonne chance au casino !")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="top", description="Classement des 10 joueurs les plus riches")
async def top(interaction: discord.Interaction):
    if not players:
        return await interaction.response.send_message("📭 Aucun joueur n'a encore d'argent.")
    
    # Trier les joueurs par argent (du plus riche au plus pauvre)
    sorted_players = sorted(players.items(), key=lambda x: x[1], reverse=True)[:10]
    
    embed = discord.Embed(
        title="🏆 **TOP 10 JOUEURS LES PLUS RICHES**",
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
    
    # Vérifier si le code est encore actif
    if not code_data["active"]:
        return await interaction.response.send_message("❌ Ce code a été désactivé.")
    
    user_id = str(interaction.user.id)
    
    # Si code à usage UNIQUE (pas infini), vérifier si QUELQU'UN l'a déjà utilisé
    if not code_data["infinite"]:
        if len(code_data["used_by"]) > 0:
            return await interaction.response.send_message("❌ Ce code a déjà été utilisé par quelqu'un.")
    
    # Si code INFINI, vérifier si CET utilisateur l'a déjà utilisé
    if user_id in code_data["used_by"]:
        return await interaction.response.send_message("❌ Tu as déjà utilisé ce code.")
    
    # Ajouter les coins
    amount = code_data["amount"]
    money = get_balance(interaction.user.id)
    set_balance(interaction.user.id, money + amount)
    
    # Marquer comme utilisé par cet utilisateur
    codes[code]["used_by"].append(user_id)
    save_codes()
    
    usage_info = "♾️ (réutilisable par d'autres)" if code_data["infinite"] else "🔒 (usage unique total)"
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
        return await interaction.response.send_message("❌ Tu n'as pas assez de coins.")
    
    # Créer les boutons
    view = discord.ui.View(timeout=30)
    
    async def coinflip_callback(button_interaction: discord.Interaction, choix: str):
        if button_interaction.user.id != interaction.user.id:
            return await button_interaction.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
        
        # Désactiver les boutons
        for item in view.children:
            item.disabled = True
        
        # Animation
        await button_interaction.response.edit_message(content="🪙 La pièce tourne... 🌀", view=view)
        await asyncio.sleep(1.5)
        
        # Avantage maison : 45% de chance de gagner, 55% de perdre
        if random.random() < 0.45:
            resultat = choix  # Le joueur gagne
        else:
            resultat = "face" if choix == "pile" else "pile"  # Le joueur perd
        
        money_now = get_balance(interaction.user.id)
        
        if resultat == choix:
            set_balance(interaction.user.id, money_now + mise)
            await button_interaction.edit_original_response(
                content=f"🎉 **{resultat.upper()} !** Tu as gagné **{mise} coins** !\n💰 Nouveau solde : **{money_now + mise} coins**",
                view=view
            )
        else:
            set_balance(interaction.user.id, money_now - mise)
            await button_interaction.edit_original_response(
                content=f"💀 **{resultat.upper()} !** Tu as perdu **{mise} coins**...\n💰 Nouveau solde : **{money_now - mise} coins**",
                view=view
            )
    
    # Bouton Pile
    pile_button = discord.ui.Button(label="🪙 PILE", style=discord.ButtonStyle.primary)
    async def pile_callback(button_interaction: discord.Interaction):
        await coinflip_callback(button_interaction, "pile")
    pile_button.callback = pile_callback
    
    # Bouton Face
    face_button = discord.ui.Button(label="🪙 FACE", style=discord.ButtonStyle.success)
    async def face_callback(button_interaction: discord.Interaction):
        await coinflip_callback(button_interaction, "face")
    face_button.callback = face_callback
    
    view.add_item(pile_button)
    view.add_item(face_button)
    
    await interaction.response.send_message(
        f"🎲 **COINFLIP** - Mise : {mise} coins\nChoisis **PILE** ou **FACE** :",
        view=view
    )


@bot.tree.command(name="roulette", description="Parie sur la roulette (nombre, couleur, pair/impair)")
@app_commands.describe(mise="Montant à miser")
async def roulette(interaction: discord.Interaction, mise: int):
    if mise < 100:
        return await interaction.response.send_message("❌ La mise minimum est 100 coins.")
    money = get_balance(interaction.user.id)
    if mise > money:
        return await interaction.response.send_message("❌ Tu n'as pas assez de coins.")

    # Créer les boutons avec menu déroulant
    view = discord.ui.View(timeout=60)
    
    # Menu pour choisir le type de pari
    select_menu = discord.ui.Select(
        placeholder="🎯 Choisis ton type de pari...",
        options=[
            discord.SelectOption(label="🔴 Rouge (x2)", value="rouge", emoji="🔴"),
            discord.SelectOption(label="⚫ Noir (x2)", value="noir", emoji="⚫"),
            discord.SelectOption(label="🟢 Zéro (x36)", value="0", emoji="🟢"),
            discord.SelectOption(label="➗ Pair (x2)", value="pair", emoji="2️⃣"),
            discord.SelectOption(label="➗ Impair (x2)", value="impair", emoji="1️⃣"),
            discord.SelectOption(label="🔢 Numéro 1-18 (x2)", value="low", emoji="📉"),
            discord.SelectOption(label="🔢 Numéro 19-36 (x2)", value="high", emoji="📈"),
        ]
    )
    
    # Variables pour stocker le choix
    user_choice = {"type": None, "value": None}
    
    async def select_callback(select_interaction: discord.Interaction):
        if select_interaction.user.id != interaction.user.id:
            return await select_interaction.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
        
        choice = select_menu.values[0]
        
        # Si choix de numéro spécifique
        if choice not in ["rouge", "noir", "pair", "impair", "low", "high", "0"]:
            user_choice["type"] = "number"
            user_choice["value"] = int(choice)
        else:
            user_choice["type"] = choice
        
        # Si on choisit un numéro entre 1-36, afficher les boutons de numéros
        if choice in ["rouge", "noir", "pair", "impair", "low", "high", "0"]:
            await play_roulette(select_interaction, choice)
        else:
            # Afficher le sélecteur de numéros
            await show_number_selector(select_interaction)
    
    select_menu.callback = select_callback
    view.add_item(select_menu)
    
    # Boutons pour numéros spécifiques
    number_buttons_view = discord.ui.View(timeout=60)
    
    async def show_number_selector(button_interaction: discord.Interaction):
        number_buttons_view.clear_items()
        
        # Créer 4 rangées de 9 numéros chacune
        for row in range(4):
            for i in range(9):
                num = row * 9 + i + 1
                if num <= 36:
                    btn = discord.ui.Button(
                        label=str(num),
                        style=discord.ButtonStyle.primary if num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else discord.ButtonStyle.secondary,
                        row=row
                    )
                    
                    async def number_callback(inter: discord.Interaction, number=num):
                        if inter.user.id != interaction.user.id:
                            return await inter.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
                        await play_roulette(inter, str(number))
                    
                    btn.callback = number_callback
                    number_buttons_view.add_item(btn)
        
        await button_interaction.response.edit_message(
            content=f"🎰 **ROULETTE** - Mise : {mise} coins\n🔢 Choisis un numéro (1-36) - Gain x36 :",
            view=number_buttons_view
        )
    
    async def play_roulette(button_interaction: discord.Interaction, choice: str):
        # Désactiver tous les boutons
        for item in view.children:
            item.disabled = True
        for item in number_buttons_view.children:
            item.disabled = True
        
        # Animation
        await button_interaction.response.edit_message(content="🎰 La roulette tourne... 🌀", view=None)
        await asyncio.sleep(1)
        await button_interaction.edit_original_response(content="🎰 La bille roule... 🔄")
        await asyncio.sleep(1)
        
        # Générer le résultat (0-36)
        resultat_num = random.randint(0, 36)
        
        # Définir les numéros rouges et noirs
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
        
        # Vérifier si gagné
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
            multiplicateur = 36
        
        if gagne:
            gain = mise * multiplicateur
            set_balance(interaction.user.id, money_now + gain)
            await button_interaction.edit_original_response(
                content=f"🎰 La bille s'arrête sur : {emoji} **{resultat_num}** {emoji}\n\n🎉 **GAGNÉ !** Tu remportes **{gain} coins** (x{multiplicateur}) !\n💰 Nouveau solde : **{money_now + gain} coins**"
            )
        else:
            set_balance(interaction.user.id, money_now - mise)
            await button_interaction.edit_original_response(
                content=f"🎰 La bille s'arrête sur : {emoji} **{resultat_num}** {emoji}\n\n💔 **Perdu !** Tu perds **{mise} coins**.\n💰 Nouveau solde : **{money_now - mise} coins**"
            )
    
    await interaction.response.send_message(
        f"🎰 **ROULETTE** - Mise : {mise} coins\n🎯 Choisis ton type de pari :",
        view=view
    )


@bot.tree.command(name="slots", description="Machine à sous simple")
@app_commands.describe(mise="Montant à miser")
async def slots(interaction: discord.Interaction, mise: int):
    if mise < 100:
        return await interaction.response.send_message("❌ La mise minimum est 100 coins.")
    money = get_balance(interaction.user.id)
    if mise > money:
        return await interaction.response.send_message("❌ Tu n'as pas assez de coins.")

    symbols = ["🍒", "🍋", "⭐", "🔔", "7️⃣"]
    
    # Animation de rotation
    await interaction.response.send_message("🎰 Lancement des rouleaux...")
    await asyncio.sleep(0.5)
    
    # Première roue
    r1 = random.choice(symbols)
    await interaction.edit_original_response(content=f"🎰 | {r1} | ❓ | ❓ |")
    await asyncio.sleep(0.7)
    
    # Deuxième roue
    r2 = random.choice(symbols)
    await interaction.edit_original_response(content=f"🎰 | {r1} | {r2} | ❓ |")
    await asyncio.sleep(0.7)
    
    # Troisième roue
    r3 = random.choice(symbols)
    await interaction.edit_original_response(content=f"🎰 | {r1} | {r2} | {r3} |")
    await asyncio.sleep(1)

    if r1 == r2 == r3:
        gain = mise * 5
        set_balance(interaction.user.id, money + gain)
        await interaction.edit_original_response(
            content=f"🎰 | {r1} | {r2} | {r3} |\n\n🎉 **JACKPOT !** Tu gagnes **{gain} coins** !\n💰 Nouveau solde : **{money + gain} coins**"
        )
    else:
        set_balance(interaction.user.id, money - mise)
        await interaction.edit_original_response(
            content=f"🎰 | {r1} | {r2} | {r3} |\n\n💀 Perdu ! Tu perds **{mise} coins**.\n💰 Nouveau solde : **{money - mise} coins**"
        )


# -------------------------------
# BLACKJACK
# -------------------------------

class BlackjackGame:
    """
    ALGORITHME BLACKJACK :
    
    1. INITIALISATION :
       - Créer un deck de 52 cartes (4 couleurs × 13 valeurs)
       - Mélanger le deck
       - Distribuer 2 cartes au joueur et 2 au croupier
       - Le croupier montre 1 carte cachée
    
    2. CALCUL DES POINTS :
       - Cartes 2-10 : valeur faciale
       - Figures (J, Q, K) : 10 points
       - As : 11 points (ou 1 si total > 21)
       - Si total > 21 avec As à 11, convertir un As en 1
    
    3. LOGIQUE DU JEU :
       - Joueur choisit : HIT (carte) ou STAND (rester)
       - Si joueur > 21 : BUST (perdu)
       - Si joueur STAND : tour du croupier
       - Croupier DOIT tirer jusqu'à 17+ points
       - Si croupier > 21 : joueur gagne
       - Sinon : comparer les scores
    
    4. GAINS :
       - Blackjack naturel (21 avec 2 cartes) : x2.5
       - Victoire normale : x2
       - Égalité : remboursement
       - Défaite : perte de la mise
    """
    
    def __init__(self):
        self.deck = []
        self.player_hand = []
        self.dealer_hand = []
        self.create_deck()
    
    def create_deck(self):
        """Crée et mélange un deck de 52 cartes"""
        suits = ["♤", "♥️", "♦️", "♧"]
        values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        self.deck = [f"{value}{suit}" for suit in suits for value in values]
        random.shuffle(self.deck)
        
        # Avantage maison subtil : Placer quelques cartes fortes au fond du deck
        # pour réduire légèrement les chances du joueur d'en obtenir
        high_cards = [c for c in self.deck if c[0] in ['J', 'Q', 'K', 'A', '1']]
        if len(high_cards) > 8 and random.random() < 0.3:
            # 30% du temps, déplacer 2-3 cartes fortes vers le fond
            for _ in range(random.randint(2, 3)):
                if high_cards:
                    card = random.choice(high_cards)
                    if card in self.deck:
                        self.deck.remove(card)
                        self.deck.insert(random.randint(0, 10), card)
                        high_cards.remove(card)
    
    def draw_card(self):
        """Tire une carte du deck"""
        return self.deck.pop()
    
    def card_value(self, card):
        """Retourne la valeur numérique d'une carte"""
        value = card[:-2] if len(card) == 3 else card[0]  # Enlever le symbole
        if value in ["J", "Q", "K"]:
            return 10
        elif value == "A":
            return 11
        else:
            return int(value)
    
    def calculate_hand(self, hand):
        """Calcule la valeur totale d'une main en gérant les As"""
        total = sum(self.card_value(card) for card in hand)
        aces = sum(1 for card in hand if card[0] == "A")
        
        # Convertir les As de 11 en 1 si nécessaire
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total
    
    def is_blackjack(self, hand):
        """Vérifie si c'est un blackjack naturel (21 avec 2 cartes)"""
        return len(hand) == 2 and self.calculate_hand(hand) == 21
    
    def dealer_play(self):
        """Le croupier tire jusqu'à avoir au moins 17"""
        while self.calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(self.draw_card())
        
        # Avantage maison : Si le croupier est à 17-18 et le joueur semble fort,
        # petite chance qu'il tire une bonne carte supplémentaire
        dealer_total = self.calculate_hand(self.dealer_hand)
        if dealer_total in [17, 18] and random.random() < 0.15:
            # 15% de chance de tirer une carte supplémentaire qui pourrait l'améliorer
            next_card_value = self.card_value(self.deck[-1]) if self.deck else 5
            if next_card_value <= 3 and dealer_total + next_card_value <= 21:
                self.dealer_hand.append(self.draw_card())


@bot.tree.command(name="blackjack", description="Joue au Blackjack contre le croupier")
@app_commands.describe(mise="Montant à miser")
async def blackjack(interaction: discord.Interaction, mise: int):
    if mise < 100:
        return await interaction.response.send_message("❌ La mise minimum est 100 coins.")
    money = get_balance(interaction.user.id)
    if mise > money:
        return await interaction.response.send_message("❌ Tu n'as pas assez de coins.")
    
    # Initialiser la partie
    game = BlackjackGame()
    game.player_hand = [game.draw_card(), game.draw_card()]
    game.dealer_hand = [game.draw_card(), game.draw_card()]
    
    player_total = game.calculate_hand(game.player_hand)
    dealer_visible = game.card_value(game.dealer_hand[0])
    
    # Vérifier blackjack naturel
    if game.is_blackjack(game.player_hand):
        gain = int(mise * 2.5)
        set_balance(interaction.user.id, money + gain)
        return await interaction.response.send_message(
            f"🃏 **BLACKJACK !**\n\n"
            f"Tes cartes : {' '.join(game.player_hand)} = **21**\n"
            f"Croupier : {' '.join(game.dealer_hand)} = {game.calculate_hand(game.dealer_hand)}\n\n"
            f"🎉 Tu gagnes **{gain} coins** (x2.5) !\n"
            f"💰 Nouveau solde : **{money + gain} coins**"
        )
    
    # Créer les boutons
    view = discord.ui.View(timeout=120)
    
    async def update_game_message(button_interaction: discord.Interaction):
        """Met à jour l'affichage de la partie"""
        player_total = game.calculate_hand(game.player_hand)
        content = (
            f"🃏 **BLACKJACK** - Mise : {mise} coins\n\n"
            f"**Tes cartes :** {' '.join(game.player_hand)} = **{player_total}**\n"
            f"**Croupier :** {game.dealer_hand[0]} 🎴 = {dealer_visible}+?\n\n"
        )
        return content
    
    async def hit_callback(button_interaction: discord.Interaction):
        if button_interaction.user.id != interaction.user.id:
            return await button_interaction.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
        
        # Tirer une carte
        game.player_hand.append(game.draw_card())
        player_total = game.calculate_hand(game.player_hand)
        
        if player_total > 21:
            # BUST - Perdu
            for item in view.children:
                item.disabled = True
            
            money_now = get_balance(interaction.user.id)
            set_balance(interaction.user.id, money_now - mise)
            
            await button_interaction.response.edit_message(
                content=(
                    f"🃏 **BLACKJACK** - Mise : {mise} coins\n\n"
                    f"**Tes cartes :** {' '.join(game.player_hand)} = **{player_total}** 💥\n"
                    f"**Croupier :** {' '.join(game.dealer_hand)} = {game.calculate_hand(game.dealer_hand)}\n\n"
                    f"💀 **BUST !** Tu as dépassé 21 !\n"
                    f"Tu perds **{mise} coins**.\n"
                    f"💰 Nouveau solde : **{money_now - mise} coins**"
                ),
                view=view
            )
        else:
            # Continuer à jouer
            content = await update_game_message(button_interaction)
            await button_interaction.response.edit_message(content=content, view=view)
    
    async def stand_callback(button_interaction: discord.Interaction):
        if button_interaction.user.id != interaction.user.id:
            return await button_interaction.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)
        
        # Désactiver les boutons
        for item in view.children:
            item.disabled = True
        
        # Le croupier joue
        game.dealer_play()
        
        player_total = game.calculate_hand(game.player_hand)
        dealer_total = game.calculate_hand(game.dealer_hand)
        
        money_now = get_balance(interaction.user.id)
        
        # Déterminer le gagnant
        if dealer_total > 21:
            # Croupier BUST
            gain = mise * 2
            set_balance(interaction.user.id, money_now + gain)
            result = f"🎉 **LE CROUPIER BUST !**\nTu gagnes **{gain} coins** !\n💰 Nouveau solde : **{money_now + gain} coins**"
        elif player_total > dealer_total:
            # Joueur gagne
            gain = mise * 2
            set_balance(interaction.user.id, money_now + gain)
            result = f"🎉 **VICTOIRE !**\nTu gagnes **{gain} coins** !\n💰 Nouveau solde : **{money_now + gain} coins**"
        elif player_total == dealer_total:
            # Égalité
            result = f"🤝 **ÉGALITÉ !**\nTu récupères ta mise de {mise} coins.\n💰 Solde : **{money_now} coins**"
        else:
            # Croupier gagne
            set_balance(interaction.user.id, money_now - mise)
            result = f"💔 **DÉFAITE !**\nTu perds **{mise} coins**.\n💰 Nouveau solde : **{money_now - mise} coins**"
        
        await button_interaction.response.edit_message(
            content=(
                f"🃏 **BLACKJACK** - Mise : {mise} coins\n\n"
                f"**Tes cartes :** {' '.join(game.player_hand)} = **{player_total}**\n"
                f"**Croupier :** {' '.join(game.dealer_hand)} = **{dealer_total}**\n\n"
                f"{result}"
            ),
            view=view
        )
    
    # Créer les boutons HIT et STAND
    hit_button = discord.ui.Button(label="🎴 HIT (Tirer)", style=discord.ButtonStyle.success)
    hit_button.callback = hit_callback
    
    stand_button = discord.ui.Button(label="✋ STAND (Rester)", style=discord.ButtonStyle.danger)
    stand_button.callback = stand_callback
    
    view.add_item(hit_button)
    view.add_item(stand_button)
    
    # Envoyer le message initial
    content = await update_game_message(interaction)
    await interaction.response.send_message(content=content, view=view)



# -------------------------------
# COMMANDES ADMIN (INVISIBLES POUR NON-ADMINS)
# -------------------------------

def admin_only():
    def predicate(interaction: discord.Interaction):
        admin_ids = ADMIN_ID if isinstance(ADMIN_ID, (list, tuple, set)) else [ADMIN_ID]
        return interaction.user.id in admin_ids
    return app_commands.check(predicate)


@bot.tree.command(name="admin_list", description="[ADMIN] Liste tous les joueurs")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@admin_only()
async def admin_list(interaction: discord.Interaction):
    if not players:
        return await interaction.response.send_message("Aucun joueur enregistré.")
    
    msg = "📜 **Liste des joueurs :**\n\n"
    for uid, money in players.items():
        try:
            user = await bot.fetch_user(int(uid))
            msg += f"**{user.name}** ({uid}) → {money} coins\n"
        except:
            msg += f"User {uid} → {money} coins\n"
    await interaction.response.send_message(msg)


@bot.tree.command(name="admin_add", description="[ADMIN] Ajouter de l'argent")
@app_commands.describe(member="Membre à créditer", amount="Montant")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@admin_only()
async def admin_add(interaction: discord.Interaction, member: discord.Member, amount: int):
    money = get_balance(member.id)
    set_balance(member.id, money + amount)
    await interaction.response.send_message(f"✔️ Ajouté {amount} coins à {member.name}.")


@bot.tree.command(name="admin_remove", description="[ADMIN] Retirer de l'argent")
@app_commands.describe(member="Membre à débiter", amount="Montant")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@admin_only()
async def admin_remove(interaction: discord.Interaction, member: discord.Member, amount: int):
    money = get_balance(member.id)
    set_balance(member.id, max(0, money - amount))
    await interaction.response.send_message(f"✔️ Retiré {amount} coins à {member.name}.")


@bot.tree.command(name="admin_reset", description="[ADMIN] Reset l'argent d'un joueur")
@app_commands.describe(member="Membre à reset")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@admin_only()
async def admin_reset(interaction: discord.Interaction, member: discord.Member):
    set_balance(member.id, 0)
    await interaction.response.send_message(f"♻️ Argent de {member.name} remis à 0.")


@bot.tree.command(name="admin_createcode", description="[ADMIN] Créer un code promo")
@app_commands.describe(
    code="Le code (ex: BIENVENUE)",
    amount="Montant de coins",
    infinite="Utilisable à l'infini ? (True/False)"
)
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
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
        f"💰 Montant : {amount} coins\n"
        f"📋 Type : {usage_type}"
    )


@bot.tree.command(name="admin_deletecode", description="[ADMIN] Supprimer un code promo")
@app_commands.describe(code="Le code à supprimer")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@admin_only()
async def admin_deletecode(interaction: discord.Interaction, code: str):
    code = code.upper()
    
    if code not in codes:
        return await interaction.response.send_message(f"❌ Le code **{code}** n'existe pas.")
    
    del codes[code]
    save_codes()
    await interaction.response.send_message(f"🗑️ Code **{code}** supprimé.")


@bot.tree.command(name="admin_listcodes", description="[ADMIN] Liste tous les codes")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
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
        msg += f"  ├ Montant : {code_data['amount']} coins\n"
        msg += f"  ├ Type : {usage_type}\n"
        msg += f"  └ Statut : {status}\n\n"
    
    await interaction.response.send_message(msg)


@bot.tree.command(name="admin_togglecode", description="[ADMIN] Activer/désactiver un code")
@app_commands.describe(code="Le code à activer/désactiver")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@admin_only()
async def admin_togglecode(interaction: discord.Interaction, code: str):
    code = code.upper()
    
    if code not in codes:
        return await interaction.response.send_message(f"❌ Le code **{code}** n'existe pas.")
    
    codes[code]["active"] = not codes[code]["active"]
    save_codes()
    
    status = "activé ✅" if codes[code]["active"] else "désactivé ❌"
    await interaction.response.send_message(f"Le code **{code}** a été {status}.")


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@admin_only()
async def admin_generate(interaction: discord.Interaction, amount: int, quantity: int, length: int = 8):
    if quantity > 50:
        return await interaction.response.send_message("❌ Maximum 50 codes à la fois.")
    
    if quantity < 1:
        return await interaction.response.send_message("❌ Il faut générer au moins 1 code.")
    
    if length < 4 or length > 20:
        return await interaction.response.send_message("❌ La longueur doit être entre 4 et 20 caractères.")
    
    if amount < 1:
        return await interaction.response.send_message("❌ Le montant doit être positif.")
    
    # Générer les codes
    generated_codes = []
    
    for i in range(quantity):
        # Générer un code aléatoire unique
        attempts = 0
        while attempts < 100:  # Limite pour éviter boucle infinie
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            if code not in codes:  # Vérifier qu'il n'existe pas déjà
                break
            attempts += 1
        
        if attempts >= 100:
            return await interaction.response.send_message(f"❌ Impossible de générer {quantity} codes uniques. Essaie avec une longueur plus grande.")
        
        # Créer le code (TOUJOURS usage unique = 1 fois au total)
        codes[code] = {
            "amount": amount,
            "infinite": False,  # Usage unique = 1 seule personne peut l'utiliser
            "active": True,
            "used_by": []
        }
        generated_codes.append(code)
    
    save_codes()
    
    # Créer le message de réponse
    embed = discord.Embed(
        title="🎟️ **CODES GÉNÉRÉS**",
        description=f"**{quantity} codes** de **{amount:,} coins** créés avec succès !",
        color=discord.Color.green()
    )
    
    # Diviser les codes en plusieurs champs si nécessaire (limite Discord)
    codes_per_field = 10
    for i in range(0, len(generated_codes), codes_per_field):
        batch = generated_codes[i:i+codes_per_field]
        field_name = f"📋 Codes {i+1}-{min(i+codes_per_field, len(generated_codes))}"
        field_value = "\n".join([f"`{code}`" for code in batch])
        embed.add_field(name=field_name, value=field_value, inline=False)
    
    embed.set_footer(text="⚠️ Chaque code est à usage UNIQUE (1 seule personne au total)")
    
    await interaction.response.send_message(embed=embed)
    
    # Envoyer aussi un fichier texte si beaucoup de codes
    if quantity > 20:
        codes_text = "\n".join(generated_codes)
        with open("generated_codes.txt", "w", encoding="utf-8") as f:
            f.write(f"Codes générés - {amount:,} coins chacun\n")
            f.write("="*40 + "\n")
            f.write("⚠️ Usage UNIQUE : Chaque code utilisable 1 fois au total\n")
            f.write("="*40 + "\n\n")
            f.write(codes_text)
        
        with open("generated_codes.txt", "rb") as f:
            file = discord.File(f, filename=f"codes_{amount}coins_{quantity}x.txt")
            await interaction.followup.send(
                "📄 **Fichier texte avec tous les codes :**",
                file=file
            )
        
        # Supprimer le fichier temporaire
        os.remove("generated_codes.txt")


@bot.tree.command(name="admin_generate", description="[ADMIN] Générer plusieurs codes uniques automatiquement")
@app_commands.describe(
    amount="Montant de coins par code",
    quantity="Nombre de codes à générer",
    length="Longueur des codes (par défaut: 8)"
)
@admin_only()
async def admin_generate(interaction: discord.Interaction, amount: int, quantity: int, length: int = 8):
    if quantity > 50:
        return await interaction.response.send_message("❌ Maximum 50 codes à la fois.")
    
    if length < 4 or length > 20:
        return await interaction.response.send_message("❌ La longueur doit être entre 4 et 20 caractères.")
    
    if amount < 1:
        return await interaction.response.send_message("❌ Le montant doit être positif.")
    
    # Générer les codes
    generated_codes = []
    
    for i in range(quantity):
        # Générer un code aléatoire unique
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            if code not in codes:  # Vérifier qu'il n'existe pas déjà
                break
        
        # Créer le code
        codes[code] = {
            "amount": amount,
            "infinite": False,  # Toujours usage unique
            "active": True,
            "used_by": []
        }
        generated_codes.append(code)
    
    save_codes()
    
    # Créer le message de réponse
    embed = discord.Embed(
        title="🎟️ **CODES GÉNÉRÉS**",
        description=f"**{quantity} codes** de **{amount} coins** créés avec succès !",
        color=discord.Color.green()
    )
    
    # Diviser les codes en plusieurs champs si nécessaire (limite Discord)
    codes_per_field = 10
    for i in range(0, len(generated_codes), codes_per_field):
        batch = generated_codes[i:i+codes_per_field]
        field_name = f"📋 Codes {i+1}-{min(i+codes_per_field, len(generated_codes))}"
        field_value = "\n".join([f"`{code}`" for code in batch])
        embed.add_field(name=field_name, value=field_value, inline=False)
    
    embed.set_footer(text="⚠️ Chaque code est à usage unique (1 joueur)")
    
    await interaction.response.send_message(embed=embed)
    
    # Envoyer aussi un fichier texte si beaucoup de codes
    if quantity > 20:
        codes_text = "\n".join(generated_codes)
        with open("generated_codes.txt", "w") as f:
            f.write(f"Codes générés - {amount} coins chacun\n")
            f.write("="*40 + "\n\n")
            f.write(codes_text)
        
        with open("generated_codes.txt", "rb") as f:
            file = discord.File(f, filename=f"codes_{amount}coins_{quantity}x.txt")
            await interaction.followup.send(
                "📄 **Fichier texte avec tous les codes :**",
                file=file
            )
        
        # Supprimer le fichier temporaire
        os.remove("generated_codes.txt")


# -------------------------------
# LANCEMENT DU BOT
# -------------------------------
TOKEN = os.getenv("DISCORD_TOKEN") # ⚠️ CHANGE LE TOKEN !
bot.run(TOKEN)