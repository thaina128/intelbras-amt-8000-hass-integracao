# Alertas de chuva com portas e janelas abertas

Documento operacional da automacao configurada no Home Assistant em 2026-07-11.

O objetivo e avisar sobre chuva sem gerar alerta assim que uma porta ou janela e
aberta. O primeiro aviso exige uma abertura continua de 10 minutos. Uma mudanca
para chuva muito forte pode escalar o mesmo episodio para o estagio 2.

Nao registrar neste repositorio tokens de notificacao, credenciais OAuth, senhas
de e-mail ou outros segredos usados pelos servicos de notificacao.

## Entidades de controle

- Helper persistente: `input_select.chuva_aberturas_nivel`
- Opcoes do helper: `nenhum`, `estagio_1` e `estagio_2`
- Estagio 1: `automation.amt_avisar_janela_aberta_quando_chover`
- Estagio 2: `automation.amt_chuva_forte_com_abertura_estagio_2`
- Reset: `automation.amt_reset_aviso_de_chuva_com_aberturas`
- Clima: `weather.forecast_casa`

O ID interno preservado da automacao original do estagio 1 e
`amt_janelas_abertas_alerta_chuva`.

## Aberturas monitoradas

- `binary_sensor.intelbras_zona_1_portao_pedestre`
- `binary_sensor.intelbras_zona_2_portao_carro`
- `binary_sensor.intelbras_zona_3_porta_entrada`
- `binary_sensor.intelbras_zona_4_porta_fundos`
- `binary_sensor.intelbras_zona_5_janela_cozinha`
- `binary_sensor.intelbras_zona_6_janela_quarto_suite`
- `binary_sensor.intelbras_zona_7_janela_closet`
- `binary_sensor.intelbras_zona_8_janela_quarto_q3`
- `binary_sensor.intelbras_zona_9_janela_escritorio`
- `binary_sensor.amt_porta_9009_zona_11`

## Estagio 1

O estagio 1 pode ser avaliado quando:

- uma abertura permanece em `on` durante 10 minutos;
- o estado do clima muda para uma condicao de chuva suportada; ou
- a verificacao periodica de 5 minutos detecta chuva atual ou prevista.

Antes de avisar, a automacao exige:

- helper em `nenhum`;
- pelo menos uma abertura em `on` ha 600 segundos ou mais;
- clima atual diferente de `pouring`, reservado para o estagio 2; e
- chuva atual ou previsao horaria de chuva nos proximos 10 minutos.

Quando essas condicoes sao atendidas, o helper muda para `estagio_1` antes do
aviso. Isso impede repeticoes no mesmo episodio. O aviso usa
`script.avisar_casa`, que fala nos dispositivos de voz configurados na casa.

## Estagio 2

O estagio 2 e disparado quando `weather.forecast_casa` muda para `pouring` com
alguma abertura aberta. Ele tambem e avaliado quando uma abertura passa para
`on` enquanto o clima ja esta em `pouring`.

O estagio 2 pode escalar um episodio que ja recebeu o estagio 1, mas nao repete
se o helper ja estiver em `estagio_2`. Ao executar, ele:

- muda o helper para `estagio_2`;
- chama `script.avisar_casa` com mensagem urgente;
- envia notificacao critica para `notify.mobile_app_iphonethaina`; e
- cria uma notificacao persistente no Home Assistant.

Destinos pendentes em 2026-07-11:

- o celular da Ingridi ainda nao esta registrado na integracao Mobile App;
- o Home Assistant ainda nao possui um servico de e-mail configurado;
- os e-mails `thaina128@gmail.com` e `ingridi.silveira1@gmail.com` devem ser
  adicionados ao estagio 2 depois da configuracao do Google Mail ou SMTP.

Para o Google Mail, usar um projeto Google Cloud e um cliente OAuth exclusivos
do Home Assistant. Nao reutilizar nem alterar as credenciais do projeto
`PublicaMundo Production`.

## Reset e deduplicacao

A automacao de reset observa o fechamento das aberturas e a inicializacao do
Home Assistant. O helper volta para `nenhum` somente quando todas as aberturas
monitoradas estao fechadas.

Consequencias:

- abrir e fechar a mesma abertura antes de 10 minutos nao gera aviso;
- o estagio 1 ocorre no maximo uma vez enquanto alguma abertura continuar
  aberta;
- o estagio 2 ocorre no maximo uma vez no mesmo episodio;
- uma nova mudanca para chuva forte nao repete o alerta enquanto ainda existir
  abertura do episodio anterior; e
- fechar todas as aberturas libera um novo ciclo de notificacao.

## Implantacao e validacao

Arquivos alterados na instancia:

- `/config/automations.yaml`
- `/data/coolify/services/uswo0ko0w8c0gkc0kcso004c/configuration.yaml`

Backups criados antes da alteracao:

- `/config/automations.yaml.bak-rain-stages-20260711-184415`
- `/data/coolify/services/uswo0ko0w8c0gkc0kcso004c/configuration.yaml.bak-rain-stages-20260711-184415`

Validacoes realizadas:

- `python -m homeassistant --script check_config --config /config` passou;
- o container do Home Assistant reiniciou e voltou a responder;
- as tres automacoes carregaram com estado `on`;
- o helper carregou com estado `nenhum`;
- nao houve erro relevante nos logs de inicializacao; e
- nenhum alerta de chuva foi disparado artificialmente durante a validacao.

Depois de adicionar um novo celular ou servico de e-mail, conferir o nome exato
do servico em Ferramentas de desenvolvedor e validar a configuracao antes de
reiniciar o Home Assistant.
