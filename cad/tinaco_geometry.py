"""
Tinaco geometric constraints for Mexico City standard models
"""

import math

class Tinaco:
    def __init__(self, model="200L"):
        self.models = {
            "200L": {"diameter": 600, "height": 1200, "mounting_points": 4},
            "300L": {"diameter": 700, "height": 1300, "mounting_points": 4},
            "500L": {"diameter": 800, "height": 1400, "mounting_points": 6}
        }
        self.dimensions = self.models.get(model, self.models["200L"])

    def validate_collector(self, collector_diameter, collector_height):
        """Validate flower collector dimensions against tinaco"""
        margin = 50  # 50mm clearance
        return (
            collector_diameter <= self.dimensions["diameter"] - margin and
            collector_height <= self.dimensions["height"] * 0.4  # Max 40% of tank height
        )

    def get_mounting_points(self):
        """Return mounting point coordinates (mm)"""
        points = []
        angle_step = 360/self.dimensions["mounting_points"]
        for i in range(self.dimensions["mounting_points"]):
            angle = math.radians(angle_step*i)
            x = self.dimensions["diameter"]/2 * math.cos(angle)
            y = self.dimensions["diameter"]/2 * math.sin(angle)
            points.append((x, y, 0))
        return points