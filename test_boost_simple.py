import requests
import io
from PIL import Image, ImageDraw, ImageFont
import os

def draw_text_with_outline(draw, text, position, font, fill_color, outline_color='#000000', outline_width=2):
    """Dibuja texto con contorno para mejor legibilidad sobre fondos complejos"""
    x, y = position
    # Dibujar contorno (sombra)
    for offset_x in range(-outline_width, outline_width + 1):
        for offset_y in range(-outline_width, outline_width + 1):
            if offset_x != 0 or offset_y != 0:
                draw.text((x + offset_x, y + offset_y), text, font=font, fill=outline_color)
    # Dibujar texto principal
    draw.text((x, y), text, font=font, fill=fill_color)

def create_boost_image_test(user_avatar_url, user_name, user_tag, boost_count):
    """Versión de prueba de la función create_boost_image"""
    try:
        # Descargar avatar del usuario
        response = requests.get(user_avatar_url)
        avatar = Image.open(io.BytesIO(response.content))
        avatar = avatar.resize((200, 200))
        
        # Intentar cargar imagen de fondo personalizada
        background_path = 'assets/boost_background.png'
        width, height = 800, 600
        
        if os.path.exists(background_path):
            image = Image.open(background_path).convert('RGB')
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(image)
            print('Imagen de fondo cargada exitosamente')
        else:
            # Fallback: Crear imagen base (fondo oscuro con acentos púrpura)
            image = Image.new('RGB', (width, height), color='#1a1a2e')
            draw = ImageDraw.Draw(image)
            
            # Gradiente de fondo (simulado con rectángulos)
            for i in range(height):
                color_intensity = int(26 + (i / height) * 30)
                draw.rectangle([(0, i), (width, i+1)], fill=(color_intensity, color_intensity, color_intensity + 20))
            
            # Borde púrpura brillante
            draw.rectangle([(10, 10), (width-10, height-10)], outline='#9b59b6', width=3)
            print('⚠️ Imagen de fondo no encontrada, usando fallback')
        
        # Dibujar círculo para el avatar (más grande y centrado como en la imagen de referencia)
        avatar_x, avatar_y = width // 2 - 120, height // 2 - 140
        # Contorno del círculo del avatar con múltiples capas para efecto brillante
        draw.ellipse([avatar_x - 4, avatar_y - 4, avatar_x + 244, avatar_y + 244], outline='#9b59b6', width=8)
        draw.ellipse([avatar_x - 2, avatar_y - 2, avatar_x + 242, avatar_y + 242], outline='#e056fd', width=4)
        
        # Pegar avatar en el centro (más grande)
        avatar = avatar.resize((240, 240), Image.Resampling.LANCZOS)
        avatar_mask = Image.new('L', (240, 240), 0)
        avatar_mask_draw = ImageDraw.Draw(avatar_mask)
        avatar_mask_draw.ellipse([(0, 0), (240, 240)], fill=255)
        avatar.putalpha(avatar_mask)
        image.paste(avatar, (avatar_x, avatar_y), avatar)
        
        # Intentar cargar fuente, si no existe usar fuente por defecto
        try:
            # Intentar varias fuentes comunes
            font_paths = [
                "arial.ttf",
                "DejaVuSans.ttf",
                "FreeSans.ttf",
                "LiberationSans-Regular.ttf"
            ]
            
            title_font = None
            subtitle_font = None
            username_font = None
            message_font = None
            small_font = None
            
            for font_path in font_paths:
                try:
                    if not title_font:
                        title_font = ImageFont.truetype(font_path, 45)
                    if not subtitle_font:
                        subtitle_font = ImageFont.truetype(font_path, 38)
                    if not username_font:
                        username_font = ImageFont.truetype(font_path, 30)
                    if not message_font:
                        message_font = ImageFont.truetype(font_path, 52)
                    if not small_font:
                        small_font = ImageFont.truetype(font_path, 22)
                    if title_font and subtitle_font and username_font and message_font and small_font:
                        break
                except:
                    continue
            
            # Si no se encontró ninguna fuente, usar por defecto
            if not title_font or not subtitle_font or not username_font or not message_font or not small_font:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                username_font = ImageFont.load_default()
                message_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
                
        except Exception as e:
            print(f'⚠️ Error al cargar fuentes: {e}, usando fuente por defecto')
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            username_font = ImageFont.load_default()
            message_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Título "DISCORD BOT" (posicionado más arriba como en la imagen de referencia)
        title_text = "DISCORD BOT"
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        draw_text_with_outline(title_text, (title_x, 15), title_font, '#c39bd3', '#000000', 3)
        
        # Subtítulo "BOOST SERVER" (en rojo brillante como en la imagen)
        subtitle_text = "BOOST SERVER"
        subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (width - subtitle_width) // 2
        draw_text_with_outline(subtitle_text, (subtitle_x, 65), subtitle_font, '#ff4757', '#000000', 3)
        
        # Texto de nombre de usuario (debajo del avatar)
        # Usar el username completo o formato clásico si el discriminator no es 0
        if user_tag and user_tag != "0":
            username_text = f"@{user_name}#{user_tag}"
        else:
            username_text = f"@{user_name}"
        
        username_bbox = draw.textbbox((0, 0), username_text, font=username_font)
        username_width = username_bbox[2] - username_bbox[0]
        username_x = (width - username_width) // 2
        draw_text_with_outline(username_text, (username_x, 385), username_font, '#ffffff', '#000000', 3)
        
        # Mensaje de agradecimiento en lugar del nombre duplicado
        thanks_text = "¡GRACIAS POR BOOSTEAR!"
        thanks_bbox = draw.textbbox((0, 0), thanks_text, font=username_font)
        thanks_width = thanks_bbox[2] - thanks_bbox[0]
        thanks_x = (width - thanks_width) // 2
        draw_text_with_outline(thanks_text, (thanks_x, 355), username_font, '#ffd700', '#000000', 3)
        
        # Texto de mensaje principal (en amarillo grande como en la imagen)
        message_text = "GRACIAS POR LA MEJORA"
        message_bbox = draw.textbbox((0, 0), message_text, font=message_font)
        message_width = message_bbox[2] - message_bbox[0]
        message_x = (width - message_width) // 2
        draw_text_with_outline(message_text, (message_x, 425), message_font, '#ffd700', '#000000', 4)
        
        # Texto de conteo de boosts (en blanco como en la imagen)
        boost_text = f"AHORA EL SERVER TIENE {boost_count} MEJORAS"
        boost_bbox = draw.textbbox((0, 0), boost_text, font=username_font)
        boost_width = boost_bbox[2] - boost_bbox[0]
        boost_x = (width - boost_width) // 2
        draw_text_with_outline(boost_text, (boost_x, 485), username_font, '#ffffff', '#000000', 3)
        
        # Texto inferior (en rojo como en la imagen)
        bottom_text = "¡BOOSTEA AHORA! Y FORMA PARTE DEL CRECIMIENTO"
        bottom_bbox = draw.textbbox((0, 0), bottom_text, font=small_font)
        bottom_width = bottom_bbox[2] - bottom_bbox[0]
        bottom_x = (width - bottom_width) // 2
        draw_text_with_outline(bottom_text, (bottom_x, 535), small_font, '#ff4757', '#000000', 2)
        
        # Guardar imagen en memoria
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG', quality=95)
        img_byte_arr.seek(0)
        
        print(f'✅ Imagen de boost creada exitosamente para {user_name}')
        return img_byte_arr
    except Exception as e:
        print(f'❌ Error al crear imagen de boost: {e}')
        return None

if __name__ == "__main__":
    print("Probando la funcion create_boost_image...")
    
    # Datos de prueba
    avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"
    user_name = "UsuarioPrueba"
    user_tag = "test1234"
    boost_count = 5

    # Crear la imagen
    img_byte_arr = create_boost_image_test(avatar_url, user_name, user_tag, boost_count)

    if img_byte_arr:
        # Guardar la imagen para revisión
        output_path = "test_boost_output.png"
        with open(output_path, "wb") as f:
            f.write(img_byte_arr.getvalue())
        print(f"Imagen guardada en: {output_path}")
        print(f"Tamano de la imagen: {len(img_byte_arr.getvalue())} bytes")
    else:
        print("Error: No se pudo crear la imagen")
