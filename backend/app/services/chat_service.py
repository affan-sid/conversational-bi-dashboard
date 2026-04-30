def handle_chat(question: str):
    nlp_result = process_query(question)

    return {
        "message": "Processed successfully",
        "nlp_result": nlp_result
    }