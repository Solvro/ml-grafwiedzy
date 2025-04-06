from rag import RAG
from dotenv import load_dotenv
from os import environ
def main():
    load_dotenv(".env")
    API_KEY =environ.get("DEEPSEEK_API_KEY")
    NEO4J_URI = environ.get("NEO4J_URI")
    NEO4J_USERNAME = environ.get("NEO4J_USERNAME")
    NEO4J_PASSWORD = environ.get("NEO4J_PASSWORD")
    rag = RAG(api_key=API_KEY, neo4j_url=NEO4J_URI,neo4j_username=NEO4J_USERNAME,
        neo4j_password=NEO4J_PASSWORD)

    response = rag.invoke("Jak mogę zaliczyć praktyki ?")
    print(response)

if __name__ == "__main__":
    main()