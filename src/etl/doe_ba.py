import httpx
import urllib3
from datetime import date, timedelta
from bs4 import BeautifulSoup
from src.config import settings

urllib3.disable_warnings()

BASE_URL = "https://dool.egba.ba.gov.br"
KEYWORDS = {
    # editais
    "concurso público", "concurso publico",
    "processo seletivo",
    "edital de abertura", "edital de concurso",
    "inscrições abertas", "inscricoes abertas",
    "reda", "pss",
    # movimentações de pessoal
    "nomeação", "nomeacao",
    "convocação", "convocacao",
    "posse",
    "apostila",
    # resultados
    "homologação", "homologacao",
    "resultado",
    "aprovados", "classificados",
    # correções
    "retificação", "retificacao",
    "errata",
}

# Categorias do sumário que são sempre relevantes, independente do título
RELEVANT_CATEGORIES = {
    "convocação", "convocacao",
    "homologação", "homologacao",
    "resultado",
    "resultados e homologações", "resultados e homologacoes",
    "retificação/errata", "retificacao/errata",
    "retificação", "retificacao",
    "apostila",
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
    "Referer": BASE_URL,
}


def _client() -> httpx.Client:
    cookies = {}
    if settings.DOOL_SESSION_COOKIE:
        cookies["CAKEPHP"] = settings.DOOL_SESSION_COOKIE
    if settings.DOOL_SESSION_COOKIE2:
        cookies["cookiesession1"] = settings.DOOL_SESSION_COOKIE2
    return httpx.Client(verify=False, timeout=30, follow_redirects=True,
                        cookies=cookies, headers=_HEADERS)


def _matches_keywords(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in KEYWORDS)


def _relevant_category(cat: str) -> bool:
    return cat.strip().lower() in RELEVANT_CATEGORIES


def _get_edition_id(client: httpx.Client, target_date: date) -> str | None:
    url = f"{BASE_URL}/apifront/portal/edicoes/edicoes_from_data/{target_date.isoformat()}"
    try:
        r = client.get(url)
        r.raise_for_status()
        data = r.json()
        if not data.get("erro") and data.get("itens"):
            return data["itens"][0]["id"]
    except Exception as e:
        print(f"[DOE-BA] Erro ao buscar edicao de {target_date}: {e}")
    return None


def _get_relevant_links(client: httpx.Client, edition_id: str) -> list[dict]:
    url = f"{BASE_URL}/html/{edition_id}.html"
    try:
        r = client.get(url)
        r.raise_for_status()
    except Exception as e:
        print(f"[DOE-BA] Erro ao buscar sumario {edition_id}: {e}")
        return []

    soup = BeautifulSoup(r.content, "html.parser")
    links = soup.find_all("a", class_="linkMateria")

    relevantes = []
    for link in links:
        texto = link.get_text(strip=True)
        cat = ""
        for parent in link.parents:
            if parent.name == "ul":
                folder = parent.find_previous_sibling("span", class_="folder")
                if folder:
                    cat = folder.get_text(strip=True)
                    break
        if _matches_keywords(texto) or _matches_keywords(cat) or _relevant_category(cat):
            relevantes.append({
                "materia_id": link.get("identificador"),
                "titulo": texto,
                "categoria": cat,
            })

    return relevantes


def _get_article_content(client: httpx.Client, materia_id: str) -> str:
    url = f"{BASE_URL}/apifront/portal/edicoes/publicacoes_ver_conteudo/{materia_id}"
    try:
        r = client.get(url)
        r.raise_for_status()
        if r.content[:4] == b"%PDF":
            return ""
        soup = BeautifulSoup(r.content, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"[DOE-BA] Erro ao buscar materia {materia_id}: {e}")
        return ""


def scrape_doe(days: int = 7) -> list[dict]:
    results = []
    client = _client()
    today = date.today()

    for i in range(days):
        target = today - timedelta(days=i)
        edition_id = _get_edition_id(client, target)
        if not edition_id:
            continue

        print(f"[DOE-BA] {target} -> edicao {edition_id}")
        links = _get_relevant_links(client, edition_id)
        print(f"[DOE-BA] {len(links)} artigos relevantes encontrados")

        for link in links:
            content = _get_article_content(client, link["materia_id"])
            if not content:
                continue
            results.append({
                "materia_id": link["materia_id"],
                "title": f"DOE-BA | {link['categoria']} | {link['titulo']}",
                "content": content,
                "date": target.isoformat(),
                "source_url": f"{BASE_URL}/portal/visualizacoes/html/{edition_id}",
            })

    client.close()
    print(f"[DOE-BA] Total: {len(results)} publicacoes coletadas.")
    return results


if __name__ == "__main__":
    pubs = scrape_doe(days=3)
    for p in pubs:
        print(f"\n--- {p['title']} ---")
        print(p["content"][:300])
