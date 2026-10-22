import threading
import time
import random
import struct
from pyModbusTCP.server import ModbusServer

HOST = 'localhost'
PORT = 502

# Enderecos
END_TEMP_R = 700
END_TEMP_S = 702
END_TEMP_T = 704
END_TEMP_CARC = 706
END_PRESSAO = 710
END_VAZAO = 712
END_FREQ = 830
END_CORRENTE = 840
END_TENSAO = 847
END_FP = 868
END_SETPOINT = 1302
END_HABILITA = 1328


def float_para_regs(valor):
    # float32 em 2 registradores, word order big (palavra alta primeiro)
    raw = struct.pack('>f', valor)
    return list(struct.unpack('>HH', raw))


def regs_para_float(regs):
    raw = struct.pack('>HH', regs[0], regs[1])
    return struct.unpack('>f', raw)[0]


estado = {
    'temp_r': 65.0,
    'temp_s': 66.0,
    'temp_t': 64.5,
    'temp_carc': 70.0,
    'pressao': 3.5,
    'vazao': 0.0,
    'freq': 60.0,
    'corrente': 12.3,
    'tensao': 380.0,
    'fp': 0.92,
}


def escrever_fp(banco, end, valor, div=1):
    # valor numerico = valor de engenharia * Div
    banco.set_holding_registers(end, float_para_regs(valor * div))


def escrever_int(banco, end, valor, div=1):
    v = int(round(valor * div))
    v = max(0, min(65535, v))
    banco.set_holding_registers(end, [v])


def escrever_medicoes(banco):
    escrever_fp(banco, END_TEMP_R, estado['temp_r'], div=10)
    escrever_fp(banco, END_TEMP_S, estado['temp_s'], div=10)
    escrever_fp(banco, END_TEMP_T, estado['temp_t'], div=10)
    escrever_fp(banco, END_TEMP_CARC, estado['temp_carc'], div=10)
    escrever_fp(banco, END_PRESSAO, estado['pressao'], div=1)
    escrever_fp(banco, END_VAZAO, estado['vazao'], div=1)
    escrever_int(banco, END_FREQ, estado['freq'], div=100)
    escrever_int(banco, END_CORRENTE, estado['corrente'], div=10)
    escrever_int(banco, END_TENSAO, estado['tensao'], div=10)
    escrever_int(banco, END_FP, estado['fp'], div=1000)


def atualizar(banco):
    while True:
        time.sleep(2)

        # comandos do cliente: o servidor so le, nunca sobrescreve
        reg_hab = banco.get_holding_registers(END_HABILITA, 1)
        sp_regs = banco.get_holding_registers(END_SETPOINT, 2)
        if reg_hab is None or sp_regs is None:
            continue

        habilita = (reg_hab[0] >> 6) & 1
        setpoint = regs_para_float(sp_regs)

        if habilita:
            estado['vazao'] += (setpoint - estado['vazao']) * 0.1
            estado['freq'] += random.uniform(-0.1, 0.1)
        # desabilitado: vazao permanece constante

        for k in ['temp_r', 'temp_s', 'temp_t', 'temp_carc']:
            estado[k] += random.uniform(-0.5, 0.5)
        estado['pressao'] += random.uniform(-0.05, 0.05)
        estado['corrente'] += random.uniform(-0.2, 0.2)
        estado['tensao'] += random.uniform(-1.0, 1.0)
        estado['fp'] = max(0.8, min(1.0, estado['fp'] + random.uniform(-0.005, 0.005)))

        escrever_medicoes(banco)


def main():
    servidor = ModbusServer(host=HOST, port=PORT, no_block=True)
    banco = servidor.data_bank

    # Setpoint inicial: 50.0 m3/h e medicoes iniciais
    banco.set_holding_registers(END_SETPOINT, float_para_regs(50.0))
    escrever_medicoes(banco)

    t = threading.Thread(target=atualizar, args=(banco,), daemon=True)
    t.start()

    servidor.start()
    print(f"Servidor Modbus TCP em {HOST}:{PORT} (Ctrl+C para parar)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        servidor.stop()
        print("Servidor parado.")


if __name__ == '__main__':
    main()

# emulacao de bancada de bombeamento