import random

def generate_human_like_dna_design_prompt():
    num_helices = random.choice([4, 5, 6])
    helix_length = random.choice([80, 100, 120])
    
    crossover_pairs = []
    possible_pairs = [(i, i+1) for i in range(1, num_helices)]
    num_crossovers = random.choice([1, 2, 3])
    selected_pairs = random.sample(possible_pairs, min(num_crossovers, len(possible_pairs)))
    
    for (h1, h2) in selected_pairs:
        pos = random.randint(30, helix_length - 30)
        crossover_pairs.append((h1, h2, pos))
    
    sticky_ends = []
    if num_helices >= 4:
        sticky_ends.append((2, 4))
    
    # Generate human-like phrase
    prompt_parts = []
    prompt_parts.append(f"Hi, I'd like to design a 2D DNA origami structure.")
    prompt_parts.append(f"Let's use {num_helices} helices, each exactly {helix_length} bases long.")
    
    if crossover_pairs:
        cross_txt = ", ".join([f"between helices {h1}-{h2} around base {pos}" for (h1, h2, pos) in crossover_pairs])
        prompt_parts.append(f"I'd like to have crossovers {cross_txt}.")
    
    if sticky_ends:
        for (h1, h2) in sticky_ends:
            prompt_parts.append(f"Also, please add a sticky end from helix {h1} to helix {h2}.")
    
    prompt_parts.append(f"Can you set it up cleanly in scadnano?")
    
    full_prompt = " ".join(prompt_parts)
    return full_prompt

# Example use:
print(generate_human_like_dna_design_prompt())
