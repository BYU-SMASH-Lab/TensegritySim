import numpy as np
from typing import Dict
from scipy.optimize import root

from .data_structures import Connection, Tensegrity


class TensegritySolver:
    """
    TensegritySolver class for solving the positions of nodes in a tensegrity structure.
    This class provides methods to initialize the solver, set forces on nodes, and solve the positions of nodes
    using optimization techniques. It also includes internal functions to compute the objective function, 
    spring connection energy, and its derivatives.
    
    Attributes:
        tensegrity (Tensegrity): The tensegrity object containing nodes and connections.
        dim (int): The dimension of the optimization problem (defaults to tensegrity's dim).
    """
    def __init__(self, tensegrity: Tensegrity) -> None:
        """
        Initializes an Optimization object.

        Args:
            tensegrity (Tensegrity): The tensegrity object containing nodes and connections.
            dim (int): The dimension of the optimization problem (default is 3).

        Raises:
            ValueError: If connection stiffness is less than 0.
        """
        self.tensegrity = tensegrity

        self.dim = tensegrity.dim
        if self.dim == 2.5:
            self.dim = 2

        self.node_indices = {node.name: i for i, node in enumerate(self.tensegrity.nodes)}

        self.forces = np.zeros(self.dim*len(self.tensegrity.nodes))

    def set_forces(self, forces: Dict[str, np.ndarray]) -> None:
        """
        Sets the forces on the nodes in the tensegrity structure.
        
        Args:
            forces (Dict[str, np.ndarray]): A dictionary containing the forces on each node.
        
        Raises:
            ValueError: If the force vector does not have the same dimension as the optimization problem.
        """
        self.forces = np.zeros(self.dim*len(self.tensegrity.nodes))

        for node, force in forces.items():
            if len(force) != self.dim:
                raise ValueError("Force vector must have the same dimension as the optimization problem.")

            index = self.node_indices[node]
            self.forces[index*self.dim : index*self.dim + self.dim] = force

    def solve(self, method: str = "lm") -> None:
        """
        Solves the position of nodes in the tensegrity structure.
        
        This method uses the root function from the scipy.optimize module to find the positions of the nodes
        in the tensegrity structure with Virtual Work.
        
        Args:
            method (str): The method to use for the root function (default is "lm").
        
        Returns:
            None. Changes are made internally to the Tensegrity object.
        """
        x0 = self._create_initial_guess() # The current positions of the nodes (excluding pinned nodes)

        result = root(self._objective, x0, method=method) # solver

        if not result.success:
            print(result)
            print("Optimization failed.")
            print("Retrying with perturbed initial guess.")

            x0 = x0 + np.random.normal(0, 0.1, len(x0))
            result = root(self._objective, x0, method=method)

            if not result.success:
                print(result)
                print("Optimization failed again.")
                return

        N = self._get_nodes_from_input(result.x)

        # update the positions of the nodes
        for i, node in enumerate(self.tensegrity.nodes):
            node.position = N[i]

        self.tensegrity.update_forces()


    # --------------------- INTERNAL FUNCTIONS ---------------------
    def _objective(self, x: np.ndarray) -> np.ndarray:
        """
        Computes the objective function for the optimization problem.
        This function calculates the virtual work from potential energy and external forces,
        and optionally includes surface constraints if a surface is defined.
        
        Args:
            x (np.ndarray): Input array representing the generalized coordinates.
        
        Returns:
            np.ndarray: The objective function value, which is the virtual work with optional surface constraints.
        """
        N = self._get_nodes_from_input(x)

        virtual_work = np.zeros(self.dim*len(self.tensegrity.nodes))

        # Virtual work from potential energy
        for connection in self.tensegrity.connections:
            virtual_work += self._spring_connection_energy_derivative(connection, N)

        # Virtual work from external forces
        virtual_work += self.forces

        # delete the pinned nodes (those cannot be generalized coordinates)
        delete_indices = set()
        for node, bools in self.tensegrity.pins.items():
            for i in range(self.dim):
                if bools[i]:
                    delete_indices.add(self.node_indices[node]*self.dim + i)

        if self.tensegrity.surface:
            for node1, node2 in self.tensegrity.surface.linked_nodes:
                if self.node_indices[node1]*self.dim in delete_indices:
                    delete_indices.add(self.node_indices[node2]*self.dim)
                elif self.node_indices[node2]*self.dim in delete_indices:
                    delete_indices.add(self.node_indices[node1]*self.dim)
                else:
                    # Because the x-coords of linked nodes must be exactly the circumference of the cylinder apart
                    # (N1[0] = N2[0] +/- C), the relationship is linear
                    # therefore dV/dq_i = dV/dq_j for the x-coord of linked nodes i and j,
                    # so we can add the virtual work of node2 in the x to node1 in the x
                    # so it was as if we always had taken the derivative with respect to node1x where node2x is a function of node1x
                    virtual_work[self.node_indices[node1]*self.dim] += virtual_work[self.node_indices[node2]*self.dim]
                    delete_indices.add(self.node_indices[node2]*self.dim)

                if self.node_indices[node1]*self.dim + 1 in delete_indices:
                    delete_indices.add(self.node_indices[node2]*self.dim + 1)
                elif self.node_indices[node2]*self.dim + 1 in delete_indices:
                    delete_indices.add(self.node_indices[node1]*self.dim + 1)
                else:
                    # The y-coords of linked nodes must be the same, so we can add the virtual work of node2 in the y to node1 in the y
                    virtual_work[self.node_indices[node1]*self.dim + 1] += virtual_work[self.node_indices[node2]*self.dim + 1]
                    delete_indices.add(self.node_indices[node2]*self.dim + 1)

            virtual_work = np.delete(virtual_work, list(delete_indices))

            objective = np.append(virtual_work, self._surface_constraints(x))

        else:
            objective = np.delete(virtual_work, list(delete_indices))

        return objective

    def _spring_connection_energy(self, connection: Connection, N: np.ndarray) -> float:
        """
        Calculates the energy stored in a spring connection.

        Args:
            connection (Connection): The spring connection object.
            N (np.ndarray): The current positions of all nodes.

        Returns:
            float: The energy stored in the spring connection.
        """
        # current length
        length = self._connection_length(connection, N)

        if connection.connection_type.name == Connection.ConnectionType.STRING.name and length < connection.initial_length:  # string connections cannot store energy when compressed
            return 0

        # energy
        energy = 0.5 * connection.stiffness * (length - connection.initial_length)**2

        return energy

    def _spring_connection_energy_derivative(self, connection: Connection, N: np.ndarray) -> np.ndarray:
        """
        Calculates the derivative of the spring connection energy with respect to node positions.

        The energy of a spring connection is given by:
            V = 0.5 * k * (l - l0)^2
        where k is the stiffness, l is the current length of the connection, and l0 is the rest length.

        The derivative of the energy with respect to the position of node i is:
            dV/dq_i = -k * (l - l0) * dl/dq_i
                    = C * dl/dq_i
        where C is a constant factor.

        Args:
            connection (Connection): The connection object representing the spring.
            N (np.ndarray): The array of node positions.

        Returns:
            np.ndarray: The derivative of the spring connection energy with respect to the node positions.
        """
        # current length
        length = self._connection_length(connection, N)

        if connection.connection_type.name == Connection.ConnectionType.STRING.name and length < connection.initial_length: # string connections cannot store energy when compressed
            return np.zeros(self.dim*len(self.tensegrity.nodes))

        C = -connection.stiffness * (length - connection.initial_length)

        return C * self._length_derivative(connection, N)

    def _length_derivative(self, connection: Connection, N: np.ndarray) -> np.ndarray:
        """
        Calculates the derivative of the length of a connection with respect to the node positions.
        
        Args:
            connection (Connection): The connection object containing the nodes.
            N (np.ndarray): The array of node positions.
        
        Returns:
            np.ndarray: The derivative of the length with respect to the node positions.
        """
        # l = sum_i=1^n-1 ||N_i - N_i+1||

        dl = np.zeros(self.dim*len(self.tensegrity.nodes))

        for i in range(len(connection.nodes) - 1):
            N1_index = self.node_indices[connection.nodes[i].name]
            N2_index = self.node_indices[connection.nodes[i+1].name]
            N1 = N[N1_index]
            N2 = N[N2_index]
            length = self._node_distance(connection.nodes[i].name, connection.nodes[i+1].name, N)
            if length == 0:
                continue
            dl[N1_index*self.dim : N1_index*self.dim + self.dim] += (N1 - N2) / length
            dl[N2_index*self.dim : N2_index*self.dim + self.dim] += (N2 - N1) / length

        return dl

    def _connection_length(self, connection: Connection, N: np.ndarray) -> float:
        """
        Calculates the current length of a connection based on the node positions.

        Args:
            connection (Connection): The connection object.
            N (np.ndarray): The current positions of all nodes.

        Returns:
            float: The current length of the connection.
        """
        length = 0
        for i in range(len(connection.nodes) - 1):
            length += self._node_distance(connection.nodes[i].name, connection.nodes[i+1].name, N)
        return length

    def _node_distance(self, node1: str, node2: str, N: np.ndarray) -> float:
        """
        Calculates the distance between two nodes based on their positions.

        Args:
            node1 (str): The name of the first node.
            node2 (str): The name of the second node.
            N (np.ndarray): The current positions of all nodes.

        Returns:
            float: The distance between the two nodes.
        """
        N1 = N[self.node_indices[node1]]
        N2 = N[self.node_indices[node2]]

        if self.tensegrity.surface:
            if {node1, node2} in self.tensegrity.surface.linked_nodes:
                return 0

        return np.linalg.norm(N1 - N2)

    def _surface_constraints(self, x: np.ndarray) -> np.ndarray:
        """
        Computes the surface constraints for the optimization problem.

        Args:
            x (np.ndarray): The input array representing the current state of the nodes.

        Returns:
            np.ndarray: An array of constraints that must be satisfied. For a cylindrical surface, 
                        the constraints ensure that:
                        - The y-coordinates of linked nodes are equal.
                        - The x-coordinates of linked nodes are exactly the circumference of the cylinder apart.
        """
        N = self._get_nodes_from_input(x)

        constraints = []
        if self.tensegrity.surface.shape["surface_type"] == "cylinder":
            r = self.tensegrity.surface.shape["properties"]["radius"]
            for node1, node2 in self.tensegrity.surface.linked_nodes:
                N1 = N[self.node_indices[node1]]
                N2 = N[self.node_indices[node2]]
                constraints.append(N1[1] - N2[1]) # y values must be the same
                constraints.append(np.abs(N1[0] - N2[0]) - 2*np.pi*r) # x values must be exactly the circumference of the cylinder apart

        return np.array(constraints)


    def _create_initial_guess(self) -> np.ndarray:
        """
        Creates the input vector x0 for the optimization problem (node positions - pinned nodes).

        Returns:
            np.ndarray: The input vector x0. 
                        length = d*len(nodes) - pins, Elements are the node positions (except those that are pinned)
        """
        x0 = np.array([node.position[:self.dim] for node in self.tensegrity.nodes]).flatten() # position of the nodes

        x0 = np.delete(x0, [self.node_indices[node]*self.dim + i for node, bools in self.tensegrity.pins.items() for i in range(self.dim) if bools[i]])

        return x0

    def _get_nodes_from_input(self, x: np.ndarray) -> np.ndarray:
        """
        Extracts node positions input vector (adding the pinned nodes back in).

        Args:
            x (np.ndarray): The input vector containing node positions.

        Returns:
            np.ndarray: The extracted node positions including those removed from the input because they were pinned.
        """
        ins_index = {}
        for node, bools in self.tensegrity.pins.items():
            index = self.node_indices[node]*self.dim
            for i in range(self.dim):
                if bools[i]:
                    ins_index[index + i] = self.tensegrity.nodes[self.node_indices[node]].position[i]
        for index, value in ins_index.items():
            x = np.insert(x, index, value)

        x = x.reshape(-1, self.dim)

        return x
