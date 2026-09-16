import torch
import ttnn  # Import the Tenstorrent NN library
from diffusion_drive import DiffusionDrive  # Import the DiffusionDrive model

# Initialize the Tenstorrent device
device = ttnn.Device('wormhole')  # or 'blackhole' based on the hardware

# Load the DiffusionDrive model
model = DiffusionDrive()
model.load_state_dict(torch.load('path/to/diffusion_drive_weights.pth'))
model.to(device)

# Define the input tensor
input_tensor = torch.randn(1, 3, 224, 224).to(device)  # Example input size

# Run the model on the Tenstorrent device
with ttnn.Session(device) as session:
    output = session.run(model, input_tensor)

# Post-process the output
output = output.cpu().detach().numpy()

print("Inference result:", output)