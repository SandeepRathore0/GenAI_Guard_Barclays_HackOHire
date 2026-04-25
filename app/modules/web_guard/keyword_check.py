keywords = ["login", "verify", "secure", "account", "bank", "update"]

def check_keywords(url):
    found = []

    for k in keywords:
        if k in url.lower():
            found.append(k)

    return found