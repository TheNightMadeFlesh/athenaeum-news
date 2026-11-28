import json
import calendar
import hashlib
from datetime import datetime, timezone

import feedparser
import requests


# ----------------------------------------
# CONFIGURATION
# ----------------------------------------

MAX_HEADLINES = 100
MAX_PER_SOURCE = 2

FEEDS_FILE = "feeds.json"
OUTPUT_FILE = "headlines.json"


# ----------------------------------------
# ARTICLE DATE
# ----------------------------------------

def get_date(entry):

    published = (
        entry.get("published_parsed")
        or entry.get("updated_parsed")
    )

    if published:
        timestamp = calendar.timegm(published)

        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        ).isoformat()

    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------
# RETRIEVE RSS FEED
# ----------------------------------------

def fetch_feed(source):

    articles = []

    try:

        response = requests.get(
            source["url"],
            timeout=20,
            headers={
                "User-Agent": "AthenaeumObscuraRSS/1.0"
            }
        )

        response.raise_for_status()

        feed = feedparser.parse(response.content)

        for entry in feed.entries:

            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                continue

            article_id = hashlib.sha256(
                link.encode("utf-8")
            ).hexdigest()

            articles.append({
                "id": article_id,
                "source": source["name"],
                "title": title,
                "url": link,
                "published": get_date(entry)
            })

        print(
            f"Retrieved {len(articles)} articles "
            f"from {source['name']}"
        )

    except Exception as error:

        print(
            f"Error retrieving {source['name']}: "
            f"{error}"
        )

    return articles


# ----------------------------------------
# MAIN AGGREGATOR
# ----------------------------------------

def main():

    # Load RSS source configuration

    with open(FEEDS_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)

    all_articles = []

    # Retrieve articles from all sources

    for source in config["feeds"]:
        all_articles.extend(fetch_feed(source))

    # ------------------------------------
    # REMOVE DUPLICATES
    # ------------------------------------

    unique_articles = {}

    for article in all_articles:
        unique_articles[article["id"]] = article

    articles = list(unique_articles.values())

    # ------------------------------------
    # SORT NEWEST FIRST
    # ------------------------------------

    articles.sort(
        key=lambda article: article["published"],
        reverse=True
    )

    # ------------------------------------
    # APPLY SOURCE BALANCING
    # ------------------------------------

    source_counts = {}
    balanced_articles = []

    for article in articles:

        source = article["source"]

        current_count = source_counts.get(source, 0)

        if current_count < MAX_PER_SOURCE:

            balanced_articles.append(article)

            source_counts[source] = current_count + 1

    # ------------------------------------
    # APPLY OVERALL HEADLINE LIMIT
    # ------------------------------------

    articles = balanced_articles[:MAX_HEADLINES]

    # ------------------------------------
    # DISPLAY SOURCE DISTRIBUTION
    # ------------------------------------

    print("\nFinal headline distribution:")

    final_counts = {}

    for article in articles:

        source = article["source"]

        final_counts[source] = (
            final_counts.get(source, 0) + 1
        )

    for source, count in sorted(final_counts.items()):

        print(f"{source}: {count}")

    # ------------------------------------
    # PRESERVE PREVIOUS DATA IF EMPTY
    # ------------------------------------

    if not articles:

        print(
            "No articles retrieved. "
            "Keeping previous JSON."
        )

        return

    # ------------------------------------
    # GENERATE JSON OUTPUT
    # ------------------------------------

    output = {
        "updated": datetime.now(
            timezone.utc
        ).isoformat(),
        "count": len(articles),
        "articles": articles
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"\nSuccessfully saved "
        f"{len(articles)} headlines."
    )


# ----------------------------------------
# EXECUTE
# ----------------------------------------

if __name__ == "__main__":
    main()
