# Teste de Lógica de Streaming (Simulação Backend)
import time

def mock_llm_stream():
    # Simula chunks vindo da LLM
    chunks = [
        "Olá, ", "tudo ", "bem?", " Eu ", "sou ", "o ", "Jarvis. ",
        "Estou ", "aqui ", "para ", "ajudar ", "você ", "hoje.\n"
    ]
    for c in chunks:
        yield c
        time.sleep(0.01) # Simula delay de rede

def teste_quebra_sentencas():
    print("--- INICIANDO TESTE DE STREAMING ---")
    
    frase_buffer = ""
    delimitadores = tuple(['.', '?', '!', '\n'])
    
    stream = mock_llm_stream()
    sentenca_idx = 0
    
    for content in stream:
        frase_buffer += content
        
        # Lógica de detecção
        if frase_buffer.strip().endswith(delimitadores) and len(frase_buffer) > 2:
            sentenca_final = frase_buffer.strip()
            print(f"[EVENTO] stream_audio_chunk | ID: {sentenca_idx} | Texto: '{sentenca_final}'")
            sentenca_idx += 1
            frase_buffer = ""
            
    # Resto do buffer
    if frase_buffer.strip():
        print(f"[EVENTO] stream_audio_chunk | ID: {sentenca_idx} | Texto: '{frase_buffer}'")

if __name__ == "__main__":
    teste_quebra_sentencas()

