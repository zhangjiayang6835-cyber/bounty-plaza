import unittest
from game.items.security_weapons import SecurityRifle, SecurityShotgun, SecurityPistol, SecurityBaton

class TestSecurityWeapons(unittest.TestCase):
    def test_security_rifle_stats(self):
        rifle = SecurityRifle()
        self.assertEqual(rifle.get_damage(), 25)
        self.assertEqual(rifle.get_range(), 50)
        self.assertEqual(rifle.get_fire_rate(), 0.3)

    def test_security_shotgun_stats(self):
        shotgun = SecurityShotgun()
        self.assertEqual(shotgun.get_damage(), 40)
        self.assertEqual(shotgun.get_range(), 20)
        self.assertEqual(shotgun.get_fire_rate(), 1.0)

    def test_security_pistol_stats(self):
        pistol = SecurityPistol()
        self.assertEqual(pistol.get_damage(), 15)
        self.assertEqual(pistol.get_range(), 30)
        self.assertEqual(pistol.get_fire_rate(), 0.5)

    def test_security_baton_stats(self):
        baton = SecurityBaton()
        self.assertEqual(baton.get_damage(), 10)
        self.assertEqual(baton.get_range(), 2)
        self.assertEqual(baton.get_fire_rate(), 0.2)

if __name__ == '__main__':
    unittest.main()