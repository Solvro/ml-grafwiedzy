'''Połączenie z Neo4j'''
from py2neo import Graph
from src.topwr_ml.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
