from lifelike_gds.arango_network.trace_graph_nx import TraceGraphNx
from lifelike_gds.arango_network.trace_graph_utils import \
    set_edge_weight_by_source_node_weight, remove_edge_prop, all_shortest_paths
import networkx as nx
import logging


class InBetweennessTrace(TraceGraphNx):
    def __init__(self, graphsource):
        super().__init__(graphsource)

    def get_betweenness_prop_name(self, sources, targets):
        return f"{sources}_{targets}_betweenness"

    def compute_inbetweenness(self, sources, targets, inbetweenness_prop_name=None, pagerank_prop=None):
        """
        Compute betweenness for paths from sources to destination, and save the value to given node property
        Args:
            sources: source node set name
            targets: target node set name
            inbetweenness_prop_name: property name for inbetweenness value
            pagerank_prop: optional node pagerank prop for calculate edge weight
        Returns:
        """
        logging.info('start computing inbetweenness')
        source_nodes = self.graph.node_set(sources)
        target_nodes = self.graph.node_set(targets)

        tempkey = None
        if pagerank_prop:
            tempkey = 'edge_wt'
            set_edge_weight_by_source_node_weight(self.graph, pagerank_prop, tempkey)

        inbetweenness = dict()
        for source_id in source_nodes:
            for target_id in target_nodes:
                # get all shortest paths between source and target
                paths = all_shortest_paths(self.graph, [source_id], [target_id], tempkey)
                if not paths:
                    continue
                num_paths = len(paths)
                # get nodes in all the paths, then count frequencies
                nodes = []
                for path in paths:
                    nodes.extend(path)
                node_freq = self._freq_count(nodes)
                # add frequences from each (source, target) pair to get betweenness values
                for k, v in node_freq.items():
                    freq = inbetweenness.setdefault(k, 0)
                    inbetweenness[k] = freq + float(v) / float(num_paths)
        sum_val = sum([v for v in inbetweenness.values()])
        betweenness_scaled = {k: v / sum_val for k, v in inbetweenness.items()}
        if not inbetweenness_prop_name:
            inbetweenness_prop_name = self.get_betweenness_prop_name(sources, targets)
        nx.set_node_attributes(self.graph, inbetweenness, inbetweenness_prop_name)
        nx.set_node_attributes(self.graph, betweenness_scaled, inbetweenness_prop_name + '_scaled')
        # clean up temp edge weight
        if tempkey:
            remove_edge_prop(self.graph, tempkey)

    def _freq_count(self, items:[]):
        """
        Count list item frequence, retuern dict of item-freq count
        """
        freqs = {i:0 for i in items}
        for k in freqs.keys():
            freqs[k] = items.count(k)
        return freqs

    def export_inbetweenness_data(self, sources, targets, filename, do_compute=False):
        if do_compute:
            self.compute_inbetweenness(sources, targets)
        prop_name = self.get_betweenness_prop_name(sources, targets)
        all_nodes = [n for n, p in self.graph.nodes(data=True) if prop_name in p]
        exclude = set.union(self.graph.node_set(sources), self.graph.node_set(targets))
        export_nodes = set(all_nodes) - exclude
        df = self.get_nodes_detail_as_dataframe(export_nodes)
        filepath = f"{self.datadir}/{filename}"
        logging.info(f"export betweenness data into {filepath}")
        df.to_excel(filepath)

    def add_trace_from_sources_to_all_selected_nodes(
        self, 
        selected_nodeset: str,
        sources: str, 
        weighted_prop,
        trace_name='Sources to selected',
        shortest_paths_plus_n=0):
        self.add_selected_nodes_traces_combined_network(
            selected_nodeset, 
            weighted_prop, 
            sources, 
            targets=None,
            trace_name=trace_name,
            shortest_paths_plus_n=shortest_paths_plus_n)
        self.add_graph_description(f"Traces from {sources} to all {selected_nodeset};")

    def add_trace_from_all_selected_nodes_to_targets(
        self, 
        selected_nodeset: str, 
        targets: str, 
        weighted_prop,
        trace_name='Selected to targets',
        shortest_paths_plus_n=0):
        self.add_selected_nodes_traces_combined_network(
            selected_nodeset, 
            weighted_prop, 
            sources=None, 
            targets=targets,
            trace_name=trace_name, 
            shortest_paths_plus_n=shortest_paths_plus_n)
        self.add_graph_description(f"traces from all {selected_nodeset} to {targets}")

    def add_trace_from_sources_to_all_selected_nodes(
        self, 
        selected_nodeset: str,
        sources: str, 
        weighted_prop,
        trace_name='Sources to select',
        shortest_paths_plus_n=0):
        self.add_selected_nodes_traces_combined_network(
            selected_nodeset, 
            weighted_prop, 
            sources, 
            targets=None,
            trace_name=trace_name,
            shortest_paths_plus_n=shortest_paths_plus_n)
        self.add_graph_description(f"Traces from {sources} to all {selected_nodeset};")

    def add_inbetweenness_trace_networks_with_selected_nodes(
        self, 
        select, 
        sources, 
        targets,
        shortest_paths_plus_n=0
    ):
        """
        Add two traces: source to selected nodes, selected nodes to targets
        Args:
            selected_nodes: list of arango nodes
            sources: source set name
            targets: target set name
            add_graphdesc: if True, add graph description
        Returns:
        """
        self.compute_inbetweenness(sources, targets)
        prop_name = self.get_betweenness_prop_name(sources, targets)
        self.add_trace_from_sources_to_all_selected_nodes(
            select,
            sources,
            prop_name,
            trace_name='Sources to selected',
            shortest_paths_plus_n=shortest_paths_plus_n)
        self.add_trace_from_all_selected_nodes_to_targets(
            select,
            targets,
            prop_name,
            trace_name='Selected to targets',
            shortest_paths_plus_n=shortest_paths_plus_n)


    def add_inbetweenness_trace_networks_with_selected_nodes_original(self, selected_nodes, sources, targets, 
                                                             include_allshortest_path=True,
                                                             do_compute=False, add_graphdesc=True,
                                                             shortest_paths_plus_n=0):
        """
        Add two traces: source to selected nodes, selected nodes to targets
        Args:
            selected_nodes: list of arango nodes
            sources: source set name
            targets: target set name
            include_allshortest_path: if True, add shortest paths to the graph
            do_compute: if True, compute in-betweenness values
            add_graphdesc: if True, add graph description
        Returns:
        """
        if do_compute:
            self.compute_inbetweenness(sources, targets)
        prop_name = self.get_betweenness_prop_name(sources, targets)
        self.add_selected_nodes_trace_networks(selected_nodes, prop_name, 'inbetweenness', sources, targets, 
                                               include_allshortest_path, shortest_paths_plus_n=shortest_paths_plus_n)
        if add_graphdesc:
            self.add_graph_description(f"Traces from {sources} to {len(selected_nodes)} selected nodes;")
            self.add_graph_description(f"Traces from {len(selected_nodes)} selected nodes to {targets};")

    def add_best_n_inbetweenness_nodes_to_trace_networks(self, sources, targets, num=10, do_compute=False):
        """
        Add best n nodes.  Need to add more filters for the best nodes
        e.g. excluding EntitySet for reactome graph, excluding nodes based on num of source node reaches
        """
        if do_compute:
            self.compute_inbetweenness(sources, targets)
        source_nodes = self.graph.node_set(sources)
        target_nodes = self.graph.node_set(targets)
        excluded = source_nodes.union(target_nodes)
        prop_name = self.get_betweenness_prop_name(sources, targets)
        selected_nodes = self.get_most_weighted_nodes(prop_name, num, exclude_nodes=excluded)
        self.add_trace_networks_with_selected_nodes(selected_nodes, sources, targets, False, False)
        self.add_graph_description(f"Traces from {sources} to top {num} betweenness nodes;")
        self.add_graph_description(f"Traces from top {num} betweenness nodes to {targets};")

