from web.game_mechanics import DailyQuests

class GameEvents:
    def __init__(self):
        self.daily_quests = DailyQuests()

    def trigger_daily_quest_event(self, player_id):
        # This would be called at the start of each day for each player
        quest = self.daily_quests.get_daily_quest(player_id)
        return quest