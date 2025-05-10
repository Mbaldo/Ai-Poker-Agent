import random 
from opponent_modeling import OpponentModel

def should_bluff(ai_hand_strength, pot_size, stage, aggression_level=0.9):
    """
    Determines if AI should bluff based on hand strength and game context.

    Parameters:
        ai_hand_strength (int): Lower is better. 1 = best, 7462 = worst (Deuces).
        pot_size (int): Total pot value.
        stage (str): One of 'Pre-Flop', 'Flop', 'Turn', 'River'.
        aggression_level (float): Base probability to bluff with a weak hand.

    Returns:
        bool: True if bluffing, False otherwise.

    --------------------
    # Simplified Example:
    # ai_hand_strength = 7100 (very weak)
    # pot_size = 80
    # stage = 'Turn'
    # aggression_level = 0.9

    # Step 1: Is it a weak hand? → 7100 > 6000 → True
    # Step 2: pot_factor = min(80 / 100, 1.0) = 0.8
    # Step 3: stage_factor = 0.4 (Turn)
    # Step 4: bluff_chance = 0.9 * (0.8 + 0.4) = 1.08 (capped at 1.0 probability)
    # Step 5: random.random() < bluff_chance → returns True most likely
    # → Function returns True → AI should bluff
    --------------------
    """
    player_id = 1
    opponent_model = OpponentModel()
    playstyle = opponent_model.predict_playstyle(player_id)

    # Adjust aggression based on playstyle
    if playstyle == 'passive' or playstyle == 'tight':
        aggression_level *= 1.2  # Bluff more often
    elif playstyle == 'aggressive' or playstyle == 'loose':
        aggression_level *= 0.8  # Bluff less often

    is_weak_hand = ai_hand_strength > 6000
    stage_weight = {'Pre-Flop': 0.2, 'Flop': 0.3, 'Turn': 0.4, 'River': 0.5}
    
    pot_factor = min(pot_size / 100.0, 1.0)
    stage_factor = stage_weight.get(stage, 0.3)

    bluff_chance = aggression_level * (pot_factor + stage_factor)
    return is_weak_hand and random.random() < bluff_chance