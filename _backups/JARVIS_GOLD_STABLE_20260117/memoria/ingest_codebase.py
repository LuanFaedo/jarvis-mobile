import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(BASE_DIR, "memoria", "memoria.json")

IGNORE_DIRS = {
    'node_modules', '__pycache__', '.git', '.wwebjs_auth', '.wwebjs_cache', 'venv', 'env', '.claude', 'audios'
}
EXTENSIONS = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.html': 'HTML',
    '.css': 'CSS',
    '.json': 'JSON',
    '.md': 'Markdown',
    '.bat': 'Batch'
}

def scan_project():
    project_context = "=== CONTEXTO DO PROJETO ATUAL (CÓDIGO FONTE) ===\n\n" 
    
    for root, dirs, files in os.walk(BASE_DIR):
        # Filter directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in EXTENSIONS:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, BASE_DIR)
                
                # Skip memory file itself and large known files to avoid recursion/bloat
                if file == "memoria.json" or "package-lock.json" in file:
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    project_context += f"--- ARQUIVO: {rel_path} ({EXTENSIONS[ext]}) ---\n"
                    project_context += content + "\n\n"
                    print(f"Lido: {rel_path}")
                except Exception as e:
                    print(f"Erro ao ler {rel_path}: {e}")

    return project_context

def update_memory(new_context):
    memory = []
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                memory = json.load(f)
        except:
            memory = []
            
    # Find system message
    system_msg_idx = -1
    for i, msg in enumerate(memory):
        if msg.get('role') == 'system':
            system_msg_idx = i
            break
            
    if system_msg_idx != -1:
        # Update existing system message
        current_content = memory[system_msg_idx]['content']
        # Check if project context is already there to avoid duplication (simple check)
        if "=== CONTEXTO DO PROJETO ATUAL" in current_content:
            # Replace old project context
            parts = current_content.split("=== CONTEXTO DO PROJETO ATUAL")
            # Keep the part before the project context (which might be the robust scan)
            base_content = parts[0]
            memory[system_msg_idx]['content'] = base_content + "\n" + new_context
        else:
            # Append
            memory[system_msg_idx]['content'] = current_content + "\n\n" + new_context
    else:
        # Create new system message
        memory.insert(0, {
            "role": "system", 
            "content": f"SISTEMA OPERACIONAL JARVIS.\n\n{new_context}"
        })
        
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
        
    print(f"Memória atualizada em: {MEMORY_FILE}")

if __name__ == "__main__":
    print("Iniciando ingestão do código fonte do projeto...")
    context = scan_project()
    update_memory(context)
