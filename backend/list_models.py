from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

models = client.models.list()
sorted_models = sorted(models, key=lambda m: m.id)

print(f"Your API key has access to {len(sorted_models)} models:\n")

for model in sorted_models:
    print(f"  {model.id:<40} owned by: {model.owned_by}")
