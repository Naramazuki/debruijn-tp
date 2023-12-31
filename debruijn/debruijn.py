#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""Perform assembly based on debruijn graph."""

import argparse
import os
import sys
import networkx as nx
import matplotlib
from operator import itemgetter
import random

random.seed(9001)
from random import randint
import statistics
import textwrap
import matplotlib.pyplot as plt

matplotlib.use("Agg")

__author__ = "REINE Mathis"
__copyright__ = "Universite Paris Diderot"
__credits__ = ["REINE Mathis"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "REINE Mathis"
__email__ = "mathis.reine@etu-paris.fr"
__status__ = "Developpement"


def isfile(path):  # pragma: no cover
    """Check if path is an existing file.

    :param path: (str) Path to the file

    :raises ArgumentTypeError: If file doesn't exist

    :return: (str) Path
    """
    if not os.path.isfile(path):
        if os.path.isdir(path):
            msg = "{0} is a directory".format(path)
        else:
            msg = "{0} does not exist.".format(path)
        raise argparse.ArgumentTypeError(msg)
    return path


def get_arguments():  # pragma: no cover
    """Retrieves the arguments of the program.

    :return: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(
        description=__doc__, usage="{0} -h".format(sys.argv[0])
    )
    parser.add_argument(
        "-i", dest="fastq_file", type=isfile, required=True, help="Fastq file"
    )
    parser.add_argument(
        "-k", dest="kmer_size", type=int, default=22, help="k-mer size (default 22)"
    )
    parser.add_argument(
        "-o",
        dest="output_file",
        type=str,
        default=os.curdir + os.sep + "contigs.fasta",
        help="Output contigs in fasta file (default contigs.fasta)",
    )
    parser.add_argument(
        "-f", dest="graphimg_file", type=str, help="Save graph as an image (png)"
    )
    return parser.parse_args()


def read_fastq(fastq_file):
    """Extract reads from fastq files.

    :param fastq_file: (str) Path to the fastq file.
    :return: A generator object that iterate the read sequences.
    """
    with open(fastq_file) as f:
        list_records = [line.strip() for line in f]
        nb_records = len(list_records) // 4
        for i in range(nb_records):
            seq = list_records[i * 4 + 1]
            yield seq


def cut_kmer(read, kmer_size):
    """Cut read into kmers of size kmer_size.

    :param read: (str) Sequence of a read.
    :return: A generator object that iterate the kmers of of size kmer_size.

    """
    for i in range(0, len(read) - kmer_size + 1):
        yield read[i : i + kmer_size]


def build_kmer_dict(fastq_file, kmer_size):
    """Build a dictionnary object of all kmer occurrences in the fastq file

    :param fastq_file: (str) Path to the fastq file.
    :return: A dictionnary object that identify all kmer occurrences.
    """
    kmer_dict = {}
    for read in read_fastq(fastq_file):
        for kmer in cut_kmer(read, kmer_size):
            if kmer in kmer_dict:
                kmer_dict[kmer] += 1
            else:
                kmer_dict[kmer] = 1
    return kmer_dict


def build_graph(kmer_dict):
    """Build the debruijn graph

    :param kmer_dict: A dictionnary object that identify all kmer occurrences.
    :return: A directed graph (nx) of all kmer substring and weight (occurrence).
    """
    G = nx.DiGraph()
    for kmer in kmer_dict:
        G.add_edge(kmer[:-1], kmer[1:], weight=kmer_dict[kmer])
    return G


def remove_paths(graph, path_list, delete_entry_node, delete_sink_node):
    """Remove a list of path in a graph. A path is set of connected node in
    the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param delete_entry_node: (boolean) True->We remove the first node of a path
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    for path in path_list:
        graph.remove_nodes_from(path[1:-1])
        if delete_entry_node:
            graph.remove_node(path[0])
        if delete_sink_node:
            graph.remove_node(path[-1])
    return graph


def select_best_path(
    graph,
    path_list,
    path_length,
    weight_avg_list,
    delete_entry_node=False,
    delete_sink_node=False,
):
    """Select the best path between different paths

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param path_length_list: (list) A list of length of each path
    :param weight_avg_list: (list) A list of average weight of each path
    :param delete_entry_node: (boolean) True->We remove the first node of a path
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    weight_std = statistics.stdev(weight_avg_list)
    length_std = statistics.stdev(path_length)
    if weight_std > 0:
        best_path_index = weight_avg_list.index(max(weight_avg_list))
        del path_list[best_path_index]
    else:
        if length_std > 0:
            best_path_index = path_length.index(max(path_length))
            del path_list[best_path_index]

        else:
            best_path_index = randint(0, len(path_list) - 1)
            del path_list[best_path_index]

    graph = remove_paths(
        graph,
        path_list,
        delete_entry_node,
        delete_sink_node,
    )
    return graph


def path_average_weight(graph, path):
    """Compute the weight of a path

    :param graph: (nx.DiGraph) A directed graph object
    :param path: (list) A path consist of a list of nodes
    :return: (float) The average weight of a path
    """
    return statistics.mean(
        [d["weight"] for (u, v, d) in graph.subgraph(path).edges(data=True)]
    )


def solve_bubble(graph, ancestor_node, descendant_node):
    """Explore and solve bubble issue

    :param graph: (nx.DiGraph) A directed graph object
    :param ancestor_node: (str) An upstream node in the graph
    :param descendant_node: (str) A downstream node in the graph
    :return: (nx.DiGraph) A directed graph object
    """
    paths = list(nx.all_simple_paths(graph, ancestor_node, descendant_node))
    list_weight = [path_average_weight(graph, path) for path in paths]
    path_length = [len(path) for path in paths]
    graph = select_best_path(
        graph,
        path_list=paths,
        weight_avg_list=list_weight,
        path_length=path_length,
        delete_entry_node=False,
        delete_sink_node=False,
    )
    return graph


def simplify_bubbles(graph):
    """Detect and explode bubbles

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    bubble = False
    for node in graph.nodes():
        if len(list(graph.successors(node))) > 1:
            predecessors = list(graph.predecessors(node))
            for i in range(len(predecessors) - 1):
                for j in range(i + 1, len(predecessors)):
                    anc_node = nx.lowest_common_ancestor(
                        graph, predecessors[i], predecessors[j]
                    )
                    if anc_node != None:
                        bubble = True
                        break
        if bubble:
            break
    if bubble:
        graph = simplify_bubbles(solve_bubble(graph, anc_node, node))
    return graph


def solve_entry_tips(graph, starting_nodes):
    """Remove entry tips

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    list_path = []
    list_weight = []
    path_length = []
    for node in list(graph.nodes()):
        if node not in starting_nodes and len(list(graph.predecessors(node))) > 1:
            for starting_node in starting_nodes:
                if nx.has_path(graph, starting_node, node):
                    for path in nx.all_simple_paths(graph, starting_node, node):
                        list_path.append(path)
                        list_weight.append(path_average_weight(graph, path))
                        path_length.append(len(path))
            break
    if len(list_path) > 1:
        graph = solve_entry_tips(
            select_best_path(
                graph,
                path_list=list_path,
                weight_avg_list=list_weight,
                path_length=path_length,
                delete_entry_node=True,
                delete_sink_node=False,
            ),
            starting_nodes,
        )

    return graph


def solve_out_tips(graph, ending_nodes):
    """Remove out tips

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    list_path = []
    list_weight = []
    path_length = []
    for node in list(graph.nodes()):
        if node not in ending_nodes and len(list(graph.successors(node))) > 1:
            for ending_node in ending_nodes:
                if nx.has_path(graph, node, ending_node):
                    for path in nx.all_simple_paths(graph, node, ending_node):
                        list_path.append(path)
                        list_weight.append(path_average_weight(graph, path))
                        path_length.append(len(path))
            break
    if len(list_path) > 1:
        graph = solve_out_tips(
            select_best_path(
                graph,
                path_list=list_path,
                weight_avg_list=list_weight,
                path_length=path_length,
                delete_entry_node=False,
                delete_sink_node=True,
            ),
            ending_nodes,
        )

    return graph


def get_starting_nodes(graph):
    """Get nodes without predecessors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without predecessors
    """
    list_pred = []
    for node in graph.nodes():
        if len(list(graph.predecessors(node))) == 0:
            list_pred.append(node)
    return list_pred


def get_sink_nodes(graph):
    """Get nodes without successors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without successors
    """
    list_succ = []
    for node in graph.nodes():
        if len(list(graph.successors(node))) == 0:
            list_succ.append(node)
    return list_succ


def get_contigs(graph, starting_nodes, ending_nodes):
    """Extract the contigs from the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param starting_nodes: (list) A list of nodes without predecessors
    :param ending_nodes: (list) A list of nodes without successors
    :return: (list) List of [contiguous sequence and their length]
    """
    list_contig = []
    for start_node in starting_nodes:
        for end_node in ending_nodes:
            if nx.has_path(graph, start_node, end_node):
                for path in nx.all_simple_paths(graph, start_node, end_node):
                    seq = ""
                    seq += path[0]
                    for i in range(1, len(path)):
                        seq = seq + path[i][-1]
                    list_contig.append((seq, len(seq)))

    return list_contig


def save_contigs(contigs_list, output_file):
    """Write all contigs in fasta format

    :param contig_list: (list) List of [contiguous sequence and their length]
    :param output_file: (str) Path to the output file
    """
    with open(output_file, "wt") as f:
        for i, contig in enumerate(contigs_list):
            f.write(f">contig_{str(i)} len={contig[1]}\n")
            f.write(textwrap.fill(contig[0], width=80) + "\n")


def draw_graph(graph, graphimg_file):  # pragma: no cover
    """Draw the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param graphimg_file: (str) Path to the output file
    """
    fig, ax = plt.subplots()
    elarge = [(u, v) for (u, v, d) in graph.edges(data=True) if d["weight"] > 3]
    # print(elarge)
    esmall = [(u, v) for (u, v, d) in graph.edges(data=True) if d["weight"] <= 3]
    # print(elarge)
    # Draw the graph with networkx
    # pos=nx.spring_layout(graph)
    pos = nx.random_layout(graph)
    nx.draw_networkx_nodes(graph, pos, node_size=6)
    nx.draw_networkx_edges(graph, pos, edgelist=elarge, width=6)
    nx.draw_networkx_edges(
        graph, pos, edgelist=esmall, width=6, alpha=0.5, edge_color="b", style="dashed"
    )
    # nx.draw_networkx(graph, pos, node_size=10, with_labels=False)
    # save image
    plt.savefig(graphimg_file)


# ==============================================================
# Main program
# ==============================================================
def main():  # pragma: no cover
    """
    Main program function
    """
    # Get arguments
    args = get_arguments()

    # Fonctions de dessin du graphe
    # A decommenter si vous souhaitez visualiser un petit
    # graphe
    # Plot the graph
    # if args.graphimg_file:
    #    draw_graph(G, args.graphimg_file)
    G = build_graph(build_kmer_dict(args.fastq_file, args.kmer_size))
    G = simplify_bubbles(G)
    G = solve_out_tips(G, get_sink_nodes(G))
    G = solve_entry_tips(G, get_starting_nodes(G))

    save_contigs(
        get_contigs(G, get_starting_nodes(G), get_sink_nodes(G)), args.output_file
    )


if __name__ == "__main__":  # pragma: no cover
    main()
