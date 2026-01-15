# LOG DE AUDITORIA DE INPUTS DE VOZ (SQLite)
from memoria.db_memoria import salvar_diario_voz as db_salvar_voz
import re

def validar_coerencia(texto):
    """
    Analisa se o texto parece uma frase humana útil ou se é ruído de reconhecimento.
    Retorna True se for coerente.
    """
    if not texto: return False
    t = texto.strip()
    
    # 1. Tamanho Mínimo (Ignora 'Oi', 'Ah', 'Hum')
    if len(t) < 4: 
        return False
    
    # 2. Contagem de Palavras
    # Frases coerentes geralmente têm pelo menos 2 partes (Ex: "Ligar luz")
    # Palavras únicas soltas no reconhecimento contínuo são 90% das vezes erro/ruído.
    palavras = t.split()
    if len(palavras) < 2:
        # Exceção: Palavras longas específicas podem ser comandos (Ex: "Desligar")
        if len(t) > 8: return True 
        return False
        
    # 3. Verificação de Repetição (Anti-Surto do Reconhecimento)
    # Conta caracteres únicos REAIS (ignorando espaços)
    texto_limpo = t.lower().replace(" ", "")
    if not texto_limpo: return False
    
    chars_unicos = len(set(texto_limpo))
    
    # Se for longo (>10 chars) mas tiver pouca variedade (<4 unicos), é ruido (ex: aaaaaaaaaa)
    if len(texto_limpo) > 8 and chars_unicos < 4:
        return False
        
    # Se for curto/médio, mas tiver APENAS 1 ou 2 chars unicos, é ruido (ex: kkkk, t t t)
    if len(texto_limpo) <= 8 and chars_unicos < 3:
        # Exceção: "Ok", "Oi" (mas já filtramos tamanho < 4 antes)
        return False

    return True

def registrar_input_usuario(texto):
    """Log simples de comandos executados"""
    gravar_diario_voz(texto)

def gravar_diario_voz(texto):
    """
    Grava apenas textos COERENTES no banco de dados.
    """
    try:
        if validar_coerencia(texto):
            db_salvar_voz(texto)
            # print(f"[DIÁRIO] Gravado: {texto}") # Debug opcional
        else:
            # print(f"[DIÁRIO] Ignorado (Ruído): {texto}") # Debug opcional
            pass
    except Exception as e:
        print(f"[ERRO DIARIO DB] Falha ao gravar voz: {e}")