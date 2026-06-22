import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits import mplot3d
from mpl_toolkits.mplot3d import proj3d
from .data_structures import Tensegrity, Connection

class Visualization:
    """
    Visualization class for tensegrity structures.

    This class provides methods to visualize 2D and 3D tensegrity structures using matplotlib.

    Attributes:
        tensegrity (Tensegrity): The tensegrity structure to visualize.
        dim (int): Dimension of the visualization (2 or 3).
        fig (Figure): Matplotlib figure object.
        ax (Axes): Matplotlib axes object.
    """
    def __init__(self, tensegrity: Tensegrity, dim: int = 2):
        """
        Initializes a Visualization object.

        Args:
            tensegrity (Tensegrity): The tensegrity structure to visualize.
            dim (int): The dimension of the visualization (default is 2).

        Raises:
            ValueError: If the dimension is not 2 or 3.
        """
        self.tensegrity = tensegrity

        self.dim = dim

        if dim == 2:
            self.fig, self.ax = plt.subplots()
        elif dim == 3:
            self.fig, self.ax = plt.subplots(subplot_kw={"projection": "3d"})
        else:
            raise ValueError("Invalid dimension. Must be 2 or 3.")

        # Hover tooltip state for node positions.
        self._hover_threshold_px = 20.0
        self._hover_transform = None
        self._hover_annotation = None
        self._node_hover_artists = []
        self._node_hover_info = {}
        self._view_initialized = False
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_hover)
        self.fig.canvas.mpl_connect("scroll_event", self._on_scroll)

        # assign distinct colors for control connections
        self.control_colors = {}
        try:
            controls = list(self.tensegrity.controls)
        except Exception:
            controls = []
        if controls:
            # Use a bright rainbow colormap for control connections
            cmap = plt.get_cmap('rainbow')
            n = len(controls)
            for i, control in enumerate(controls):
                # store by object id so we can match the exact Connection instances
                self.control_colors[id(control)] = cmap(float(i) / max(1, n - 1))

    def plot(self, label_nodes: bool = False, label_connections: bool = False, label_forces: bool = False):
        """
        Plots the visualization of the tensegrity structure.

        Args:
            label_nodes (bool): Whether to label the node names in the plot. Default is False.
            label_connections (bool): Whether to label the connection names in the plot. Default is False.
            label_forces (bool): Whether to label the forces on the connections. Default is False.
        """
        if self.dim == 3:
            self._plot_3d(label_nodes, label_connections, label_forces)
        else:
            self._plot_2d(label_nodes, label_connections, label_forces)

    @staticmethod
    def _grayscale_from_distance(distance: float, min_distance: float, max_distance: float) -> tuple:
        """
        Maps a reference-distance value to a grayscale color.

        Args:
            distance (float): The distance value to convert.
            min_distance (float): The minimum distance in the current plot.
            max_distance (float): The maximum distance in the current plot.

        Returns:
            tuple: An RGBA color tuple suitable for matplotlib.
        """
        if np.isclose(max_distance, min_distance):
            shade = 0.55
        else:
            normalized_distance = float(np.clip((distance - min_distance) / (max_distance - min_distance), 0.0, 1.0))
            shade = 0.18 + 0.62 * normalized_distance
        return (shade, shade, shade, 1.0)

    @staticmethod
    def _camera_direction(elev: float, azim: float) -> np.ndarray:
        """
        Returns a unit vector that points from the scene center toward the camera.

        Args:
            elev (float): Camera elevation in degrees.
            azim (float): Camera azimuth in degrees.

        Returns:
            np.ndarray: A unit vector describing the camera direction.
        """
        elev_radians = np.deg2rad(elev)
        azim_radians = np.deg2rad(azim)
        direction = np.array([
            np.cos(elev_radians) * np.cos(azim_radians),
            np.cos(elev_radians) * np.sin(azim_radians),
            np.sin(elev_radians),
        ], dtype=float)
        direction_norm = np.linalg.norm(direction)
        if np.isclose(direction_norm, 0.0):
            return np.array([1.0, 0.0, 0.0], dtype=float)
        return direction / direction_norm

    @staticmethod
    def _camera_position(points: np.ndarray, elev: float, azim: float) -> np.ndarray:
        """
        Computes a virtual camera position for shading.

        Args:
            points (np.ndarray): Point cloud used to estimate the scene center and scale.
            elev (float): Camera elevation in degrees.
            azim (float): Camera azimuth in degrees.

        Returns:
            np.ndarray: The camera position in scene coordinates.
        """
        if points.size == 0:
            return np.array([0.0, 0.0, 1.0], dtype=float)

        bounds_min = np.min(points, axis=0)
        bounds_max = np.max(points, axis=0)
        center = (bounds_min + bounds_max) / 2.0
        scene_radius = float(max(np.linalg.norm(bounds_max - bounds_min), 1.0))
        return center + Visualization._camera_direction(elev, azim) * scene_radius

    @staticmethod
    def _connection_distance(connection: Connection, camera_position: np.ndarray, transform=None) -> float:
        """
        Returns a representative camera distance for a connection.

        Args:
            connection (Connection): The connection to measure.
            camera_position (np.ndarray): Camera position in scene coordinates.
            transform (callable | None): Optional point transform used for surface-backed plots.

        Returns:
            float: The average distance from the camera to the connection nodes.
        """
        positions = []
        for node in connection.nodes:
            if transform:
                positions.append(transform(*node.position))
            else:
                positions.append(node.position)
        return float(np.mean([np.linalg.norm(position - camera_position) for position in positions]))

    @staticmethod
    def _connection_xdistance(connection: Connection, ref_x: float, transform=None) -> float:
        """
        Returns the representative distance in the X dimension for a connection
        relative to a reference x-coordinate.

        Args:
            connection (Connection): The connection to measure.
            ref_x (float): Reference x-coordinate to measure distance from.
            transform (callable | None): Optional transform for surface-backed plots.

        Returns:
            float: The average absolute x-distance from the reference for the connection nodes.
        """
        xs = []
        for node in connection.nodes:
            if transform:
                pos = transform(*node.position)
                x = float(pos[0])
            else:
                x = float(node.position[0])
            xs.append(abs(x - float(ref_x)))
        if len(xs) == 0:
            return 0.0
        return float(np.mean(xs))

    @staticmethod
    def _format_position(position: np.ndarray) -> str:
        """Formats a node position for the hover tooltip."""
        values = np.asarray(position, dtype=float).ravel()
        formatted = ", ".join(f"{value:.3f}" for value in values)
        return f"({formatted})"

    def _ensure_hover_annotation(self):
        """Recreates the hover annotation after axes clears, if needed."""
        if self._hover_annotation is None or self._hover_annotation.axes is not self.ax:
            self._hover_annotation = self.ax.annotate(
                "",
                xy=(0.0, 0.0),
                xytext=(10, 10),
                textcoords="offset points",
                fontsize=10,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", alpha=0.85),
            )
            self._hover_annotation.set_zorder(1000)
            self._hover_annotation.set_visible(False)

    def _capture_view_state(self):
        """Captures the current axes view so redraws preserve zoom and angle."""
        if not self._view_initialized:
            return None
        if self.dim == 3:
            return {
                "xlim": self.ax.get_xlim3d(),
                "ylim": self.ax.get_ylim3d(),
                "zlim": self.ax.get_zlim3d(),
                "elev": float(getattr(self.ax, "elev", 30.0)),
                "azim": float(getattr(self.ax, "azim", -60.0)),
            }
        return {
            "xlim": self.ax.get_xlim(),
            "ylim": self.ax.get_ylim(),
        }

    def _restore_view_state(self, view_state):
        """Restores a previously captured axes view."""
        if not view_state:
            return
        if self.dim == 3:
            self.ax.set_xlim3d(view_state["xlim"])
            self.ax.set_ylim3d(view_state["ylim"])
            self.ax.set_zlim3d(view_state["zlim"])
            self.ax.view_init(elev=view_state["elev"], azim=view_state["azim"])
        else:
            self.ax.set_xlim(view_state["xlim"])
            self.ax.set_ylim(view_state["ylim"])

    def _set_initial_view(self, positions: np.ndarray):
        """Sets a reasonable initial view from plotted node positions."""
        if positions.size == 0:
            return
        bounds_min = np.min(positions, axis=0)
        bounds_max = np.max(positions, axis=0)
        span = bounds_max - bounds_min
        max_span = float(max(np.max(span), 1.0))
        padding = 0.15 * max_span

        if self.dim == 3:
            self.ax.set_xlim3d(bounds_min[0] - padding, bounds_max[0] + padding)
            self.ax.set_ylim3d(bounds_min[1] - padding, bounds_max[1] + padding)
            self.ax.set_zlim3d(bounds_min[2] - padding, bounds_max[2] + padding)
            self.ax.view_init(elev=30.0, azim=-60.0)
        else:
            self.ax.set_xlim(bounds_min[0] - padding, bounds_max[0] + padding)
            self.ax.set_ylim(bounds_min[1] - padding, bounds_max[1] + padding)

    def _on_scroll(self, event):
        """Zooms the plot using the mouse wheel."""
        if event.inaxes != self.ax:
            return

        zoom_factor = 0.9 if getattr(event, "button", None) == "up" else 1.1

        if self.dim == 2:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            center_x = event.xdata if event.xdata is not None else sum(xlim) / 2.0
            center_y = event.ydata if event.ydata is not None else sum(ylim) / 2.0
            new_width = (xlim[1] - xlim[0]) * zoom_factor
            new_height = (ylim[1] - ylim[0]) * zoom_factor
            self.ax.set_xlim(center_x - new_width / 2.0, center_x + new_width / 2.0)
            self.ax.set_ylim(center_y - new_height / 2.0, center_y + new_height / 2.0)
        else:
            xlim = self.ax.get_xlim3d()
            ylim = self.ax.get_ylim3d()
            zlim = self.ax.get_zlim3d()
            center_x = sum(xlim) / 2.0
            center_y = sum(ylim) / 2.0
            center_z = sum(zlim) / 2.0
            new_x = (xlim[1] - xlim[0]) * zoom_factor
            new_y = (ylim[1] - ylim[0]) * zoom_factor
            new_z = (zlim[1] - zlim[0]) * zoom_factor
            self.ax.set_xlim3d(center_x - new_x / 2.0, center_x + new_x / 2.0)
            self.ax.set_ylim3d(center_y - new_y / 2.0, center_y + new_y / 2.0)
            self.ax.set_zlim3d(center_z - new_z / 2.0, center_z + new_z / 2.0)

        self._view_initialized = True
        self.fig.canvas.draw_idle()

    def _register_hover_artist(self, artist, anchor, text):
        """Registers a node marker for hover hit-testing."""
        self._node_hover_artists.append(artist)
        self._node_hover_info[id(artist)] = {"anchor": anchor, "text": text}

    def _project_3d_point(self, position: np.ndarray) -> tuple:
        """Projects a 3D point into 2D axes coordinates for annotation placement."""
        proj_x, proj_y, _ = proj3d.proj_transform(position[0], position[1], position[2], self.ax.get_proj())
        return float(proj_x), float(proj_y)

    def _refresh_hover_targets_2d(self):
        """No-op placeholder kept for compatibility with older hover code."""
        return

    def _refresh_hover_targets_3d(self, transform):
        """No-op placeholder kept for compatibility with older hover code."""
        return

    def _on_hover(self, event):
        """Shows node position when cursor hovers near a node."""
        if event.inaxes != self.ax or event.x is None or event.y is None:
            if self._hover_annotation is not None and self._hover_annotation.get_visible():
                self._hover_annotation.set_visible(False)
                self.fig.canvas.draw()
            return

        for artist in self._node_hover_artists:
            contains, _ = artist.contains(event)
            if contains:
                info = self._node_hover_info.get(id(artist))
                if info is None:
                    continue
                self._ensure_hover_annotation()
                self._hover_annotation.xy = info["anchor"]
                self._hover_annotation.set_text(info["text"])
                self._hover_annotation.set_visible(True)
                self.fig.canvas.draw()
                return

        if self._hover_annotation is not None and self._hover_annotation.get_visible():
            self._hover_annotation.set_visible(False)
            self.fig.canvas.draw()

    def _plot_2d(self, label_nodes: bool = False, label_connections: bool = False, label_forces: bool = False):
        """
        Plots the 2D visualization of the tensegrity structure.

        Args:
            label_nodes (bool): Whether to label the node names in the plot. Default is False.
            label_connections (bool): Whether to label the connection names in the plot. Default is False.
            label_forces (bool): Whether to label the forces on the connections. Default is False.
        """
        view_state = self._capture_view_state()
        self.ax.clear()
        self._ensure_hover_annotation()
        self._hover_transform = None
        self._node_hover_artists = []
        self._node_hover_info = {}
        self.ax.set_aspect("equal")
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        node_positions = np.array([node.position for node in self.tensegrity.nodes], dtype=float)
        # Use the first node in the YAML as the reference x for shading
        if len(self.tensegrity.nodes) > 0:
            ref_x = float(self.tensegrity.nodes[0].position[0])
        else:
            ref_x = 0.0
        node_depths = np.array([abs(float(node.position[0]) - ref_x) for node in self.tensegrity.nodes], dtype=float)
        connection_depths = np.array([self._connection_xdistance(connection, ref_x) for connection in self.tensegrity.connections], dtype=float)
        node_depth_min = float(np.min(node_depths)) if len(node_depths) else 0.0
        node_depth_max = float(np.max(node_depths)) if len(node_depths) else 1.0
        connection_depth_min = float(np.min(connection_depths)) if len(connection_depths) else 0.0
        connection_depth_max = float(np.max(connection_depths)) if len(connection_depths) else 1.0

        # --- Plot connections ---
        for connection_index, connection in enumerate(self.tensegrity.connections):
            color = self._grayscale_from_distance(connection_depths[connection_index], connection_depth_min, connection_depth_max)
            # Strings are dashed lines
            if connection.connection_type == Connection.ConnectionType.STRING:
                style = "--" if connection.force > 1e-3 else ":"
                # use control color if this connection is a control
                if id(connection) in self.control_colors:
                    plot_color = self.control_colors[id(connection)]
                else:
                    plot_color = color
                # Plot line
                self.ax.plot([node.position[0] for node in connection.nodes], [node.position[1] for node in connection.nodes], linestyle=style, color=plot_color)


            # Bars are solid lines
            elif connection.connection_type == Connection.ConnectionType.BAR:
                style = "-" if np.abs(connection.force) > 1e-3 else "-."
                self.ax.plot([connection.nodes[0].position[0], connection.nodes[1].position[0]], [connection.nodes[0].position[1], connection.nodes[1].position[1]], linestyle=style, color=color)

        # --- plot nodes as points; labels are optional ---
        for node_index, node in enumerate(self.tensegrity.nodes):
            # TODO: How to differentiate between 1D and 2D pinning?
            color = self._grayscale_from_distance(node_depths[node_index], node_depth_min, node_depth_max)
            if node.name in self.tensegrity.pins:
                node_artist = self.ax.scatter([node.position[0]], [node.position[1]], marker="X", color=color, s=80, picker=True)
            else:
                node_artist = self.ax.scatter([node.position[0]], [node.position[1]], marker="o", color=color, s=36, picker=True)
            self._register_hover_artist(
                node_artist,
                anchor=(node.position[0], node.position[1]),
                text=f"{node.name}: {self._format_position(node.position)}",
            )
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

        self._restore_view_state(view_state)
        if view_state is None:
            self._set_initial_view(node_positions)
        self._view_initialized = True
        self._refresh_hover_targets_2d()


        self.fig.show()

    def _plot_3d(self, label_nodes: bool = False, label_connections: bool = False, label_forces: bool = False):
        """
        Plots the 3D visualization of the tensegrity structure.

        Args:
            label_nodes (bool): Whether to label the node names in the plot. Default is False.
            label_connections (bool): Whether to label the connection names in the plot. Default is False.
            label_forces (bool): Whether to label the forces on the connections. Default is False.
        """
        view_state = self._capture_view_state()
        self.ax.clear()
        self._ensure_hover_annotation()
        self.ax.set_box_aspect([1.0,1.0,1.0])
        self._node_hover_artists = []
        self._node_hover_info = {}
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_zlabel("Z")

        def transform(x, y, z=0):
            if self.tensegrity.surface:
                if self.tensegrity.surface.shape["surface_type"] == "cylinder":
                    self.r = self.tensegrity.surface.shape["properties"]["radius"]
                    return np.array([self.r*np.cos(x/self.r), self.r*np.sin(x/self.r), y])
            return np.array([x, y, z]) # Default to no transformation

        self._hover_transform = transform

        node_positions = np.array([transform(*node.position) for node in self.tensegrity.nodes], dtype=float)
        # Use the first node in the YAML (transformed) as the reference x for shading
        if len(self.tensegrity.nodes) > 0:
            ref_x = float(transform(*self.tensegrity.nodes[0].position)[0])
        else:
            ref_x = 0.0
        node_depths = np.array([abs(transform(*node.position)[0] - ref_x) for node in self.tensegrity.nodes], dtype=float)
        connection_depths = np.array([self._connection_xdistance(connection, ref_x, transform) for connection in self.tensegrity.connections], dtype=float)
        node_depth_min = float(np.min(node_depths)) if len(node_depths) else 0.0
        node_depth_max = float(np.max(node_depths)) if len(node_depths) else 1.0
        connection_depth_min = float(np.min(connection_depths)) if len(connection_depths) else 0.0
        connection_depth_max = float(np.max(connection_depths)) if len(connection_depths) else 1.0

        # --- plot nodes as points; labels are optional ---
        for node_index, node in enumerate(self.tensegrity.nodes):
            color = self._grayscale_from_distance(node_depths[node_index], node_depth_min, node_depth_max)
            if node.name in self.tensegrity.pins:
                node_artist = self.ax.scatter([transform(*node.position)[0]], [transform(*node.position)[1]], [transform(*node.position)[2]], marker="X", color=color, s=80, picker=True)
            else:
                node_artist = self.ax.scatter([transform(*node.position)[0]], [transform(*node.position)[1]], [transform(*node.position)[2]], marker="o", color=color, s=36, picker=True)
            projected_xy = self._project_3d_point(transform(*node.position))
            self._register_hover_artist(
                node_artist,
                anchor=projected_xy,
                text=f"{node.name}: {self._format_position(transform(*node.position))}",
            )
            if label_nodes:
                self.ax.text(*transform(*node.position), node.name)

        # --- Plot connections ---
        for connection_index, connection in enumerate(self.tensegrity.connections):
            color = self._grayscale_from_distance(connection_depths[connection_index], connection_depth_min, connection_depth_max)
            # Strings are dashed lines
            if connection.connection_type == Connection.ConnectionType.STRING:
                style = "--" if connection.force > 1e-3 else ":"
                # Plot line
                # calculate all the points along the line before the transform
                if self.tensegrity.surface:
                    for i in range(len(connection.nodes)-1):
                        # if nodes are linked nodes, continue
                        if {connection.nodes[i].name, connection.nodes[i+1].name} in self.tensegrity.surface.linked_nodes:
                            continue
                        t_values = np.linspace(0, 1, 100)
                        x_values = connection.nodes[i].position[0] + t_values*(connection.nodes[i+1].position[0] - connection.nodes[i].position[0])
                        y_values = connection.nodes[i].position[1] + t_values*(connection.nodes[i+1].position[1] - connection.nodes[i].position[1])
                        positions = transform(x_values, y_values)
                        plot_color = self.control_colors.get(id(connection), color)
                        self.ax.plot3D(positions[0], positions[1], positions[2], linestyle=style, color=plot_color)
                else:
                    positions = [transform(node.position[0], node.position[1], node.position[2]) for node in connection.nodes]
                    plot_color = self.control_colors.get(id(connection), color)
                    self.ax.plot3D([pos[0] for pos in positions], [pos[1] for pos in positions], [pos[2] for pos in positions], linestyle=style, color=plot_color)

            # Bars are solid lines
            elif connection.connection_type == Connection.ConnectionType.BAR:
                style = "-" if np.abs(connection.force) > 1e-3 else "-."
                for i in range(len(connection.nodes)-1):
                    t_values = np.linspace(0, 1, 100)
                    x_values = connection.nodes[i].position[0] + t_values*(connection.nodes[i+1].position[0] - connection.nodes[i].position[0])
                    y_values = connection.nodes[i].position[1] + t_values*(connection.nodes[i+1].position[1] - connection.nodes[i].position[1])
                    positions = transform(x_values, y_values)
                    self.ax.plot3D(positions[0], positions[1], positions[2], linestyle=style, color=color)

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
        self._restore_view_state(view_state)
        if view_state is None:
            self._set_initial_view(node_positions)
        self._view_initialized = True
        self._refresh_hover_targets_3d(transform)
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
