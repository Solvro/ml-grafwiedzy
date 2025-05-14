from langchain_openai.chat_models.base import BaseChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END, MessagesState
from typing import List


class PipeState(MessagesState):
    context: str
    generated_cypher: List[str]


class LLMPipe:
    def __init__(
        self, api_key: str = None, nodes: List[str] = None, relations: List[str] = None
    ):
        self.model = BaseChatOpenAI(
            model="deepseek-chat",
            openai_api_base="https://api.deepseek.com",
            api_key=api_key,
            max_tokens=1024,
            temperature=0.1,
        )
        self._initialize_prompt_templates()
        self.nodes = nodes
        self.relations = relations
        self._build_pipe_graph()

    def _initialize_prompt_templates(self) -> None:
        """Initialize all prompt templates used in the RAG pipeline."""

        self.generate_template = PromptTemplate(
            input_variables=["context", "nodes", "relations"],
            template="""Based ONLY on the provided context extracted from PDF or text file, identify entities and relationships.
            Don't use your general knowledge if not found in context.
            
            Context: {context}
            
            Allowed node types in graph database: {nodes}
            Allowed relation types in graph database: {relations}
            
            Your task is to analyze the context and generate Cypher code that will create new nodes and relationships 
            in the Neo4j graph database based on the information found in the context. Only use the allowed node and relation types.
            
            The Cypher code should follow these guidelines:
            // Create nodes for identified entities
            // Create relationships between entities
            // Use MERGE statements to avoid duplicates
            
            The Cypher code should be executable in Neo4j and properly handle the creation of all relevant nodes and relationships.
            Answer only with the Cypher code, without any additional explanations or comments.
            
            Divide cypher code into multiple lines if necessary - if you do 
            divide it with | character.
            Do not use any other characters or symbols to divide the code.  

            Nodes should have property of context and you should pass to that property proper text of given context.
            Make also appropariate titles for nodes .
            """,
        )

    def _build_pipe_graph(self) -> None:
        """Build the pipeline graph for the RAG process."""

        builder = StateGraph(PipeState)

        nodes = [
            ("generate", self.generate_cypher),
        ]

        for node_name, node_func in nodes:
            builder.add_node(node_name, node_func)

        builder.add_edge(START, "generate")
        builder.add_edge("generate", END)

        self.graph = builder.compile()

    def generate_cypher(self, state: PipeState) -> List[str]:
        chain = self.generate_template | self.model | StrOutputParser()

        cypher_code = chain.invoke(
            {
                "context": state["context"],
                "nodes": self.nodes,
                "relations": self.relations,
            }
        )

        return {
            "generated_cypher": [code_part for code_part in cypher_code.split("|")],
        }

    def run(self, context: str) -> List[str]:
        """Run the pipeline with the given context."""
        result = self.graph.invoke(
            {
                "context": context,
                "generated_cypher": [],
            },
            config={"configurable": {"thread_id": 1}},
        )
        return result["generated_cypher"]
