import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timedelta
import pytz
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
}

def get_article_date(url):
    """Pobiera dokładną datę z meta-tagów artykułu."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        meta = soup.find("meta", attrs={"property": "article:published_time"})
        if meta and meta.get("content"):
            return datetime.fromisoformat(meta["content"].replace('Z', '+00:00'))
    except Exception:
        pass
    return None

def generate_rss():
    fg = FeedGenerator()
    fg.title('Bankier.pl - Tylko Najnowsze')
    fg.link(href='https://www.bankier.pl/wiadomosc/', rel='alternate')
    fg.description('Bieżące wiadomości z ostatnich 48h (z 2 pierwszych stron)')
    fg.language('pl')

    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    # FILTR: Tylko artykuły nie starsze niż 48 godziny
    cutoff_date = now - timedelta(hours=48)
    
    all_links = []
    pages = ['https://www.bankier.pl/wiadomosc/', 'https://www.bankier.pl/wiadomosc/2.html']
    
    # 1. Zbieramy linki z 2 stron
    for p_url in pages:
        try:
            resp = requests.get(p_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for link in soup.find_all("a", href=True):
                href = link["href"]
                title = link.get_text(strip=True)
                if "/wiadomosc/" in href and len(title) > 20: # Omijamy krótkie linki i nawigację
                    full_url = "https://www.bankier.pl" + href if href.startswith("/") else href
                    if full_url not in [a['link'] for a in all_links]:
                        all_links.append({'title': title, 'link': full_url})
        except Exception as e:
            print(f"Błąd strony {p_url}: {e}")

    # 2. Weryfikujemy datę każdego artykułu i dodajemy tylko świeże
    added_count = 0
    for art in all_links:
        pub_date = get_article_date(art['link'])
        
        # Sprawdzamy, czy data mieści się w naszym limicie świeżości
        if pub_date:
            pub_date_tz = pub_date.astimezone(tz)
            if pub_date_tz > cutoff_date:
                fe = fg.add_entry()
                fe.title(art['title'])
                fe.link(href=art['link'])
                fe.id(art['link'])
                fe.pubDate(pub_date_tz)
                added_count += 1
        
        # Throttling, aby nie przeciążyć serwera
        time.sleep(0.2)
        if added_count >= 40: # Nie potrzebujemy więcej niż 40 najświeższych
            break

    fg.rss_file('rss.xml')
    print(f"DEBUG: RSS wygenerowany. Dodano {added_count} świeżych artykułów.")

if __name__ == '__main__':
    generate_rss()
