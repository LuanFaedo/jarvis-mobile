# Teste de Geração de Áudio
import asyncio
import edge_tts

async def testar_tts():
    texto = "Olá mestre Patrick, minha voz está ajustada para vinte por cento a mais de velocidade."
    output = "tests/teste_voz.mp3"
    
    print(f"Gerando áudio com AntonioNeural e rate=+20%...")
    try:
        comm = edge_tts.Communicate(texto, "pt-BR-AntonioNeural", rate="+20%")
        await comm.save(output)
        print(f"Sucesso! Arquivo salvo em {output}")
    except Exception as e:
        print(f"Erro ao gerar áudio: {e}")

if __name__ == "__main__":
    asyncio.run(testar_tts())
