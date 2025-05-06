import pandas as pd
import numpy as np
import csv

def create_mock_data():
    # Define player styles and their characteristics
    player_styles = {
        2: {  # Tight player
            'actions': ['fold', 'fold', 'fold', 'bet', 'call'],
            'bet_sizes': [0.0, 0.0, 0.0, 0.5, 0.2],
            'style': 'tight'
        },
        3: {  # Passive player
            'actions': ['call', 'call', 'call', 'fold', 'check'],
            'bet_sizes': [0.1, 0.15, 0.2, 0.0, 0.0],
            'style': 'passive'
        },
        4: {  # Loose player
            'actions': ['call', 'bet', 'raise', 'bet', 'raise'],
            'bet_sizes': [0.2, 0.4, 0.6, 0.5, 0.7],
            'style': 'loose'
        }
    }

    mock_data = []
    for player_id, style in player_styles.items():
        # Generate 20 hands per player
        for _ in range(50):
            hand = f"{np.random.choice(['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2'])}" + \
                   f"{np.random.choice(['♠', '♣', '♥', '♦'])}" + \
                   f"{np.random.choice(['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2'])}" + \
                   f"{np.random.choice(['♠', '♣', '♥', '♦'])}"
            
            row = {
                'hand': hand,
                'flop': '',
                'result1': '',
                'turn': '',
                'result2': '',
                'river': '',
                'result3': '',
                'player_id': player_id,
                'playstyle_label': style['style'],
                'action_flop': np.random.choice(style['actions']),
                'bet_size_flop': np.random.choice(style['bet_sizes']),
                'action_turn': np.random.choice(style['actions']),
                'bet_size_turn': np.random.choice(style['bet_sizes']),
                'action_river': np.random.choice(style['actions']),
                'bet_size_river': np.random.choice(style['bet_sizes'])
            }
            mock_data.append(row)

    # Create DataFrame and save to CSV
    df = pd.DataFrame(mock_data)
    df.to_csv('opponent_dataset.csv', mode='a', header=False, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"Added {len(mock_data)} mock hands to opponent_dataset.csv")

if __name__ == "__main__":
    create_mock_data()