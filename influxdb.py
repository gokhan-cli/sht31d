import board
import adafruit_sht31d
import time
import math
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

load_dotenv()
# INFLUX_URL = INFLUXDB nin kurulu olduğu ip adresini yazıyorum.
INFLUX_URL = "http://192.168.9.5:8086"
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")

if not INFLUX_TOKEN:
    raise ValueError("KRİTİK HATA: INFLUX_TOKEN .env dosyasında bulunamadı!")
# BUCKET = verilerin aktarılacağı yeri belirtiyorum.
ORG = "IOT"
BUCKET = "sensordata"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

try:
    # I2C bağlantısını başlat
    i2c = board.I2C()
    # SHT31D sensör nesnesini oluştur
    sensor = adafruit_sht31d.SHT31D(i2c)
except Exception as e:
    raise RuntimeError(f"Sensör başlatılamadı: {e}")

HEATER_CYCLE = 10
loop_counter = 0
heater_status = 0

def get_avg_readings(sensor, samples=10, delay=0.05):
    temps = []
    hums = []
    for _ in range(samples):
        try:
            temps.append(sensor.temperature)
            hums.append(sensor.relative_humidity)
        except Exception:
            pass
        time.sleep(delay)

    if len(temps) > 2 and len(hums) > 2:
        avg_temp = sum(sorted(temps)[1:-1]) / (len(temps) - 2)
        avg_hum  = sum(sorted(hums)[1:-1])  / (len(hums)  - 2)
        return avg_temp, avg_hum
    elif len(temps) > 0 and len(hums) > 0:
        return sum(temps) / len(temps), sum(hums) / len(hums)

    return None, None

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read()) / 1000.0
    except Exception as e:
        print(f"CPU sıcaklığı okunamadı: {e}")
        return None

def calculate_heat_index_accurate(T_celsius, RH):
    T_f = T_celsius * 9 / 5 + 32

    if T_f < 80:
        return T_celsius

    HI = (-42.379 +
          2.04901523  * T_f +
          10.14333127 * RH -
          0.22475541  * T_f * RH -
          0.00683783  * T_f**2 -
          0.05481717  * RH**2 +
          0.00122874  * T_f**2 * RH +
          0.00085282  * T_f  * RH**2 -
          0.00000199  * T_f**2 * RH**2)

    if RH < 13 and 80 <= T_f <= 112:
        HI -= ((13 - RH) / 4) * math.sqrt((17 - abs(T_f - 95)) / 17)
    elif RH > 85 and 80 <= T_f <= 87:
        HI += ((RH - 85) / 10) * ((87 - T_f) / 5)

    return (HI - 32) * 5 / 9

# --- Ana Döngü ---
try:
    while True:
        loop_start = time.time()
        heat_index = 0.0

        avg_temp, avg_hum = get_avg_readings(sensor)
        cpu_temp = get_cpu_temp()

        if avg_temp is not None:
            heat_index = calculate_heat_index_accurate(avg_temp, avg_hum)
            cpu_str = f"{cpu_temp:.2f} °C" if cpu_temp is not None else "N/A"
            print(f"{datetime.now()} | Temp: {avg_temp:.2f} °C | Hum: {avg_hum:.2f} % | HI: {heat_index:.2f} °C | CPU: {cpu_str} | HS: {heater_status}")

            point = (
                Point("environment")
                .tag("device", "iot-rpi3")
                .field("temperature", avg_temp)
                .field("humidity", avg_hum)
                .field("heat_index", heat_index)
                .field("cpu_temp", cpu_temp if cpu_temp else 0)
                .field("heater", heater_status)
            )
            try:
                write_api.write(bucket=BUCKET, org=ORG, record=point)
                print("Veriler InfluxDB'ye gönderildi.")
            except Exception as e:
                print(f"UYARI: InfluxDB bağlantı hatası! Hata: {e}")
        else:
            print("Veri gönderilmedi: Geçerli ölçüm yok.")

        # Isıtıcı döngüsü kontrolü
        if loop_counter >= HEATER_CYCLE:
            try:
                print("Isıtıcı AÇIK")
                sensor.heater = True
                heater_status = 1

                point_on = (
                    Point("environment")
                    .tag("device", "iot-rpi3")
                    .field("temperature", avg_temp if avg_temp is not None else 0)
                    .field("humidity",    avg_hum  if avg_hum  is not None else 0)
                    .field("heat_index",  heat_index)
                    .field("cpu_temp",    cpu_temp if cpu_temp else 0)
                    .field("heater",      heater_status)
                )
                try:
                    write_api.write(bucket=BUCKET, org=ORG, record=point_on)
                    print("Isıtıcı AÇIK verisi InfluxDB'ye gönderildi.")
                except Exception as e:
                    print(f"UYARI: InfluxDB hatası (Isıtıcı AÇIK)! Hata: {e}")

                time.sleep(1)

                sensor.heater = False
                heater_status = 0
                print("Isıtıcı KAPALI")

                point_off = (
                    Point("environment")
                    .tag("device", "iot-rpi3")
                    .field("temperature", avg_temp if avg_temp is not None else 0)
                    .field("humidity",    avg_hum  if avg_hum  is not None else 0)
                    .field("heat_index",  heat_index)
                    .field("cpu_temp",    cpu_temp if cpu_temp else 0)
                    .field("heater",      heater_status)
                )
                try:
                    write_api.write(bucket=BUCKET, org=ORG, record=point_off)
                    print("Isıtıcı KAPALI verisi InfluxDB'ye gönderildi.")
                except Exception as e:
                    print(f"UYARI: InfluxDB hatası (Isıtıcı KAPALI)! Hata: {e}")

                loop_counter = 0  # ✅ Başarılı tamamlanmada sıfırla

            except Exception as e:
                print(f"Isıtıcı donanım kontrol hatası: {e}")
                loop_counter = 0  # ✅ Hata durumunda da sıfırla

        loop_counter += 1
        time.sleep(max(0, 2.0 - (time.time() - loop_start)))

except KeyboardInterrupt:
    print("\nProgram durduruluyor...")
finally:
    client.close()
    print("InfluxDB bağlantısı güvenli bir şekilde kapatıldı.")
