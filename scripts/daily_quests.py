#!/usr/bin/env python3
"""
daily_quests.py — Daily Security Quests for bounty-plaza
Users can complete daily security-themed quests to earn coins.
"""
import json
import os
import sys
from datetime import date

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
QUESTS_FILE = os.path.join(DATA_DIR, "daily_quests.json")
STATE_FILE = os.path.join(DATA_DIR, "daily_quests_state.json")

# Default quests if file doesn't exist
DEFAULT_QUESTS = [
    {
        "id": "q1",
        "question": "Which of the following is a common vulnerability in smart contracts where an attacker can repeatedly call a function before the first invocation is complete?",
        "options": ["A. Reentrancy", "B. Integer Overflow", "C. Front-running", "D. Denial of Service"],
        "correct_answer": "A",
        "reward_coins": 50
    },
    {
        "id": "q2",
        "question": "In web security, what does XSS stand for?",
        "options": ["A. Cross Site Scripting", "B. Xml Site Security", "C. Extra Secure Socket", "D. None of the above"],
        "correct_answer": "A",
        "reward_coins": 30
    },
    {
        "id": "q3",
        "question": "What is the principle of least privilege (PoLP) in security?",
        "options": [
            "A. Users should be given the maximum permissions possible",
            "B. Users should be given only the permissions they need to perform their job",
            "C. Privileges should be rotated daily",
            "D. Privileges should be shared among all users"
        ],
        "correct_answer": "B",
        "reward_coins": 40
    },
    {
        "id": "q4",
        "question": "Which HTTP status code indicates that the server refused to fulfill the request due to client error?",
        "options": ["A. 200 OK", "B. 404 Not Found", "C. 500 Internal Server Error", "D. 403 Forbidden"],
        "correct_answer": "D",
        "reward_coins": 25
    },
    {
        "id": "q5",
        "question": "What is the main purpose of a salt in password hashing?",
        "options": [
            "A. To make the hash faster to compute",
            "B. To prevent rainbow table attacks",
            "C. To compress the password",
            "D. To encrypt the password"
        ],
        "correct_answer": "B",
        "reward_coins": 35
    }
]

def load_quests():
    if not os.path.exists(QUESTS_FILE):
        # Create default quests file
        with open(QUESTS_FILE, 'w') as f:
            json.dump(DEFAULT_QUESTS, f, indent=2)
        return DEFAULT_QUESTS
    with open(QUESTS_FILE, 'r') as f:
        return json.load(f)

def select_daily_quest(quests):
    """Select a quest for today and save the state."""
    today = date.today().isoformat()
    state = {
        "date": today,
        "quest_id": None,
        "completed_by": []  # list of usernames who completed today's quest
    }
    if quests:
        # Select a quest deterministically based on day of year to avoid randomness issues
        day_of_year = date.today().timetuple().tm_yday
        idx = day_of_year % len(quests)
        state["quest_id"] = quests[idx]["id"]
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    return state

def load_state():
    """Load the state for today, ensuring a quest is selected."""
    if not os.path.exists(STATE_FILE):
        # No state file, create one and select a quest
        return select_daily_quest(load_quests())
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
    today = date.today().isoformat()
    # If the date has changed, reset for new day and select a quest
    if state.get("date") != today:
        return select_daily_quest(load_quests())
    # If quest_id is None (shouldn't happen if we always set it, but just in case)
    if state.get("quest_id") is None:
        return select_daily_quest(load_quests())
    return state

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def get_quest_by_id(quests, quest_id):
    for q in quests:
        if q["id"] == quest_id:
            return q
    return None

def award_coins(username, amount):
    # For simplicity in this implementation, we'll simulate awarding coins
    # by updating the user's balance directly in the coin database
    # In a production system, this would use proper transaction logic
    try:
        import sqlite3
        DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        DB_PATH = os.path.join(DB_DIR, "coins.db")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Ensure user account exists
        cur = conn.execute("SELECT 1 FROM accounts WHERE username = ?", (username,))
        if not cur.fetchone():
            conn.execute("INSERT INTO accounts (username, balance) VALUES (?, 0)", (username,))
        
        # Add coins to user's balance
        conn.execute("UPDATE accounts SET balance = balance + ? WHERE username = ?", (amount, username))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error awarding coins: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/daily_quests.py [list|attempt] [quest_id|answer]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        quests = load_quests()
        state = load_state()
        quest_id = state["quest_id"]
        quest = get_quest_by_id(quests, quest_id)
        if quest:
            print(f"Today's Quest (ID: {quest_id}):")
            print(f"  Question: {quest['question']}")
            for i, opt in enumerate(quest["options"]):
                print(f"    {chr(65+i)}. {opt}")
            print(f"  Reward: {quest['reward_coins']} coins")
        else:
            print("Error: Could not load today's quest.")
    elif command == "attempt":
        if len(sys.argv) < 3:
            print("Usage: python scripts/daily_quests.py attempt <answer>")
            sys.exit(1)
        answer = sys.argv[2].strip().upper()
        quests = load_quests()
        state = load_state()
        quest_id = state["quest_id"]
        quest = get_quest_by_id(quests, quest_id)
        if not quest:
            print("Error: Could not load today's quest.")
            sys.exit(1)
        if answer == quest["correct_answer"]:
            username = os.getenv("USER", "unknown")
            # Check if user already completed today's quest
            completed_by = state.get("completed_by", [])
            if username in completed_by:
                print(f"You have already completed today's quest. No additional reward.")
            else:
                # Award coins
                reward_coins = quest["reward_coins"]
                if award_coins(username, reward_coins):
                    print(f"Correct! You have earned {reward_coins} coins.")
                    # Add user to completed_by list
                    completed_by.append(username)
                    state["completed_by"] = completed_by
                    save_state(state)
                    print(f"Your completion has been recorded for today.")
                else:
                    print(f"Correct! But there was an error awarding your {reward_coins} coins.")
        else:
            print(f"Incorrect. The correct answer is {quest['correct_answer']}.")
    else:
        print("Unknown command. Use 'list' or 'attempt'.")