import scadnano as sc
import re
import os
from datetime import datetime
from transformers import GPT2Tokenizer, GPT2LMHeadModel, pipeline

# Load model and tokenizer
tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
model = GPT2LMHeadModel.from_pretrained('gpt2')
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

#  extract parameters from the model output
def extract_parameters(model_output):
    print("Thought: Extracting parameters from model output...")

    # Number of helices
    helices_match = re.search(r"(\d+) helices", model_output)
    helices = int(helices_match.group(1)) if helices_match else None
    print(f"Thought: Extracted number of helices: {helices}")

    # Total length
    length_match = re.search(r"each (\d+) base pairs", model_output)
    base_pair_length = int(length_match.group(1)) if length_match else None
    total_length = helices * base_pair_length if helices and base_pair_length else None
    print(f"Thought: Extracted total length: {total_length}")

    # Loops
    loops = []
    loop_matches = re.findall(r"helixes (\d+) and (\d+) loop with (\d+) base pairs", model_output)
    for match in loop_matches:
        loops.append([int(match[0]), int(match[1]), int(match[2])])
    print(f"Thought: Extracted loops: {loops}")

    # Sticky ends
    sticky_ends = []
    sticky_end_matches = re.findall(r"Helix (\d+) should have a sticky end that connects to helix (\d+)", model_output)
    for match in sticky_end_matches:
        sticky_ends.append([int(match[0]), int(match[1])])
    print(f"Thought: Extracted sticky ends: {sticky_ends}")

    # Crossovers
    crossovers = []
    crossover_matches = re.findall(r"crossovers? between helices (\d+) and (\d+)", model_output)
    for match in crossover_matches:
        crossovers.append([int(match[0]), int(match[1])])
    print(f"Thought: Extracted crossovers: {crossovers}")

    return helices, total_length, loops, sticky_ends, crossovers

# ReAct function that integrates the design process
def react_design(prompt: str):
    print("Thought: Generating model output using LLM...")

    # Generate model output using LLM
    formatted_prompt = (
        f'Given this DNA design description: "{prompt}".\n'
        f'Extract the key parameters by reasoning step-by-step and return them in this format:\n'
        f'1. Number of helices: <int>\n'
        f'2. Total length: <int>\n'
        f'3. Loops: <list of loops, each defined as [helix_start, helix_end, loop_length]>\n'
        f'4. Sticky ends: <list of sticky ends, each defined as [helix1, helix2]>\n'
        f'5. Crossovers: <list of crossovers, each defined as [helix1, helix2]>\n'
        f'Answer in a numbered list format only, no explanations.'
    )

    model_output = generator(formatted_prompt, max_length=500, truncation=True)[0]["generated_text"]
    model_output = model_output.strip()
    print(f"Thought: Model output generated:\n{model_output}")

    # Extract parameters from model output
    helices, total_length, loops, sticky_ends, crossovers = extract_parameters(model_output)

    if helices is None or total_length is None:
        print("Error: Failed to extract necessary parameters.")
        return None

    offset = total_length // 2  # Middle of the strand
    print(f"Thought: Calculated offset: {offset}")

    # Initialize the design
    helices_list = [sc.Helix(max_offset=total_length) for _ in range(helices)]
    design = sc.Design(helices=helices_list, strands=[], grid=sc.Grid.square)
    design.set_helices_view_order(list(range(helices)))
    print("Thought: Initialized design with helices.")

    # Add strands and nick them
    for i in range(helices):
        strand = sc.Strand([sc.Domain(helix=i, start=0, end=total_length, forward=True)])
        design.add_strand(strand)
        design.add_nick(helix=i, offset=offset, forward=True)
        print(f"Thought: Added strand and nick to helix {i}.")

    # Add loops if present
    for loop in loops:
        helix_start, helix_end, loop_length = loop
        try:
            design.add_loopout(helix_start - 1, helix_end - 1, loop_length)  # 1-based to 0-based
            print(f"Thought: Added loop between helix {helix_start} and {helix_end} with length {loop_length}.")
        except Exception as e:
            print(f"Error adding loop between helix {helix_start} and {helix_end}: {e}")
            print("Thought: Re-evaluating loop placement...")

            # Try swapping helix_start and helix_end
            try:
                design.add_loopout(helix_end - 1, helix_start - 1, loop_length)
                print(f"Thought: Added loop after swapping helices {helix_end} and {helix_start}.")
            except Exception as e2:
                print(f"Error after swapping helices: {e2}")
                # If still fails, skip or log the error
                print(f"Thought: Skipping loop between helix {helix_start} and {helix_end}.")

    # Add crossovers if present
    for helix1, helix2 in crossovers:
        try:
            # Ensure strands are present at the correct offset before adding crossovers
            strand1_exists = any(any(domain.helix == helix1 - 1 and domain.start <= offset < domain.end for domain in strand.domains) for strand in design.strands)
            strand2_exists = any(any(domain.helix == helix2 - 1 and domain.start <= offset < domain.end for domain in strand.domains) for strand in design.strands)

            if strand1_exists and strand2_exists:
                design.add_full_crossover(helix=helix1 - 1, helix2=helix2 - 1, offset=offset, forward=True)
                print(f"Thought: Added crossover between helix {helix1} and {helix2}.")
            else:
                print(f"Thought: Cannot add crossover between helix {helix1} and {helix2}: Strands missing at offset.")
                print("Thought: Re-evaluating crossover placement...")

                # Try creating sticky ends with 4-base overhangs instead of 5
                try:
                    sticky_end_helix1 = sc.Strand([sc.Domain(helix=helix1 - 1, start=total_length - 4, end=total_length, forward=True)])
                    sticky_end_helix2 = sc.Strand([sc.Domain(helix=helix2 - 1, start=0, end=4, forward=False)])
                    design.add_strand(sticky_end_helix1)
                    design.add_strand(sticky_end_helix2)
                    print(f"Thought: Successfully added sticky ends with 4 base pairs between helix {helix1} and {helix2}.")
                except Exception as e2:
                    print(f"Error retrying sticky ends: {e2}")
                    print(f"Thought: Skipping sticky ends between helix {helix1} and {helix2}.")

        except Exception as e:
            print(f"Error adding crossover between helix {helix1} and {helix2}: {e}")

    # Add sticky ends if present
    for helix1, helix2 in sticky_ends:
        try:
            sticky_length = 5  # Start with 5 nt sticky ends
            success = False

            for length in range(sticky_length, 9):  # 5 to 8 nt
                try:
                    # Forward strand sticky end (helix1)
                    sticky_end_helix1 = sc.Strand([
                        sc.Domain(helix=helix1 - 1, start=total_length - length, end=total_length, forward=True)
                    ])
                    # Reverse strand sticky end (helix2)
                    sticky_end_helix2 = sc.Strand([
                        sc.Domain(helix=helix2 - 1, start=0, end=length, forward=False)
                    ])

                    # Try adding strands
                    design.add_strand(sticky_end_helix1)
                    design.add_strand(sticky_end_helix2)

                    print(f"Thought: Added sticky ends between helix {helix1} and {helix2} with {length} nt.")
                    success = True
                    break  # Exit loop if success
                except Exception as inner_e:
                    continue  # Try with longer sticky end

            if not success:
                print(f"Thought: Failed to add sticky end between helix {helix1} and {helix2} even after length adjustment.")
            
        except Exception as e:
            print(f"Error adding sticky ends between helix {helix1} and {helix2}: {e}")

    # Save the design to a file
    output_directory = 'designs'
    os.makedirs(output_directory, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'dna_design_{helices}x{total_length}_{timestamp}.sc'
    design.write_scadnano_file(directory=output_directory, filename=filename)

    print(f"Thought: Design saved to {output_directory}/{filename}")
    return f"{output_directory}/{filename}"

# MAIN
if __name__ == "__main__":
    prompt = input("Describe your DNA structure:\n> ")
    output = react_design(prompt)

    if output:
        print(f"\nFinal design saved to {output}")
    else:
        print("\nDesign could not be saved due to errors.")