"""
Alerta de precio del Dólar → Telegram
======================================
Consulta la tasa USD/COP cada X minutos y te avisa por Telegram
cuando el dólar suba o baje de tus umbrales configurados.
También envía un reporte cada lunes con el precio actual.

REQUISITOS:
  pip install requests beautifulsoup4
"""

import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
#  ✏️  CONFIGURA ESTOS VALORES
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = "8645826108:AAFB9Mmn9ErCKylpi0rGuoppBHdexYhs5iA"
TELEGRAM_CHAT_ID = "8769119970"

ALERTA_SUBE_DE   = 3800   # Avisar si el dólar SUBE de este valor (COP)
ALERTA_BAJA_DE   = 3400   # Avisar si el dólar BAJA de este valor (None para desactivar)

INTERVALO_MINUTOS = 1440   # Con qué frecuencia revisar el precio
REPORTE_LUNES     = True  # Enviar resumen cada lunes
HORA_REPORTE      = 8     # Hora del reporte del lunes (formato 24h)
# ─────────────────────────────────────────────

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AlertaDolar/1.0)"}

ultimo_estado       = None
ultimo_reporte_lunes = None


def obtener_tasa():
    try:
        r = requests.get("https://www.google.com/finance/quote/USD-COP", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        el = soup.find("div", {"data-last-price": True})
        if el:
            return float(el["data-last-price"])
    except Exception:
        pass
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        data = r.json()
        if data.get("result") == "success":
            return float(data["rates"]["COP"])
    except Exception:
        pass
    try:
        r = requests.get("https://wise.com/gb/currency-converter/usd-to-cop-rate?amount=1", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        el = soup.find("span", {"class": "text-success"})
        if el:
            return float(el.text.strip().replace(",", ""))
    except Exception:
        pass
    return None


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"  ✗ Error enviando mensaje: {e}")
        return False


def formatear_cop(valor):
    return f"${valor:,.2f} COP"


def ahora_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def es_lunes_y_hora_de_reporte():
    global ultimo_reporte_lunes
    ahora = datetime.now()
    hoy = ahora.date()
    if ahora.weekday() == 0 and ahora.hour == HORA_REPORTE:
        if ultimo_reporte_lunes != hoy:
            ultimo_reporte_lunes = hoy
            return True
    return False


def enviar_reporte_lunes(tasa):
    estado = "🟡 En rango normal"
    if ALERTA_SUBE_DE and tasa > ALERTA_SUBE_DE:
        estado = "🔴 Por encima de tu umbral alto"
    elif ALERTA_BAJA_DE and tasa < ALERTA_BAJA_DE:
        estado = "🟢 Por debajo de tu umbral bajo"

    mensaje = (
        f"📅 <b>Reporte del lunes</b>\n\n"
        f"💵 Dólar hoy: <b>{formatear_cop(tasa)}</b>\n"
        f"📊 Estado: {estado}\n\n"
        f"🔔 Alertas configuradas:\n"
        f"   • Sube de: {formatear_cop(ALERTA_SUBE_DE) if ALERTA_SUBE_DE else 'Desactivada'}\n"
        f"   • Baja de: {formatear_cop(ALERTA_BAJA_DE) if ALERTA_BAJA_DE else 'Desactivada'}\n\n"
        f"🕐 {ahora_str()}"
    )
    print(f"  → Enviando reporte del lunes...")
    ok = enviar_telegram(mensaje)
    print(f"  {'✓ Enviado' if ok else '✗ Falló el envío'}")


def revisar_y_alertar():
    global ultimo_estado
    ahora = datetime.now().strftime("%H:%M:%S")
    print(f"[{ahora}] Consultando tasa USD/COP...", end=" ")
    tasa = obtener_tasa()
    if tasa is None:
        print("✗ No se pudo obtener la tasa.")
        return
    print(f"✓ {formatear_cop(tasa)}")

    if REPORTE_LUNES and es_lunes_y_hora_de_reporte():
        enviar_reporte_lunes(tasa)

    nuevo_estado = "normal"
    mensaje = None

    if ALERTA_SUBE_DE is not None and tasa > ALERTA_SUBE_DE:
        nuevo_estado = "alto"
        if ultimo_estado != "alto":
            mensaje = (
                f"🔴 <b>¡Alerta! El dólar subió</b>\n\n"
                f"💵 Precio actual: <b>{formatear_cop(tasa)}</b>\n"
                f"📈 Superó tu umbral de {formatear_cop(ALERTA_SUBE_DE)}\n"
                f"🕐 {ahora_str()}"
            )
    elif ALERTA_BAJA_DE is not None and tasa < ALERTA_BAJA_DE:
        nuevo_estado = "bajo"
        if ultimo_estado != "bajo":
            mensaje = (
                f"🟢 <b>¡Alerta! El dólar bajó</b>\n\n"
                f"💵 Precio actual: <b>{formatear_cop(tasa)}</b>\n"
                f"📉 Bajó de tu umbral de {formatear_cop(ALERTA_BAJA_DE)}\n"
                f"🕐 {ahora_str()}"
            )
    elif ultimo_estado in ("alto", "bajo"):
        nuevo_estado = "normal"
        mensaje = (
            f"⚪ <b>Dólar volvió a zona normal</b>\n\n"
            f"💵 Precio actual: <b>{formatear_cop(tasa)}</b>\n"
            f"🕐 {ahora_str()}"
        )

    if mensaje:
        print(f"  → Enviando alerta a Telegram...")
        ok = enviar_telegram(mensaje)
        print(f"  {'✓ Enviado' if ok else '✗ Falló el envío'}")

    ultimo_estado = nuevo_estado


def main():
    print("=" * 50)
    print("  Monitor de Dólar USD/COP → Telegram")
    print("=" * 50)

    if "PEGA_AQUI" in TELEGRAM_TOKEN or "PEGA_AQUI" in str(TELEGRAM_CHAT_ID):
        print("\n⚠️  Configura tu TOKEN y CHAT_ID antes de ejecutar.\n")
        return

    print(f"\n  Umbral alto  : {formatear_cop(ALERTA_SUBE_DE) if ALERTA_SUBE_DE else 'Desactivado'}")
    print(f"  Umbral bajo  : {formatear_cop(ALERTA_BAJA_DE) if ALERTA_BAJA_DE else 'Desactivado'}")
    print(f"  Intervalo    : cada {INTERVALO_MINUTOS} minutos")
    print(f"  Reporte lunes: {'Sí, a las ' + str(HORA_REPORTE) + ':00h' if REPORTE_LUNES else 'No'}")
    print(f"\n  Presiona Ctrl+C para detener.\n")
    print("-" * 50)

    enviar_telegram(
        f"✅ <b>Monitor de dólar iniciado</b>\n\n"
        f"Te avisaré si el dólar supera <b>{formatear_cop(ALERTA_SUBE_DE)}</b> "
        f"o baja de <b>{formatear_cop(ALERTA_BAJA_DE)}</b>\n"
        f"📅 Recibirás un reporte cada lunes a las {HORA_REPORTE}:00h\n"
        f"🔄 Revisando cada {INTERVALO_MINUTOS} minutos."
    )

    while True:
        try:
            revisar_y_alertar()
            time.sleep(INTERVALO_MINUTOS * 60)
        except KeyboardInterrupt:
            print("\n\n  Monitor detenido.")
            break
        except Exception as e:
            print(f"  Error inesperado: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
