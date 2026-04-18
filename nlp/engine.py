from nlp.intent_classifier import classify_intent
from nlp.entity_extractor import extract_entities

def process_query(question):
    intent = classify_intent(question)
    entities = extract_entities(question)

    return {
        "question": question,
        "intent": intent,
        "entities": entities
    }
