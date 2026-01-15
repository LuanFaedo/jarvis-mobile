import os
import sys
import asyncio
import edge_tts
import speech_recognition as sr
from pydub import AudioSegment
import shutil
import time

def check_ffmpeg():
    print("\n--- 1. VERIFICANDO DEPENDÊNCIAS (FFMPEG) ---")
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"[OK] FFMPEG encontrado em: {ffmpeg_path}")
        return True
    else:
        print("[ERRO] FFMPEG NÃO ENCONTRADO no PATH do sistema.")
        print("       Sem ffmpeg, o sistema não consegue converter áudios do WhatsApp (OGG) para WAV.")
        return False

async def test_tts_generation():
    print("\n--- 2. TESTANDO GERAÇÃO DE ÁUDIO (TTS) ---")
    texto = "Teste de sistema Jarvis. Áudio gerado com sucesso."
    output_file = "test_audio_gen.mp3"
    
    try:
        communicate = edge_tts.Communicate(texto, "pt-BR-AntonioNeural")
        await communicate.save(output_file)
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"[OK] Áudio gerado: {output_file} ({os.path.getsize(output_file)} bytes)")
            return output_file
        else:
            print("[ERRO] Arquivo de áudio não foi criado ou está vazio.")
            return None
    except Exception as e:
        print(f"[ERRO CRÍTICO TTS] {e}")
        return None

def test_transcription(audio_file):
    print("\n--- 3. TESTANDO TRANSCRIÇÃO (STT) ---")
    if not audio_file:
        print("[PULAR] Sem arquivo de áudio para testar.")
        return

    wav_file = "test_audio_conv.wav"
    
    # 3.1 Conversão (Pydub)
    try:
        print(f"Tentando converter {audio_file} para WAV...")
        audio = AudioSegment.from_file(audio_file)
        audio.export(wav_file, format="wav")
        print(f"[OK] Conversão realizada: {wav_file}")
    except Exception as e:
        print(f"[ERRO CONVERSÃO] Falha ao usar Pydub/FFmpeg: {e}")
        return

    # 3.2 Reconhecimento (SpeechRecognition)
    try:
        r = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio_data = r.record(source)
            print("Enviando para Google Speech Recognition...")
            texto = r.recognize_google(audio_data, language="pt-BR")
            print(f"[OK] Texto reconhecido: '{texto}'")
    except sr.UnknownValueError:
        print("[ERRO] Google Speech Recognition não entendeu o áudio.")
    except sr.RequestError as e:
        print(f"[ERRO] Erro de conexão com Google Speech API: {e}")
    except Exception as e:
        print(f"[ERRO GERAL STT] {e}")
    
    # Limpeza
    if os.path.exists(wav_file): os.remove(wav_file)
    if os.path.exists(audio_file): os.remove(audio_file)

if __name__ == "__main__":
    check_ffmpeg()
    
    # Executa teste async de TTS
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    generated_file = loop.run_until_complete(test_tts_generation())
    loop.close()
    
    # Executa teste de Transcrição
    test_transcription(generated_file)
