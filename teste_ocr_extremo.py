import time
import os
from PIL import Image, ImageOps
import pytesseract

# Aponta caminhos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_DIR, "memoria", "IMG-20260105-WA0007.jpg")
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
DATA_DIR = r"C:\WORD" # O Tesseract vai procurar 'tessdata' aqui dentro

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
os.environ['OMP_THREAD_LIMIT'] = '1'
# Configura TESSDATA_PREFIX globalmente para garantir
os.environ['TESSDATA_PREFIX'] = r"C:\WORD\tessdata" 

def benchmark():
    if not os.path.exists(IMG_PATH):
        print(f"ERRO: Imagem {IMG_PATH} não encontrada.")
        return

    print(f"--- INICIANDO BENCHMARK DE OCR ---")
    print(f"Imagem Alvo: {IMG_PATH}")
    
    # 1. Análise da Imagem
    try:
        img = Image.open(IMG_PATH)
        print(f"Dimensoes Originais: {img.size}")
        print(f"Formato: {img.format}")
    except Exception as e:
        print(f"ERRO CRITICO AO ABRIR IMAGEM: {e}")
        return

    # --- TESTE 1: Padrão (Baseline) ---
    print("\n[TESTE 1] Tesseract Puro (Sem configs)...")
    start = time.time()
    try:
        # Usa apenas ingles padrão se tiver, ou falha
        txt = pytesseract.image_to_string(img)
        print(f"Tempo: {time.time() - start:.4f}s | Caracteres lidos: {len(txt)}")
    except Exception as e:
        print(f"Erro Teste 1 (Provavelmente falta eng.traineddata): {e}")

    # --- TESTE 2: Config Atual (Fast + Grayscale) ---
    print("\n[TESTE 2] Otimizado (Fast Model + Grayscale)...")
    start = time.time()
    try:
        img_gray = ImageOps.grayscale(img)
        # REMOVIDO --tessdata-dir para confiar no ENV VAR
        config_fast = f'--oem 1 --psm 3'
        txt = pytesseract.image_to_string(img_gray, lang='por', config=config_fast)
        print(f"Tempo: {time.time() - start:.4f}s | Caracteres lidos: {len(txt)}")
    except Exception as e:
        print(f"Erro Teste 2: {e}")

    # --- TESTE 3: Turbo Bruto (Resize 1024px + PSM 6) ---
    print("\n[TESTE 3] Turbo (Resize 1024px + PSM 6 - Bloco único)...")
    start = time.time()
    try:
        if img.width > 1024:
            ratio = 1024 / float(img.width)
            new_h = int(img.height * ratio)
            img_small = img.resize((1024, new_h), Image.NEAREST)
        else:
            img_small = img
        
        img_small = ImageOps.grayscale(img_small)
        
        config_turbo = f'--oem 1 --psm 6'
        txt = pytesseract.image_to_string(img_small, lang='por', config=config_turbo)
        print(f"Tempo: {time.time() - start:.4f}s | Caracteres lidos: {len(txt)}")
    except Exception as e:
        print(f"Erro Teste 3: {e}")

if __name__ == "__main__":
    benchmark()
