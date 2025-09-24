# Digital Communication UMNG
# jose.rugeles@unimilitar.edu.co
# OLED I2C Menu - Raspberry Pi Pico

# oled_menu_i2c_chunked_subclass.py — MicroPython (Raspberry Pi Pico / Pico W)
# OLED SSD1306 por I2C1: SCL=GP15, SDA=GP14
# Hardware: pull-ups externos 4.7k–10k to 3V3 for SDA/SCL.

from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import time, sys

# ---------- Config ----------
BUS_ID   = 0
PIN_SCL  = 13
PIN_SDA  = 12
FREQ     = 50_000       # 50 kHz: cómodo para analizador lógico (sube a 100k/400k si todo va bien)
CHUNK    = 16           # tamaño de trozo para write_data (8/16/32 suelen ir bien)
PAUSE_US = 0            # micro-pausa entre trozos (0..100). Si hay errores, prueba 50.

CUR_FREQ = FREQ         # espejo de la frecuencia actual (algunos puertos no exponen i2c.freq())

# ---------- Subclase que trocea write_data ----------
class ChunkedSSD1306_I2C(SSD1306_I2C):
    def write_data(self, buf):
        # Enviar en una sola transacción: 0x40 (control byte de datos) + trozo.
        mv = memoryview(buf)
        for i in range(0, len(mv), CHUNK):
            part = bytes(mv[i:i+CHUNK])           # conversion explícita evita problemas con memoryview
            # Una sola transacción con el control byte al frente (SSD1306 lo espera así):
            self.i2c.writeto(self.addr, b'\x40' + part)
            if PAUSE_US:
                time.sleep_us(PAUSE_US)

# ---------- I2C + escaneo ----------
i2c = I2C(BUS_ID, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=FREQ)
addrs = i2c.scan()
print("I2C scan:", [hex(a) for a in addrs])
if not addrs:
    raise SystemExit("No hay dispositivos I2C. Revisa SCL=GP15, SDA=GP14, 3V3 y GND, y pull-ups en SDA/SCL.")
ADDR = 0x3C if 0x3C in addrs else (0x3D if 0x3D in addrs else addrs[0])
print("Usando OLED en addr:", hex(ADDR))

# ---------- Instanciar OLED usando la subclase (chunked) ----------
# Intento primero 128x32 y si falla pruebo 128x64.
try:
    oled = ChunkedSSD1306_I2C(128, 32, i2c, addr=ADDR)
except Exception:
    oled = ChunkedSSD1306_I2C(128, 64, i2c, addr=ADDR)

# ---------- Helpers RAW (útiles para el analizador) ----------
def send_cmd_raw(cmd):
    # 0x80 => Co=1, D/C#=0 (comando)
    i2c.writeto(ADDR, bytes([0x80, cmd & 0xFF]))
    time.sleep_ms(2)

def send_data_raw(db):
    # 0x40 => Co=0, D/C#=1 (dato)
    i2c.writeto(ADDR, bytes([0x40, db & 0xFF]))
    time.sleep_ms(2)

# ---------- Acciones del menú ----------
def act_poweroff():
    send_cmd_raw(0xAE)     # Display OFF
    print("-> OFF (0xAE)")

def act_poweron():
    send_cmd_raw(0xAF)     # Display ON
    print("-> ON (0xAF)")

def act_contrast():
    try:
        v = int(input("Contraste (0-255): "))
        if not 0 <= v <= 255:
            raise ValueError
    except:
        print("Valor inválido.")
        return
    send_cmd_raw(0x81)     # SET_CONTRAST
    send_cmd_raw(v)
    print(f"-> CONTRASTE = {v}")

def act_invert():
    try:
        v = int(input("Invertir? 1=ON / 0=OFF: "))
        if v not in (0, 1):
            raise ValueError
    except:
        print("Valor inválido.")
        return
    send_cmd_raw(0xA7 if v else 0xA6)
    print("-> INVERT =", v)

def act_clear():
    try:
        oled.fill(0)
        oled.show()
        print("-> CLEAR (buffer a 0 y show con chunking)")
    except Exception as e:
        print("Error al limpiar/mostrar:", e)

def act_text_demo():
    try:
        oled.fill(0)
        oled.text("I2C MENU", 0, 0)
        oled.text("Addr " + hex(ADDR), 0, 10)
        y = 22 if oled.height >= 32 else 16
        oled.text("Hola UMNG!", 0, y)
        oled.show()
        print("-> Texto enviado (ver ráfagas 0x40 + datos)")
    except Exception as e:
        print("Error en texto demo:", e)

def act_anim():
    print("Animando 3 s a baja velocidad...")
    t_end = time.ticks_add(time.ticks_ms(), 3000)
    x = 0
    while time.ticks_diff(t_end, time.ticks_ms()) > 0:
        try:
            oled.fill(0)
            oled.text("ANIM", 0, 0)
            oled.fill_rect(x, oled.height - 10, 20, 8, 1)
            oled.show()
            x = (x + 6) % oled.width
            time.sleep_ms(120)
        except Exception as e:
            print("Error en animación:", e)
            break
    print("-> Fin animación")

def act_cmd_raw():
    s = input("Comando hex (ej. AE para OFF): ").strip()
    try:
        val = int(s, 16) & 0xFF
    except:
        print("Hex inválido.")
        return
    send_cmd_raw(val)
    print(f"-> CMD RAW 0x{val:02X}")

def act_data_raw():
    s = input("Dato hex (ej. 7E): ").strip()
    try:
        val = int(s, 16) & 0xFF
    except:
        print("Hex inválido.")
        return
    send_data_raw(val)
    print(f"-> DATA RAW 0x{val:02X} (columna/píxeles)")

def act_freq():
    global i2c, oled, CUR_FREQ
    try:
        f = int(input("Frecuencia I2C (Hz, p.ej. 50000, 100000, 400000): ").strip())
        if f < 1000:
            raise ValueError
    except:
        print("Valor inválido.")
        return

    # Re-crear I2C y OLED (subclase) con la nueva frecuencia:
    try:
        i2c = I2C(BUS_ID, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=f)
        CUR_FREQ = f
    except Exception as e:
        print("No se pudo reconfigurar I2C:", e)
        return

    try:
        oled_tmp = ChunkedSSD1306_I2C(oled.width, oled.height, i2c, addr=ADDR)
    except Exception:
        # Si no conocemos alto correcto, probar ambas alturas comunes.
        try:
            oled_tmp = ChunkedSSD1306_I2C(128, 32, i2c, addr=ADDR)
        except Exception:
            oled_tmp = ChunkedSSD1306_I2C(128, 64, i2c, addr=ADDR)
    oled = oled_tmp
    print(f"-> Frecuencia I2C ajustada a {f} Hz")

# ---------- Menú ----------
MENU = {
    "1": ("Apagar (0xAE)",           act_poweroff),
    "2": ("Encender (0xAF)",         act_poweron),
    "3": ("Contraste (0-255)",       act_contrast),
    "4": ("Invertir 1/0",            act_invert),
    "5": ("Limpiar",                 act_clear),
    "6": ("Texto demo",              act_text_demo),
    "7": ("Animación breve",         act_anim),
    "8": ("Enviar COMANDO RAW",      act_cmd_raw),
    "9": ("Enviar DATO RAW",         act_data_raw),
    "F": ("Cambiar frecuencia I2C",  act_freq),
    "0": ("Salir",                   None),
}

def print_menu():
    print("\n=== MENU OLED I2C (freq={} Hz, {}x{}) ===".format(CUR_FREQ, oled.width, oled.height))
    for k in ["1","2","3","4","5","6","7","8","9","F","0"]:
        print(f"{k}. {MENU[k][0]}")
    print("> ", end="")

# Mensaje inicial (prueba de show con chunking)
try:
    act_text_demo()
except Exception as e:
    print("Aviso: show inicial falló:", e)

# Loop del menú
while True:
    try:
        print_menu()
        opt = input().strip().upper()
    except (KeyboardInterrupt, EOFError):
        print("\nSaliendo.")
        break

    if opt == "0":
        print("Bye.")
        break

    action = MENU.get(opt, (None, None))[1]
    if action:
        try:
            action()
        except Exception as e:
            print("Error:", e)
    else:
        print("Opción inválida.")