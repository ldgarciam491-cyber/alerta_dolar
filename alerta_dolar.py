"""
Monitor de Dólar USD/COP → Telegram (Optimizado)
================================================
- Revisión cada 60 minutos (configurable)
- Alertas por umbral (sube / baja / vuelve a normal)
- Reporte semanal los lunes
- Uso de variables de entorno (seguridad)
- Manejo de errores robusto
"""

import requests
import time
import os
from datetime import datetime
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# VARIABLES DE ENTORNO (Railway)
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ALERTA_SUBE_DE = float(os.getenv("ALERTA_SUBE_DE", 3800))
ALERTA_BAJA_DE = float(os.getenv("ALERTA_BAJA_DE", 3400))

INTERVALO_MINUTOS = 60   # 🔥 óptimo (puedes poner 30–120)
HORA_REPORTE = 8

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Estado en memoria
ultimo_estado = None
ultimo_reporte_lunes = None

# ─────────────────────────────────────────────
# FUNCIONES
# ─────────────────────────────────────────────

def obtener_tasa():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        data = r.json()
        if data.get("result") == "success":
            return float(data["rates"]["COP"])
    except:
        pass
    return None


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")


def formatear(valor):
    return f"${valor:,.0f} COP"


def ahora():
    return datetime.now().strftime("%d/%m %H:%M")


# ─────────────────────────────────────────────
# REPORTE LUNES (ROBUSTO)
# ─────────────────────────────────────────────
def debe_enviar_reporte():
    global ultimo_reporte_lunes

    now = datetime.now()
    hoy = now.date()

    if now.weekday() == 0 and now.hour >= HORA_REPORTE:
        if ultimo_reporte_lunes != hoy:
            ultimo_reporte_lunes = hoy
            return True
    return False


def enviar_reporte(tasa):
    mensaje = (
        f"📅 <b>Reporte semanal</b>\n\n"
        f"💵 Dólar: <b>{formatear(tasa)}</b>\n\n"
        f"🔔 Umbrales:\n"
        f"↑ {formatear(ALERTA_SUBE_DE)}\n"
        f"↓ {formatear(ALERTA_BAJA_DE)}\n\n"
        f"🕐 {ahora()}"
    )
    enviar_telegram(mensaje)


# ─────────────────────────────────────────────
# LÓGICA DE ALERTAS
# ─────────────────────────────────────────────
def evaluar_alertas(tasa):
    global ultimo_estado

    nuevo_estado = "normal"
    mensaje = None

    if tasa > ALERTA_SUBE_DE:
        nuevo_estado = "alto"
        if ultimo_estado != "alto":
            mensaje = f"🔴 Dólar ALTO\n💵 {formatear(tasa)}\n🕐 {ahora()}"

    elif tasa < ALERTA_BAJA_DE:
        nuevo_estado = "bajo"
        if ultimo_estado != "bajo":
            mensaje = f"🟢 Dólar BAJO\n💵 {formatear(tasa)}\n🕐 {ahora()}"

    elif ultimo_estado in ("alto", "bajo"):
        nuevo_estado = "normal"
        mensaje = f"⚪ Dólar en rango normal\n💵 {formatear(tasa)}\n🕐 {ahora()}"

    if mensaje:
        print("Enviando alerta...")
        enviar_telegram(mensaje)

    ultimo_estado = nuevo_estado


# ─────────────────────────────────────────────
# LOOP PRINCIPAL (24/7)
# ─────────────────────────────────────────────
def main():
    print("Monitor USD/COP iniciado")

    enviar_telegram(
        f"✅ Monitor activo\n"
        f"Revisión cada {INTERVALO_MINUTOS} min\n"
        f"↑ {formatear(ALERTA_SUBE_DE)} | ↓ {formatear(ALERTA_BAJA_DE)}"
    )

    while True:
        try:
            print(f"[{ahora()}] Consultando...")

            tasa = obtener_tasa()

            if tasa:
                print(f"Precio: {formatear(tasa)}")

                evaluar_alertas(tasa)

                if debe_enviar_reporte():
                    print("Enviando reporte lunes...")
                    enviar_reporte(tasa)
            else:
                print("Error obteniendo tasa")

            time.sleep(INTERVALO_MINUTOS * 60)

        except Exception as e:
            print(f"Error general: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()