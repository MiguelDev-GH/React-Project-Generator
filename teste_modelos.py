import google.generativeai as genai

CHAVE_API = "AIzaSyAWI5dbjeBreNjY6MNypg2Orlz98hQbm4w"
genai.configure(api_key=CHAVE_API)

print(">>> Consultando modelos disponíveis para sua chave...")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Erro ao listar modelos: {e}")

print("\n>>> Fim da lista.")