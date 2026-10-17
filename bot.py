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
GROQ_ANAHTARI = os.environ.get("GROQ_ANAHTARI", "")
SAHIP_NUMARASI = os.environ.get("SAHIP_NUMARASI", "").strip()
SOHBET_ISMI = os.environ.get("SOHBET_ISMI", "")
SOHBET_NUMARALARI = {n.strip() for n in os.environ.get("SOHBET_NUMARALARI", "").split(",") if n.strip()}
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
            "body": {"text": "Merhaba! Hangi menüye bakmak istersin? Listeden seç ya da yaz, örneğin: yarın akşam"},
            "footer": {"text": "Fikrin varsa: önce \"öneri\" yaz, sonra fikrini"},
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
                        {"id": "oneri", "title": "Öneri / fikir"},
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


GROQ_MODEL = "openai/gpt-oss-120b"
SISTEM_MESAJI = (
    "Sen Taha'nın bu sohbet için özel yaptığı bir WhatsApp botusun. Karşındaki kişi seni zaten "
    "tanıyor, açılış mesajında kendini tanıttın. Kim olduğunu SADECE biri sorarsa söyle "
    "('Taha'nın sana özel botuyum' de), kendiliğinden kendini tanıtma ve selamlaşmayı tekrarlama. "
    "Sosyal medyada arkadaşıyla yazışan biri gibi, günlük konuşma diliyle, samimi ve rahat yaz "
    "(küçük harfle başlayabilirsin, 'ya', 'valla', 'bence' gibi kelimeler kullanabilirsin, resmi olma). "
    "ASLA emoji ya da emoticon kullanma. Kısa yaz: WhatsApp mesajı gibi, en fazla birkaç cümle. "
    "Karşındaki Taha'nın arkadaşı, sıkılmış ya da "
    "moralsiz olabilir; dinle, destek ol, gerekirse espri yap. Uzun listeler ve markdown kullanma. "
    "Bilmediğin şeyi uydurma."
)
if SOHBET_ISMI:
    SISTEM_MESAJI += f" Karşındakine '{SOHBET_ISMI}' diye hitap et, ama her mesajda tekrarlama."
SOHBETTE = set()
GECMIS = {}


def yapay_zeka_cevabi(kimden, yazi):
    gecmis = GECMIS.setdefault(kimden, [])
    gecmis.append({"role": "user", "content": yazi})
    del gecmis[:-20]
    try:
        sonuc = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer " + GROQ_ANAHTARI},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "system", "content": SISTEM_MESAJI}] + gecmis,
                "reasoning_effort": "low",
                "max_completion_tokens": 1000,
            },
            timeout=30,
        )
    except requests.RequestException as hata:
        print("GROQ HATA:", repr(hata))
        gecmis.pop()
        return "Bağlanamadım, birazdan tekrar dene."
    if sonuc.status_code != 200:
        print("GROQ", sonuc.status_code, sonuc.text[:300])
        gecmis.pop()
        if sonuc.status_code == 429:
            return "Biraz yoğunum, birazdan tekrar dene."
        return "Bir sorun oldu, birazdan tekrar dene."
    try:
        cevap = (sonuc.json()["choices"][0]["message"].get("content") or "").strip()
    except (ValueError, KeyError, IndexError):
        cevap = ""
    if not cevap:
        gecmis.pop()
        return "Cevap üretemedim, bir daha yazar mısın?"
    gecmis.append({"role": "assistant", "content": cevap})
    del gecmis[:-20]
    return cevap[:4000]


def sohbet_mi(kimden, yazi):
    """Sohbet modu mesajı ise cevaplar ve True döner."""
    if kimden not in SOHBET_NUMARALARI:
        return False
    soru = temizle(yazi).strip(" .!")
    if kimden in SOHBETTE:
        if soru in ("cik", "bitir"):
            SOHBETTE.discard(kimden)
            GECMIS.pop(kimden, None)
            cevap_gonder(kimden, "Sohbet bitti. Menü için bugün, yarın gibi bir şey yazabilirsin. Tekrar konuşmak için 'sohbet' yaz.")
        else:
            cevap_gonder(kimden, yapay_zeka_cevabi(kimden, yazi))
        return True
    if soru == "sohbet":
        SOHBETTE.add(kimden)
        selam = f"Selam {SOHBET_ISMI}" if SOHBET_ISMI else "Selam"
        cevap_gonder(kimden, f"{selam}, ben Taha'nın sana özel botuyum. Mesajların yapay zeka servisine (Groq) gider. Çıkmak için 'çık' yaz. Anlat bakalım, ne var ne yok?")
        return True
    return False


ONERI_SAYAC = {}
ONERI_LIMIT = 5


def oneri_mi(kimden, yazi):
    """'öneri ...' mesajıysa işler ve True döner."""
    soru = temizle(yazi)
    ilk = soru.split()[0].strip(":,.-") if soru.split() else ""
    if ilk not in ("oneri", "fikir"):
        return False
    parcalar = yazi.strip().split(None, 1)
    metin = parcalar[1].strip() if len(parcalar) > 1 else ""
    if not metin:
        cevap_gonder(kimden, "Mesajının başına \"öneri\" yaz, devamına fikrini ekle. Örnek: öneri haftalık menü de gelsin")
        return True
    if ONERI_SAYAC.get(kimden, 0) >= ONERI_LIMIT:
        cevap_gonder(kimden, "Çok fikrin var, teşekkürler! Biraz sonra tekrar yazabilirsin.")
        return True
    ONERI_SAYAC[kimden] = ONERI_SAYAC.get(kimden, 0) + 1
    metin = metin[:1000]
    print("ONERI:", kimden, metin)
    if SAHIP_NUMARASI:
        try:
            gonder({
                "messaging_product": "whatsapp",
                "to": SAHIP_NUMARASI,
                "type": "text",
                "text": {"body": f"Öneri ({kimden}):\n{metin}"},
            })
        except requests.RequestException as hata:
            print("ONERI iletilemedi:", repr(hata))
    cevap_gonder(kimden, "Teşekkürler, fikrini Taha'ya ilettim!")
    return True


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
            if not sohbet_mi(kimden, yazi) and not oneri_mi(kimden, yazi):
                cevapla(kimden, temizle(yazi))
        elif mesaj["type"] == "interactive":
            secim = mesaj["interactive"].get("list_reply", {}).get("id", "")
            print(kimden, "seçti:", secim)
            if secim == "oneri":
                oneri_mi(kimden, "oneri")
            else:
                cevapla(kimden, secim)
        else:
            cevap_gonder(kimden, "Şimdilik sadece yazılı mesajları anlıyorum. " + YARDIM_METNI)


if __name__ == "__main__":
    app.run(port=5000)