'''Testy połączenia z Neo4j'''
def test_graph_connection():
    from src.topwr_ml.graph.connection import graph
    assert graph is not None
