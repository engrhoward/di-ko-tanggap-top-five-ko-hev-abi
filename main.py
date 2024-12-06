import os
import sqlite3
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import pandas as pd
import streamlit as st
import threading
from dotenv import load_dotenv

# Load environment variables for Spotify API credentials
load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# Spotify API authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id='be5bf4d4ec214d218c705976796ebe38',
    client_secret='e79d71ac90594d5c90264723d199d70d',
    redirect_uri='http://localhost/',
    scope='user-read-currently-playing'
))

# Database setup
DB_NAME = 'play_counts.db'

def initialize_database():
    """Initialize the SQLite database with necessary tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Create tables if they don't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS song_count (
                        song_name TEXT PRIMARY KEY,
                        play_count INTEGER
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS artist_count (
                        artist_name TEXT PRIMARY KEY,
                        play_count INTEGER
                    )''')
    conn.commit()
    conn.close()

def load_data_from_database():
    """Load song and artist play counts from the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Load song data
    cursor.execute('SELECT * FROM song_count')
    songs = cursor.fetchall()
    play_count = {row[0]: row[1] for row in songs}

    # Load artist data
    cursor.execute('SELECT * FROM artist_count')
    artists = cursor.fetchall()
    artist_count = {row[0]: row[1] for row in artists}

    conn.close()
    return play_count, artist_count

def save_data_to_database(play_count, artist_count):
    """Save updated song and artist play counts to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Save song data
    for song, count in play_count.items():
        cursor.execute('''INSERT INTO song_count (song_name, play_count)
                          VALUES (?, ?)
                          ON CONFLICT(song_name) DO UPDATE SET play_count=excluded.play_count''',
                       (song, count))

    # Save artist data
    for artist, count in artist_count.items():
        cursor.execute('''INSERT INTO artist_count (artist_name, play_count)
                          VALUES (?, ?)
                          ON CONFLICT(artist_name) DO UPDATE SET play_count=excluded.play_count''',
                       (artist, count))

    conn.commit()
    conn.close()

# Initialize the database and load existing data
initialize_database()
play_count, artist_count = load_data_from_database()

last_song_id = None  # To avoid duplicate counting

def track_songs():
    """Continuously track currently playing songs and update play counts."""
    global play_count, artist_count, last_song_id
    while True:
        current_track = sp.current_user_playing_track()
        if current_track:
            track = current_track['item']
            song_id = track['id']
            song_name = track['name']
            artist_names = ", ".join(artist['name'] for artist in track['artists'])  # Extract artist names

            if song_id != last_song_id:
                # Update play count for the song
                play_count[song_name] = play_count.get(song_name, 0) + 1

                # Update play count for the artist(s)
                artist_count[artist_names] = artist_count.get(artist_names, 0) + 1

                # Save updated data to the database
                save_data_to_database(play_count, artist_count)

                # Track the last song to avoid duplicate counting
                last_song_id = song_id

        time.sleep(2)  # Avoid too frequent API calls

# Start the tracking thread
threading.Thread(target=track_songs, daemon=True).start()

# Streamlit App
st.title("Howard's Most Played Songs and Artists")

# Create placeholders for dynamic updates
song_graph_placeholder = st.empty()
song_table_placeholder = st.empty()
artist_graph_placeholder = st.empty()
artist_table_placeholder = st.empty()

# Main loop for visualizations
while True:
    # Sort and prepare data for visualization
    ranked_songs = sorted(play_count.items(), key=lambda x: x[1], reverse=True)
    ranked_artists = sorted(artist_count.items(), key=lambda x: x[1], reverse=True)

    # If there are any songs tracked, update the visualizations
    if ranked_songs:
        # Create DataFrame for songs
        df_songs = pd.DataFrame(ranked_songs, columns=["Song", "Play Count"]).head(10)

        # Update song bar chart and table dynamically
        with song_graph_placeholder:
            st.bar_chart(data=df_songs.set_index("Song"))
        with song_table_placeholder:
            st.table(df_songs)

    # If there are any artists tracked, update the visualizations
    if ranked_artists:
        # Create DataFrame for artists
        df_artists = pd.DataFrame(ranked_artists, columns=["Artist", "Play Count"]).head(10)

        # Update artist bar chart and table dynamically
        with artist_graph_placeholder:
            st.bar_chart(data=df_artists.set_index("Artist"))
        with artist_table_placeholder:
            st.table(df_artists)

    time.sleep(1)  # Refresh visualizations every second
