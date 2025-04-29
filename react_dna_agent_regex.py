import scadnano as sc
import re
from datetime import datetime
import os

# Parse the prompt to extract values (dynamically, later I want LLM to do this for me)
def parse_prompt(prompt):

    helices = int(re.search(r'(\d+)\s*helices?', prompt).group(1)) # if 'helices' in prompt else 6
    length_match = re.search(r'(\d+)\s*(?:bases|bp)', prompt)
    length = int(length_match.group(1)) # if length_match else 32
    
    # Loop instructions: (helix_start, helix_end, loop_length)
    loop_instructions = []
    loop_matches = re.findall(r'helix\s*(\d+)\s*and\s*(\d+)\s*have\s*a\s*loop\s*of\s*(\d+)\s*base\s*pairs', prompt.lower())
    for match in loop_matches:
        loop_instructions.append((int(match[0]), int(match[1]), int(match[2])))  # Store as (helix_start, helix_end, loop_length)

    # Sticky end instructions: (helix1, helix2)
    sticky_end_instructions = []
    sticky_matches = re.findall(r'helix\s*(\d+)\s*has\s*a\s*sticky\s*end\s*linking\s*with\s*helix\s*(\d+)', prompt.lower())
    for match in sticky_matches:
        sticky_end_instructions.append((int(match[0]), int(match[1])))  # Store as (helix1, helix2)

    # Crossover instructions: (helix1, helix2)
    crossover_instructions = []
    crossover_matches = re.findall(r'crossovers?\s*between\s*helix\s*(\d+)\s*and\s*helix\s*(\d+)', prompt.lower())
    for match in crossover_matches:
        crossover_instructions.append((int(match[0]), int(match[1])))  # Store as (helix1, helix2)

    return helices, length, loop_instructions, sticky_end_instructions, crossover_instructions


# Logging
def log_step(steps, thought, action, observation):
    steps.append({
        "thought": thought,
        "action": action,
        "observation": observation
    })


# ReAct function
def react_design(prompt: str):
    steps = []  

    # === Step 1: Extract parameters from prompt ===
    helices, total_bases, loop_instructions, sticky_end_instructions, crossover_instructions = parse_prompt(prompt)
    offset = total_bases // 2  # middle of the strand

    # === Step 2: Initialize design ===
    helices_list = [sc.Helix(max_offset=total_bases) for _ in range(helices)]
    design = sc.Design(helices=helices_list, strands=[], grid=sc.Grid.square)
    design.set_helices_view_order(list(range(helices)))
    log_step(steps, "Initialize design", "Create helices and set view order", "Design initialized")

    # === Step 3: Add strands and nick them ===
    for i in range(helices):
        strand = sc.Strand([
            sc.Domain(helix=i, start=0, end=total_bases, forward=True)
        ])
        design.add_strand(strand)
        design.add_nick(helix=i, offset=offset, forward=True)
        log_step(steps, f"Add strand to helix {i}", "Add strand and nick", "Strand added and nicked")
    
    # === Step 4: Add loops if present ===
    for loop in loop_instructions:
        helix_start, helix_end, loop_length = loop
        design.add_loopout(helix_start - 1, helix_end - 1, loop_length)  # Adjust indexing (1-based to 0-based)
        log_step(steps, f"Add loop between helix {helix_start} and {helix_end}", "Add loop", f"Loop of {loop_length} bases added")
    
    # === Step 5: Add crossovers ===
    for helix1, helix2 in crossover_instructions:
        try:
            # Check if strands exist at the correct offsets before adding crossovers
            strand1_exists = any(any(domain.helix == helix1 - 1 and domain.start <= offset < domain.end for domain in strand.domains) for strand in design.strands)
            strand2_exists = any(any(domain.helix == helix2 - 1 and domain.start <= offset < domain.end for domain in strand.domains) for strand in design.strands)

            # Ensure strands exist at the correct offset for crossovers
            if strand1_exists and strand2_exists:
                design.add_full_crossover(helix=helix1 - 1, helix2=helix2 - 1, offset=offset, forward=True)  # Adjust indexing
                log_step(steps, f"Add crossover between helix {helix1} and {helix2}", "Add crossover", "Crossover added")
            else:
                log_step(steps, f"Failed to add crossover between helix {helix1} and {helix2}", "Add crossover", "Strands not found at the correct offsets")
        except Exception as e:
            log_step(steps, f"Failed to add crossover between helix {helix1} and {helix2}", "Add crossover", f"Error: {e}")
    
    # === Step 6: Add sticky ends ===
    try:
        for helix1, helix2 in sticky_end_instructions:
            sticky_end_helix1 = sc.Strand([
                sc.Domain(helix=helix1 - 1, start=total_bases - 5, end=total_bases, forward=True)
            ])
            sticky_end_helix2 = sc.Strand([
                sc.Domain(helix=helix2 - 1, start=0, end=5, forward=True)
            ])
            design.add_strand(sticky_end_helix1)
            design.add_strand(sticky_end_helix2)
            log_step(steps, f"Add sticky ends between helix {helix1} and {helix2}", "Add sticky ends", "Sticky ends added")
    except Exception as e:
        log_step(steps, "Failed to add sticky ends", "Add sticky ends", f"Error: {e}")

    # === Step 7: Save the model ===
    output_directory = 'designs'
    os.makedirs(output_directory, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'dna_design_{helices}x{total_bases}_{timestamp}.sc'
    design.write_scadnano_file(directory=output_directory, filename=filename)
    log_step(steps, "Save design", f"Save to {output_directory}/{filename}", "Design saved")

    return steps, f"{output_directory}/{filename}"  # Return steps and the file path

# MAIN
if __name__ == "__main__":
    prompt = input("Describe your DNA structure:\n> ")
    steps, output = react_design(prompt)  # Unpack steps and output

    print("\nReAct Trace:")
    for step in steps:
        print(step)

    print(f"\nFinal design saved to {output}")
