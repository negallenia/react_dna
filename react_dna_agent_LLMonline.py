import scadnano as sc
import re
from datetime import datetime
import os
import requests
import time

# Parse the prompt to extract values (dynamically, using LLM)
def parse_prompt_with_llm(prompt: str):
    MODEL_NAME = "HuggingFaceH4/zephyr-7b-beta"
    url = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

    headers = {
        "Authorization": f"Bearer ", 
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": f"Extract the following details from this DNA design prompt: {prompt}. Provide the output in this format: 'Helices: <number>, Total length: <number>, Loops: [(<helix1>, <helix2>, <length>)], Sticky ends: [(<helix1>, <helix2>)], Crossovers: [(<helix1>, <helix2>)]'.",
        "parameters": {
            "max_new_tokens": 300,
            "temperature": 0.2
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    result = response.json()

    # Handle model loading or errors
    if isinstance(result, dict) and result.get("error"):
        print(f"Model loading... waiting 5 seconds. Error: {result['error']}")
        time.sleep(5)
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()

    # Check the result
    if isinstance(result, list) and "generated_text" in result[0]:
        parsed_data = result[0]['generated_text'].strip()
    else:
        raise ValueError(f"Unexpected API response: {result}")

    # Debugging: Print the parsed data
    print("Parsed Data from LLM:", parsed_data)

    # Attempt to parse data
    try:
        helices, length, loop_instructions, sticky_end_instructions, crossover_instructions = parse_structured_data(parsed_data)
    except Exception as e:
        print(f"Error while parsing structured data: {e}")
        helices, length, loop_instructions, sticky_end_instructions, crossover_instructions = None, None, [], [], []

    return helices, length, loop_instructions, sticky_end_instructions, crossover_instructions

"""# parse function
def parse_structured_data(parsed_data: str):

    helices = None
    length = None
    loop_instructions = []
    sticky_end_instructions = []
    crossover_instructions = []

    # Extract the number of helices
    helices_match = re.search(r'Helices:\s*(\d+)', parsed_data)
    if helices_match:
        helices = int(helices_match.group(1))
    else:
        raise ValueError("The LLM response did not provide the number of helices.")

    # Extract the total base length
    length_match = re.search(r'Total length:\s*(\d+)', parsed_data)
    if length_match:
        length = int(length_match.group(1))
    else:
        raise ValueError("The LLM response did not provide the total base length.")

    # Extract loop instructions
    loop_matches = re.findall(r'\((\d+),\s*(\d+),\s*(\d+)\)', parsed_data)  
    for match in loop_matches:
        loop_instructions.append((int(match[0]), int(match[1]), int(match[2])))

    # Extract sticky end instructions
    sticky_matches = re.findall(r'\((\d+),\s*(\d+)\)', parsed_data)  
    for match in sticky_matches:
        sticky_end_instructions.append((int(match[0]), int(match[1])))

    # Extract crossover instructions
    crossover_matches = re.findall(r'\((\d+),\s*(\d+)\)', parsed_data)  
    for match in crossover_matches:
        crossover_instructions.append((int(match[0]), int(match[1])))

    return helices, length, loop_instructions, sticky_end_instructions, crossover_instructions"""


def parse_structured_data(parsed_data: str):

    helices = None
    length = None
    loop_instructions = []
    sticky_end_instructions = []
    crossover_instructions = []

    # Extract the number of helices
    helices_match = re.search(r'Helices:\s*(\d+)', parsed_data)
    if helices_match:
        helices = int(helices_match.group(1))
    else:
        raise ValueError("The LLM response did not provide the number of helices.")

    # Extract the total base length
    length_match = re.search(r'Total length:\s*(\d+)', parsed_data)
    if length_match:
        length = int(length_match.group(1))
    else:
        raise ValueError("The LLM response did not provide the total base length.")

    # Extract loop instructions
    loop_matches = re.findall(r'\((\d+),\s*(\d+),\s*(\d+)\)', parsed_data)  
    for match in loop_matches:
        loop_instructions.append((int(match[0]), int(match[1]), int(match[2])))

    # Extract sticky end instructions
    sticky_matches = re.findall(r'\((\d+),\s*(\d+)\)', parsed_data)  
    for match in sticky_matches:
        sticky_end_instructions.append((int(match[0]), int(match[1])))

    # Extract crossover instructions
    crossover_matches = re.findall(r'\((\d+),\s*(\d+)\)', parsed_data)  
    for match in crossover_matches:
        crossover_instructions.append((int(match[0]), int(match[1])))

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
    helices, total_bases, loop_instructions, sticky_end_instructions, crossover_instructions = parse_prompt_with_llm(prompt)
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

    return steps, f"{output_directory}/{filename}"  

# MAIN
if __name__ == "__main__":
    prompt = input("Describe your DNA structure:\n> ")
    steps, output = react_design(prompt)  # Unpack steps and output

    print("\nReAct Trace:")
    for step in steps:
        print(step)

    print(f"\nFinal design saved to {output}")