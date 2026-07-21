from player.player import Player
from events.event import Event

class MetamorphosisEvent(Event):
    def __init__(self):
        super().__init__("Metamorphosis")
        self.kafka_text = self._load_kafka_text()

    def _load_kafka_text(self):
        with open("data/metamorphosis.txt", "r", encoding="utf-8") as file:
            return file.read()

    def on_round_start(self, players):
        for player in players:
            if player.name == "Gregor Samsa":
                self.transform_to_insect(player)

    def transform_to_insect(self, player):
        player.is_insect = True
        player.behavior = "crawl"
        player.interaction = "unnerving"

    def on_player_interaction(self, player, target):
        if player.is_insect:
            self._handle_insect_interaction(player, target)

    def _handle_insect_interaction(self, player, target):
        # Implement insect-specific interactions
        pass