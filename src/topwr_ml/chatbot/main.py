from rag import RAG
from dotenv import load_dotenv
from os import environ


def main():
    load_dotenv(r"C:\Users\pawli\OneDrive\Pulpit\GrafWiedzy\ml-grafwiedzy\.env")
    API_KEY = environ.get("DEEPSEEK_API_KEY")
    NEO4J_URI = environ.get("NEO4J_URI")
    NEO4J_USERNAME = environ.get("NEO4J_USERNAME", environ.get("NEO4J_USER"))
    NEO4J_PASSWORD = environ.get("NEO4J_PASSWORD")
    
    # Sprawdzenie czy wszystkie wymagane zmienne są dostępne
    missing_vars = []
    if not API_KEY:
        missing_vars.append("DEEPSEEK_API_KEY")
    if not NEO4J_URI:
        missing_vars.append("NEO4J_URI")
    if not NEO4J_USERNAME:
        missing_vars.append("NEO4J_USERNAME lub NEO4J_USER")
    if not NEO4J_PASSWORD:
        missing_vars.append("NEO4J_PASSWORD")
    
    if missing_vars:
        raise ValueError(f"Brakujące zmienne środowiskowe: {', '.join(missing_vars)}")
    
    rag = RAG(
        api_key=API_KEY, 
        neo4j_url=NEO4J_URI,
        neo4j_username=NEO4J_USERNAME,
        neo4j_password=NEO4J_PASSWORD
    )

    response = rag.invoke("Jak mogę zaliczyć praktyki?")
    print(response)

if __name__ == "__main__":
    main()