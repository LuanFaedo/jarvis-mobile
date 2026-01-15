# Teste de Formatação de Horário para TTS
from datetime import datetime, timezone, timedelta

def obter_horario_mock(hour, minute):
    return {
        "local": "Brasília",
        "horario": f"{hour:02d}:{minute:02d}",
        "completo": "completo_original_ignorado"
    }

def formatar_para_tts(info):
    try:
        h_str, m_str = info['horario'].split(':')
        h, m = int(h_str), int(m_str)
        
        lbl_h = "hora" if h == 1 else "horas"
        lbl_m = "minuto" if m == 1 else "minutos"
        
        msg_voz = f"{h} {lbl_h}"
        if m > 0:
            msg_voz += f" e {m} {lbl_m}"
        
        return f"Agora são {msg_voz} em {info['local']}."
    except Exception as e:
        return f"Erro: {e}"

# Casos de Teste
casos = [
    (18, 8),   # Caso do problema original (18:08)
    (1, 0),    # Hora cheia singular
    (2, 0),    # Hora cheia plural
    (12, 30),  # Meio dia e meia
    (0, 15),   # Meia noite e quinze
]

print("--- RESULTADOS DO TESTE DE FORMATAÇÃO TTS ---")
for h, m in casos:
    info = obter_horario_mock(h, m)
    resultado = formatar_para_tts(info)
    print(f"Entrada {h:02d}:{m:02d} -> Saída: '{resultado}'")
