import os
import subprocess
import time
import random
import re
import sys
import shutil
import json
import signal

# Tenta importar ollama
try:
    import ollama
except ImportError:
    ollama = None

# --- CONFIG ---
PROJECT_PATH = os.path.join(os.getcwd(), "base-app")
USE_DATABASE = False 
LOCAL_MODEL = "llama3.2"

# --- CORE AI FUNCTION (LOCAL LLAMA) ---
def call_local_ai(system_prompt, user_prompt, json_mode=False):
    if not ollama:
        return "// Error: 'ollama' library not installed."

    try:
        fmt = 'json' if json_mode else ''
        
        response = ollama.chat(model=LOCAL_MODEL, messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ], format=fmt)
        
        return response['message']['content']
    except Exception as e:
        return f"// Local Llama Error: {str(e)}"

# --- UTILS (Mesmos do fabrica original) ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def clean_input(text):
    sys.stdout.flush()
    return input(text).strip()

def kill_process(process):
    try:
        if os.name == 'nt':
            subprocess.run(f"taskkill /F /T /PID {process.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except: pass

def reset_project():
    print(">>> [🧹] FACTORY RESET: Cleaning old files...")
    src_path = os.path.join(PROJECT_PATH, "src")
    if not os.path.exists(src_path): return
    
    folders_to_remove = ["components", "lib", "utils", "hooks", "pages", "context"]
    
    for item in os.listdir(src_path):
        item_path = os.path.join(src_path, item)
        if os.path.isdir(item_path) and item in folders_to_remove:
            try: shutil.rmtree(item_path)
            except: pass
        elif os.path.isfile(item_path):
            if item not in ["main.jsx", "index.css", "vite-env.d.ts", "App.css"]:
                if item == "App.jsx":
                    with open(item_path, "w", encoding="utf-8") as f:
                        f.write("export default function App() { return <div>Loading...</div> }")
                else:
                    os.remove(item_path)
    print("✅ Project Cleaned.")

# --- PROMPTS ---
def get_db_instructions():
    if USE_DATABASE:
        return """
    💾 STORAGE: SUPABASE ENABLED.
    - Assume keys are in .env (do not hardcode).
    - Use @supabase/supabase-js.
        """
    else:
        return """
    💾 STORAGE MODE: [NO DATABASE]
    🛑 STRICT PROHIBITION: DO NOT import supabase.
    ✅ REQUIREMENT: Use HARDCODED Arrays of Objects (Mock Data) inside components.
        """

def plan_architecture(user_prompt):
    print("\n>>> [1/3] 🧠 LOCAL ARCHITECT: Blueprinting...")
    
    if USE_DATABASE:
        extra_rule = '5. Use "src/lib/supabase.js" for DB connection.'
    else:
        extra_rule = '5. 🛑 FORBIDDEN: Do NOT include "src/lib/supabase.js".'

    system = "You are a Senior React Architect. Output only JSON."
    user = f"""
    TASK: List files to build this app: "{user_prompt}".
    
    RULES:
    1. Output strictly a JSON Array of strings.
    2. Max 5 files (Llama 3 works better with smaller scopes).
    3. NEVER include "src/main.jsx", "index.html".
    4. INCLUDE "src/App.jsx".
    {extra_rule}
    
    JSON RESPONSE FORMAT:
    ["src/App.jsx", "src/components/Example.jsx"]
    """
    
    try:
        resp_text = call_local_ai(system, user, json_mode=True)
        try:
            file_list = json.loads(resp_text)
            # Llama as vezes devolve um objeto { "files": [...] }, tratamos isso:
            if isinstance(file_list, dict):
                file_list = list(file_list.values())[0]
        except:
            match_json = re.search(r'\[.*\]', resp_text, re.DOTALL)
            file_list = json.loads(match_json.group(0)) if match_json else []

        forbidden = ["src/main.jsx", "src/main.js", "index.html", "src/index.css", "vite.config.js"]
        if not USE_DATABASE: forbidden.append("src/lib/supabase.js")

        filtered_list = [f for f in file_list if f not in forbidden]
        if "src/App.jsx" not in filtered_list: filtered_list.append("src/App.jsx")
        return filtered_list

    except Exception as e:
        print(f"⚠️ Architect Error: {e}. Fallback to basic.")
        return ["src/App.jsx"]

def plan_modification(user_request, existing_files):
    print("\n>>> [🔍] LOCAL AGENT: Analyzing impact...")
    
    system = "You are a Code Maintenance Expert. Output only JSON."
    user = f"""
    TASK: Identify WHICH files need to be edited for: "{user_request}".
    EXISTING FILES: {json.dumps(existing_files)}
    RULES: Return ONLY a JSON Array of strings.
    """
    
    try:
        resp_text = call_local_ai(system, user, json_mode=True)
        try:
            data = json.loads(resp_text)
            if isinstance(data, dict): return list(data.values())[0]
            return data
        except:
            match_json = re.search(r'\[.*\]', resp_text, re.DOTALL)
            return json.loads(match_json.group(0)) if match_json else []
    except:
        return ["src/App.jsx"]

def generate_file(target_file, global_context, user_prompt, is_modification=False):
    action = "MODIFYING" if is_modification else "BUILDER"
    print(f">>> [2/3] 👷 {action} (Local): {target_file}...")
    
    project_summary = ""
    for path, code in global_context.items():
        project_summary += f"\n--- FILE: {path} ---\n{code[:600]}...\n"

    if is_modification:
        old_code = global_context.get(target_file, "// New File")
        task_desc = f"""
        TASK: EDIT '{target_file}' based on request: "{user_prompt}".
        OLD CODE: {old_code}
        INSTRUCTION: Keep layout, change only what is asked.
        """
    else:
        task_desc = f"""
        TASK: Write code for '{target_file}'.
        GOAL: "{user_prompt}"
        OTHER FILES: {project_summary}
        """

    system = "You are a React Expert. Output ONLY raw code. No markdown."
    user = f"""
    {task_desc}
    
    CONTEXT:
    - {get_db_instructions()}
    
    RULES:
    1. Use 'lucide-react' for icons.
    2. For 'src/App.jsx': MUST use `export default function App() {{ ... }}`.
    3. Do NOT use markdown code blocks. Just the code.
    """
    
    for attempt in range(2):
        try:
            resp_text = call_local_ai(system, user, json_mode=False)
            code = resp_text.replace("```jsx", "").replace("```javascript", "").replace("```js", "").replace("```", "")
            return code.strip()
        except Exception as e:
            print(f"⚠️ Error on attempt {attempt+1}: {e}")
            time.sleep(1)
            
    return f"// LOCAL ERROR: {str(e)}"

def save_file(rel_path, code):
    clean_path = rel_path.replace("base-app/", "").replace("./", "").replace("\\", "/")
    while "src/src/" in clean_path: clean_path = clean_path.replace("src/src/", "src/")
    if not clean_path.startswith("src/"): clean_path = f"src/{clean_path}"

    full_path = os.path.join(PROJECT_PATH, clean_path)
    folder = os.path.dirname(full_path)
    if not os.path.exists(folder): os.makedirs(folder)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(code)

def check_dependencies(global_context):
    print("\n>>> [3/3] 📦 DEPENDENCIES...")
    required_libs = ['react', 'react-dom', 'vite', '@vitejs/plugin-react', 'tailwindcss', 'postcss', 'autoprefixer', 'lucide-react']
    blacklist = ['react-context', 'fs', 'path', 'os']

    total_text = "".join(global_context.values())
    imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", total_text)
    
    to_install = []
    for lib in imports:
        if lib.startswith(".") or lib.startswith("/"): continue
        parts = lib.split("/")
        root_lib = f"{parts[0]}/{parts[1]}" if lib.startswith("@") and len(parts) > 1 else parts[0]
            
        if root_lib not in required_libs and root_lib not in blacklist:
            to_install.append(root_lib)
            
    if to_install:
        to_install = list(set(to_install))
        print(f"Installing: {to_install}")
        subprocess.run(f"npm install {' '.join(to_install)}", cwd=PROJECT_PATH, shell=True, stdout=subprocess.DEVNULL)

def check_http_domain(slug):
    domain = f"http://{slug}.surge.sh"
    try:
        req = urllib.request.Request(domain, method='HEAD')
        urllib.request.urlopen(req)
        return True 
    except: return False

def deploy_project(initial_name):
    print("\n>>> [BUILDING]...")
    subprocess.run("npm run build", cwd=PROJECT_PATH, shell=True, stdout=subprocess.DEVNULL)
    
    current_name = initial_name.replace(" ", "-").lower()
    while check_http_domain(current_name):
        current_name += f"-{random.randint(1,99)}"
    
    subprocess.run(f"npx surge ./dist --domain {current_name}.surge.sh", cwd=PROJECT_PATH, shell=True, stdout=subprocess.DEVNULL)
    return f"{current_name}.surge.sh"

# --- ENTRY POINT ---
def iniciar_sistema_local():
    global USE_DATABASE
    
    if not ollama:
        print("❌ Error: 'ollama' library missing. Run: pip install ollama")
        return

    clear_screen()
    print(f"-=[ 🏭 FACTORY LOCAL (Llama 3) ]=-")
    print(f"🧠 Engine: OLLAMA LOCAL | Model: {LOCAL_MODEL}")
    
    # Verifica se o Ollama está rodando
    try:
        ollama.list()
    except:
        print("❌ Error: Could not connect to Ollama.")
        print("👉 Make sure Ollama app is running on your PC.")
        sys.exit()

    while True:
        print("🔌 Enable Database (Supabase)? (y/n)")
        choice = clean_input(">>> ").lower()
        if choice == 'y':
            USE_DATABASE = True # No modo local, assume-se que o user configure o .env depois ou hardcode
            print("⚠️  Local Mode: Ensure you configure Supabase keys in your code manually.")
            break
        elif choice == 'n':
            USE_DATABASE = False
            break

    while True:
        initial_prompt = clean_input("\n📝 App Idea (or 'exit'): ")
        if initial_prompt.lower() == 'exit': break
        
        reset_project()

        files_to_create = plan_architecture(initial_prompt)
        print(f"📋 Plan: {files_to_create}")
        
        project_context = {}
        for file in files_to_create:
            code = generate_file(file, project_context, initial_prompt)
            project_context[file] = code
            save_file(file, code)
            
        check_dependencies(project_context)
        
        preview_process = None
        
        while True:
            if preview_process: kill_process(preview_process)
            
            print("\n✨ App Ready. Opening Preview...")
            print("👉 http://localhost:5173")
            preview_process = subprocess.Popen("npm run dev -- --open", cwd=PROJECT_PATH, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            
            print("\n" + "="*30)
            print(" [1] ✏️  MODIFY")
            print(" [2] 🚀 PUBLISH")
            print(" [3] 🔙 NEW PROJECT")
            print(" [4] ❌ EXIT")
            print("="*30)
            
            option = clean_input(">>> ")
            
            if option == "1":
                change_request = clean_input("\n✏️  Change Request: ")
                files_to_edit = plan_modification(change_request, files_to_create)
                print(f"🎯 Files to Edit: {files_to_edit}")
                
                for f in files_to_edit:
                    if f not in files_to_create: files_to_create.append(f)
                
                for file in files_to_edit:
                    new_code = generate_file(file, project_context, change_request, is_modification=True)
                    project_context[file] = new_code
                    save_file(file, new_code)
                
                print("✅ Done! Reloading...")
                
            elif option == "2":
                kill_process(preview_process)
                link = deploy_project(initial_prompt[:15])
                print(f"\n🚀 LIVE: https://{link}\n")
                input("Press ENTER...")
                break
            elif option == "3":
                kill_process(preview_process)
                break
            elif option == "4":
                kill_process(preview_process)
                sys.exit()