from deuces import Card, Deck, Evaluator
import random
from bluffing_module import should_bluff
import os
from opponent_modeling import OpponentModel

# Get the absolute path to the directory this script is in
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Global bluff statistics tracker
bluff_stats = {
    "total_bluffs": 0,
    "successful_bluffs": 0,
    "failed_bluffs": 0
}

# Converts human-readable card strings to Deuces format (e.g., 'K♠' -> 'Ks')
def convert_card(card_str):
    rank_map = {'T': 'T', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}
    rank_map.update({str(i): str(i) for i in range(2, 10)})
    suit_map = {'♠': 's', '♥': 'h', '♦': 'd', '♣': 'c'}
    return Card.new(rank_map[card_str[0]] + suit_map[card_str[1]])

# Converts a list of card strings to Deuces card objects
def convert_hand(hand):
    return [convert_card(card) for card in hand]

# Evaluates the strength of a hand against the board using Deuces
# Returns an integer value: lower is better
def evaluate_strength(hand, board):
    evaluator = Evaluator()
    if len(board) + len(hand) < 5:
        return 7462  # Worst possible score when not enough cards
    return evaluator.evaluate(board, hand)

# Converts a score to a human-readable hand rank string
def rank_to_string(score):
    evaluator = Evaluator()
    return evaluator.class_to_string(evaluator.get_rank_class(score))

# Determines a fixed AI bet amount based on its hand strength
# Stronger hands yield higher bets
def determine_ai_bet_amount(ai_hand, community_cards):
    board = convert_hand(community_cards)
    hand = convert_hand(ai_hand)
    score = evaluate_strength(hand, board)
    if score < 2000:
        return 50
    elif score < 4000:
        return 30
    return 10

# Estimates pre-flop hand strength using simple heuristics
# Uses pairing, suitedness, and proximity to rank value
def estimate_preflop_strength(hand):
    ranks = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
             '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    r1, s1 = hand[0][0], hand[0][1]
    r2, s2 = hand[1][0], hand[1][1]
    v1, v2 = ranks[r1], ranks[r2]
    base = max(v1, v2) * 2
    if r1 == r2:
        base += 30
    if s1 == s2:
        base += 10
    if abs(v1 - v2) == 1:
        base += 5
    return min(base, 100)

"""
Simulates many possible future outcomes to estimate AI win rate post-flop.
This method randomly draws opponent hands and completes the board to see how often
AI wins versus a random opponent hand, helping inform post-flop decision making.

Parameters:
    ai_hand (list[str]): AI's hand as list of card strings.
    board (list[str]): Community cards on the table.
    num_simulations (int): How many Monte Carlo runs to perform.

Returns:
    float: AI win rate (0 to 1) based on simulated hands.

--------------------
# Simplified Example:

ai_hand = ['A♠', 'Q♠']
board = ['K♦', 'J♣', '2♥']
num_simulations = 1000

# For each simulation:
# 1. Draw two random cards for opponent (player)
# 2. Draw 2 more community cards to complete the 5-card board
# 3. Evaluate both hands using Deuces
# 4. Track how many times AI wins

If AI wins 680 out of 1000 simulations,
Return value: 0.68
--------------------
"""
def monte_carlo_win_rate(ai_hand, board, num_simulations=1000):
    deck = Deck()
    ai_converted = convert_hand(ai_hand)
    board_converted = convert_hand(board)

    # Remove known cards (AI's hand + board) from the deck
    for card in ai_converted + board_converted:
        if card in deck.cards:
            deck.cards.remove(card)

    wins = 0
    ties = 0
    evaluator = Evaluator()

    for _ in range(num_simulations):
        # Draw a random opponent hand from the remaining deck
        opp_hand = [deck.draw(), deck.draw()]

        # Build a full 5-card board
        remaining_board = list(board_converted)
        while len(remaining_board) < 5:
            remaining_board.append(deck.draw())

        # Evaluate AI and opponent hands against the same board
        ai_score = evaluator.evaluate(remaining_board, ai_converted)
        opp_score = evaluator.evaluate(remaining_board, opp_hand)

        if ai_score < opp_score:
            wins += 1
        elif ai_score == opp_score:
            ties += 1

        # Return used cards back to the deck for the next simulation
        deck.cards += opp_hand + [c for c in remaining_board if c not in board_converted]
        random.shuffle(deck.cards)

    return wins / num_simulations

"""
Determines the AI's betting behavior based on hand strength, game stage,
player action, and bluffing strategy. This is the central logic that decides
whether the AI will check, call, bet, raise, or fold at any given point.

Parameters:
    ai_hand (list[str]): AI's hand in string format.
    community_cards (list[str]): Shared board cards.
    player_action (str): Player's last action ('check', 'bet', etc).
    pot_size (int): Total value of the pot.
    stage (str): Game stage ('Flop', 'Turn', 'River').
    last_player_bet (int): Amount the player bet if applicable.

Returns:
    tuple[str, int]: AI decision ('fold', 'call', 'raise', etc) and amount.

--------------------
# Simplified Example:

ai_hand = ['7♣', '2♦']
community_cards = ['K♠', '9♦', '4♣']
player_action = 'bet'
pot_size = 60
stage = 'Flop'
last_player_bet = 20

# Step 1: Run Monte Carlo to estimate win_rate (e.g., 0.18)
# Step 2: Since win_rate < 0.75, check if AI should bluff
# Step 3: Call should_bluff → returns True
# Step 4: AI chooses to raise (bluff) to 30
# Function returns: ('raise', 30)
--------------------
"""
from opponent_modeling import OpponentModel

def make_ai_decision(ai_hand, community_cards, player_action, pot_size=0, stage="Flop", last_player_bet=20):
    evaluator = Evaluator()
    board = convert_hand(community_cards)
    hand = convert_hand(ai_hand)
    opponent_model = OpponentModel()
    player_id = 1  # Assuming player_id is 1 for the human player
    playstyle = opponent_model.predict_playstyle(player_id)

    # Adjust thresholds based on playstyle
    win_rate_threshold = 0.75
    bluff_aggression = 0.9
    if playstyle == 'aggressive':
        win_rate_threshold = 0.8  # Require stronger hand to call
        bluff_aggression = 0.7    # Bluff less often
    elif playstyle == 'passive':
        win_rate_threshold = 0.7  # Call with weaker hands
        bluff_aggression = 1.0    # Bluff more often
    elif playstyle == 'tight':
        win_rate_threshold = 0.7
        bluff_aggression = 1.0
    elif playstyle == 'loose':
        win_rate_threshold = 0.8
        bluff_aggression = 0.7

    # --- Pre-Flop Logic ---
    if len(community_cards) < 3:
        score = estimate_preflop_strength(ai_hand)
        print(f"DEBUG: Pre-flop hand strength = {score}")

        if player_action == 'check':
            if random.random() < 0.3 or score > 60:
                print("DEBUG: Pre-flop aggression — AI chooses to bet.")
                bluff_stats["total_bluffs"] += 1
                bluff_stats["successful_bluffs"] += 1
                log_path = os.path.join(SCRIPT_DIR, "ai_bluff_log.txt")
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"Bluff on Pre-Flop: AI Hand = {ai_hand}, Player checked, Score = {score}\n")
                return ('bet', 20)
            return ('check', 0)
        else:
            if playstyle == 'aggressive' and score < 50:
                return ('fold', 0)
            return ('call', 0)

    # --- Post-Flop Logic with Monte Carlo ---
    win_rate = monte_carlo_win_rate(ai_hand, community_cards)
    print(f"DEBUG: Monte Carlo estimated win rate = {win_rate:.2f}")

    if player_action == 'check':
        if win_rate > win_rate_threshold:
            return ('check', 0)
        elif win_rate > 0.4:
            return random.choice([('check', 0), ('bet', 30)])
        elif should_bluff(7000, pot_size, stage, aggression_level=bluff_aggression):
            print("DEBUG: AI decided to bluff after check.")
            bluff_stats["total_bluffs"] += 1
            bluff_stats["successful_bluffs"] += 1
            log_path = os.path.join(SCRIPT_DIR, "ai_bluff_log.txt")
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Bluff after player check on {stage}: AI Hand = {ai_hand}, Pot = {pot_size}\n")
            return ('bet', 30)
        else:
            return ('check', 0)

    elif player_action == 'bet':
        if win_rate > win_rate_threshold:
            return ('call', 0)
        elif should_bluff(7000, pot_size, stage, aggression_level=bluff_aggression):
            bluff_raise = max(int(last_player_bet * 1.5), int(pot_size * 0.1), 10)
            print(f"DEBUG: Player bet detected. AI decides to bluff (raise to {bluff_raise}).")
            bluff_stats["total_bluffs"] += 1
            log_path = os.path.join(SCRIPT_DIR, "ai_bluff_log.txt")
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Bluff in response to player bet on {stage}: AI Hand = {ai_hand}, Pot = {pot_size}, Raise = {bluff_raise}\n")
            return ('raise', bluff_raise)
        else:
            return ('fold', 0)

    return ('check', 0)

# --- Print bluff stats at the end of the game ---
def print_bluff_stats():
    print("\n--- AI Bluffing Summary ---")
    print(f"Total Bluffs: {bluff_stats['total_bluffs']}")
    print(f"Successful Bluffs: {bluff_stats['successful_bluffs']}")
    print(f"Failed Bluffs (estimated): {bluff_stats['failed_bluffs']}")
