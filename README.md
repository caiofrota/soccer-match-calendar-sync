# Web Soccer Match Crawler

Sincroniza partidas de futebol da API pública do [SportScore](https://sportscore.com/) com o Google
Calendar ou gera um arquivo `.ics`. O crawler aceita a agenda de um time ou descobre as partidas de
uma competição por sua classificação, chaveamento e agendas dos participantes.

## Comportamento da sincronização

- Partidas reagendadas movem o evento existente quando há uma única correspondência segura.
- Partidas adiadas sem nova data permanecem no horário anterior com o prefixo `ADIADO`.
- Partidas canceladas permanecem visíveis com o prefixo `CANCELADO`.
- A ausência de uma partida na resposta não é interpretada como cancelamento.
- Os eventos guardam metadados privados do SportScore para evitar duplicações futuras.
- Horários são lidos com o fuso informado pelo provedor e publicados em `America/Fortaleza`.

## Configuração do Google Calendar

1. Habilite a Google Calendar API em um projeto Google Cloud.
2. Crie uma conta de serviço e baixe sua chave JSON como `credentials.json`.
3. Compartilhe cada calendário com o e-mail da conta de serviço, permitindo alterar eventos.
4. No GitHub, salve o conteúdo da chave no secret `GOOGLE_CREDENTIALS_JSON`.

## Instalação e uso

```bash
pip install -r requirements.txt

# Agenda de um time
python crawler.py gcalendar \
  --target-type team \
  --slug ceara \
  --calendar-id "seu-calendario@group.calendar.google.com"

# Partidas de uma competição
python crawler.py gcalendar \
  --target-type competition \
  --slug fifa-world-cup \
  --calendar-id "seu-calendario@group.calendar.google.com"

# Arquivo ICS
python crawler.py ics \
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

Os sete calendários anteriores conservam seus IDs. Para habilitar os dois novos, crie os calendários,
compartilhe-os com a conta de serviço e configure estas variáveis em
`Settings > Secrets and variables > Actions > Variables`:

- `GOOGLE_CALENDAR_ID_WOMENS_WORLD_CUP`
- `GOOGLE_CALENDAR_ID_BRAZIL_WOMEN`

Sem essas variáveis, os dois jobs são ignorados de forma segura. O SportScore já reconhece a Copa do
Mundo Feminina, mas só publicará jogos de 2027 quando a programação estiver disponível no provedor.

## Automação

O workflow executa às `08:00` e `20:00` UTC (`05:00` e `17:00` em Fortaleza). Também pode ser
executado manualmente pela aba Actions. Workflows agendados podem iniciar alguns minutos depois do
horário durante períodos de alta demanda do GitHub.

## Testes

```bash
python -m unittest -v
```

## Licença

MIT. Os dados esportivos são fornecidos pelo SportScore e estão sujeitos à disponibilidade e às
condições do provedor.
