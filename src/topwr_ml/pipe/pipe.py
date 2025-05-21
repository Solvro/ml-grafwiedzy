from src.topwr_ml.pipe.pdf_loader import PDFLoader
from typing import List
from src.topwr_ml.pipe.llm_pipe import LLMPipe
import os
from langchain_neo4j import Neo4jGraph


class DataPipe:
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        api_key: str = None,
        nodes: List[str] = None,
        relations: List[str] = None,
    ):
        self.docs_data = []
        self.llm_pipe = LLMPipe(api_key=api_key, nodes=nodes, relations=relations)
        self.graph_db = Neo4jGraph(url=url, username=username, password=password)

    def _load_data(self, file_path: str) -> None:
        """Load data from a file and append it to the docs_data list."""
        loader = PDFLoader(file_path)
        self.docs_data.append(loader.load_document())

    def load_data_from_directory(self, directory_path: str) -> None:
        """Load data from all files in a given directory."""
        for filename in os.listdir(directory_path):
            if (
                filename.endswith(".pdf")
                or filename.endswith(".txt")
                or filename.endswith(".docx")
            ):
                self._load_data(os.path.join(directory_path, filename))

    def clear_database(self) -> None:
        """Clear the Neo4j database."""
        self.execute_cypher("MATCH (n) DETACH DELETE n")

        print("Database cleared successfully")

    def execute_cypher(self, query: str) -> None:
        """Execute a Cypher query on the Neo4j database."""
        self.graph_db.query(query)
