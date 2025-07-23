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
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalizar_texto(texto):
    # Quita tildes y pasa a minúsculas
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


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


@app.route("/verificar", methods=["POST"])
def verificar_usuario_en_imagenes():
    data = request.get_json()

    if "imagen1" not in data or "imagen2" not in data:
        return jsonify({"error": "Faltan una o ambas imágenes"}), 400

    try:
        texto1, img1 = extraer_texto_base64(data["imagen1"])
        texto2, img2 = extraer_texto_base64(data["imagen2"])

        if not texto1 or not texto2:
            return (
                jsonify({"error": "No se pudo extraer texto de una o ambas imágenes"}),
                400,
            )

        usuarios = cargar_usuarios()
        usuario_encontrado = None

        for usuario in usuarios.get("usuarios", []):
            nombres = normalizar_texto(usuario.get("nombres", ""))
            apellidos = normalizar_texto(usuario.get("apellidos", ""))

            # Verificar que ambos nombres y apellidos estén en ambos textos
            if (
                nombres in texto1
                and apellidos in texto1
                and nombres in texto2
                and apellidos in texto2
            ):
                usuario_encontrado = usuario
                break

        if usuario_encontrado:
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            carpeta_destino = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "verificados", fecha_actual
            )
            os.makedirs(carpeta_destino, exist_ok=True)

            archivos_en_carpeta = os.listdir(carpeta_destino)
            nombre_busqueda = f"{usuario_encontrado['nombres']}_{usuario_encontrado['apellidos']}".lower()

            ya_verificado = any(
                nombre_busqueda in archivo.lower() for archivo in archivos_en_carpeta
            )

            if ya_verificado:
                return (
                    jsonify(
                        {
                            "mensaje": "Este usuario ya ha sido verificado hoy. No es posible verificar nuevamente.",
                            "usuario": usuario_encontrado,
                        }
                    ),
                    403,
                )

            timestamp = datetime.now().strftime("%H%M%S")
            nombre_base = f"{usuario_encontrado['nombres']}_{usuario_encontrado['apellidos']}_{timestamp}"
            ruta_imagen1 = os.path.join(carpeta_destino, f"{nombre_base}_1.jpg")
            ruta_imagen2 = os.path.join(carpeta_destino, f"{nombre_base}_2.jpg")

            cv2.imwrite(ruta_imagen1, img1)
            cv2.imwrite(ruta_imagen2, img2)

            return jsonify(
                {
                    "mensaje": "Usuario verificado con éxito en ambas imágenes",
                    "usuario": usuario_encontrado,
                }
            )

        else:
            return (
                jsonify(
                    {
                        "mensaje": "Los nombres y apellidos no coinciden en ambas imágenes o no están en la base de datos"
                    }
                ),
                404,
            )

    except Exception as e:
        return (
            jsonify({"error": f"Ocurrió un error al procesar las imágenes: {str(e)}"}),
            500,
        )


@app.route("/validar_deposito", methods=["POST"])
def validar_deposito():
    data = request.get_json()

    if "imagen" not in data:
        return jsonify({"error": "No se recibió la imagen"}), 400

    try:
        texto, _ = extraer_texto_base64(data["imagen"])

        # Buscar expresiones comunes para 17 bolivianos
        patrones_validos = ["17 bs", "bs 17", "17,00", "17.00", "17bs", "bs17"]

        if any(pat in texto for pat in patrones_validos):
            return jsonify({"valido": True})
        else:
            return jsonify({"valido": False})
    except Exception as e:
        return jsonify({"error": f"Error al procesar la imagen: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
