import os

from lifelike_gds.arango_network.reactome import *
from lifelike_gds.arango_network.shortest_paths_trace import ShortestPathTrace

"""
Create shortest paths traces from endo in-chemical to out-chemical, by selecting different cluster group (1-5).
Compare paths by excluding different chemicals from the traces, e.g. H+, H2O, or all secondary metabs
"""

uri = os.getenv('ARANGO_URI', 'bolt://localhost:7687')
username = os.getenv('ARANGO_USER', 'arango')
password = os.getenv('ARANGO_PASSWORD', 'rcai')
dbname = os.getenv('ARANGO_DATABASE', 'reactome-human')
db_version = 'reactome-human from 12152021 dump'
database = ReactomeDB(dbname, uri, username, password)


def create_tracegraph(exclude, output_dir='./eot/output'):
    reactome = Reactome(database)
    tracegraph = ShortestPathTrace(reactome)

    graphdesc = 'Projected graph '
    if not exclude:
        print('no exclude')
        tracegraph.init_default_graph(exclude_currency=False)
        graphdesc += 'contains all chemicals'
    elif exclude == 'ALL':
        print("exclude ", exclude)
        tracegraph.init_default_graph()
        graphdesc += 'has all secondary metabolites removed'
    else:
        print("exclude ", exclude)
        exclude_nodes = database.get_nodes_by_attr(exclude, 'name')
        reactome.custome_init_trace_graph(tracegraph, exclude_nodes)
        graphdesc += f'has the following chemicals removed: {exclude}'
    tracegraph.datadir = output_dir
    tracegraph.add_graph_description(db_version)
    tracegraph.add_graph_description(graphdesc)
    return tracegraph


def get_graph_name(cluster_num, exclude):
    graphName = f"EoT cluster{cluster_num} in->out shortest paths"
    name_postfix = ""
    if exclude == 'ALL':
        name_postfix = " excluding all secondary"
    elif exclude:
        if len(exclude) < 3:
            name_postfix = f" excluding {' and '.join(exclude)}"
        else:
            name_postfix = f" excluding {len(exclude)} secondary"
    graphName += name_postfix
    return graphName


def write_inout_shortest_paths_sankey(tracegraph, inout_paris, cluster_num, exclude):
    tracegraph.graph = tracegraph.orig_graph.copy()
    sources = []
    targets = []
    for id1, id2 in inout_paris:
        source = database.get_nodes_by_attr([id1], 'stId')
        target = database.get_nodes_by_attr([id2], 'stId')
        if source and target:
            source_name = tracegraph.set_node_set_for_node(source[0])
            target_name = tracegraph.set_node_set_for_node(target[0])
            tracegraph.add_shortest_paths(source_name, target_name)
        sources += source
        targets += target
    ingroup = f"eot_cluster{cluster_num}_in"
    outgroup = f"eot_cluster{cluster_num}_out"
    tracegraph.set_node_set_from_arango_nodes(sources, ingroup, ingroup)
    tracegraph.set_node_set_from_arango_nodes(target, outgroup, outgroup)
    tracegraph.add_shortest_paths(ingroup, outgroup)

    outfileName = f"{get_graph_name(cluster_num, exclude)}.graph"
    tracegraph.write_to_sankey_file(outfileName)


def generate_eot_cluster_inout_shortest_paths_sankey(cluster_nums: [], exclude='ALL', input_dir='./eot/input',
                                                     inputfile="endo_match_inout_chems.xlsx"):
    tracegraph = create_tracegraph(exclude)
    infile = os.path.join(input_dir, inputfile)
    df = pd.read_excel(infile, usecols=['Cluster', 'IN stId', 'OUT stId'])
    df = df.dropna()
    for cluster_num in cluster_nums:
        df_c = df[df['Cluster'] == cluster_num]
        cluster_pairs = [(row['IN stId'], row['OUT stId']) for index, row in df_c.iterrows()]
        write_inout_shortest_paths_sankey(tracegraph, cluster_pairs, cluster_num, exclude)


if __name__ == '__main__':
    generate_eot_cluster_inout_shortest_paths_sankey([2, 4], None)
    generate_eot_cluster_inout_shortest_paths_sankey([2, 4], ['H+'])
    generate_eot_cluster_inout_shortest_paths_sankey([2, 4], ['H+', 'H2O'])
    generate_eot_cluster_inout_shortest_paths_sankey([2, 4])
