import json
import calendar
import hashlib
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests


MAX_HEADLINES = 30

MAX_PER_SOURCE = 3

FEEDS_FILE = "feeds.json"
OUTPUT_FILE = "headlines.json"


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


def main():

    with open(FEEDS_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)

    all_articles = []

    for source in config["feeds"]:
        all_articles.extend(fetch_feed(source))

    # Remove duplicate article URLs

unique_articles = {}

for article in all_articles:
    unique_articles[article["id"]] = article

articles = list(unique_articles.values())


# Sort all articles newest first

articles.sort(
    key=lambda article: article["published"],
    reverse=True
)


# Apply source balancing

source_counts = {}

balanced_articles = []

for article in articles:

    source = article["source"]

    current_count = source_counts.get(source, 0)

    if current_count < MAX_PER_SOURCE:

        balanced_articles.append(article)

        source_counts[source] = current_count + 1


# Keep the newest headlines from the balanced pool

articles = balanced_articles[:MAX_HEADLINES]


# Display source distribution in GitHub Actions log

print("\nFinal headline distribution:")

final_counts = {}

for article in articles:

    source = article["source"]

    final_counts[source] = final_counts.get(source, 0) + 1

for source, count in sorted(final_counts.items()):

    print(f"{source}: {count}")
    
    # Preserve previous data if every feed fails

    if not articles:
        print("No articles retrieved. Keeping previous JSON.")
        return

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

    print(f"Saved {len(articles)} headlines.")


if __name__ == "__main__":
    main()
