from os.path import isfile
import yaml
import numpy as np

from .data_structures import Node, Connection, Surface, Tensegrity

class YamlParser:
    """
    A class for parsing YAML files and creating a Tensegrity object.

    Methods:
        parse(file: str) -> Tensegrity:
            Parses the YAML file and returns a Tensegrity object.
    """

    @staticmethod
    def parse(file: str) -> Tensegrity:
        """
        Parses the YAML file and returns a Tensegrity object.

        Args:
            file (str): The path to the YAML file.

        Returns:
            Tensegrity: The tensegrity system containing Nodes and Connections.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            yaml.YAMLError: If the YAML file is invalid.
            KeyError: If a builder type does not have a builder.
            ValueError: If a connection type is not recognized.
        """
        if not isfile(file):
            raise FileNotFoundError(f"The file {file} does not exist.")

        with open(file, "r", encoding="utf-8") as stream:
            try:
                data = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print("Invalid YAML file.")
                raise exc

            # --- Nodes ---
            nodes = {} # Dictionary to store nodes so I can find them by name
            for node_name in data["nodes"]:
                nodes[node_name] = Node(node_name, data["nodes"][node_name])

            # --- Surface ---
            surface = None
            linked_nodes = []
            if "surface" in data:
                for node_pairs in data["surface"]["linked_nodes"]:
                    linked_nodes.append({node_pairs[0], node_pairs[1]})
                surface_type = [key for key in data["surface"].keys() if key != "linked_nodes"][0] #find the key that is not linked_nodes
                shape = {"surface_type": surface_type, "properties": data["surface"][surface_type]}
                surface = Surface(shape, linked_nodes)

            # --- Connections ---
            connections = [] # List to store connections used to create Tensegrity object
            connection_names = {} # Dictionary to store named connections

            for builder_type in data["connections"]:
                # --- Builders ---
                if builder_type not in data["builders"]:
                    raise KeyError(f"Builder type {builder_type} does not have a builder.")

                stiffness = float(data["builders"][builder_type]["stiffness"])

                if data["builders"][builder_type]["type"] == "string":
                    connection_type = Connection.ConnectionType.STRING
                elif data["builders"][builder_type]["type"] == "bar":
                    connection_type = Connection.ConnectionType.BAR
                else:
                    raise ValueError(f"Connection type {data['builders'][builder_type]['type']} not recognized.")

                if "initial_length_ratio" in data["builders"][builder_type]:
                    initial_length_ratio = float(data["builders"][builder_type]["initial_length_ratio"])
                else:
                    initial_length_ratio = 1.0

                # Create connections
                for connection in data["connections"][builder_type]:
                    if isinstance(connection, dict): # If the connection has a name
                        for name, nodes_list in connection.items():
                            initial_length = 0
                            for i in range(len(nodes_list) - 1):
                                if {nodes_list[i], nodes_list[i+1]} in linked_nodes:
                                    continue
                                initial_length += np.linalg.norm(nodes[nodes_list[i]].position - nodes[nodes_list[i+1]].position)
                            initial_length *= initial_length_ratio

                            connection = Connection([nodes[n_name] for n_name in nodes_list], connection_type, stiffness, initial_length, name)
                            connections.append(connection)
                            connection_names[name] = connection
                    else:
                        initial_length = 0
                        for i in range(len(connection) - 1):
                            if {connection[i], connection[i+1]} in linked_nodes:
                                continue
                            initial_length += np.linalg.norm(nodes[connection[i]].position - nodes[connection[i+1]].position)
                        initial_length *= initial_length_ratio
                        connections.append(Connection([nodes[n_name] for n_name in connection], connection_type, stiffness, initial_length))

            # --- Pins ---
            pins = {}
            if "pin" in data:
                for pin in data["pin"]:
                    pins[pin] = data["pin"][pin] # NodeName: <Array of bools>

            # --- Control ---
            controls = []
            if "control" in data:
                for connection_name in data["control"]:
                    controls.append(connection_names[connection_name])

        return Tensegrity(list(nodes.values()), connections, pins, controls, surface)
