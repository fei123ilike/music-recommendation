import os
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
import re

# Genius API Access Token
GENIUS_ACCESS_TOKEN = "kegZ_ilazglzLCEk1ANFhLDgVeQHJQIqXN1S8Y1qia2NlzqNYvfBFv7ZhckcJeF7"  # Replace with your Genius access token
GENIUS_API_BASE_URL = "https://api.genius.com"

# Allowed main tags
MAIN_TAGS = {"Country", "Pop", "R&B", "Rap", "Rock"}

import re

def clean_song_title(title):
    """
    Cleans the song title by removing bracketed content (e.g., [From The Motion Picture "Barbie"]) 
    and extra spaces, leaving only the core title.
    
    Args:
        title (str): The original song title.
    
    Returns:
        str: The cleaned song title.
    """
    # Remove content inside brackets (e.g., [], (), {})
    cleaned_title = re.sub(r"\[.*?\]|\(.*?\)|\{.*?\}", "", title)
    # Remove extra spaces
    cleaned_title = cleaned_title.strip()
    return cleaned_title

def search_song_on_genius(song_title, artist_name):
    """
    Searches for a song on Genius and returns the most relevant song match.
    Args:
        song_title (str): The title of the song.
        artist_name (str): The name of the artist.
    Returns:
        dict: The best song match or None if no valid match is found.
    """
    # Clean the song title
    cleaned_title = clean_song_title(song_title)
    print(f"Searching for: {cleaned_title} by {artist_name}")

    search_url = f"{GENIUS_API_BASE_URL}/search"
    headers = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}
    params = {"q": f"{cleaned_title} {artist_name}"}

    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        search_results = response.json()["response"]["hits"]
        for result in search_results:
            # Only consider results from the "song" index
            if result["index"] == "song":
                # Check if the primary artist matches
                result_artist = result["result"]["primary_artist"]["name"].lower()
                if artist_name.lower() in result_artist:
                    return result["result"]  # Return the matching song
    return None

def scrape_genres(genius_url):
    """
    Scrapes the first three main tags (genres) from a Genius song page.
    Filters tags based on the allowed MAIN_TAGS.
    Excludes tracks with "Non-Music" tags.
    Args:
        genius_url (str): URL of the Genius song page.
    Returns:
        str: Comma-separated list of up to three genres from MAIN_TAGS, or None if no tags are found.
    """
    try:
        response = requests.get(genius_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Locate the tags container
            tags_div = soup.find("div", class_="SongTags-sc-b55131f0-1")
            if tags_div:
                # Extract all <a> tags inside the container
                tags = [tag.get_text(strip=True) for tag in tags_div.find_all("a", href=lambda x: "/tags/" in x)]
                
                # Exclude if "Non-Music" is in the tags
                if "Non-Music" in tags:
                    print(f"Excluding track due to 'Non-Music' tag: {genius_url}")
                    return None
                
                # Filter tags based on MAIN_TAGS
                filtered_tags = [tag for tag in tags if tag in MAIN_TAGS]
                return ", ".join(filtered_tags[:3])  # Get up to 3 tags and join them
    except Exception as e:
        print(f"Error scraping genres from {genius_url}: {e}")
    return None

def fetch_genres(song_data):
    """
    Fetches genres for a given song.
    Args:
        song_data (tuple): A tuple containing the song title and artist name.
    Returns:
        str: Comma-separated genres or None if not found.
    """
    title, artist = song_data
    try:
        # Search for the song on Genius
        song = search_song_on_genius(title, artist)
        if not song:
            print(f"No results found for: {title} by {artist}")
            return None

        song_url = song["url"]
        # Scrape the genres
        return scrape_genres(song_url)
    except Exception as e:
        print(f"Error fetching genres for {title} by {artist}: {e}")
    return None

def main():
    """
    Main function to process songs and save genres.
    """
    file_path = "../data/spotify-2023.csv"  # Replace with your CSV file path
    output_csv = "../data/song.csv"

    try:
        # Read the original CSV
        data = pd.read_csv(file_path, encoding="ISO-8859-2")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Insert a new 'genre' column
    data.insert(1, "genre", None)

    counter = 0
    # Process each song in the CSV file
    for index, row in data.iterrows():
        track_name = row["track_name"]
        artist_name = row["artist(s)_name"]

        print(f"Processing: {track_name} by {artist_name}")
        genres = fetch_genres((track_name, artist_name))
        if genres is None:  # Skip tracks with "Non-Music" tags or no genres
            print(f"Skipping: {track_name} by {artist_name}")
            continue

        data.at[index, "genre"] = genres  # Update the genre column

        # Rate limiting
        time.sleep(0.1)
        counter += 1
        if counter > 500:  # Limit to 10 songs for testing
            break

    # Save the updated data to a new CSV
    data.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"Processed data saved to {output_csv}")

if __name__ == "__main__":
    main()