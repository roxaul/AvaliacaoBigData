SCRIPT's







**3.0**

**PRIMEIRO SCRIPT:**

Utilizado para verificar os top 10 jogos com mais jogadores ativos em um período de 24hrs.



SELECT "Name", "24h\_Peak\_Players" 

FROM public.steam\_games 

ORDER BY "24h\_Peak\_Players" DESC 

LIMIT 10;



**SEGUNDO SCRIPT:**

Utilizado para verificar as 5 categoria de jogos mais jogados.



SELECT 

&nbsp;   "Primary\_Genre" AS Categoria, 

&nbsp;   COUNT(\*) AS Quantidade\_de\_Jogos

FROM steam\_games

GROUP BY "Primary\_Genre"

ORDER BY Quantidade\_de\_Jogos DESC

LIMIT 5;









**4.0**

**PRIMEIRO SCRIPT:**

Utilizado para verificar o preço médio global.



SELECT AVG("Price\_USD") AS Media\_de\_Preco\_em\_USD

FROM public.steam\_games;



**SEGUNDO SCRIPT:**

**Utilizado para verificar a quantidade de avaliações ao total, sendo boas ou más.**



select SUM(preco\_produto) from produtos;









**5.0**

Utilizado para verificar a taxa de engajamento do qual gênero tem a comunidade mais ativa proporcionalmente ao tamanho da base de usuários.



**PRIMEIRO SCRIPT:**

SELECT 

&nbsp;   "Primary\_Genre" AS Gênero,

&nbsp;   SUM("Estimated\_Owners") AS Total\_Estimado\_Donos,

&nbsp;   SUM("24h\_Peak\_Players") AS Jogadores\_Ativos\_Pico,

&nbsp;   ROUND((SUM("24h\_Peak\_Players")::numeric / NULLIF(SUM("Estimated\_Owners"), 0)) \* 100, 4) AS Taxa\_Engajamento\_Percentual

FROM public.steam\_games

GROUP BY "Primary\_Genre"

ORDER BY Jogadores\_Ativos\_Pico DESC;



**SEGUNDO SCRIPT:**



SELECT 

&nbsp;   "Name" AS Nome\_do\_Jogo,

&nbsp;   COUNT(\*) AS Qtd\_Entradas,

&nbsp;   AVG("Price\_USD") AS Media\_Preco,

&nbsp;   MAX("Price\_USD") AS Maior\_Preco,

&nbsp;   MIN("Price\_USD") AS Menor\_Preco

FROM public.steam\_games

WHERE "All\_Tags" LIKE '%Shooter%' 

&nbsp; AND "All\_Tags" LIKE '%Zombies%'

GROUP BY "Name"

ORDER BY "Name" ASC;



