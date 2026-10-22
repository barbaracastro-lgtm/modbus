import threading
import time
import random
import struct
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

HOST = 'localhost'
PORT = 502

# Enderecos
END_TEMP_R     = 700
END_TEMP_S     = 702
END_TEMP_T     = 704
END_TEMP_CARC  = 706
END_PRESSAO    = 710
END_VAZAO      = 712
END_FREQ       = 830
END_CORRENTE   = 840
END_TENSAO     = 847
END_FP         = 868
END_SETPOINT   = 1302
END_HABILITA   = 1328

def float_para_regs(valor):
    raw = struct.pack('>f', valor)
    hi = struct.unpack('>H', raw[0:2])[0]
    lo = struct.unpack('>H', raw[2:4])[0]
    return [hi, lo]

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

def atualizar(ctx):
    bloco = ctx[0].store['h']
    while True:
        time.sleep(2)
        regs = bloco.getValues(1, 2000)

        hi = regs[END_HABILITA - 1]
        habilita = (hi >> 6) & 1

        sp_regs = [regs[END_SETPOINT - 1], regs[END_SETPOINT]]
        setpoint = regs_para_float(sp_regs)

        if habilita:
            estado['vazao'] += (setpoint - estado['vazao']) * 0.1
            estado['freq'] += random.uniform(-0.1, 0.1)
        else:
            estado['vazao'] = estado['vazao']

        for k in ['temp_r', 'temp_s', 'temp_t', 'temp_carc']:
            estado[k] += random.uniform(-0.5, 0.5)
        estado['pressao'] += random.uniform(-0.05, 0.05)
        estado['corrente'] += random.uniform(-0.2, 0.2)
        estado['tensao'] += random.uniform(-1.0, 1.0)
        estado['fp'] += random.uniform(-0.005, 0.005)

        def escrever_fp(end, valor, div=1):
            v = valor * div
            r = float_para_regs(v)
            bloco.setValues(end, r)

        def escrever_int(end, valor, div=1):
            v = int(round(valor * div))
            v = max(0, min(65535, v))
            bloco.setValues(end, [v])

        escrever_fp(END_TEMP_R,    estado['temp_r'],    div=10)
        escrever_fp(END_TEMP_S,    estado['temp_s'],    div=10)
        escrever_fp(END_TEMP_T,    estado['temp_t'],    div=10)
        escrever_fp(END_TEMP_CARC, estado['temp_carc'], div=10)
        escrever_fp(END_PRESSAO,   estado['pressao'],   div=1)
        escrever_fp(END_VAZAO,     estado['vazao'],     div=1)
        escrever_int(END_FREQ,     estado['freq'],      div=100)
        escrever_int(END_CORRENTE, estado['corrente'],  div=10)
        escrever_int(END_TENSAO,   estado['tensao'],    div=10)
        escrever_int(END_FP,       estado['fp'],        div=1000)

def main():
    bloco = ModbusSequentialDataBlock(1, [0] * 2000)
    ctx_escravo = ModbusSlaveContext(hr=bloco)
    ctx = ModbusServerContext(slaves=ctx_escravo, single=True)

    # Setpoint inicial: 50.0 m3/h
    sp = float_para_regs(50.0)
    bloco.setValues(END_SETPOINT, sp)

    t = threading.Thread(target=atualizar, args=(ctx,), daemon=True)
    t.start()

    print(f"Servidor Modbus TCP em {HOST}:{PORT}")
    StartTcpServer(context=ctx, address=(HOST, PORT))

if __name__ == '__main__':
    main()
# emulacao de bancada de bombeamento