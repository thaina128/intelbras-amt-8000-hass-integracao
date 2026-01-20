# Integração Intelbras AMT para Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/robsonfelix/intelbras-amt-hass-integration?include_prereleases)](https://github.com/robsonfelix/intelbras-amt-hass-integration/releases)
[![License](https://img.shields.io/github/license/robsonfelix/intelbras-amt-hass-integration)](LICENSE)

Integração nativa para Home Assistant dos sistemas de alarme Intelbras AMT 4010, AMT 2018 e AMT 1016.

## Adicionar ao Home Assistant

[![Abrir sua instância do Home Assistant e adicionar este repositório ao HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=robsonfelix&repository=intelbras-amt-hass-integration&category=integration)

## Funcionalidades

- **Painéis de Alarme**: Central e partições com código de segurança obrigatório
- **Modo Stay**: Armar em modo stay (parcial)
- **Monitoramento de Zonas**: Até 64 zonas com status aberta, violada, anulada, tamper e curto-circuito
- **Controle de Partições**: Painéis individuais para armar/desarmar partições A, B, C, D (com código)
- **Controle de PGM**: 19 saídas PGM (switches on/off)
- **Controle da Sirene**: Switch para ligar/desligar sirene
- **Sensores de Status**: Nível da bateria, energia AC, problemas detalhados
- **Contadores de Zonas**: Quantidade de zonas abertas, violadas e anuladas

## Arquitetura: Modo Servidor

Esta integração funciona em **modo servidor**: o Home Assistant abre uma porta TCP e aguarda a conexão da central AMT. A central é configurada para conectar ao IP do Home Assistant.

```
┌─────────────────┐         ┌─────────────────┐
│   Central AMT   │ ──────► │  Home Assistant │
│  (IP da rede)   │  TCP    │   (porta 9009)  │
└─────────────────┘         └─────────────────┘
```

**Vantagens:**
- Conexão mais estável (central mantém a conexão ativa)
- Não requer configuração de NAT/firewall na direção HA→Central
- Compatível com protocolo ISECNet/ISECMobile

## Modelos Suportados

| Modelo | Zonas | Partições | PGMs | Status |
|--------|-------|-----------|------|--------|
| AMT 4010 SMART | 64 | 4 | 19 | ✅ Testado |
| AMT 2018 | 18 | 4 | 19 | 🔄 Deve funcionar |
| AMT 1016 | 16 | 4 | 19 | 🔄 Deve funcionar |

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

### 1. Configurar a Central AMT

Configure sua central AMT para conectar ao Home Assistant:

1. Acesse o menu de programação da central
2. Configure o **IP de destino** com o endereço IP do Home Assistant
3. Configure a **porta de destino**: `9009`
4. Anote a **senha de acesso remoto** (4-6 dígitos)

> **Nota**: A central precisa ter módulo Ethernet configurado e conectado à mesma rede do Home Assistant.

### 2. Adicionar a Integração no Home Assistant

1. Vá em **Configurações** → **Dispositivos e Serviços**
2. Clique em **+ Adicionar Integração**
3. Procure por "Intelbras AMT"
4. Preencha:
   - **Porta**: Porta TCP para escutar (padrão: `9009`)
   - **Senha**: Senha de acesso remoto configurada na central

### 3. Segurança

Todos os painéis de alarme (central e partições) requerem **código numérico** para armar/desarmar. Este código é a mesma senha de acesso remoto configurada na central. Isso garante que mesmo usuários com acesso ao Home Assistant precisem saber a senha para controlar o alarme.

## Entidades Criadas

### Painéis de Alarme
| Entidade | Descrição |
|----------|-----------|
| `alarm_control_panel.amt_porta_XXXX_central` | Painel principal (requer código) |
| `alarm_control_panel.amt_porta_XXXX_particao_a` | Partição A (requer código) |
| `alarm_control_panel.amt_porta_XXXX_particao_b` | Partição B (requer código) |
| `alarm_control_panel.amt_porta_XXXX_particao_c` | Partição C (requer código) |
| `alarm_control_panel.amt_porta_XXXX_particao_d` | Partição D (requer código) |

Estados: `disarmed`, `armed_away`, `armed_home`, `triggered`

### Switches (Controles)
| Entidade | Descrição |
|----------|-----------|
| `switch.amt_*_sirene` | Ligar/desligar sirene |
| `switch.amt_*_pgm_N` | Ativar/desativar PGM (1-19) |

### Sensores Binários - Zonas
| Entidade | Quantidade | Descrição |
|----------|------------|-----------|
| `binary_sensor.amt_*_zona_N` | 64 | Zona aberta |
| `binary_sensor.amt_*_zona_N_violada` | 64 | Zona violada |
| `binary_sensor.amt_*_zona_N_anulada` | 64 | Zona anulada (bypass) |
| `binary_sensor.amt_*_zona_N_tamper` | 18 | Zona com tamper |
| `binary_sensor.amt_*_zona_N_curto_circuito` | 18 | Zona em curto-circuito |
| `binary_sensor.amt_*_zona_N_bateria_fraca` | 40 | Bateria fraca (sensor sem fio) |

### Sensores Binários - Status
| Entidade | Descrição |
|----------|-----------|
| `binary_sensor.amt_*_energia_ac` | Energia AC conectada |
| `binary_sensor.amt_*_bateria_conectada` | Bateria conectada |
| `binary_sensor.amt_*_sirene` | Sirene ativa |
| `binary_sensor.amt_*_problema` | Indicador de problema |
| `binary_sensor.amt_*_bateria_fraca` | Bateria da central fraca |
| `binary_sensor.amt_*_bateria_ausente` | Bateria ausente |
| `binary_sensor.amt_*_bateria_em_curto` | Bateria em curto-circuito |
| `binary_sensor.amt_*_sobrecarga_aux` | Sobrecarga na saída auxiliar |
| `binary_sensor.amt_*_fio_sirene_cortado` | Fio da sirene cortado |
| `binary_sensor.amt_*_sirene_em_curto` | Sirene em curto-circuito |
| `binary_sensor.amt_*_linha_telefonica_cortada` | Linha telefônica cortada |
| `binary_sensor.amt_*_falha_de_comunicacao` | Falha de comunicação |

### Sensores
| Entidade | Descrição |
|----------|-----------|
| `sensor.amt_*_nivel_da_bateria` | Nível da bateria (%) |
| `sensor.amt_*_modelo` | Nome do modelo |
| `sensor.amt_*_firmware` | Versão do firmware |
| `sensor.amt_*_zonas_abertas` | Quantidade de zonas abertas |
| `sensor.amt_*_zonas_violadas` | Quantidade de zonas violadas |
| `sensor.amt_*_zonas_anuladas` | Quantidade de zonas anuladas |

### Botões
| Entidade | Descrição |
|----------|-----------|
| `button.amt_*_armar_stay` | Armar em modo stay |
| `button.amt_*_anular_zonas_abertas` | Anular todas as zonas abertas |

## Opções

| Opção | Padrão | Descrição |
|-------|--------|-----------|
| scan_interval | 1 | Intervalo de atualização em segundos |

## Solução de Problemas

### Central Não Conecta

1. Verifique se o IP do Home Assistant está configurado corretamente na central
2. Confirme que a porta 9009 está acessível (firewall)
3. Verifique se a central tem conexão de rede
4. Veja os logs para mensagens de conexão

### Senha Incorreta

Se receber erro de senha incorreta:
1. Confirme a senha de acesso remoto configurada na central
2. A senha deve ter 4-6 dígitos numéricos
3. Reconfigure a integração com a senha correta

### Entidades Indisponíveis

- Verifique se a central está conectada (aguarde até 60s)
- Verifique os logs do Home Assistant para erros
- A integração reconecta automaticamente quando a central reconecta

### Debug Logging

Adicione ao `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.intelbras_amt: debug
```

## Protocolo

Esta integração implementa o protocolo ISECNet/ISECMobile da Intelbras.

### Formato do Frame
```
[Tamanho] [0xE9] [0x21] [SENHA_ASCII] [COMANDO] [0x21] [CHECKSUM]
```

- **Senha**: Codificada em ASCII (ex: "1234" = `0x31 0x32 0x33 0x34`)
- **Checksum**: XOR de todos os bytes, depois XOR com 0xFF

### Comandos Principais
| Comando | Código | Descrição |
|---------|--------|-----------|
| Status | `0x5B` | Solicita status completo (54 bytes) |
| Armar | `0x41` | Armar alarme |
| Desarmar | `0x44` | Desarmar alarme |
| Stay | `0x41 0x50` | Armar em modo stay |
| Sirene On | `0x43` | Ligar sirene |
| Sirene Off | `0x63` | Desligar sirene |

## Contribuindo

Contribuições são bem-vindas! Por favor:
1. Faça um fork do repositório
2. Crie uma branch para sua feature
3. Envie um pull request

Se você tem um modelo diferente de central AMT e quer ajudar a adicionar suporte, abra uma issue com:
- Nome do modelo da sua central
- Logs de debug da integração

## Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Créditos

- Originalmente desenvolvido como conversão de um projeto Node-RED para Python
- Protocolo ISECNet/ISECMobile da Intelbras
- Referência adicional do projeto [intelbras-amt-home-assistant](https://github.com/Pehesi97/intelbras-amt-home-assistant) de Pehesi97 para detalhes do protocolo
