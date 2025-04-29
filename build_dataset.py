import os
import json
import scadnano as sc

def build_dataset_from_scadnano_files(folder_path):
    dataset = []

    # Iterate over all files in the folder (designs)
    for filename in os.listdir(folder_path):
        if filename.endswith(".sc"):  # Process only .sc files
            file_path = os.path.join(folder_path, filename)
            
            # Read files
            try:
                design = sc.Design.from_scadnano_file(file_path)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue  

            # Extract relevant information
            design_data = []
            for strand in design.strands:
                design_data.append({
                    "helix_index": strand.domains[0].helix,  
                    "strand_name": strand.name if hasattr(strand, 'name') else None,
                    "strand_length": sum(domain.end - domain.start for domain in strand.domains),
                    "direction": 'forward' if strand.domains[0].forward else 'reverse'
                })

            # Create the "prompt" and "target" for fine-tuning
            prompt = f"Generate DNA design with {len(design.strands)} strands, each with properties: {design_data}"
            target = json.dumps({
                "design_data": design_data
            })

            # Prepare the final data structure
            data = {
                "input": prompt,  # "input" field for the prompt
                "target": target  # "target" field for the expected output
            }

            dataset.append(data)

    # Save the dataset to a JSONL
    with open("react_dna_dataset.jsonl", "a") as f:
        for data in dataset:
            f.write(json.dumps(data) + "\n")

    print("📁 Data appended to react_dna_dataset.jsonl")

if __name__ == "__main__":
    folder_path = "designs" 
    build_dataset_from_scadnano_files(folder_path)
