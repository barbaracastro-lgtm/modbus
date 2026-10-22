from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

HOST = 'localhost'
PORT = 502
WORD_ORDER = 'big'  # palavra alta primeiro, igual ao servidor


class ClienteModbus:
    """Comunicacao Modbus TCP: conexao, leitura, escrita e conversoes."""

    def __init__(self, host=HOST, port=PORT, device_id=1, word_order=WORD_ORDER):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.word_order = word_order
        self.client = ModbusTcpClient(host, port=port)

    # ---------- conexao ----------
    def conectar(self):
        if not self.client.connect():
            raise ConnectionError(f"Nao foi possivel conectar em {self.host}:{self.port}")

    def desconectar(self):
        self.client.close()

    # ---------- registradores brutos ----------
    def ler_registradores(self, endereco, quantidade=1):
        try:
            r = self.client.read_holding_registers(
                endereco, count=quantidade, device_id=self.device_id)
        except ModbusException as e:
            raise RuntimeError(f"Falha de comunicacao ao ler {endereco}: {e}")
        if r.isError():
            raise RuntimeError(f"Erro ao ler {endereco}: {r}")
        return list(r.registers)

    def escrever_registradores(self, endereco, valores):
        try:
            r = self.client.write_registers(
                endereco, valores, device_id=self.device_id)
        except ModbusException as e:
            raise RuntimeError(f"Falha de comunicacao ao escrever {endereco}: {e}")
        if r.isError():
            raise RuntimeError(f"Erro ao escrever {endereco}: {r}")

    def ler_registrador(self, endereco):
        return self.ler_registradores(endereco, 1)[0]

    def escrever_registrador(self, endereco, valor):
        if not 0 <= valor <= 65535:
            raise ValueError("Valor fora do intervalo de 16 bits (0 a 65535)")
        self.escrever_registradores(endereco, [valor])

    # ---------- inteiro com escala ----------
    def ler_inteiro(self, endereco, div=1):
        """Retorna valor de engenharia = valor recebido / Div."""
        return self.ler_registrador(endereco) / div

    def escrever_inteiro(self, endereco, valor_eng, div=1):
        """Envia valor de engenharia * Div, arredondado."""
        self.escrever_registrador(endereco, int(round(valor_eng * div)))

    # ---------- float32 em 2 registradores ----------
    def ler_float(self, endereco, div=1):
        """Decodifica float32 primeiro, depois aplica a escala."""
        regs = self.ler_registradores(endereco, 2)
        valor = self.client.convert_from_registers(
            regs, ModbusTcpClient.DATATYPE.FLOAT32, word_order=self.word_order)
        return valor / div

    def escrever_float(self, endereco, valor_eng, div=1):
        """Aplica a escala primeiro, depois converte para registradores."""
        regs = self.client.convert_to_registers(
            valor_eng * div, ModbusTcpClient.DATATYPE.FLOAT32,
            word_order=self.word_order)
        self.escrever_registradores(endereco, regs)

    # ---------- bits ----------
    def ler_bits(self, endereco):
        """Lista de 16 bits: indice 0 = menos significativo."""
        valor = self.ler_registrador(endereco)
        return [(valor >> i) & 1 for i in range(16)]

    def escrever_bit(self, endereco, bit, valor_bit):
        if not 0 <= bit <= 15:
            raise ValueError("Bit deve ser entre 0 e 15")
        if valor_bit not in (0, 1):
            raise ValueError("Valor do bit deve ser 0 ou 1")
        reg = self.ler_registrador(endereco)
        if valor_bit == 1:
            reg |= (1 << bit)
        else:
            reg &= ~(1 << bit)
        self.escrever_registrador(endereco, reg)
        return reg


# Mapa: (tag, endereco, tipo, Div, unidade)
MAPA = [
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


def ler_mapa(c):
    for tag, end, tipo, div, un in MAPA:
        v = c.ler_float(end, div) if tipo == 'FP' else c.ler_inteiro(end, div)
        print(f"  {tag:10s} (end {end:4d}) = {v:10.3f} {un}")


if __name__ == '__main__':
    import math
    import time

    c = ClienteModbus()
    c.conectar()
    print(f"Conectado em {c.host}:{c.port}")
    try:
        print("\n=== 1. Leitura dos 10 dados, em dois instantes ===")
        print("-- instante 1")
        ler_mapa(c)
        time.sleep(3)
        print("-- instante 2")
        ler_mapa(c)

        print("\n=== 2. Escala (inteiro com Div diferente de 1) ===")
        raw = c.ler_registrador(830)
        div = 100
        print(f"  freq: recebido={raw}, Div={div}, m={1/div}, "
              f"eng={raw/div:.2f} Hz")

        print("\n=== 3. Float: escrita e leitura do setpoint (1302) ===")
        sp = 62.37
        c.escrever_float(1302, sp, div=1)
        regs = c.ler_registradores(1302, 2)
        lido = c.ler_float(1302, div=1)
        print(f"  enviado={sp}  registradores={regs}  lido={lido:.4f}")
        print(f"  iguais (tolerancia float32): "
              f"{math.isclose(sp, lido, rel_tol=1e-6)}")

        print("\n=== 4. Bits do registrador 1328 ===")
        c.escrever_registrador(1328, 0b0000000000100101)  # bits 0, 2 e 5 ativos
        print(f"  inicial:       {c.ler_registrador(1328):016b}")
        for i, b in enumerate(c.ler_bits(1328)):
            print(f"    bit {i:2d}: {b}")
        c.escrever_bit(1328, 6, 1)
        print(f"  bit 6 = 1:     {c.ler_registrador(1328):016b}")
        c.escrever_bit(1328, 6, 0)
        print(f"  bit 6 = 0:     {c.ler_registrador(1328):016b}")
        print("  (os bits 0, 2 e 5 foram preservados)")

        print("\n=== 5. Efeito do comando (habilita bit 6) ===")
        c.escrever_float(1302, 80.0, div=1)
        c.escrever_bit(1328, 6, 1)
        print("  habilitado, setpoint=80.0: vazao deve subir")
        for _ in range(4):
            time.sleep(2.2)
            print(f"    vazao = {c.ler_float(712):.3f} m3/h")
        c.escrever_bit(1328, 6, 0)
        print("  desabilitado: vazao deve ficar constante")
        for _ in range(2):
            time.sleep(2.2)
            print(f"    vazao = {c.ler_float(712):.3f} m3/h")
    finally:
        c.desconectar()
        print("\nDesconectado.")