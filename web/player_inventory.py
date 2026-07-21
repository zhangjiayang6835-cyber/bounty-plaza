import json

class PlayerInventory:
    def __init__(self, player_id):
        self.player_id = player_id
        self.load_inventory()

    def load_inventory(self):
        try:
            with open(f'data/inventory_{self.player_id}.json', 'r') as f:
                self.inventory = json.load(f)
        except FileNotFoundError:
            self.inventory = {'credits': 0}

    def save_inventory(self):
        with open(f'data/inventory_{self.player_id}.json', 'w') as f:
            json.dump(self.inventory, f)

    def add_credits(self, amount):
        self.inventory['credits'] += amount
        self.save_inventory()

    def get_credits(self):
        return self.inventory['credits']