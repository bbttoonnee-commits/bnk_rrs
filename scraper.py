import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz

def get_articles(url):
    headers = {
        # Bardziej wiarygodny User-Agent, aby uniknąć blokad
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    
    # Na bankier.pl/wiadomosc/ każdy news jest w kontenerze .entry-text
    # Szukamy bezpośrednio tytułów, które są linkami
    items = soup.select('.entry-text .entry-title a')
    
    for a_tag in items:
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        if link.startswith('/'):
            link = "https://www.bankier.pl" + link
            
        # Szukamy daty: na Bankierze czas jest w tagu <time> obok tytułu
        # Musimy wyjść poziom wyżej do rodzica (.entry-text), by znaleźć <time>
        parent = a_tag.find_parent(class_='entry-text')
        time_tag = parent.select_one('time') if parent else None
        
        if time_tag and time_tag.has_attr('datetime'):
            date_str = time_tag['datetime']
        else:
            # Jeśli nie ma tagu time, bierzemy aktualną chwilę
            date_str = datetime.now().isoformat()
            
        articles.append({
            'title': title, 
            'link': link, 
            'date': date_str
        })
    
    print(f"DEBUG: Znaleziono {len(articles)} artykułów na stronie {url}")
    return articles

def generate_rss():
    fg = FeedGenerator()
    fg.title('Bankier.pl - Najnowsze Wiadomości')
    fg.link(href='https://www.bankier.pl/wiadomosc/', rel='alternate')
    fg.description('Automatyczny czytnik RSS dla serwisu Bankier.pl')
    fg.language('pl')

    tz = pytz.timezone('Europe/Warsaw')

    # Pobieranie z dwóch pierwszych stron
    pages = ['', '2.html']
    all_articles = []
    
    for page in pages:
        url = f'https://www.bankier.pl/wiadomosc/{page}'
        all_articles.extend(get_articles(url))

    # Usuwanie ewentualnych duplikatów (na wypadek przesunięcia newsów między stronami)
    seen_links = set()
    for art in all_articles:
        if art['link'] not in seen_links:
            fe = fg.add_entry()
            fe.title(art['title'])
            fe.link(href=art['link'])
            fe.id(art['link'])
            
            try:
                # Obsługa formatu daty z Bankiera (często ISO)
                dt = datetime.fromisoformat(art['date'].replace('Z', '+00:00'))
                fe.pubDate(dt.astimezone(tz))
            except Exception:
                fe.pubDate(datetime.now(tz))
            
            seen_links.add(art['link'])

    fg.rss_file('rss.xml')

if __name__ == '__main__':
    generate_rss()
