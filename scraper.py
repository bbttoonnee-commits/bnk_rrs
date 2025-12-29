import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import time

# Wykorzystujemy nagłówki, które zadziałały w Twoim app.py
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
}

def get_article_date(url):
    """Pobiera datę bezpośrednio z artykułu (metoda z Twojego app.py)"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Szukamy meta tagu z datą (najbardziej precyzyjne źródło na Bankierze)
        meta = soup.find("meta", attrs={"property": "article:published_time"})
        if meta and meta.get("content"):
            return datetime.fromisoformat(meta["content"])
            
        t = soup.find("time")
        if t and t.get("datetime"):
            return datetime.fromisoformat(t["datetime"])
    except Exception as e:
        print(f"DEBUG: Nie udało się pobrać daty dla {url}: {e}")
    return None

def get_articles(url):
    articles = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Logika filtrowania z Twojego app.py: szukamy wszystkich <a> i filtrujemy po href
        for link in soup.find_all("a", href=True):
            href = link["href"]
            title = link.get_text(strip=True)

            # Filtry z app.py
            if "/wiadomosc/" not in href:
                continue
            if not title or len(title) < 10:
                continue
            if "Czytaj dalej" in title or title == "Następne":
                continue
            
            # Pomijamy linki paginacji (te które kończą się tylko cyfrą)
            slug = href.rstrip("/").split("/")[-1]
            if slug.isdigit():
                continue

            full_url = "https://www.bankier.pl" + href if href.startswith("/") else href
            
            # Unikanie duplikatów
            if not any(a['link'] == full_url for a in articles):
                articles.append({'title': title, 'link': full_url})
        
        print(f"DEBUG: Znaleziono {len(articles)} potencjalnych linków na {url}")
        return articles
    except Exception as e:
        print(f"DEBUG: Błąd strony {url}: {e}")
        return []

def generate_rss():
    fg = FeedGenerator()
    fg.title('Bankier.pl - Wiadomości (RSS)')
    fg.link(href='https://www.bankier.pl/wiadomosc/', rel='alternate')
    fg.description('Prywatny kanał RSS wygenerowany z Bankier.pl')
    fg.language('pl')

    tz = pytz.timezone('Europe/Warsaw')
    all_items = []
    
    # Przechodzimy przez 2 strony
    for page in ['', '/2.html']:
        url = f'https://www.bankier.pl/wiadomosc{page}'
        all_items.extend(get_articles(url))

    # Dla każdego artykułu pobieramy datę (z lekkim opóźnieniem, żeby nie zablokowali)
    for art in all_items[:40]: # limit 40 najnowszych
        fe = fg.add_entry()
        fe.title(art['title'])
        fe.link(href=art['link'])
        fe.id(art['link'])
        
        # Pobieranie daty z wnętrza artykułu
        pub_date = get_article_date(art['link'])
        if pub_date:
            fe.pubDate(pub_date.astimezone(tz))
        else:
            fe.pubDate(datetime.now(tz))
        
        time.sleep(0.2) # Throttling jak w app.py

    fg.rss_file('rss.xml')
    print("DEBUG: Plik rss.xml został wygenerowany.")

if __name__ == '__main__':
    generate_rss()
