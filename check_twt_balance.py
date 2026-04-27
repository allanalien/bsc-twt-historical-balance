"""
Script: Consulta de saldo histórico de TWT en BNB Smart Chain (BSC)

Este script consulta el balance del token TWT (Trust Wallet Token) en una wallet
específica para un bloque exacto del pasado, usando el método eth_call de JSON-RPC
a través de MegaNode (el proveedor RPC oficial y gratuito de BNB Chain).

Requisitos previos:
    1. Crear cuenta gratuita en https://www.meganode.io/
    2. Generar una API Key para BNB Chain Mainnet desde el panel
    3. Copiar la URL RPC y configurarla en la variable MEGANODE_RPC_URL

Uso:
    python check_twt_balance.py

Formato de salida:
    Saldo en TWT (unidades legibles, 18 decimales)
"""

import os
from decimal import Decimal

from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

# Contrato del token TWT en BSC Mainnet
# Usamos to_checksum_address para validar y corregir el EIP-55 checksum
TWT_CONTRACT_ADDRESS = Web3.to_checksum_address(
    "0x4B0F1812e5Df2A09796481Ff14017e6005508003"
)
WALLET_ADDRESS = Web3.to_checksum_address(
    "0xe2fc31F816A9b94326492132018C3aEcC4a93aE1"
)

# Bloque a consultar (histórico)
BLOCK_NUMBER = 46080111

# Decimales del token TWT
TWT_DECIMALS = 18

# ABI mínimo para la función balanceOf(address) -> uint256
# Solo necesitamos esta función para eth_call
BALANCE_OF_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    }
]

# ---------------------------------------------------------------------------
# 1. Cargar variables de entorno
# ---------------------------------------------------------------------------

# Primero intenta cargar desde un archivo .env
load_dotenv()

# Luego lee desde variable de entorno del sistema
MEGANODE_RPC_URL = os.getenv("MEGANODE_RPC_URL")

# Si no hay URL configurada, mostrar instrucciones y salir
if not MEGANODE_RPC_URL:
    print("=" * 70)
    print(" ERROR: No se encontró la URL RPC de MegaNode.")
    print("=" * 70)
    print()
    print("Para usar este script necesitas una API Key gratuita de MegaNode:")
    print()
    print("  1. Regístrate en https://www.meganode.io/")
    print("  2. Crea una API Key para BNB Chain Mainnet en el panel")
    print("  3. Copia la URL RPC (formato: https://bsc-mainnet.nodereal.io/v1/<key>)")
    print()
    print("Luego configura la URL de una de estas formas:")
    print()
    print("  a) Crea un archivo .env en el mismo directorio con:")
    print("     MEGANODE_RPC_URL=https://bsc-mainnet.nodereal.io/v1/tu-api-key")
    print()
    print("  b) Exporta la variable de entorno:")
    print("     export MEGANODE_RPC_URL=https://bsc-mainnet.nodereal.io/v1/tu-api-key")
    print()
    exit(1)

# ---------------------------------------------------------------------------
# 2. Conectar a BSC Mainnet vía MegaNode
# ---------------------------------------------------------------------------

print("Conectando a BNB Smart Chain Mainnet vía MegaNode...")
w3 = Web3(Web3.HTTPProvider(MEGANODE_RPC_URL))

# BSC es una cadena Proof of Authority (PoA) — requiere este middleware
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

# Verificar conexión
if not w3.is_connected():
    print("ERROR: No se pudo conectar al nodo RPC. Verifica tu API Key.")
    exit(1)

print(f"Conectado exitosamente. Chain ID: {w3.eth.chain_id}")
print()

# ---------------------------------------------------------------------------
# 3. Construir la consulta eth_call para el bloque histórico
# ---------------------------------------------------------------------------

# eth_call permite ejecutar una función de un contrato en el estado de un
# bloque específico. Esto es lo que nos da el saldo HISTÓRICO, no el actual.
#
# Parámetros:
#   - to:      dirección del contrato TWT
#   - data:    firma de la función balanceOf(address) + address de la wallet
#              codificados en ABI
#   - block:   número de bloque en hexadecimal (ej. 46080111 -> 0x2BF206F)

# Codificar la llamada: balanceOf(WALLET_ADDRESS)
contract = w3.eth.contract(address=TWT_CONTRACT_ADDRESS, abi=BALANCE_OF_ABI)
encoded_data = contract.encode_abi("balanceOf", args=[WALLET_ADDRESS])

# Número de bloque en hexadecimal (sin 0x seguido del valor hex)
block_hex = hex(BLOCK_NUMBER)

print(f"Consultando saldo histórico de TWT...")
print(f"  Contrato TWT:  {TWT_CONTRACT_ADDRESS}")
print(f"  Wallet:        {WALLET_ADDRESS}")
print(f"  Bloque:        {BLOCK_NUMBER} (0x{BLOCK_NUMBER:X})")
print()

# ---------------------------------------------------------------------------
# 4. Ejecutar eth_call
# ---------------------------------------------------------------------------

# Construir el objeto de transacción (sin from, ya que es una llamada estática)
call_params = {
    "to": TWT_CONTRACT_ADDRESS,
    "data": encoded_data,
}

# eth_call con el parámetro block_identifier para consultar el estado histórico
try:
    raw_balance = w3.eth.call(call_params, block_identifier=BLOCK_NUMBER)
except Exception as e:
    error_msg = str(e)
    if "missing trie node" in error_msg or "historical state" in error_msg:
        print("ERROR: El nodo RPC no tiene estado histórico para ese bloque.")
        print()
        print("Esto ocurre porque el nodo no es un 'archive node'.")
        print("Necesitas un proveedor con archive data. Recomendado:")
        print("  => MegaNode (plan gratuito): https://www.meganode.io/")
        exit(1)
    print(f"ERROR al ejecutar eth_call: {e}")
    exit(1)

# ---------------------------------------------------------------------------
# 5. Decodificar y convertir el resultado
# ---------------------------------------------------------------------------

# El resultado es un uint256 en formato bytes. Lo decodificamos.
# Al ser balanceOf -> uint256, podemos decodificar como entero directamente.
balance_wei = int.from_bytes(raw_balance, byteorder="big")

# Convertir de wei (18 decimales) a unidades legibles de TWT
# Usamos Decimal para evitar pérdida de precisión
balance_twt = Decimal(balance_wei) / Decimal(10**TWT_DECIMALS)

# ---------------------------------------------------------------------------
# 6. Mostrar resultado
# ---------------------------------------------------------------------------

print("=" * 60)
print(" RESULTADO")
print("=" * 60)
print(f"  Saldo en wei:  {balance_wei:,}")
print(f"  Saldo en TWT:  {balance_twt:,.18f}".rstrip("0").rstrip("."))
print("=" * 60)
print()
print(f"NOTA: Este es el saldo al bloque {BLOCK_NUMBER} (histórico), no el actual.")
