import streamlit as st
import pickle
import requests
import base64
import pandas as pd

# =========================
# API KEYS
# =========================
TMDB_API_KEY = "c9726776608cccd6a3cfdbf1b83d58ec"
SPOTIFY_CLIENT_ID = "44dbd0a7fe724a90836f3b4fc18c966c"
SPOTIFY_CLIENT_SECRET = "c9f80ea6b1fa447c8b358ffdaec58d30"

# =========================
# Placeholders
# =========================
MOVIE_PLACEHOLDER = "https://via.placeholder.com/500x750?text=No+Poster"
SONG_PLACEHOLDER = "https://via.placeholder.com/500x500?text=No+Cover"

# =========================
# Movies Section (Fixed)
# =========================
def fetch_movie_poster(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        poster_path = data.get('poster_path')
        if poster_path:
            return "https://image.tmdb.org/t/p/w500/" + poster_path
        else:
            return MOVIE_PLACEHOLDER
    except requests.exceptions.RequestException as e:
        print(f"Error fetching poster for {movie_id}: {e}")
        return "https://via.placeholder.com/500x750?text=Error"

def recommend_movie(movie, movies, similarity):
    index = movies[movies['title'] == movie].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    recommended_movie_names = []
    recommended_movie_posters = []
    for i in distances[1:6]:
        movie_id = movies.iloc[i[0]].movie_id
        recommended_movie_names.append(movies.iloc[i[0]].title)
        recommended_movie_posters.append(fetch_movie_poster(movie_id))
    return recommended_movie_names, recommended_movie_posters

# =========================
# Spotify - Auth & Covers
# =========================
def get_spotify_token():
    try:
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": "Basic " + base64.b64encode(
                f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
            ).decode()
        }
        data = {"grant_type": "client_credentials"}
        response = requests.post(url, headers=headers, data=data, timeout=8)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print("Spotify token error:", e)
        return None

def fetch_song_cover(track, artist, token):
    try:
        query = f"{track} {artist}"
        url = f"https://api.spotify.com/v1/search?q={query}&type=track&limit=1"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        data = response.json()
        if data["tracks"]["items"]:
            return data["tracks"]["items"][0]["album"]["images"][0]["url"]
    except Exception as e:
        print("Song cover fetch error:", e)
    return SONG_PLACEHOLDER

# =========================
# Load Song Data
# =========================
@st.cache_data
def load_songs():
    try:
        songs = pickle.load(open("songs.pkl", "rb"))
        similarity = pickle.load(open("song_similarity.pkl", "rb"))
        return songs, similarity
    except Exception as e:
        print("Song data load error:", e)
        return None, None

def recommend_song(selected_song, songs, similarity, token):
    index = songs[songs["track_name"] == selected_song].index[0]
    distances = sorted(list(enumerate(similarity[index])),
                       reverse=True, key=lambda x: x[1])[1:6]
    recommendations, covers = [], []
    for i in distances:
        row = songs.iloc[i[0]]
        track, artist = row["track_name"], row["artist(s)_name"]
        recommendations.append(f"{track} — {artist}")
        covers.append(fetch_song_cover(track, artist, token))
    return recommendations, covers

# =========================
# Streamlit UI
# =========================
st.title("🎬🎵 Movie & Song Recommendation System")

option = st.sidebar.radio("Choose Recommendation System", ("Movies", "Songs"))

# -------------------------
# Movies Section
# -------------------------
if option == "Movies":
    st.header("🎬 Movie Recommendation System")

    try:
        movies = pickle.load(open('movie_list.pkl', 'rb'))
        similarity = pickle.load(open('similarity.pkl', 'rb'))
    except Exception as e:
        st.error("❌ Movie pickle files not found")
        movies, similarity = None, None

    if movies is not None:
        movie_list = movies['title'].values
        selected_movie = st.selectbox("Type or select a movie from the dropdown", movie_list)
        if st.button('Show Recommendation'):
            names, posters = recommend_movie(selected_movie, movies, similarity)
            cols = st.columns(5)
            for col, name, poster in zip(cols, names, posters):
                with col:
                    st.text(name)
                    st.image(poster)

# -------------------------
# Songs Section
# -------------------------
elif option == "Songs":
    st.header("🎵 Song Recommendation System")

    songs, song_similarity = load_songs()
    if songs is None:
        st.error("❌ Song pickle files not found")
    else:
        selected_song = st.selectbox("Select a Song:", songs["track_name"].values)
        if st.button("Recommend Songs"):
            token = get_spotify_token()
            if token is None:
                st.error("❌ Failed to connect to Spotify API")
            else:
                with st.spinner("Fetching recommendations..."):
                    names, covers = recommend_song(selected_song, songs, song_similarity, token)
                st.subheader("Recommended Songs:")
                cols = st.columns(5)
                for i, col in enumerate(cols):
                    with col:
                        st.text(names[i])
                        st.image(covers[i])
