# KYK Yemek Menüsü WhatsApp Botu

KYK yurdu yemek menüsünü (kahvaltı ve akşam) WhatsApp'tan öğreten bir bot. "bugün" veya "yarın" yaz, bot o günün menüsünü gönderir.

## Nasıl çalışır

1. Aylık menü PDF'leri (`kahvalti.pdf`, `aksam.pdf`) `pdfplumber` ile okunur, tablolardaki yemekler tarihlerle eşleştirilir.
2. WhatsApp Cloud API (Meta) gelen her mesajı bir Flask webhook'una iletir.
3. Bot mesajı okur, istenen günün menüsünü bulur ve cevabı API üzerinden geri gönderir.

## Kullanılan teknolojiler

- Python, Flask, Gunicorn
- pdfplumber (PDF tablo okuma)
- WhatsApp Cloud API (Meta)
- Render üzerinde barındırılıyor, UptimeRobot ile uyanık tutuluyor

## Ayarlar

Gizli bilgiler yerelde `ayarlar.py`'den, sunucuda ortam değişkenlerinden okunur:

- `DOGRULAMA_KELIMESI`: webhook doğrulama kelimesi
- `TOKEN`: WhatsApp API erişim anahtarı
- `TELEFON_ID`: WhatsApp telefon numarası ID'si

## Menüyü güncelleme

Yeni ayın `kahvalti.pdf` ve `aksam.pdf` dosyalarını aynı isimlerle değiştirip GitHub'a gönder. Render otomatik yeniden yayınlar.

## Sınırlar

- Meta'nın test numarası kullanıldığı için sadece sınırlı sayıda doğrulanmış kişi kullanabilir.
- Menü verisi PDF düzeninin aynı kalmasına bağlı.

---

# KYK Meal Menu WhatsApp Bot

A WhatsApp bot that replies with the KYK dormitory meal menu (breakfast and dinner). Send "bugün" (today) or "yarın" (tomorrow) and the bot answers with that day's menu.

## How it works

1. The monthly menu PDFs (`kahvalti.pdf`, `aksam.pdf`) are parsed with `pdfplumber`, which extracts the tables and maps each dish to its date.
2. The WhatsApp Cloud API (Meta) sends every incoming message to a Flask webhook.
3. The bot reads the message, looks up the menu for the requested day and sends the reply back through the API.

## Tech stack

- Python, Flask, Gunicorn
- pdfplumber (PDF table extraction)
- WhatsApp Cloud API (Meta)
- Hosted on Render, kept awake with UptimeRobot

## Configuration

Secrets are read from `ayarlar.py` locally, or from environment variables in production:

- `DOGRULAMA_KELIMESI`: webhook verify token
- `TOKEN`: WhatsApp API access token
- `TELEFON_ID`: WhatsApp phone number ID

## Updating the menu

Replace `kahvalti.pdf` and `aksam.pdf` with the new month's files (same names) and push to GitHub. Render redeploys automatically.

## Limitations

- Uses Meta's test number, so only a limited number of verified recipients can use it.
- Menu data depends on the PDF layout staying the same.