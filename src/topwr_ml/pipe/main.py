from dotenv import load_dotenv
import os
from topwr_ml.pipe.pipe import DataPipe


def main():
    load_dotenv()

    nodes = ["Internship", "Student", "Company", "Supervisor", "Documentation"]

    relationships = [
        "chooses",
        "completes",
        "consults",
        "provides",
        "approves",
        "verifies",
        "requires",
        "demands",
        "confirms",
        "proves",
    ]

    pipe = DataPipe(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        nodes=nodes,
        relations=relationships,
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
    )

    pipe.load_data_from_directory("data/test")
    pipe.clear_database()
    pipe_response = "".join(
        pipe_element
        for pipe_element in pipe.llm_pipe.run(
            "".join([item for item in pipe.docs_data]).strip("|")
        )
    )

    try:
        print(f"GENERATED CYPHER: {pipe_response}")
        pipe.execute_cypher(pipe_response)

    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
