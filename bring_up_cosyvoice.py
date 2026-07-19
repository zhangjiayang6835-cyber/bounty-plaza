import ttnn_api
from cosyvoice import CosyVoice

def main():
    # Initialize the TTNN API
    tt_api = ttnn_api.TTNNAPI()

    # Load the CosyVoice model
    model = CosyVoice(model_path="path/to/cosyvoice/model")

    # Prepare input data (example)
    input_data = "Hello, how are you?"

    # Run inference on the Tenstorrent hardware
    output = tt_api.run_inference(model, input_data)

    # Print the output
    print("Output:", output)

if __name__ == "__main__":
    main()
