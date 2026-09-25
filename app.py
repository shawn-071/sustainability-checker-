import html
import hashlib
import io
import json
import os
import textwrap
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import folium
from folium.plugins import LocateControl
from branca.element import MacroElement
from streamlit_folium import st_folium
from PIL import Image
from jinja2 import Template
import qrcode

from crop_data import (
    CROP_THRESHOLDS,
)
from data_sources import fetch_climate, fetch_soil, fetch_terrain
from suitability import evaluate, get_factor_scores
from disease_model import load_model, predict
from localization import LANGUAGES, t as tr
from local_store import (
    authenticate,
    create_user,
    get_history,
    get_location_cache,
    init_db,
    put_location_cache,
    record_history,
    ensure_external_user,
)
from plant_health import first_steps
from polyculture import recommendations


# ============================================================
# PAGE CONFIG
# ============================================================

APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "assets" / "terrasense-logo.png"

st.set_page_config(
    page_title="CropWise | Field planning companion",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "CropWise",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONSTANTS
# ============================================================

DEFAULT_LAT = 25.2854
DEFAULT_LON = 51.5310

PAGES = ["map", "planner", "doctor", "history", "impact", "share"]


# ============================================================
# SESSION STATE
# ============================================================

if "page" not in st.session_state:
    st.session_state.page = PAGES[0]

if "page_navigation" not in st.session_state:
    st.session_state.page_navigation = st.session_state.page

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Light"

if "language" not in st.session_state:
    st.session_state.language = "en"

if "offline_mode" not in st.session_state:
    st.session_state.offline_mode = False

if "username" not in st.session_state:
    st.session_state.username = None

if "lat" not in st.session_state:
    st.session_state.lat = DEFAULT_LAT

if "lon" not in st.session_state:
    st.session_state.lon = DEFAULT_LON

if "field_point_selected" not in st.session_state:
    st.session_state.field_point_selected = False

if "field_map_generation" not in st.session_state:
    st.session_state.field_map_generation = 0

if "location_auto_start" not in st.session_state:
    st.session_state.location_auto_start = True

if "planner_lat" not in st.session_state:
    st.session_state.planner_lat = st.session_state.lat

if "planner_lon" not in st.session_state:
    st.session_state.planner_lon = st.session_state.lon

if "planner_point_selected" not in st.session_state:
    st.session_state.planner_point_selected = False

if "planner_map_generation" not in st.session_state:
    st.session_state.planner_map_generation = 0

if "planner_last_map_click" not in st.session_state:
    st.session_state.planner_last_map_click = None

if "auth_provider" not in st.session_state:
    st.session_state.auth_provider = None

if "display_name" not in st.session_state:
    st.session_state.display_name = None

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "crop_results" not in st.session_state:
    st.session_state.crop_results = None

if "disease_results" not in st.session_state:
    st.session_state.disease_results = None

if "last_map_click" not in st.session_state:
    st.session_state.last_map_click = None

if "latitude_input" not in st.session_state:
    st.session_state.latitude_input = DEFAULT_LAT

if "longitude_input" not in st.session_state:
    st.session_state.longitude_input = DEFAULT_LON

if "manual_field_data" not in st.session_state:
    st.session_state.manual_field_data = False

try:
    init_db()
    DB_READY = True
except Exception:
    DB_READY = False


def google_auth_configured():
    """Return true only when the required Google OIDC secrets are present."""
    try:
        auth = st.secrets.get("auth", {})
        required = ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")
        values = [str(auth.get(key, "")).strip().lower() for key in required]
        return all(
            value
            and value not in {"xxx", "<your-value>"}
            and "replace-with" not in value
            and not value.startswith("<")
            for value in values
        )
    except Exception:
        return False


GOOGLE_LOGIN_CONFIGURED = google_auth_configured()

try:
    google_user = st.user if st.user.is_logged_in else None
except Exception:
    google_user = None

if google_user is not None:
    google_identity = google_user.to_dict()
    google_email = str(google_identity.get("email") or google_identity.get("sub") or "").strip().lower()
    if google_email:
        external_username = "google_" + hashlib.sha256(google_email.encode("utf-8")).hexdigest()[:20]
        if DB_READY:
            try:
                ensure_external_user(external_username)
            except Exception:
                DB_READY = False
        st.session_state.username = external_username
        st.session_state.display_name = google_identity.get("name") or google_identity.get("email") or "Google account"
        st.session_state.auth_provider = "google"


# ============================================================
# HELPERS
# ============================================================

def safe_text(value):
    """Safely display text inside HTML."""
    if value is None:
        return "—"
    return html.escape(str(value))


def render_html(markup):
    """Render an HTML fragment without Markdown interpreting indentation as code."""
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)


class LocationClickBridge(MacroElement):
    """Forward a browser geolocation result as a normal map click for Streamlit."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        var cropwiseMap = {{ this._parent.get_name() }};
        cropwiseMap.on('locationfound', function(event) {
            cropwiseMap.fire('click', {latlng: event.latlng});
        });
        {% endmacro %}
        """
    )


def add_location_controls(map_object, auto_start=False):
    LocateControl(
        auto_start=auto_start,
        position="topleft",
        strings={"title": "Show my location"},
        flyTo=True,
        keepCurrentZoomLevel=False,
        showPopup=True,
    ).add_to(map_object)
    LocationClickBridge().add_to(map_object)


def get_location_coordinates(map_data):
    clicked = map_data.get("last_clicked") if isinstance(map_data, dict) else None
    if not clicked:
        return None
    try:
        latitude = round(float(clicked["lat"]), 5)
        longitude = round(float(clicked["lng"]), 5)
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def score_percent(score):
    if score is None:
        return 0

    try:
        return int(round(float(score) * 100))
    except (TypeError, ValueError):
        return 0


def factor_status(score):
    if score is None:
        return "Unavailable"

    if score >= 0.8:
        return "Good"

    if score >= 0.5:
        return "Moderate"

    return "Poor"


def field_result_summary(crop, verdict, score, factors=None):
    """Turn the screening result into a short, farmer-facing explanation."""
    if verdict == "Unknown":
        return (
            f"There is not enough climate or soil information to assess {crop}. "
            "Add local values or reconnect to refresh the field data, then try again."
        )

    score_text = f" The screening score is {score_percent(score)}%." if score is not None else ""

    if verdict == "Suitable":
        return (
            f"The available climate and soil indicators are broadly within the "
            f"screening ranges for {crop}.{score_text} Check local planting dates, "
            "water access, and field conditions before making a planting decision."
        )

    if verdict == "Marginal":
        review_factors = [
            name.lower()
            for name, factor in (factors or {}).items()
            if factor.get("score") is not None and factor["score"] < 0.8
        ]
        review_text = (
            "Review " + ", ".join(review_factors) + " against local conditions. "
            if review_factors
            else "Review the factor breakdown against local conditions. "
        )
        return (
            f"Some available conditions fit {crop}, while others are outside its "
            f"preferred ranges.{score_text} {review_text}Local advice can help "
            "determine whether the crop is practical for this field."
        )

    return (
        f"The available field indicators are outside the screening ranges for "
        f"{crop}.{score_text} Consider comparing other crops and confirm the "
        "location and data before deciding."
    )


def leaf_result_summary(plant, disease, match_score):
    """Describe the model's leading label in plain language and set expectations."""
    score_text = f" The model match score is {match_score * 100:.1f}%."
    if disease == "Healthy":
        return (
            f"The image model's leading match is a healthy-looking {plant} leaf."
            f"{score_text} Keep monitoring the plant; this screen cannot rule out disease."
        )
    return (
        f"The image model's leading match is {disease} on {plant}.{score_text} "
        "This is an automated visual screening, not a confirmed diagnosis. "
        "Use the first steps below and ask local agricultural support to confirm the cause."
    )


def format_factor_value(value, unit):
    if value is None:
        return "Unavailable"

    try:
        if unit == "°C":
            return f"{float(value):.1f} °C"

        if unit == "mm/year":
            return f"{float(value):,.0f} mm/year"

        if unit == "pH":
            return f"{float(value):.2f}"

    except (TypeError, ValueError):
        pass

    return str(value)


def reset_analysis():
    st.session_state.analysis = None
    st.session_state.crop_results = None
    st.session_state.disease_results = None


def sync_field_coordinates():
    latitude = float(st.session_state.latitude_input)
    longitude = float(st.session_state.longitude_input)
    coordinates = (round(latitude, 5), round(longitude, 5))
    st.session_state.lat = latitude
    st.session_state.lon = longitude
    st.session_state.last_map_click = coordinates
    st.session_state.field_point_selected = True
    st.session_state.location_auto_start = False
    st.session_state.field_map_generation += 1
    if not st.session_state.planner_point_selected:
        st.session_state.planner_lat = latitude
        st.session_state.planner_lon = longitude
        st.session_state.planner_lat_input = latitude
        st.session_state.planner_lon_input = longitude
        st.session_state.planner_point_selected = True
    reset_analysis()


def sync_planner_coordinates():
    latitude = float(st.session_state.planner_lat_input)
    longitude = float(st.session_state.planner_lon_input)
    st.session_state.planner_lat = latitude
    st.session_state.planner_lon = longitude
    st.session_state.planner_last_map_click = (round(latitude, 5), round(longitude, 5))
    st.session_state.planner_point_selected = True
    st.session_state.planner_map_generation += 1
    st.session_state.crop_results = None


def fetch_field_data(latitude, longitude, offline=False, manual=None):
    """Read the exact saved point offline, otherwise use free public sources and cache it."""
    cached = get_location_cache(latitude, longitude) if DB_READY else None
    if offline:
        if cached:
            return cached["climate"], cached["soil"], "saved"
        if manual and manual.get("enabled"):
            return (
                {
                    "temp_c": manual.get("temp_c"),
                    "rain_mm_year": manual.get("rain_mm_year"),
                    "humidity_pct": None,
                    "error": "Entered locally by the user.",
                },
                {"ph": manual.get("ph"), "error": "Entered locally by the user."},
                "manual",
            )
        empty_climate = {
            "temp_c": None, "rain_mm_year": None, "humidity_pct": None,
            "error": "No saved values for this point. Enter local values below or connect to refresh.",
        }
        return empty_climate, {"ph": None, "error": "No saved soil value for this point."}, "empty"

    climate = fetch_climate(latitude, longitude)
    soil = fetch_soil(latitude, longitude)
    terrain = fetch_terrain(latitude, longitude)
    soil.update(terrain)
    if cached:
        for key in ("temp_c", "rain_mm_year", "humidity_pct"):
            if climate.get(key) is None:
                climate[key] = cached.get("climate", {}).get(key)
        if soil.get("ph") is None:
            soil["ph"] = cached.get("soil", {}).get("ph")
        for key in ("elevation_m", "slope_pct"):
            if soil.get(key) is None:
                soil[key] = cached.get("soil", {}).get(key)
    if DB_READY and (climate.get("temp_c") is not None or soil.get("ph") is not None or soil.get("elevation_m") is not None):
        put_location_cache(latitude, longitude, {"climate": climate, "soil": soil})
    return climate, soil, "live"


def save_activity(entry_type, *, latitude=None, longitude=None, crop=None, outcome=None, score=None, details=None):
    username = st.session_state.get("username")
    if username and DB_READY:
        record_history(
            username,
            entry_type,
            latitude=latitude,
            longitude=longitude,
            crop=crop,
            outcome=outcome,
            score=score,
            details=details,
        )


@st.cache_resource(show_spinner=False)
def cached_disease_model(offline):
    return load_model(local_files_only=offline)


def render_voice_button(message):
    language = {"en": "en-US", "ar": "ar-SA", "zh": "zh-CN", "fr": "fr-FR", "ru": "ru-RU", "es": "es-ES"}.get(st.session_state.language, "en-US")
    safe_message = json.dumps(message, ensure_ascii=False).replace("</", "<\\/")
    components.html(
        f"""<button type="button" aria-label="Read guidance aloud" aria-pressed="false" style="
            background:#174d38;color:white;border:0;border-radius:8px;
            padding:10px 16px;font-size:15px;font-weight:600;cursor:pointer">
            Read this guidance aloud
        </button>
        <script>
        const button = document.currentScript.previousElementSibling;
        let activeUtterance = null;
        let isPlaying = false;
        const idleLabel = 'Read this guidance aloud';
        const playingLabel = 'Stop reading';
        function setPlaying(value) {{
          isPlaying = value;
          button.textContent = value ? playingLabel : idleLabel;
          button.setAttribute('aria-label', value ? playingLabel : idleLabel);
          button.setAttribute('aria-pressed', value ? 'true' : 'false');
        }}
        button.addEventListener('click', () => {{
          if (!('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) {{
            button.textContent = 'Voice playback is unavailable';
            return;
          }}
          if (isPlaying) {{
            setPlaying(false);
            activeUtterance = null;
            window.speechSynthesis.cancel();
            return;
          }}
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance({safe_message});
          activeUtterance = utterance;
          utterance.lang = '{language}';
          utterance.onend = () => {{ if (activeUtterance === utterance) setPlaying(false); }};
          utterance.onerror = () => {{ if (activeUtterance === utterance) setPlaying(false); }};
          setPlaying(true);
          window.speechSynthesis.speak(utterance);
        }});
        </script>""",
        height=54,
    )


# ============================================================
# CUSTOM CSS
# ============================================================

dark_theme = st.session_state.theme_mode == "Dark"
theme = {
    "page": "#0b0f14" if dark_theme else "#ffffff",
    "surface": "#151b22" if dark_theme else "#f7faf8",
    "card": "#1b232c" if dark_theme else "#ffffff",
    "text": "#edf2f7" if dark_theme else "#18231d",
    "muted": "#aab6c2" if dark_theme else "#5c6b62",
    "border": "#34404c" if dark_theme else "#dce5df",
    "accent": "#72d6b2" if dark_theme else "#176b4d",
    "hero": "#162720" if dark_theme else "#eef8f1",
}

render_html(
    f"""
    <style>
    :root {{
        color-scheme: {"dark" if dark_theme else "light"};
        --app-page: {theme["page"]};
        --app-surface: {theme["surface"]};
        --app-card: {theme["card"]};
        --app-text: {theme["text"]};
        --app-muted: {theme["muted"]};
        --app-border: {theme["border"]};
        --app-accent: {theme["accent"]};
        --app-hero: {theme["hero"]};
    }}
    html, body, .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stMain"], [data-testid="stHeader"],
    [data-testid="stSidebar"], [data-testid="stBottom"] {{
        background-color: var(--app-page) !important;
        color: var(--app-text) !important;
    }}
    .stApp, [data-testid="stAppViewContainer"] {{ min-height: 100vh; }}
    [data-testid="stMain"] > div, [data-testid="stSidebar"] > div {{
        background-color: var(--app-page) !important;
    }}
    [data-testid="stSidebar"] {{ border-right: 1px solid var(--app-border); }}
    [data-testid="stHeader"] {{ border-bottom: 1px solid var(--app-border); }}
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4, [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6, [data-testid="stCaptionContainer"] {{
        color: var(--app-text) !important;
    }}
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
    [data-testid="stRadio"] label, [data-testid="stCheckbox"] label,
    [data-testid="stSelectbox"] label, [data-testid="stNumberInput"] label {{
        color: var(--app-text) !important;
    }}
    [data-testid="stCaptionContainer"] {{ opacity: 0.84; }}
    [data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: var(--app-card) !important;
        border-color: var(--app-border) !important;
    }}
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{ color: var(--app-text) !important; }}
    input, textarea, [data-baseweb="select"] > div,
    [data-baseweb="input"] > div, [data-baseweb="textarea"] > div {{
        background-color: var(--app-card) !important;
        color: var(--app-text) !important;
        border-color: var(--app-border) !important;
    }}
    [data-testid="stExpander"] {{
        background-color: var(--app-card) !important;
        border-color: var(--app-border) !important;
    }}
    [data-testid="stAlert"] {{ background-color: var(--app-surface) !important; }}
    [data-testid="stAlert"] *, [data-testid="stExpander"] * {{ color: var(--app-text) !important; }}
    [data-testid="stBaseButton-secondary"] {{
        background-color: var(--app-surface) !important;
        color: var(--app-text) !important;
        border-color: var(--app-border) !important;
    }}
    [data-testid="stBaseButton-primary"] {{ background-color: var(--app-accent) !important; color: #ffffff !important; }}
    .block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }}
    .hero {{
        padding: 1.3rem 1.5rem; border-radius: 18px;
        background: var(--app-hero); border: 1px solid var(--app-border);
        margin-bottom: 1rem; color: var(--app-text);
    }}
    .hero h1 {{ margin: 0; font-size: 2.25rem; font-weight: 800; color: var(--app-text) !important; }}
    .hero p {{ margin: .4rem 0 0; color: var(--app-muted) !important; font-size: 1.02rem; }}
    .about-box {{ padding: 1.2rem; border-radius: 16px; border: 1px solid var(--app-border); background: var(--app-card); margin-bottom: 1rem; }}
    .about-title {{ font-size: 1.2rem; font-weight: 750; margin-bottom: .7rem; color: var(--app-accent); }}
    .feature-title {{ color: var(--app-accent); font-weight: 750; font-size: 1.05rem; margin-bottom: .35rem; }}
    footer {{ visibility: hidden; }}
    </style>
    """
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    language_names = list(LANGUAGES.keys())
    selected_language = st.selectbox(
        tr("language", st.session_state.language),
        language_names,
        index=list(LANGUAGES.values()).index(st.session_state.language),
        key="language_selector",
    )
    st.session_state.language = LANGUAGES[selected_language]
    language = st.session_state.language

    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=104)
    st.markdown("## CropWise")
    st.caption(tr("tagline", language))

    st.divider()

    st.selectbox("Appearance", ["Light", "Dark"], key="theme_mode")

    st.markdown(f"### {safe_text(tr('nav', language))}")

    for sidebar_page in PAGES:
        sidebar_label = tr(sidebar_page, language)

        if st.button(
            sidebar_label,
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.page == sidebar_page
                else "secondary"
            ),
            key=f"sidebar_{sidebar_page}",
        ):

            if st.session_state.page != sidebar_page:
                st.session_state.page = sidebar_page
                st.session_state.page_navigation = sidebar_page
                st.rerun()

    st.divider()

    st.checkbox(
        tr("offline", language),
        key="offline_mode",
        help=tr("offline_note", language),
    )

    with st.expander(tr("account", language)):
        if st.session_state.username:
            account_label = st.session_state.display_name or st.session_state.username
            st.success(f"Signed in as {safe_text(account_label)}")
            if st.button(tr("logout", language), use_container_width=True):
                use_google_logout = st.session_state.auth_provider == "google"
                st.session_state.username = None
                st.session_state.display_name = None
                st.session_state.auth_provider = None
                if use_google_logout:
                    st.logout()
                else:
                    st.rerun()
        else:
            if st.button(
                "Sign in with Google",
                key="google_sign_in_button",
                use_container_width=True,
                disabled=not GOOGLE_LOGIN_CONFIGURED,
            ):
                st.login()
            if not GOOGLE_LOGIN_CONFIGURED:
                st.caption("Google sign-in needs OAuth details in Streamlit secrets. Setup steps are in the README.")

            if not DB_READY:
                st.warning("Local account storage could not be opened on this installation.")
            else:
                login_tab, register_tab = st.tabs([tr("sign_in", language), tr("register", language)])
                with login_tab:
                    login_name = st.text_input(tr("username", language), key="login_username")
                    login_password = st.text_input(tr("password", language), type="password", key="login_password")
                    if st.button(tr("sign_in", language), key="sign_in_button", use_container_width=True):
                        if authenticate(login_name, login_password):
                            st.session_state.username = login_name.strip()
                            st.session_state.display_name = login_name.strip()
                            st.session_state.auth_provider = "local"
                            st.rerun()
                        st.error("The username or password was not recognized.")
                with register_tab:
                    new_name = st.text_input(tr("username", language), key="register_username")
                    new_password = st.text_input(tr("password", language), type="password", key="register_password")
                    if st.button(tr("register", language), key="register_button", use_container_width=True):
                        created, message = create_user(new_name, new_password)
                        (st.success if created else st.error)(message)
            st.caption("A local database stores a salted password hash and saved activity. Hosted retention depends on the deployment's storage.")

    st.caption(
        "Reboot the Earth 2026\n\n"
        "Challenge 1 • Team 17"
    )


# ============================================================
# HERO
# ============================================================

hero_logo, hero_copy = st.columns([0.12, 0.88], vertical_alignment="center")
with hero_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=68)
with hero_copy:
    render_html(
        f"""
        <div class="hero">
            <h1>CropWise</h1>
            <p>{safe_text(tr("tagline", language))}<br>
            <span>{safe_text(tr("problem", language))}</span></p>
        </div>
        """
    )

feature_columns = st.columns(3)
feature_copy = [
    ("map", "map_intro"),
    ("planner", "planner_intro"),
    ("doctor", "doctor_intro"),
]
for column, (title_key, description_key) in zip(feature_columns, feature_copy):
    with column:
        st.markdown(f"#### {tr(title_key, language)}")
        st.caption(tr(description_key, language))
render_voice_button(". ".join(tr(key, language) for key in ("problem", "map_intro", "planner_intro", "doctor_intro")))


# ============================================================
# TOP NAVIGATION
# ============================================================

page = st.radio(
    tr("nav", language),
    PAGES,
    format_func=lambda page_key: tr(page_key, language),
    horizontal=True,
    label_visibility="collapsed",
    key="page_navigation",
)

if page != st.session_state.page:
    st.session_state.page = page


# ============================================================
# ANALYZE LAND
# ============================================================

if st.session_state.page == "map":

    st.subheader(tr("map_title", language))
    st.write(tr("map_intro", language))
    st.caption(tr("offline_note" if st.session_state.offline_mode else "online_note", language))

    col1, col2 = st.columns([2.1, 1])

    # ========================================================
    # MAP
    # ========================================================

    with col1:

        st.markdown("#### Select a location")

        field_map_location = (
            [st.session_state.lat, st.session_state.lon]
            if st.session_state.field_point_selected
            else [20.0, 0.0]
        )
        m = folium.Map(
            location=field_map_location,
            zoom_start=11 if st.session_state.field_point_selected else 2,
            tiles=None if st.session_state.offline_mode else "OpenStreetMap",
            control_scale=True,
        )
        add_location_controls(m, auto_start=st.session_state.location_auto_start)

        leaf_html = """
        <div style="
            position: relative;
            width: 48px;
            height: 58px;
            transform: translate(-12px, -50px);
        ">
            <div style="
                width: 42px;
                height: 42px;
                border-radius: 50%;
                background: white;
                border: 2px solid #43A047;
                box-shadow: 0 3px 10px rgba(0,0,0,0.25);
                display: flex;
                align-items: center;
                justify-content: center;
                position: absolute;
                top: 0;
                left: 0;
            ">
                <svg
                    width="25"
                    height="25"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <path
                        d="M20.7 3.3C14.1 3.5 8.8 5.1 5.7 8.2C2.8 11.1 3.1 15.7 4.2 18.1C6.6 19.2 11.2 19.5 14.1 16.6C17.2 13.5 18.8 8.2 20.7 3.3Z"
                        fill="#4CAF50"
                    />
                    <path
                        d="M4.5 19.5C7.2 15.6 10.4 12.5 15.5 9.5"
                        stroke="#1B5E20"
                        stroke-width="1.6"
                        stroke-linecap="round"
                    />
                </svg>
            </div>

            <div style="
                position: absolute;
                top: 38px;
                left: 17px;
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 10px solid #43A047;
            "></div>
        </div>
        """

        if st.session_state.field_point_selected:
            folium.Marker(
                [st.session_state.lat, st.session_state.lon],
                tooltip="Selected location",
                icon=folium.DivIcon(html=leaf_html),
            ).add_to(m)

        map_data = st_folium(
            m,
            height=470,
            width=None,
            returned_objects=["last_clicked"],
            key=f"cropwise_map_{st.session_state.field_map_generation}",
        )

        selected_coordinates = get_location_coordinates(map_data)
        if selected_coordinates and st.session_state.last_map_click != selected_coordinates:
            new_lat, new_lon = selected_coordinates
            st.session_state.last_map_click = selected_coordinates
            st.session_state.lat = new_lat
            st.session_state.lon = new_lon
            st.session_state.latitude_input = new_lat
            st.session_state.longitude_input = new_lon
            st.session_state.field_point_selected = True
            st.session_state.location_auto_start = False
            st.session_state.field_map_generation += 1
            if not st.session_state.planner_point_selected:
                st.session_state.planner_lat = new_lat
                st.session_state.planner_lon = new_lon
                st.session_state.planner_lat_input = new_lat
                st.session_state.planner_lon_input = new_lon
                st.session_state.planner_point_selected = True
            reset_analysis()
            st.rerun()

        if st.session_state.field_point_selected:
            st.caption(f"Selected point: {st.session_state.lat:.5f}, {st.session_state.lon:.5f}")
        else:
            st.caption("The map will request your location. You can also zoom in and select any point.")

        if st.button(
            "Clear selected point",
            key="clear_field_point",
            use_container_width=True,
            disabled=not st.session_state.field_point_selected,
        ):
            st.session_state.field_point_selected = False
            st.session_state.location_auto_start = False
            st.session_state.field_map_generation += 1
            st.session_state.last_map_click = None
            st.session_state.lat = DEFAULT_LAT
            st.session_state.lon = DEFAULT_LON
            st.session_state.latitude_input = DEFAULT_LAT
            st.session_state.longitude_input = DEFAULT_LON
            reset_analysis()
            st.rerun()

    # ========================================================
    # LOCATION CONTROLS
    # ========================================================

    with col2:

        st.markdown("#### Coordinates")

        latitude = st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            step=0.0001,
            format="%.5f",
            key="latitude_input",
            on_change=sync_field_coordinates,
        )

        longitude = st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            step=0.0001,
            format="%.5f",
            key="longitude_input",
            on_change=sync_field_coordinates,
        )

        st.session_state.lat = latitude
        st.session_state.lon = longitude

        st.caption(
            "Click anywhere on the map or enter coordinates manually. Browser location is requested on the field map and can be denied at any time."
        )

        with st.expander("Enter local climate and soil values", expanded=st.session_state.offline_mode):
            st.checkbox("Use values entered here when no saved point is available", key="manual_field_data")
            manual_temperature = st.number_input(
                tr("temperature", language), min_value=-40.0, max_value=60.0,
                value=None, step=0.5, key="manual_temperature",
            )
            manual_rainfall = st.number_input(
                tr("rainfall", language), min_value=0.0, max_value=20000.0,
                value=None, step=25.0, key="manual_rainfall",
            )
            manual_ph = st.number_input(
                tr("soil_ph", language), min_value=0.0, max_value=14.0,
                value=None, step=0.1, key="manual_ph",
            )

        reset = st.button(
            "Reset location",
            use_container_width=True,
        )

        if reset:

            st.session_state.lat = DEFAULT_LAT
            st.session_state.lon = DEFAULT_LON

            st.session_state.latitude_input = DEFAULT_LAT
            st.session_state.longitude_input = DEFAULT_LON

            st.session_state.last_map_click = None
            st.session_state.field_point_selected = False
            st.session_state.location_auto_start = False
            st.session_state.field_map_generation += 1

            reset_analysis()

            st.rerun()

    # ========================================================
    # CROP SELECTION
    # ========================================================

    st.divider()

    st.subheader(tr("select_crop", language))

    crop_names = sorted(CROP_THRESHOLDS.keys())

    crop_options = [
        "Select a crop..."
    ] + crop_names

    selected_crop = st.selectbox(
        "Crop",
        crop_options,
        index=0,
    )

    # ========================================================
    # NO CROP SELECTED
    # ========================================================

    if selected_crop == "Select a crop...":

        st.info(
            "Select a crop to view its preferred conditions and analyze this location."
        )

    # ========================================================
    # CROP SELECTED
    # ========================================================

    else:

        thresholds = CROP_THRESHOLDS[selected_crop]

        with st.expander("View preferred conditions"):

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "Temperature",
                    f"{thresholds['temp_c'][0]}–"
                    f"{thresholds['temp_c'][1]} °C",
                )

            with c2:
                st.metric(
                    "Rainfall",
                    f"{thresholds['rain_mm'][0]:,}–"
                    f"{thresholds['rain_mm'][1]:,} mm",
                )

            with c3:
                st.metric(
                    "Soil pH",
                    f"{thresholds['ph'][0]}–"
                    f"{thresholds['ph'][1]}",
                )

        st.caption(
            thresholds.get(
                "notes",
                "Preferred growing conditions.",
            )
        )

        # ====================================================
        # ANALYZE BUTTON
        # ====================================================

        if st.button(
            tr("analyze", language),
            type="primary",
            use_container_width=True,
            disabled=not st.session_state.field_point_selected,
        ):

            with st.spinner(
                "Fetching climate and soil data..."
            ):

                try:

                    manual = {
                        "enabled": st.session_state.get("manual_field_data", False),
                        "temp_c": st.session_state.get("manual_temperature"),
                        "rain_mm_year": st.session_state.get("manual_rainfall"),
                        "ph": st.session_state.get("manual_ph"),
                    }
                    climate, soil, data_mode = fetch_field_data(
                        st.session_state.lat,
                        st.session_state.lon,
                        offline=st.session_state.offline_mode,
                        manual=manual,
                    )

                    verdict, score, reasons = evaluate(
                        climate,
                        soil,
                        thresholds,
                    )

                    factors = get_factor_scores(
                        climate,
                        soil,
                        thresholds,
                    )

                    st.session_state.analysis = {
                        "crop": selected_crop,
                        "climate": climate,
                        "soil": soil,
                        "verdict": verdict,
                        "score": score,
                        "reasons": reasons,
                        "factors": factors,
                        "data_mode": data_mode,
                    }
                    save_activity(
                        "field suitability",
                        latitude=st.session_state.lat,
                        longitude=st.session_state.lon,
                        crop=selected_crop,
                        outcome=verdict,
                        score=score,
                        details={"data_mode": data_mode},
                    )

                except Exception:

                    st.error(
                        "We couldn't assess this location. Check the coordinates and "
                        "field values, then try again. If you are offline, use saved "
                        "data or enter local values."
                    )

    # ========================================================
    # RESULTS
    # ========================================================

    analysis = st.session_state.analysis

    if analysis:

        st.divider()

        st.subheader(
            f"Results for {analysis['crop']}"
        )

        verdict = analysis["verdict"]
        score = analysis["score"]

        with st.container(border=True):
            if verdict == "Suitable":
                st.success(verdict)
            elif verdict == "Not suitable":
                st.error(verdict)
            else:
                st.warning(verdict)
            st.metric("Suitability score", f"{score_percent(score)}%")

        st.subheader("Plain-language summary")
        st.write(
            field_result_summary(
                analysis["crop"],
                verdict,
                score,
                analysis.get("factors"),
            )
        )

        climate = analysis["climate"]
        soil = analysis["soil"]

        c1, c2, c3 = st.columns(3)
        temp = climate.get("temp_c")
        rain = climate.get("rain_mm_year")
        ph = soil.get("ph")
        c1.metric("Average temperature", f"{temp:.1f} °C" if temp is not None else "Unavailable")
        c2.metric("Annual rainfall", f"{rain:,.0f} mm" if rain is not None else "Unavailable")
        c3.metric("Soil pH", f"{ph:.2f}" if ph is not None else "Unavailable")

        terrain1, terrain2 = st.columns(2)
        with terrain1:
            elevation = soil.get("elevation_m")
            st.metric("Terrain elevation", f"{elevation:.0f} m" if elevation is not None else "Unavailable")
        with terrain2:
            slope = soil.get("slope_pct")
            st.metric("Nearby slope estimate", f"{slope:.1f}%" if slope is not None else "Unavailable")
        st.caption("Terrain uses a 90 m digital elevation model. The slope value is a rough estimate from nearby points, not a field survey.")
        st.caption(f"Data source: {analysis.get('data_mode', 'unknown')} • Soil pH and terrain are approximate screening signals.")

        st.markdown("")

        st.subheader("Factor breakdown")

        for factor_name, factor in analysis["factors"].items():

            value = factor["value"]
            low = factor["low"]
            high = factor["high"]
            score_value = factor["score"]
            unit = factor["unit"]

            status = factor_status(score_value)

            with st.container(border=True):
                factor_col, score_col = st.columns([3, 1])
                with factor_col:
                    st.markdown(f"**{factor_name}**")
                    st.caption(
                        f"Observed: {format_factor_value(value, unit)}  ·  "
                        f"Preferred: {low:g}–{high:g} {unit}  ·  {status}"
                    )
                with score_col:
                    st.metric("Screening fit", f"{score_percent(score_value)}%")
                if score_value is not None:
                    st.progress(max(0.0, min(1.0, float(score_value))))

        st.subheader("Why this result")

        for reason in analysis["reasons"]:
            st.write(f"- {reason}")

        if climate.get("error"):
            st.warning(climate["error"])

        if soil.get("error"):
            st.warning(soil["error"])
        if soil.get("terrain_error"):
            st.warning(soil["terrain_error"])
        render_voice_button(tr("screening_warning", language))


# ============================================================
# CROP FINDER
# ============================================================

elif st.session_state.page == "planner":

    st.subheader(tr("planner_title", language))

    st.write(tr("planner_intro", language))
    st.caption("Start with a field assessment to compare suitable crops, then build a companion plan from the screened pairings.")

    st.markdown("#### Select a point on the planting map")
    planner_map_center = (
        [st.session_state.planner_lat, st.session_state.planner_lon]
        if st.session_state.planner_point_selected
        else [20.0, 0.0]
    )
    planner_map = folium.Map(
        location=planner_map_center,
        zoom_start=11 if st.session_state.planner_point_selected else 2,
        tiles=None if st.session_state.offline_mode else "OpenStreetMap",
        control_scale=True,
    )
    add_location_controls(planner_map)
    if st.session_state.planner_point_selected:
        folium.Marker(
            [st.session_state.planner_lat, st.session_state.planner_lon],
            tooltip="Selected planting point",
        ).add_to(planner_map)

    planner_map_data = st_folium(
        planner_map,
        height=430,
        width=None,
        returned_objects=["last_clicked"],
        key=f"cropwise_planner_map_{st.session_state.planner_map_generation}",
    )
    planner_coordinates = get_location_coordinates(planner_map_data)
    if planner_coordinates and st.session_state.planner_last_map_click != planner_coordinates:
        st.session_state.planner_last_map_click = planner_coordinates
        st.session_state.planner_lat, st.session_state.planner_lon = planner_coordinates
        st.session_state.planner_lat_input = planner_coordinates[0]
        st.session_state.planner_lon_input = planner_coordinates[1]
        st.session_state.planner_point_selected = True
        st.session_state.planner_map_generation += 1
        st.session_state.crop_results = None
        st.rerun()

    if st.session_state.planner_point_selected:
        st.caption(
            f"Selected point: {st.session_state.planner_lat:.5f}, "
            f"{st.session_state.planner_lon:.5f}"
        )
    else:
        st.caption("Zoom and click the map to choose a planting location, or use your device location control.")

    if st.button(
        "Clear selected point",
        key="clear_planner_point",
        use_container_width=True,
        disabled=not st.session_state.planner_point_selected,
    ):
        st.session_state.planner_point_selected = False
        st.session_state.planner_map_generation += 1
        st.session_state.planner_last_map_click = None
        st.session_state.planner_lat = DEFAULT_LAT
        st.session_state.planner_lon = DEFAULT_LON
        st.session_state.planner_lat_input = DEFAULT_LAT
        st.session_state.planner_lon_input = DEFAULT_LON
        st.session_state.crop_results = None
        st.rerun()

    with st.expander("Enter planting coordinates manually"):
        c1, c2 = st.columns(2)
        with c1:
            finder_lat = st.number_input(
                "Latitude", min_value=-90.0, max_value=90.0, step=0.0001,
                format="%.5f", value=float(st.session_state.planner_lat), key="planner_lat_input",
                on_change=sync_planner_coordinates,
            )
        with c2:
            finder_lon = st.number_input(
                "Longitude", min_value=-180.0, max_value=180.0, step=0.0001,
                format="%.5f", value=float(st.session_state.planner_lon), key="planner_lon_input",
                on_change=sync_planner_coordinates,
            )

    if st.button(
        tr("find_crops", language),
        type="primary",
        use_container_width=True,
        disabled=not st.session_state.planner_point_selected,
    ):

        with st.spinner(
            "Analyzing the location..."
        ):

            try:

                manual = {
                    "enabled": st.session_state.get("manual_field_data", False),
                    "temp_c": st.session_state.get("manual_temperature"),
                    "rain_mm_year": st.session_state.get("manual_rainfall"),
                    "ph": st.session_state.get("manual_ph"),
                }
                climate, soil, data_mode = fetch_field_data(
                    finder_lat,
                    finder_lon,
                    offline=st.session_state.offline_mode,
                    manual=manual,
                )

                results = []

                for crop_name, thresholds in CROP_THRESHOLDS.items():

                    verdict, score, reasons = evaluate(
                        climate,
                        soil,
                        thresholds,
                    )

                    results.append(
                        {
                            "crop": crop_name,
                            "verdict": verdict,
                            "score": score,
                            "reasons": reasons,
                        }
                    )

                results.sort(
                    key=lambda item: (
                        item["score"]
                        if item["score"] is not None
                        else -1
                    ),
                    reverse=True,
                )

                st.session_state.crop_results = {
                    "climate": climate,
                    "soil": soil,
                    "results": results,
                    "latitude": finder_lat,
                    "longitude": finder_lon,
                    "data_mode": data_mode,
                }
                top_result = results[0] if results else {}
                save_activity(
                    "crop finder",
                    latitude=finder_lat,
                    longitude=finder_lon,
                    crop=top_result.get("crop"),
                    outcome=top_result.get("verdict"),
                    score=top_result.get("score"),
                    details={"data_mode": data_mode},
                )

            except Exception:

                st.error(
                    "We couldn't assess this location. Check the coordinates and "
                    "field values, then try again. If you are offline, use saved "
                    "data or enter local values."
                )

    finder = st.session_state.get("crop_results")

    if isinstance(finder, dict):

        results = finder.get("results", [])

        if results:

            st.divider()

            best_result = results[0]
            st.subheader("Plain-language summary")
            st.write(
                field_result_summary(
                    best_result["crop"],
                    best_result["verdict"],
                    best_result["score"],
                )
            )
            st.subheader("Matching crops")

            for result in results[:12]:

                score = score_percent(
                    result["score"]
                )

                with st.container(border=True):
                    crop_col, score_col = st.columns([3, 1])
                    with crop_col:
                        st.markdown(f"**{result['crop']}**")
                        st.caption(result["verdict"])
                    with score_col:
                        st.metric("Screening fit", f"{score}%")
                    if result.get("score") is not None:
                        st.progress(max(0.0, min(1.0, float(result["score"]))))

            st.divider()
            st.subheader("Companion planting plan")
            main_crop = st.selectbox(
                "Choose the main crop for the companion plan",
                sorted(CROP_THRESHOLDS.keys()),
                index=(
                    sorted(CROP_THRESHOLDS.keys()).index(st.session_state.analysis["crop"])
                    if st.session_state.get("analysis")
                    and st.session_state.analysis.get("crop") in CROP_THRESHOLDS
                    else 0
                ),
                key="planner_main_crop",
            )
            companion_options = recommendations(main_crop, finder["climate"], finder["soil"])
            if companion_options:
                for option in companion_options:
                    percent = score_percent(option["score"])
                    st.markdown(f"### {safe_text(option['crop'])} · {percent}% site screen")
                    st.write(option["why"])
                    st.caption(f"Management: {option['manage']}")
                    st.caption(f"Site fit: {option['verdict']}. Review local spacing and planting dates before using this pairing.")
                    st.markdown(f"[Reference: extension guidance]({option['source']})")
            else:
                st.info("This first edition includes sourced examples for maize, green bean, pumpkin, cabbage, broccoli, carrot, and tomato. More locally reviewed pairings can be added.")
            st.warning(tr("screening_warning", language))
            render_voice_button(tr("planner_intro", language) + " " + tr("screening_warning", language))


# ============================================================
# DISEASE AI
# ============================================================

elif st.session_state.page == "doctor":

    st.subheader(tr("doctor_title", language))

    st.write(tr("doctor_intro", language))
    st.warning(tr("screening_warning", language))

    camera_photo = st.camera_input(tr("camera_photo", language))
    uploaded_file = camera_photo or st.file_uploader(
        tr("upload", language),
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp",
        ],
    )

    if uploaded_file:

        try:

            image = Image.open(uploaded_file)

            st.image(
                image,
                caption="Uploaded image",
                use_container_width=True,
            )

            if st.button(
                tr("analyze_leaf", language),
                type="primary",
                use_container_width=True,
            ):

                with st.spinner(
                    "Loading the disease AI..."
                ):

                    try:

                        model = cached_disease_model(st.session_state.offline_mode)

                        predictions = predict(
                            image,
                            model,
                            top_k=3,
                        )

                        st.session_state.disease_results = predictions
                        best = predictions[0] if predictions else {}
                        save_activity(
                            "leaf screening",
                            crop=best.get("plant"),
                            outcome=best.get("disease"),
                            score=best.get("confidence"),
                            details={"image_saved": False},
                        )

                    except Exception:

                        if st.session_state.offline_mode:
                            st.error("The model is not cached for offline use yet. Connect once, run a screening, and then retry offline.")
                        else:
                            st.error(
                                "Leaf screening couldn't run. Try again later. If you "
                                "are offline, connect once to download the model, then retry."
                            )

        except Exception:

            st.error(
                "We couldn't open that image. Choose a clear JPG, PNG, or WebP leaf photo and try again."
            )

    disease_results = st.session_state.get(
        "disease_results"
    )

    if disease_results:

        st.divider()

        st.subheader("Leaf screening result")

        best = disease_results[0]

        disease = best["disease"]
        plant = best["plant"]
        confidence = best["confidence"]

        st.subheader("Plain-language result")
        st.write(leaf_result_summary(plant, disease, confidence))

        st.metric(
            "Model match score",
            f"{confidence * 100:.1f}%",
        )
        st.caption("The model score is not a measure of diagnostic certainty.")

        st.subheader(tr("treatment_title", language))
        st.info(first_steps(disease))
        st.caption("The image is used for this screening and is not written to the history database. Hosted deployments still receive the upload for local inference.")
        st.caption("General first steps follow [University of Minnesota Extension disease-prevention guidance](https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/yard-and-garden-problems/preventing-plant-diseases-in-the-garden). See [UC IPM tomato mosaic guidance](https://ipm.ucanr.edu/agriculture/tomato/tobacco-mosaic/) and [Oregon State Extension apple scab guidance](https://extension.oregonstate.edu/es/node/123546/printable/print) for those examples. Local diagnosis and treatment rules vary.")
        render_voice_button(f"Possible condition: {disease}. {first_steps(disease)} {tr('screening_warning', language)}")

        if len(disease_results) > 1:

            with st.expander(
                "Other possibilities"
            ):

                for result in disease_results[1:]:

                    st.write(
                        f"• {result['plant']} — "
                        f"{result['disease']} "
                        f"({result['confidence'] * 100:.1f}%)"
                    )


# ============================================================
# ABOUT
# ============================================================

elif st.session_state.page == "history":

    st.subheader(tr("history_title", language))
    st.write(tr("history_intro", language))
    if not st.session_state.username:
        st.info("Sign in from the sidebar to view saved activity. Guest activity remains only in the current session.")
    elif not DB_READY:
        st.error("Local history storage is unavailable on this installation.")
    else:
        history_rows = get_history(st.session_state.username)
        if not history_rows:
            st.info(tr("no_history", language))
        else:
            for entry in history_rows:
                title = entry.get("entry_type", "Activity").title()
                st.markdown(f"### {title}")
                details = [entry.get("created_at", "")]
                if entry.get("crop"):
                    details.append(str(entry["crop"]))
                if entry.get("outcome"):
                    details.append(str(entry["outcome"]))
                if entry.get("score") is not None:
                    details.append(f"{score_percent(entry['score'])}%")
                if entry.get("latitude") is not None and entry.get("longitude") is not None:
                    details.append(f"{entry['latitude']:.5f}, {entry['longitude']:.5f}")
                st.caption(" · ".join(details))
                st.divider()

elif st.session_state.page == "share":

    st.subheader(tr("share_title", language))
    st.write("Create a QR code for a public CropWise deployment. QR generation happens locally in this app.")
    public_url = st.text_input(
        tr("public_url", language),
        value=os.environ.get("APP_PUBLIC_URL", ""),
        placeholder="https://your-app.streamlit.app",
    ).strip()
    if public_url:
        from urllib.parse import urlparse

        parsed_url = urlparse(public_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            st.error("Enter a complete HTTPS URL for the deployed app.")
        else:
            qr_image = qrcode.make(public_url)
            qr_buffer = io.BytesIO()
            qr_image.save(qr_buffer, format="PNG")
            qr_bytes = qr_buffer.getvalue()
            st.image(qr_bytes, caption=tr("scan_qr", language), width=240)
            st.download_button(tr("download_qr", language), qr_bytes, file_name="cropwise-app-qr.png", mime="image/png")
    else:
        st.info(tr("qr_missing", language))

elif st.session_state.page == "impact":

    st.subheader(tr("impact_title", language))

    # --------------------------------------------------------
    # WHAT IS CROPWISE?
    # --------------------------------------------------------

    st.markdown(
        '<div class="about-box">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="about-title">What is CropWise?</div>',
        unsafe_allow_html=True,
    )

    st.write(
        "CropWise addresses a practical knowledge gap: farmers need clear field information before choosing a crop or treatment. It combines coordinate-based climate and soil signals with a transparent crop screen, companion planting prompts, and a low-cost first response to leaf symptoms."
    )

    st.write(
        "The aim is to support better use of land and help farmers compare options that may improve crop production with lower cost and environmental pressure. The app does not promise a specific yield."
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(f"### {tr('sdg_title', language)}")
    sdg_cols = st.columns(4)
    for column, number, title, description in zip(
        sdg_cols,
        ("2", "12", "13", "15"),
        ("Zero Hunger", "Responsible Consumption and Production", "Climate Action", "Life on Land"),
        (
            "Supports crop choices and food production decisions.",
            "Promotes efficient use of soil, water, and inputs.",
            "Uses climate information to guide field planning.",
            "Encourages soil care and diverse planting systems.",
        ),
    ):
        with column:
            st.metric(f"UN SDG {number}", title)
            st.caption(description)
            st.markdown(f"[Official UN Goal {number}](https://sdgs.un.org/goals/goal{number})")
    st.caption(tr("sdg_note", language))

    st.markdown(f"### {tr('privacy_title', language)}")
    st.info(tr("privacy_body", language))

    st.markdown(f"### {tr('terms_title', language)}")
    st.info(tr("terms_body", language))

    st.markdown("### Free and offline use")
    st.write(tr("offline_detail", language))
    st.caption(tr("language_note", language))
    render_voice_button(tr("impact_title", language) + ". " + tr("sdg_title", language))

    # --------------------------------------------------------
    # DATA SOURCES
    # --------------------------------------------------------

    st.markdown(
        '<div class="about-box">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="about-title">Data sources</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        - **NASA POWER** — free public climate data (online refresh)
        - **SoilGrids / ISRIC** — soil pH estimates (online refresh)
        - **OpenStreetMap** — online map tiles
        - **Open-Meteo Elevation API / Copernicus GLO-90** — terrain elevation and rough slope estimate; attribution required
        - **PlantVillage** — source dataset for the local leaf image model
        - **Hugging Face** — model files; download once before offline use
        - **Free to run without paid API keys**; hosting and device costs depend on deployment
        """
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # HOW SUITABILITY IS CALCULATED
    # --------------------------------------------------------

    st.markdown(
        '<div class="about-box">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="about-title">How suitability is calculated</div>',
        unsafe_allow_html=True,
    )

    st.write(
        "CropWise compares the following environmental factors:"
    )

    st.markdown(
        """
        - **Average temperature**
        - **Annual rainfall**
        - **Soil pH**
        """
    )

    st.write(
        "The available factors are combined into a transparent screening score. It does not account for every farm variable, including local varieties, irrigation, slope, soil depth, pests, market access, or planting date."
    )

    st.caption("Long-term climate estimates are regional baselines, not farm sensor readings or a true microclimate model. Soil pH and terrain estimates are not a laboratory test or field survey.")

    st.info(
        "The result is a screening indicator, not a guaranteed "
        "prediction of crop yield."
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # HOW THE APP WORKS
    # --------------------------------------------------------

    st.markdown(
        '<div class="about-box">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="about-title">How CropWise works</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        **1. Map the field** — choose a point and review available climate and soil estimates.

        **2. Compare crops** — use the suitability screen and see which factors affected the score.

        **3. Plan companion crops** — review sourced pairings and check each companion crop against the same field conditions.

        **4. Check leaf symptoms** — use a local image model for an initial screen and follow low-cost hygiene steps.

        **5. Save a history** — sign in to keep your results in the local SQLite database on this installation.
        """
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "CropWise • Reboot the Earth 2026 • "
    "Challenge 1 • Team 17"
)
