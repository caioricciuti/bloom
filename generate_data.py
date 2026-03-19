# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "faker",
#     "duckdb",
# ]
# ///
"""
Gera dataset de ~10M usernames + bloom filter pré-computado.
Uso: uv run generate_data.py
"""

import json
import math
import os
import struct
import unicodedata

import duckdb
from faker import Faker

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PARQUET_PATH = os.path.join(DATA_DIR, "usernames.parquet")
BLOOM_PATH = os.path.join(DATA_DIR, "bloom.bin")
META_PATH = os.path.join(DATA_DIR, "bloom_meta.json")

# Bloom filter params for ~10M items, FPR ≈ 0.8%
TARGET_N = 10_000_000
FPR = 0.008
M = 95_850_584  # bits (~12MB)
K = 7
SEED_MULTIPLIER = 0x123456


def normalize(s: str) -> str:
    """Lowercase + remove accents."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def bloom_hash(s: str, seed: int, m: int) -> int:
    """Must match the JS implementation exactly."""
    MUL = 0x9E3779B9
    h = (seed ^ MUL) & 0xFFFFFFFF
    for ch in s:
        h ^= ord(ch)
        h = (h * MUL) & 0xFFFFFFFF
        h ^= (h >> 16)
        h &= 0xFFFFFFFF
    return h % m


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    # --- Step 1: Generate seed lists with Faker ---
    print("Gerando seeds com Faker...")
    fake_pt = Faker("pt_BR")
    fake_en = Faker("en_US")
    Faker.seed(42)

    first_names: set[str] = set()
    last_names: set[str] = set()
    words: set[str] = set()

    for _ in range(1500):
        first_names.add(normalize(fake_pt.first_name()))
        first_names.add(normalize(fake_en.first_name()))
        last_names.add(normalize(fake_pt.last_name()))
        last_names.add(normalize(fake_en.last_name()))

    for _ in range(800):
        w = normalize(fake_pt.word())
        if len(w) >= 3:
            words.add(w)
        w = normalize(fake_en.word())
        if len(w) >= 3:
            words.add(w)

    first_names_list = sorted(first_names)[:500]
    last_names_list = sorted(last_names)[:500]
    words_list = sorted(words)[:300]

    print(f"  {len(first_names_list)} first names, {len(last_names_list)} last names, {len(words_list)} words")

    # --- Step 2: Generate usernames via DuckDB SQL cross-joins ---
    print("Gerando usernames via DuckDB...")
    con = duckdb.connect()

    con.execute("CREATE TABLE first_names (name VARCHAR)")
    con.executemany("INSERT INTO first_names VALUES (?)", [(n,) for n in first_names_list])

    con.execute("CREATE TABLE last_names (name VARCHAR)")
    con.executemany("INSERT INTO last_names VALUES (?)", [(n,) for n in last_names_list])

    con.execute("CREATE TABLE words (word VARCHAR)")
    con.executemany("INSERT INTO words VALUES (?)", [(w,) for w in words_list])

    # Numbers for combinations
    con.execute("CREATE TABLE nums AS SELECT unnest(generate_series(0, 999)) AS num")

    # Suffixes
    suffixes = ["dev", "oficial", "real", "br", "usa", "tech", "pro", "online", "web", "app",
                "code", "hq", "lab", "io", "net", "live", "gamer", "fan", "top", "xyz"]
    con.execute("CREATE TABLE suffixes (suffix VARCHAR)")
    con.executemany("INSERT INTO suffixes VALUES (?)", [(s,) for s in suffixes])

    # Classic usernames that everyone would try
    classic_usernames = [
        # Service/system accounts
        "admin", "administrator", "test", "teste", "testing", "user", "usuario",
        "root", "master", "guest", "demo", "info", "contato", "contact",
        "support", "suporte", "help", "ajuda", "webmaster", "postmaster",
        "noreply", "no-reply", "mail", "email", "staff", "team", "equipe",
        # Platforms
        "google", "youtube", "facebook", "instagram", "twitter", "tiktok",
        "whatsapp", "telegram", "discord", "reddit", "github", "linkedin",
        # Common Brazilian first names (guaranteed in dataset)
        "joao", "maria", "pedro", "ana", "paulo", "lucas", "gabriel",
        "rafael", "carlos", "julia", "mariana", "fernanda", "bruno",
        "marcos", "andre", "ricardo", "felipe", "daniel", "rodrigo",
        "diego", "thiago", "gustavo", "mateus", "vinicius", "leonardo",
        # Common Brazilian last names (guaranteed in dataset)
        "silva", "souza", "santos", "oliveira", "pereira", "ferreira",
        "costa", "rodrigues", "almeida", "nascimento", "lima", "araujo",
        "fernandes", "barros", "ribeiro", "martins", "carvalho", "gomes",
        # General words
        "brasil", "brazil", "futebol", "soccer", "gamer", "player", "pro",
        "ninja", "hacker", "dev", "developer", "coder", "programmer",
        "music", "musica", "foto", "photo", "video", "blog", "news",
        "noticias", "loja", "shop", "store", "vendas", "sales",
        "oficial", "official", "real", "original", "verdadeiro",
        "amor", "love", "vida", "life", "paz", "feliz", "happy",
        "king", "queen", "rei", "rainha", "prince", "princess",
        "dragon", "dragao", "wolf", "lobo", "lion", "leao",
        "dark", "shadow", "fire", "ice", "storm", "thunder",
        "cyber", "digital", "tech", "data", "cloud", "server",
        "python", "javascript", "linux", "windows", "android", "apple",
        "minecraft", "fortnite", "valorant", "csgo", "lol", "dota",
        "flamengo", "corinthians", "palmeiras", "santos", "saopaulo",
        "empresa", "company", "startup", "projeto", "project",
        "seguranca", "security", "privado", "private", "publico", "public",
    ]
    con.execute("CREATE TABLE classics (username VARCHAR)")
    con.executemany("INSERT INTO classics VALUES (?)", [(u,) for u in classic_usernames])

    # Priority usernames (patterns 7-9) — must survive trim
    con.execute("""
    CREATE TABLE priority_usernames AS
    WITH priority AS (
        -- Pattern 7: bare first names (joao, maria, pedro)
        SELECT f.name AS username FROM first_names f
        UNION ALL
        -- Pattern 8: bare last names (silva, santos)
        SELECT l.name AS username FROM last_names l
        UNION ALL
        -- Pattern 9: classic usernames (admin, test, google, etc.)
        SELECT c.username AS username FROM classics c
    )
    SELECT DISTINCT username FROM priority
    WHERE length(username) >= 3 AND length(username) <= 30
    """)
    priority_count = con.execute("SELECT COUNT(*) FROM priority_usernames").fetchone()[0]
    print(f"  Usernames prioritarios (nomes/classicos): {priority_count:,}")

    # Bulk usernames (patterns 1-6)
    con.execute("""
    CREATE TABLE bulk_usernames AS
    WITH combined AS (
        -- Pattern 1: nome + sobrenome (joaosilva)
        SELECT f.name || l.name AS username
        FROM first_names f CROSS JOIN last_names l

        UNION ALL

        -- Pattern 2: nome_sobrenome (joao_silva)
        SELECT f.name || '_' || l.name AS username
        FROM first_names f CROSS JOIN last_names l

        UNION ALL

        -- Pattern 3: nome + numero (maria123)
        SELECT f.name || CAST(n.num AS VARCHAR) AS username
        FROM first_names f CROSS JOIN nums n
        WHERE n.num < 500

        UNION ALL

        -- Pattern 4: nome_sobrenome + numero (joao_silva42)
        SELECT f.name || '_' || l.name || CAST(n.num AS VARCHAR) AS username
        FROM first_names f CROSS JOIN last_names l CROSS JOIN nums n
        WHERE n.num < 100

        UNION ALL

        -- Pattern 5: palavra + numero (gato2024)
        SELECT w.word || CAST(n.num AS VARCHAR) AS username
        FROM words w CROSS JOIN nums n

        UNION ALL

        -- Pattern 6: nome + sufixo (pedro_dev)
        SELECT f.name || '_' || s.suffix AS username
        FROM first_names f CROSS JOIN suffixes s
    )
    SELECT DISTINCT username FROM combined
    WHERE length(username) >= 4 AND length(username) <= 30
    """)

    bulk_count = con.execute("SELECT COUNT(*) FROM bulk_usernames").fetchone()[0]
    print(f"  Usernames bulk (patterns 1-6): {bulk_count:,}")

    # Trim bulk to fit TARGET_N, then merge with priority
    bulk_limit = TARGET_N - priority_count
    con.execute(f"""
        CREATE TABLE usernames AS
        SELECT username FROM priority_usernames
        UNION
        SELECT username FROM (
            SELECT username FROM bulk_usernames
            WHERE username NOT IN (SELECT username FROM priority_usernames)
            ORDER BY hash(username)
            LIMIT {bulk_limit}
        )
    """)

    final_count = con.execute("SELECT COUNT(*) FROM usernames").fetchone()[0]
    print(f"  Usernames finais: {final_count:,}")

    # --- Step 3: Export to Parquet ---
    print(f"Exportando para {PARQUET_PATH}...")
    con.execute(f"""
        COPY (SELECT * FROM usernames ORDER BY username)
        TO '{PARQUET_PATH}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 50000)
    """)

    # --- Step 4: Build Bloom Filter ---
    print("Construindo Bloom Filter...")
    m = M
    k = K
    # Recalculate m based on actual count
    actual_n = final_count
    m = int(-actual_n * math.log(FPR) / (math.log(2) ** 2))
    # Round up to multiple of 8
    m = ((m + 7) // 8) * 8
    k = max(1, round((m / actual_n) * math.log(2)))

    print(f"  m={m:,} bits ({m // 8:,} bytes), k={k}, n={actual_n:,}")
    print(f"  FPR teórica: {(1 - math.exp(-k * actual_n / m)) ** k:.4%}")

    # Allocate bit array
    byte_count = m // 8
    bloom = bytearray(byte_count)

    # Read all usernames and hash them
    cursor = con.execute("SELECT username FROM usernames")
    batch_size = 100_000
    processed = 0

    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        for (username,) in batch:
            for i in range(k):
                seed = i * SEED_MULTIPLIER
                pos = bloom_hash(username, seed, m)
                bloom[pos >> 3] |= 1 << (pos & 7)
        processed += len(batch)
        if processed % 1_000_000 == 0:
            print(f"  Processados: {processed:,}")

    print(f"  Total processados: {processed:,}")

    # Bits set
    bits_set = sum(bin(b).count("1") for b in bloom)
    print(f"  Bits marcados: {bits_set:,} / {m:,} ({bits_set / m:.2%})")

    # Save bloom.bin
    with open(BLOOM_PATH, "wb") as f:
        f.write(bytes(bloom))
    print(f"  Salvo: {BLOOM_PATH} ({os.path.getsize(BLOOM_PATH):,} bytes)")

    # Save bloom_meta.json
    meta = {
        "m": m,
        "k": k,
        "n": actual_n,
        "seed_multiplier": SEED_MULTIPLIER,
        "fpr": round((1 - math.exp(-k * actual_n / m)) ** k, 6),
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  Salvo: {META_PATH}")

    con.close()
    print("\nDone!")
    print(f"  Parquet: {os.path.getsize(PARQUET_PATH) / 1024 / 1024:.1f} MB")
    print(f"  Bloom:   {os.path.getsize(BLOOM_PATH) / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
