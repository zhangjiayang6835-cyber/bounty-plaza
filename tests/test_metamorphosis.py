import unittest
from events.metamorphosis import MetamorphosisEvent
from player.player import Player

class TestMetamorphosisEvent(unittest.TestCase):
    def setUp(self):
        self.event = MetamorphosisEvent()
        self.players = [Player("Gregor Samsa"), Player("Other Player")]

    def test_transformation(self):
        self.event.on_round_start(self.players)
        self.assertTrue(self.players[0].is_insect)
        self.assertFalse(self.players[1].is_insect)

    def test_kafka_text_loaded(self):
        self.assertIsNotNone(self.event.kafka_text)
        self.assertGreater(len(self.event.kafka_text), 0)

if __name__ == '__main__':
    unittest.main()