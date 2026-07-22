import json
import sys
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
USERS_FILE = os.path.join(DATA_DIR, 'seed_users.json')

def load_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def add_nanites(username, amount):
    users = load_users()
    for user in users:
        if user['username'] == username:
            if 'nanites' not in user:
                user['nanites'] = 0
            user['nanites'] += amount
            save_users(users)
            return f"Added {amount} nanites to {username}. Current: {user['nanites']}"
    return "User not found."

def remove_nanites(username, amount):
    users = load_users()
    for user in users:
        if user['username'] == username:
            if 'nanites' not in user:
                return "No nanites to remove."
            user['nanites'] -= amount
            if user['nanites'] < 0:
                user['nanites'] = 0
            save_users(users)
            return f"Removed {amount} nanites from {username}. Current: {user['nanites']}"
    return "User not found."

def get_nanites(username):
    users = load_users()
    for user in users:
        if user['username'] == username:
            return user.get('nanites', 0)
    return None

def list_nanites():
    users = load_users()
    return {user['username']: user.get('nanites', 0) for user in users}

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: nanites.py <add|remove|get|list> [username] [amount]")
        sys.exit(1)
    command = sys.argv[1]
    if command == 'add':
        if len(sys.argv) != 4:
            print("Usage: nanites.py add <username> <amount>")
            sys.exit(1)
        username = sys.argv[2]
        amount = int(sys.argv[3])
        print(add_nanites(username, amount))
    elif command == 'remove':
        if len(sys.argv) != 4:
            print("Usage: nanites.py remove <username> <amount>")
            sys.exit(1)
        username = sys.argv[2]
        amount = int(sys.argv[3])
        print(remove_nanites(username, amount))
    elif command == 'get':
        if len(sys.argv) != 3:
            print("Usage: nanites.py get <username>")
            sys.exit(1)
        username = sys.argv[2]
        nanites = get_nanites(username)
        if nanites is not None:
            print(f"{username} has {nanites} nanites.")
        else:
            print("User not found.")
    elif command == 'list':
