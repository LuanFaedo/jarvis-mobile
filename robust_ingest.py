import json
import re
import os
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
import io

PDF_PATH = r"D:\\compartilhado\\Projetos\\jarvis01\\Jarviz01\\biblia\\nwt_T.pdf"
MEMORY_FILE = r"D:\\compartilhado\\Projetos\\jarvis01\\Jarviz01\\memoria\\memoria.json"

livros_biblia = [
    "Gênesis", "Êxodo", "Levítico", "Números", "Deuteronômio", "Josué", "Juízes", "Rute", 
    "1 Samuel", "2 Samuel", "1 Reis", "2 Reis", "1 Crônicas", "2 Crônicas", "Esdras", "Neemias", "Ester",
    "Jó", "Salmos", "Provérbios", "Eclesiastes", "Cântico de Salomão", "Isaías", "Jeremias", "Lamentações",
    "Ezequiel", "Daniel", "Oseias", "Joel", "Amós", "Obadias", "Jonas", "Miqueias", "Naum", "Habacuque",
    "Sofonias", "Ageu", "Zacarias", "Malaquias", "Mateus", "Marcos", "Lucas", "João", "Atos",
    "Romanos", "1 Coríntios", "2 Coríntios", "Gálatas", "Efésios", "Filipenses", "Colossenses",
    "1 Tessalonicenses", "2 Tessalonicenses", "1 Timóteo", "2 Timóteo", "Tito", "Filemom", "Hebreus",
    "Tiago", "1 Pedro", "2 Pedro", "1 João", "2 João", "3 João", "Judas", "Apocalipse"
]

def clean_text(text):
    text = text.replace('♂', '').replace('♀', '').replace('', '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extrair_versiculos(texto, livro_atual):
    """
    Extrai versículos do texto usando padrões como:
    - '1 Texto do versículo' 
    - '2 Mais texto'
    Retorna lista de dicionários com capítulo, versículo e texto
    """
    versiculos = []
    
    # Padrão para detectar início de capítulo (número grande sozinho ou palavra "CAPÍTULO")
    capitulo_pattern = r'(?:CAPÍTULO|CAP\.?)\s*(\d+)|^(\d+)\s*$'
    
    # Padrão para versículos: número no início seguido de texto
    versiculo_pattern = r'^\s*(\d+)\s+([^0-9].*?)(?=^\s*\d+\s+|\Z)'
    
    capitulo_atual = 1
    linhas = texto.split('\n')
    
    i = 0
    while i < len(linhas):
        linha = linhas[i].strip()
        
        # Detecta novo capítulo
        match_cap = re.search(capitulo_pattern, linha, re.MULTILINE)
        if match_cap:
            capitulo_atual = int(match_cap.group(1) or match_cap.group(2))
            i += 1
            continue
        
        # Detecta versículo
        match_vers = re.match(r'^(\d+)\s+(.+)', linha)
        if match_vers:
            num_versiculo = int(match_vers.group(1))
            texto_versiculo = match_vers.group(2)
            
            # Continua lendo linhas até encontrar próximo versículo
            i += 1
            while i < len(linhas):
                proxima = linhas[i].strip()
                if re.match(r'^\d+\s+', proxima):
                    break
                texto_versiculo += ' ' + proxima
                i += 1
            
            versiculos.append({
                'livro': livro_atual,
                'capitulo': capitulo_atual,
                'versiculo': num_versiculo,
                'texto': clean_text(texto_versiculo)
            })
            continue
        
        i += 1
    
    return versiculos

def agrupar_versiculos_por_capitulo(versiculos):
    """Agrupa versículos por capítulo para facilitar busca"""
    capitulos = {}
    
    for v in versiculos:
        chave = f"{v['livro']}|{v['capitulo']}"
        if chave not in capitulos:
            capitulos[chave] = []
        capitulos[chave].append(v)
    
    return capitulos

def salvar_progresso(dados):
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(">> Progresso salvo no disco.")
    except Exception as e:
        print(f"Erro ao salvar: {e}")

def process():
    print("Iniciando extração ESTRUTURADA da Bíblia...")
    
    # Preserva dados não-bíblicos existentes
    dados_existentes = []
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            dados_existentes = [x for x in raw if "Bíblia" not in x.get('source', '')]
            print(f"Preservados {len(dados_existentes)} itens existentes.")
        except:
            print("Arquivo de memória vazio ou inválido.")

    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    
    current_book = "Gênesis"
    page_count = 0
    
    # Armazena TODOS os versículos extraídos
    todos_versiculos = []
    
    # Buffer de texto por livro
    buffer_livro = ""
    
    try:
        with open(PDF_PATH, 'rb') as fp:
            pages = list(PDFPage.get_pages(fp))
            total_pages = len(pages)
            print(f"Total de páginas: {total_pages}")
            
            for i, page in enumerate(pages):
                retstr = io.StringIO()
                device = TextConverter(rsrcmgr, retstr, laparams=laparams)
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                interpreter.process_page(page)
                
                raw_text = retstr.getvalue()
                retstr.close()
                
                # Detecta mudança de livro
                upper_text = raw_text[:400].upper()
                livro_anterior = current_book
                
                for livro in livros_biblia:
                    if livro.upper() in upper_text:
                        # Se mudou de livro, processa o buffer anterior
                        if livro != current_book and buffer_livro:
                            print(f"Processando {current_book}...")
                            versiculos = extrair_versiculos(buffer_livro, current_book)
                            todos_versiculos.extend(versiculos)
                            buffer_livro = ""
                        
                        current_book = livro
                        break
                
                # Adiciona texto ao buffer do livro atual
                buffer_livro += "\n" + clean_text(raw_text)
                
                page_count += 1
                
                if page_count % 50 == 0:
                    print(f"Página {page_count}/{total_pages} - Livro: {current_book}")

            # Processa último livro
            if buffer_livro:
                print(f"Processando {current_book} (final)...")
                versiculos = extrair_versiculos(buffer_livro, current_book)
                todos_versiculos.extend(versiculos)

            print(f"\n✓ Total de versículos extraídos: {len(todos_versiculos)}")
            
            # Cria entradas estruturadas na memória
            novos_dados_biblia = []
            
            # Agrupa por capítulo para otimizar busca
            capitulos = agrupar_versiculos_por_capitulo(todos_versiculos)
            
            for chave, versiculos_cap in capitulos.items():
                livro, capitulo = chave.split('|')
                
                # Cria um registro por capítulo com todos os versículos
                texto_completo = ""
                for v in versiculos_cap:
                    texto_completo += f"{v['versiculo']} {v['texto']} "
                
                novos_dados_biblia.append({
                    "source": f"Bíblia - {livro} {capitulo}",
                    "livro": livro,
                    "capitulo": int(capitulo),
                    "content": texto_completo.strip(),
                    "tipo": "capitulo_completo"
                })
                
                # TAMBÉM cria registros individuais por versículo para busca precisa
                for v in versiculos_cap:
                    novos_dados_biblia.append({
                        "source": f"Bíblia - {v['livro']} {v['capitulo']}:{v['versiculo']}",
                        "livro": v['livro'],
                        "capitulo": v['capitulo'],
                        "versiculo": v['versiculo'],
                        "content": v['texto'],
                        "tipo": "versiculo_individual"
                    })

            # Salva tudo
            salvar_progresso(dados_existentes + novos_dados_biblia)
            print(f"\n✓ Ingestão completa! {len(novos_dados_biblia)} registros salvos.")
            print(f"✓ Total no arquivo: {len(dados_existentes) + len(novos_dados_biblia)} registros")

    except Exception as e:
        print(f"Erro durante ingestão: {e}")
        import traceback
        traceback.print_exc()

def buscar_versiculo(livro, capitulo, versiculo):
    """Função auxiliar para testar busca de versículos específicos"""
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Busca exata
        for item in dados:
            if (item.get('livro') == livro and 
                item.get('capitulo') == capitulo and 
                item.get('versiculo') == versiculo):
                return item['content']
        
        return "Versículo não encontrado"
    except:
        return "Erro ao buscar"

if __name__ == "__main__":
    process()
    
    # Testes de busca
    print("\n--- TESTES DE BUSCA ---")
    print(f"Salmos 83:18 → {buscar_versiculo('Salmos', 83, 18)}")
    print(f"2 Timóteo 3:16 → {buscar_versiculo('2 Timóteo', 3, 16)}")