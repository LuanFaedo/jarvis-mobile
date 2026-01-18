# LOG DE AUDITORIA DE INPUTS DE VOZ (SQLite Local)
# Usa o módulo de banco de dados LOCAL (memoria.db_memoria)
try:
    from memoria.db_memoria import salvar_diario_voz as db_salvar_voz
except ImportError:
    # Fallback silencioso caso a função não exista no módulo de memória
    def db_salvar_voz(texto): pass

import re

def validar_coerencia(texto):
    """
    Analisa se o texto parece uma frase humana útil ou se é ruído de reconhecimento.
    Retorna True se for coerente.
    """
    if not texto: return False
    t = texto.strip()
    
    # 1. Tamanho Mínimo
    if len(t) < 4: 
        return False
    
    # 2. Contagem de Palavras
    palavras = t.split()
    if len(palavras) < 2:
        if len(t) > 8: return True 
        return False
        
    # 3. Verificação de Repetição
    texto_limpo = t.lower().replace(" ", "")
    if not texto_limpo: return False
    chars_unicos = len(set(texto_limpo))
    
    if len(texto_limpo) > 8 and chars_unicos < 4:
        return False
        
    if len(texto_limpo) <= 8 and chars_unicos < 3:
        return False

    return True

def registrar_input_usuario(texto):
    """Log simples de comandos executados"""
    gravar_diario_voz(texto)

def gravar_diario_voz(texto):
    """
    Grava apenas textos COERENTES no banco de dados LOCAL.
    """
    try:
        if validar_coerencia(texto):
            db_salvar_voz(texto)
    except Exception as e:
        print(f"[ERRO DIARIO DB LOCAL] Falha ao gravar voz: {e}")
