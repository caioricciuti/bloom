# bloom-filter-demo

Interactive demo showing how Google checks if a username is already taken — using Bloom Filters + DuckDB-WASM, all in the browser.

**[Live demo → bloom.caioricciuti.com](https://bloom.caioricciuti.com)**

## What it does

When you type a username, the app runs the same 4-step pipeline that Google likely uses:

1. **Debounce** — waits for you to stop typing (300ms)
2. **Bloom Filter** — instant in-memory check against a 100M-bit filter (~12MB). If the bit pattern doesn't match, the username is **definitely available** — no database query needed
3. **Prefix search** — DuckDB-WASM scans the parquet file for similar usernames (suggestions)
4. **DB confirmation** — full DuckDB query to confirm the exact match, eliminating false positives

## Numbers

| Metric | Value |
|---|---|
| Usernames | 10,000,000 |
| Bloom filter size | 100M bits (~12MB) |
| False positive rate | ~0.8% |
| Hash functions (k) | 7 |
| Parquet file | ~26.5MB (ZSTD compression) |

## How Bloom Filters work

A Bloom filter is a space-efficient probabilistic data structure:

- A **bit array** with *m* bits, all initialized to zero
- **k** independent hash functions, each mapping an item to a position in the array
- To **add** an item: apply the k hash functions and set those k bits to 1
- To **check** an item: apply the k hash functions — if all k bits are 1, the item is *probably* in the set. If any bit is 0, the item is **definitely not**

**False positives** are possible (all bits may have been set by other items), but **false negatives are impossible**. This makes Bloom filters perfect for a quick "does this username exist?" check.

## Google's real scale

Google has ~2 billion accounts. A Bloom filter for that:

- ~2.4GB of RAM (with 0.8% FPR)
- Fits in a single server's memory
- Distributed across ~200 points of presence worldwide
- **Microsecond lookups** — no disk, no database, no network round-trip

The actual database is only queried when the Bloom filter says "maybe taken" (~0.8% of available usernames).

## Stack

- **Frontend**: Plain HTML/JS — no framework, no build step
- **Database**: [DuckDB-WASM](https://duckdb.org/docs/api/wasm/overview) — runs SQL directly in the browser
- **Data generation**: Python + [Faker](https://faker.readthedocs.io/) + [DuckDB](https://duckdb.org/)

## Run locally

The `data/` directory is already committed, so just run:

```bash
python -m http.server
```

Open http://localhost:8000.

## Regenerate data

To regenerate the 10M usernames and bloom filter from scratch:

```bash
uv run generate_data.py
```

Uses [uv](https://docs.astral.sh/uv/) to manage dependencies automatically (Faker + DuckDB).

## Author

Made by [Caio Ricciuti](https://github.com/caioricciuti) — [GitHub repo](https://github.com/caioricciuti/bloom)

## License

[MIT](LICENSE)

---

# bloom-filter-demo (PT-BR)

Demo interativa mostrando como o Google verifica se um nome de usuario ja esta em uso — usando Bloom Filters + DuckDB-WASM, tudo no browser.

**[Demo ao vivo → bloom.caioricciuti.com](https://bloom.caioricciuti.com)**

## O que faz

Quando voce digita um username, a app executa o mesmo pipeline de 4 etapas que o Google provavelmente usa:

1. **Debounce** — espera voce parar de digitar (300ms)
2. **Bloom Filter** — checagem instantanea em memoria contra um filtro de 100M bits (~12MB). Se o padrao de bits nao bate, o username **definitivamente esta disponivel** — sem precisar consultar banco
3. **Busca por prefixo** — DuckDB-WASM varre o arquivo parquet buscando usernames similares (sugestoes)
4. **Confirmacao no DB** — query completa no DuckDB para confirmar o match exato, eliminando falsos positivos

## Numeros

| Metrica | Valor |
|---|---|
| Usernames | 10.000.000 |
| Tamanho do Bloom filter | 100M bits (~12MB) |
| Taxa de falso positivo | ~0,8% |
| Funcoes hash (k) | 7 |
| Arquivo Parquet | ~26,5MB (compressao ZSTD) |

## Como Bloom Filters funcionam

Um Bloom filter e uma estrutura de dados probabilistica e eficiente em espaco:

- Um **array de bits** com *m* bits, todos inicializados em zero
- **k** funcoes hash independentes, cada uma mapeando um item para uma posicao no array
- Para **adicionar** um item: aplica as k funcoes hash e seta esses k bits para 1
- Para **verificar** um item: aplica as k funcoes hash — se todos os k bits sao 1, o item *provavelmente* esta no conjunto. Se qualquer bit for 0, o item **definitivamente nao esta**

**Falsos positivos** sao possiveis (todos os bits podem ter sido setados por outros itens), mas **falsos negativos sao impossiveis**. Isso torna Bloom filters perfeitos para uma checagem rapida de "esse username ja existe?".

## A escala real do Google

O Google tem ~2 bilhoes de contas. Um Bloom filter pra isso:

- ~2,4GB de RAM (com 0,8% de FPR)
- Cabe na memoria de um unico servidor
- Distribuido em ~200 pontos de presenca pelo mundo
- **Consultas em microssegundos** — sem disco, sem banco, sem round-trip de rede

O banco de dados real so e consultado quando o Bloom filter diz "talvez ocupado" (~0,8% dos usernames disponiveis).

## Stack

- **Frontend**: HTML/JS puro — sem framework, sem build
- **Banco de dados**: [DuckDB-WASM](https://duckdb.org/docs/api/wasm/overview) — roda SQL direto no browser
- **Geracao de dados**: Python + [Faker](https://faker.readthedocs.io/) + [DuckDB](https://duckdb.org/)

## Rodar localmente

O diretorio `data/` ja esta commitado, entao e so rodar:

```bash
python -m http.server
```

Abra http://localhost:8000.

## Regenerar dados

Para regenerar os 10M usernames e o bloom filter do zero:

```bash
uv run generate_data.py
```

Usa o [uv](https://docs.astral.sh/uv/) pra gerenciar dependencias automaticamente (Faker + DuckDB).

## Autor

Feito por [Caio Ricciuti](https://github.com/caioricciuti) — [Repositorio no GitHub](https://github.com/caioricciuti/bloom)

## Licenca

[MIT](LICENSE)
