# bloom-filter-demo

Demo interativa mostrando como o Google verifica se um nome de usuário já está em uso — usando Bloom Filters + DuckDB-WASM, tudo no browser.

**[Demo ao vivo → bloom.caioricciuti.com](https://bloom.caioricciuti.com)**

## O que faz

Quando você digita um username, a app executa o mesmo pipeline de 4 etapas que o Google provavelmente usa:

1. **Debounce** — espera você parar de digitar (300ms)
2. **Bloom Filter** — checagem instantânea em memória contra um filtro de 100M bits (~12MB). Se o padrão de bits não bate, o username **definitivamente está disponível** — sem precisar consultar banco
3. **Busca por prefixo** — DuckDB-WASM varre o arquivo parquet buscando usernames similares (sugestões)
4. **Confirmação no DB** — query completa no DuckDB para confirmar o match exato, eliminando falsos positivos

## Números

| Métrica | Valor |
|---|---|
| Usernames | 10.000.000 |
| Tamanho do Bloom filter | 100M bits (~12MB) |
| Taxa de falso positivo | ~0,8% |
| Funções hash (k) | 7 |
| Arquivo Parquet | ~26,5MB (compressão ZSTD) |

## Como Bloom Filters funcionam

Um Bloom filter é uma estrutura de dados probabilística e eficiente em espaço:

- Um **array de bits** com *m* bits, todos inicializados em zero
- **k** funções hash independentes, cada uma mapeando um item para uma posição no array
- Para **adicionar** um item: aplica as k funções hash e seta esses k bits para 1
- Para **verificar** um item: aplica as k funções hash — se todos os k bits são 1, o item *provavelmente* está no conjunto. Se qualquer bit for 0, o item **definitivamente não está**

**Falsos positivos** são possíveis (todos os bits podem ter sido setados por outros itens), mas **falsos negativos são impossíveis**. Isso torna Bloom filters perfeitos para uma checagem rápida de "esse username já existe?".

## A escala real do Google

O Google tem ~2 bilhões de contas. Um Bloom filter pra isso:

- ~2,4GB de RAM (com 0,8% de FPR)
- Cabe na memória de um único servidor
- Distribuído em ~200 pontos de presença pelo mundo
- **Consultas em microssegundos** — sem disco, sem banco, sem round-trip de rede

O banco de dados real só é consultado quando o Bloom filter diz "talvez ocupado" (~0,8% dos usernames disponíveis).

## Stack

- **Frontend**: HTML/JS puro — sem framework, sem build
- **Banco de dados**: [DuckDB-WASM](https://duckdb.org/docs/api/wasm/overview) — roda SQL direto no browser
- **Geração de dados**: Python + [Faker](https://faker.readthedocs.io/) + [DuckDB](https://duckdb.org/)

## Rodar localmente

O diretório `data/` já está commitado, então é só rodar:

```bash
python -m http.server
```

Abra http://localhost:8000.

## Regenerar dados

Para regenerar os 10M usernames e o bloom filter do zero:

```bash
uv run generate_data.py
```

Usa o [uv](https://docs.astral.sh/uv/) pra gerenciar dependências automaticamente (Faker + DuckDB).

## Autor

Feito por [Caio Ricciuti](https://github.com/caioricciuti) — [Repositório no GitHub](https://github.com/caioricciuti/bloom)

## Licença

[MIT](LICENSE)
