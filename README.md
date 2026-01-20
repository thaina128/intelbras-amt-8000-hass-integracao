# Integração Intelbras AMT para Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/robsonfelix/intelbras-amt-hass-integration.svg)](https://github.com/robsonfelix/intelbras-amt-hass-integration/releases)
[![License](https://img.shields.io/github/license/robsonfelix/intelbras-amt-hass-integration.svg)](LICENSE)

Integração nativa para Home Assistant dos sistemas de alarme Intelbras AMT 4010, AMT 2018 e AMT 1016.

## Adicionar ao Home Assistant

[![Abrir sua instância do Home Assistant e adicionar este repositório ao HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=robsonfelix&repository=intelbras-amt-hass-integration&category=integration)

## Funcionalidades

- **Painel de Alarme**: Armar/desarmar, modo stay
- **Monitoramento de Zonas**: Todas as zonas (até 64) com status aberta, violada e anulada
- **Controle de Partições**: Armar/desarmar individual para partições A, B, C, D
- **Controle de PGM**: Ativar/desativar saídas PGM 1, 2, 3
- **Sensores de Status**: Nível da bateria, energia AC, sirene, problemas
- **Reconexão Automática**: Reconecta automaticamente em caso de perda de conexão

## Modelos Suportados

| Modelo | Zonas | Partições | Status |
|--------|-------|-----------|--------|
| AMT 4010 SMART | 64 | 4 | ✅ Testado |
| AMT 2018 | 18 | 4 | 🔄 Deve funcionar |
| AMT 1016 | 16 | 4 | 🔄 Deve funcionar |

## Instalação

### HACS (Recomendado)

1. Clique no botão acima **"Adicionar repositório ao HACS"**, ou:
2. Abra o HACS no Home Assistant
3. Clique em "Integrações"
4. Clique no menu ⋮ (três pontos) → "Repositórios personalizados"
5. Adicione `robsonfelix/intelbras-amt-hass-integration` como "Integração"
6. Procure por "Intelbras AMT" e clique em "Instalar"
7. Reinicie o Home Assistant

### Instalação Manual

1. Baixe a última versão do [GitHub Releases](https://github.com/robsonfelix/intelbras-amt-hass-integration/releases)
2. Copie a pasta `custom_components/intelbras_amt` para o diretório `config/custom_components/` do seu Home Assistant
3. Reinicie o Home Assistant

## Configuração

1. Vá em **Configurações** → **Dispositivos e Serviços**
2. Clique em **+ Adicionar Integração**
3. Procure por "Intelbras AMT"
4. Preencha:
   - **Host**: Endereço IP do painel de alarme (ex: `192.168.1.100`)
   - **Porta**: Porta TCP (padrão: `9015`)
   - **Senha Master**: Senha master de 6 dígitos
5. Opcionalmente configure as senhas das partições

## Conexão de Hardware

O painel AMT conecta via TCP/IP na porta 9015. Certifique-se de que:
- O módulo Ethernet do alarme está configurado e conectado à rede
- A porta 9015 está acessível a partir do Home Assistant
- Você possui a senha master do painel

## Entidades Criadas

### Painel de Alarme
- `alarm_control_panel.amt_central` - Painel principal do alarme

### Sensores Binários
- `binary_sensor.amt_zona_N` - Status da zona N aberta (1-64)
- `binary_sensor.amt_zona_N_violada` - Status da zona N violada
- `binary_sensor.amt_zona_N_anulada` - Status da zona N anulada (bypass)
- `binary_sensor.amt_particao_X` - Status da partição X armada (A/B/C/D)
- `binary_sensor.amt_pgm_N` - Status do PGM N (1-3)
- `binary_sensor.amt_energia_ac` - Status da energia AC
- `binary_sensor.amt_bateria_conectada` - Status da bateria conectada
- `binary_sensor.amt_sirene` - Status da sirene
- `binary_sensor.amt_problema` - Indicador de problema

### Sensores
- `sensor.amt_nivel_da_bateria` - Nível da bateria (%)
- `sensor.amt_modelo` - Nome do modelo
- `sensor.amt_firmware` - Versão do firmware

### Botões
- `button.amt_armar` - Armar o alarme
- `button.amt_desarmar` - Desarmar o alarme
- `button.amt_armar_stay` - Armar em modo stay
- `button.amt_armar_particao_X` - Armar partição X
- `button.amt_desarmar_particao_X` - Desarmar partição X
- `button.amt_ativar_pgm_N` - Ativar PGM N
- `button.amt_desativar_pgm_N` - Desativar PGM N
- `button.amt_anular_zonas_abertas` - Anular todas as zonas abertas

## Opções

| Opção | Padrão | Descrição |
|-------|--------|-----------|
| scan_interval | 1 | Intervalo de atualização em segundos |

## Solução de Problemas

### Não Consegue Conectar
- Verifique se o endereço IP está correto
- Certifique-se de que a porta 9015 está acessível
- Confirme que a senha master está correta
- Verifique se o painel de alarme está conectado à rede

### Entidades Indisponíveis
- Verifique os logs do Home Assistant para erros de conexão
- A integração reconecta automaticamente em caso de perda de conexão

### Debug Logging

Adicione ao `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.intelbras_amt: debug
```

## Protocolo

Esta integração se comunica diretamente com o painel AMT via TCP na porta 9015 usando o protocolo proprietário da Intelbras.

### Formato do Frame
```
[Tamanho] [0xe9] [0x21] [SENHA_BYTES] [COMANDO] [0x21] [XOR_CHECKSUM]
```

## Contribuindo

Contribuições são bem-vindas! Por favor:
1. Faça um fork do repositório
2. Crie uma branch para sua feature
3. Envie um pull request

Se você tem um modelo diferente de central AMT e quer ajudar a adicionar suporte, abra uma issue com:
- Nome do modelo da sua central
- Logs de debug da integração
- Qualquer documentação do protocolo que você tenha

## Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Créditos

Baseado em engenharia reversa do protocolo Intelbras AMT.
