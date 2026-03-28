# Avaliação Big Data — Top 1000 Jogos Steam (2024–2026)

Projeto acadêmico de Big Data que coleta, armazena e analisa dados públicos dos 1000 jogos mais populares da plataforma Steam.

**Dataset:** [Top 1000 Steam Games 2024–2026 (Kaggle)](https://www.kaggle.com/datasets/waddahali/top-1000-steam-games-20242026)

---

## Estrutura do Projeto

```
AvaliacaoBigData/
├── InicializarBanco.py       # Script principal de coleta e scraping de dados
├── Inicializarobanco.py      # Script alternativo via kagglehub
├── steam_games_2026.csv      # Dataset com 1000 jogos (exportado pelo scraper)
├── AvaliaçãoBigData.pbix     # Dashboard Power BI
├── steam_bi_theme.json       # Tema personalizado Steam para o Power BI
├── SCRIPT's.md               # Consultas SQL documentadas
└── Anotações.md              # Checklist da avaliação
```

---

## Tecnologias Utilizadas

- **Python 3** — coleta e processamento de dados
- **PostgreSQL** — armazenamento dos dados
- **Power BI** — visualizações e dashboards
- **Bibliotecas Python:** `requests`, `BeautifulSoup`, `pandas`, `tqdm`, `kagglehub`

---

## Dataset — Colunas

| Coluna | Descrição |
|---|---|
| `AppID` | Identificador único do jogo na Steam |
| `Name` | Título do jogo |
| `Release_Date` | Data de lançamento (YYYY-MM-DD) |
| `Primary_Genre` | Gênero principal |
| `All_Tags` | Tags definidas pelos usuários (separadas por `;`, até 10) |
| `Price_USD` | Preço em dólares (0.0 = gratuito) |
| `Discount_Pct` | Percentual de desconto atual |
| `Review_Score_Pct` | Percentual de avaliações positivas |
| `Total_Reviews` | Total de avaliações na Steam |
| `Steam_Deck_Status` | Compatibilidade: Verified / Playable / Unsupported / Unknown |
| `Estimated_Owners` | Estimativa de proprietários (Total_Reviews × 30, método Boxleiter) |
| `24h_Peak_Players` | Pico de jogadores simultâneos em 24 horas (via SteamSpy) |

---

## Como Executar

### 1. Instalar dependências

```bash
pip install requests beautifulsoup4 pandas tqdm kagglehub
```

### 2. Coletar os dados

```bash
# Opção A — scraping completo da Steam (4 fases)
python InicializarBanco.py

# Opção B — download direto do Kaggle
python Inicializarobanco.py
```

### 3. Importar para o PostgreSQL

Crie a tabela e importe o CSV gerado (`steam_games_2026.csv`) para o banco de dados.

---

## Consultas SQL

### Básicas

**Top 10 jogos por pico de jogadores (24h)**
```sql
SELECT "Name", "24h_Peak_Players"
FROM public.steam_games
ORDER BY "24h_Peak_Players" DESC
LIMIT 10;
```

**Top 5 categorias com mais jogos**
```sql
SELECT "Primary_Genre" AS Categoria, COUNT(*) AS Quantidade_de_Jogos
FROM steam_games
GROUP BY "Primary_Genre"
ORDER BY Quantidade_de_Jogos DESC
LIMIT 5;
```

### Com Funções Agregadas

**Preço médio global dos jogos**
```sql
SELECT AVG("Price_USD") AS Media_de_Preco_em_USD
FROM public.steam_games;
```

### Com GROUP BY

**Taxa de engajamento por gênero**
```sql
SELECT
    "Primary_Genre" AS Gênero,
    SUM("Estimated_Owners") AS Total_Estimado_Donos,
    SUM("24h_Peak_Players") AS Jogadores_Ativos_Pico,
    ROUND((SUM("24h_Peak_Players")::numeric / NULLIF(SUM("Estimated_Owners"), 0)) * 100, 4) AS Taxa_Engajamento_Percentual
FROM public.steam_games
GROUP BY "Primary_Genre"
ORDER BY Jogadores_Ativos_Pico DESC;
```

**Análise de preços — jogos de Shooter + Zombies**
```sql
SELECT
    "Name" AS Nome_do_Jogo,
    COUNT(*) AS Qtd_Entradas,
    AVG("Price_USD") AS Media_Preco,
    MAX("Price_USD") AS Maior_Preco,
    MIN("Price_USD") AS Menor_Preco
FROM public.steam_games
WHERE "All_Tags" LIKE '%Shooter%'
  AND "All_Tags" LIKE '%Zombies%'
GROUP BY "Name"
ORDER BY "Name" ASC;
```

---

## Checklist da Avaliação

| # | Tarefa | Pontos | Status |
|---|--------|--------|--------|
| 1 | Coletar dados públicos e armazenar no PostgreSQL | 1,0 | Feito |
| 2 | Documentar dados (resumo, URL, colunas) | 1,0 | Feito |
| 3 | Duas consultas SQL básicas | 2,0 | Feito |
| 4 | Duas consultas SQL com funções agregadas | 2,0 | Feito |
| 5 | Duas consultas SQL com GROUP BY | 2,0 | Feito |
| 6 | Duas visualizações/dashboards (Power BI) | 2,0 | Feito |
