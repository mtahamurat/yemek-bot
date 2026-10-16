from flask import Flask, request

import os
import re
from collections import deque

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
GORULEN = deque(maxlen=500)


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
    sonuc = requests.post(adres, headers=basliklar, json=paket, timeout=10)
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


AYLAR = {
    "ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5, "haziran": 6,
    "temmuz": 7, "agustos": 8, "eylul": 9, "ekim": 10, "kasim": 11, "aralik": 12,
}


def tarih_bul(soru):
    bu = bugun()
    if "yarin" in soru:
        return bu + timedelta(days=1)
    if "obur gun" in soru:
        return bu + timedelta(days=2)
    eslesme = re.search(r"(\d{1,2}) gun sonra", soru)
    if eslesme:
        return bu + timedelta(days=int(eslesme.group(1)))
    if "dun" in soru:
        return bu - timedelta(days=1)
    eslesme = re.search(r"(\d{1,2})\s*(" + "|".join(AYLAR) + ")", soru)
    if eslesme:
        try:
            return date(bu.year, AYLAR[eslesme.group(2)], int(eslesme.group(1)))
        except ValueError:
            return None
    eslesme = re.search(r"(\d{1,2})[./](\d{1,2})", soru)
    if eslesme:
        try:
            return date(bu.year, int(eslesme.group(2)), int(eslesme.group(1)))
        except ValueError:
            return None
    if "bugun" in soru:
        return bu
    return None


@app.route("/webhook", methods=["POST"])
def mesaj_geldi():
    try:
        mesaj_isle(request.get_json())
    except Exception as hata:
        print("HATA:", repr(hata))
    return "ok"


def mesaj_isle(veri):
    deger = veri["entry"][0]["changes"][0]["value"]

    if "messages" in deger:
        mesaj = deger["messages"][0]
        if mesaj["id"] in GORULEN:
            return
        GORULEN.append(mesaj["id"])
        if mesaj["type"] != "text":
            cevap_gonder(mesaj["from"], "Şimdilik sadece yazılı mesajları anlıyorum. bugün, yarın, kahvaltı ya da akşam yaz")
        if mesaj["type"] == "text":
            kimden = mesaj["from"]
            yazi = mesaj["text"]["body"]
            print(kimden, "yazdı:", yazi)
            soru = temizle(yazi)
            tarih = tarih_bul(soru)
            if "kahvalti" in soru or "sabah" in soru:
                ogun = "kahvalti"
            elif "aksam" in soru:
                ogun = "aksam"
            else:
                ogun = None
            if tarih is None and ogun is None and "ne var" not in soru and "menu" not in soru:
                cevap_gonder(kimden, "bugün, yarın, 2 gün sonra, 25 ekim, kahvaltı ya da akşam yaz")
            else:
                if tarih is None:
                    tarih = bugun()
                cevap_gonder(kimden, yemek.menu_metni(tarih, ogun))

if __name__ == "__main__":
    app.run(port=5000)