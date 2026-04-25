from rapidfuzz import fuzz

brands = [
    "paypal.com",
    "google.com",
    "amazon.com",
    "facebook.com",
    "apple.com"
]

def typosquat_score(domain):
    scores = []

    for brand in brands:
        score = fuzz.ratio(domain, brand)
        scores.append(score)

    return max(scores)