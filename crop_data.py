"""
crop_data.py
------------
Static reference data for crop suitability and disease treatments.
"""

CROP_THRESHOLDS = {

    # =========================
    # FRUITS
    # =========================

    "Apple": {
        "temp_c": (10, 24),
        "rain_mm": (500, 1000),
        "ph": (5.5, 7.0),
        "notes": "Prefers cool to mild climates and well-drained soil. Many varieties require winter chilling."
    },

    "Banana": {
        "temp_c": (20, 35),
        "rain_mm": (1200, 2500),
        "ph": (5.5, 7.5),
        "notes": "Tropical crop requiring warm temperatures, abundant moisture, and good drainage."
    },

    "Grapes": {
        "temp_c": (15, 30),
        "rain_mm": (500, 900),
        "ph": (5.5, 7.5),
        "notes": "Performs well in warm climates with good sunlight and well-drained soil."
    },

    "Mango": {
        "temp_c": (24, 35),
        "rain_mm": (750, 2500),
        "ph": (5.5, 7.5),
        "notes": "Warm-season fruit tree that performs best in tropical and subtropical climates."
    },

    "Orange": {
        "temp_c": (15, 30),
        "rain_mm": (1000, 1500),
        "ph": (5.5, 7.5),
        "notes": "Prefers warm subtropical conditions, adequate moisture, and well-drained soil."
    },

    "Papaya": {
        "temp_c": (21, 33),
        "rain_mm": (1000, 2000),
        "ph": (5.5, 7.0),
        "notes": "Tropical crop that requires warmth, sunlight, moisture, and good drainage."
    },

    "Pineapple": {
        "temp_c": (18, 32),
        "rain_mm": (1000, 1500),
        "ph": (4.5, 6.5),
        "notes": "Tropical fruit that prefers acidic, well-drained soils."
    },

    "Pomegranate": {
        "temp_c": (15, 35),
        "rain_mm": (300, 800),
        "ph": (5.5, 7.5),
        "notes": "Drought-tolerant fruit crop that performs well in warm, relatively dry climates."
    },

    "Strawberry": {
        "temp_c": (10, 25),
        "rain_mm": (500, 800),
        "ph": (5.5, 6.5),
        "notes": "Prefers cool conditions and slightly acidic, well-drained soil."
    },

    "Watermelon": {
        "temp_c": (22, 35),
        "rain_mm": (400, 600),
        "ph": (6.0, 6.8),
        "notes": "Heat-loving crop that needs warm weather and well-drained soil."
    },

    "Coconut": {
        "temp_c": (21, 32),
        "rain_mm": (1500, 2500),
        "ph": (5.0, 8.0),
        "notes": "Tropical palm requiring warm temperatures and abundant moisture."
    },


    # =========================
    # CEREALS / GRAINS
    # =========================

    "Barley": {
        "temp_c": (10, 28),
        "rain_mm": (250, 800),
        "ph": (6.0, 8.5),
        "notes": "More heat-, drought-, and salt-tolerant than wheat."
    },

    "Corn (Maize)": {
        "temp_c": (18, 32),
        "rain_mm": (500, 800),
        "ph": (5.8, 7.0),
        "notes": "Needs warm temperatures and steady water, especially during flowering."
    },

    "Millet": {
        "temp_c": (20, 35),
        "rain_mm": (300, 700),
        "ph": (5.5, 7.5),
        "notes": "Warm-season cereal known for relatively strong drought tolerance."
    },

    "Oats": {
        "temp_c": (10, 24),
        "rain_mm": (500, 1000),
        "ph": (5.0, 7.5),
        "notes": "Cool-season cereal that performs best with adequate moisture."
    },

    "Rice": {
        "temp_c": (20, 35),
        "rain_mm": (1000, 2500),
        "ph": (5.0, 7.5),
        "notes": "Warm-season crop with high water requirements. Irrigated systems can reduce dependence on rainfall."
    },

    "Rye": {
        "temp_c": (5, 24),
        "rain_mm": (400, 800),
        "ph": (5.0, 7.0),
        "notes": "Cool-season cereal that tolerates poorer soils and colder conditions."
    },

    "Sorghum": {
        "temp_c": (20, 35),
        "rain_mm": (400, 800),
        "ph": (5.5, 8.0),
        "notes": "Heat- and drought-tolerant cereal suitable for warm, relatively dry regions."
    },

    "Wheat": {
        "temp_c": (10, 26),
        "rain_mm": (300, 900),
        "ph": (6.0, 7.5),
        "notes": "Cool-season crop. High heat during grain filling can reduce yield."
    },


    # =========================
    # VEGETABLES
    # =========================

    "Artichoke": {
        "temp_c": (13, 24),
        "rain_mm": (500, 1000),
        "ph": (6.0, 7.5),
        "notes": "Prefers mild temperatures and fertile, well-drained soil."
    },

    "Beetroot": {
        "temp_c": (10, 24),
        "rain_mm": (400, 800),
        "ph": (6.0, 7.5),
        "notes": "Cool-season root crop that prefers loose, well-drained soil."
    },

    "Bell Pepper": {
        "temp_c": (18, 30),
        "rain_mm": (600, 1200),
        "ph": (5.5, 6.8),
        "notes": "Warm-season crop that is sensitive to frost and prolonged extreme heat."
    },

    "Broccoli": {
        "temp_c": (10, 24),
        "rain_mm": (500, 900),
        "ph": (6.0, 7.0),
        "notes": "Cool-season vegetable that performs poorly under prolonged high temperatures."
    },

    "Cabbage": {
        "temp_c": (10, 24),
        "rain_mm": (400, 800),
        "ph": (6.0, 7.5),
        "notes": "Cool-season vegetable requiring consistent moisture."
    },

    "Carrot": {
        "temp_c": (10, 24),
        "rain_mm": (350, 700),
        "ph": (5.5, 7.0),
        "notes": "Prefers cool temperatures and loose, stone-free soil for good root development."
    },

    "Cauliflower": {
        "temp_c": (10, 24),
        "rain_mm": (500, 900),
        "ph": (6.0, 7.0),
        "notes": "Cool-season crop that is sensitive to excessive heat."
    },

    "Cucumber": {
        "temp_c": (18, 32),
        "rain_mm": (400, 800),
        "ph": (5.5, 7.0),
        "notes": "High water demand. Greenhouse and hydroponic systems work well in hot climates."
    },

    "Eggplant": {
        "temp_c": (20, 32),
        "rain_mm": (600, 1000),
        "ph": (5.5, 6.8),
        "notes": "Heat-tolerant vegetable that is sensitive to cold conditions."
    },

    "Garlic": {
        "temp_c": (10, 25),
        "rain_mm": (400, 700),
        "ph": (6.0, 7.0),
        "notes": "Prefers well-drained soil and relatively cool conditions during bulb development."
    },

    "Lettuce": {
        "temp_c": (7, 24),
        "rain_mm": (300, 500),
        "ph": (6.0, 6.8),
        "notes": "Cool-season and heat-sensitive crop."
    },

    "Okra": {
        "temp_c": (21, 35),
        "rain_mm": (700, 1200),
        "ph": (6.0, 7.5),
        "notes": "Warm-season vegetable that performs well in hot climates."
    },

    "Onion": {
        "temp_c": (13, 24),
        "rain_mm": (350, 550),
        "ph": (6.0, 7.0),
        "notes": "Bulbing depends on temperature, day length, and adequate moisture."
    },

    "Peas": {
        "temp_c": (10, 24),
        "rain_mm": (400, 800),
        "ph": (6.0, 7.5),
        "notes": "Cool-season legume that struggles under prolonged high temperatures."
    },

    "Potato": {
        "temp_c": (10, 25),
        "rain_mm": (500, 700),
        "ph": (4.8, 6.5),
        "notes": "Prefers cooler conditions and slightly acidic soil."
    },

    "Pumpkin": {
        "temp_c": (18, 32),
        "rain_mm": (500, 1000),
        "ph": (5.5, 7.5),
        "notes": "Warm-season crop requiring adequate moisture and good drainage."
    },

    "Radish": {
        "temp_c": (10, 24),
        "rain_mm": (350, 600),
        "ph": (5.5, 7.0),
        "notes": "Fast-growing cool-season root vegetable."
    },

    "Spinach": {
        "temp_c": (7, 24),
        "rain_mm": (400, 800),
        "ph": (6.0, 7.5),
        "notes": "Cool-season leafy vegetable that can bolt in hot conditions."
    },

    "Sweet Potato": {
        "temp_c": (21, 32),
        "rain_mm": (750, 1500),
        "ph": (5.5, 6.8),
        "notes": "Warm-season crop that requires a long frost-free growing period."
    },

    "Tomato": {
        "temp_c": (15, 32),
        "rain_mm": (400, 800),
        "ph": (5.8, 7.0),
        "notes": "Sensitive to frost and extreme heat above roughly 35C. Needs steady irrigation."
    },

    "Turnip": {
        "temp_c": (10, 24),
        "rain_mm": (350, 700),
        "ph": (5.5, 7.0),
        "notes": "Cool-season root vegetable that prefers loose, well-drained soil."
    },


    # =========================
    # LEGUMES
    # =========================

    "Alfalfa": {
        "temp_c": (15, 32),
        "rain_mm": (500, 900),
        "ph": (6.5, 7.5),
        "notes": "Deep-rooted forage crop that becomes relatively drought-tolerant once established."
    },

    "Chickpea": {
        "temp_c": (15, 30),
        "rain_mm": (300, 700),
        "ph": (6.0, 8.0),
        "notes": "Relatively drought-tolerant legume suited to dry and semi-arid regions."
    },

    "Kidney Bean": {
        "temp_c": (18, 30),
        "rain_mm": (500, 1000),
        "ph": (6.0, 7.5),
        "notes": "Warm-season legume requiring adequate moisture."
    },

    "Lentil": {
        "temp_c": (10, 27),
        "rain_mm": (300, 600),
        "ph": (6.0, 8.0),
        "notes": "Cool-season legume that can perform well under relatively dry conditions."
    },

    "Peanut": {
        "temp_c": (21, 32),
        "rain_mm": (500, 1000),
        "ph": (5.5, 7.0),
        "notes": "Warm-season crop requiring a long frost-free period and loose soil."
    },

    "Soybean": {
        "temp_c": (20, 30),
        "rain_mm": (500, 900),
        "ph": (6.0, 7.5),
        "notes": "Warm-season legume requiring adequate moisture during flowering and pod filling."
    },

    "Green Bean": {
        "temp_c": (18, 30),
        "rain_mm": (500, 900),
        "ph": (6.0, 7.5),
        "notes": "Warm-season vegetable legume requiring consistent moisture."
    },


    # =========================
    # INDUSTRIAL / CASH CROPS
    # =========================

    "Cocoa": {
        "temp_c": (21, 32),
        "rain_mm": (1500, 2500),
        "ph": (5.0, 7.5),
        "notes": "Tropical crop requiring warm temperatures, high rainfall, and adequate humidity."
    },

    "Coffee": {
        "temp_c": (15, 28),
        "rain_mm": (1200, 2500),
        "ph": (5.0, 6.5),
        "notes": "Prefers mild tropical conditions, adequate rainfall, and slightly acidic soil."
    },

    "Cotton": {
        "temp_c": (21, 35),
        "rain_mm": (500, 1200),
        "ph": (5.5, 8.0),
        "notes": "Warm-season crop requiring a long frost-free growing period."
    },

    "Rubber": {
        "temp_c": (24, 30),
        "rain_mm": (2000, 3000),
        "ph": (4.5, 6.5),
        "notes": "Tropical tree crop requiring consistently warm and humid conditions."
    },

    "Sugarcane": {
        "temp_c": (20, 35),
        "rain_mm": (1000, 2000),
        "ph": (5.0, 8.0),
        "notes": "Warm-season crop with high water requirements and a long growing period."
    },

    "Sunflower": {
        "temp_c": (18, 32),
        "rain_mm": (400, 800),
        "ph": (6.0, 7.5),
        "notes": "Warm-season crop with moderate drought tolerance once established."
    },

    "Tobacco": {
        "temp_c": (18, 30),
        "rain_mm": (500, 1200),
        "ph": (5.5, 7.0),
        "notes": "Warm-season crop requiring a frost-free growing period and well-drained soil."
    },


    # =========================
    # SPICES / HERBS
    # =========================

    "Black Pepper": {
        "temp_c": (20, 35),
        "rain_mm": (1500, 3000),
        "ph": (5.5, 7.0),
        "notes": "Tropical climbing crop requiring warmth, high rainfall, and humidity."
    },

    "Cardamom": {
        "temp_c": (18, 30),
        "rain_mm": (1500, 4000),
        "ph": (5.5, 6.5),
        "notes": "Tropical spice crop requiring warm, humid conditions and shade."
    },

    "Chili Pepper": {
        "temp_c": (18, 32),
        "rain_mm": (600, 1200),
        "ph": (5.5, 7.0),
        "notes": "Warm-season crop requiring good drainage and consistent moisture."
    },

    "Ginger": {
        "temp_c": (20, 32),
        "rain_mm": (1500, 3000),
        "ph": (5.5, 7.0),
        "notes": "Tropical rhizome crop requiring warm conditions, moisture, and good drainage."
    },

    "Turmeric": {
        "temp_c": (20, 35),
        "rain_mm": (1000, 2000),
        "ph": (5.0, 7.5),
        "notes": "Warm tropical crop requiring moisture and well-drained fertile soil."
    },

    "Basil": {
        "temp_c": (18, 32),
        "rain_mm": (500, 1000),
        "ph": (5.5, 7.5),
        "notes": "Warm-season herb requiring sunlight, warmth, and adequate moisture."
    },

    "Mint": {
        "temp_c": (15, 30),
        "rain_mm": (600, 1500),
        "ph": (6.0, 7.5),
        "notes": "Moisture-loving herb that performs best in fertile soil."
    },


    # =========================
    # OTHER CROPS
    # =========================

    "Date Palm": {
        "temp_c": (20, 45),
        "rain_mm": (50, 400),
        "ph": (6.0, 8.5),
        "notes": "Thrives in hot, arid conditions with irrigation and tolerates saline and alkaline soils well."
    },

    "Flax": {
        "temp_c": (10, 25),
        "rain_mm": (400, 750),
        "ph": (5.5, 7.5),
        "notes": "Cool-season crop that prefers moderate temperatures and well-drained soil."
    },

    "Jute": {
        "temp_c": (24, 35),
        "rain_mm": (1500, 2500),
        "ph": (6.0, 7.5),
        "notes": "Warm and moisture-loving fiber crop suited to humid tropical climates."
    },

    "Quinoa": {
        "temp_c": (8, 24),
        "rain_mm": (300, 700),
        "ph": (6.0, 8.5),
        "notes": "Adaptable crop that can tolerate relatively dry conditions and some soil salinity."
    },

    "Sesame": {
        "temp_c": (20, 35),
        "rain_mm": (400, 800),
        "ph": (5.5, 8.0),
        "notes": "Warm-season oilseed with relatively good drought tolerance."
    },

    "Tea": {
        "temp_c": (18, 30),
        "rain_mm": (1500, 3000),
        "ph": (4.5, 5.5),
        "notes": "Prefers warm, humid climates and strongly acidic, well-drained soils."
    },
}


# ============================================================
# DISEASE TREATMENTS
# ============================================================

DISEASE_TREATMENTS = {

    "Healthy":
        "No signs of disease. Maintain proper watering, spacing, and regular monitoring.",

    "Early Blight":
        "Remove affected lower leaves, avoid overhead watering, and apply an appropriate fungicide if needed.",

    "Late Blight":
        "Remove infected plants promptly, improve airflow, and use a fungicide labelled for late blight.",

    "Leaf Mold":
        "Increase ventilation, reduce humidity, avoid wetting leaves, and remove affected leaves.",

    "Bacterial Spot":
        "Avoid overhead irrigation, remove infected material, disinfect tools, and consider a suitable copper-based treatment.",

    "Powdery Mildew":
        "Improve air circulation, avoid excess nitrogen, and use an appropriate mildew treatment.",

    "Target Spot":
        "Remove infected leaves, avoid overhead watering, and apply a labelled fungicide if required.",

    "Septoria Leaf Spot":
        "Remove infected leaves, prevent soil from splashing onto foliage, and use an appropriate fungicide.",

    "Tomato Mosaic Virus":
        "There is no direct cure. Remove infected plants, disinfect tools, and control insect vectors.",

    "Tomato Yellow Leaf Curl Virus":
        "Remove infected plants and control whiteflies, which are a major vector.",

    "Common Rust":
        "Use a labelled fungicide when appropriate, avoid overhead watering, and consider resistant varieties.",

    "Northern Leaf Blight":
        "Rotate crops, remove crop debris, and use a labelled fungicide when appropriate.",

    "Apple Scab":
        "Remove fallen leaves, improve airflow through pruning, and use an appropriate fungicide.",

    "Black Rot":
        "Remove infected wood and fruit, improve airflow, and use a labelled fungicide.",

    "Cedar Apple Rust":
        "Remove nearby cedar/juniper hosts where practical and use appropriate disease management.",
}


DEFAULT_TREATMENT = (
    "Specific guidance for this exact disease label is not available yet. "
    "General steps: remove severely affected leaves, avoid overhead watering, "
    "improve airflow, and consult local agricultural extension guidance."
)
