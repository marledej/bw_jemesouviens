import bw2calc as bc
import bw2data as bd
import bw_temporalis as bt
import numpy as np
from bw_temporalis import TemporalDistribution, easy_datetime_distribution, FixedTD
from bw_graph_tools import NewNodeEachVisitGraphTraversal
import pandas as pd

def create_distribution(start,end,dist_type):
    '''
    Returns a fixed (!!) temporal distribution object in annual resolution.

            Parameters:
                    start (int): an integer specifying the start year
                    end (int): an integer specifying the end year (OK if it is the same as start)
                    dist_type (tuple): a tuple containing distribution type and parameter. If (nan,nan): unifrom distribution will be assumed
            Returns:
                    fixed_distribution (str): Fixed temporal distribution object
    '''
    #check that the provided start and end are 4-letter integers (years)

    #assert(all([type(start)==int,len(str(start))==4,
    #            type(end)==int,len(str(end))==4
    #            ]))
    
    if start==end:
        date_sequence = np.array([str(start)], dtype='datetime64[Y]')
    elif start<end:
        date_sequence = np.array([str(x) for x in range(start,end+1)], dtype='datetime64[Y]')
    else:
        raise ValueError("endyear before startyear")
    

    points = len(date_sequence)


    if ((dist_type[0]) != "triangular" or (dist_type[0]) != "normal") or dist_type[0] == "uniform":
        #not using the "easy_datetime_distribution" function because it can't handle one unique data point
        distribution = TemporalDistribution(
                    date=date_sequence,
                    amount=np.ones(points)/points)

    else:
        if dist_type[0]=="triangular":
            param_conv = str(int(dist_type[1]))
        elif dist_type[0]=="normal":
            param_conv = dist_type[1]
        distribution = easy_datetime_distribution(
            str(start),
            str(end),
            steps=int(end-start+1), # to ensure annual resolution
            kind=dist_type[0],
            param=param_conv
            )
                                            
    # fix the distribution because we expect explicit absolute calendar year inputs even for upstream supply chain 
    fixed_distribution = FixedTD(date=distribution.date,
                                 amount=distribution.amount)
    return fixed_distribution


# Function for adding temporal distributions to corresponding exchanges

def add_temporal_distributions(df_user,df_nodes):
    '''
    Assigns user-defined fixed temporal distributions to exchanges of corresponding nodes

            Parameters:
                    df_nodes: dataframe containing nodes to temporalize and temporal distributions
                    |node_id|start|end|dist_type|parameter| and more columns. do not put node_id as index.
                    node_id should be the id that allows to identify the node in the database
    '''
    df_user['node_id']=df_nodes['activity_datapackage_id']
    for nrow, node in df_user.iterrows():
        print(df_user)
        for exc in bd.get_node(id = node.node_id).exchanges():
            if exc['type'] != 'production':
                exc['temporal_distribution'] = create_distribution(
                    int(df_user.at[nrow, 'Starting time of the activity']), int(df_user.at[nrow, 'Ending time of the activity']), 
                    (df_user.at[nrow, 'Type of Temporalization distribution'], df_user.at[nrow, 'Parameters of the distribution'])
                )
                exc.save()

    return

def characterization(cfs,flow):
    """
    apply characterization method to a biosphere flow
            Parameters:
                    cfs: lcia method object
                    flow: node id of a biosphere flow
            Returns:
                    val: impact for specified biosphere flow
                    np.nan if flow was not found
    """
    cur_node = bd.get_activity(id=flow)
    code = cur_node.as_dict()["code"]
    for idx, val in cfs:
        if idx[1] == code:
            print(bd.get_activity(id=flow)["name"], val)
            return val
    print(f"flow {flow} not characterized")
    return np.nan
    

def apply_characterization_factors(data,*,use_method=('EF v3.1','climate change','global warming potential (GWP100)')):
    """
    applies the CFs of a selected method to the "amount" column of a df that specifies the biosphere flows in a "flow" column.
            Parameters:
                    data (pd.DataFrame): dataframe of structure
                        |index(arbitrary)|flow(the node id of the biosphere flow)|amount(flow inventory)|, more columns are allowed.
                    use_method (tuple): tuple defining the lcia method to apply. Default: GWP100 of the EF v3.1
            Returns:
                    data: dataframe of structure
                        |index(arbitrary)|flow(the node id of the biosphere flow)|amount(flow inventory)|CF(for respective flow)|impact|
                    use_method: the tuple of the lcia method used (could be default or the specified one)
    """
    method = bd.Method(use_method)
    cfs = method.load()
    data["CF"] = data["flow"].apply(lambda x: characterization(cfs,x))
    data["impact"] = data["CF"]*data["amount"]
    return data, use_method


# Run temporal LCA and get timeline dataframe with impacts

def calculate_timeline(df_user,df_nodes, lca,*, temporal_graph_cutoff=0.001, max_calc=3000):
    """
    calculating the lca timeline. note that the temporal_graph_cutoff and max_calc can notably influence the final results.
    Timeline does not allow to distinguish individual processes/activities
            Parameters:
                    df (pd.DataFrame): dataframe specifying node ids and their uncertainty parameters.

                    lca (lca object): lca object to temporalize (has to be the same that the df was created from)
                    temporal_graph_cutoff (float): cutoff under which nodes are not considered for graph traversal
                    max_calc (int): maximum number of calculations allowed for the graph traversal
            returns:
                    characterized_annual (pd.DataFrame): a dataframe indexed with np.datetime in annual resolution,
                    specifying the annual impact of the product system
                    used_characterization (tuple): the label of the used characterization method
    """
    print("Temporalizing lca object. Note that temporalization is added to the database on disc.")
    add_temporal_distributions(df_user=df_user,df_nodes=df_nodes)
    # convert lca object to temporalized lca object
    templca = bt.TemporalisLCA(lca,
                               cutoff=temporal_graph_cutoff,
                               max_calc=max_calc)
    tl = templca.build_timeline()
    dfa = tl.build_dataframe()

    characterized_timeline, used_characterization = apply_characterization_factors(dfa,use_method = lca.method)
    characterized_annual = characterized_timeline.set_index("date")[["amount","impact"]].resample("YE", label="left").sum()
    return characterized_annual,used_characterization
