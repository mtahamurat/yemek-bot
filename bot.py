from random import random

from flask import Flask, request

import os

try:
    import ayarlar

    DOGRULAMA_KELIMESI = ayarlar.DOGRULAMA_KELIMESI
    TOKEN = ayarlar.TOKEN
    TELEFON_ID = ayarlar.TELEFON_ID
except ImportError:
    DOGRULAMA_KELIMESI = os.environ["DOGRULAMA_KELIMESI"]
    TOKEN = os.environ["TOKEN"]
    TELEFON_ID = os.environ["TELEFON_ID"]
import requests
import yemek
from datetime import date, timedelta

app = Flask(__name__)


@app.route("/")
def ana_sayfa():
    return "Bot çalışıyor"


@app.route("/webhook", methods=["GET"])
def dogrula():
    mod = request.args.get("hub.mode")
    kelime = request.args.get("hub.verify_token")
    sinama = request.args.get("hub.challenge")
    if mod == "subscribe" and kelime == DOGRULAMA_KELIMESI:
        return sinama
    return "Yanlış kelime", 403

def cevap_gonder(numara, metin):
    adres = f"https://graph.facebook.com/v25.0/{TELEFON_ID}/messages"
    basliklar = {"Authorization": "Bearer " + TOKEN}
    paket = {
        "messaging_product": "whatsapp",
        "to": numara,
        "type": "text",
        "text": {"body": metin},
    }
    sonuc = requests.post(adres, headers=basliklar, json=paket)
    print(sonuc.status_code, sonuc.text)

from datetime import datetime
from zoneinfo import ZoneInfo


def bugun():
    return datetime.now(ZoneInfo("Europe/Istanbul")).date()


def temizle(metin):
    metin = metin.strip().lower()
    cevirme = {"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c", "\u0307": ""}
    for eski, yeni in cevirme.items():
        metin = metin.replace(eski, yeni)
    return metin


@app.route("/webhook", methods=["POST"])
def mesaj_geldi():
    veri = request.get_json()
    deger = veri["entry"][0]["changes"][0]["value"]

    if "messages" in deger:
        mesaj = deger["messages"][0]
        if mesaj["type"] == "text":
            kimden = mesaj["from"]
            yazi = mesaj["text"]["body"]
            print(kimden, "yazdı:", yazi)
            soru = temizle(yazi)
            if "yarin" in soru:
                tarih = bugun() + timedelta(days=1)
            elif "bugun" in soru:
                tarih = bugun()
            else:
                tarih = None
            if "kahvalti" in soru or "sabah" in soru:
                ogun = "kahvalti"
            elif "aksam" in soru:
                ogun = "aksam"
            else:
                ogun = None
            if tarih is None and ogun is None:
                cevap_gonder(kimden, "bugün, yarın, kahvaltı ya da akşam yaz")
            else:
                if tarih is None:
                    tarih = bugun()
                cevap_gonder(kimden, yemek.menu_metni(tarih, ogun))
    return "ok"

if __name__ == "__main__":
    app.run(port=5000)