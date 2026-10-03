```python
from google.cloud import aiplatform
import os

def check_gemini_setup():
    os.environ["GOOGLE_CLOUD_PROJECT"] = "your_project_id"
    aiplatform.init(location="us-central1")
    models = aiplatform.list_models()
    print("Available models:", [model.display_name for model in models])
    print("Gemini is ready.")

check_gemini_setup()
```