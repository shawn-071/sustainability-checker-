# CropWise

CropWise helps farmers review a field, compare crop options, plan a small set of companion crops, and run a first-pass leaf health screen. The project addresses the knowledge gap behind poor land-use decisions with clear, low-cost information.

Built for Reboot the Earth 2026, Challenge 1, Team 17.

## What the app includes

- Coordinate-based field map with climate, soil pH, elevation, and a rough nearby slope estimate.
- Interactive world maps for field assessment and planting plans, with optional browser location at startup and manual point clearing.
- Crop suitability screening with visible factor scores and assumptions.
- A starter companion-planting planner with references and site-fit checks.
- Leaf photo screening with general low-cost first steps.
- Optional account registration, salted password hashes, local activity history, and cached point data.
- Voice readout using the browser’s speech support.
- Core navigation and guidance in Arabic, Chinese, English, French, Russian, and Spanish.
- Local QR-code generation for a configured public deployment URL.
- Draft privacy and terms copy, plus relevant UN Sustainable Development Goals.

The app is a decision-support prototype. It does not predict yield, diagnose plant disease, or replace local agricultural advice.

## Run locally

1. Install Python 3.10 or newer.
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   streamlit run app.py
   ```

The first online disease screening downloads the open-source model. Once the model is present in the local Hugging Face cache, Offline mode can use it without downloading files.

## Configuration

- `APP_PUBLIC_URL`: optional HTTPS URL used to prefill the Share app page before generating a QR code.
- `CROPWISE_DB_PATH`: optional path for the SQLite database. By default, the app creates `cropwise.db` beside `app.py`.
- Google sign-in uses Streamlit's OpenID Connect support. It remains inactive until OAuth credentials are configured in Streamlit secrets.

### Configure Google sign-in

1. Create a Web application OAuth client in Google Cloud.
2. Add the exact app callback URL to its authorized redirect URIs. For local development, use `http://localhost:8501/oauth2callback`; for Streamlit Community Cloud, use `https://YOUR-APP.streamlit.app/oauth2callback`.
3. Add the following values to the app's Streamlit secrets, replacing each placeholder. Do not commit a real `secrets.toml` or client secret to the repository.

   ```toml
   [auth]
   redirect_uri = "https://YOUR-APP.streamlit.app/oauth2callback"
   cookie_secret = "a-long-random-secret"
   client_id = "YOUR_GOOGLE_CLIENT_ID"
   client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
   server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
   ```

   In Streamlit Community Cloud, enter this under the app's **Settings → Secrets**. For local use, save it as `.streamlit/secrets.toml`. The Google redirect URI and `redirect_uri` value must match exactly. See the [Streamlit Google authentication guide](https://docs.streamlit.io/develop/tutorials/authentication/google).

The database stores usernames, salted password hashes, saved history, and cached field values. Uploaded leaf images are not written to the database. A hosted installation needs persistent, access-controlled storage for durable account history. Treat the account flow as a prototype until production security, backups, password recovery, and retention policies are reviewed.

## Free data and connectivity

The app needs no paid API key. It uses:

- [NASA POWER](https://power.larc.nasa.gov/) for long-term climate values.
- [SoilGrids / ISRIC](https://soilgrids.org/) for soil pH estimates.
- [OpenStreetMap](https://www.openstreetmap.org/copyright) map tiles.
- [Open-Meteo Elevation API](https://open-meteo.com/en/docs/elevation-api) using the Copernicus GLO-90 elevation model.
- [PlantVillage](https://huggingface.co/datasets) labels and a MobileNetV2 model hosted on Hugging Face.

Live map tiles and climate, soil, and elevation refreshes require an internet connection. Offline mode uses saved values for an exact coordinate or values entered by the user. The offline map has no basemap. A fully disconnected first-time setup requires preloading the model and any field data the user needs. Open-Meteo and each data provider’s terms and attribution requirements apply; confirm them before commercial deployment.

The field map asks the browser for device location when the app opens. The user can deny permission and select a map point or enter coordinates instead. Browser geolocation requires a secure HTTPS page when deployed. The planting map starts from the field point when one has been selected.

## Language coverage

The language selector offers all six official UN languages. Navigation and core guidance have translations. Crop names and some reference material remain in their published language in this prototype.

## Companion-planting references

The starter pairings draw on [Oregon State University Extension’s Companion Planting guide](https://extension.oregonstate.edu/imported-publication/companion-planting) and [FAO guidance on intercropping](https://www.fao.org/4/a0218e/A0218E16.htm). Pairings are prompts to investigate locally; spacing, planting dates, varieties, water, labor, and local pest pressure affect results.

Crop screening ranges are broad starting points, not cultivar-specific recommendations or yield forecasts. The expanded crop list should be checked against local agricultural guidance. [FAO EcoCrop](https://ecocrop.apps.fao.org/ecocrop/srv/en/home) provides crop-specific climate and soil requirements for further review.

## Privacy and terms

The in-app privacy and terms sections are drafts for project review, not legal advice. When browser location is allowed, the device provides coordinates to the field map; coordinates go to the named public data providers when online lookups are enabled. On a hosted deployment, leaf photos reach the app server for inference but the app does not persist them. Review hosting, database access, and local data-protection requirements before inviting public users.
