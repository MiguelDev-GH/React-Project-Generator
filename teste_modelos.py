import google.generativeai as genai
import sys

AI_API_KEY = ""

try:
    with open('credentials.txt', 'r', encoding='utf-8') as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            
            try:
                if "> GOOGLE API KEY" in linha:
                    AI_API_KEY = linha.split('"')[1]
            except:
                pass
            
except FileNotFoundError:
    print("\n❌ CRITICAL ERROR: File 'credentials.txt' not found.")
    print("Please create it before running the factory.")
    sys.exit()

genai.configure(api_key=AI_API_KEY)

erros = []

if not AI_API_KEY:
    erros.append("- GOOGLE API KEY is missing or invalid.")
    
if erros:
    print("\n❌ CONFIGURATION ERROR:")
    for erro in erros:
        print(erro)
    print("\nCheck your 'credentials.txt' file formatting.")
    sys.exit()

print(">>> Consulting IA valid models...")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error to show models: {e}")

print("\n>>> End of list.")
