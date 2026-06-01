# 🌡️ RPi3 SHT31D Endüstriyel IoT Hava İstasyonu

Bu proje, Raspberry Pi 3 ve yüksek hassasiyetli Adafruit SHT31D sensörü kullanılarak geliştirilmiş, 7/24 kesintisiz çalışmak üzere tasarlanmış endüstriyel düzeyde bir IoT veri toplama ve izleme sistemidir. Sistem; donanım, ağ ve yazılım katmanlarında tam otonom hata yönetimi yaparken, verileri InfluxDB'ye kaydeder ve "E-Mürekkep (E-Ink) / Gazete Kağıdı" temalı özel bir web arayüzü ile anlık olarak sunar.

## ✨ Öne Çıkan Özellikler

* 
**🛡️ Kırılmaz Veri Akışı (Fail-Safe):** I2C hattındaki elektriksel parazitlere, Wi-Fi kopmalarına ve InfluxDB sunucu kesintilerine karşı anında toparlanan try-except zırhı ve ZeroDivisionError koruması.


* 
**⏱️ Sıfır Zaman Kayması (Drift Compensation):** Döngü sürelerindeki gecikmeleri dinamik olarak hesaplayarak InfluxDB'ye saniyesi saniyesine tutarlı zaman serisi verisi gönderimi.


* 
**🔥 Akıllı Isıtıcı Yönetimi:** Sensör üzerindeki yoğuşmayı önlemek için dahili ısıtıcının periyodik döngülerle çalıştırılması ve veri manipülasyonunu önlemek adına bu durumun (AÇIK/KAPALI) veritabanına kaydedilmesi.


* 
**🌡️ Isı İndeksi (Heat Index):** ABD Ulusal Hava Durumu Servisi (NWS) regresyon formülü kullanılarak hesaplanan, ekstrem koşullara göre hassaslaştırılmış hissedilen sıcaklık. Model şu denkleme dayanır:



$$HI = c_1 + c_2T + c_3R + c_4TR + c_5T^2 + c_6R^2 + c_7T^2R + c_8TR^2 + c_9T^2R^2$$


* 
**📟 E-Mürekkep (E-Ink) Web Arayüzü:** Dijital ekran yorgunluğunu önleyen, fiziksel gazete kağıdı dokusuna (fractalNoise SVG) ve sıcak gri tonlara sahip retro-endüstriyel arayüz. Server-Sent Events (SSE) ile sayfa yenilemeden saniyelik veri akışı sağlar.


* 
**📱 WhatsApp Alarm Sistemi:** Sıcaklık belirlenen eşiği (örn: 23.0°C) aştığında CallMeBot API üzerinden anında WhatsApp bildirimi.


* 
**⚙️ Otonom Servis Yönetimi:** Elektrik kesintilerinde veya cihaz yeniden başlatıldığında sistemi tam otonom olarak ayağa kaldıran, kaynak sızıntılarını önleyen systemd entegrasyonu.



---

## 🛠️ Kullanılan Teknolojiler

* 
**Donanım:** Raspberry Pi 3, Adafruit SHT31D (I2C) 


* 
**Dil & Kütüphaneler:** Python 3, Flask, Gunicorn, Gevent, Adafruit-Blinka, python-dotenv 


* 
**Veritabanı & Görselleştirme:** InfluxDB v2, Grafana 


* 
**Altyapı:** Systemd, Journalctl, Server-Sent Events (SSE) 



---

## 📂 Proje Yapısı

* 
**`app.py` (Sensör Servisi):** Sensörden veri okur, anlık sapmaları filtreler, ısı indeksini hesaplar ve senkron olarak InfluxDB'ye veri gönderir.


* 
**`webui.py` (Web Servisi):** Arka plandaki `app.py` loglarını `journalctl` üzerinden dinleyip SSE teknolojisi ile Flask ve Gunicorn üzerinden web arayüzüne basar. Ayrıca WhatsApp bildirimlerini yönetir.


* 
**`influxdb.service` & `webui.service`:** Otonom çalışma, yetki denetimi ve hızlı kapanma (`TimeoutStopSec=5`) özellikleri barındıran Linux arka plan servisi dosyaları.



---

## 🚀 Kurulum

### 1. Gerekli Kütüphanelerin Yüklenmesi

Raspberry Pi üzerinde (tercihen sanal ortamda veya kullanıcı dizininde) gerekli bağımlılıkları kurun:

```bash
pip install adafruit-circuitpython-sht31d influxdb-client python-dotenv flask gunicorn gevent

```

### 2. Ortam Değişkenleri (.env)

Proje dizininde güvenliğiniz için bir `.env` dosyası oluşturun ve API/Token bilgilerinizi ekleyin:

```ini
INFLUX_TOKEN=sizin_influx_token_degeriniz
WA_PHONE=905551234567
WA_APIKEY=sizin_callmebot_api_anahtariniz

```

(Not: `app.py` ve `webui.py` dosyaları bu değişkenler olmadan çalışmayı reddederek "Fail-Fast" prensibiyle çökecek şekilde tasarlanmıştır.)

### 3. Systemd Servislerinin Kurulumu

`.service` uzantılı dosyaları `/etc/systemd/system/` dizinine kopyalayın. Ardından servisleri Linux'a tanıtın, etkinleştirin ve başlatın:

```bash
sudo systemctl daemon-reload
sudo systemctl enable influxdb.service webui.service
sudo systemctl start influxdb.service webui.service

```

### 4. Grafana Optimizasyonu (İsteğe Bağlı)

Eğer verileri Grafana üzerinden görselleştiriyorsanız, yüksek performans ve mobil uyumluluk için şu adımları izlemeniz tavsiye edilir:

* 
**Dinamik Zaman Serileri:** Flux sorgularınızda `every: 1m` yerine `v.windowPeriod` kullanarak veri yükünü hafifletin.


* 
**Isıtıcı Durumu:** Isıtıcının çalıştığı anlardaki sıcaklık sıçramalarını anlamlandırabilmek için "State Timeline" paneli ekleyerek `heater` durumunu yeşil/kırmızı izleyin.

<img width="974" height="565" alt="image" src="https://github.com/user-attachments/assets/3a481a98-7fdf-450a-951d-df7c62341f98" />
