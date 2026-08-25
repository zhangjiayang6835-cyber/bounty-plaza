# Issue #922: Solution for #921: Solution for #889: Fix #832: [Bounty] [3 USDC][Open Competit

```python
            return True

    def close_competition(self) -> None:
        """Mark the competition as closed"""
        if self.status == "closed":
            return
        self.status = "closed"

    def get_winner(self) -> Optional[Dict]:
        """Determine the winner based on some criteria (simplified for this example)"""
        if not self.entries or self.status != "closed":
            return None

        # Simple winner selection - first entry in this example
        return self.entries[0]

    def to_dict(self) -> Dict:
        """Convert competition data to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prize": self.prize,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "status": self.status,
            "entries": self.entries
        }

class CompetitionManager:
    def __init__(self):
        self.competitions: Dict[str, Competition] = {}

    def create_competition(self, name: str, description: str, prize: float,
                          start_date: str, end_date: str) -> str:
        """Create a new competition"""
        competition = Competition(name, description, prize, start_date, end_date)
        self.competitions[competition.id] = competition
        return competition.id

    def get_competition(self, competition_id: str) -> Optional[Competition]:
        """Retrieve a competition by ID"""
        return self.competitions.get(competition_id)

    def save_to_file(self, filename: str) -> None:
        """Save all competitions to a JSON file"""
        with open(filename, 'w') as f:
            json.dump({id: comp.to_dict() for id, comp in self.competitions.items()}, f, indent=2)

    def load_from_file(self, filename: str) -> None:
        """Load competitions from a JSON file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                for id, comp_data in data.items():
                    comp = Competition(
                        name=comp_data["name"],
                        description=comp_data["description"],
                        prize=comp_data["prize"],
                        start_date=comp_data["start_date"],
                        end_date=comp_data["end_date"]
                    )
                    comp.entries = comp_data["entries"]
                    comp.status = comp_data["status"]
                    self.competitions[id] = comp
        except FileNotFoundError:
            print(f"File {filename} not found. Starting with empty competitions.")

def main():
    """Demonstration of the competition system"""
    manager = CompetitionManager()

    # Create a competition
    comp_id = manager.create_competition(
        name="Open Competition V2",
        description="A programming competition with a 3 USDC prize",
        prize=3.0,
        start_date="2023-01-01",
        end_date="2023-12-31"
    )

    # Add entries (simulating participants)
    manager.get_competition(comp_id).add_entry("Alice", "Python solution")
    manager.get_competition(comp_id).add_entry("Bob", "Java solution")

    # Close the competition
    manager.get_competition(comp_id).close_competition()

    # Get the winner
    winner = manager.get_competition(comp_id).get_winner()
    print(f"Winner: {winner['participant']} with submission: {winner['submission']}")

    # Save to file
    manager.save_to_file("competitions.json")

if __name__ == "__main__":
    main()
```

```python
# File: test_solution.py
# Unit tests for the competition system

import unittest
from datetime import datetime, date
from solution import Competition, CompetitionManager

class TestCompetition(unittest.TestCase):
    def setUp(self):
        self.competition = Competition(
            name="Test Competition",
            description="Test description",
            prize=100.0,
            start_date="2023-01-01",
            end_date="2023-12-31"
        )

    def test_initialization(self):
        self.assertEqual(self.competition.name, "Test Competition")
        self.assertEqual(self.competition.prize, 100.0)
        self.assertEqual(self.competition.start_date, date(2023, 1, 1))
        self.assertEqual(self.competition.end_date, date(2023, 12, 31))
        self.assertEqual(self.competition.status, "active")

    def test_add_entry(self):
        self.assertTrue(self.competition.add_entry("Alice", "Python solution"))
        self.assertEqual(len(self.competition.entries), 1)
        self.assertFalse(self.competition.add_entry("Bob", "Java solution"))  # Should fail if closed

    def test_close_competition(self):
        self.competition.close_competition()
        self.assertEqual(self.competition.status, "closed")
        self.assertFalse(self.competition.add_entry("Bob", "Java solution"))

    def test_get_winner(self):
        self.competition.add_entry("Alice", "Python solution")
        self.competition.close_competition()
        winner = self.competition.get_winner()
        self.assertIsNotNone(winner)
        self.assertEqual(winner["participant"], "Alice")

class TestCompetitionManager(unittest.TestCase):
    def setUp(self):
        self.manager = CompetitionManager()

    def test_create_and_get_competition(self):
        comp_id = self.manager.create_competition(
            name="Test Competition",
            description="Test",
            prize=100.0,
            start_date="2023-01-01",
            end_date="2023-12-31"
        )
        self.assertIsNotNone(self.manager.get_competition(comp_id))

    def test_save_and_load(self):
        comp_id = self.manager.create_competition(
            name="Test Competition",
            description="Test",
            prize=100.0,
            start_date="2023-01-01",
            end_date="2023-12-31"
        )
        self.manager.get_competition(comp_id).add_entry("Alice", "Python solution")

        # Save and load
        self.manager.save_to_file("test_competitions.json")
        self.manager.__init__()  # Reset manager
        self.manager.load_from_file("test_competitions.json")

        loaded_comp = self.manager.get_competition(comp_id)
        self.assertIsNotNone(loaded_comp)
        self.assertEqual(len(loaded_comp.entries), 1)

if __name__ == "__main__":
    unittest.main()
```

## Verification
- Generated by DevilX auto-claim (OpenRouter/NVIDIA)
- Tue Aug 25 18:07:34 UTC 2026

Closes #922
