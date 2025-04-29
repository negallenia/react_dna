In a couple days, I experimented with scadnano's Python API and the ReAct technique to generate DNA sequences, save them as scadnano files, and create a JSON database for AI model tuning and future use. Here’s a breakdown:
Version 1: Using Regex
Goal: I used regular expressions (regex) to interpret user prompts and generate DNA sequences.
Outcome: The sequences were saved as scadnano files locally. While it was a good start, I found that I could explore more advanced techniques for better flexibility and adaptability.


Version 2: Integrating with Zephyr-7b-Beta (LLM)
Goal: I shifted to using Zephyr-7b-beta (from Hugging Face) to process prompts more intelligently and generate more varied DNA sequences.
Outcome: This approach worked well, but I had to pause the experiment prematurely due to hitting my data limit with Hugging Face’s free tier. It was still insightful, showcasing the potential of large language models in improving DNA sequence generation. The picture you can see on top. This is what LLM parsed to scadnano.


Version 3: Local Fine-Tuning with FLAN 5 Small
Goal: For Version 3, I used the FLAN 5 Small model saved locally. Due to my laptop’s limited specs, I focused on fine-tuning with a simulated dataset, including noisy inputs (around 30% messy data).
Outcome: The fine-tuning is ongoing. While it’s still in progress, early results are promising, especially in improving the model’s robustness to messy data.


Key Learnings:
Refined my skills in fine-tuning AI models locally under hardware constraints.
Improved my data simulation skills, especially in handling noisy or messy user inputs.
