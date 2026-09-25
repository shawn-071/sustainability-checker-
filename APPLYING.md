# CropWise website update bundle

This is a source overlay for NakulMarar/challenge1-suitability-checker.

## Apply it

1. Extract the archive into the repository root and replace files when prompted.
2. Review the updated README.md for setup, data, privacy, and offline limitations.
3. Run the app locally and review it before deploying.

The overlay includes updates to the app, requirements, and README plus new support modules for local account/history storage, six-language core UI, companion planting, and conservative plant-health guidance. .gitignore excludes the local SQLite database and secrets.

The app is free of paid API keys. It is not fully offline on first use: live datasets/map tiles need a connection, and the disease model and location data must be cached or prepared first. QR generation needs the public deployment URL. Local SQLite account storage is a prototype and hosted persistence must be configured separately.

The GitHub connection for the linked repository is read-only: branch creation returned HTTP 403. These files are ready for a branch or fork once the account has write access.
