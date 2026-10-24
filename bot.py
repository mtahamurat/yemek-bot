from flask import Flask, request

import hashlib
import hmac
import json
import os
import re
import time
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
META_APP_SECRET = os.environ.get("META_APP_SECRET", "").strip()
SAHIP_NUMARASI = os.environ.get("SAHIP_NUMARASI", "").strip()
SOHBET_ISMI = os.environ.get("SOHBET_ISMI", "")
ONERI_SINIRSIZ = {n.strip() for n in os.environ.get("ONERI_SINIRSIZ", "").split(",") if n.strip()}
SOHBET_NUMARALARI = {n.strip() for n in os.environ.get("SOHBET_NUMARALARI", "").split(",") if n.strip()}
import requests
import yemek
from datetime import date, timedelta

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024
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
            "footer": {"text": "Fikrin varsa: önce \"öneri\" yaz, devamında fikrini"},
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


GUNLER = {
    "pazartesi": 0, "sali": 1, "carsamba": 2, "persembe": 3,
    "cumartesi": 5, "cuma": 4, "pazar": 6,
}
AY_ADLARI = [
    "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]
AYLAR = {
    "ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5, "haziran": 6,
    "temmuz": 7, "agustos": 8, "eylul": 9, "ekim": 10, "kasim": 11, "aralik": 12,
}


def yil_duzelt(bu, gun, ay):
    """Yılı verilmemiş tarih için en mantıklı yılı seçer (aralıkta '5 ocak' -> gelecek yıl)."""
    tarih = date(bu.year, ay, gun)
    if (bu - tarih).days > 60:
        tarih = date(bu.year + 1, ay, gun)
    elif (tarih - bu).days > 300:
        tarih = date(bu.year - 1, ay, gun)
    return tarih


def gun_ismi_bul(soru, bu):
    """'cuma', 'salıya', 'haftaya pazartesi' -> en yakın o gün (bugünse bugün)."""
    eslesme = re.search(r"\b(" + "|".join(GUNLER) + r")", soru)
    if not eslesme:
        return None
    fark = (GUNLER[eslesme.group(1)] - bu.weekday()) % 7
    if "haftaya" in soru or "gelecek hafta" in soru or "onumuzdeki hafta" in soru:
        fark += 7
    return bu + timedelta(days=fark)


def tarih_bul(soru):
    bu = bugun()
    if "yarin" in soru:
        return bu + timedelta(days=1)
    if "obur gun" in soru:
        return bu + timedelta(days=2)
    eslesme = re.search(r"(\d{1,2}) gun sonra", soru)
    if eslesme:
        return bu + timedelta(days=int(eslesme.group(1)))
    if re.search(r"\bdun\b", soru):
        return bu - timedelta(days=1)
    eslesme = re.search(r"(\d{1,2})\s*(" + "|".join(AYLAR) + ")", soru)
    if eslesme:
        try:
            return yil_duzelt(bu, int(eslesme.group(1)), AYLAR[eslesme.group(2)])
        except ValueError:
            return None
    eslesme = re.search(r"(" + "|".join(AYLAR) + r")\s*(\d{1,2})\b", soru)
    if eslesme:
        try:
            return yil_duzelt(bu, int(eslesme.group(2)), AYLAR[eslesme.group(1)])
        except ValueError:
            return None
    eslesme = re.search(r"(\d{1,2})[./](\d{1,2})", soru)
    if eslesme:
        try:
            return yil_duzelt(bu, int(eslesme.group(1)), int(eslesme.group(2)))
        except ValueError:
            return None
    gun = gun_ismi_bul(soru, bu)
    if gun:
        return gun
    if "bugun" in soru:
        return bu
    return None


SON_MESAJLAR = {}
HIZ_LIMITI = 15  # bir numaradan 60 saniyede en fazla bu kadar mesaj


def hiz_asildi(kimden):
    simdi = time.time()
    kayit = SON_MESAJLAR.setdefault(kimden, deque())
    while kayit and simdi - kayit[0] > 60:
        kayit.popleft()
    if len(kayit) >= HIZ_LIMITI:
        return True
    kayit.append(simdi)
    return False


def imza_gecerli(govde):
    if not META_APP_SECRET:
        return True
    gelen = request.headers.get("X-Hub-Signature-256", "")
    beklenen = "sha256=" + hmac.new(META_APP_SECRET.encode(), govde, hashlib.sha256).hexdigest()
    return hmac.compare_digest(gelen, beklenen)


@app.route("/webhook", methods=["POST"])
def mesaj_geldi():
    govde = request.get_data()
    if not imza_gecerli(govde):
        print("IMZA HATALI, istek reddedildi")
        return "Yetkisiz", 403
    try:
        mesaj_isle(json.loads(govde))
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
        cevap_gonder(kimden, f"{selam}, ben Taha'nın sadece senin için yaptığı botum. Burada sana yapay zeka cevap veriyor. Canın sıkıldığında buradayım. Çıkmak için 'çık' yaz. Anlat bakalım, ne var ne yok?")
        return True
    return False


ONERI_SAYAC = {}
ONERI_LIMIT = 5  # kişi başı günlük


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
    gun, adet = ONERI_SAYAC.get(kimden, (None, 0))
    if gun != bugun():
        adet = 0
    if adet >= ONERI_LIMIT and kimden not in ONERI_SINIRSIZ:
        cevap_gonder(kimden, "Bugünlük fikir hakkın doldu, teşekkürler! Yarın tekrar yazabilirsin.")
        return True
    ONERI_SAYAC[kimden] = (bugun(), adet + 1)
    metin = metin[:1000]
    print("ONERI:", kimden, metin)
    if SAHIP_NUMARASI:
        try:
            gonder({
                "messaging_product": "whatsapp",
                "to": SAHIP_NUMARASI,
                "type": "text",
                "text": {"body": f"Öneri ({kimden}):\n{metin}\n\nCevaplamak için: cevap {kimden} mesajın"},
            })
        except requests.RequestException as hata:
            print("ONERI iletilemedi:", repr(hata))
    cevap_gonder(kimden, "Teşekkürler, fikrini Taha'ya ilettim!")
    return True


TESEKKUR_KELIMELERI = {
    "tesekkur", "tesekkurler", "tesekkurlar", "tsk", "tskler", "tsm", "tsk ederim",
    "sagol", "sagolun", "saol", "sgl", "eyv", "eyw", "eyvallah", "eywallah",
    "thanks", "thx", "ty", "mersi", "super", "harika", "eline saglik",
}


def tesekkur_mu(soru):
    temiz = re.sub(r"[^a-z ]", " ", soru)
    kelimeler = temiz.split()
    if not kelimeler or len(kelimeler) > 6:
        return False
    birlesik = " ".join(kelimeler)
    if "sag ol" in birlesik or "eline saglik" in birlesik or "allah razi olsun" in birlesik:
        return True
    return any(k in TESEKKUR_KELIMELERI or k.startswith("tesekkur") for k in kelimeler)


def menu_yok_mesaji(tarih):
    """O gün için hiç menü yoksa açıklayıcı mesaj döner, varsa None."""
    if tarih in yemek.kahvalti or tarih in yemek.aksam:
        return None
    tum = set(yemek.kahvalti) | set(yemek.aksam)
    gun_yazisi = tarih.strftime("%d.%m.%Y")
    ay = AY_ADLARI[tarih.month]
    yuklu_aylar = {(t.year, t.month) for t in tum}
    if tum and tarih > max(tum) and (tarih.year, tarih.month) not in yuklu_aylar:
        return f"{gun_yazisi}: {ay} menüsü henüz yüklenmedi. Yüklenince buradan bakabilirsin."
    if tum and tarih < min(tum):
        return f"{gun_yazisi}: bu tarihin menüsü artık bende yok."
    return f"{gun_yazisi}: bu gün için menü bulunamadı."


BASLANGIC = datetime.now(ZoneInfo("Europe/Istanbul"))
GUNLUK_KULLANICI = {}   # {tarih: {numara özeti}}
TUM_KULLANICILAR = set()
MESAJ_SAYISI = [0]


def kullanici_kaydet(kimden):
    if kimden == SAHIP_NUMARASI:
        return
    ozet = hashlib.sha256(kimden.encode()).hexdigest()[:16]
    gun = bugun()
    GUNLUK_KULLANICI.setdefault(gun, set()).add(ozet)
    TUM_KULLANICILAR.add(ozet)
    MESAJ_SAYISI[0] += 1
    for eski in [g for g in GUNLUK_KULLANICI if (gun - g).days > 30]:
        del GUNLUK_KULLANICI[eski]


def istatistik_metni():
    gun = bugun()
    son7 = set()
    for g, kisiler in GUNLUK_KULLANICI.items():
        if (gun - g).days < 7:
            son7 |= kisiler
    return "\n".join([
        "İstatistik",
        f"Bugün: {len(GUNLUK_KULLANICI.get(gun, set()))} kişi",
        f"Dün: {len(GUNLUK_KULLANICI.get(gun - timedelta(days=1), set()))} kişi",
        f"Son 7 gün: {len(son7)} kişi",
        f"Toplam: {len(TUM_KULLANICILAR)} kişi, {MESAJ_SAYISI[0]} mesaj",
        f"Sayım başlangıcı: {BASLANGIC:%d.%m.%Y %H:%M}",
        "(Sunucu yeniden başlayınca sıfırlanır)",
    ])


def numara_duzelt(ham):
    """'0541...', '541...', '+90 541...' -> '90541...' (geçersizse None)."""
    rakam = re.sub(r"\D", "", ham)
    if rakam.startswith("0"):
        rakam = "9" + rakam
    elif len(rakam) == 10 and rakam.startswith("5"):
        rakam = "90" + rakam
    return rakam if len(rakam) == 12 and rakam.startswith("905") else None


def cevap_ilet(yazi):
    """'cevap 905xxxxxxxxx mesaj' komutunu işler, sahibe gidecek sonucu döner."""
    # 'cevap' kelimesinden sonra gelen rakam parçalarını numara say (boşluklu yazılabilir)
    parcalar = list(re.finditer(r"\S+", yazi))[1:]
    numara_ham, bitis = "", None
    for p in parcalar:
        if not re.fullmatch(r"\+?\d+", p.group()) or len(re.sub(r"\D", "", numara_ham)) >= 12:
            break
        numara_ham += p.group()
        bitis = p.end()
    mesaj = yazi[bitis:].strip()[:1000] if bitis else ""
    if not numara_ham or not mesaj:
        return "Kullanım: cevap 905xxxxxxxxx mesajın"
    numara = numara_duzelt(numara_ham)
    if not numara:
        return "Numara geçersiz. Örnek: cevap 905xxxxxxxxx Teşekkürler!"
    try:
        sonuc = gonder({
            "messaging_product": "whatsapp",
            "to": numara,
            "type": "text",
            "text": {"body": mesaj},
        })
    except requests.RequestException as hata:
        print("CEVAP iletilemedi:", repr(hata))
        return "İletilemedi, bağlantı hatası. Biraz sonra tekrar dene."
    if sonuc.status_code == 200:
        return f"İletildi: {numara}"
    return "İletilemedi. Kişi son 24 saatte bota yazmamış olabilir."


def sahip_komutu_mu(kimden, yazi):
    if not SAHIP_NUMARASI or kimden != SAHIP_NUMARASI:
        return False
    if temizle(yazi).split()[:1] == ["cevap"]:
        cevap_gonder(kimden, cevap_ilet(yazi))
        return True
    if temizle(yazi).strip(" .!?") in ("istatistik", "istatistikler", "stat"):
        cevap_gonder(kimden, istatistik_metni())
        return True
    return False


def cevapla(kimden, soru):
    tarih = tarih_bul(soru)
    if "kahvalti" in soru or "sabah" in soru:
        ogun = "kahvalti"
    elif "aksam" in soru:
        ogun = "aksam"
    else:
        ogun = None
    if tarih is None and ogun is None and "ne var" not in soru and "menu" not in soru:
        if tesekkur_mu(soru):
            cevap_gonder(kimden, "Rica ederim, afiyet olsun!")
        else:
            liste_gonder(kimden)
        return
    if tarih is None:
        tarih = bugun()
    yok = menu_yok_mesaji(tarih)
    cevap_gonder(kimden, yok if yok else yemek.menu_metni(tarih, ogun))


def mesaj_isle(veri):
    deger = veri["entry"][0]["changes"][0]["value"]

    if "messages" in deger:
        mesaj = deger["messages"][0]
        if mesaj["id"] in GORULEN:
            return
        GORULEN.append(mesaj["id"])
        kimden = mesaj["from"]
        if hiz_asildi(kimden):
            print("HIZ SINIRI:", kimden)
            return
        kullanici_kaydet(kimden)
        if mesaj["type"] == "text":
            yazi = mesaj["text"]["body"]
            print(kimden, "yazdı:", yazi)
            if sahip_komutu_mu(kimden, yazi):
                return
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