"""Small transparent baseline sentiment lexicon; not a trained production model."""
POSITIVE = {"sube", "alcista", "crece", "positivo", "recupera", "fuerte", "gana"}
NEGATIVE = {"baja", "bajista", "cae", "negativo", "riesgo", "débil", "pierde"}
def analizar_sentimiento(texto: str) -> dict:
    if not isinstance(texto, str):
        raise ValueError("texto must be a string")
    tokens = {token.strip(".,:;!?¡¿()[]{}").lower() for token in texto.split()}
    score = (len(tokens & POSITIVE) - len(tokens & NEGATIVE)) / max(1, len(tokens))
    return {"score": round(max(-1.0, min(1.0, score)), 6), "method": "transparent_lexicon_baseline",
            "is_trained_model": False}
