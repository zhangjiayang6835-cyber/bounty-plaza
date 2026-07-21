class MechEquipment:
    def __init__(self, mech):
        self.mech = mech
        self.modules = []
        self.capacity = mech.tier * 10  # Base capacity based on mech tier

    def add_module(self, module):
        if self.get_used_capacity() + module.complexity <= self.capacity:
            self.modules.append(module)
            return True
        return False

    def get_used_capacity(self):
        return sum(module.complexity for module in self.modules)

    def deactivate_all(self):
        for module in self.modules:
            module.deactivate()