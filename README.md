# Multimodal Vision-Language Model From Scratch (PyTorch)

This repository provides an implementation of a multimodal vision-language model built from scratch using PyTorch. The model is designed to handle both visual and textual inputs, enabling powerful interactions between images and language. The project includes a script for launching inference and requires a specific setup to get started.

## Installation

1. **Clone the Repository:**

   First, download this repository and save it to a folder on your local machine.

   ```bash
   git clone https://github.com/yourusername/your-repository.git
   cd your-repository

2. **Download the Model:**

   Download the model from Hugging Face by cloning the model repository:

   ```bash
   git clone https://huggingface.co/google/paligemma-3b-pt-224
   ```
   Save the cloned folder path for use in the next step.

3. **Update the Path:**

   Open the launch_inference.sh file and update the MODEL_PATH variable to point to the path of the downloaded model folder. For example:

   ```bash
   MODEL_PATH = "path/to/paligemma-3b-pt-224"

4. **Install Required Packages:**

   Install the required Python packages using the provided requirements.txt file:

   ```bash
   pip install -r requirements.txt


## Usage

1. **Prepare Your Image:**

   Place the image you want to use for inference in the images folder of the repository.

2. **Configure Inference:**

   Edit the launch_inference.sh file to specify the path of the image and the questions you want to ask about the image. Set the IMAGE_PATH and QUERY variables accordingly.

3. **Run Inference:**

   Execute the launch_inference.py script to start the inference process:

   ```bash
   ./launch_inference.sh
   ```

   This will run the model on the provided image and output the results based on the queries specified.



   
