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


    if type(dist_type[0]) != str or dist_type[0] == "uniform":
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

def add_temporal_distributions(df_nodes, df_temporal_distributions):
    '''
    Assigns user-defined fixed temporal distributions to exchanges of corresponding nodes

            Parameters:
                    df_node: dataframe containing nodes to temporalize and temporal distributions
    '''

    for nrow, node in df_nodes.iterrows():
        for exc in bd.get_node(id = node.node_id).exchanges():
            if node.node_id  in df_temporal_distributions.index.to_list() and exc['type'] != 'production':
                exc['temporal_distribution'] = create_distribution(
                    df_temporal_distributions.at[node.node_id, 'start'], df_temporal_distributions.at[node.node_id, 'end'], 
                    (df_temporal_distributions.at[node.node_id, 'dist_type'], df_temporal_distributions.at[node.node_id, 'parameter'])
                )
                exc.save()

    return