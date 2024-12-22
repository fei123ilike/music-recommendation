import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import requests
import time
import os

# Step 1: Set up Spotify API credentials
SPOTIFY_CLIENT_ID = 'a466578a0f4d49bea980e068fa0a326a'
SPOTIFY_CLIENT_SECRET = 'c34595a1a5c54331b3964d8e57fae362'
# ACCESS_TOKEN = "1POdFZRZbvb...qqillRxMr2z"

# Authenticate with Spotify using Authorization Code Flow
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri="http://localhost:8888/callback",
    scope="playlist-read-private playlist-read-collaborative"
))

# Function to fetch playlist data
def fetch_playlist_data(playlist_id):
    playlist_tracks = []
    try:
        results = sp.playlist_tracks(playlist_id, market="US")
        
        # Loop through all tracks in the playlist
        while results:
            for item in results['items']:
                track = item['track']
                if track:  # Ensure the track data is not None
                    # Fetch audio features for the track
                    try:
                        audio_features = sp.audio_features(track['id'])
                        audio_features = audio_features[0] if audio_features else {}
                    except Exception as e:
                        print(f"Error fetching audio features for {track['name']}: {e}")
                        audio_features = {}

                    # Fetch artist genres
                    artist_id = track['artists'][0]['id']
                    try:
                        artist = sp.artist(artist_id)
                        genres = artist['genres']
                    except Exception as e:
                        print(f"Error fetching artist genres for {track['name']}: {e}")
                        genres = []

                    # Compile track information
                    track_info = {
                        "Track Name": track['name'],
                        "Artist": ", ".join([artist['name'] for artist in track['artists']]),
                        "Album": track['album']['name'],
                        "Release Date": track['album']['release_date'],
                        "Popularity": track['popularity'],
                        "Danceability": audio_features.get('danceability'),
                        "Energy": audio_features.get('energy'),
                        "Key": audio_features.get('key'),
                        "Loudness": audio_features.get('loudness'),
                        "Mode": audio_features.get('mode'),
                        "Speechiness": audio_features.get('speechiness'),
                        "Acousticness": audio_features.get('acousticness'),
                        "Instrumentalness": audio_features.get('instrumentalness'),
                        "Liveness": audio_features.get('liveness'),
                        "Valence": audio_features.get('valence'),
                        "Tempo": audio_features.get('tempo'),
                        "Duration (ms)": track['duration_ms'],
                        "Time Signature": audio_features.get('time_signature'),
                        "Genres": ", ".join(genres),
                        "Preview URL": track.get('preview_url', None),  # May be None if not available
                        "Spotify URL": track['external_urls']['spotify']
                    }
                    
                    playlist_tracks.append(track_info)
                    
                    # Add a delay to avoid hitting rate limits
                    time.sleep(0.5)  # 2 requests per second
                print("Processed Track:", track['name'])
            
            # Get the next page of results
            results = sp.next(results) if results['next'] else None
    except spotipy.exceptions.SpotifyException as e:
        print(f"Error fetching playlist data: {e}")
    
    return playlist_tracks

# Function to save metadata to CSV
def save_to_csv(playlist_tracks, csv_file="playlist_metadata.csv"):
    df = pd.DataFrame(playlist_tracks)
    df.to_csv(csv_file, index=False)
    print(f"Saved metadata to {csv_file}")

# Function to download previews
def download_preview(preview_url, track_name, save_dir="previews"):
    if preview_url:
        response = requests.get(preview_url)
        sanitized_name = "".join(c if c.isalnum() else "_" for c in track_name)  # Sanitize file name
        file_path = f"{save_dir}/{sanitized_name}.mp3"
        with open(file_path, "wb") as file:
            file.write(response.content)
        print(f"Downloaded: {track_name}")
    else:
        print(f"No preview available for: {track_name}")

# Save metadata and download previews
def save_playlist_to_csv_and_download(playlist_id, csv_file="../data/playlist_metadata.csv", save_dir="../data/previews"):
    os.makedirs(save_dir, exist_ok=True)
    
    # Fetch playlist data
    playlist_tracks = fetch_playlist_data(playlist_id)
    
    # Save metadata to CSV
    save_to_csv(playlist_tracks, csv_file)
    
    # Download previews
    for track in playlist_tracks:
        download_preview(track["Preview URL"], track["Track Name"], save_dir)
        time.sleep(1)  # Delay between downloads

# Main function to execute the process
if __name__ == "__main__":
    playlist_id = "774kUuKDzLa8ieaSmi8IfS"  # User-created public playlist ID
    try:
        playlist = sp.playlist(playlist_id)
        print(f"Playlist Name: {playlist['name']}")
        save_playlist_to_csv_and_download(playlist_id)
    except Exception as e:
        print(f"Error: {e}")