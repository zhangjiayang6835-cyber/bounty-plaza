import ttnn  # Assuming TTNN APIs are available
import torch
import time

# Load the SAM2 Hiera Tiny model
model = ttnn.load_model('facebook/sam2-hiera-tiny')

# Define the input size
input_size = (1024, 1024)

# Define the device (assuming Tenstorrent hardware)
device = 'tt:0'  # Replace with the appropriate device identifier

# Move the model to the device
model.to(device)

def preprocess_image(image):
    """Preprocess the input image for the model."""
    # Resize and normalize the image
    image = ttnn.resize_image(image, input_size)
    image = ttnn.normalize_image(image)
    return image

def encode_prompt(prompt_type, prompt_data):
    """Encode the prompt based on the type (point, box, or mask)."""
    if prompt_type == 'point':
        return ttnn.encode_point_prompt(prompt_data)
    elif prompt_type == 'box':
        return ttnn.encode_box_prompt(prompt_data)
    elif prompt_type =='mask':
        return ttnn.encode_mask_prompt(prompt_data)
    else:
        raise ValueError("Unsupported prompt type")

def run_inference(image, prompt_type, prompt_data):
    """Run the inference pipeline: image encoding, prompt encoding, and mask decoding."""
    # Preprocess the image
    preprocessed_image = preprocess_image(image)
    
    # Move the image to the device
    preprocessed_image = preprocessed_image.to(device)
    
    # Encode the prompt
    encoded_prompt = encode_prompt(prompt_type, prompt_data)
    
    # Move the prompt to the device
    encoded_prompt = encoded_prompt.to(device)
    
    # Run the model
    with torch.no_grad():
        start_time = time.time()
        output = model(preprocessed_image, encoded_prompt)
        end_time = time.time()
    
    # Measure latency
    latency = end_time - start_time
    
    return output, latency

def measure_performance(image, prompt_type, prompt_data, num_runs=100):
    """Measure the throughput and latency of the model."""
    latencies = []
    for _ in range(num_runs):
        _, latency = run_inference(image, prompt_type, prompt_data)
        latencies.append(latency)
    
    average_latency = sum(latencies) / len(latencies)
    throughput = num_runs / sum(latencies)
    
    print(f"Average Latency: {average_latency:.4f} seconds")
    print(f"Throughput: {throughput:.4f} inferences/second")

# Example usage
if __name__ == "__main__":
    # Load an example image
    image = ttnn.load_image('example_image.jpg')
    
    # Define the prompt (e.g., point prompt)
    prompt_type = 'point'
    prompt_data = [(500, 500)]  # Example point coordinates
    
    # Run the inference and measure performance
    measure_performance(image, prompt_type, prompt_data)