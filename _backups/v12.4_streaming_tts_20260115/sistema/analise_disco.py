import os
import heapq

def get_largest_files(drive_path="C:\\", top_n=10):
    print(f"Iniciando varredura rápida em {drive_path} (Top {top_n} arquivos)...")
    print("Isso pode levar alguns segundos dependendo do tamanho do disco.")
    
    largest_files = []
    
    # Pastas para ignorar e acelerar o processo
    IGNORE_DIRS = {'Windows', 'Program Files', 'Program Files (x86)', 'AppData', '$Recycle.Bin', 'System Volume Information'}
    
    scanned_count = 0
    errors = 0
    
    for root, dirs, files in os.walk(drive_path, topdown=True):
        # Modifica dirs in-place para pular pastas de sistema pesadas/protegidas se estivermos na raiz
        if root == drive_path:
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
        for name in files:
            try:
                filepath = os.path.join(root, name)
                # Pega tamanho sem seguir links simbólicos
                size = os.path.getsize(filepath)
                
                # Mantém apenas os top N na heap (lista de prioridade)
                if len(largest_files) < top_n:
                    heapq.heappush(largest_files, (size, filepath))
                else:
                    heapq.heappushpop(largest_files, (size, filepath))
                
                scanned_count += 1
                if scanned_count % 50000 == 0:
                    print(f"Varridos {scanned_count} arquivos...", end='\r')
                    
            except (OSError, PermissionError):
                errors += 1
                continue
    
    print(f"\nVarredura concluída. {scanned_count} arquivos analisados. {errors} acessos negados (ignorado sistema).")
    
    # Ordena do maior para o menor
    largest_files.sort(key=lambda x: x[0], reverse=True)
    
    print("\n=== MAIORES ARQUIVOS ENCONTRADOS ===")
    for size, path in largest_files:
        size_mb = size / (1024 * 1024)
        if size_mb > 1024:
            print(f"{size_mb/1024:.2f} GB - {path}")
        else:
            print(f"{size_mb:.2f} MB - {path}")

if __name__ == "__main__":
    import sys
    drive = sys.argv[1] if len(sys.argv) > 1 else "C:\\"
    get_largest_files(drive)
