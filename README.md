# BSC Analyzer

Herramienta para auditoría on-chain de tokens BEP-20 en BNB Smart Chain. Consulta saldos históricos, rastrea transferencias y genera análisis visuales — todo desde la blockchain, sin depender de APIs de terceros como BscScan.

## Requisitos

- Python 3.8+
- API Key gratuita de [NodeReal](https://www.nodereal.io/) (archive node)

## Instalación

```bash
pip install -r requirements.txt
```

## Configuración

Crea un archivo `.env` con tu URL RPC de MegaNode:

```
MEGANODE_RPC_URL=https://bsc-mainnet.nodereal.io/v1/tu-api-key
```

## Uso

### Consulta rápida (CLI)

Saldo de un token en un bloque exacto:

```bash
python3 check_twt_balance.py
```

Por defecto consulta TWT en la wallet `0xe2fc31...` al bloque `46080111`. Para cambiar token/wallet/bloque, edita las constantes al inicio del script.

### Análisis completo (Jupyter Notebook)

```bash
jupyter notebook notebooks/twt_analysis.ipynb
```

Ejecuta cada celda con `Shift+Enter`. El notebook contiene:

| Sección | Descripción |
|---|---|
| Setup | Conexión a BSC vía MegaNode |
| Saldo histórico | Balance en cualquier bloque del pasado |
| Tendencia | Gráfico de evolución del saldo cada 1M bloques |
| Transferencias | Tracking BEP-20 con detección inteligente de cambios |
| Top contrapartes | Ranking de destinos de transfers salientes |
| Consulta puntual | Saldo en un bloque arbitrario |

## Cómo funciona

### Saldo histórico (`eth_call`)

Ejecuta `balanceOf(wallet)` en el estado de la blockchain congelado en un bloque específico. No consulta el saldo actual sino el de ese momento exacto.

### Tracking de transferencias

En vez de barrer todos los bloques con `eth_getLogs`, el algoritmo:

1. Muestrea `balanceOf` cada 500k bloques
2. Detecta solo los rangos donde el saldo cambió
3. Escanea únicamente esos rangos con `eth_getLogs` (en chunks de 49,999 bloques)

Esto reduce ~2000 llamadas RPC a ~200 para un rango típico de 50M bloques.

### Análisis

- **Tendencia**: muestrea el saldo cada 1M bloques y lo grafica
- **Contrapartes**: agrupa transfers salientes por destinatario y muestra top N

## Uso con otros tokens o wallets

Edita `bsc_analyzer/config.py`:

```python
TWT_CONTRACT = Web3.to_checksum_address("0xNuevoToken...")
WALLET = Web3.to_checksum_address("0xNuevaWallet...")
START_BLOCK = 12345678   # Bloque desde donde empezar el análisis
```

## Compatibilidad

Funciona con cualquier EVM chain (Ethereum, Polygon, Arbitrum, etc.). Solo cambia `MEGANODE_RPC_URL` por un RPC de archive node de la red deseada.

## Estructura del proyecto

```
bsc_analyzer/
├── config.py       # Constantes, conexión RPC
├── balance.py      # eth_call para saldo histórico
├── transfers.py    # Tracking inteligente de transfers
├── trend.py        # Muestreo de tendencia
├── reports.py      # Contrapartes y resúmenes
└── viz.py          # Gráficos matplotlib
check_twt_balance.py  # Script CLI
notebooks/
└── twt_analysis.ipynb  # Notebook interactivo
```

## Limitaciones

- El tracking de transfers requiere ~1 min por cada millón de bloques con actividad
- MegaNode tiene rate limits; para análisis muy extensos considera usar lotes más pequeños
