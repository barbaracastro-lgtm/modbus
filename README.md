# Modbus TCP com emulação de CLP (bancada de bombeamento)

Atividade prática ENE118: servidor Modbus TCP que emula um CLP e cliente Python (PyModbus) que lê e escreve Holding Registers, floats e bits.

## Integrantes

- Barbara Castro (`barbaracastro-lgtm`): servidor (emulação do CLP), requirements, README
- Barbara Reis (`barbarasrdecastro-prog`): cliente Modbus (conexão, float, bits, demonstrações)

Trabalho desenvolvido por uma única aluna usando duas contas do GitHub, conforme combinado com o professor, para demonstrar o fluxo de branches e pull requests.

## Instalação

```
py -m pip install -r requirements.txt
```

Dependências: `pymodbus==3.16.1` (cliente) e `pyModbusTCP==0.3.1` (servidor).

## Execução (a partir da raiz do projeto)

Terminal 1 (servidor):

```
py servidor\servidor_modbus.py
```

Terminal 2 (cliente, executa todas as demonstrações):

```
py cliente\cliente_modbus.py
```

- IP: `localhost`
- Porta: `502` (no Windows pode exigir permissão de administrador ou liberar a porta)
- Device ID: 1

## Convenções

- Leitura: valor de engenharia = valor recebido / Div = valor recebido × m
- Escrita: valor enviado = valor de engenharia × Div
- **FP**: float32 em dois Holding Registers consecutivos. Primeiro decodifica o float32, depois aplica a escala. Na escrita, aplica a escala antes de converter para registradores.
- **4X**: inteiro de 16 bits sem sinal em um Holding Register. Na escrita, o valor é arredondado (`round`) e limitado ao intervalo 0 a 65535.
- **Ordem de palavras dos floats**: big-endian (`word_order='big'`): o registrador de endereço menor contém a palavra mais significativa. É a mesma no servidor e no cliente.
- Bits: bit 0 é o menos significativo e bit 15 o mais significativo. Valores 0/1, sem escala.
- Endereços usados diretamente na API (ex.: 830), sem prefixo 4xxxx.

## Mapa de dados

| Tag | Descrição | Tipo | Endereço inicial | Qtd. regs | Bit | Div | Multiplicador (m) | Unidade |
|---|---|---|---|---|---|---|---|---|
| temp_r | Temperatura R | FP | 700 | 2 | - | 10 | 0,1 | °C |
| temp_s | Temperatura S | FP | 702 | 2 | - | 10 | 0,1 | °C |
| temp_t | Temperatura T | FP | 704 | 2 | - | 10 | 0,1 | °C |
| temp_carc | Temperatura da carcaça | FP | 706 | 2 | - | 10 | 0,1 | °C |
| pressao | Pressão (PIT01) | FP | 710 | 2 | - | 1 | 1 | bar |
| vazao | Vazão (FIT01) | FP | 712 | 2 | - | 1 | 1 | m³/h |
| freq | Frequência | 4X | 830 | 1 | - | 100 | 0,01 | Hz |
| corrente | Corrente R | 4X | 840 | 1 | - | 10 | 0,1 | A |
| tensao | Tensão R-S | 4X | 847 | 1 | - | 10 | 0,1 | V |
| fp | Fator de potência R | 4X | 868 | 1 | - | 1000 | 0,001 | - |
| sp_pid | Setpoint de vazão | FP | 1302 | 2 | - | 1 | 1 | m³/h |
| habilita | Habilitar motor | 4X / bit | 1328 | 1 | 6 | 1 | 1 | - |

Exemplos: em 830, o inteiro 6000 representa 60,00 Hz; em 868, 950 representa fator de potência 0,950; 12,3 A em 840 é codificado como 123.

As medições (700 a 868) são escritas pelo servidor. O setpoint (1302) e o registrador de comandos (1328) ficam em áreas separadas e são escritos apenas pelo cliente: o servidor só os lê.

## Comportamento da simulação

O servidor atualiza as medições a cada 2 segundos:

- Temperaturas, pressão, corrente, tensão e fator de potência variam de forma aleatória limitada (passos pequenos).
- Com o bit 6 de 1328 em 1 (motor habilitado), a vazão se aproxima gradualmente do setpoint (10% da diferença a cada ciclo) e a frequência oscila levemente.
- Com o bit 6 em 0, a vazão permanece constante.
- Valores iniciais: setpoint 50,0 m³/h, vazão 0, frequência 60 Hz.

## Demonstrações (bloco `__main__` do cliente)

1. Leitura dos 10 dados em dois instantes diferentes.
2. Escala: valor recebido, Div, multiplicador e valor de engenharia da frequência.
3. Float: escrita e leitura do setpoint, mostrando valor enviado, registradores e valor lido.
4. Bits: registrador 1328 com bits 0, 2 e 5 já ativos; alteração do bit 6 para 1 e depois 0, com os demais preservados.
5. Efeito do comando: vazão sobe com o motor habilitado e permanece constante ao desabilitar.

Importar a classe `ClienteModbus` em outro arquivo não abre conexões nem executa demonstrações.

## Estrutura

```
README.md
requirements.txt
.gitignore
servidor/servidor_modbus.py   # servidor e emulação do CLP
cliente/cliente_modbus.py     # comunicação e conversões
```
## Observações

Foi utilizada IA para escrever nessa aba e conferir alguns erros.