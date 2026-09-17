"""
Cultivation skill module.
Players can hone their body and mind to master martial arts and become enlightened.
"""

class Cultivation:
    def __init__(self, player_id=None):
        self.player_id = player_id
        self.level = 0          # 0 = mortal, 1+ = cultivation realms
        self.exp = 0
        self.enlightenment = 0  # enlightenment points
        self.martial_arts = []
        self.spells = []
        self.essence = 0        # essence to transfer
        self.resistance = {
            "osmanthus_soup": False,
            "lightning": 0
        }
        self.training_log = []

    def practice_feng_shui(self, hours=1):
        """Practice Feng Shui to harmonize energy."""
        self.exp += 10 * hours
        self.enlightenment += 1 * hours
        self._check_level_up()
        self.training_log.append(f"Practiced Feng Shui for {hours} hours")
        return f"Gained {10*hours} exp, {1*hours} enlightenment from Feng Shui."

    def meditate(self, hours=1):
        """Meditation cultivates inner peace and insight."""
        self.exp += 5 * hours
        self.enlightenment += 3 * hours
        self._check_level_up()
        self.training_log.append(f"Meditated for {hours} hours")
        return f"Gained {5*hours} exp, {3*hours} enlightenment from meditation."

    def survive_extreme_cold_realm(self, duration=1):
        """Endure the Extreme Cold Realm to strengthen body and spirit."""
        # Requires minimum level 2
        if self.level < 2:
            return "You are not ready for the Extreme Cold Realm. Reach level 2 first."
        self.exp += 20 * duration
        self.enlightenment += 5 * duration
        self._check_level_up()
        self.training_log.append(f"Survived Extreme Cold Realm for {duration} cycles")
        return f"Gained {20*duration} exp, {5*duration} enlightenment from extreme cold."

    def rigorous_training(self, intensity=1):
        """Rigorous physical and mental training."""
        self.exp += 15 * intensity
        self._check_level_up()
        self.training_log.append(f"Did rigorous training intensity {intensity}")
        return f"Gained {15*intensity} exp from rigorous training."

    def acupuncture(self, points=1):
        """Acupuncture aligns meridians."""
        self.exp += 8 * points
        self.enlightenment += 2 * points
        self._check_level_up()
        self.training_log.append(f"Received acupuncture on {points} points")
        return f"Gained {8*points} exp, {2*points} enlightenment from acupuncture."

    def consume_herb(self, herb_type="common"):
        """Consume magical herbs and elixirs."""
        gains = {"common": (5, 0), "rare": (20, 5), "legendary": (50, 20)}
        exp_gain, enlight_gain = gains.get(herb_type, (1, 0))
        self.exp += exp_gain
        self.enlightenment += enlight_gain
        self._check_level_up()
        self.training_log.append(f"Consumed {herb_type} herb/elixir")
        return f"Gained {exp_gain} exp, {enlight_gain} enlightenment from {herb_type} herb."

    def struck_by_lightning(self, times=1):
        """Get struck by lightning several times in a row. Dangerous but rewarding."""
        for _ in range(times):
            self.exp += 100
            self.enlightenment += 10
            self.resistance["lightning"] += 1
            self._check_level_up()
        self.training_log.append(f"Struck by lightning {times} times")
        return f"Gained {100*times} exp, {10*times} enlightenment from lightning strikes."

    def _check_level_up(self):
        """Check and perform level up based on exp thresholds."""
        # Simple exponential leveling
        while self.exp >= 100 * (2 ** self.level):
            self.exp -= 100 * (2 ** self.level)
            self.level += 1
            # Unlock benefits
            if self.level >= 1:
                self.martial_arts.append("Basic Martial Art")
            if self.level >= 3:
                self.spells.append("Minor Spell")
            if self.level >= 5:
