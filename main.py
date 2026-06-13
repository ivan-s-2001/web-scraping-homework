from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


URL = "https://habr.com/ru/all/"
KEYWORDS = ["дизайн", "фото", "web", "python"]
MAX_WORKERS = 5
TIMEOUT = 5
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def get_soup(url):
    """Получает страницу и возвращает BeautifulSoup-объект."""
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def has_keyword(text, keywords):
    """Проверяет, есть ли в тексте хотя бы одно ключевое слово."""
    text = text.lower()
    return any(keyword.lower() in text for keyword in keywords)


def get_article_full_text(article_url):
    """Получает полный текст статьи для дополнительной части задания."""
    soup = get_soup(article_url)
    article_body = (
        soup.select_one("div.tm-article-body")
        or soup.select_one("div.article-formatted-body")
        or soup.select_one("div#post-content-body")
    )

    if article_body:
        return article_body.get_text(" ", strip=True)

    return soup.get_text(" ", strip=True)


def parse_article_preview(article):
    """Достаёт дату, заголовок, ссылку и preview-текст из карточки статьи."""
    title_tag = (
        article.select_one("a.tm-title__link")
        or article.select_one("h2 a")
        or article.find("a", href=True)
    )
    time_tag = article.find("time")

    if not title_tag:
        return None

    title = title_tag.get_text(" ", strip=True)
    link = urljoin(URL, title_tag.get("href"))
    date = (
        time_tag.get("title") or time_tag.get_text(" ", strip=True)
        if time_tag
        else "Дата не найдена"
    )

    preview_tag = (
        article.select_one("div.article-formatted-body")
        or article.select_one("div.tm-article-snippet")
        or article.select_one("div.tm-article-body")
    )
    preview = preview_tag.get_text(" ", strip=True) if preview_tag else ""
    card_text = " ".join([title, preview])

    return {
        "date": date,
        "title": title,
        "link": link,
        "card_text": card_text,
    }


def print_article(article_info):
    """Печатает статью в формате, который требуется по заданию."""
    print(f"{article_info['date']} – {article_info['title']} – {article_info['link']}")


def find_matches_by_full_text(candidates, keywords):
    """
    Проверяет полный текст только у тех статей,
    в карточках которых ключевые слова не найдены.
    """
    matched_links = set()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_article = {
            executor.submit(get_article_full_text, article_info["link"]): article_info
            for article_info in candidates
        }

        for future in as_completed(future_to_article):
            article_info = future_to_article[future]

            try:
                full_text = future.result()
            except requests.RequestException:
                continue

            if has_keyword(full_text, keywords):
                matched_links.add(article_info["link"])

    return matched_links


def parse_articles():
    if not KEYWORDS:
        return

    soup = get_soup(URL)
    articles = soup.find_all("article")

    parsed_articles = []
    full_text_candidates = []

    for article in articles:
        article_info = parse_article_preview(article)

        if not article_info:
            continue

        if has_keyword(article_info["card_text"], KEYWORDS):
            article_info["is_matched"] = True
        else:
            article_info["is_matched"] = False
            full_text_candidates.append(article_info)

        parsed_articles.append(article_info)

    full_text_matched_links = find_matches_by_full_text(full_text_candidates, KEYWORDS)

    for article_info in parsed_articles:
        if article_info["is_matched"] or article_info["link"] in full_text_matched_links:
            print_article(article_info)


if __name__ == "__main__":
    parse_articles()
