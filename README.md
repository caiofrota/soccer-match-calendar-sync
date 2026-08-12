# Soccer Match Calendar Sync

Sincroniza partidas de futebol da API pública do [SportScore](https://sportscore.com/) com o Google
Calendar ou gera um arquivo `.ics`. O sincronizador aceita a agenda de um time ou descobre as partidas de
uma competição por sua classificação, chaveamento e agendas dos participantes.

## Comportamento da sincronização

- Partidas reagendadas movem o evento existente quando há uma única correspondência segura.
- Partidas adiadas sem nova data permanecem no horário anterior com o prefixo `ADIADO`.
- Partidas canceladas permanecem visíveis com o prefixo `CANCELADO`.
- A ausência de uma partida na resposta não é interpretada como cancelamento.
- Os eventos guardam metadados privados do SportScore para evitar duplicações futuras.
- Horários são lidos com o fuso informado pelo provedor e publicados em `America/Fortaleza`.

## Adicione ao seu calendário

Estes são calendários comunitários e não oficiais, atualizados automaticamente com dados do
[SportScore](https://sportscore.com/). Datas e horários podem mudar; confirme informações críticas
nos organizadores oficiais.

| Calendário | Google Calendar | Apple Calendar, Outlook e outros |
| --- | --- | --- |
| Champions League | [Adicionar](https://calendar.google.com/calendar/u/0/r?cid=401be6a3ffc7a181b7569f3dfa362cd7bf797ac26d05f5b49ec3e8043a42bad8%40group.calendar.google.com) | [Endereço iCal](https://calendar.google.com/calendar/ical/401be6a3ffc7a181b7569f3dfa362cd7bf797ac26d05f5b49ec3e8043a42bad8%40group.calendar.google.com/public/basic.ics) |
| Copa América | [Adicionar](https://calendar.google.com/calendar/u/0/r?cid=fe1896bb7a29bfc75ceef4e36c22187fa0b3ccb3a60c7275f07bc7dc8b498531%40group.calendar.google.com) | [Endereço iCal](https://calendar.google.com/calendar/ical/fe1896bb7a29bfc75ceef4e36c22187fa0b3ccb3a60c7275f07bc7dc8b498531%40group.calendar.google.com/public/basic.ics) |
| Eurocopa | [Adicionar](https://calendar.google.com/calendar/u/0/r?cid=6c59ceb5c9d3c0d508a7c365fac106b18a2b1f5e8cf61f256b38b19e8c206dc1%40group.calendar.google.com) | [Endereço iCal](https://calendar.google.com/calendar/ical/6c59ceb5c9d3c0d508a7c365fac106b18a2b1f5e8cf61f256b38b19e8c206dc1%40group.calendar.google.com/public/basic.ics) |
| Copa da Liga Inglesa | [Adicionar](https://calendar.google.com/calendar/u/0/r?cid=28df770f8678c4f6890da87576397504c150669c30d8e2ed6d23fd0262a441a7%40group.calendar.google.com) | [Endereço iCal](https://calendar.google.com/calendar/ical/28df770f8678c4f6890da87576397504c150669c30d8e2ed6d23fd0262a441a7%40group.calendar.google.com/public/basic.ics) |
| Ceará | [Adicionar](https://calendar.google.com/calendar/u/0/r?cid=2229d57329c1589bf08b9a2752fc29be6fcb7139409a300fb9bd63f866d24a60%40group.calendar.google.com) | [Endereço iCal](https://calendar.google.com/calendar/ical/2229d57329c1589bf08b9a2752fc29be6fcb7139409a300fb9bd63f866d24a60%40group.calendar.google.com/public/basic.ics) |
| Brasil masculino | [Adicionar](https://calendar.google.com/calendar/u/0/r?cid=5e4c412c5caba27497079e63dd4f54b4eb50f6dafe409a07a58ec63069199558%40group.calendar.google.com) | [Endereço iCal](https://calendar.google.com/calendar/ical/5e4c412c5caba27497079e63dd4f54b4eb50f6dafe409a07a58ec63069199558%40group.calendar.google.com/public/basic.ics) |
| Copa do Mundo masculina | [Adicionar](https://calendar.google.com/calendar/u/0/r?cid=055de4983aede32a642bd40331aeffaa1bf2c0f2e65919a432499464f24f28c0%40group.calendar.google.com) | [Endereço iCal](https://calendar.google.com/calendar/ical/055de4983aede32a642bd40331aeffaa1bf2c0f2e65919a432499464f24f28c0%40group.calendar.google.com/public/basic.ics) |
| Copa do Mundo feminina | [Adicionar](https://calendar.google.com/calendar/u/0/r?cid=a8ab46505d7334594054a6bdc61c7c40c8239961ade4785f164025c2d7cd9996%40group.calendar.google.com) | [Endereço iCal](https://calendar.google.com/calendar/ical/a8ab46505d7334594054a6bdc61c7c40c8239961ade4785f164025c2d7cd9996%40group.calendar.google.com/public/basic.ics) |
| Brasil feminino | [Adicionar](https://calendar.google.com/calendar/u/0/r?cid=101b0eee6b70857535f94f4fd4cfa5408cd6f1b299094e2d2f29a253fd2fc2ec%40group.calendar.google.com) | [Endereço iCal](https://calendar.google.com/calendar/ical/101b0eee6b70857535f94f4fd4cfa5408cd6f1b299094e2d2f29a253fd2fc2ec%40group.calendar.google.com/public/basic.ics) |

No Google Calendar, use **Adicionar** e confirme a assinatura. Em outros aplicativos, copie o
**Endereço iCal** e escolha a opção de assinar um calendário por URL. Não baixe e importe o arquivo:
a importação cria uma cópia que não recebe atualizações futuras. O aplicativo pode demorar algumas
horas para buscar uma alteração publicada pelo Google.

### Ativação pelo administrador

Antes de divulgar os links, o proprietário deve abrir cada calendário no Google Calendar pelo
computador e acessar **Configurações e compartilhamento → Autorizações de acesso aos eventos →
Disponibilizar ao público**. Selecione a opção que mostra todos os detalhes dos eventos.

Divulgue somente o endereço **Público no formato iCal**. O endereço secreto nunca deve ser publicado,
versionado no repositório nem enviado a terceiros. Depois da ativação, abra o endereço iCal em uma
janela anônima e confirme que ele responde sem login. Em 12 de agosto de 2026, os nove endereços
públicos ainda respondiam `404`; conclua esta ativação antes de divulgar ou mesclar os links.

## Configuração do Google Calendar

1. Habilite a Google Calendar API em um projeto Google Cloud.
2. Crie uma conta de serviço e baixe sua chave JSON como `credentials.json`.
3. Compartilhe cada calendário com o e-mail da conta de serviço, permitindo alterar eventos.
4. No GitHub, salve o conteúdo da chave no secret `GOOGLE_CREDENTIALS_JSON`.

## Instalação e uso

```bash
uv sync --locked

# Agenda de um time
uv run python match_sync.py gcalendar \
  --target-type team \
  --slug ceara \
  --calendar-id "seu-calendario@group.calendar.google.com"

# Partidas de uma competição
uv run python match_sync.py gcalendar \
  --target-type competition \
  --slug fifa-world-cup \
  --calendar-id "seu-calendario@group.calendar.google.com"

# Arquivo ICS
uv run python match_sync.py ics \
  --target-type team \
  --slug brazil-women \
  --output calendar.ics
```

## Alvos configurados no GitHub Actions

| Calendário | Tipo | Slug SportScore |
| --- | --- | --- |
| Champions League | competição | `uefa-champions-league` |
| Copa América | competição | `conmebol-copa-america` |
| Eurocopa | competição | `uefa-european-championship` |
| Copa da Liga Inglesa | competição | `english-football-league-cup` |
| Ceará | time | `ceara` |
| Brasil masculino | time | `brazil` |
| Copa do Mundo masculina | competição | `fifa-world-cup` |
| Copa do Mundo feminina | competição | `fifa-womens-world-cup` |
| Brasil feminino | time | `brazil-women` |

Cada calendário usa uma variável em
`Settings > Secrets and variables > Actions > Variables`:

- `GOOGLE_CALENDAR_ID_CHAMPIONS_LEAGUE`
- `GOOGLE_CALENDAR_ID_COPA_AMERICA`
- `GOOGLE_CALENDAR_ID_EUROCOPA`
- `GOOGLE_CALENDAR_ID_ENGLISH_LEAGUE_CUP`
- `GOOGLE_CALENDAR_ID_CEARA`
- `GOOGLE_CALENDAR_ID_BRAZIL`
- `GOOGLE_CALENDAR_ID_WORLD_CUP`
- `GOOGLE_CALENDAR_ID_WOMENS_WORLD_CUP`
- `GOOGLE_CALENDAR_ID_BRAZIL_WOMEN`

As nove variáveis estão configuradas. O SportScore já reconhece a Copa do Mundo Feminina,
mas só publicará jogos de 2027 quando a programação estiver disponível no provedor.

## Automação

O workflow executa às `08:00` e `20:00` UTC (`05:00` e `17:00` em Fortaleza). Também pode ser
executado manualmente pela aba Actions. Workflows agendados podem iniciar alguns minutos depois do
horário durante períodos de alta demanda do GitHub.

## Testes

```bash
uv run python -m unittest -v
```

## CI/CD

O repositório é um único worker/CLI Python 3.11. O check obrigatório `CI / required` valida o
lockfile, formatação, lint, tipos, sintaxe, testes e segurança dos workflows em pull requests, pushes
para `main` e execuções manuais. Ele não recebe segredos nem altera calendários.

O workflow agendado existente é a entrega operacional: usa credenciais de produção para atualizar
os calendários duas vezes ao dia. Build, publicação de pacote, banco de dados, browser, mobile e
monorepo não se aplicam. Testes contra SportScore e Google Calendar reais ficam fora do check porque
dependem de serviços externos ou de produção; a suíte obrigatória usa mocks e contratos
determinísticos. As razões, limites e condição de revisão estão registradas em
[`docs/decisions/0001-ci-cd.md`](docs/decisions/0001-ci-cd.md).

## Créditos

Os dados de partidas, competições, times, horários e status utilizados por este projeto são
fornecidos pelo [SportScore](https://sportscore.com/). A disponibilidade e a atualização dessas
informações dependem do provedor.

## Licença

MIT.
