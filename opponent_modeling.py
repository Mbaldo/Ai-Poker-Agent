import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import os
import csv
from collections import defaultdict
from deuces import Evaluator, Card

class OpponentModel:
    def __init__(self, data_path="poker_dataset.csv", min_hands_for_ml=50):
        """Initialize the opponent model with data storage and ML setup."""
        self.data_path = data_path
        self.min_hands_for_ml = min_hands_for_ml
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.label_encoder = LabelEncoder()
        self.opponent_data = defaultdict(list)  # Store raw hand/action data
        self.opponent_features = {}  # Store computed features
        self.opponent_hands_count = defaultdict(int)  # Track hands per opponent
        self.playstyle_labels = ['aggressive', 'passive', 'tight', 'loose']
        self.evaluator = Evaluator()  # Deuces hand evaluator
        
        # Define dtypes for CSV columns
        self.dtypes = {
            'hand': pd.StringDtype(),
            'flop': pd.StringDtype(),
            'result1': pd.StringDtype(),
            'turn': pd.StringDtype(),
            'result2': pd.StringDtype(),
            'river': pd.StringDtype(),
            'result3': pd.StringDtype(),
            'player_id': pd.Int64Dtype(),
            'playstyle_label': pd.StringDtype(),
            'action_flop': pd.StringDtype(),
            'bet_size_flop': 'float64',
            'action_turn': pd.StringDtype(),
            'bet_size_turn': 'float64',
            'action_river': pd.StringDtype(),
            'bet_size_river': 'float64'
        }
        
        # Initialize or load CSV
        self._initialize_csv()

    def _initialize_csv(self):
        """Create or load poker_dataset.csv, adding necessary columns."""
        if not os.path.exists(self.data_path):
            self.data = pd.DataFrame(columns=self.dtypes.keys()).astype(self.dtypes)
            self.data.to_csv(self.data_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
        else:
            try:
                # Load CSV with specified dtypes
                self.data = pd.read_csv(self.data_path, dtype=self.dtypes, keep_default_na=True)
                # Add missing columns
                for col in self.dtypes:
                    if col not in self.data.columns:
                        self.data[col] = pd.Series(dtype=self.dtypes[col])
                # Coerce columns to correct types
                self.data['player_id'] = pd.to_numeric(self.data['player_id'], errors='coerce').astype(pd.Int64Dtype())
                for col in ['action_flop', 'action_turn', 'action_river', 'hand', 'flop', 'result1', 'turn', 'result2', 'river', 'result3', 'playstyle_label']:
                    self.data[col] = self.data[col].astype(pd.StringDtype())
                self.data.to_csv(self.data_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
            except pd.errors.ParserError as e:
                print(f"Error reading CSV: {e}. Creating new CSV.")
                self.data = pd.DataFrame(columns=self.dtypes.keys()).astype(self.dtypes)
                self.data.to_csv(self.data_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

    def _convert_card_to_deuces(self, card):
        """Convert card string (e.g., '♣K') to Deuces format (e.g., 'Kc')."""
        suit_map = {'♣': 'c', '♥': 'h', '♦': 'd', '♠': 's'}
        rank = card[1] if card[1] in '23456789TJQKA' else '10' if card[1:3] == '10' else ''
        suit = suit_map.get(card[0], '')
        return rank + suit

    def update_opponent_data(self, player_hand, community_cards, stage, player_action, player_bet, pot_size, player_id):
        """Update opponent hand and action data."""
        # Format card strings to avoid commas
        hand = ''.join(player_hand).replace(',', '') if player_hand else ''
        flop = ''.join(community_cards[:3]).replace(',', '') if len(community_cards) >= 3 else ''
        turn = ''.join(community_cards[:4]).replace(',', '') if len(community_cards) >= 4 else ''
        river = ''.join(community_cards[:5]).replace(',', '') if len(community_cards) >= 5 else ''

        # Compute hand strength
        result1 = result2 = result3 = ''
        if player_hand and len(community_cards) >= 3:
            try:
                hole_cards = [Card.new(self._convert_card_to_deuces(c)) for c in player_hand]
                board = [Card.new(self._convert_card_to_deuces(c)) for c in community_cards]
                if len(board) >= 3:
                    rank = self.evaluator.evaluate(board[:3], hole_cards)
                    result1 = self._rank_to_strength(rank)
                if len(board) >= 4:
                    rank = self.evaluator.evaluate(board[:4], hole_cards)
                    result2 = self._rank_to_strength(rank)
                if len(board) >= 5:
                    rank = self.evaluator.evaluate(board[:5], hole_cards)
                    result3 = self._rank_to_strength(rank)
            except:
                pass

        # Assign action and bet size based on stage
        action_flop = action_turn = action_river = ''
        bet_size_flop = bet_size_turn = bet_size_river = 0
        normalized_bet = player_bet / pot_size if pot_size > 0 else 0
        if stage == 'Flop':
            action_flop = player_action if player_action else ''
            bet_size_flop = normalized_bet
        elif stage == 'Turn':
            action_turn = player_action if player_action else ''
            bet_size_turn = normalized_bet
        elif stage == 'River':
            action_river = player_action if player_action else ''
            bet_size_river = normalized_bet

        # Store data
        new_row = {
            'hand': hand,
            'flop': flop,
            'result1': result1,
            'turn': turn,
            'result2': result2,
            'river': river,
            'result3': result3,
            'player_id': int(player_id),  # Ensure integer
            'playstyle_label': None,
            'action_flop': action_flop,
            'bet_size_flop': bet_size_flop,
            'action_turn': action_turn,
            'bet_size_turn': bet_size_turn,
            'action_river': action_river,
            'bet_size_river': bet_size_river
        }
        self.opponent_data[player_id].append(new_row)
        self.opponent_hands_count[player_id] += 1

        # Append to CSV with consistent dtypes, quoting to handle special characters
        new_row_df = pd.DataFrame([new_row]).astype(self.dtypes)
        new_row_df.to_csv(self.data_path, mode='a', header=not os.path.exists(self.data_path), index=False, quoting=csv.QUOTE_NONNUMERIC)
        self.data = pd.concat([self.data, new_row_df], ignore_index=True)

    def _rank_to_strength(self, rank):
        """Convert Deuces rank to hand strength label."""
        if rank <= 1:
            return 'ROYAL FLUSH'
        elif rank <= 10:
            return 'STRAIGHT FLUSH'
        elif rank <= 166:
            return 'FOUR OF A KIND'
        elif rank <= 322:
            return 'FULL HOUSE'
        elif rank <= 1599:
            return 'FLUSH'
        elif rank <= 1609:
            return 'STRAIGHT'
        elif rank <= 2467:
            return 'THREE OF A KIND'
        elif rank <= 3325:
            return 'TWO PAIR'
        elif rank <= 6185:
            return 'PAIR'
        else:
            return 'NOTHING'

    def compute_features(self, player_id):
        """Compute features from opponent hand and action data."""
        if player_id not in self.opponent_data:
            return None

        hands = self.opponent_data[player_id]
        total_hands = len(hands)
        if total_hands == 0:
            return None

        # Initialize feature dictionary
        features = {
            'raise_freq': 0,
            'call_freq': 0,
            'fold_freq': 0,
            'avg_bet_size': 0,
            'weak_hand_river_freq': 0,
            'weak_hand_aggressiveness': 0
        }

        # Count actions and bet sizes
        action_counts = defaultdict(int)
        bet_sizes = []
        weak_hand_river = 0
        weak_hand_aggressive = 0
        weak_hand_count = 0

        for hand_data in hands:
            # Count actions
            for action in [hand_data['action_flop'], hand_data['action_turn'], hand_data['action_river']]:
                if action:
                    action_counts[action] += 1
            # Collect bet sizes
            for bet in [hand_data['bet_size_flop'], hand_data['bet_size_turn'], hand_data['bet_size_river']]:
                if bet:
                    bet_sizes.append(bet)
            # Check for weak hands played to river
            if hand_data['result3'] in ['NOTHING', 'PAIR']:
                weak_hand_count += 1
                if hand_data['action_river'] in ['raise', 'bet']:
                    weak_hand_aggressive += 1
                if hand_data['action_river']:  # Any action means they reached river
                    weak_hand_river += 1

        # Compute features
        features['raise_freq'] = action_counts['raise'] / total_hands
        features['call_freq'] = action_counts['call'] / total_hands
        features['fold_freq'] = action_counts['fold'] / total_hands
        features['avg_bet_size'] = np.mean(bet_sizes) if bet_sizes else 0
        features['weak_hand_river_freq'] = weak_hand_river / (weak_hand_count or 1)
        features['weak_hand_aggressiveness'] = weak_hand_aggressive / (weak_hand_count or 1)

        self.opponent_features[player_id] = features
        return features

    def train_model(self):
        """Train the Random Forest model using labeled data."""
        labeled_data = self.data[self.data['playstyle_label'].notnull()]
        if len(labeled_data) < 10:
            return False

        X, y = [], []
        for player_id in labeled_data['player_id'].unique():
            features = self.compute_features(player_id)
            if features:
                X.append([
                    features['raise_freq'], features['call_freq'], features['fold_freq'],
                    features['avg_bet_size'], features['weak_hand_river_freq'],
                    features['weak_hand_aggressiveness']
                ])
                player_labels = labeled_data[labeled_data['player_id'] == player_id]['playstyle_label']
                y.append(player_labels.mode()[0])

        if not X or not y:
            return False

        y_encoded = self.label_encoder.fit_transform(y)
        self.model.fit(X, y_encoded)
        return True

    def predict_playstyle(self, player_id):
        """Predict the opponent's playstyle using ML or heuristic fallback."""
        if self.opponent_hands_count[player_id] < self.min_hands_for_ml:
            return self._heuristic_playstyle(player_id)

        features = self.compute_features(player_id)
        if not features:
            return 'unknown'

        feature_vector = [[
            features['raise_freq'], features['call_freq'], features['fold_freq'],
            features['avg_bet_size'], features['weak_hand_river_freq'],
            features['weak_hand_aggressiveness']
        ]]

        try:
            prediction = self.model.predict(feature_vector)
            playstyle = self.label_encoder.inverse_transform(prediction)[0]
        except:
            playstyle = self._heuristic_playstyle(player_id)

        return playstyle

    def _heuristic_playstyle(self, player_id):
        """Fallback heuristic for playstyle when ML is not viable."""
        features = self.compute_features(player_id)
        if not features:
            return 'unknown'

        if features['raise_freq'] > 0.3 or features['weak_hand_aggressiveness'] > 0.5:
            return 'aggressive'
        elif features['fold_freq'] > 0.6:
            return 'tight'
        elif features['call_freq'] > 0.5:
            return 'passive'
        elif features['weak_hand_river_freq'] > 0.5:
            return 'loose'
        else:
            return 'unknown'

    def label_opponent(self, player_id, playstyle):
        """Manually label an opponent's playstyle for training."""
        if playstyle not in self.playstyle_labels:
            raise ValueError(f"Playstyle must be one of {self.playstyle_labels}")

        self.data.loc[self.data['player_id'] == player_id, 'playstyle_label'] = playstyle
        self.data.to_csv(self.data_path, index=False, quoting=csv.QUOTE_NONNUMERIC)