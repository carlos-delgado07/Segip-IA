import os
import pytesseract
import json
from flask import Flask, request, jsonify
import cv2
import numpy as np
import base64
from datetime import datetime
import unicodedata

app = Flask(__name__)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def cargar_usuarios():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usuarios.json")
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return json.load(f)

# Extraer texto usando pytesseract desde imagen base64
def extraer_texto_base64(imagen_base64):
    try:
        img_data = base64.b64decode(imagen_base64)
        img_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(img_arr, cv2.IMREAD_GRAYSCALE)
        texto = pytesseract.image_to_string(img)
        texto = normalizar_texto(texto.strip())
        return texto, img
    except Exception as e:
        return "", None

@app.route('/verificar', methods=['POST'])
def comparar_dos_imagenes():
    data = request.get_json()

    # Verificar que estén ambas imágenes
    if 'imagen1' not in data or 'imagen2' not in data:
        return jsonify({'error': 'Faltan una o ambas imágenes'}), 400

    try:
        # Extraer texto de ambas imágenes
        texto1, img1 = extraer_texto_base64(data['imagen1'])
        texto2, img2 = extraer_texto_base64(data['imagen2'])

        if not texto1 or not texto2:
            return (
                jsonify({"error": "No se pudo extraer texto de una o ambas imágenes"}),
                400,
            )

        # Limpiar y formatear los textos extraídos
        texto1 = texto1.strip().lower()
        texto2 = texto2.strip().lower()

        # Verificar si ambos textos contienen el mismo nombre y apellido
        if texto1 == texto2:
            usuarios = cargar_usuarios()
            usuario_encontrado = None

            for usuario in usuarios.get("usuarios", []):
                if usuario["nombre"].lower() in texto1 and usuario["apellido"].lower() in texto1:
                    usuario_encontrado = usuario
                    break

            if usuario_encontrado:
                # Crear carpeta de destino por fecha
                fecha_actual = datetime.now().strftime("%Y-%m-%d")
                carpeta_destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'verificados', fecha_actual)
                os.makedirs(carpeta_destino, exist_ok=True)

                # Guardar ambas imágenes con nombre diferenciado
                timestamp = datetime.now().strftime('%H%M%S')
                nombre_base = f"{usuario_encontrado['nombre']}_{usuario_encontrado['apellido']}_{timestamp}"
                ruta_imagen1 = os.path.join(carpeta_destino, f"{nombre_base}_1.jpg")
                ruta_imagen2 = os.path.join(carpeta_destino, f"{nombre_base}_2.jpg")

            cv2.imwrite(ruta_imagen1, img1)
            cv2.imwrite(ruta_imagen2, img2)

                return jsonify({
                    'mensaje': 'Usuario encontrado en la base de datos',
                    'usuario': usuario_encontrado
                })

            else:
                return jsonify({'mensaje': 'El usuario no se encuentra en la base de datos'}), 404
        else:
            return jsonify({'error': 'Los nombres y apellidos de ambas imágenes no coinciden'}), 400

    except Exception as e:
        return (
            jsonify({"error": f"Ocurrió un error al procesar las imágenes: {str(e)}"}),
            500,
        )


if __name__ == "__main__":
    app.run(port=5000, debug=True)
