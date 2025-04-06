from langchain_openai.chat_models.base import BaseChatOpenAI
from langchain_core.prompts import PromptTemplate
from typing import TypedDict, List
from langchain_core.messages import BaseMessage
from langgraph.graph import START, StateGraph, END, MessagesState
from langchain_core.documents import Document
from langgraph.checkpoint.memory import MemorySaver
from langchain_neo4j import Neo4jGraph
from langchain_core.output_parsers import StrOutputParser


class State(MessagesState):
    """Represents the state of the RAG pipeline with all necessary components."""
    user_question: str
    context: List[Document]
    answer: str
    next_node: str
    generated_cypher: str
    

class RAG:
    """Retrieval-Augmented Generation system with Neo4j graph database backend."""
    
    def __init__(self, api_key: str, neo4j_url: str, neo4j_username: str, neo4j_password: str):
        """
        Initialize RAG system with API keys and database credentials.
        
        Args:
            api_key: DeepSeek API key
            neo4j_url: Neo4j database connection URL
            neo4j_username: Neo4j username
            neo4j_password: Neo4j password
        """
        self.api_key = api_key
        self.llm = BaseChatOpenAI(
            model="deepseek-chat",
            openai_api_base="https://api.deepseek.com",
            api_key=api_key,
            max_tokens=1024,
            temperature=0.1
        )
        
        # Initialize prompt templates
        self._initialize_prompt_templates()
        
        # Setup memory and database connections
        self.memory = MemorySaver()
        self.database = Neo4jGraph(
            url=neo4j_url,
            username=neo4j_username,
            password=neo4j_password
        )
        
        # Build the processing graph
        self.graph = self._build_processing_graph()
        
    def _initialize_prompt_templates(self):
        """Initialize all prompt templates used in the RAG pipeline."""
        self.generate_template = PromptTemplate(
            input_variables=["context", "user_question"],
            template="""Answer the user's question based on the provided context. 
            If no context is available, use your general knowledge.
            Always respond in the language used by the user. 

            Context: {context}
            Question: {user_question}
            Answer in user language:"""
        )
        
        self.generate_cypher_template = PromptTemplate(
            input_variables=["user_question", "schema"],
            template="""Generate a CYPHER query based on the given graph database schema and user's question.
            The query should answer the question when executed against a Neo4j database. 
            Only respond in CYPHER, because if you don't program will crash :(.

            Database schema: {schema}
            Question: {user_question}

            Important: 
            - The generated CYPHER query must be valid syntax
            - Should work with the provided schema
            - No natural language explanation - just pure CYPHER

            CYPHER query:"""
        )
    
    def _build_processing_graph(self):
        """Construct the state machine graph for the RAG pipeline."""
        builder = StateGraph(State)
        
        # Define nodes
        builder.add_node("generate_cypher", self.generate_cypher)
        builder.add_node("retrieve", self.retrieve)
        builder.add_node("generate_response", self.generate_answer)
        builder.add_node("debug_print", self.debug_print)
        
        # Define edges
        builder.add_edge(START, "generate_cypher")
        builder.add_edge("generate_cypher", "retrieve")
        builder.add_edge("retrieve", "generate_response")
        builder.add_edge("generate_response", "debug_print")
        builder.add_edge("debug_print", END)
        
        return builder.compile(checkpointer=self.memory)
        
    def generate_cypher(self, state: State):
        """
        Generate CYPHER query from user question using database schema.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated state with generated CYPHER query
        """
        chain = self.generate_cypher_template | self.llm | StrOutputParser()
        generated_cypher = chain.invoke({
            "user_question": state["user_question"],
            "schema": self.database.get_schema
        })
        
        return {
            "generated_cypher": generated_cypher,
            "next_node": "generate_response"
        }
        
    def retrieve(self, state: State):
        """
        Execute CYPHER query against Neo4j database and retrieve results.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated state with retrieved context
        """
        response = self.database.query(state["generated_cypher"])
        return {"context": response}
        
    def generate_answer(self, state: State):
        """
        Generate natural language answer from retrieved context.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated state with generated answer
        """
        chain = self.generate_template | self.llm | StrOutputParser()
        llm_response = chain.invoke({
            "user_question": state["user_question"],
            "context": state["context"]
        })
        return {"answer": llm_response}

    def debug_print(self, state: State):
        """
        Print debug information about current pipeline state.
        
        Args:
            state: Current pipeline state
        """
        print("\n" + "="*50)
        print("STATE DEBUG INFORMATION")
        print("="*50)
        
        # User question
        print(f"\n[USER QUESTION]\n{state['user_question']}")
        
        # Context documents
        print("\n[CONTEXT DOCUMENTS]")
        print(state["context"] if state["context"] else "No context available")
        
        # Generated Cypher
        print("\n[GENERATED CYPHER]")
        print(state["generated_cypher"] if state["generated_cypher"] else "No Cypher generated")
        
        # Answer
        print("\n[ANSWER]")
        print(state["answer"] if state["answer"] else "No answer generated")
        
        print("\n" + "="*50 + "\n")
            
    def invoke(self, message: str):
        """
        Execute the RAG pipeline with user message.
        
        Args:
            message: User's question/input
            
        Returns:
            Generated answer
        """
        result = self.graph.invoke(
            {"user_question": message},
            config={"configurable": {"thread_id": 1}},
        )
        return result.get("answer")