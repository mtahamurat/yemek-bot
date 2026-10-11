from flask import Flask, request

import ayarlar
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
    if mod == "subscribe" and kelime == ayarlar.DOGRULAMA_KELIMESI:
        return sinama
    return "Yanlış kelime", 403

def cevap_gonder(numara, metin):
    adres = f"https://graph.facebook.com/v25.0/{ayarlar.TELEFON_ID}/messages"
    basliklar = {"Authorization": "Bearer " + ayarlar.TOKEN}
    paket = {
        "messaging_product": "whatsapp",
        "to": numara,
        "type": "text",
        "text": {"body": metin},
    }
    sonuc = requests.post(adres, headers=basliklar, json=paket)
    print(sonuc.status_code, sonuc.text)

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
            soru = yazi.strip().lower()
            if soru in ("bugün", "bugun"):
                cevap_gonder(kimden, yemek.menu_metni(date.today()))
            elif soru in ("yarın", "yarin"):
                cevap_gonder(kimden, yemek.menu_metni(date.today() + timedelta(days=1)))
            else:
                cevap_gonder(kimden, "bugün ya da yarın yaz")

    return "ok"


if __name__ == "__main__":
    app.run(port=5000)