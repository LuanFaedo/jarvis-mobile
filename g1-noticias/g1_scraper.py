import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import os

def fetch_page(url: str) -> str:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        sys.stderr.write(f"[ERRO] Falha ao baixar a página: {e}\\n")
        return ""

def parse_news(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []

    possible = [
        ("div", {"class": "feed-post-body"}),
        ("div", {"class": "widget--info"}),
        ("a", {"class": "feed-post-link"}),
        ("article", {"class": "bstn-related"}),
    ]

    for tag, attrs in possible:
        for cnt in soup.find_all(tag, attrs=attrs):
            title_tag = cnt.find(["h2", "h3", "h4", "strong"])
            title = title_tag.get_text(strip=True) if title_tag else None

            link = cnt.find("a", href=True)
            url = link["href"] if link else None
            if url and not url.startswith("http"):
                url = f"https://g1.globo.com{url}"

            time_tag = cnt.find("time")
            raw = time_tag["datetime"] if time_tag and time_tag.has_attr("datetime") else cnt.get("data-time", "")
            date_hora = ""
            if raw:
                for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
                    try:
                        dt = datetime.strptime(raw, fmt)
                        date_hora = dt.isoformat()
                        break
                    except ValueError:
                        continue
            if not date_hora and time_tag:
                try:
                    dt = datetime.strptime(time_tag.get_text(strip=True), "%d/%m/%Y %H:%M")
                    date_hora = dt.isoformat()
                except Exception:
                    pass

            if title and url:
                items.append({"titulo": title, "url": url, "data_hora": date_hora})

    if not items:
        for a in soup.select("a[href^='https://g1.globo.com/']"):
            t = a.get_text(strip=True)
            u = a["href"]
            if t and u:
                items.append({"titulo": t, "url": u, "data_hora": ""})
            if len(items) >= 30:
                break

    return items

def save_csv(news: list[dict], path: str):
    fields = ["titulo", "url", "data_hora"]
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for n in news:
                w.writerow(n)
        print(f"[OK] CSV salvo em: {path}")
    except OSError as e:
        sys.stderr.write(f"[ERRO] Ao gravar CSV: {e}\\n")

def main():
    url = "https://g1.globo.com/"
    html = fetch_page(url)
    if not html:
        sys.exit(1)
    news = parse_news(html)
    if not news:
        sys.stderr.write("[AVISO] Nenhuma notícia encontrada.\\n")
    else:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "g1_noticias.csv")
        save_csv(news, out)

if __name__ == "__main__":
    main()