# Digital Communication UMNG
# jose.rugeles@unimilitar.edu.co
# Ping I2C - Raspberry Pi Pico


import machine, time

i2c  = machine.I2C(1, scl=machine.Pin(15), sda=machine.Pin(14), freq=100000)
ADDR = 0x3C

time.sleep_ms(1000)  # tiempo para armar el analizador

print("Probing 0x3c ...")
try:
    # (addr, buffer, stop) -> sin keywords
    i2c.writeto(ADDR, b"", True)   # START, 0x3C(W), ACK, STOP
    print("ACK de 0x3c")
except OSError as e:
    print("NACK / no responde:", e)
    # Si tu firmware no permite buffer vacío, descomenta la siguiente línea:
    # i2c.writeto(ADDR, b"\x00", True)  # verás 0x3C(W), ACK, 0x00, ACK, STOP
