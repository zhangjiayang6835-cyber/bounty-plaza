import pytest
import time
from scripts.dodge_roll import DodgeRollManager

def test_dodge_roll_success():
    manager = DodgeRollManager(stamina_cost=20, iframe_duration=0.5, cooldown=1.0)
    res = manager.execute_roll(current_stamina=100)
    assert res["success"] is True
    assert res["stamina_remaining"] == 80
    assert res["is_invincible"] is True

def test_dodge_roll_insufficient_stamina():
    manager = DodgeRollManager(stamina_cost=20, iframe_duration=0.5, cooldown=1.0)
    res = manager.execute_roll(current_stamina=10)
    assert res["success"] is False
    assert res["reason"] == "Insufficient stamina"

def test_dodge_roll_cooldown():
    manager = DodgeRollManager(stamina_cost=20, iframe_duration=0.5, cooldown=1.0)
    res1 = manager.execute_roll(current_stamina=100)
    assert res1["success"] is True
    
    res2 = manager.execute_roll(current_stamina=80)
    assert res2["success"] is False
    assert "cooldown" in res2["reason"].lower()
