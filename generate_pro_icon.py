from PIL import Image, ImageDraw, ImageFilter
import math

def create_pro_icon():
    size = (1024, 1024)
    # Fundo Preto Profundo
    img = Image.new('RGBA', size, (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    
    center = (512, 512)
    
    # 1. Glow de Fundo (Aura Azulada)
    # Desenhamos vários círculos com alpha baixo para fazer um gradiente
    for r in range(500, 200, -10):
        alpha = int(max(0, (500-r)/500 * 50))
        draw.ellipse([center[0]-r, center[1]-r, center[0]+r, center[1]+r], 
                     outline=(0, 255, 255, alpha), width=5)

    # 2. Anel Externo Segmentado (HUD Tech)
    # Arco 1
    draw.arc([100, 100, 924, 924], start=30, end=150, fill=(0, 255, 255, 255), width=40)
    # Arco 2
    draw.arc([100, 100, 924, 924], start=210, end=330, fill=(0, 255, 255, 255), width=40)
    
    # 3. Anel Médio Fino
    draw.ellipse([200, 200, 824, 824], outline=(0, 200, 200, 200), width=10)
    
    # 4. Núcleo Central (A Pupila do Jarvis)
    # Círculo Sólido com brilho
    draw.ellipse([350, 350, 674, 674], fill=(0, 255, 255, 255), outline=(255, 255, 255, 255), width=5)
    
    # 5. Detalhes Internos do Núcleo (Hexágono sutil)
    # Pontos do hexágono
    radius_hex = 100
    points = []
    for i in range(6):
        angle_deg = 60 * i
        angle_rad = math.pi / 180 * angle_deg
        x = center[0] + radius_hex * math.cos(angle_rad)
        y = center[1] + radius_hex * math.sin(angle_rad)
        points.append((x, y))
    
    draw.polygon(points, outline=(0, 0, 0, 200), width=8) # Linhas pretas dentro do núcleo ciano

    # 6. Brilho Final (Overlay Branco Suave)
    draw.ellipse([400, 400, 450, 450], fill=(255, 255, 255, 180))

    # Salvar
    img.save("jarvis_flutter/assets/icon.png")
    print("Ícone PRO gerado com sucesso!")

if __name__ == "__main__":
    create_pro_icon()
