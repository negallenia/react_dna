import json
import random
import string
from tqdm import tqdm

# --- CONFIGURATION ---
NUM_EXAMPLES = 10000  # total examples
NOISE_PROB = 0.35    # % of messy prompts

# --- Basic vocab for prompt generation ---
structures = [
    "2D grid", "3D cube", "linear array", "double helix", "twisted ladder", "square lattice"
]
actions = [
    "Create", "Make", "Design", "Build", "Generate"
]
units = ["bases", "bp", "base pairs"]

# --- Functions to create prompts and outputs ---
def create_clean_prompt():
    action = random.choice(actions)
    structure = random.choice(structures)
    helices = random.randint(2, 20)
    length = random.choice([32, 64, 128, 256])
    unit = random.choice(units)
    prompt = f"{action} a {structure} with {helices} helices, each {length} {unit} long."
    return prompt, helices, length, structure

def create_fake_output(helices, length, structure):
    # Fake scadnano-style output (you could replace with real scadnano JSON if you want)
    output = {
        "design": {
            "structure": structure,
            "helices": helices,
            "length_per_helix": length,
            "scaffold": "random",  # placeholder
            "staples": "auto"
        }
    }
    return json.dumps(output)

# --- Functions to messify prompts ---
def random_typo(word):
    if len(word) < 4:
        return word
    idx = random.randint(0, len(word)-2)
    return word[:idx] + word[idx+1] + word[idx] + word[idx+2:]

def messify_prompt(prompt):
    words = prompt.split()
    new_words = []
    for word in words:
        if random.random() < 0.15:  # typo some words
            word = random_typo(word)
        if random.random() < 0.1:  # random casing
            word = word.lower() if random.random() < 0.5 else word.upper()
        new_words.append(word)
    
    # Random insertions
    if random.random() < 0.2:
        new_words = ["plz"] + new_words
    if random.random() < 0.1:
        new_words.append("ty")
    
    # Random shuffle some part
    if random.random() < 0.1 and len(new_words) > 5:
        i = random.randint(0, len(new_words)-3)
        new_words[i], new_words[i+1] = new_words[i+1], new_words[i]
    
    return " ".join(new_words)

# --- MAIN dataset creation ---
dataset = []

for _ in tqdm(range(NUM_EXAMPLES)):
    clean_prompt, helices, length, structure = create_clean_prompt()
    output = create_fake_output(helices, length, structure)

    # Decide if we add noise
    if random.random() < NOISE_PROB:
        prompt = messify_prompt(clean_prompt)
    else:
        prompt = clean_prompt

    # Final dataset entry
    entry = {
        "prompt": prompt,
        "output": output
    }
    dataset.append(entry)

# --- Save to JSONL file ---
with open("scadnano_finetune_dataset.jsonl", "w") as f:
    for item in dataset:
        f.write(json.dumps(item) + "\n")

print(f"✅ Dataset with {NUM_EXAMPLES} examples saved to scadnano_finetune_dataset.jsonl")
