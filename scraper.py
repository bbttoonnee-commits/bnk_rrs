import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import time

# Używamy sprawdzonych nagłówków z Twojego app.py
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
}

def get_article_date(url):
    """Pobiera dokładną datę z meta-tagów artykułu (metoda z app.py)"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Szukamy meta tagu SEO z datą publikacji
        meta = soup.find("meta", attrs={"property": "article:published_time"})
        if meta and meta.get("content"):
            return datetime.fromisoformat(meta["content"].replace('Z', '+00:00'))
    except Exception as e:
        print(f"DEBUG: Błąd daty dla {url}: {e}")
    return None

def get_articles_from_page(url):
    """Wyciąga linki do artykułów z listy wiadomości"""
    articles = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Skanujemy wszystkie linki i filtrujemy je (logika z app.py)
        for link in soup.find_all("a", href=True):
            href = link["href"]
            title = link.get_text(strip=True)

            if "/wiadomosc/" not in href or not title or len(title) < 15:
                continue
            if "Czytaj dalej" in title or title == "Następne":
                continue
            
            # Ignoruj linki będące tylko numerami stron
            slug = href.rstrip("/").split("/")[-1]
            if slug.isdigit():
                continue

            full_url = "https://www.bankier.pl" + href if href.startswith("/") else href
            
            if not any(a['link'] == full_url for a in articles):
                articles.append({'title': title, 'link': full_url})
        return articles
    except Exception as e:
        print(f"DEBUG: Błąd pobierania strony {url}: {e}")
        return []

def generate_rss():
    fg = FeedGenerator()
    fg.title('Bankier.pl - Najnowsze Wiadomości')
    fg.link(href='https://www.bankier.pl/wiadomosc/', rel='alternate')
    fg.description('Aktualne wiadomości z 2 pierwszych stron Bankier.pl')
    fg.language('pl')

    tz = pytz.timezone('Europe/Warsaw')
    all_links = []
    
    # Pobieramy 2 pierwsze strony (strona główna wiadomości i strona 2)
    pages = ['https://www.bankier.pl/wiadomosc/', 'https://www.bankier.pl/wiadomosc/2.html']
    for p_url in pages:
        all_links.extend(get_articles_from_page(p_url))

    # Ograniczamy do 30 najnowszych i pobieramy ich realne daty
    for art in all_links[:30]:
        fe = fg.add_entry()
        fe.title(art['title'])
        fe.link(href=art['link'])
        fe.id(art['link'])
        
        real_date = get_article_date(art['link'])
        if real_date:
            fe.pubDate(real_date.astimezone(tz))
        else:
            fe.pubDate(datetime.now(tz))
        
        # Throttling – 0.3s przerwy między zapytaniami, żeby nie dostać bana
        time.sleep(0.3)

    fg.rss_file('rss.xml')
    print(f"DEBUG: RSS wygenerowany pomyślnie z {len(all_links[:30])} artykułami.")

if __name__ == '__main__':
    generate_rss()
