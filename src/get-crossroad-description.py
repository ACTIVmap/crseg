#!/usr/bin/env python3
# coding: utf-8

import argcomplete, argparse


import networkx as nx
import osmnx as ox
# add information about cycleways
cycletags = ["cycleway", "cycleway:right", "cycleway:left"]
ox.utils.config(osm_xml_way_tags = ox.settings.osm_xml_way_tags + cycletags,
                useful_tags_way = ox.settings.useful_tags_way + cycletags)


import crseg.segmentation as cs
import crseg.reliability as r
import crseg.region as rg
import json

# load predefined crossroad coordinates
with open("crossroads-by-name.json") as f:
    coordsByName = json.load(f)


# set parser
parser = argparse.ArgumentParser(description="Build a basic description of the crossroad located at the requested coordinate.")

group_input = parser.add_argument_group('Input region', "Define the input region from OSM (by coordinates or by name) or from a local file")
input_params = group_input.add_mutually_exclusive_group(required=True)
input_params.add_argument('--by-coordinates', nargs=2, help='Load input from OSM using the given latitude', type=float)

input_params.add_argument('--by-name', help='Load input from OSM using a predefined region', choices=[n for n in coordsByName])
input_params.add_argument('--from-graphml', help='Load road graph from a GraphML file', type=argparse.FileType('r'))


parser.add_argument('-r', '--radius', help='Radius (in meter) where the crossroads will be reconstructed. Default: 150m', type=float, default=150)
parser.add_argument('--connection-intensity', help='Intensity of the connection (2: small intensiy, 5: strong intensity). Default: 2.', type=float, default=2)
parser.add_argument('--max-cycle-elements', help='Maximum number of small crossroads to be combined as a ring in a large crossroad. Default: 10.', type=int, default=10)
parser.add_argument('-v', '--verbose', help='Verbose messages', action='store_true')

parser.add_argument('--skip-processing', help="Do not compute segmentation (can be useful to store OSM data without modification, or to use result of a previous run by loading a GraphML.", action='store_true')

parser.add_argument('--multiscale', help="Display and save crossings with multiscale data (not only the main crossroad, but also the small crossroads part of the large one.", action='store_true')

group_display = parser.add_argument_group("Display", "Activate a display")
group_display.add_argument('-d', '--display', help='Display crossroads in the reconstructed region', action='store_true')
group_display.add_argument('--display-reliability', help='Display reliability computed before any segmentation', action='store_true')
group_display.add_argument('--display-segmentation', help='Display segmentation (crossroads) in the reconstructed region', action='store_true')
group_display.add_argument('--display-main-crossroad', help='Display main crossroad (and associated branches)', action='store_true')

group_output = parser.add_argument_group("Output", "Export intermediate properties or final data in a dedicated format")
group_output.add_argument('--to-text-all', help='Generate a text description of all reconstructed crossings', action='store_true')
group_output.add_argument('--to-text', help='Generate a text description of crossing in the middle of the map', action='store_true')
group_output.add_argument('--to-gexf', help='Generate a GEXF file with the computed graph (contains reliability scores for edges and nodes). Some metadata will not be exported.', type=argparse.FileType('w'))
group_output.add_argument('--to-graphml', help='Generate a GraphML file with the computed graph (contains reliability scores for edges and nodes)', type=argparse.FileType('w'))
group_output.add_argument('--to-json-all', help='Generate a json description of the crossings', type=argparse.FileType('w'))
group_output.add_argument('--to-json', help='Generate a json description of the crossing in the middle of the map', type=argparse.FileType('w'))

# handle bash autocomplete
argcomplete.autocomplete(parser)
# load and validate parameters
args = parser.parse_args()

# get parameters
if args.by_coordinates:
    latitude = args.by_coordinates[0]
    longitude = args.by_coordinates[1]
byname = args.by_name

if byname in coordsByName:
    latitude = coordsByName[byname]["latitude"]
    longitude = coordsByName[byname]["longitude"]

from_graphml = args.from_graphml

# set input parameters
radius = args.radius
verbose = args.verbose

display = args.display
display_reliability = args.display_reliability
display_segmentation = args.display_segmentation
display_main_crossroad = args.display_main_crossroad
to_text_all = args.to_text_all
to_text = args.to_text
to_gexf = args.to_gexf
to_graphml = args.to_graphml
to_json = args.to_json
to_json_all = args.to_json_all
skip_processing = args.skip_processing
multiscale = args.multiscale
connection_intensity = args.connection_intensity
max_cycle_elements = args.max_cycle_elements

# load data

if verbose:
    print("=== DOWNLOADING DATA ===")

if from_graphml:
    G = ox.io.load_graphml(from_graphml.name, 
                                node_dtypes={r.Reliability.boundary_reliability: float, 
                                        r.Reliability.crossroad_reliability: float,
                                        rg.Region.label_region: int},
                                edge_dtypes={r.Reliability.crossroad_reliability: float,
                                            rg.Region.label_region: int})
    # load parameters
    latitude = G.graph["cr.latitude"]
    longitude = G.graph["cr.longitude"]
    radius = G.graph["cr.radius"]

    print(type(G))    
else:
    G = ox.graph_from_point((latitude, longitude), dist=radius, network_type="all", retain_all=False, truncate_by_edge=True, simplify=False)

    if verbose:
        print("=== PREPROCESSING (1) ===")

    # remove sidewalks, cycleways
    keep_all_components = False
    G = cs.Segmentation.remove_footways_and_parkings(G, keep_all_components)

    if verbose:
        print("=== PREPROCESSING (2) ===")

    # build an undirected version of the graph
    G = ox.utils_graph.get_undirected(G)

if verbose:
    print("Coordinates:", latitude, longitude)
    print("Radius:", radius)


if skip_processing:
    print("=== SKIP INITIALISATION ===")
    seg = cs.Segmentation(G, False)
else:
    if verbose:
        print("=== INITIALISATION ===")

    # segment it using topology and semantic
    seg = cs.Segmentation(G, connection_intensity = connection_intensity, max_cycle_elements = max_cycle_elements)

if display_reliability:
    print("=== RENDERING RELIABILITY ===")

    if multiscale:
        print("Warning: this display do not handle multiscale option")

    ec = seg.get_edges_reliability_colors()

    nc = seg.get_nodes_reliability_colors()

    ox.plot.plot_graph(G, edge_color=ec, node_color=nc)


if skip_processing:
    print("=== SKIP SEGMENTATION ===")
else:
    if display or display_segmentation or to_text or to_text_all or to_gexf or \
     to_json or to_json_all or to_graphml or display_main_crossroad: # or any other next step
        if verbose:
            print("=== SEGMENTATION ===")
        seg.process()


if to_text_all:
    if verbose:
            print("=== TEXT OUTPUT ===")
    print(seg.to_text_all(multiscale))

if to_text:
    if verbose:
            print("=== TEXT OUTPUT ===")
    print(seg.to_text(longitude, latitude, multiscale))

if to_json:
    if verbose:
            print("=== EXPORT IN JSON ===")
    seg.to_json(to_json.name, longitude, latitude, multiscale)

if to_json_all:
    if verbose:
            print("=== EXPORT IN JSON ===")
    seg.to_json_all(to_json_all.name, multiscale)

if display:
    if verbose:
        print("=== RENDERING ===")

    if multiscale:
        print("Warning: this display do not handle multiscale option")

    ec = seg.get_regions_class_colors()

    nc = seg.get_nodes_reliability_on_regions_colors()

    ox.plot.plot_graph(G, edge_color=ec, node_color=nc)

if display_segmentation:
    if verbose:
        print("=== RENDERING SEGMENTATION ===")

    if multiscale:
        print("Warning: this display do not handle multiscale option")
    ec = seg.get_regions_colors()

    nc = seg.get_nodes_regions_colors()

    ox.plot.plot_graph(G, edge_color=ec, node_color=nc)

if display_main_crossroad:
    if verbose:
        print("=== RENDERING MAIN CROSSROAD ===")


    cr = seg.get_crossroad(longitude, latitude, multiscale)
    
    ec = seg.get_regions_colors_from_crossroad(cr)

    nc = seg.get_nodes_regions_colors_from_crossroad(cr)

    ox.plot.plot_graph(G, edge_color=ec, node_color=nc)

if to_gexf:
    if verbose:
        print("=== EXPORT IN GEXF ===")

    att_list = ['geometry']
    for n1, n2, d in G.edges(data=True):
        for att in att_list:
            d.pop(att, None)

    # Simplify after removing attribute
    nx.write_gexf(G, to_gexf.name)

if to_graphml:
    if verbose:
        print("=== EXPORT IN GraphML ===")
        # Store parameters
        G.graph["cr.latitude"] = latitude
        G.graph["cr.longitude"] = longitude
        G.graph["cr.radius"] = radius
        for r in seg.regions:
            G.graph[rg.Region.regiontag_prefix + str(r)] = "crossroad" if seg.regions[r].is_crossroad() else "branch"
        # TODO: store for each region id its kind (crossing or branch)
        ox.io.save_graphml(G, to_graphml.name)
