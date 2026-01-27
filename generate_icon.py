from PIL import Image, ImageDraw, ImageFilter
import os

def create_jarvis_icon():
    size = (1024, 1024)
    # Fundo Preto
    img = Image.new('RGBA', size, (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    
    center = (512, 512)
    
    # 1. Glow Externo (Azul Ciano)
    for i in range(40):
        radius = 450 - i * 2
        opacity = int(5 + i * 2)
        draw.ellipse([center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius], 
                     outline=(0, 255, 255, opacity), width=4)

    # 2. Anel Principal (Reator)
    draw.ellipse([100, 100, 924, 924], outline=(0, 255, 255, 255), width=30)
    
    # 3. Núcleo Brilhante
    draw.ellipse([350, 350, 674, 674], fill=(0, 255, 255, 50), outline=(255, 255, 255, 200), width=10)
    
    # 4. Triângulo Central (Estilo Ark antigo)
    draw.polygon([(512, 380), (380, 650), (644, 650)], outline=(0, 255, 255, 255), width=15)

    # Salvar
    if not os.path.exists("jarvis_flutter/assets"):
        os.makedirs("jarvis_flutter/assets")
    
    img.save("jarvis_flutter/assets/icon.png")
    print("Ícone gerado em jarvis_flutter/assets/icon.png")

if __name__ == "__main__":
    create_jarvis_icon()
