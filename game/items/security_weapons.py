class SecurityWeapon:
    def __init__(self, name, damage, range, fire_rate, special_effect=None):
        self.name = name
        self.damage = damage
        self.range = range
        self.fire_rate = fire_rate
        self.special_effect = special_effect

    def get_damage(self):
        return self.damage

    def get_range(self):
        return self.range

    def get_fire_rate(self):
        return self.fire_rate

    def apply_special_effect(self, target):
        if self.special_effect:
            self.special_effect.apply(target)

class SecurityRifle(SecurityWeapon):
    def __init__(self):
        super().__init__(
            name="Security Rifle",
            damage=25,  # Reduced from previous value
            range=50,
            fire_rate=0.3,
            special_effect=None
        )

class SecurityShotgun(SecurityWeapon):
    def __init__(self):
        super().__init__(
            name="Security Shotgun",
            damage=40,  # Reduced from previous value
            range=20,
            fire_rate=1.0,
            special_effect=None
        )

class SecurityPistol(SecurityWeapon):
    def __init__(self):
        super().__init__(
            name="Security Pistol",
            damage=15,  # Reduced from previous value
            range=30,
            fire_rate=0.5,
            special_effect=None
        )

class SecurityBaton(SecurityWeapon):
    def __init__(self):
        super().__init__(
            name="Security Baton",
            damage=10,  # Reduced from previous value
            range=2,
            fire_rate=0.2,
            special_effect=None
        )