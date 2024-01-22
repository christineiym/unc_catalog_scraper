import networkx as nx
from pyvis.network import Network  # https://github.com/WestHealth/pyvis
import pandas as pd

# https://stackoverflow.com/questions/49683445/create-networkx-graph-from-csv-file
df = pd.read_csv('prereqs.csv')
Graphtype = nx.Graph()
G = nx.from_pandas_edgelist(df, source="prereq_id", target="course_id")

nt = Network('750px', '80%', cdn_resources='remote', notebook=False)
nt.from_nx(G)
nt.show_buttons()
nt.show('test.html')