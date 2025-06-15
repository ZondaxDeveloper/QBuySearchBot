from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from urllib.parse import quote
import re

TOKEN = "7751946058:AAEjrCiceGujRBjc-zXpY1DuCR1UzBgpVoo"
SERPAPI_KEY = "e307eea4f96c08f1374278ce8dd16af72c7583e74662080e9792a20a2fe51d9f"
MI_TRACKING_ID = "mrd2009-21"
TRACKING_IDS = {
    "amazon.com": "qbuysearch-20",
    "amazon.com.mx": "mrdmex-20",
    "amazon.es": "mrd2009-21",
    # puedes agregar más si te registras en más países
}

USUARIO_IDIOMAS = {}  # user_id -> 'es', 'en', 'fr', etc.
PLACE_DOMINIOS = {
    "mx": "amazon.com.mx",
    "us": "amazon.com",
    "com": "amazon.com",
    "es": "amazon.es",
    "fr": "amazon.fr",
    "it": "amazon.it",
    "jp": "amazon.co.jp"
}

TRADUCCIONES = {
    "es": {
        "bienvenida":"📌 Bienvenido a QBuySearch 🛍️\n\nPara buscar productos, escribe:\n➨ buscar <producto>\nSi quieres buscar en otro país, añade:\n buscar /place mx|es|us\n\n🌐 Puedes cambiar el idioma con:\n /setlang <es|en|fr>\n\nSe te mostrarán los mejores productos con precio, imagen y descripción 💵",
        "buscar_palabra": "buscar",
        "buscando": "🔎 Buscando '{query}' en {dominio}...",
        "formato_invalido": "❗️Escribe algo como: buscar audífonos bluetooth /place mx",
        "ayuda": "Escríbeme 'buscar <producto> /place <mx|us|es|...>' para encontrar productos en Amazon 🛍️",
        "ver_producto": "Ver producto"
    },
    "en": {
        "bienvenida": "📌 Welcome to QBuySearch 🛍️\n\nTo search for products, type:\n➨ search <product>\nTo search in another country, add:\nMexico ➨ search /place mx|es|us\n\n🌐 You can change the language with:\n /setlang <en|es|fr>\n\nYou'll see the best products with price, image and description 💵",
        "buscar_palabra": "search",
        "buscando": "🔎 Searching for '{query}' on {dominio}...",
        "formato_invalido": "❗️Type something like: search bluetooth headphones /place us",
        "ayuda": "Type 'search <product> /place <mx|us|es|...>' to find products on Amazon 🛍️",
        "ver_producto": "View product"
    },
    "fr": {
        "bienvenida": "📌 Bienvenue sur QBuySearch 🛍️\n\nPour rechercher des produits, écrivez :\n➨ rechercher <produit>\nPour rechercher dans un autre pays, ajoutez :\nMexique ➨ rechercher <produit> /place mx\nEspagne ➨ rechercher <produit> /place es\nUSA ➨ rechercher <produit> /place us\nVous verrez les meilleurs produits avec prix, image et description 💵",
        "buscar_palabra": "rechercher",
        "buscando": "🔎 Recherche de '{query}' sur {dominio}...",
        "formato_invalido": "❗️Écrivez quelque chose comme : rechercher écouteurs bluetooth /place fr",
        "ayuda": "Écrivez 'rechercher <produit> /place <fr|us|es|...>' pour trouver des produits sur Amazon 🛍️",
        "ver_producto": "Voir le produit"
    }
}
def get_idioma(update: Update) -> str:
    user_id = update.effective_user.id if update.effective_user else None
    if user_id in USUARIO_IDIOMAS:
        return USUARIO_IDIOMAS[user_id]

    if update.message and update.message.from_user:
        idioma = update.message.from_user.language_code
        if idioma:
            idioma = idioma[:2]
            print("🌐 Idioma detectado:", idioma)
            return idioma
    return "es"


from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def construir_link_afiliado(link_original):
    try:
        parsed = urlparse(link_original)
        query = parse_qs(parsed.query)

        dominio = parsed.netloc.replace("www.", "")
        
        # ❌ No usar afiliado si es US o MX
        if dominio in ["amazon.com", "amazon.com.mx"]:
            return link_original

        tracking_id = TRACKING_IDS.get(dominio, "mrd2009-21")

        if 'tag' in query:
            return link_original

        query['tag'] = tracking_id
        new_query = urlencode(query, doseq=True)

        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

        return new_url
    except Exception as e:
        print("❌ Error construyendo link de afiliado:", e)
        return link_original


def extraer_asin(link):
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", link)
    return match.group(1) if match else None

def buscar_amazon(producto, dominio="amazon.com"):
    params = {
        "engine": "amazon",
        "amazon_domain": dominio,
        "k": producto,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
        resultados = []
        if "organic_results" in data:
            encontrados = 0
            for item in data["organic_results"]:
                if encontrados >= 3:
                    break
                if isinstance(item, dict):
                    link_original = item.get("link", "")
                    asin = extraer_asin(link_original)
                    if asin is None:
                        continue
                    titulo = item.get("title", "Sin título")
                    precio_raw = item.get("price")
                    if isinstance(precio_raw, dict):
                        precio = precio_raw.get("raw", "Sin precio")
                    elif isinstance(precio_raw, str):
                        precio = precio_raw
                    else:
                        precio = item.get("primary_offer", {}).get("price", "Sin precio")
                    link_afiliado = construir_link_afiliado(link_original)
                    imagen_url = item.get("thumbnail") or item.get("image")
                    resultados.append({
                        "titulo": titulo,
                        "precio": precio,
                        "url": link_afiliado,
                        "imagen": imagen_url
                    })
                    encontrados += 1
        else:
            resultados.append({"titulo": "Sin resultados", "precio": "—", "url": "#", "imagen": None})
        return resultados or [{"titulo": "No se encontraron productos con enlace válido.", "precio": "—", "url": "#", "imagen": None}]
    except Exception as e:
        return [{"titulo": "⚠️ Error al buscar", "precio": str(e), "url": "#", "imagen": None}]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_idioma(update)
    mensajes = TRADUCCIONES.get(lang, TRADUCCIONES["es"])
    
    # Mensaje temporal para depurar idioma
    await update.message.reply_text(f"🌐 Idioma detectado: {lang}")
    
    mensaje = await update.message.reply_text(mensajes["bienvenida"])
    try:
        await context.bot.pin_chat_message(chat_id=update.effective_chat.id, message_id=mensaje.message_id)
    except Exception as e:
        print(f"⚠️ No se pudo fijar el mensaje: {e}")

async def setlang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else None
    if not context.args:
        await update.message.reply_text("❗️ Debes escribir un idioma. Ejemplo: /setlang en")
        return

    nuevo_idioma = context.args[0].lower()
    if nuevo_idioma not in TRADUCCIONES:
        await update.message.reply_text("❗️ Idioma no soportado. Usa uno de estos: " + ", ".join(TRADUCCIONES.keys()))
        return

    USUARIO_IDIOMAS[user_id] = nuevo_idioma
    mensajes = TRADUCCIONES[nuevo_idioma]
    await update.message.reply_text(f"✅ Idioma cambiado a {nuevo_idioma.upper()}.\n\n" + mensajes["bienvenida"])

async def enviar_producto_con_boton(update: Update, titulo: str, precio: str, url: str, imagen: str = None, boton_text="Ver producto"):
    boton = InlineKeyboardButton(text=boton_text, url=url)
    teclado = InlineKeyboardMarkup([[boton]])
    mensaje = f"📦 {titulo}\n💵 {precio}"
    if imagen:
        await update.message.reply_photo(photo=imagen, caption=mensaje, reply_markup=teclado)
    else:
        await update.message.reply_text(mensaje, reply_markup=teclado)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.lower()
    lang = get_idioma(update)
    mensajes = TRADUCCIONES.get(lang, TRADUCCIONES["es"])
    palabra_buscar = mensajes.get("buscar_palabra", "buscar")

    if palabra_buscar in texto:
        match = re.search(r"/place\s+(\w+)", texto)

        if match and match.group(1).lower() not in PLACE_DOMINIOS:
            await update.message.reply_text("❗ País no válido. Usa /place mx, es, us, fr, etc.")
            return
        
        dominio = PLACE_DOMINIOS.get(match.group(1), "amazon.es") if match else "amazon.es"
        
        palabra_clave = re.sub(rf"{palabra_buscar}", "", texto)
        palabra_clave = re.sub(r"/place\s+\w+", "", palabra_clave).strip()

        if not palabra_clave:
            await update.message.reply_text(mensajes["formato_invalido"])
            return
        
        await update.message.reply_text(mensajes["buscando"].format(query=palabra_clave, dominio=dominio))
        resultados = buscar_amazon(palabra_clave, dominio)
        for producto in resultados:
            await enviar_producto_con_boton(
                update,
                producto["titulo"],
                producto["precio"],
                producto["url"],
                producto["imagen"],
                mensajes["ver_producto"]
            )
    else:
        await update.message.reply_text(mensajes["ayuda"])
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_idioma(update)
    mensajes = TRADUCCIONES.get(lang, TRADUCCIONES["es"])
    await update.message.reply_text(mensajes["bienvenida"])


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("setlang", setlang))
    app.add_handler(CommandHandler("help", help_command))
    print("🤖 Bot corriendo...")
    app.run_polling()
