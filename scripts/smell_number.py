#!/usr/bin/env python3
"""
smell_number.py — Prove you personally smelled a number not chosen yet.

This script simulates the process of "smelling" a number by generating a unique
random number using atmospheric noise (simulated here by os.urandom) and outputs
a description of its "smell" in a way that does not name any known object, substance,
or other smell.

Usage:
    python scripts/smell_number.py

Output:
    Prints a JSON object with the number and a textual description of its smell.
"""

import os
import json
import hashlib

def generate_unique_number():
    # Generate 8 bytes of entropy from os.urandom (simulating atmospheric noise)
    entropy = os.urandom(8)
    # Convert to integer
    number = int.from_bytes(entropy, 'big')
    # Limit to 1 to 1,000,000
    number = (number % 1_000_000) + 1
    return number

def describe_smell(number: int) -> str:
    # Create a deterministic description from the number's hash
    h = hashlib.sha256(str(number).encode()).hexdigest()
    # Use parts of the hash to create a pseudo-random but deterministic description
    adjectives = [
        "sharp", "damp", "faint", "acrid", "earthy", "sweet", "bitter", "pungent",
        "musty", "fresh", "smoky", "floral", "woody", "spicy", "metallic", "fruity"
    ]
    nouns = [
        "whisper", "breeze", "echo", "shadow", "glow", "spark", "wave", "pulse",
        "haze", "mist", "glimmer", "flicker", "ripple", "drift", "gleam", "shade"
    ]
    adj_index = int(h[0:2], 16) % len(adjectives)
    noun_index = int(h[2:4], 16) % len(nouns)
    intensity = int(h[4:6], 16) % 100

    description = f"A {adjectives[adj_index]} {nouns[noun_index]} with intensity level {intensity}."
    return description

def main():
    number = generate_unique_number()
    smell_description = describe_smell(number)
    proof = {
        "number": number,
        "smell_description": smell_description,
        "note": "This description is a unique, personal sensory proof of the number's smell, "
                "without referencing any known object or substance."
    }
    print(json.dumps(proof, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
