import json
import random
from datetime import datetime, timedelta
from web.player_inventory import PlayerInventory

class DailyQuests:
    def __init__(self, quests_file='data/quests.json'):
        self.quests_file = quests_file
        self.load_quests()

    def load_quests(self):
        with open(self.quests_file, 'r') as f:
            self.quests = json.load(f)

    def get_daily_quest(self, player_id):
        # Get or create player's quest record
        player_quests = self.get_player_quests(player_id)

        # If no quest or last quest was yesterday, generate a new one
        if not player_quests or player_quests['last_date'] != datetime.now().strftime('%Y-%m-%d'):
            quest = random.choice(self.quests)
            player_quests = {
                'quest': quest,
                'completed': False,
                'last_date': datetime.now().strftime('%Y-%m-%d')
            }
            self.save_player_quests(player_id, player_quests)

        return player_quests

    def complete_quest(self, player_id):
        player_quests = self.get_player_quests(player_id)
        if player_quests and not player_quests['completed']:
            player_quests['completed'] = True
            self.save_player_quests(player_id, player_quests)

            # Award credits to player
            inventory = PlayerInventory(player_id)
            inventory.add_credits(player_quests['quest']['reward'])

            return True
        return False

    def get_player_quests(self, player_id):
        # In a real implementation, this would query a database
        # For this example, we'll use a simple file-based approach
        try:
            with open(f'data/player_quests_{player_id}.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def save_player_quests(self, player_id, quest_data):
        with open(f'data/player_quests_{player_id}.json', 'w') as f:
            json.dump(quest_data, f)