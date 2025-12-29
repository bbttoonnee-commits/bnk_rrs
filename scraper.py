import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz

def get_articles(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    
    # Selektor Bankiera dla głównych newsów
    items = soup.select('article.article, .entry-text') # Uproszczony selektor
    for item in items:
        title_tag = item.select_one('.entry-title a, a.article-link')
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = "https://www.bankier.pl" + title_tag['href'] if title_tag['href'].startswith('/') else title_tag['href']
            
            # Próba wyciągnięcia daty (Bankier często używa tagu time)
            time_tag = item.select_one('time')
            if time_tag and time_tag.has_attr('datetime'):
                date_str = time_tag['datetime']
            else:
                date_str = datetime.now().isoformat()
                
            articles.append({'title': title, 'link': link, 'date': date_str})
    return articles

def generate_rss():
    fg = FeedGenerator()
    fg.title('Bankier.pl - Wiadomości (RSS)')
    fg.link(href='https://www.bankier.pl/wiadomosc/', rel='alternate')
    fg.description('Nieoficjalny czytnik RSS dla Bankier.pl')
    fg.language('pl')

    tz = pytz.timezone('Europe/Warsaw')

    # Pobieramy 2 pierwsze strony
    all_articles = []
    all_articles.extend(get_articles('https://www.bankier.pl/wiadomosc/'))
    all_articles.extend(get_articles('https://www.bankier.pl/wiadomosc/2.html'))

    for art in all_articles:
        fe = fg.add_entry()
        fe.title(art['title'])
        fe.link(href=art['link'])
        # Parsowanie daty z formatu ISO Bankiera
        try:
            dt = datetime.fromisoformat(art['date'].replace('Z', '+00:00'))
            fe.pubDate(dt.astimezone(tz))
        except:
            fe.pubDate(datetime.now(tz))

    fg.rss_file('rss.xml')

if __name__ == '__main__':
    generate_rss()