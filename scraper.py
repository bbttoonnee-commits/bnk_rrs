import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timedelta
import pytz
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

def get_article_date(url):
    """Pobiera datę z wnętrza, jeśli nie ma jej na liście (z Twojego app.py)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=7)
        soup = BeautifulSoup(resp.text, "html.parser")
        meta = soup.find("meta", attrs={"property": "article:published_time"})
        if meta and meta.get("content"):
            return datetime.fromisoformat(meta["content"].replace('Z', '+00:00'))
    except:
        pass
    return None

def generate_rss():
    fg = FeedGenerator()
    fg.title('Bankier.pl - Wszystkie Najnowsze')
    fg.link(href='https://www.bankier.pl/wiadomosc/', rel='alternate')
    fg.description('Pełny skan 5 stron wiadomości Bankier.pl')
    fg.language('pl')

    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    # Rozszerzamy filtr do 72h, żeby mieć pewność, że nic nie ucieka z weekendu
    cutoff_date = now - timedelta(hours=72)
    
    seen_links = set()
    all_valid_entries = []

    # Skanujemy strony 1-5
    pages = ['https://www.bankier.pl/wiadomosc/'] + [f'https://www.bankier.pl/wiadomosc/{i}.html' for i in range(2, 6)]
    
    for p_url in pages:
        print(f"Pobieram: {p_url}")
        try:
            resp = requests.get(p_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # SZEROKI SELEKTOR: szukamy wszystkich tytułów w kontenerach entry-content
            # To pokrywa układ z Twojego zrzutu ekranu
            for entry in soup.select('.entry-content, .article'):
                link_tag = entry.select_one('.entry-title a, a[href*="/wiadomosc/"]')
                if not link_tag:
                    continue
                
                title = link_tag.get_text(strip=True)
                href = link_tag['href']
                full_url = "https://www.bankier.pl" + href if href.startswith("/") else href
                
                # Ignorujemy nawigację i duplikaty
                if full_url in seen_links or "/wiadomosc/2" in full_url or len(title) < 10:
                    continue
                
                # Próba wyciągnięcia daty z listy (tag <time>)
                dt = None
                time_tag = entry.find('time')
                if time_tag and time_tag.has_attr('datetime'):
                    try:
                        dt = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                    except:
                        pass
                
                seen_links.add(full_url)
                all_valid_entries.append({'title': title, 'link': full_url, 'date': dt})
                
        except Exception as e:
            print(f"Błąd na stronie {p_url}: {e}")

    # Weryfikacja brakujących dat (tylko dla tych, których nie było na liście)
    final_count = 0
    for item in all_valid_entries:
        # Jeśli nie znaleźliśmy daty na liście, wchodzimy do środka (max 50 wejść dla szybkości)
        if not item['date'] and final_count < 50:
            item['date'] = get_article_date(item['link'])
            time.sleep(0.1) # Mały throttling
        
        # Jeśli nadal brak daty, uznajemy że to "teraz"
        pub_date = item['date'] if item['date'] else now
        
        if pub_date.astimezone(tz) > cutoff_date:
            fe = fg.add_entry()
            fe.title(item['title'])
            fe.link(href=item['link'])
            fe.id(item['link'])
            fe.pubDate(pub_date.astimezone(tz))
            final_count += 1

    fg.rss_file('rss.xml')
    print(f"Sukces! RSS zawiera {final_count} artykułów.")

if __name__ == '__main__':
    generate_rss()
