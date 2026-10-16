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

def gonder(paket):
    adres = f"https://graph.facebook.com/v25.0/{TELEFON_ID}/messages"
    basliklar = {"Authorization": "Bearer " + TOKEN}
    sonuc = requests.post(adres, headers=basliklar, json=paket, timeout=10)
    print(sonuc.status_code, sonuc.text)
    return sonuc


def cevap_gonder(numara, metin):
    gonder({
        "messaging_product": "whatsapp",
        "to": numara,
        "type": "text",
        "text": {"body": metin},
    })


YARDIM_METNI = "bugün, yarın, 2 gün sonra, 25 ekim, kahvaltı ya da akşam yaz"


def liste_gonder(numara):
    paket = {
        "messaging_product": "whatsapp",
        "to": numara,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Merhaba! Hangi menüye bakmak istersin? Listeden seçebilir ya da yazabilirsin: " + YARDIM_METNI},
            "action": {
                "button": "Menüyü seç",
                "sections": [
                    {"title": "Bugün", "rows": [
                        {"id": "bugun", "title": "Tüm gün"},
                        {"id": "bugun kahvalti", "title": "Kahvaltı"},
                        {"id": "bugun aksam", "title": "Akşam yemeği"},
                    ]},
                    {"title": "Yarın", "rows": [
                        {"id": "yarin", "title": "Tüm gün"},
                        {"id": "yarin kahvalti", "title": "Kahvaltı"},
                        {"id": "yarin aksam", "title": "Akşam yemeği"},
                    ]},
                    {"title": "Diğer", "rows": [
                        {"id": "2 gun sonra", "title": "2 gün sonra"},
                    ]},
                ],
            },
        },
    }
    sonuc = gonder(paket)
    if sonuc.status_code != 200:
        cevap_gonder(numara, YARDIM_METNI)


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


def cevapla(kimden, soru):
    tarih = tarih_bul(soru)
    if "kahvalti" in soru or "sabah" in soru:
        ogun = "kahvalti"
    elif "aksam" in soru:
        ogun = "aksam"
    else:
        ogun = None
    if tarih is None and ogun is None and "ne var" not in soru and "menu" not in soru:
        liste_gonder(kimden)
    else:
        if tarih is None:
            tarih = bugun()
        cevap_gonder(kimden, yemek.menu_metni(tarih, ogun))


def mesaj_isle(veri):
    deger = veri["entry"][0]["changes"][0]["value"]

    if "messages" in deger:
        mesaj = deger["messages"][0]
        if mesaj["id"] in GORULEN:
            return
        GORULEN.append(mesaj["id"])
        kimden = mesaj["from"]
        if mesaj["type"] == "text":
            yazi = mesaj["text"]["body"]
            print(kimden, "yazdı:", yazi)
            cevapla(kimden, temizle(yazi))
        elif mesaj["type"] == "interactive":
            secim = mesaj["interactive"].get("list_reply", {}).get("id", "")
            print(kimden, "seçti:", secim)
            cevapla(kimden, secim)
        else:
            cevap_gonder(kimden, "Şimdilik sadece yazılı mesajları anlıyorum. " + YARDIM_METNI)


if __name__ == "__main__":
    app.run(port=5000)