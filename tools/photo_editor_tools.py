
import os
from pathlib import Path
import math

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("⚠️  Pillow no está disponible. Las herramientas de edición de fotos mostrarán mensajes informativos.")


class PhotoEditorTools:
    """
    Herramientas profesionales para edición de fotos y diseño gráfico.
    """

    @staticmethod
    def _check_pillow_available():
        if not PILLOW_AVAILABLE:
            return "Pillow (PIL) no está instalado. Instálalo con: pip install pillow"
        return None

    @staticmethod
    def open_image(file_path):
        """
        Abre una imagen para edición.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(file_path)
        return f"Imagen abierta exitosamente: {file_path} ({img.width}x{img.height} píxeles)"

    @staticmethod
    def resize_image(input_path, output_path, width, height=None, maintain_aspect_ratio=True):
        """
        Redimensiona una imagen profesionalmente.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        
        if maintain_aspect_ratio and height is None:
            ratio = width / img.width
            height = int(img.height * ratio)
        elif maintain_aspect_ratio and width is None:
            ratio = height / img.height
            width = int(img.width * ratio)
        elif maintain_aspect_ratio:
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            img.save(output_path)
            return f"Imagen redimensionada exitosamente a {img.width}x{img.height} y guardada en {output_path}"
        
        img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
        img_resized.save(output_path)
        
        return f"Imagen redimensionada exitosamente a {width}x{height} y guardada en {output_path}"

    @staticmethod
    def crop_image(input_path, output_path, left, top, right, bottom):
        """
        Recorta una imagen a las dimensiones especificadas.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        cropped_img = img.crop((left, top, right, bottom))
        cropped_img.save(output_path)
        
        return f"Imagen recortada exitosamente y guardada en {output_path}"

    @staticmethod
    def adjust_brightness(input_path, output_path, factor):
        """
        Ajusta el brillo de la imagen profesionalmente.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        enhancer = ImageEnhance.Brightness(img)
        img_bright = enhancer.enhance(factor)
        img_bright.save(output_path)
        
        return f"Brillo ajustado por un factor de {factor} y guardado en {output_path}"

    @staticmethod
    def adjust_contrast(input_path, output_path, factor):
        """
        Ajusta el contraste de la imagen profesionalmente.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        enhancer = ImageEnhance.Contrast(img)
        img_contrast = enhancer.enhance(factor)
        img_contrast.save(output_path)
        
        return f"Contraste ajustado por un factor de {factor} y guardado en {output_path}"

    @staticmethod
    def adjust_saturation(input_path, output_path, factor):
        """
        Ajusta la saturación de la imagen profesionalmente.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        enhancer = ImageEnhance.Color(img)
        img_saturation = enhancer.enhance(factor)
        img_saturation.save(output_path)
        
        return f"Saturación ajustada por un factor de {factor} y guardado en {output_path}"

    @staticmethod
    def apply_filter(input_path, output_path, filter_name):
        """
        Aplica filtros profesionales a la imagen.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        
        filters = {
            "blur": ImageFilter.BLUR,
            "contour": ImageFilter.CONTOUR,
            "detail": ImageFilter.DETAIL,
            "edge_enhance": ImageFilter.EDGE_ENHANCE,
            "edge_enhance_more": ImageFilter.EDGE_ENHANCE_MORE,
            "emboss": ImageFilter.EMBOSS,
            "find_edges": ImageFilter.FIND_EDGES,
            "sharpen": ImageFilter.SHARPEN,
            "smooth": ImageFilter.SMOOTH,
            "smooth_more": ImageFilter.SMOOTH_MORE
        }
        
        if filter_name not in filters:
            return f"Error: Filtro '{filter_name}' no encontrado. Filtros disponibles: {list(filters.keys())}"
        
        img_filtered = img.filter(filters[filter_name])
        img_filtered.save(output_path)
        
        return f"Filtro '{filter_name}' aplicado exitosamente y guardado en {output_path}"

    @staticmethod
    def rotate_image(input_path, output_path, degrees, expand=True):
        """
        Rota una imagen profesionalmente.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        img_rotated = img.rotate(degrees, expand=expand)
        img_rotated.save(output_path)
        
        return f"Imagen rotada {degrees} grados exitosamente y guardada en {output_path}"

    @staticmethod
    def flip_image(input_path, output_path, direction="horizontal"):
        """
        Voltea una imagen horizontal o verticalmente.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        
        if direction == "horizontal":
            img_flipped = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif direction == "vertical":
            img_flipped = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        else:
            return "Error: Dirección debe ser 'horizontal' o 'vertical'."
        
        img_flipped.save(output_path)
        return f"Imagen volteada {direction} exitosamente y guardada en {output_path}"

    @staticmethod
    def convert_image_format(input_path, output_path, output_format):
        """
        Convierte una imagen a diferentes formatos (PNG, JPG, BMP, etc.).
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        
        if img.mode in ('RGBA', 'P') and output_format.upper() == 'JPEG':
            img = img.convert('RGB')
        
        img.save(output_path, format=output_format.upper())
        
        return f"Imagen convertida a {output_format.upper()} exitosamente y guardada en {output_path}"

    @staticmethod
    def add_text_watermark(input_path, output_path, text, position=(10, 10), font_size=36, color=(255, 255, 255, 128)):
        """
        Añade una marca de agua de texto profesional a la imagen.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path).convert("RGBA")
        
        txt = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt)
        
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        draw.text(position, text, font=font, fill=color)
        
        watermarked = Image.alpha_composite(img, txt)
        
        if watermarked.mode in ('RGBA', 'P') and output_path.lower().endswith(('.jpg', '.jpeg')):
            watermarked = watermarked.convert('RGB')
        
        watermarked.save(output_path)
        
        return f"Marca de agua añadida exitosamente y guardada en {output_path}"

    @staticmethod
    def add_image_watermark(input_path, output_path, watermark_path, position=(10, 10), opacity=0.5):
        """
        Añade una marca de agua de imagen profesional a la imagen.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path).convert("RGBA")
        watermark = Image.open(watermark_path).convert("RGBA")
        
        watermark = watermark.resize((int(watermark.width * opacity), int(watermark.height * opacity)))
        
        txt = Image.new('RGBA', img.size, (255, 255, 255, 0))
        txt.paste(watermark, position, watermark)
        
        watermarked = Image.alpha_composite(img, txt)
        
        if watermarked.mode in ('RGBA', 'P') and output_path.lower().endswith(('.jpg', '.jpeg')):
            watermarked = watermarked.convert('RGB')
        
        watermarked.save(output_path)
        
        return f"Marca de agua de imagen añadida exitosamente y guardada en {output_path}"

    @staticmethod
    def create_thumbnail(input_path, output_path, size=(128, 128)):
        """
        Crea una miniatura profesional de la imagen.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        img.save(output_path)
        
        return f"Miniatura creada exitosamente en {output_path} con tamaño {size}"

    @staticmethod
    def create_collage(image_paths, output_path, grid_size=(3, 3), image_size=(300, 300), bg_color=(255, 255, 255)):
        """
        Crea un collage profesional de imágenes.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        rows, cols = grid_size
        width = cols * image_size[0]
        height = rows * image_size[1]
        
        collage = Image.new('RGB', (width, height), bg_color)
        
        for i, img_path in enumerate(image_paths[:rows*cols]):
            row = i // cols
            col = i % cols
            x = col * image_size[0]
            y = row * image_size[1]
            
            img = Image.open(img_path)
            img.thumbnail(image_size, Image.Resampling.LANCZOS)
            
            paste_x = x + (image_size[0] - img.width) // 2
            paste_y = y + (image_size[1] - img.height) // 2
            
            collage.paste(img, (paste_x, paste_y))
        
        collage.save(output_path)
        return f"Collage creado exitosamente en {output_path} con {len(image_paths[:rows*cols])} imágenes"

    @staticmethod
    def adjust_exposure(input_path, output_path, exposure_factor):
        """
        Ajusta la exposición de la imagen profesionalmente.
        """
        check = PhotoEditorTools._check_pillow_available()
        if check:
            return check
        img = Image.open(input_path)
        img = img.point(lambda p: p * exposure_factor)
        img.save(output_path)
        return f"Exposición ajustada por un factor de {exposure_factor} y guardada en {output_path}"


print("PhotoEditorTools inicializado: Herramientas profesionales para edición de fotos y diseño gráfico.")
