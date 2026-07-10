# Plano: Alexa + IA para Analisar Cameras e Frigate

Documento de planejamento criado em 2026-07-10 para adicionar uma funcao em que o usuario fala com a Alexa, o Home Assistant analisa cameras/Frigate com IA multimodal e a Alexa responde em voz alta.

Nao registrar neste repositorio senhas, tokens, Authorization headers, URLs OAuth temporarias, imagens sensiveis, snapshots de cameras, chaves de provedores de IA ou credenciais da Amazon/Home Assistant.

## Objetivo

Permitir comandos como:

- `Alexa, o que tem nas cameras da casa?`
- `Alexa, tem alguem no portao?`
- `Alexa, o carro esta na garagem?`
- `Alexa, veja as cameras antes de ligar o alarme`

Resultado esperado:

1. A Alexa dispara um comando no Home Assistant.
2. O Home Assistant captura imagens ou eventos recentes das cameras/Frigate.
3. Uma IA multimodal analisa as imagens/eventos.
4. O Home Assistant resume a resposta em portugues.
5. A Alexa fala a resposta usando `script.avisar_casa`.

## Estado Atual que Sera Reaproveitado

- Home Assistant publico em `https://ha.thainamonteiro.com.br`.
- Alexa Smart Home Skill `Casa Thaina` ja envia comandos da Alexa para o Home Assistant.
- Integracao `Alexa Devices` ja permite o caminho inverso: Home Assistant falando no Echo Dot.
- Script central `script.avisar_casa` ja anuncia no Google Nest e na Alexa.
- Frigate aparece no ambiente Home Assistant e deve ser validado como fonte de cameras/eventos.

## Decisao de Arquitetura

### Caminho Recomendado para MVP

Usar Alexa Smart Home Skill + rotina da Alexa + automacao do Home Assistant.

Fluxo:

```text
Voz do usuario
  -> Rotina Alexa
  -> Liga entidade de comando exposta pelo HA
  -> Automacao HA
  -> LLM Vision / IA multimodal
  -> script.avisar_casa
  -> Echo Dot fala a resposta
```

Vantagens:

- Usa a infraestrutura ja configurada.
- Nao precisa criar outra skill agora.
- Funciona mesmo se a IA demorar mais que o tempo normal de resposta da Alexa, porque a resposta final e enviada pelo Home Assistant como anuncio.
- Facil de testar e manter em YAML.

Limitacao:

- A Alexa nao passa uma pergunta livre dinamica para o Home Assistant. Cada frase natural deve virar uma rotina ou comando especifico.

### Caminho Avancado Futuro

Criar uma Custom Alexa Skill separada, com intents e slots.

Fluxo:

```text
Alexa Custom Skill
  -> Lambda de intent
  -> Home Assistant API
  -> IA multimodal
  -> resposta direta da skill
```

Vantagens:

- Permite perguntas mais naturais e dinamicas.
- Pode ter intents como `PerguntarCameraIntent`, `CameraSlot`, `ObjetoSlot`.

Limitacoes:

- A skill precisa responder em cerca de 8 segundos. Analise de imagem/video pode estourar esse tempo.
- Progressive Response melhora a percepcao de espera, mas nao aumenta o limite total.
- Exige outro modelo de interacao na Amazon Developer Console.

Conclusao: comecar pelo MVP assincrono via Home Assistant e so criar Custom Skill se o MVP ficar limitado.

## Integracoes Necessarias

### Frigate

Validar:

- Frigate acessivel pelo Home Assistant.
- Integracao Frigate instalada pelo HACS, se ainda nao estiver.
- MQTT configurado, porque a integracao Frigate depende de MQTT para muitas entidades.
- Cameras Frigate expostas como `camera.*` no Home Assistant.
- Eventos/reviews do Frigate disponiveis para automacoes.

Referencia:

- `https://docs.frigate.video/integrations/home-assistant/`

### LLM Vision

Instalar pelo HACS:

- Integracao: `LLM Vision`
- Repositorio: `valentinfrlch/ha-llmvision`

Uso previsto:

- Analisar cameras atuais.
- Analisar imagens/snapshots.
- Analisar eventos do Frigate.
- Opcionalmente manter timeline de eventos para consultas posteriores.

Referencia:

- `https://llmvision.org/`
- `https://github.com/valentinfrlch/ha-llmvision`

### Provedor de IA

Opcoes:

- Cloud simples: OpenAI, Gemini, Anthropic ou OpenRouter.
- Local/privado: Ollama, LocalAI ou Open WebUI com modelo vision.

Recomendacao inicial:

- Comecar com provedor cloud para validar a experiencia.
- Depois avaliar provedor local se privacidade/custo for prioridade.

Cuidados:

- Cameras internas podem conter informacao sensivel.
- Definir claramente quais cameras podem ser enviadas para IA cloud.
- Evitar salvar snapshots em `/config/www`, porque arquivos ali podem ficar publicos por URL.
- Preferir `/media` quando a integracao precisar salvar imagens temporarias.

## MVP Proposto

### Comando 1: Analise Geral da Casa

Frase:

`Alexa, o que tem nas cameras da casa?`

Rotina Alexa:

- Quando eu disser: `o que tem nas cameras da casa`
- Acao: Casa inteligente -> ligar `Analisar Cameras Casa`

Entidade HA exposta:

- `automation.alexa_analisar_cameras_comando`
- Nome Alexa: `Analisar Cameras Casa`

Comportamento:

1. Desliga a entidade de comando para voltar ao estado `off`.
2. Chama `script.analisar_cameras_casa`.
3. O script analisa cameras selecionadas.
4. A resposta e falada na Alexa.

### Comando 2: Verificar Portao

Frase:

`Alexa, tem alguem no portao?`

Rotina Alexa:

- Quando eu disser: `tem alguem no portao`
- Acao: Casa inteligente -> ligar `Analisar Portao`

Entidade HA exposta:

- `automation.alexa_analisar_portao_comando`
- Nome Alexa: `Analisar Portao`

Comportamento:

- Analisa somente camera(s) do portao/entrada.
- Responde curto: pessoa, veiculo, animal, portao aberto ou nada relevante.

### Comando 3: Verificar Antes de Armar

Frase:

`Alexa, verificar casa antes de ligar o alarme`

Comportamento:

- Analisa cameras externas principais.
- Verifica tambem sensores de portas/janelas ja existentes.
- Fala um resumo.
- Nao arma o alarme automaticamente no MVP.

## YAML Base Proposto

Os nomes de cameras abaixo sao placeholders. Antes de implementar, listar as entidades reais `camera.*` do Home Assistant e substituir.

### Script de Analise Geral

O campo exato retornado em `response_variable` deve ser validado na versao instalada do LLM Vision. O nome `response_text` abaixo e propositalmente tratado como rascunho.

```yaml
analisar_cameras_casa:
  alias: Analisar cameras da casa
  description: Analisa cameras selecionadas com IA e fala o resumo na Alexa.
  mode: single
  sequence:
    - action: script.avisar_casa
      data:
        google: false
        alexa: true
        title: Cameras
        message: Estou analisando as cameras da casa.

    - action: llmvision.image_analyzer
      data:
        image_entity:
          - camera.portao
          - camera.garagem
          - camera.fundos
        message: >
          Analise as imagens das cameras da casa. Responda em portugues do Brasil,
          em no maximo duas frases. Diga somente pessoas, veiculos, animais,
          portoes abertos, movimentacao suspeita ou riscos. Se nao houver nada
          importante, diga que nao viu nada relevante.
        max_tokens: 120
        temperature: 0.1
      response_variable: analise_cameras

    - action: script.avisar_casa
      data:
        google: false
        alexa: true
        title: Cameras
        message: "{{ analise_cameras.response_text | default('Nao consegui concluir a analise das cameras.') }}"
```

### Automacao de Comando para Alexa

```yaml
- id: alexa_analisar_cameras_comando
  alias: Alexa - Analisar cameras comando
  description: Entidade de comando para Alexa acionar analise de cameras.
  triggers:
    - trigger: event
      event_type: alexa_analisar_cameras_comando_nunca
  conditions: []
  actions:
    - stop: Entidade de comando para Alexa; nao executar diretamente.
  mode: single

- id: alexa_executar_analisar_cameras
  alias: Alexa - Executar analise de cameras
  description: Executa analise de cameras quando a Alexa liga a entidade de comando.
  triggers:
    - trigger: state
      entity_id: automation.alexa_analisar_cameras_comando
      to: "on"
  conditions: []
  actions:
    - action: automation.turn_off
      target:
        entity_id: automation.alexa_analisar_cameras_comando
    - action: script.analisar_cameras_casa
  mode: restart
```

### Expor para Alexa Smart Home

Adicionar em `alexa.smart_home.filter.include_entities`:

```yaml
- automation.alexa_analisar_cameras_comando
```

Adicionar em `alexa.smart_home.entity_config`:

```yaml
automation.alexa_analisar_cameras_comando:
  name: "Analisar Cameras Casa"
  description: "Comando para analisar cameras da casa com IA"
```

Depois:

1. Rodar `check_config`.
2. Reiniciar Home Assistant.
3. No app Alexa, descobrir dispositivos.
4. Criar rotina com a frase desejada.

## Plano de Implementacao

### Etapa 1 - Inventario e Validacao

1. Listar entidades `camera.*` existentes no Home Assistant.
2. Confirmar quais cameras sao do Frigate.
3. Confirmar se MQTT/Frigate estao saudaveis.
4. Escolher cameras do MVP:
   - portao/entrada
   - garagem
   - fundos
5. Definir quais cameras nunca devem ser enviadas para IA cloud.

Saida esperada:

- Lista de cameras aprovadas para analise.
- Lista de cameras bloqueadas por privacidade.

### Etapa 2 - Instalar LLM Vision

1. HACS -> Integrations -> buscar `LLM Vision`.
2. Instalar e reiniciar HA.
3. Settings -> Devices & services -> Add Integration -> `LLM Vision`.
4. Configurar provider inicial.
5. Testar `llmvision.image_analyzer` em uma camera pelo Developer Tools.

Saida esperada:

- Uma chamada manual retorna uma descricao curta da camera.

### Etapa 3 - Criar Script Central

1. Criar `script.analisar_cameras_casa`.
2. Usar `script.avisar_casa` para:
   - avisar que iniciou a analise;
   - falar a resposta final;
   - falar erro amigavel se a IA falhar.
3. Limitar resposta a duas frases.
4. Usar `mode: single` ou `mode: restart` conforme teste pratico.

Saida esperada:

- Executar o script manualmente faz a Alexa responder com resumo.

### Etapa 4 - Criar Comando Alexa

1. Criar `automation.alexa_analisar_cameras_comando`.
2. Criar `automation.alexa_executar_analisar_cameras`.
3. Expor a automacao de comando em `alexa.smart_home`.
4. Rodar discovery no app Alexa.
5. Criar rotina: `o que tem nas cameras da casa`.

Saida esperada:

- Frase na Alexa dispara a analise.
- Resposta sai no Echo Dot quando o HA terminar.

### Etapa 5 - Criar Comandos Especificos

Adicionar depois do MVP:

- `Analisar Portao`
- `Analisar Garagem`
- `Analisar Fundos`
- `Verificar Casa Antes do Alarme`

Cada comando pode chamar o mesmo script com parametros:

```yaml
action: script.analisar_cameras_com_prompt
data:
  cameras:
    - camera.portao
  pergunta: "Tem alguem no portao?"
```

Se o Home Assistant dificultar lista dinamica em script, criar scripts separados por camera.

## Testes

### Teste Manual da IA

Pelo Developer Tools -> Acoes:

```yaml
action: llmvision.image_analyzer
data:
  image_entity:
    - camera.portao
  message: "Descreva em portugues o que aparece nesta camera em uma frase."
  max_tokens: 80
  temperature: 0.1
```

Validar:

- A IA responde.
- Latencia aceitavel.
- Resposta nao inventa detalhes perigosos.

### Teste Manual do Script

```yaml
action: script.analisar_cameras_casa
```

Validar:

- Alexa fala "Estou analisando..." ou equivalente.
- Depois fala o resumo.
- Logs sem erro de `llmvision`, `alexa_devices`, `notify.send_message` ou `script.avisar_casa`.

### Teste pela Alexa

Frase:

`Alexa, o que tem nas cameras da casa`

Validar:

- Rotina liga a entidade correta.
- Entidade volta para `off`.
- Script executa uma unica vez.
- Resposta sai no Echo Dot.

### Teste de Falha

Simular:

- Provider de IA indisponivel.
- Camera indisponivel.
- Frigate fora do ar.

Resposta esperada:

- Alexa fala erro curto e seguro, por exemplo:
  `Nao consegui analisar as cameras agora.`

## Criterios de Aceite

- Comando por voz dispara a analise sem tocar em credenciais.
- Alexa responde em ate alguns segundos ou anuncia que esta analisando.
- Resultado final e falado no Echo Dot.
- Nenhum snapshot sensivel fica em pasta publica.
- Automacao nao envia cameras internas para IA cloud sem autorizacao explicita.
- Logs do HA nao mostram erro apos teste.
- Documentacao atualizada com entidades, scripts, cameras usadas e provider escolhido.

## Riscos e Mitigacoes

### Latencia da IA

Risco:

- Analise pode levar mais que o esperado.

Mitigacao:

- Usar fluxo assincrono: Alexa so dispara; Home Assistant fala quando terminar.
- Reduzir numero de cameras por comando.
- Limitar `max_tokens`.

### Privacidade

Risco:

- Imagens internas ou sensiveis serem enviadas para provider cloud.

Mitigacao:

- Comecar com cameras externas.
- Manter lista de cameras permitidas.
- Avaliar provider local para cameras internas.

### Alucinacao da IA

Risco:

- IA afirmar algo que nao esta claro na imagem.

Mitigacao:

- Prompt obrigando incerteza:
  `Se nao tiver certeza, diga que nao conseguiu confirmar.`
- Evitar automacoes criticas baseadas apenas na IA.
- Nao usar resposta de IA para destrancar portas ou desativar alarme.

### Excesso de Anuncios

Risco:

- Echo Dot falar demais.

Mitigacao:

- Criar cooldown por comando.
- Usar `mode: single` ou `restart`.
- Restringir respostas a perguntas manuais no MVP.

## Possibilidades Depois do MVP

- Resumo ao armar o alarme:
  `Alarme ligado. Garagem vazia. Janela da suite aberta.`
- Analise de evento Frigate:
  `Pessoa vista no portao ha dois minutos carregando uma caixa.`
- Confirmacao de entrega:
  `O pacote parece estar na entrada.`
- Verificacao de garagem:
  `O carro branco esta na garagem.`
- Verificacao antes de abrir portao:
  `Nao vejo pessoa ou veiculo encostado no portao.`
- Timeline de eventos com LLM Vision para perguntar depois o que aconteceu.

## Referencias

- Home Assistant Alexa Smart Home:
  `https://www.home-assistant.io/integrations/alexa.smart_home/`
- Frigate Home Assistant Integration:
  `https://docs.frigate.video/integrations/home-assistant/`
- LLM Vision:
  `https://llmvision.org/`
- LLM Vision GitHub:
  `https://github.com/valentinfrlch/ha-llmvision`
- Alexa Progressive Response:
  `https://developer.amazon.com/en-US/docs/alexa/custom-skills/send-the-user-a-progressive-response.html`
