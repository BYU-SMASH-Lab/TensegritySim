import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import numpy as np
from src.data_structures import Connection, Node, Tensegrity
from tensegrity_solver import TensegritySolver


@pytest.fixture
def OnexOne_tensegrity():
    node1 = Node(name="A", position=np.array([0.0, 0.0, 0.0]))
    node2 = Node(name="B", position=np.array([1.0, 0.0, 0.0]))
    node3 = Node(name="C", position=np.array([1.0, 1.0, 0.0]))
    node4 = Node(name="D", position=np.array([0.0, 1.0, 0.0]))
    nodes = [node1, node2, node3, node4]

    connection1 = Connection(nodes=[node1, node2, node3], connection_type=Connection.ConnectionType.STRING, stiffness=1.0)
    connection2 = Connection(nodes=[node3, node4], connection_type=Connection.ConnectionType.STRING, stiffness=1.0)
    connection3 = Connection(nodes=[node4, node1], connection_type=Connection.ConnectionType.STRING, stiffness=1.0)
    connection4 = Connection(nodes=[node1, node3], connection_type=Connection.ConnectionType.BAR, stiffness=100.0)
    connection5 = Connection(nodes=[node2, node4], connection_type=Connection.ConnectionType.BAR, stiffness=100.0)
    connections = [connection1, connection2, connection3, connection4, connection5]
 
    return Tensegrity(nodes, connections)

def test_node_distance(OnexOne_tensegrity):
    solver = TensegritySolver(OnexOne_tensegrity)
    N = np.array([node.position for node in OnexOne_tensegrity.nodes])

    # Test distance between node A and node B
    distance1 = solver._node_distance("A", "B", N)
    assert distance1 == 1.0, f"Expected distance 1.0, but got {distance1}"

    # Test distance between node A and node C
    distance2 = solver._node_distance("A", "C", N)
    assert distance2 == np.sqrt(2), f"Expected distance {np.sqrt(2)}, but got {distance2}"

    # Test distance between node B and node D
    distance3 = solver._node_distance("B", "D", N)
    assert distance3 == np.sqrt(2), f"Expected distance {np.sqrt(2)}, but got {distance3}"

    # Test distance between node C and node D
    distance4 = solver._node_distance("C", "D", N)
    assert distance4 == 1.0, f"Expected distance 1.0, but got {distance4}"

def test_connection_length(OnexOne_tensegrity):
    solver = TensegritySolver(OnexOne_tensegrity)
    N = np.array([node.position for node in OnexOne_tensegrity.nodes])

    # Test single connection length
    node_to_node_connection = OnexOne_tensegrity.connections[2]
    length1 = solver._connection_length(node_to_node_connection, N)
    assert length1 == 1.0, f"Expected length 1.0, but got {length1}"

    # Test multiple connection length
    multiple_node_connection = OnexOne_tensegrity.connections[0]
    length2 = solver._connection_length(multiple_node_connection, N)
    assert length2 == 2.0, f"Expected length 2.0, but got {length2}"


def test_spring_connection_energy(OnexOne_tensegrity):
    solver = TensegritySolver(OnexOne_tensegrity)
    N = np.array([node.position for node in OnexOne_tensegrity.nodes])

    # Test energy for a connection with zero length difference
    connection1 = OnexOne_tensegrity.connections[2]
    connection1.initial_length = 1.0
    # current length is 1.0
    energy1 = solver._spring_connection_energy(connection1, N)
    assert energy1 == 0.0, f"Expected energy 0.0, but got {energy1}"

    # Test energy for a connection with positive length difference
    connection2 = OnexOne_tensegrity.connections[0]
    connection2.initial_length = 1.0
    # current length is 2.0
    energy2 = solver._spring_connection_energy(connection2, N)
    expected_energy2 = 0.5 * connection2.stiffness * (2.0 - 1.0)**2
    assert energy2 == expected_energy2, f"Expected energy {expected_energy2}, but got {energy2}"

    # Test energy for a connection with negative length difference
    connection3 = OnexOne_tensegrity.connections[1]
    connection3.initial_length = 2.0
    # current length is 1.0
    energy3 = solver._spring_connection_energy(connection3, N)
    expected_energy3 = 0 # string connection cannot be compressed
    assert energy3 == expected_energy3, f"Expected energy {expected_energy3}, but got {energy3}"