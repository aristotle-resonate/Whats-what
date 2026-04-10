from typing import TypedDict


class CityConfig(TypedDict):
    reddit_subreddit: str
    yelp_location: str
    eventbrite_city: str
    bandsintown_location: str
    eater_rss: str | None
    luma_city: str


CITY_CONFIG: dict[str, CityConfig] = {
    "austin": {
        "reddit_subreddit": "Austin",
        "yelp_location": "Austin, TX",
        "eventbrite_city": "Austin",
        "bandsintown_location": "Austin, TX",
        "eater_rss": "https://austin.eater.com/rss/index.xml",
        "luma_city": "austin",
    },
    "dallas": {
        "reddit_subreddit": "Dallas",
        "yelp_location": "Dallas, TX",
        "eventbrite_city": "Dallas",
        "bandsintown_location": "Dallas, TX",
        "eater_rss": "https://dallas.eater.com/rss/index.xml",
        "luma_city": "dallas",
    },
    "san-antonio": {
        "reddit_subreddit": "sanantonio",
        "yelp_location": "San Antonio, TX",
        "eventbrite_city": "San Antonio",
        "bandsintown_location": "San Antonio, TX",
        "eater_rss": None,
        "luma_city": "san-antonio",
    },
    "new-york": {
        "reddit_subreddit": "nyc",
        "yelp_location": "New York, NY",
        "eventbrite_city": "New York",
        "bandsintown_location": "New York, NY",
        "eater_rss": "https://ny.eater.com/rss/index.xml",
        "luma_city": "new-york",
    },
    "los-angeles": {
        "reddit_subreddit": "LosAngeles",
        "yelp_location": "Los Angeles, CA",
        "eventbrite_city": "Los Angeles",
        "bandsintown_location": "Los Angeles, CA",
        "eater_rss": "https://la.eater.com/rss/index.xml",
        "luma_city": "los-angeles",
    },
}

CITIES = list(CITY_CONFIG.keys())
