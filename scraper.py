import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

def generate_rss():
    fg = FeedGenerator()
    fg.title('Bankier.pl - Wiadomości Dnia')
    fg.link(href='https://www.bankier.pl/wiadomosc/', rel='alternate')
    fg.description('Zoptymalizowany czytnik 5 stron Bankier.pl')
    fg.language('pl')

    tz = pytz.timezone('Europe/Warsaw')
    
    # Lista stron do przeskanowania
    pages = ['https://www.bankier.pl/wiadomosc/'] + [f'https://www.bankier.pl/wiadomosc/{i}.html' for i in range(2, 6)]
    
    seen_links = set()

    for p_url in pages:
        try:
            resp = requests.get(p_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Celujemy w główny kontener artykułu (zgodnie z Twoim screenem HTML)
            # Klasa .article zazwyczaj grupuje pojedynczy wpis na liście
            articles = soup.select('.article, .entry-text') 
            
            for art in articles:
                # Szukamy tytułu i linku
                title_tag = art.select_one('.entry-title a, .article-title a')
                if not title_tag:
                    continue
                    
                title = title_tag.get_text(strip=True)
                link = title_tag['href']
                if link.startswith('/'):
                    link = "https://www.bankier.pl" + link
                
                if link in seen_links:
                    continue

                # KLUCZOWA OPTYMALIZACJA: Pobieramy datę bezpośrednio z tagu <time> na liście
                # Dzięki temu nie musimy wchodzić do środka każdego artykułu!
                time_tag = art.select_one('time')
                if time_tag and time_tag.has_attr('datetime'):
                    date_str = time_tag['datetime']
                    try:
                        # Format Bankiera to zazwyczaj ISO
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        dt = datetime.now(tz)
                else:
                    dt = datetime.now(tz)

                fe = fg.add_entry()
                fe.title(title)
                fe.link(href=link)
                fe.id(link)
                fe.pubDate(dt.astimezone(tz))
                
                seen_links.add(link)
                
            print(f"DEBUG: Przetworzono stronę {p_url} - znaleziono {len(articles)} elementów.")
            
        except Exception as e:
            print(f"DEBUG: Błąd na stronie {p_url}: {e}")

    fg.rss_file('rss.xml')
    print(f"Sukces! RSS gotowy. Łącznie artykułów: {len(seen_links)}")

if __name__ == '__main__':
    generate_rss()
