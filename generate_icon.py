"""
Gera um ícone .ico simples para o RLBotPro.
Requer: pip install Pillow
Uso: python generate_icon.py
"""
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow não instalado. Execute: pip install Pillow")
    print("Depois: python generate_icon.py")
    exit(1)

def create_icon(output_path="icone.ico"):
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (10, 11, 15, 255))
        draw = ImageDraw.Draw(img)

        # Background circle
        margin = size // 8
        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=size // 4,
            fill=(17, 19, 26, 255),
            outline=(173, 198, 255, 200),
            width=max(1, size // 32)
        )

        # "RL" text
        font_size = size // 3
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), "RL", font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (size - tw) // 2
        ty = (size - th) // 2
        draw.text((tx, ty), "RL", fill=(173, 198, 255, 255), font=font)

        images.append(img)

    # Save as .ico with multiple sizes
    images[-1].save(output_path, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[:-1])
    print(f"Ícone gerado: {output_path} ({len(sizes)} tamanhos: {sizes})")

if __name__ == "__main__":
    create_icon()
