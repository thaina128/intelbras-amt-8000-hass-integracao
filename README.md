# Intelbras AMT-8000 para Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Abrir no HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thaina128&repository=intelbras-amt-8000-hass-integracao&category=integration)

Integração custom para Home Assistant focada na central de alarme **Intelbras AMT-8000**.

- Protocolo (AMT-8000): **ISECNet2**
- Transporte: **TCP**
- Porta padrão: **9009**

> Este repositório é um fork e foi ajustado para AMT-8000. Se você usa outros modelos AMT, este fork pode não ser a melhor opção.

## Funcionalidades (Atuais)

### Alarm Control Panel

- `alarm_control_panel` da **Central** (armar/desarmar, `armed_away` e `armed_home`/stay)
- `alarm_control_panel` das **Partições A/B/C/D** (armar/desarmar, `armed_away` e `armed_home`/stay)
- `code_arm_required: true` (o HA exige código para armar/desarmar via UI)

### Zonas

- Entidades para **64 zonas** (Zona 1..Zona 64) com status:
  - **Aberta**
  - **Violada**
  - **Anulada/Bypass**
- Contadores (sensores):
  - Zonas abertas
  - Zonas violadas
  - Zonas anuladas

### Sensores

- Sensor de **nível de bateria (%)**
- Sensores de **modelo** e **firmware**

### Sirene e PGMs

- `switch` para **sirene** (on/off)
- `switch` para **PGM 1..19** (on/off)

### Botões (Ações rápidas)

- Botão: **Armar Stay**
- Botão: **Anular Zonas Abertas**

### Debug / CLI (Desenvolvedor)

- Servidor HTTP de controle em `0.0.0.0:9019` (para debug local)
- CLI em `tools/amt_cli.py` para consultar status e enviar comandos

## Como Funciona

### Modo Cliente (Recomendado para AMT-8000)

O Home Assistant **conecta na central**:

```
Home Assistant  --TCP 9009-->  AMT-8000
```

No fluxo de configuração, preencha o campo `Host` (IP da central). Se `Host` estiver preenchido, a integração usa modo cliente.

### Modo Servidor (Legado)

Se você deixar `Host` vazio, a integração entra em **modo servidor** (o HA escuta na porta e a central conecta no HA).

Esse modo existe por compatibilidade com código legado e usa um conjunto de comandos ASCII (ver tabela abaixo).

## Comandos (Modo Servidor / ASCII)

Tabela de comandos (hex) que a integração usa no modo servidor:

| Comando | Código | Descrição |
|---|---:|---|
| Status | `0x5B` | Solicita status completo (54 bytes de payload na resposta) |
| Armar | `0x41` | Armar alarme |
| Desarmar | `0x44` | Desarmar alarme |
| Stay | `0x41 0x50` | Armar em modo stay |
| Sirene On | `0x43` | Ligar sirene |
| Sirene Off | `0x63` | Desligar sirene |

### Teste Rápido (CLI)

Quando a integração estiver rodando no HA e o painel estiver conectado, você pode testar via CLI:

```bash
python3 tools/amt_cli.py status
python3 tools/amt_cli.py raw "5B"
python3 tools/amt_cli.py arm
python3 tools/amt_cli.py disarm
python3 tools/amt_cli.py siren on
python3 tools/amt_cli.py siren off
```

## Instalação

### HACS (Recomendado)

1. HACS -> Integrations -> ... -> **Custom repositories**
2. Adicione `thaina128/intelbras-amt-8000-hass-integracao` como **Integration**
3. Instale **Intelbras AMT Alarm**
4. Reinicie o Home Assistant

### Manual

1. Copie `custom_components/intelbras_amt` para `config/custom_components/intelbras_amt`
2. Reinicie o Home Assistant

## Configuração (UI)

Configurações -> Dispositivos e Serviços -> **Adicionar Integração** -> "Intelbras AMT Alarm"

Campos:

- `Host`: IP da central (ex.: `192.168.1.50`)
- `Port`: `9009`
- `Password`: **senha de acesso remoto** (normalmente 4 ou 6 dígitos)

## Teste de Conectividade

Verifique se a porta da central está acessível a partir do host do Home Assistant:

```bash
nc -vz <IP_DA_CENTRAL> 9009
```

## Logs (Debug)

Em `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.intelbras_amt: debug
```

## Segurança

- Não exponha a porta `9009` da central na internet.
- Este repositório inclui um **servidor HTTP de controle** para debug em `0.0.0.0:9019` (sem autenticação). Use apenas em rede confiável e não faça port-forward dessa porta.

## Limitações Conhecidas

- No modo AMT-8000 (ISECNet2), alguns campos de diagnóstico ainda podem estar incompletos (WIP), dependendo do firmware e do parsing disponível.
- O estado de PGMs pode não refletir corretamente no HA dependendo do protocolo/firmware (comandos estão implementados, mas o feedback pode variar).

## Créditos

Este projeto é derivado do trabalho da comunidade e foi adaptado para um foco maior em AMT-8000.
