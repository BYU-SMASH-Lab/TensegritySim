import argparse

from TensegritySim import YamlParser, Visualization, TensegritySolver


def _print_requested_positions(tensegrity_system):
    if not tensegrity_system.positions:
        return

    nodes_by_name = {node.name: node for node in tensegrity_system.nodes}
    for node_name in tensegrity_system.positions:
        node = nodes_by_name[node_name]
        position = node.position[1]
        print(f"{position:.2f}")

def main(file):
    # Load the tensegrity system from the YAML file
    tensegrity_system = YamlParser.parse(file)

    # Create the visualization object
    if tensegrity_system.surface:
        viz = Visualization(tensegrity_system, dim=3)
    else:
        viz = Visualization(tensegrity_system, dim=2)


    # Plot the initial tensegrity system
    viz.plot(label_nodes=False, label_connections=True)

    # Solve the tensegrity system
    solver = TensegritySolver(tensegrity_system, dim=2)
    solver.solve()
    viz.plot(label_nodes=False, label_connections=True)
    _print_requested_positions(tensegrity_system)

    show_forces = False

    print("Enter 'q' to quit.")
    print("Enter 'r' to reset control lengths.")
    print("Enter 'f' to show/hide forces.")
    if len(tensegrity_system.controls) == 1:
        print(f"Enter changes in length to control {tensegrity_system.get_control_order()} to update simulation.")
    else:
        print(f"Enter changes in length to control strings as comma-separated values in the order of: {tensegrity_system.get_control_order()} to update simulation.")

    while True:
        user_input = input("Input: ")
        if user_input == "q":
            break
        elif user_input == "r":
            tensegrity_system.reset_control_lengths()
        elif user_input == "f":
            show_forces = not show_forces
            viz.plot(label_nodes=False, label_connections=True, label_forces=show_forces)
            continue
        else:
            delta_lengths = user_input.split(",")
            delta_lengths = [float(delta) for delta in delta_lengths]
            tensegrity_system.change_control_lengths(*delta_lengths)

        solver.solve()
        viz.plot(label_nodes=False, label_connections=True, label_forces=show_forces)
        _print_requested_positions(tensegrity_system)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="2D Tensegrity Simulator")
    parser.add_argument("filename", help="YAML file to load", default="yaml/1-box.yaml")

    args = vars(parser.parse_args())
    main(file=args["filename"])
