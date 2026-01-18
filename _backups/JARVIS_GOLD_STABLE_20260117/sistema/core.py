import subprocess
import os
import sys
import glob

class ManipuladorTotal:
    def __init__(self, base_dir):
        self.base_dir = os.path.abspath(base_dir)

    def executar_comando_terminal(self, comando):
        """Executa comandos shell (CMD/PowerShell) e retorna a saída."""
        print(f"[SISTEMA] Executando comando: {comando}")
        try:
            # Usa shell=True para permitir comandos complexos
            result = subprocess.run(comando, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            saida = f"--- SAÍDA ---\n{result.stdout}"
            if result.stderr:
                saida += f"\n--- ERROS ---\n{result.stderr}"
            return saida
        except Exception as e:
            return f"[ERRO CRÍTICO] Falha ao executar comando: {e}"

    def listar_arquivos(self, diretorio="."):
        """Lista arquivos do diretório relativo à base."""
        target_dir = os.path.join(self.base_dir, diretorio)
        try:
            if not os.path.exists(target_dir):
                return "Diretório não encontrado."
            
            items = os.listdir(target_dir)
            return "\n".join(items)
        except Exception as e:
            return f"Erro ao listar: {e}"

    def ler_arquivo(self, caminho):
        """Lê o conteúdo de um arquivo (código, config, log)."""
        target_path = os.path.join(self.base_dir, caminho)
        try:
            with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            return f"Erro ao ler arquivo: {e}"

    def escrever_arquivo(self, caminho, conteudo):
        """Cria ou sobrescreve um arquivo."""
        target_path = os.path.join(self.base_dir, caminho)
        print(f"[SISTEMA] Escrevendo em: {target_path}")
        try:
            # Garante que o diretório existe
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(conteudo)
            return f"Arquivo '{caminho}' salvo com sucesso."
        except Exception as e:
            return f"Erro ao escrever arquivo: {e}"

    def criar_pasta(self, caminho):
        target_path = os.path.join(self.base_dir, caminho)
        try:
            os.makedirs(target_path, exist_ok=True)
            return f"Pasta '{caminho}' criada/verificada."
        except Exception as e:
            return f"Erro ao criar pasta: {e}"

    def validar_script_python(self, caminho_script):
        """
        Tenta executar um script Python para validar se ele roda sem erros.
        Útil para auto-teste de código gerado.
        """
        target_path = os.path.join(self.base_dir, caminho_script)
        print(f"[VALIDAÇÃO] Testando script: {target_path}")
        
        try:
            # Executa o script isolado
            result = subprocess.run(
                [sys.executable, target_path], 
                capture_output=True, 
                text=True, 
                timeout=10 # Timeout de segurança para não travar
            )
            
            if result.returncode == 0:
                return {"sucesso": True, "msg": f"Script '{caminho_script}' passou no teste de execução!"}
            else:
                return {
                    "sucesso": False, 
                    "erro": f"Script falhou (Código {result.returncode}).\nSTDERR: {result.stderr}\nSTDOUT: {result.stdout}"
                }
        except subprocess.TimeoutExpired:
            return {"sucesso": False, "erro": "Script demorou demais para responder (Timeout). Loop infinito?"}
        except Exception as e:
            return {"sucesso": False, "erro": f"Erro crítico ao tentar validar: {e}"}

