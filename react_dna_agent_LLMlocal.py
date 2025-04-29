import scadnano as sc
import re
import os
from datetime import datetime
from transformers import GPT2Tokenizer, GPT2LMHeadModel, pipeline

# Load pre-trained GPT-2 model and tokenizer
tokenizer = GPT2Tokenizer.from_pretrained('gpt2')  # or 'distilgpt2' for a smaller model
model = GPT2LMHeadModel.from_pretrained('gpt2')  # or 'distilgpt2' for a smaller model
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

# Function to extract parameters from the model output
def extract_parameters(model_output):
    # Number of helices: search for the number of helices (expected to be a number in the text)
    helices_match = re.search(r"(\d+) helices", model_output)
    helices = int(helices_match.group(1)) if helices_match else None

    # Total length: (base pairs per helix * number of helices)
    length_match = re.search(r"each (\d+) base pairs", model_output)
    base_pair_length = int(length_match.group(1)) if length_match else None
    total_length = helices * base_pair_length if helices and base_pair_length else None

    # Loops: search for loops between helices and their lengths
    loops = []
    loop_matches = re.findall(r"helixes (\d+) and (\d+) loop with (\d+) base pairs", model_output)
    for match in loop_matches:
        loops.append([int(match[0]), int(match[1]), int(match[2])])

    # Sticky ends: search for sticky ends (helix pair)
    sticky_ends = []
    sticky_end_matches = re.findall(r"Helix (\d+) should have a sticky end that connects to helix (\d+)", model_output)
    for match in sticky_end_matches:
        sticky_ends.append([int(match[0]), int(match[1])])

    # Crossovers: search for crossovers between helices
    crossovers = []
    crossover_matches = re.findall(r"crossovers between helices (\d+) and (\d+)", model_output)
    for match in crossover_matches:
        crossovers.append([int(match[0]), int(match[1])])

    return helices, total_length, loops, sticky_ends, crossovers

# ReAct function that integrates the design process
def react_design(prompt: str):
    # Generate model output using LLM
    formatted_prompt = f'Given this DNA design description: "{prompt}".\nExtract the key parameters by reasoning step-by-step and return them in this format:\n' \
                       '1. Number of helices: <int>\n2. Total length: <int>\n3. Loops: <list of loops, each defined as [helix_start, helix_end, loop_length]>\n' \
                       '4. Sticky ends: <list of sticky ends, each defined as [helix1, helix2]>\n5. Crossovers: <list of crossovers, each defined as [helix1, helix2]>\n' \
                       'Answer in a numbered list format only, no explanations.'

    model_output = generator(formatted_prompt, max_length=500, truncation=True)[0]["generated_text"]
    model_output = model_output.strip()

    # Extract parameters from model output
    helices, total_length, loops, sticky_ends, crossovers = extract_parameters(model_output)

    if helices is None or total_length is None:
        print("Error: Failed to extract necessary parameters.")
        return None

    offset = total_length // 2  # Middle of the strand

    # Initialize the design
    helices_list = [sc.Helix(max_offset=total_length) for _ in range(helices)]
    design = sc.Design(helices=helices_list, strands=[], grid=sc.Grid.square)
    design.set_helices_view_order(list(range(helices)))

    # Add strands and nick them
    for i in range(helices):
        strand = sc.Strand([sc.Domain(helix=i, start=0, end=total_length, forward=True)])
        design.add_strand(strand)
        design.add_nick(helix=i, offset=offset, forward=True)

    # Add loops if present
    for loop in loops:
        helix_start, helix_end, loop_length = loop
        design.add_loopout(helix_start - 1, helix_end - 1, loop_length)  # 1-based to 0-based

    # Add crossovers if present
    for helix1, helix2 in crossovers:
        try:
            # Ensure strands are present at the correct offset before adding crossovers
            strand1_exists = any(any(domain.helix == helix1 - 1 and domain.start <= offset < domain.end for domain in strand.domains) for strand in design.strands)
            strand2_exists = any(any(domain.helix == helix2 - 1 and domain.start <= offset < domain.end for domain in strand.domains) for strand in design.strands)

            if strand1_exists and strand2_exists:
                design.add_full_crossover(helix=helix1 - 1, helix2=helix2 - 1, offset=offset, forward=True)
            else:
                print(f"Cannot add crossover between helix {helix1} and {helix2}: Strands missing at offset.")
        except Exception as e:
            print(f"Error adding crossover between helix {helix1} and {helix2}: {e}")

    # Add sticky ends if present
    for helix1, helix2 in sticky_ends:
        try:
            # Ensure the sticky ends are on opposing directions
            sticky_end_helix1 = sc.Strand([sc.Domain(helix=helix1 - 1, start=total_length - 5, end=total_length, forward=True)])
            sticky_end_helix2 = sc.Strand([sc.Domain(helix=helix2 - 1, start=0, end=5, forward=False)])  # Opposing direction
            design.add_strand(sticky_end_helix1)
            design.add_strand(sticky_end_helix2)
        except Exception as e:
            print(f"Error adding sticky ends between helix {helix1} and {helix2}: {e}")

    # Save the design to a file
    output_directory = 'designs'
    os.makedirs(output_directory, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'dna_design_{helices}x{total_length}_{timestamp}.sc'
    design.write_scadnano_file(directory=output_directory, filename=filename)

    print(f"Design saved to {output_directory}/{filename}")
    return f"{output_directory}/{filename}"

# MAIN
if __name__ == "__main__":
    prompt = input("Describe your DNA structure:\n> ")
    output = react_design(prompt)

    if output:
        print(f"\nFinal design saved to {output}")
    else:
        print("\nDesign could not be saved due to errors.")
