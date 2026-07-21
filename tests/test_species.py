# ... existing code ...

def test_shitman_transformation():
    human = Human()
    shitman = Shitman()
    shitman.apply_transformation(human)
    assert human.species.name == "Shitman"

# ... existing code ...