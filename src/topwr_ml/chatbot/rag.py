from langchain_openai.chat_models.base import BaseChatOpenAI
from langchain_core.prompts import PromptTemplate
from typing import List
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
    conversation_history: List[str]  
    is_valid_cypher: bool = True
    cypher_validation_error: str  
    cypher_attempt: int = 0
    
    

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

        self._initialize_prompt_templates()
        
        self.memory = MemorySaver()
        self.database = Neo4jGraph(
            url=neo4j_url,
            username=neo4j_username,
            password=neo4j_password
        )
        
        self.conversation_store = {}
        
        self.graph = self._build_processing_graph()
        
    def _initialize_prompt_templates(self):
        """Initialize all prompt templates used in the RAG pipeline."""
        self.generate_template = PromptTemplate(
            input_variables=["context", "user_question", "conversation_history"],
            template="""Answer the user's question based on the provided context and previous conversation. 
            If no context is available, use your general knowledge.
            Always respond in the language used by the user. 

            Previous conversation:
            {conversation_history}

            Context: {context}
            Question: {user_question}
            Answer in user language:"""
        )
        
        self.generate_cypher_template = PromptTemplate(
            input_variables=["user_question", "schema", "conversation_history"],
            template="""Generate a CYPHER query based on the given graph database schema, user's question, and previous conversation.
            The query should answer the question when executed against a Neo4j database. 
            Only respond in CYPHER, because if you don't program will crash :(.

            Previous conversation:
            {conversation_history}

            Database schema: {schema}
            Question: {user_question}

            Important: 
            - The generated CYPHER query must be valid syntax
            - Should work with the provided schema
            - No natural language explanation - just pure CYPHER
            - Consider previous conversation context when relevant

            CYPHER query:"""
        )
        
        self.guard_rails_template = PromptTemplate(
            input_variables=["user_question", "conversation_history"],
            template=
            """
            As an intelligent assistant, your primary objective is to decide whether a given question is related to 
            Wroclaw Univeristy of Science and Technology or Univeristy at all (terminology, workers, classes etc.)
            If the question is related to univeristy, output "generate_cypher". Otherwise, output "end".
            To make this decision, assess the content of the question and determine if it refers to any 
            college terminology, professors, syllabus or faculty. But if its general university knowledge,
            such as "Who is dean?" or "What is a faculty?" or general knowledge at all, generate "end" response.
            Consider previous conversation context when making your decision.
            Respond only with words "end" or "generate_cypher"            
            Previous conversation:
            {conversation_history}
            
            User question : {user_question}
            """
        )
        
        self.summarize_conversation_template = PromptTemplate(
            input_variables=["conversation_history", "user_question", "response"],
            template="""Generate summary of conversation in 2-3 sentences

            Previous conversation:
            {conversation_history}
            
            User question:
            {user_question}
            
            LLM response:
            {response}
            
            """
        )
    
    def _build_processing_graph(self):
        """Construct the state machine graph for the RAG pipeline."""
        builder = StateGraph(State)
        
        builder.add_node("guardrails_system", self.guardrails_system)
        builder.add_node("generate_cypher", self.generate_cypher)
        builder.add_node("validate_cypher", self.validate_cypher)  
        builder.add_node("correct_cypher", self.correct_cypher)  
        builder.add_node("retrieve", self.retrieve)
        builder.add_node("generate_response", self.generate_answer)
        builder.add_node("update_history", self.update_history)
        builder.add_node("debug_print", self.debug_print)
        builder.add_node("loop_end", self.loop_end)
        
        builder.add_edge(START, "guardrails_system")
        builder.add_conditional_edges(
            "guardrails_system",
            lambda state: state["next_node"],
            {
                "generate_cypher": "generate_cypher",
                "end": "generate_response"
            }
        )
        
        builder.add_edge("generate_cypher", "validate_cypher")
        
        builder.add_conditional_edges(
            "validate_cypher",
            lambda state: (
                "correct_cypher"
                if not state.get("is_valid_cypher", True) and state.get("cypher_attempt", 0) < 5 # limit attempts to 5
                else (
                      "loop_end"
                      if not state.get("is_valid_cypher", True) and state.get("cypher_attempt", 0) >= 5
                      else "retrieve"
                )
            ),
            {
                "correct_cypher": "correct_cypher",
                "loop_end": "loop_end",
                "retrieve": "retrieve" 
            }
        )
        
        builder.add_edge("correct_cypher", "validate_cypher")
        
        builder.add_edge("retrieve", "generate_response")
        builder.add_edge("generate_response", "update_history")
        builder.add_edge("update_history", "debug_print")
        
        builder.add_edge("loop_end", END)
        builder.add_edge("debug_print", END)
        
        return builder.compile(checkpointer=self.memory)
        
    def format_conversation_history(self, history: List[str]) -> str:
        """
        Format conversation history as a string for inclusion in prompts.
        
        Args:
            history: List of conversation messages
            
        Returns:
            Formatted conversation history string
        """
        if not history:
            return "No previous conversation."
                
        return "".join([shard for shard in history])
        
    def generate_cypher(self, state: State):
        """
        Generate CYPHER query from user question using database schema.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated state with generated CYPHER query
        """
        formatted_history = self.format_conversation_history(state["conversation_history"])
        
        chain = self.generate_cypher_template | self.llm | StrOutputParser()
        generated_cypher = chain.invoke({
            "user_question": state["user_question"],
            "schema": self.database.get_schema,
            "conversation_history": formatted_history
        })
        
        return {
            "generated_cypher": generated_cypher,
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
        formatted_history = self.format_conversation_history(state["conversation_history"])
        
        chain = self.generate_template | self.llm | StrOutputParser()
        llm_response = chain.invoke({
            "user_question": state["user_question"],
            "context": state["context"],
            "conversation_history": formatted_history
        })
        return {"answer": llm_response}
    
    def guardrails_system(self, state: State):
        """
        Decide whether to base answer on retireved information or on LLMs general knowledge
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated state with generated next_step
        """
        formatted_history = self.format_conversation_history(state["conversation_history"])
        
        guardrails_chain = self.guard_rails_template | self.llm | StrOutputParser()
        
        guardrail_output = guardrails_chain.invoke({
            "user_question": state["user_question"],
            "conversation_history": formatted_history
        })
        
        return {
            "next_node": guardrail_output,
            "context": "No context given" if guardrail_output == "end" else None,
            "generated_cypher": "No cypher generated" if guardrail_output == "end" else None, 
        }
        
    def update_history(self, state: State):
        """
        Update conversation history with the latest exchange.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated state with updated conversation history
        """
        
        summarizer_chain = self.summarize_conversation_template | self.llm | StrOutputParser()
        
        summarizer_output = summarizer_chain.invoke({
            "conversation_history" : state["conversation_history"],
            "user_question" : state["user_question"],
            "response" : state["answer"]
            
        })
       
        return {"conversation_history": summarizer_output}

    def debug_print(self, state: State):
        """
        Print debug information about current pipeline state.
        
        Args:
            state: Current pipeline state
        """
        print("\n" + "="*50)
        print("STATE DEBUG INFORMATION")
        print("="*50)
        
        print(f"\n[USER QUESTION]\n{state['user_question']}")
        
        print("\n[CONTEXT DOCUMENTS]")
        print(state["context"] if state["context"] else "No context available")
        
        print("\n[GENERATED CYPHER]")
        print(state["generated_cypher"] if state["generated_cypher"] else "No Cypher generated")
        
        print("\n[ANSWER]")
        print(state["answer"] if state["answer"] else "No answer generated")
        
        print("\n[CONVERSATION HISTORY]")
        print(self.format_conversation_history(state["conversation_history"]))
        
        print("\n" + "="*50 + "\n")
        
        return state
    
    def validate_cypher(self, state: State):
        """
        Validate the generated Cypher query for syntax correctness and schema compatibility.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated state with validation result
        """
        if state.get("generated_cypher") in [None, "No cypher generated"]:
                return {"is_valid_cypher": False, "cypher_validation_error": "No Cypher query to validate"}
        
        try:
            validation_query = f"EXPLAIN {state['generated_cypher']}"
            
            try:
                self.database.query(validation_query)
                return {"is_valid_cypher": True, "cypher_validation_error": None}
            except Exception as e:

                error_message = str(e)
                return {
                    "is_valid_cypher": False,
                    "cypher_validation_error": error_message
                }
                
        except Exception as general_error:
            return {
                "is_valid_cypher": False,
                "cypher_validation_error": f"Validation error: {str(general_error)}"
            }

    def correct_cypher(self, state: State):
        """
        Correct the Cypher query if validation failed.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated state with corrected Cypher query
        """

        if state.get("is_valid_cypher", True):
            return {}
        formatted_history = self.format_conversation_history(state["conversation_history"])

        attempts = state.get("cypher_attempt", 0) + 1
        
        correction_template = PromptTemplate(
            input_variables=["user_question", "schema", "original_cypher", "error_message"],
            template="""
            The Cypher query generated to answer the user's question has syntax or schema compatibility errors.
            Please correct the query to make it valid.
            
            User question: {user_question}
            Database schema: {schema}
            
            Original query with errors:
            ```
            {original_cypher}
            ```
            
            Error message:
            {error_message}
            
            Please provide a corrected Cypher query that addresses these errors.
            Return ONLY the corrected Cypher query without any explanations or markdown:
            """
        )
        

        correction_chain = correction_template | self.llm | StrOutputParser()

        corrected_cypher = correction_chain.invoke({
            "user_question": state["user_question"],
            "schema": self.database.get_schema,
            "original_cypher": state["generated_cypher"],
            "error_message": state.get("cypher_validation_error", "Unknown error")
        })
        
        print(f"\n[CYPHER CORRECTION]\nOriginal: {state['generated_cypher']}\nCorrected: {corrected_cypher}")
        
        return {"generated_cypher": corrected_cypher, "cypher_attempt": attempts}
        
        
    def invoke(self, message: str, session_id: str = "default"):
        """
        Execute the RAG pipeline with user message and maintain conversation history.
        
        Args:
            message: User's question/input
            session_id: Unique identifier for the conversation session
            
        Returns:
            Generated answer
        """
        if session_id not in self.conversation_store:
            self.conversation_store[session_id] = []
            
        conversation_history = self.conversation_store[session_id]
  
        result = self.graph.invoke(
            {
                "user_question": message,
                "conversation_history": conversation_history
            },
            config={"configurable": {"thread_id": session_id}},
        )
        

        self.conversation_store[session_id] = result.get("conversation_history", conversation_history)
        
        return result.get("answer")
    
    def loop_end(self, state: State):
        """
        Returns prompt when cypher_attempt limit is reached.
        """
        return {'answer': "I'm sorry, but I couldn't generate a valid Cypher query after multiple attempts. Please try rephrasing your question or ask something else."}