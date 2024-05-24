import bw2io, bw2data, bw2calc
import pandas as pd
from bw_graph_tools import NewNodeEachVisitGraphTraversal

def import_ei(fpei):
    if 'ecoinvent' in bw2data.databases:
        print("Database has already been imported")
    else:
        ei = bw2io.SingleOutputEcospold2Importer(fpei, 'ecoinvent')
        ei.apply_strategies()
        ei.statistics()

        if len(list(ei.unlinked)) == 0:
            ei.write_database()     
    ei = None
    chosen_database = bw2data.Database("ecoinvent")

    return chosen_database


def import_useeio():
    if 'USEEIO-1.1' not in bw2data.projects:
        bw2io.install_project(project_key="USEEIO-1.1", overwrite_existing=True)
    bw2data.projects.set_current(name='USEEIO-1.1')
    chosen_database = bw2data.Database("USEEIO-1.1")
    return chosen_database


def create_nodes_and_edges_lists(chosen_database, user_activity_name, user_location, user_amount, user_method, user_cutoff):
    # Perform LCA
    chosen_node = [n for n in chosen_database if user_activity_name in n["name"] and user_location in n['location']][0]
    chosen_method =[m for m in bw2data.methods if user_method in str(m)][0]
    chosen_lca = bw2calc.LCA( 
    demand={chosen_node: user_amount}, 
    method = chosen_method.name # attention here: it's not the Method object, just its name!!!
    ) 
    chosen_lca.lci() 
    chosen_lca.lcia()

    # Getting the initial (ugly) object listing nodes and edges
    contributing_nodes = NewNodeEachVisitGraphTraversal.calculate(chosen_lca, cutoff=user_cutoff)
    
    # Transform nodes list into dataframe
    # Initialize
    df_nodes = pd.DataFrame.from_dict(contributing_nodes['nodes'], orient='index')
    df_nodes.set_index('unique_id', inplace=True)
    df_nodes = df_nodes.drop(-1)
    # Add useful information
    df_nodes['cumulative_contribution'] = df_nodes['cumulative_score']/chosen_lca.score
    nodes_names=[]
    for unique_id in df_nodes.index.tolist():
        name=[act["name"] for act in chosen_database if act["id"]==contributing_nodes["nodes"][unique_id].activity_datapackage_id]
        nodes_names.append(name[0])
    df_nodes['node_name'] = pd.Series(data=nodes_names)
    
    # Transform edges list into dataframe
    df_edges = pd.DataFrame.from_dict(contributing_nodes['edges'])
    df_edges = df_edges.drop(0)
    # Add producer and consumer names
    if chosen_database.name == 'ecoinvent':
    for edge_id in df_edges.index.tolist():
        df_edges.at[edge_id,'producer_name'] = [act['name'] for act in chosen_database if act["id"]==df_edges.loc[edge_id]['producer_index']+4710][0]
        df_edges.at[edge_id,'consumer_name'] = [act['name'] for act in chosen_database if act["id"]==df_edges.loc[edge_id]['consumer_index']+4710][0]
    elif chosen_database.name == 'USEEIO-1.1':
        for edge_id in df_edges.index.tolist():
            df_edges.at[edge_id,'producer_name'] = [act['name'] for act in chosen_database if act["id"]==df_edges.loc[edge_id]['producer_index']][0]
            df_edges.at[edge_id,'consumer_name'] = [act['name'] for act in chosen_database if act["id"]==df_edges.loc[edge_id]['consumer_index']][0]
    else:
        print('Mh, what database are you using? For the moment you can only choose between USEEIO-1.1 and ecoinvent.')     

    return [df_nodes, df_edges]


def get_producers_ids(node_unique_id, df_edges):
    producers_ids = []
    for edge_id in df_edges.index.tolist(): 
        if df_edges.at[edge_id,'consumer_unique_id']==node_unique_id:
            producers_ids.append(df_edges.at[edge_id,'producer_unique_id'])
    
    return producers_ids


def remove_markets_ancestors(df_nodes, df_edges):
    df_nodes_without_markets_ancestors = df_nodes.copy()
    to_remove = []
    for n in range (1,len(df_nodes)): # this excludes the demand node in case it is a market
        if 'market' in df_nodes_without_markets_ancestors.at[n,'node_name']:
            producers_ids = get_producers_ids(n,df_edges)
            to_remove = to_remove + producers_ids
            while len(producers_ids) > 0:
                for previous_producer_id in producers_ids:
                    producers_ids = get_producers_ids(previous_producer_id,df_edges)
                    to_remove = to_remove + producers_ids
    df_nodes_without_markets_ancestors = df_nodes_without_markets_ancestors.drop(labels=to_remove)
    
    return df_nodes_without_markets_ancestors


def adjust_nodes_list(chosen_database, df_nodes, user_market, user_transport):
    # Remove producers (and producers of producers, etc.) of markets if automated market scenario
    if user_market == "auto":
        df_nodes_adjusted = remove_markets_ancestors(df_nodes)
    
    # Remove freight transport nodes if automated transport scenario
    if user_transport == 'auto':
    for n in df_nodes_adjusted.index.tolist():
        unit=[act["unit"] for act in chosen_database if act["id"]==df_nodes_adjusted.at[n,'reference_product_datapackage_id']][0]
        if unit=='ton kilometer':
            df_nodes_adjusted.drop(n)
        else:
            df_nodes_adjusted.at[n,'supply_unit']=unit
    
    return df_nodes_adjusted


def create_dataframe_for_temporalisation(df_nodes_adjusted, df_edges):
    # Initializing
    df_for_temporalisation = df_nodes_adjusted.copy()
    # Adding useful columns
    copy_of_df_edges = df_edges.copy()
    copy_of_df_edges.set_index('producer_unique_id')
    df_for_temporalisation['consumer_name'] = copy_of_df_edges['consumer_name']
    df_for_temporalisation['consumer_id'] = copy_of_df_edges['consumer_unique_id']

    return df_for_temporalisation


def create_dataframe_for_user(df_for_temporalisation):
    df_for_user = df_for_temporalisation.copy()
    # Removing useless columns
    df_for_user.drop(labels=['consumer_id','activity_datapackage_id','activity_index','reference_product_datapackage_id','reference_product_index','reference_product_production_amount', 'supply_amount'], axis=1, inplace=True)

    # A bit of formatting
    df_for_user.reset_index(inplace=True)
    df_for_user.rename(mapper={'unique_id':'activity_id', 'node_name':'activity_name'}, axis=1, inplace=True)
    df_for_user.set_index('activity_id', inplace=True)
    df_for_user = df_for_user.reindex(['activity_name', 'consumer_name', 'direct_emissions_score', 'cumulative_score', 'cumulative_contribution'], axis=1)

    return df_for_user

