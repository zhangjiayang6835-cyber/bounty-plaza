import ttnn  # Assuming TTNN API is available
import torch
import time

# Load the SAM2 model
def load_sam2_model():
    model = ttnn.load_model('facebook/sam2-hiera-tiny')
    return model

# Image Encoder
def image_encoder(model, image):
    return model.image_encoder(image)

# Prompt Encoder
def prompt_encoder(model, prompt):
    return model.prompt_encoder(prompt)

# Mask Decoder
def mask_decoder(model, image_embedding, prompt_embedding):
    return model.mask_decoder(image_embedding, prompt_embedding)

# Main function to run the SAM2 pipeline
def run_sam2_pipeline(image, prompt):
    model = load_sam2_model()

    # Encode the image
    start_time = time.time()
    image_embedding = image_encoder(model, image)
    image_encoding_time = time.time() - start_time

    # Encode the prompt
    start_time = time.time()
    prompt_embedding = prompt_encoder(model, prompt)
    prompt_encoding_time = time.time() - start_time

    # Decode the mask
    start_time = time.time()
    mask = mask_decoder(model, image_embedding, prompt_embedding)
    mask_decoding_time = time.time() - start_time

    # Print timing information
    print(f"Image Encoding Time: {image_encoding_time:.4f} seconds")
    print(f"Prompt Encoding Time: {prompt_encoding_time:.4f} seconds")
    print(f"Mask Decoding Time: {mask_decoding_time:.4f} seconds")

    return mask

if __name__ == "__main__":
    # Example usage
    image = torch.randn(1, 3, 1024, 1024)  # Example input image
    prompt = {'points': [(512, 512)], 'boxes': [torch.tensor([0, 0, 1024, 1024])],'masks': [torch.zeros(1, 1024, 1024)]}
    
    mask = run_sam2_pipeline(image, prompt)
    print("Mask:", mask)