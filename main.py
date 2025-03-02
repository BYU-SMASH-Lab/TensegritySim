import argparse

from TensegritySim import YamlParser, Visualization, TensegritySolver

def main(file):
    # Load the tensegrity system from the YAML file
    tensegrity_system = YamlParser.parse(file)

    # Create the visualization object
    viz = Visualization(tensegrity_system)

    # Plot the initial tensegrity system
    viz.plot(label_nodes=True, label_connections=True)

    # Solve the tensegrity system
    solver = TensegritySolver(tensegrity_system)
    solver.solve()
    
    viz.plot(label_nodes=True, label_connections=True)

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
            viz.plot(label_nodes=True, label_connections=True, label_forces=show_forces)
            continue
        else:
            delta_lengths = user_input.split(",")
            delta_lengths = [float(delta) for delta in delta_lengths]
            tensegrity_system.change_control_lengths(*delta_lengths)

        solver.solve()
        viz.plot(label_nodes=True, label_connections=True, label_forces=show_forces)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="2D Tensegrity Simulator")
    parser.add_argument("filename", help="YAML file to load", default="yaml/1-box.yaml")

    args = vars(parser.parse_args())
    main(file=args["filename"])
