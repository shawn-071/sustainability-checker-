"""Conservative, low-cost first steps shown after a leaf screening."""

GENERAL_STEPS = (
    "Photograph the plant and note when symptoms began. Remove clearly diseased "
    "tissue with clean tools while plants are dry, water near the roots, and ask "
    "a local agricultural extension service to confirm the cause before applying "
    "a treatment."
)

BIO_FIRST_STEPS = {
    "Healthy": "No likely disease label was returned. Keep monitoring and water the soil rather than the leaves.",
    "Early Blight": "Remove heavily spotted lower leaves, clear crop debris, mulch to limit soil splash, and rotate away from tomatoes and potatoes where possible.",
    "Late Blight": "Separate affected plants and seek local agricultural advice promptly; late blight can spread quickly. Do not compost severely infected material unless local guidance says it is safe.",
    "Leaf Mold": "Increase airflow, avoid overhead watering, and remove badly affected leaves with clean tools.",
    "Bacterial Spot": "Avoid handling wet plants, clean tools between plants, and remove infected debris. Use clean seed and transplants next season.",
    "Powdery Mildew": "Improve airflow, remove badly affected leaves, and avoid excessive nitrogen that encourages soft growth.",
    "Target Spot": "Remove affected debris, water at the soil line, and improve spacing so leaves dry quickly.",
    "Septoria Leaf Spot": "Remove spotted lower leaves, use mulch to reduce soil splash, and avoid overhead watering.",
    "Tomato Mosaic Virus": "Avoid handling plants after touching a suspected plant, clean tools, and ask local extension staff about safe removal and disposal.",
    "Tomato Yellow Leaf Curl Virus": "Photograph symptoms and ask local agricultural extension staff to confirm the cause and advise on local vector management before treating or removing plants.",
    "Common Rust": "Remove heavily affected leaves, improve airflow, and ask about locally adapted resistant varieties.",
    "Northern Leaf Blight": "Remove crop debris after harvest, rotate crop families where practical, and ask local extension staff to confirm the diagnosis.",
    "Apple Scab": "Collect fallen leaves, prune for airflow during the appropriate season, and ask a local advisor about resistant varieties.",
}


def first_steps(disease: str) -> str:
    return BIO_FIRST_STEPS.get(disease, GENERAL_STEPS)
