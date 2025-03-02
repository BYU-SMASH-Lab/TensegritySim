import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits import mplot3d
from .data_structures import Tensegrity, Connection

class Visualization:
    """
    Visualization class for tensegrity structures.

    This class provides methods to visualize 2D and 3D tensegrity structures using matplotlib.

    Attributes:
        tensegrity (Tensegrity): The tensegrity structure to visualize.
        fig (Figure): Matplotlib figure object.
        ax (Axes): Matplotlib axes object.
        dim (int): Dimension of the visualization (2, 2.5 or 3), set by the dim of the tensegrity.
    """

    def __init__(self, tensegrity: Tensegrity, dim: int = None):
        """
        Initializes a Visualization object.

        Args:
            tensegrity (Tensegrity): The tensegrity structure to visualize.
            dim (int, optional): The dimension of the visualization. Defaults to None, which matches the dim of tensegrity.

        Raises:
            ValueError: If the dimension is not 2, 2.5, or 3.
        """
        self.tensegrity = tensegrity

        if dim is None:
            self.dim = tensegrity.dim
        else:
            self.dim = dim

        if self.dim == 2:
            self.fig, self.ax = plt.subplots()
        elif self.dim == 3 or self.dim == 2.5:
            self.fig, self.ax = plt.subplots(subplot_kw={"projection": "3d"})
        else:
            raise ValueError("Invalid dimension. Must be 2, 2.5, or 3.")

    def plot(self, label_nodes: bool = False, label_connections: bool = False, label_forces: bool = False):
        """
        Plots the visualization of the tensegrity structure.

        Args:
            label_nodes (bool, optional): Whether to label the node names in the plot. Defaults to False.
            label_connections (bool, optional): Whether to label the connection names in the plot. Defaults to False.
            label_forces (bool, optional): Whether to label the forces on the connections. Defaults to False.
        """
        if self.dim == 3:
            self._plot_3d(label_nodes, label_connections, label_forces)
        elif self.dim == 2.5:
            self._plot_2_5d(label_nodes, label_connections, label_forces)
        else:
            self._plot_2d(label_nodes, label_connections, label_forces)

    def _plot_2d(self, label_nodes: bool = False, label_connections: bool = False, label_forces: bool = False):
        """
        Plots the 2D visualization of the tensegrity structure.

        Args:
            label_nodes (bool, optional): Whether to label the node names in the plot. Defaults to False.
            label_connections (bool, optional): Whether to label the connection names in the plot. Defaults to False.
            label_forces (bool, optional): Whether to label the forces on the connections. Defaults to False.
        """
        self.ax.clear()
        self.ax.set_aspect("equal")
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        color_index = 1 # Using "CN" color cycle
        color_names = {}

        # --- Plot connections ---
        for connection in self.tensegrity.connections:
            # Strings are dashed lines
            if connection.connection_type == Connection.ConnectionType.STRING:
                # Set color
                color = "k"
                if connection.name or len(connection.nodes) > 2:
                    color = f"C{color_index}"
                    if connection.name:
                        color_names[connection.name] = color_index
                    color_index += 1

                style = "--" if connection.force > 1e-3 else ":"
                # Plot line
                self.ax.plot([node.position[0] for node in connection.nodes], [node.position[1] for node in connection.nodes], f"{color}{style}")

            # Bars are solid lines
            elif connection.connection_type == Connection.ConnectionType.BAR:
                style = "-" if np.abs(connection.force) > 1e-3 else "-."
                self.ax.plot([connection.nodes[0].position[0], connection.nodes[1].position[0]], [connection.nodes[0].position[1], connection.nodes[1].position[1]], f"k{style}")

        # --- plot nodes and label ---
        for node in self.tensegrity.nodes:
            # TODO: How to differentiate between 1D and 2D pinning?
            if node.name in self.tensegrity.pins:
                self.ax.plot(node.position[0], node.position[1], "rX")
            else:
                self.ax.plot(node.position[0], node.position[1], "ko")
            if label_nodes:
                self.ax.annotate(node.name, (node.position[0], node.position[1]), (.2, .2), textcoords="offset fontsize")

        if label_forces:
            for connection in self.tensegrity.connections:
                if connection.name:
                    self.ax.annotate(f"{connection.name}: {connection.force:.2f}", ((connection.nodes[0].position[0] + connection.nodes[1].position[0])/2, (connection.nodes[0].position[1] + connection.nodes[1].position[1])/2), ha="center")
                else:
                    self.ax.annotate(f"{connection.force:.2f}", ((connection.nodes[0].position[0] + connection.nodes[1].position[0])/2, (connection.nodes[0].position[1] + connection.nodes[1].position[1])/2), ha="center")
        elif label_connections:
            for connection in self.tensegrity.connections:
                if connection.name:
                    self.ax.annotate(connection.name, ((connection.nodes[0].position[0] + connection.nodes[1].position[0])/2, (connection.nodes[0].position[1] + connection.nodes[1].position[1])/2), ha="center")

        self.fig.show()

    def _plot_3d(self, label_nodes: bool = False, label_connections: bool = False, label_forces: bool = False):
        """
        Plots the 3D visualization of the tensegrity structure.

        Args:
            label_nodes (bool, optional): Whether to label the node names in the plot. Defaults to False.
            label_connections (bool, optional): Whether to label the connection names in the plot. Defaults to False.
            label_forces (bool, optional): Whether to label the forces on the connections. Defaults to False.
        """
        self.ax.clear()
        self.ax.set_box_aspect([1.0,1.0,1.0])
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_zlabel("Z")
        color_index = 1 # Using "CN" color cycle
        color_names = {}

        # --- plot nodes ---
        for node in self.tensegrity.nodes:
            if node.name in self.tensegrity.pins:
                self.ax.plot3D(*node.position, "rX")
            else:
                self.ax.plot3D(*node.position, "ko")

            if label_nodes:
                self.ax.text(*node.position, node.name)

        # --- Plot connections ---
        for connection in self.tensegrity.connections:
            # Strings are dashed lines
            if connection.connection_type == Connection.ConnectionType.STRING:
                # Set color
                color = "k"
                if connection.name or len(connection.nodes) > 2:
                    color = f"C{color_index}"
                    if connection.name:
                        color_names[connection.name] = color_index
                    color_index += 1

                style = "--" if connection.force > 1e-3 else ":"
                # Plot line
                positions = np.array([node.position for node in connection.nodes])
                self.ax.plot3D(positions[:, 0], positions[:, 1], positions[:, 2], f"{color}{style}")

            # Bars are solid lines
            elif connection.connection_type == Connection.ConnectionType.BAR:
                style = "-" if np.abs(connection.force) > 1e-3 else "-."
                for i in range(len(connection.nodes)-1):
                    positions = np.array([node.position for node in connection.nodes])
                    self.ax.plot3D(positions[:, 0], positions[:, 1], positions[:, 2], f"k{style}")

        # --- label ---
        if label_forces:
            for connection in self.tensegrity.connections:
                if connection.name:
                    self.ax.text(*(connection.nodes[0].position + connection.nodes[1].position)/2, f"{connection.name}: {connection.force:.2f}")
                else:
                    self.ax.text(*(connection.nodes[0].position + connection.nodes[1].position)/2, f"{connection.force:.2f}")
        elif label_connections:
            for connection in self.tensegrity.connections:
                if connection.name:
                    self.ax.text(*(connection.nodes[0].position + connection.nodes[1].position)/2, connection.name)

        self.set_3d_equal_scaling(self.ax)
        self.fig.show()

    def _plot_2_5d(self, label_nodes: bool = False, label_connections: bool = False, label_forces: bool = False):
        """
        Plots the 2.5D visualization of the tensegrity structure.

        Args:
            label_nodes (bool, optional): Whether to label the node names in the plot. Defaults to False.
            label_connections (bool, optional): Whether to label the connection names in the plot. Defaults to False.
            label_forces (bool, optional): Whether to label the forces on the connections. Defaults to False.
        """
        self.ax.clear()
        self.ax.set_box_aspect([1.0,1.0,1.0])
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_zlabel("Z")
        color_index = 1 # Using "CN" color cycle
        color_names = {}

        def transform(x, y, z=0):
            if self.tensegrity.surface:
                if self.tensegrity.surface.shape["surface_type"] == "cylinder":
                    self.r = self.tensegrity.surface.shape["properties"]["radius"]
                    return np.array([self.r*np.cos(x/self.r), self.r*np.sin(x/self.r), y])
            return np.array([x, y, z]) # Default to no transformation

        # --- plot nodes ---
        for node in self.tensegrity.nodes:
            if node.name in self.tensegrity.pins:
                self.ax.plot3D(*transform(*node.position), "rX")
            else:
                self.ax.plot3D(*transform(*node.position), "ko")

            if label_nodes:
                self.ax.text(*transform(*node.position), node.name)

        # --- Plot connections ---
        for connection in self.tensegrity.connections:
            # Strings are dashed lines
            if connection.connection_type == Connection.ConnectionType.STRING:
                # Set color
                color = "k"
                if connection.name or len(connection.nodes) > 2:
                    color = f"C{color_index}"
                    if connection.name:
                        color_names[connection.name] = color_index
                    color_index += 1

                style = "--" if connection.force > 1e-3 else ":"
                # Plot line
                # calculate all the points along the line before the transform
                for i in range(len(connection.nodes)-1):
                    # if nodes are linked nodes, continue
                    if {connection.nodes[i].name, connection.nodes[i+1].name} in self.tensegrity.surface.linked_nodes:
                        continue
                    t_values = np.linspace(0, 1, 100)
                    positions = np.array([connection.nodes[i].position, connection.nodes[i+1].position])
                    positions = positions[0] + t_values[:, None] * (positions[1] - positions[0])
                    positions = transform(positions[:, 0], positions[:, 1])
                    self.ax.plot3D(positions[0], positions[1], positions[2], f"{color}{style}")

            # Bars are solid lines
            elif connection.connection_type == Connection.ConnectionType.BAR:
                style = "-" if np.abs(connection.force) > 1e-3 else "-."
                for i in range(len(connection.nodes)-1):
                    t_values = np.linspace(0, 1, 100)
                    positions = np.array([node.position for node in connection.nodes])
                    positions = positions[0] + t_values[:, None] * (positions[1] - positions[0])
                    positions = transform(positions[:, 0], positions[:, 1])

                    self.ax.plot3D(positions[0], positions[1], positions[2], f"k{style}")

        # --- label ---
        if label_forces:
            for connection in self.tensegrity.connections:
                if connection.name:
                    self.ax.text(*(transform(*connection.nodes[0].position) + transform(*connection.nodes[1].position))/2, f"{connection.name}: {connection.force:.2f}")
                else:
                    self.ax.text(*(transform(*connection.nodes[0].position) + transform(*connection.nodes[1].position))/2, f"{connection.force:.2f}")
        elif label_connections:
            for connection in self.tensegrity.connections:
                if connection.name:
                    self.ax.text(*(transform(*connection.nodes[0].position) + transform(*connection.nodes[1].position))/2, connection.name)

        # --- plot surface ---
        if self.tensegrity.surface:
            if self.tensegrity.surface.shape["surface_type"] == "cylinder":
                r = self.tensegrity.surface.shape["properties"]["radius"]
                z_max = -np.inf
                z_min = np.inf
                for node in self.tensegrity.nodes:
                    if transform(*node.position)[2] > z_max:
                        z_max = transform(*node.position)[2]
                    if transform(*node.position)[2] < z_min:
                        z_min = transform(*node.position)[2]
                resolution = 100 # Number of points to plot
                z_min = z_min - 0.2*(z_max - z_min)
                z_max = z_max + 0.2*(z_max - z_min)
                z = np.linspace(z_min, z_max, resolution)
                theta = np.linspace(0, 2*np.pi, resolution)
                theta_grid, z_grid = np.meshgrid(theta, z)
                x_grid = r*np.cos(theta_grid)
                y_grid = r*np.sin(theta_grid)
                self.ax.plot_surface(x_grid, y_grid, z_grid, alpha=0.25, color="gray")
        self.set_3d_equal_scaling(self.ax)
        self.fig.show()

    def set_3d_equal_scaling(self, ax):
        """
        Sets equal scaling for the 3D plot.

        Args:
            ax (Axes3D): The 3D axes object.
        """
        x_limits = ax.get_xlim3d()
        y_limits = ax.get_ylim3d()
        z_limits = ax.get_zlim3d()

        x_range = abs(x_limits[1] - x_limits[0])
        y_range = abs(y_limits[1] - y_limits[0])
        z_range = abs(z_limits[1] - z_limits[0])

        max_range = max(x_range, y_range, z_range)

        x_middle = sum(x_limits) / 2
        y_middle = sum(y_limits) / 2
        z_middle = sum(z_limits) / 2

        ax.set_xlim3d([x_middle - max_range / 2, x_middle + max_range / 2])
        ax.set_ylim3d([y_middle - max_range / 2, y_middle + max_range / 2])
        ax.set_zlim3d([z_middle - max_range / 2, z_middle + max_range / 2])
