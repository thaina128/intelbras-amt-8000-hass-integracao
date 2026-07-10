# Home Assistant, Alexa Smart Home e AMT-8000

Documento operacional do ambiente configurado em 2026-07-10 para expor o Home Assistant para a Alexa usando uma Alexa Smart Home Skill propria, AWS Lambda e o dominio `ha.thainamonteiro.com.br`.

Nao registrar neste repositorio senhas, tokens, Access Secret, PIN da Alexa, senha remota do alarme, senha master de fechaduras, logs com Authorization headers ou credenciais de contas.

## Mudancas Aplicadas

### Acesso Externo do Home Assistant

- Criado/validado acesso publico em `https://ha.thainamonteiro.com.br`.
- Configurado Cloudflare para o subdominio `ha.thainamonteiro.com.br` apontar para o tunnel `tunel-monteiro-hq`.
- Removido registro DNS incorreto `ha.thainamonteiro.com.br.catalogomobile.com.br` da zona `catalogomobile.com.br`.
- Configurado no Home Assistant:

```yaml
homeassistant:
  external_url: "https://ha.thainamonteiro.com.br"
  internal_url: "http://192.168.15.16:8123"
```

### Alexa Smart Home

- Criada a AWS Lambda `home-assistant-alexa-smart-home` em `us-east-1`.
- Instalado na Lambda o proxy oficial do Home Assistant para Alexa Smart Home.
- Criada a Alexa Smart Home Skill `Casa Thaina`.
- Configurado endpoint da skill para a Lambda.
- Adicionada permissao da Skill para invocar a Lambda.
- Configurado Account Linking da skill para OAuth do Home Assistant.
- Expostas entidades selecionadas do HA para Alexa com nomes amigaveis.
- Criadas orientacoes para rotinas de voz:
  - `ligar alarme casa`
  - `forcar ligar alarme casa`
  - `desarmar Alarme Casa` com PIN no app Alexa

### Avisos Falados na Alexa

- Configurada a integracao nativa `Alexa Devices` do Home Assistant para a conta Amazon da casa.
- O login foi concluido por OAuth/codigo de autorizacao; nenhum token, senha ou codigo OTP deve ser registrado neste repositorio.
- Entidades criadas para o Echo Dot:
  - `notify.echo_dot_de_thaina_announce`
  - `notify.echo_dot_de_thaina_speak`
  - `binary_sensor.echo_dot_de_thaina_connectivity`
  - `binary_sensor.echo_dot_de_thaina_motion`
  - `sensor.echo_dot_de_thaina_temperature`
  - `sensor.echo_dot_de_thaina_illuminance`
  - `switch.echo_dot_de_thaina_do_not_disturb`
- Atualizado o script central `script.avisar_casa` para falar no Google Nest e tambem na Alexa via `notify.send_message`.
- Atualizadas as automacoes executoras da Alexa para usar `script.avisar_casa` nos retornos de sucesso/falha, incluindo o caso de porta/janela aberta.
- A automacao de chuva/janelas ja chamava `script.avisar_casa`; portanto, os avisos de chuva passaram a sair tambem no Echo Dot.

Backups criados no Home Assistant:

- `/config/.storage/core.config_entries.bak-alexa-devices-20260710T211149Z`
- `/config/scripts.yaml.bak-alexa-devices-20260710T211554Z`
- `/config/automations.yaml.bak-alexa-devices-announce-20260710T212101Z`

Hotfix aplicado no container:

- Arquivo: `/usr/local/lib/python3.13/site-packages/aioamazondevices/api.py`
- Backup: `/tmp/aioamazondevices_api.py.before_alexa_error_none_patch`
- Motivo: a validacao da biblioteca falhava quando a Amazon retornava `error: null` em um recurso do Echo.
- Ajuste: tratar `feature_property.get("error")` como `{}` quando vier `None`.

Esse hotfix fica dentro da imagem/container em execucao. Se o container for recriado ou a imagem do Home Assistant for atualizada, ele pode ser perdido. Se a integracao `Alexa Devices` voltar a falhar com erro `NoneType` em `.get`, conferir primeiro se a versao nova da biblioteca ja corrigiu o problema; se nao corrigiu, reaplicar o patch no container.

Validacoes realizadas em 2026-07-10:

- `python3 -m homeassistant --script check_config --config /config` passou sem erros.
- O container `homeassistant-uswo0ko0w8c0gkc0kcso004c` voltou `healthy` apos restart.
- O teste manual de `script.avisar_casa` pela UI foi aceito sem erros recentes de `alexa_devices`, `notify.send_message` ou `script.avisar_casa` nos logs.

### Temperatura do Aquecedor via Alexa

- Criado `input_number.aquecedor_temperatura_alexa` para contornar limite de temperatura da skill Tuya/Smart Life pela Alexa.
- Nome exposto para Alexa: `Temperatura Aquecedor`.
- Faixa configurada: `35` a `65 °C`.
- Passo configurado: `1 °C`.
- Criada automacao `Aquecedor - Sincronizar temperatura para Alexa` para manter o `input_number` alinhado com `climate.aquecedor`.
- Criada automacao `Alexa - Aplicar temperatura do aquecedor` para aplicar no `climate.aquecedor` o valor definido no `input_number`.
- Validado em 2026-07-10: ajustar `input_number.aquecedor_temperatura_alexa` para `42` atualizou `climate.aquecedor` para `temperature: 42`.

Backups criados:

- `/data/coolify/services/uswo0ko0w8c0gkc0kcso004c/configuration.yaml.bak-aquecedor-input-number-20260710T220249Z`
- `/config/automations.yaml.bak-aquecedor-input-number-20260710T220306Z`

Depois de qualquer alteracao no filtro `alexa.smart_home`, pedir para a Alexa descobrir dispositivos novamente.

### AMT-8000 e Porta RX500

- Configurada automacao para a porta RX500 acompanhar o estado real do alarme.
- Ao armar, a automacao envia `Fechar Porta` 3 vezes.
- Ao desarmar, a automacao envia `Abrir Porta` com pulso de preparacao e mais 3 pulsos fortes.
- A automacao usa `mode: restart` para cancelar tentativas pendentes quando o estado do alarme muda novamente.

## Resumo do Estado Atual

### Home Assistant

- URL local: `http://192.168.15.16:8123`
- URL publica: `https://ha.thainamonteiro.com.br`
- Instalacao: Home Assistant Container gerenciado pelo Coolify
- Container observado: `homeassistant-uswo0ko0w8c0gkc0kcso004c`
- Imagem observada: `ghcr.io/home-assistant/home-assistant:2025.10.2`
- Arquivo principal bind-mounted:
  `/data/coolify/services/uswo0ko0w8c0gkc0kcso004c/configuration.yaml`
- Volume Docker com arquivos internos do HA:
  `/var/lib/docker/volumes/uswo0ko0w8c0gkc0kcso004c_homeassistant-config/_data`
- Caminho dentro do container: `/config`

### Acesso Publico

- Dominio usado pela Alexa: `https://ha.thainamonteiro.com.br`
- DNS no Cloudflare: `ha.thainamonteiro.com.br` apontando para o tunnel `tunel-monteiro-hq`
- Validacao basica esperada:

```bash
curl -sS --max-time 10 -o /dev/null -w '%{http_code}\n' https://ha.thainamonteiro.com.br/
```

Resultado esperado: `200`.

### AWS Lambda

- Conta AWS: `CatalogMobile-INT (125746528827)`
- Regiao obrigatoria para Alexa `pt-BR`: `us-east-1` / N. Virginia
- Function: `home-assistant-alexa-smart-home`
- ARN: `arn:aws:lambda:us-east-1:125746528827:function:home-assistant-alexa-smart-home`
- Runtime: `python3.13`
- Handler: `lambda_function.lambda_handler`
- Timeout: `15`
- Memory: `128 MB`
- Env var:
  - `BASE_URL=https://ha.thainamonteiro.com.br`
- Role criada pela AWS:
  `arn:aws:iam::125746528827:role/service-role/home-assistant-alexa-smart-home-role-z112ymq7`
- Trigger/permissao:
  - Principal: `alexa-connectedhome.amazon.com`
  - `lambda:EventSourceToken`: `amzn1.ask.skill.e9339e08-fc33-47bb-a6ae-9a7b22924bd4`
- Recursos configurados de forma compativel com free tier: Lambda simples, 128 MB, sem VPC, sem URL publica propria, sem execucao agendada.

### Codigo da Lambda

A Lambda usa o codigo proxy recomendado pela documentacao do Home Assistant para Alexa Smart Home.

Fluxo:

1. Alexa chama a Lambda com uma diretiva Smart Home.
2. A Lambda extrai o Bearer Token enviado pela Alexa depois do Account Linking.
3. A Lambda encaminha o evento para:
   `https://ha.thainamonteiro.com.br/api/alexa/smart_home`
4. O Home Assistant responde para a Alexa com discovery, estados ou resultado de comandos.

Decisoes de seguranca:

- Nao foi configurado `LONG_LIVED_ACCESS_TOKEN`.
- Nao foi configurado `DEBUG`.
- Nao foi desativada verificacao SSL.
- O segredo do Account Linking e arbitrario e fica apenas na Amazon Developer Console.

### Amazon Developer / Alexa Skill

- Skill name: `Casa Thaina`
- Skill ID: `amzn1.ask.skill.e9339e08-fc33-47bb-a6ae-9a7b22924bd4`
- Locale: `Portuguese (BR)`
- Model: `Smart Home`
- Hosting: `Provision your own`
- Smart Home service endpoint:
  `arn:aws:lambda:us-east-1:125746528827:function:home-assistant-alexa-smart-home`
- Account Linking:
  - Authorization URI: `https://ha.thainamonteiro.com.br/auth/authorize`
  - Access Token URI: `https://ha.thainamonteiro.com.br/auth/token`
  - Client ID: `https://pitangui.amazon.com/`
  - Client Secret: valor arbitrario configurado na Amazon Developer Console; nao precisa ser guardado aqui
  - Authentication Scheme: `Credentials in request body`
  - Scope: `smart_home`

### Alexa Devices / Echo Dot

- Integracao HA: `Alexa Devices`
- Conta: conta Amazon da casa
- Site final usado pela integracao: `https://www.amazon.com.br`
- Entidade de anuncio principal:
  `notify.echo_dot_de_thaina_announce`
- Entidade de fala simples:
  `notify.echo_dot_de_thaina_speak`

A integracao `Alexa Devices` e usada para o caminho inverso da skill Smart Home:

- Skill Smart Home: Alexa envia comandos para o Home Assistant.
- Alexa Devices: Home Assistant envia falas/avisos para o Echo Dot.

## Entidades Expostas para Alexa

O bloco `alexa.smart_home` do Home Assistant esta configurado com filtro explicito. Isso evita expor a casa inteira por engano.

```yaml
alexa:
  smart_home:
    locale: pt-BR
    filter:
      include_entities:
        - alarm_control_panel.amt_porta_9009_central
        - automation.alexa_ligar_alarme_comando
        - automation.alexa_forcar_ligar_alarme_comando
        - cover.cortina
        - input_number.aquecedor_temperatura_alexa
    entity_config:
      alarm_control_panel.amt_porta_9009_central:
        name: "Alarme Casa"
        description: "Central de alarme da casa"
      automation.alexa_ligar_alarme_comando:
        name: "Ligar Alarme Casa"
        description: "Comando para armar o alarme da casa"
      automation.alexa_forcar_ligar_alarme_comando:
        name: "Forcar Ligar Alarme Casa"
        description: "Comando para armar o alarme da casa ignorando zonas abertas"
      cover.cortina:
        name: "Cortina"
        description: "Cortina RF controlada pelo Smart Life"
      input_number.aquecedor_temperatura_alexa:
        name: "Temperatura Aquecedor"
        description: "Controle numerico da temperatura do aquecedor"
```

Na Alexa, depois de descobrir dispositivos, devem aparecer:

- `Alarme Casa`
- `Ligar Alarme Casa`
- `Forcar Ligar Alarme Casa`
- `Cortina`
- `Temperatura Aquecedor`

## Comandos de Voz Recomendados

### Armar Alarme Normal

Use rotina no app Alexa:

- Quando eu disser: `ligar alarme casa`
- Acao: Casa inteligente -> `Ligar Alarme Casa` -> ligar

Essa rotina aciona a automacao de comando, que valida as aberturas antes de armar. Se houver janela/porta aberta, o Home Assistant anuncia o que esta aberto e nao arma.

### Armar Forcado

Use rotina no app Alexa:

- Quando eu disser: `forcar ligar alarme casa`
- Acao: Casa inteligente -> `Forcar Ligar Alarme Casa` -> ligar

Essa rotina usa a automacao de forcar: anula zonas abertas e tenta armar.

### Desarmar

Nao criar rotina de automacao para desarmar sem PIN. Para manter seguranca, usar o dispositivo nativo:

- Dispositivo: `Alarme Casa`
- Habilitar no app Alexa: desarmar por voz com PIN de 4 digitos
- Frase recomendada: `Alexa, desarmar Alarme Casa`

A frase `desligar alarme casa` pode conflitar com alarmes de relogio da Alexa. Se houver conflito, usar `desarmar Alarme Casa`.

## Automacoes Existentes no Home Assistant

### Comandos Expostos para Alexa

As automacoes abaixo existem apenas para a Alexa conseguir ligar algo como se fosse um switch. Elas ficam desligadas e nao executam diretamente.

- `automation.alexa_ligar_alarme_comando`
  - Alias: `Alexa - Ligar alarme comando`
  - Exposta para Alexa como `Ligar Alarme Casa`
- `automation.alexa_forcar_ligar_alarme_comando`
  - Alias: `Alexa - Forcar ligar alarme comando`
  - Exposta para Alexa como `Forcar Ligar Alarme Casa`

### Automacoes Executor

As automacoes abaixo observam quando a Alexa liga as automacoes de comando e executam a logica real.

- `automation.alexa_executar_ligar_alarme`
  - Alias: `Alexa - Executar ligar alarme`
  - Modo: `restart`
  - Valida se a central esta disponivel
  - Valida se o alarme ja esta armado
  - Valida aberturas antes de armar
  - Se nao houver abertura, chama `alarm_control_panel.alarm_arm_away`
  - Anuncia sucesso/falha via `script.avisar_casa`, que fala no Google Nest e na Alexa
- `automation.alexa_executar_forcar_ligar_alarme`
  - Alias: `Alexa - Executar forcar ligar alarme`
  - Modo: `restart`
  - Se houver zonas abertas, pressiona `button.amt_porta_9009_anular_zonas_abertas`
  - Tenta armar o alarme
  - Anuncia sucesso/falha via `script.avisar_casa`, que fala no Google Nest e na Alexa

O `mode: restart` e importante: se uma mudanca nova chegar enquanto a sequencia anterior ainda esta rodando, a sequencia anterior e cancelada.

### Controle Numerico do Aquecedor

O comando de voz direto da skill Tuya/Smart Life pode limitar a temperatura maxima aceita pela Alexa, mesmo que o aquecedor aceite valores maiores no Home Assistant. Para contornar isso, o Home Assistant expoe um controle numerico proprio.

- `input_number.aquecedor_temperatura_alexa`
  - Nome Alexa: `Temperatura Aquecedor`
  - Minimo: `35`
  - Maximo: `65`
  - Passo: `1`
- `automation.aquecedor_temperatura_alexa_sincronizar`
  - Sincroniza o controle numerico com a temperatura alvo real de `climate.aquecedor`.
- `automation.alexa_aquecedor_temperatura_aplicar`
  - Quando o controle numerico muda, chama `climate.set_temperature` em `climate.aquecedor`.

Frases para testar depois da descoberta da Alexa:

- `Alexa, descobrir dispositivos`
- `Alexa, definir Temperatura Aquecedor para 42`
- `Alexa, ajustar Temperatura Aquecedor para 42`

Se a frase com `graus` falhar, testar sem `graus`, porque a entidade exposta e um controle numerico `RangeController`, nao um termostato Tuya.

### Script Central de Avisos

`script.avisar_casa` fica em `/config/scripts.yaml` e deve ser o padrao para avisos falados da casa.

Comportamento atual:

- `google: true` por padrao: fala em `media_player.som_escritorio` via Google Translate TTS.
- `alexa: true` por padrao: anuncia em `notify.echo_dot_de_thaina_announce` via Alexa Devices.
- `title` e opcional.
- `message` e obrigatorio.

Exemplo para usar em automacoes:

```yaml
- action: script.avisar_casa
  data:
    title: Chuva prevista
    message: "Chuva prevista, fechar as: {{ open_names | join(', ') }}."
```

Exemplo somente Alexa, sem Google Nest:

```yaml
- action: script.avisar_casa
  data:
    google: false
    alexa: true
    title: Teste Alexa
    message: Teste do Home Assistant na Alexa.
```

## Porta RX500 / RF433

Dispositivo Smart Life/Tuya integrado ao Home Assistant:

- Device HA: `053912ad56d55c7b428928e56032b7b4`
- `switch.porta_switch_1`: abrir porta
- `switch.porta_switch_2`: fechar porta

Automacao:

- `automation.amt8000_porta_rx500_acompanha_alarme`
- Alias: `AMT8000 - Porta RX500 acompanha alarme`
- Modo: `restart`

Comportamento:

- Quando o alarme vai para estado armado real (`armed_away`, `armed_home`, `armed_night`, `armed_custom_bypass`, `armed_vacation`):
  - desliga o canal de abrir
  - prepara/desliga o canal de fechar se necessario
  - envia `Fechar Porta` 3 vezes pelo RF433
- Quando o alarme muda de armado/triggered para `disarmed`:
  - desliga o canal de fechar
  - prepara/desliga o canal de abrir se necessario
  - envia um pulso inicial curto no `Abrir Porta`
  - envia mais 3 pulsos fortes no `Abrir Porta`

Esse desenho existe porque o modulo RF433 nao confirma estado; repetir pulsos reduz falhas de radio. O estado fisico da porta nao deve ser inferido pelos switches.

## Como Adicionar Coisas Novas para Alexa

### Regra Geral

1. Criar ou identificar a entidade no Home Assistant.
2. Decidir se ela deve ser exposta diretamente ou por uma entidade de comando.
3. Adicionar a entidade ao filtro `alexa.smart_home.filter.include_entities`.
4. Definir nome amigavel em `alexa.smart_home.entity_config`.
5. Rodar `check_config`.
6. Reiniciar o Home Assistant.
7. No app Alexa, executar `descobrir dispositivos`.
8. Se quiser frase natural, criar rotina no app Alexa.

### Expor Entidade Direta

Use para entidades que a Alexa entende bem:

- `light.*`
- `switch.*`
- `cover.*`
- `lock.*`
- `alarm_control_panel.*`
- sensores suportados

Exemplo:

```yaml
alexa:
  smart_home:
    filter:
      include_entities:
        - switch.exemplo
    entity_config:
      switch.exemplo:
        name: "Nome Natural"
        description: "Descricao curta"
```

### Expor Comando por Automacao

Use quando o comando precisa fazer validacoes, chamar varias acoes, anunciar erro, ou nao deve ser um controle direto.

Padrao usado neste ambiente:

1. Criar uma automacao de comando, que fica desligada e nao faz nada sozinha.
2. Expor essa automacao para Alexa como switch.
3. Criar uma automacao executor que dispara quando a automacao de comando muda para `on`.
4. A primeira acao da executor deve desligar a automacao de comando.

Modelo:

```yaml
- id: alexa_exemplo_comando
  alias: Alexa - Exemplo comando
  triggers:
    - trigger: event
      event_type: alexa_exemplo_comando_nunca
  actions:
    - stop: Entidade de comando para Alexa; nao executar diretamente.
  mode: single

- id: alexa_executar_exemplo
  alias: Alexa - Executar exemplo
  triggers:
    - trigger: state
      entity_id: automation.alexa_exemplo_comando
      to: "on"
  actions:
    - action: automation.turn_off
      target:
        entity_id: automation.alexa_exemplo_comando
    - action: script.alguma_acao_real
  mode: restart
```

Depois expor somente a automacao de comando:

```yaml
alexa:
  smart_home:
    filter:
      include_entities:
        - automation.alexa_exemplo_comando
    entity_config:
      automation.alexa_exemplo_comando:
        name: "Exemplo Casa"
        description: "Comando acionado pela Alexa"
```

### Quando Usar Rotina no App Alexa

Use rotina quando a frase desejada nao e natural para o tipo de dispositivo que a Alexa descobriu.

Exemplo:

- Entidade descoberta: `Ligar Alarme Casa`
- Frase desejada: `ligar alarme casa`
- Rotina:
  - Quando eu disser: `ligar alarme casa`
  - Acao: Casa inteligente -> `Ligar Alarme Casa` -> ligar

Nao usar rotina para desarmar alarme sem PIN.

### Adicionar Novo Aviso Falado

Para qualquer aviso novo, preferir chamar `script.avisar_casa` em vez de chamar `tts.speak` ou `notify.send_message` diretamente. Isso mantem Google Nest e Alexa sincronizados.

Modelo:

```yaml
- action: script.avisar_casa
  data:
    title: Nome curto do aviso
    message: Texto que deve ser falado.
```

Para um aviso que deve sair apenas na Alexa:

```yaml
- action: script.avisar_casa
  data:
    google: false
    alexa: true
    title: Nome curto do aviso
    message: Texto que deve ser falado.
```

## Manutencao

### Validar Home Assistant Publico

```bash
curl -sS --max-time 10 -o /dev/null -w '%{http_code}\n' https://ha.thainamonteiro.com.br/
```

Esperado: `200`.

### Validar Configuracao Antes de Reiniciar

```bash
ssh -i ~/.ssh/chave_servidor_casa thaina128@192.168.15.16 \
  'docker exec homeassistant-uswo0ko0w8c0gkc0kcso004c python -m homeassistant --script check_config --config /config'
```

### Reiniciar Home Assistant

```bash
ssh -i ~/.ssh/chave_servidor_casa thaina128@192.168.15.16 \
  'docker restart homeassistant-uswo0ko0w8c0gkc0kcso004c'
```

Validar que voltou saudavel:

```bash
ssh -i ~/.ssh/chave_servidor_casa thaina128@192.168.15.16 \
  'docker ps --filter name=homeassistant-uswo0ko0w8c0gkc0kcso004c --format "{{.Names}} {{.Status}}"'
```

### Editar `configuration.yaml`

Fazer backup antes:

```bash
ssh -i ~/.ssh/chave_servidor_casa thaina128@192.168.15.16 \
  'ts=$(date +%Y%m%d-%H%M%S); sudo cp /data/coolify/services/uswo0ko0w8c0gkc0kcso004c/configuration.yaml /data/coolify/services/uswo0ko0w8c0gkc0kcso004c/configuration.yaml.bak-$ts'
```

### Consultar Configuracao Alexa Atual

```bash
ssh -i ~/.ssh/chave_servidor_casa thaina128@192.168.15.16 \
  'sudo sed -n "14,45p" /data/coolify/services/uswo0ko0w8c0gkc0kcso004c/configuration.yaml'
```

### Testar Aviso Falado na Alexa

Pela UI do Home Assistant:

1. Abrir Ferramentas de desenvolvedor -> Acoes.
2. Usar modo YAML.
3. Executar:

```yaml
action: script.avisar_casa
data:
  google: false
  alexa: true
  title: Teste Alexa
  message: Teste do Home Assistant na Alexa.
```

Validacao esperada:

- O Echo Dot anuncia a mensagem.
- O log recente do Home Assistant nao mostra erro de `alexa_devices`, `notify.send_message` ou `script.avisar_casa`.

### Conferir Entidades Alexa Devices

```bash
ssh -i ~/.ssh/chave_servidor_casa thaina128@192.168.15.16 \
  "docker exec homeassistant-uswo0ko0w8c0gkc0kcso004c sh -lc 'grep -o \"notify.echo_dot_de_thaina_[a-z_]*\" /config/.storage/core.entity_registry | sort -u'"
```

Esperado:

- `notify.echo_dot_de_thaina_announce`
- `notify.echo_dot_de_thaina_speak`

### Conferir Logs da Alexa Devices

```bash
ssh -i ~/.ssh/chave_servidor_casa thaina128@192.168.15.16 \
  'docker logs --since 5m homeassistant-uswo0ko0w8c0gkc0kcso004c 2>&1 | grep -Ei "alexa_devices|notify.echo_dot|notify.send_message|avisar_casa|error|exception|traceback|amazon"'
```

### Validar Lambda

Pelo AWS CloudShell em `us-east-1`:

```bash
AWS_PAGER="" aws lambda get-function-configuration \
  --function-name home-assistant-alexa-smart-home \
  --region us-east-1 \
  --query '{FunctionArn:FunctionArn,Runtime:Runtime,Handler:Handler,Timeout:Timeout,MemorySize:MemorySize,Environment:Environment.Variables,LastUpdateStatus:LastUpdateStatus,Role:Role,Architectures:Architectures}' \
  --output json
```

Validar policy:

```bash
AWS_PAGER="" aws lambda get-policy \
  --function-name home-assistant-alexa-smart-home \
  --region us-east-1 \
  --query Policy \
  --output text | python3 -m json.tool
```

### Recriar Permissao da Skill na Lambda

Usar somente se a skill for recriada ou a policy for perdida.

```bash
AWS_PAGER="" aws lambda remove-permission \
  --function-name home-assistant-alexa-smart-home \
  --statement-id AlexaSmartHomeInvoke \
  --region us-east-1 || true

AWS_PAGER="" aws lambda add-permission \
  --function-name home-assistant-alexa-smart-home \
  --statement-id AlexaSmartHomeInvoke \
  --action lambda:InvokeFunction \
  --principal alexa-connectedhome.amazon.com \
  --event-source-token amzn1.ask.skill.e9339e08-fc33-47bb-a6ae-9a7b22924bd4 \
  --region us-east-1
```

## Troubleshooting

### Alexa Nao Descobre Dispositivos

1. Confirmar que `https://ha.thainamonteiro.com.br` abre.
2. Confirmar que a skill `Casa Thaina` esta ativada no app Alexa.
3. Confirmar que o account linking foi feito no app Alexa.
4. Confirmar que a Lambda tem `BASE_URL` correto.
5. Confirmar que a Lambda policy tem `alexa-connectedhome.amazon.com` e o Skill ID atual.
6. Confirmar `check_config` do Home Assistant.
7. Reiniciar Home Assistant e pedir nova descoberta.

### Skill Pede Para Vincular Conta de Novo

Refazer ativacao da skill no app Alexa. Se a URL abrir erro, testar:

- `https://ha.thainamonteiro.com.br/auth/authorize`
- `https://ha.thainamonteiro.com.br/auth/token` deve existir para OAuth, mas normalmente nao e acessada manualmente por GET.

### Endpoint da Skill Nao Salva

Erro comum:

`Please make sure that "Alexa Smart Home" is selected for the event source type`

Correcao:

- adicionar/recriar a permissao Lambda com `aws lambda add-permission`
- principal deve ser `alexa-connectedhome.amazon.com`
- `event-source-token` deve ser o Skill ID atual

### Alexa Confunde com Alarme de Relogio

Usar rotinas com frases completas:

- `ligar alarme casa` -> ligar `Ligar Alarme Casa`
- `forcar ligar alarme casa` -> ligar `Forcar Ligar Alarme Casa`

Para desligar, preferir:

- `desarmar Alarme Casa`

### Aquecedor Nao Aceita 42 Graus por Voz

Se `Alexa, definir o aquecedor para 38 graus` funciona, mas `42 graus` falha, provavelmente a Alexa esta usando a skill Tuya/Smart Life e tratando o dispositivo como termostato ambiente, com limite menor que o aquecedor real.

Usar o controle exposto pelo Home Assistant:

1. Pedir `Alexa, descobrir dispositivos`.
2. Confirmar se aparece `Temperatura Aquecedor`.
3. Testar:
   - `Alexa, definir Temperatura Aquecedor para 42`
   - `Alexa, ajustar Temperatura Aquecedor para 42`
4. Conferir no Home Assistant:
   - `input_number.aquecedor_temperatura_alexa` deve ficar em `42`.
   - `climate.aquecedor` deve ficar com atributo `temperature: 42`.

Se a Alexa continuar usando o dispositivo Tuya antigo chamado `Aquecedor`, renomear ou desativar esse dispositivo no app Alexa para evitar conflito de nomes.

### Alexa Devices Pede Reautenticacao ou Para de Falar

1. Em Home Assistant, abrir Configuracoes -> Dispositivos e servicos -> `Alexa Devices`.
2. Se aparecer reautenticacao, refazer login na conta Amazon da casa.
3. Se o fluxo travar em captcha/verificacao de celular, concluir no navegador real e usar o codigo/URL de autorizacao somente na sessao corrente; nao salvar em arquivo de documentacao.
4. Conferir se `notify.echo_dot_de_thaina_announce` ainda existe.
5. Conferir logs de `alexa_devices`.
6. Se o erro for `AttributeError: 'NoneType' object has no attribute 'get'` dentro de `aioamazondevices/api.py`, verificar se o hotfix do container foi perdido em recriacao/upgrade.

### Porta RX500 Nao Abre/Fecha Sempre

O modulo e RF433 e nao tem feedback de estado. A automacao ja repete pulsos. Se falhar:

1. Conferir se `switch.porta_switch_1` abre no HA.
2. Conferir se `switch.porta_switch_2` fecha no HA.
3. Conferir historico da automacao `AMT8000 - Porta RX500 acompanha alarme`.
4. Evitar reduzir tempos dos pulsos sem teste fisico.

## Fontes

- Home Assistant Alexa Smart Home:
  `https://www.home-assistant.io/integrations/alexa.smart_home/`
- Amazon Developer Console:
  `https://developer.amazon.com/alexa/console/ask`
- AWS Lambda Console:
  `https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1`
