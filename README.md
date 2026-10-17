# KYK Yemek Menüsü WhatsApp Botu

KYK yurdu yemek menüsünü (kahvaltı ve akşam) WhatsApp'tan öğreten bağımsız bir hobi botu. "bugün", "yarın akşam" ya da "25 ekim" yaz, bot o günün menüsünü gönderir. KYK ile bağlantısı yoktur.

## Kullanım

Bota şunlardan birini yazabilirsin, büyük/küçük harf ve Türkçe karakter fark etmez:

| Yazdığın | Cevap |
| --- | --- |
| `bugün`, `yarın`, `dün` | O günün kahvaltı ve akşam menüsü |
| `2 gün sonra`, `öbür gün` | Belirtilen gün sonrasının menüsü |
| `25 ekim`, `25.10`, `25/10` | O tarihin menüsü |
| `kahvaltı`, `akşam` | Sadece o öğün (tek başına yazılırsa bugünün) |
| `yarın akşam`, `25 ekim kahvaltı` | Gün ve öğün birlikte |
| `ne var`, `menü` | Bugünün menüsü |
| `yardım`, `merhaba` | Tıklanabilir seçenek listesi |

## Nasıl çalışır

1. Aylık menü PDF'leri (`kahvalti.pdf`, `aksam.pdf`) `pdfplumber` ile okunur, tablolardaki yemekler tarihlerle eşleştirilir.
2. WhatsApp Cloud API (Meta) gelen her mesajı bir Flask webhook'una iletir.
3. Mesaj normalize edilir (küçük harf, Türkçe karakterler sadeleştirilir), içinden gün, tarih ve öğün bulunur.
4. Bot istenen menüyü hazırlar ve cevabı API üzerinden geri gönderir. Anlaşılmayan mesajlara tıklanabilir bir liste mesajıyla yanıt verir.

Sağlamlık için:

- Aynı mesaj ID'si iki kez gelirse (Meta yeniden denerse) ikinci kez cevaplanmaz.
- İşlem sırasında hata olursa loglanır, webhook yine de başarılı döner; Meta sürekli yeniden denemez.
- "Bugün" ve "yarın" Türkiye saatine (Europe/Istanbul) göre hesaplanır, sunucu saat dilimi fark etmez.
- Metin dışı mesajlara (fotoğraf, ses vb.) kısa bir yönlendirme cevabı gider.

## Kullanılan teknolojiler

- Python, Flask, Gunicorn
- pdfplumber (PDF tablo okuma)
- WhatsApp Cloud API (Meta), liste (interactive) mesajları dahil
- Render üzerinde barındırılıyor, UptimeRobot ile uyanık tutuluyor

## Ayarlar

Gizli bilgiler yerelde `ayarlar.py`'den, sunucuda ortam değişkenlerinden okunur:

- `DOGRULAMA_KELIMESI`: webhook doğrulama kelimesi
- `TOKEN`: WhatsApp API erişim anahtarı
- `TELEFON_ID`: WhatsApp telefon numarası ID'si
- `GROQ_ANAHTARI` (isteğe bağlı): sohbet modu için Groq API anahtarı
- `SAHIP_NUMARASI` (isteğe bağlı): önerilerin iletileceği numara (`905xxxxxxxxx`)
- `SOHBET_NUMARALARI` (isteğe bağlı): sohbet modunu kullanabilecek numaralar, virgülle ayrılmış (`905xxxxxxxxx`)

## Öneri

Kullanıcılar `öneri <mesaj>` yazarak fikir gönderebilir, mesaj sahibine WhatsApp'tan iletilir (kişi başı 5 öneri sınırı). WhatsApp kuralı gereği sahibin son 24 saatte bota mesaj yazmış olması gerekir; iletilemezse öneri loglarda `ONERI:` ile görünür.

## Sohbet modu

Sadece izin verilen numaralar `sohbet` yazarak yapay zeka ile sohbet edebilir (Groq üzerinde `openai/gpt-oss-120b`). `çık` yazınca menü moduna döner. Geçmiş sadece bellekte tutulur. Diğer kullanıcılar için hiçbir şey değişmez.

## Menüyü güncelleme

Yeni ayın `kahvalti.pdf` ve `aksam.pdf` dosyalarını aynı isimlerle değiştirip GitHub'a gönder. Render otomatik yeniden yayınlar.

## Gizlilik

Bot yalnızca gelen mesaja cevap verir. Telefon numarası ve mesaj metni sadece cevap vermek için kullanılır, paylaşılmaz (isteğe bağlı sohbet modunda mesajlar yapay zeka servisine gider). Ayrıntılar: [Gizlilik politikası](https://mtahamurat.github.io/yemek-bot/privacy.html)

## Sınırlar

- Menü sadece PDF'i yüklenmiş aylar için vardır, diğer günler "Menü bulunamadı" der.
- Menü verisi PDF düzeninin aynı kalmasına bağlıdır.
- Ücretsiz sunucu planı kullanıldığı için uzun bir hareketsizlikten sonra ilk cevap birkaç saniye gecikebilir.

---

# KYK Meal Menu WhatsApp Bot

An independent hobby WhatsApp bot that replies with the KYK dormitory meal menu (breakfast and dinner). Send "bugün" (today), "yarın akşam" (tomorrow dinner) or "25 ekim" (October 25) and the bot answers with that day's menu. It is not affiliated with KYK.

## Usage

Send any of these. Case and Turkish characters do not matter:

| You send | Reply |
| --- | --- |
| `bugün`, `yarın`, `dün` | Breakfast and dinner for that day |
| `2 gün sonra`, `öbür gün` | The menu a number of days from now |
| `25 ekim`, `25.10`, `25/10` | The menu for that date |
| `kahvaltı`, `akşam` | Only that meal (today's if sent alone) |
| `yarın akşam`, `25 ekim kahvaltı` | Day and meal combined |
| `ne var`, `menü` | Today's menu |
| `yardım`, `merhaba` | A tappable list of options |

## How it works

1. The monthly menu PDFs (`kahvalti.pdf`, `aksam.pdf`) are parsed with `pdfplumber`, which extracts the tables and maps each dish to its date.
2. The WhatsApp Cloud API (Meta) sends every incoming message to a Flask webhook.
3. The message is normalized (lowercased, Turkish characters simplified) and the day, date and meal are extracted from it.
4. The bot builds the requested menu and sends it back through the API. Unrecognized messages get an interactive list message.

Robustness:

- A message ID that arrives twice (Meta retries) is answered only once.
- Errors during processing are logged and the webhook still returns success, so Meta does not retry endlessly.
- "Today" and "tomorrow" are calculated in Turkish time (Europe/Istanbul), regardless of the server's time zone.
- Non-text messages (photos, audio, etc.) get a short guidance reply.

## Tech stack

- Python, Flask, Gunicorn
- pdfplumber (PDF table extraction)
- WhatsApp Cloud API (Meta), including interactive list messages
- Hosted on Render, kept awake with UptimeRobot

## Configuration

Secrets are read from `ayarlar.py` locally, or from environment variables in production:

- `DOGRULAMA_KELIMESI`: webhook verify token
- `TOKEN`: WhatsApp API access token
- `TELEFON_ID`: WhatsApp phone number ID
- `GROQ_ANAHTARI` (optional): Groq API key for chat mode
- `SAHIP_NUMARASI` (optional): number that receives suggestions (`905xxxxxxxxx`)
- `SOHBET_NUMARALARI` (optional): comma-separated numbers allowed to use chat mode (`905xxxxxxxxx`)

## Suggestions

Users can send ideas with `öneri <message>`; the message is forwarded to the owner on WhatsApp (limit 5 per user). Per WhatsApp rules the owner must have messaged the bot within the last 24 hours; otherwise the suggestion is only visible in the logs as `ONERI:`.

## Chat mode

Only allow-listed numbers can send `sohbet` to chat with an AI (`openai/gpt-oss-120b` on Groq); `çık` returns to menu mode. History is kept in memory only. Nothing changes for other users.

## Updating the menu

Replace `kahvalti.pdf` and `aksam.pdf` with the new month's files (same names) and push to GitHub. Render redeploys automatically.

## Privacy

The bot only replies to incoming messages. The phone number and message text are used solely to reply and are not shared (in the optional chat mode, messages go to the AI provider). Details: [Privacy policy](https://mtahamurat.github.io/yemek-bot/privacy.html)

## Limitations

- Menus exist only for months whose PDFs have been added; other days return "Menü bulunamadı" (menu not found).
- Menu data depends on the PDF layout staying the same.
- On the free hosting plan, the first reply after a long idle period can take a few seconds.
