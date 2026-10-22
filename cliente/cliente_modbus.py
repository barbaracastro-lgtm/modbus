import struct
from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian

HOST = 'localhost'
PORT = 502

class ClienteModbus:
    def __init__(self, host=HOST, port=PORT):
        self.client = ModbusTcpClient(host, port=port)

    def conectar(self):
        ok = self.client.connect()
        if not ok:
            raise ConnectionError(f"Nao foi possivel conectar em {HOST}:{PORT}")
        print(f"Conectado em {HOST}:{PORT}")

    def desconectar(self):
        self.client.close()
        print("Desconectado.")

    def ler_float(self, endereco, div=1):
        r = self.client.read_holding_registers(endereco, count=2)
        if r.isError():
            raise RuntimeError(f"Erro ao ler float em {endereco}: {r}")
        decoder = BinaryPayloadDecoder.fromRegisters(
            r.registers, byteorder=Endian.BIG, wordorder=Endian.BIG
        )
        valor_raw = decoder.decode_32bit_float()
        return valor_raw / div

    def escrever_float(self, endereco, valor, div=1):
        valor_raw = valor * div
        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
        builder.add_32bit_float(valor_raw)
        regs = builder.to_registers()
        r = self.client.write_registers(endereco, regs)
        if r.isError():
            raise RuntimeError(f"Erro ao escrever float em {endereco}: {r}")

    def ler_registrador(self, endereco):
        r = self.client.read_holding_registers(endereco, count=1)
        if r.isError():
            raise RuntimeError(f"Erro ao ler registrador em {endereco}: {r}")
        return r.registers[0]

    def escrever_registrador(self, endereco, valor):
        r = self.client.write_register(endereco, valor)
        if r.isError():
            raise RuntimeError(f"Erro ao escrever registrador em {endereco}: {r}")

    def ler_bits(self, endereco):
        valor = self.ler_registrador(endereco)
        bits = []
        for i in range(16):
            bits.append((valor >> i) & 1)
        return bits

    def escrever_bit(self, endereco, bit, valor_bit):
        if bit < 0 or bit > 15:
            raise ValueError("Bit deve ser entre 0 e 15")
        if valor_bit not in (0, 1):
            raise ValueError("Valor do bit deve ser 0 ou 1")
        reg = self.ler_registrador(endereco)
        if valor_bit == 1:
            reg = reg | (1 << bit)
        else:
            reg = reg & ~(1 << bit)
        self.escrever_registrador(endereco, reg)
        return reg


if __name__ == '__main__':
    c = ClienteModbus()
    c.conectar()

    print("\n--- Leitura dos 10 dados do CLP ---")
    dados = [
        ('temp_r',    700, 'FP', 10,   'C'),
        ('temp_s',    702, 'FP', 10,   'C'),
        ('temp_t',    704, 'FP', 10,   'C'),
        ('temp_carc', 706, 'FP', 10,   'C'),
        ('pressao',   710, 'FP', 1,    'bar'),
        ('vazao',     712, 'FP', 1,    'm3/h'),
        ('freq',      830, '4X', 100,  'Hz'),
        ('corrente',  840, '4X', 10,   'A'),
        ('tensao',    847, '4X', 10,   'V'),
        ('fp',        868, '4X', 1000, ''),
    ]
    for tag, end, tipo, div, unidade in dados:
        if tipo == 'FP':
            v = c.ler_float(end, div=div)
        else:
            raw = c.ler_registrador(end)
            v = raw / div
            print(f"  [escala] {tag}: raw={raw}, Div={div}, m={1/div}, eng={v:.3f} {unidade}")
            continue
        print(f"  {tag}: {v:.3f} {unidade}")

    print("\n--- Escrita e leitura de float (setpoint) ---")
    sp_enviar = 75.5
    c.escrever_float(1302, sp_enviar, div=1)
    sp_lido = c.ler_float(1302, div=1)
    print(f"  Setpoint enviado: {sp_enviar}")
    print(f"  Setpoint lido:    {sp_lido:.4f}")

    print("\n--- Bits do registrador 1328 (habilita) ---")
    bits = c.ler_bits(1328)
    for i, b in enumerate(bits):
        print(f"  bit {i:2d}: {b}")

    print("\n--- Escrita do bit 6 (habilitar motor) ---")
    print(f"  Antes: reg={c.ler_registrador(1328):016b}")
    c.escrever_bit(1328, 6, 1)
    print(f"  Depois (bit 6 = 1): reg={c.ler_registrador(1328):016b}")
    c.escrever_bit(1328, 6, 0)
    print(f"  Depois (bit 6 = 0): reg={c.ler_registrador(1328):016b}")

    c.desconectar()