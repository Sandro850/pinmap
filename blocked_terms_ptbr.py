BLOCKED_TERMS_BY_CATEGORY = {
    "profanity": {
        "palavrao",
        "bosta",
        "merda",
        "porra",
        "caralho",
        "cacete",
        "droga",
        "foda",
        "foder",
        "fodase",
        "puta",
        "putaria",
        "pqp",
        "cu",
        "buceta",
        "piroca",
        "rola",
    },
    "harassment": {
        "ofensa",
        "burro",
        "burra",
        "idiota",
        "imbecil",
        "otario",
        "otaria",
        "babaca",
        "trouxa",
        "lixo",
        "escroto",
        "escrota",
        "desgracado",
        "desgracada",
    },
    "threat": {
        "ameaca",
        "ameacar",
        "matar",
        "morte",
        "morrer",
        "morra",
        "terror",
        "explodir",
        "bomba",
        "agredir",
        "violencia",
        "espancar",
    },
    "spam": {
        "spam",
        "golpe",
        "fraude",
        "scam",
        "phishing",
        "clique aqui",
        "dinheiro facil",
        "ganhe dinheiro",
        "pix gratis",
        "aposta",
        "cassino",
        "bet",
    },
}


def get_blocked_terms() -> set[str]:
    terms: set[str] = set()

    for category_terms in BLOCKED_TERMS_BY_CATEGORY.values():
        terms.update(category_terms)

    return terms
