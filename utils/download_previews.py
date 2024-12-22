import os
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from pydub import AudioSegment
import re

# Genius API Access Token
GENIUS_ACCESS_TOKEN = "kegZ_ilazglzLCEk1ANFhLDgVeQHJQIqXN1S8Y1qia2NlzqNYvfBFv7ZhckcJeF7"  # Replace with your Genius access token
GENIUS_API_BASE_URL = "https://api.genius.com"

# Directories to save files
LYRICS_DIR = "../data/lyrics"
PREVIEWS_DIR = "../data/previews"
WAV_DIR = "../data/wav_previews"  # Separate folder for WAV files
os.makedirs(LYRICS_DIR, exist_ok=True)
os.makedirs(PREVIEWS_DIR, exist_ok=True)
os.makedirs(WAV_DIR, exist_ok=True)

# Index file to record processed songs
INDEX_FILE = "../data/index.txt"

# Ensure the index file exists
if not os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "w") as f:
        f.write("Processed Songs (1-indexed):\n")

def clean_song_title(title):
    """
    Cleans the song title by removing bracketed content (e.g., [From The Motion Picture "Barbie"]) 
    and extra spaces, leaving only the core title.
    """
    cleaned_title = re.sub(r"\[.*?\]|\(.*?\)|\{.*?\}", "", title)
    return cleaned_title.strip()

def search_song_on_genius(song_title, artist_name):
    search_url = f"{GENIUS_API_BASE_URL}/search"
    song_title = clean_song_title(song_title)
    headers = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}
    params = {"q": f"{song_title} {artist_name}"}
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        hits = response.json()["response"]["hits"]
        if hits:
            return hits[0]["result"]
    return None

def scrape_lyrics(genius_url):
    try:
        response = requests.get(genius_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            lyrics_div = soup.find("div", class_="lyrics") or soup.find("div", {"data-lyrics-container": "true"})
            if lyrics_div:
                return lyrics_div.get_text(separator="\n").strip()
    except Exception as e:
        print(f"Error scraping lyrics from {genius_url}: {e}")
    return None

def search_itunes_preview(track_name, artist_name):
    search_url = "https://itunes.apple.com/search"
    track_name = clean_song_title(track_name)
    params = {"term": f"{track_name} {artist_name}", "media": "music", "limit": 1}
    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        results = response.json().get("results")
        if results:
            return results[0].get("previewUrl")
    return None

def download_preview(preview_url, title):
    if preview_url:
        try:
            preview_response = requests.get(preview_url, stream=True)
            if preview_response.status_code == 200:
                preview_path = os.path.join(PREVIEWS_DIR, f"{title}.m4a")
                with open(preview_path, "wb") as f:
                    for chunk in preview_response.iter_content(1024):
                        f.write(chunk)
                print(f"Preview saved: {preview_path}")
                return preview_path
        except Exception as e:
            print(f"Error downloading preview for {title}: {e}")
    return None

def convert_m4a_to_wav(m4a_path, title):
    try:
        wav_path = os.path.join(WAV_DIR, f"{title}.wav")
        audio = AudioSegment.from_file(m4a_path, format="m4a")
        audio.export(wav_path, format="wav")
        print(f"Converted to WAV: {wav_path}")
        return wav_path
    except Exception as e:
        print(f"Error converting {m4a_path} to WAV: {e}")
    return None

def fetch_lyrics_and_preview(row_index, song_data, max_songs=100):
    """
    Fetch lyrics and preview for a given song and log the 1-indexed row number.
    """
    title, artist = song_data
    try:
        # Fetch lyrics
        song = search_song_on_genius(title, artist)
        if not song:
            print(f"No lyrics found for: {title} by {artist}")
            return False

        song_url = song["url"]
        lyrics = scrape_lyrics(song_url)
        preview_url = search_itunes_preview(title, artist)

        if lyrics and preview_url:
            # Save lyrics
            lyrics_path = os.path.join(LYRICS_DIR, f"{title}.txt")
            with open(lyrics_path, "w", encoding="utf-8") as f:
                f.write(lyrics)
            print(f"Lyrics saved: {lyrics_path}")

            # Save and convert preview
            m4a_path = download_preview(preview_url, title)
            if m4a_path:
                convert_m4a_to_wav(m4a_path, title)

                # Append to index.txt with the 1-indexed row number
                with open(INDEX_FILE, "a") as index_file:
                    index_file.write(f"{row_index + 1}: {title} by {artist}\n")
                return True
        else:
            print(f"Missing lyrics or preview for: {title} by {artist}")
    except Exception as e:
        print(f"Error processing {title} by {artist}: {e}")
    return False

def main():
    file_path = "../data/song.csv"  # Replace with your CSV file path
    try:
        data = pd.read_csv(file_path, encoding="ISO-8859-2")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    processed_count = 0
    max_songs = 200
    for index, row in data.iterrows():
        if processed_count >= max_songs:
            break

        track_name = row["track_name"]
        artist_name = row["artist(s)_name"]
        success = fetch_lyrics_and_preview(index, (track_name, artist_name), max_songs)

        if success:
            processed_count += 1

        time.sleep(1)  # Rate limiting

if __name__ == "__main__":
    main()