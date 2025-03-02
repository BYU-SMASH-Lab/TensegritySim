# YAML Reference <!-- omit from toc -->
The config file is a YAML file defining:
- [Nodes](#nodes)
- [Connections](#connections)
- [Builders](#builders)
- [Pins](#pins)
- [Control](#control)
- [Surface](#surface)
  - [Type](#type)
  - [Linked Nodes](#linked-nodes)

These sections can be defined in any order in the YAML file, but it is easiest to logically go through them in the order defined above.

There are sample config files in the `yaml` directory.

## Nodes
Nodes are the points that bars and strings connect at.

Nodes have a name and initial x, y, z positions.  
A node named `Node1` with x = 1, y = 2, and z = 0, it would look like:

```yaml
nodes:
    Node1: [1, 2, 0]
```

The Tensegrity class sets the number of dimensions to 2 or 3 based on the number of coordinates given for the nodes. If all nodes have 3 coordinates, the structure is solved in 3D space. If any nodes have only 2 coordinates, the structure is solved in 2D space.

## Connections
Connections are how the nodes are connected to each other. There can be unlimited connection types, with each connection type having different properties as defined in the [Builders](#builders) section.

A connection type named `strings` with a connection between `Node1` and `Node2` looks like:

```yaml
connections:
    strings:
        - [Node1, Node2]
```

Connections can also optionally be named (for later specifying connections to control).

```yaml
connections:
    strings:
        - string1: [Node1, Node2] # Named connection
        - [Node2, Node3] # Unnamed connection
```

String connections (as defined in the builders section) can pass through multiple nodes. They are assumed to frictionlessly pass through nodes and therefore always have the same tension along it's entire length.

```yaml
connections:
    strings:
        - string1: [Node1, Node2, Node5, Node6]
```

## Builders
Builders are the connection properties that define the strings or bars that hold the nodes together.
A builder must have a name matching a connection type in the `Connections` section.

For the `string` connection type with a stiffness (k) of 100N/m (it is actually unitless, but it helps me to think of everything in terms of metric units) and the unstretched length of the string 95% of the currently defined length between nodes:

```yaml
builders:
    strings:
        stiffness: 100
        type: string
        initial_length_ratio: 0.95
```

If the unstretched length of the string is unknown but the tension is known, Hooke's Law can be used to calculate the initial length: $F = k * (l_s - l)$ where $l_s$ is the stretched length of the string (distance between it's nodes) and $l$ is the unstretched length.

Bars are defined in the builder's sections just like strings. The `initial_length_ratio` is normally left out because bars are usually significantly stiff enough it is assumed to be 1

```yaml
builders:
    bars:
        stiffness: 10000
        type: bar
```
**Important**: The name of each builder can be what ever the user desires (bars, strings, high_tension_strings, blue_string, red_springs, etc), but the defined type in each must be exactly `bar` or `string`

## Pins
In 2D space the solved structure can float anywhere in the XY plane with any rotation unless we pin nodes (to define a place in XY space the structure is fixed to)

A pin needs a node name and a list of True/False values, with True indicating that the node is translationally pinned in that direction. To pin `Node1` in the x and y directions:
```yaml
pin:
  Node1: [True, True, False]
```

## Control
The `control` section defines which strings are able to be controlled (change length).

To define a control string the name of the connections need to be defined. For instance if the connection `String1` is being controlled:
```yaml
control:
  - String1
```

## Surface
### Type
The only type of surface currently implemented is a cylinder. A radius must be specified for the radius of the cylinder to wrap the tensegrity around.

The structure is wrapped around a $\hat{k}$ axis. In other words the x-axis wraps the circumference of the cylinder with a set radius, r. In the future I hope we can define the radius to change as a function of the z height, either with an equation, or reading in points from a file and using interpolation.

### Linked Nodes
The linked nodes section takes pairs of nodes to be connected to each other on opposite sides of the cylinder.

```yaml
surface:
  cylinder:
    radius: 3.5

  linked_nodes:
    - [Node1, Node7]
    - [Node4, Node8]
    - [Node9, Node12]
```
The only currently defined surface for linking nodes around is a cylinder.