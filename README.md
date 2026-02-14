# Intelbras AMT-8000 para Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Abrir no HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thaina128&repository=intelbras-amt-8000-hass-integracao&category=integration)

Integração custom para Home Assistant focada na central de alarme **Intelbras AMT-8000**.

- Protocolo: **ISECNet2**
- Transporte: **TCP**
- Porta padrão: **9009**

> Este repositório é um fork e foi ajustado para AMT-8000. Se você usa outros modelos AMT, este fork pode não ser a melhor opção.

## Como Funciona

### Modo Cliente (Recomendado para AMT-8000)

O Home Assistant **conecta na central**:

```
Home Assistant  --TCP 9009-->  AMT-8000
```

No fluxo de configuração, preencha o campo `Host` (IP da central). Se `Host` estiver preenchido, a integração usa modo cliente.

### Modo Servidor (Legado)

Se você deixar `Host` vazio, a integração entra em **modo servidor** (o HA escuta na porta e a central conecta no HA).

Esse modo existe por compatibilidade com código legado e **não é o foco deste fork**.

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

## Entidades

Principais entidades criadas:

- `alarm_control_panel.*`: Central e Partições (A/B/C/D)
- `binary_sensor.*`: Zonas (aberta/violada/anulada) e diagnósticos (energia/bateria/sirene/problemas)
- `sensor.*`: nível de bateria, contadores de zonas
- `switch.*`: sirene, PGM 1..19
- `button.*`: armar stay, anular zonas abertas

## Limitações Conhecidas (AMT-8000)

Algumas informações expostas no Home Assistant ainda podem estar **incompletas** no modo AMT-8000 (WIP), por exemplo:

- Estado detalhado de energia AC e PGMs
- Tamper/curto/bateria fraca por zona (sensores por zona)

Se você quiser contribuir com dumps/offsets para melhorar o parsing, abra uma issue.

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

## Créditos

Este projeto é derivado do trabalho da comunidade e foi adaptado para um foco maior em AMT-8000.
