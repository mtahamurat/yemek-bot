import re
from datetime import date, datetime, timedelta

import pdfplumber


def menu_oku(dosya):
    """PDF'i okur, {tarih: [yemekler]} sözlüğü döndürür."""
    menu = {}

    with pdfplumber.open(dosya) as pdf:
        tablo = pdf.pages[0].extract_tables()[0]

    tarih_sutunlari = {}  # {sutun_no: tarih}

    for satir in tablo:
        # 1) Bu satırda tarih var mı?
        tarihler = {}
        for sutun, hucre in enumerate(satir):
            if hucre and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", hucre):
                tarihler[sutun] = datetime.strptime(hucre, "%m/%d/%Y").date()

        if tarihler:  # evet: yeni hafta başladı
            tarih_sutunlari = tarihler
            for t in tarihler.values():
                menu[t] = []
            continue

        # 2) Boş satır: hafta bitti
        if not any(satir):
            tarih_sutunlari = {}
            continue

        # 3) Yemek satırı: her tarihin sütunundaki yemeği ekle
        for sutun, t in tarih_sutunlari.items():
            yemek = satir[sutun]
            if yemek:
                menu[t].append(yemek.replace("\n", ", ").replace("*", "").strip())

    return menu


kahvalti = menu_oku("kahvalti.pdf")
aksam = menu_oku("aksam.pdf")


def goster(gun):
    print()
    print(gun.strftime("%d.%m.%Y"))
    print("KAHVALTI:")
    for yemek in kahvalti.get(gun, ["Menü bulunamadı"]):
        print(" -", yemek)
    print("AKSAM:")
    for yemek in aksam.get(gun, ["Menü bulunamadı"]):
        print(" -", yemek)
    print()

def menu_metni(gun, ogun=None):
    satirlar = [gun.strftime("%d.%m.%Y")]
    if ogun is None or ogun == "kahvalti":
        satirlar.append("")
        satirlar.append("KAHVALTI:")
        for yemek in kahvalti.get(gun, ["Menü bulunamadı"]):
            satirlar.append("- " + yemek)
    if ogun is None or ogun == "aksam":
        satirlar.append("")
        satirlar.append("AKŞAM:")
        for yemek in aksam.get(gun, ["Menü bulunamadı"]):
            satirlar.append("- " + yemek)
    return "\n".join(satirlar)

if __name__ == "__main__":
    while True:
        soru = input("bugün / yarın / çık: ").strip().lower()
        if soru in ("bugün", "bugun"):
            goster(date.today())
        elif soru in ("yarın", "yarin"):
            goster(date.today() + timedelta(days=1))
        elif soru in ("çık", "cik"):
            break
        else:
            print("Anlamadım.")