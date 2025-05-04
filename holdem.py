from deuces import Card, Deck, Evaluator
import random
from bluffing_module import should_bluff
from decision_engine import make_ai_decision, convert_hand, determine_ai_bet_amount, evaluate_strength, bluff_stats

# Define card suits and ranks for deck creation
suits = ['♠', '♥', '♦', '♣']
ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

# Create a standard 52-card deck
def create_deck():
    return [rank + suit for suit in suits for rank in ranks]

# Shuffle the given deck
def shuffle_deck(deck):
    random.shuffle(deck)

# Deal a hand of n cards from the deck
def deal_hand(deck, num_cards=2):
    return [deck.pop() for _ in range(num_cards)]

# Burn one card from the top of the deck (common in Texas Hold'em)
def burn_card(deck):
    deck.pop()

# Deal the flop (three community cards)
def deal_flop(deck):
    burn_card(deck)
    return [deck.pop() for _ in range(3)]

# Deal the turn (one card)
def deal_turn(deck):
    burn_card(deck)
    return deck.pop()

# Deal the river (one card)
def deal_river(deck):
    burn_card(deck)
    return deck.pop()

# Prompt player for an action until valid input is given
def player_decision():
    while True:
        action = input("Your move (check, bet, call, fold): ").lower()
        if action in ['check', 'bet', 'call', 'fold']:
            return action
        print("Invalid input.")

# Handle a single round of betting between player and AI
def betting_round(player_hand, ai_hand, community_cards, pot, stage):
    print(f"\n--- {stage} Betting Round ---")
    print(f"Community Cards: {community_cards}")
    print(f"Your Hand: {player_hand}")
    print(f"Current Pot: {pot} chips")

    player_action = player_decision()
    player_bet = 0

    # If player bets, prompt for bet amount
    if player_action == 'bet':
        while True:
            try:
                player_bet = int(input("Enter your bet amount (minimum 1): "))
                if player_bet >= 1:
                    break
                print("Bet must be at least 1 chip.")
            except ValueError:
                print("Please enter a valid number.")

    # Handle player folding immediately
    if player_action == 'fold':
        print("You folded. AI wins the pot.")
        return 'fold', pot

    # Let the AI make its move based on context
    ai_action, ai_amount = make_ai_decision(
        ai_hand,
        community_cards,
        player_action,
        pot_size=pot + player_bet,
        stage=stage,
        last_player_bet=player_bet
    )

    print(f"AI chooses to {ai_action}.")

    # If both players check
    if player_action == 'check' and ai_action == 'check':
        print("Both players check.")

    # If player checks and AI bets, prompt player to respond
    elif player_action == 'check' and ai_action == 'bet':
        print(f"AI bets {ai_amount} chips.")
        response = input("AI bet — do you want to call or fold? ").lower()
        while response not in ['call', 'fold']:
            response = input("Please enter 'call' or 'fold': ").lower()
        if response == 'call':
            pot += ai_amount * 2  # Match AI bet
            bluff_stats["failed_bluffs"] += 1  # Assume AI bluff failed (called)
        else:
            print("You folded. AI wins the pot.")
            return 'fold', pot

    # If AI folds to player action
    elif ai_action == 'fold':
        print("AI folded. You win the pot!")
        return 'win', pot

    # If player bets and AI simply calls
    elif player_action == 'bet' and ai_action == 'call':
        pot += 2 * player_bet  # Both player and AI contributed equally

    # If AI raises in response to player's bet
    elif player_action == 'bet' and ai_action == 'raise':
        print(f"AI raises to {ai_amount} chips.")
        response = input("AI raised — do you want to call or fold? ").lower()
        while response not in ['call', 'fold']:
            response = input("Please enter 'call' or 'fold': ").lower()
        if response == 'call':
            call_amount = ai_amount - player_bet  # Extra needed to match raise
            pot += player_bet + call_amount + ai_amount  # Total contributions
            bluff_stats["failed_bluffs"] += 1  # AI bluff called
        else:
            print("You folded. AI wins the pot.")
            bluff_stats["successful_bluffs"] += 1  # Bluff succeeded
            return 'fold', pot

    # Fallback: AI folds to player's bet (not call or raise)
    elif player_action == 'bet' and ai_action != 'call':
        print("AI folded to your bet. You win the pot!")
        return 'win', pot

    return 'continue', pot

# Compare hands and declare a winner
def showdown(player_hand, ai_hand, community_cards, pot):
    evaluator = Evaluator()
    p1 = convert_hand(player_hand)
    p2 = convert_hand(ai_hand)
    board = convert_hand(community_cards)

    p1_score = evaluator.evaluate(board, p1)
    p2_score = evaluator.evaluate(board, p2)

    print("\n--- Showdown ---")
    print(f"\nYour Hand: {player_hand}")
    print(f"AI Hand: {ai_hand}")
    print(f"Board: {community_cards}")
    print(f"Final Pot: {pot} chips")
    print(f"Your Hand Rank: {evaluator.class_to_string(evaluator.get_rank_class(p1_score))}")
    print(f"AI Hand Rank: {evaluator.class_to_string(evaluator.get_rank_class(p2_score))}")

    if p1_score < p2_score:
        print("You win the pot!")
    elif p2_score < p1_score:
        print("AI wins the pot!")
    else:
        print("It's a tie!")

# Play through a single round of Texas Hold'em
def play_round():
    deck = create_deck()
    shuffle_deck(deck)

    pot = 0
    player_hand = deal_hand(deck)
    ai_hand = deal_hand(deck)

    # Pre-flop betting
    state, pot = betting_round(player_hand, ai_hand, [], pot, "Pre-Flop")
    if state != 'continue': return

    # Flop betting
    flop = deal_flop(deck)
    state, pot = betting_round(player_hand, ai_hand, flop, pot, "Flop")
    if state != 'continue': return

    # Turn betting
    turn = deal_turn(deck)
    state, pot = betting_round(player_hand, ai_hand, flop + [turn], pot, "Turn")
    if state != 'continue': return

    # River betting
    river = deal_river(deck)
    state, pot = betting_round(player_hand, ai_hand, flop + [turn, river], pot, "River")
    if state != 'continue': return

    # Final hand comparison
    community_cards = flop + [turn, river]
    showdown(player_hand, ai_hand, community_cards, pot)

    # Display bluff statistics
    print("\n--- AI Bluff Summary ---")
    print(f"Total Bluffs: {bluff_stats['total_bluffs']}")
    print(f"Successful Bluffs: {bluff_stats['successful_bluffs']}")
    print(f"Failed Bluffs: {bluff_stats['failed_bluffs']}")

if __name__ == "__main__":
    play_round()
