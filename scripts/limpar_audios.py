import os
import glob

def limpar_pasta_audios(pasta="audios", manter=10):
    if not os.path.exists(pasta):
        return
    
    # Lista arquivos mp3 ordenados por tempo de modificação
    arquivos = sorted(glob.glob(os.path.join(pasta, "*.mp3")), key=os.path.getmtime)
    
    if len(arquivos) > manter:
        para_apagar = arquivos[:-manter]
        for f in para_apagar:
            try:
                os.remove(f)
            except:
                pass

if __name__ == "__main__":
    limpar_pasta_audios()
