import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from skyfield.api import load, Topos
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Ensure nltk resources are available
nltk.download('vader_lexicon')

# Load planetary data
planets = load('de421.bsp')
ts = load.timescale()

# Define observer location (e.g., at the center of the Earth)
earth = planets['earth']
observer = earth + Topos(latitude_degrees=0, longitude_degrees=0)

# Define planetary objects
planetary_objects = {
    'mercury': planets['mercury'],
    'venus': planets['venus'],
    'mars': planets['mars'],
    'jupiter': planets['jupiter barycenter'],
    'saturn': planets['saturn barycenter'],
    'uranus': planets['uranus barycenter'],
    'neptune': planets['neptune barycenter'],
    'pluto': planets['pluto barycenter']
}

# Define the aspects we're interested in
aspect_angles = {
    "conjunction": 0,
    "opposition": 180,
    "trine": 120,
    "square": 90,
    "sextile": 60,
    "quintile": 72
}
aspect_tolerance = 8  # Degrees of tolerance for aspects

# Function to calculate aspects for a given date
def calculate_aspects(date):
    t = ts.utc(date.year, date.month, date.day)
    positions = {name: observer.at(t).observe(planet).apparent().ecliptic_latlon()[1].degrees for name, planet in planetary_objects.items()}

    aspects = {}
    for planet1, pos1 in positions.items():
        for planet2, pos2 in positions.items():
            if planet1 != planet2:
                angle = abs(pos1 - pos2)
                for aspect, aspect_angle in aspect_angles.items():
                    if abs(angle - aspect_angle) <= aspect_tolerance or abs((angle + 360) - aspect_angle) <= aspect_tolerance:
                        key_str = f"{planet1}-{planet2}-{aspect}"
                        if key_str not in aspects:
                            aspects[key_str] = []
                        aspects[key_str].append(date.strftime('%Y-%m-%d'))
    return aspects

# Function to match current aspects with historical data
def match_aspects_with_history(current_aspects, years_back=100):
    matched_dates_map = {}
    for i in range(years_back):
        historical_date = datetime.now() - timedelta(days=365 * (i + 1))
        historical_aspects = calculate_aspects(historical_date)

        for aspect_key, current_dates in current_aspects.items():
            if aspect_key in historical_aspects:
                if aspect_key not in matched_dates_map:
                    matched_dates_map[aspect_key] = []
                matched_dates_map[aspect_key].extend(historical_aspects[aspect_key])

    return matched_dates_map

# Function to fetch Wikipedia events for a given year
def fetch_wikipedia_events(year):
    url = f'https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&explaintext=true&titles={year}'
    response = requests.get(url)
    json_data = response.json()

    pages = json_data.get('query', {}).get('pages', {})
    extract = ""
    for page_id in pages:
        if 'extract' in pages[page_id]:
            extract = pages[page_id]['extract']

    return extract

# Function to categorize events based on keywords in the event descriptions
def categorize_event(description):
    if "war" in description.lower() or "conflict" in description.lower() or "battle" in description.lower():
        return "War"
    elif "politic" in description.lower() or "election" in description.lower() or "government" in description.lower():
        return "Political"
    elif "economic" in description.lower() or "market" in description.lower() or "financial" in description.lower():
        return "Economic"
    elif "environment" in description.lower() or "hurricane" in description.lower() or "earthquake" in description.lower():
        return "Environmental"
    elif "scientific" in description.lower() or "discovery" in description.lower() or "nobel" in description.lower():
        return "Scientific"
    elif "cultural" in description.lower() or "art" in description.lower() or "festival" in description.lower():
        return "Cultural"
    else:
        return "Other"

# Function to extract a probable event name from the description
def extract_event_name(description):
    words = description.split()
    if len(words) > 5:
        return " ".join(words[:5]) + "..."
    else:
        return " ".join(words)

# Function to analyze the sentiment of an event's description
def analyze_sentiment(description):
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(description)
    return sentiment['compound']  # Returns the compound sentiment score

# Function to generate historical context summary
def generate_historical_context(aspect_key, event_name, year, event_category):
    return (f"{aspect_key.replace('-', ' ').title()} has historically coincided with periods of {event_category.lower()}. "
            f"For example, during {year}, this aspect was present during the event '{event_name}', "
            f"which led to significant {event_category.lower()} developments. "
            "The key during this transit is to be mindful of these patterns and consider the potential for similar dynamics.")

# Function to analyze the current week's aspects
def analyze_weekly_aspects(start_date, days=7):
    weekly_aspects_map = {}
    for i in range(days):
        date = start_date + timedelta(days=i)
        aspects = calculate_aspects(date)

        for aspect_key, dates in aspects.items():
            if aspect_key not in weekly_aspects_map:
                weekly_aspects_map[aspect_key] = []
            weekly_aspects_map[aspect_key].extend(dates)

    return weekly_aspects_map

# Start analysis
start_date = datetime.now()
current_week_aspects = analyze_weekly_aspects(start_date)

# Match with historical aspects and fetch corresponding historical events
matched_aspects_map = match_aspects_with_history(current_week_aspects)
data = []

for aspect_key, matched_dates in matched_aspects_map.items():
    for date in matched_dates:
        event_description = fetch_wikipedia_events(date[:4])
        event_category = categorize_event(event_description)
        event_name = extract_event_name(event_description)
        sentiment_score = analyze_sentiment(event_description)
        historical_context = generate_historical_context(aspect_key, event_name, date[:4], event_category)
        summary = (f"On {date}, during the aspect {aspect_key}, the event '{event_name}' occurred, categorized as {event_category}.")

        data.append({
            "aspect_key": aspect_key,
            "date": date,
            "event_category": event_category,
            "event_name": event_name,
            "sentiment_score": sentiment_score,  # Add sentiment score to the data
            "historical_context": historical_context,  # Add historical context
            "summary": summary
        })

# Convert the data into a pandas DataFrame
df = pd.DataFrame(data)

# Save the DataFrame to a JSON file
df.to_json("weeks_historical_celestial_forecast.json", orient='records', lines=True)
