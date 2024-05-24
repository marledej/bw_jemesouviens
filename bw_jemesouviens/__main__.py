import bw2io, bw2data, bw2calc
import pandas as pd
from bw_graph_tools import NewNodeEachVisitGraphTraversal
import bw_jemesouviens.nodes_lists_multiple_databases as nl
import user_interface as ui # TBD
import panel as pn
from .user_interface import panel_app


def main():
    # open user interface - see https://panel.holoviz.org/how_to/server/programmatic.html
    pn.serve(panel_app)
    # get user inputs i.e. user_activity_name,user_location,user_amount,user_method,user_cutoff,user_market,user_transport (and fpei is user_database == 'ecoinvent')

    #if user_database=='ecoinvent': chosen_database=import_ei(fpei)
    #elif user_database=='USEEIO-1.1': chosen_database=import_useeio()

    #[df_nodes, df_edges] = nl.create_nodes_and_edges_lists(user_activity_name, user_location, user_amount, user_method, user_cutoff)

    #if chosen_database == 'ecoinvent: df_nodes_adjusted = nl.adjust_nodes_list(df_nodes, user_market, user_transport)
    #df_for_temporalisation = nl.create_dataframe_for_temporalisation(df_nodes_adjusted, df_edges) # Georg and Willy: this is what I sent
    #elif chosen_database == 'USEEIO-1.1': df_for_temporalisation = nl.create_dataframe_for_temporalisation(df_nodes, df_edges)

    #df_for_user = nl.create_dataframe_for_user(df_for_temporalisation) # This is the one to show on the user interface

    # perform temporalisation

    # print final graph
