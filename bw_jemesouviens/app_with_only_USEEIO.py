# %%
import bw2io as bi
import bw2data as bd
import bw2calc as bc
from bw_graph_tools import NewNodeEachVisitGraphTraversal
import pandas as pd
import panel as pn
import numpy as np
from math import pi
import datetime
import bokeh



#https://panel.holoviz.org/developer_guide/extensions.html#extension-plugins
pn.extension()

# https://panel.holoviz.org/reference/widgets/Tabulator.html
pn.extension('tabulator')

# BRIGHTAY SETUP ################################################################




def check_for_useeio_brightway_project():
        if 'USEEIO-1.1' not in bd.projects:
            bi.install_project(project_key="USEEIO-1.1", overwrite_existing=True)
        bd.projects.set_current(name='USEEIO-1.1')
        useeio = bd.Database("USEEIO-1.1")
        return useeio

useeio = check_for_useeio_brightway_project()

list_of_useeio_products=[
    node['name'] for node in useeio
    if 'product' in node['type']
]

list_of_method0_names1=([list(bd.methods)[0:19][i] for i in range (19)], ([str(list(bd.methods)[0:19][i]) for i in range (19)])) 

    



# PANEL SETUP ###################################################################

search_string =''
lca_score = 0
df_activities = pd.DataFrame()

# https://panel.holoviz.org/reference/widgets/AutocompleteInput.html
# https://panel.holoviz.org/reference/widgets/AutocompleteInput.html
widget_autocomplete_input_activity = pn.widgets.AutocompleteInput(
    name='Autocomplete Product Selection',
    options=list_of_useeio_products,
    case_sensitive=False,
    search_strategy='includes',
    placeholder='Write something her...'
)
widget_autocomplete_input_method = pn.widgets.AutocompleteInput(
    name='Autocomplete Method Selection',
    options=list_of_method0_names1[1],
    case_sensitive=False,
    search_strategy='includes',
    placeholder='Write something her...',
    min_characters = 0
)

#https://panel.holoviz.org/reference/widgets/Checkbox.html
widget_checkbox_market = pn.widgets.Checkbox(name='Market : automatic')

#https://panel.holoviz.org/reference/widgets/Checkbox.html
widget_checkbox_transport = pn.widgets.Checkbox(name='Transport : automatic')

#https://panel.holoviz.org/reference/widgets/ArrayInput.html
widget_amount_activity = pn.widgets.ArrayInput(name='Amount of Process', value=None)

#https://panel.holoviz.org/reference/widgets/ArrayInput.html
widget_amount_cut_off = pn.widgets.ArrayInput(name='Cut-off', value=None)

# https://panel.holoviz.org/reference/widgets/Button.html
widget_button_activity = pn.widgets.Button(
    name='Click me to calculate LCA score!',
    button_type='primary'
)

# https://panel.holoviz.org/reference/widgets/Button.html
widget_button_tabulator = pn.widgets.Button(
    name='Click me to perform temporalization!',
    button_type='primary'
)

# https://panel.holoviz.org/reference/widgets/StaticText.html
widget_static_text = pn.widgets.StaticText(
    name='Selected Database Activity',
    value="Nothing yet"
)

# this needs to be updated
tabulator_editors = {
    'int': None,
    'float': {'type': 'number', 'max': 10, 'step': 0.1},
    'bool': {'type': 'tickCross', 'tristate': True, 'indeterminateValue': None},
    'str': {'type': 'list', 'valuesLookup': True},
    'date': 'date',
    'datetime': 'datetime'
}

# https://panel.holoviz.org/reference/widgets/Tabulator.html
widget_tabulator = pn.widgets.Tabulator(
    df_activities,
)

widget_button_update_figure = pn.widgets.Button(
    name='Click me to update Figure!',
    button_type='primary'
)

# CALCULATION FUNCTIONS ######################################################


def select_database_activity(search_string):
    # https://docs.brightway.dev/en/latest/content/gettingstarted/objects.html#object-selection
    selected_activity = [
        node for node in useeio
        if search_string.lower() == node['name'].lower()
        and 'product' in node['type']
    ][0] # this just selects the first element in the list
    return selected_activity




def perform_lca_and_path_analysis(
    selected_activity, name_method_chosen, list_of_method0_names1
) -> pd.DataFrame:
    # https://docs.brightway.dev/en/latest/content/gettingstarted/lca.html#calculate-one-lcia-result
    index = list_of_method0_names1[1].index(name_method_chosen)
    lca = bc.LCA(
        demand={selected_activity: 1},
        method=list_of_method0_names1[0][index] # globaJl climate change
    )
    lca.lci()
    lca.lcia()
    lca_score = round(lca.score,2)

    # https://docs.brightway.dev/projects/graphtools/en/latest/content/api/bw_graph_tools/graph_traversal/index.html#bw_graph_tools.graph_traversal.NewNodeEachVisitGraphTraversal
    graph_traversal_result = NewNodeEachVisitGraphTraversal.calculate(lca, cutoff=0.01)

    return lca_score, pd.DataFrame.from_dict(graph_traversal_result['nodes'], orient='index')

def updating_col_data_frame(
        df,
):
    df['Starting time of the activity'] =[None]*df.shape[0]
    df['Ending time of the activity'] = [None]*df.shape[0]
    df['Type of Temporalization distribution'] = [None]*df.shape[0]
    df['Parameters of the distribution'] = [None]*df.shape[0]
    return df

# PLOTTING FUNCTIONS #########################################################


#example : 
    # Exemple de DataFrame
    '''
dummy_df = pd.DataFrame(np.array([
    [datetime.datetime.now(), 1, 'a flow', 'an activity'],
    [datetime.datetime(2022, 5, 1), 2, 'b flow', 'an activity'],
    [datetime.datetime(2022, 6, 1), 3, 'c flow', 'another activity'],
    [datetime.datetime(2023, 7, 1), 0.5, 'c flow', 'another activity'],
    [datetime.datetime(2024, 7, 1), 1, 'c flow', 'third activity'],
    [datetime.datetime(2023, 7, 1), 8, 'c flow', 'fourth activity']
]), columns=['date', 'impact', 'flow', 'activity'])

df_temporalized=dummy_df
'''

def dataframe_manipulation(df: pd.DataFrame) :
    # Convertir les dates en années
    df['year'] = df['date'].dt.year
    # Regrouper par année et activité, puis sommer les impacts
    grouped_df = df.groupby(['year', 'activity'])['impact'].sum().unstack(fill_value=0)
    # Convertir les années en chaînes de caractères
    grouped_df.index = grouped_df.index.astype(str)

    return grouped_df

def dataframe_to_graph(grouped_df: pd.DataFrame) : 
    # Convertir le DataFrame groupé en ColumnDataSource
    source = bokeh.models.ColumnDataSource(grouped_df.reset_index())
    # Les années serviront de catégories pour l'axe x
    years = grouped_df.index.tolist()
    # Les activités serviront de catégories pour les barres empilées
    activities = grouped_df.columns.tolist()
    # Couleurs pour les différentes activités
    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
        "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
        "#c49c94", "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5"
    ]  # Ajoutez plus de couleurs si nécessaire
    # Vérifier le nombre de couleurs et ajuster si nécessaire
    if len(colors) < len(activities):
        colors = colors * (len(activities) // len(colors)) + colors[:len(activities) % len(colors)]
    elif len(colors) > len(activities):
        colors = colors[:len(activities)]
    # Créer un graphique
    graph = bokeh.plotting.figure(x_range=years, height=350, title="Emissions des Activités par Année",
               toolbar_location=None, tools="")
    # Ajouter des barres empilées
    graph.vbar_stack(stackers=activities, x='year', width=0.9, color=colors, source=source,
                 legend_label=activities)
    # Configurer les axes
    graph.y_range.start = 0
    graph.xgrid.grid_line_color = None
    graph.yaxis.axis_label = 'Impact'
    graph.xaxis.axis_label = 'Année'
    graph.axis.minor_tick_line_color = None
    graph.outline_line_color = None
    graph.legend.location = "top_left"
    graph.legend.orientation = "horizontal"
    
    return graph



pane_bokeh = pn.pane.Bokeh(bokeh.plotting.figure())



# INTERACTIVE ELEMENTS #######################################################
###
def update_interactive_elements_lca(event):
    selected_activity = select_database_activity(search_string=widget_autocomplete_input_activity.value)
    widget_static_text.value = selected_activity['name']
    widget_tabulator.loading = True
    lca_score, df_activities = perform_lca_and_path_analysis(selected_activity=selected_activity, name_method_chosen=widget_autocomplete_input_method.value, list_of_method0_names1=list_of_method0_names1)
    df_activities=updating_col_data_frame(df_activities)
    #df_activities=updating_col_data_frame(mon_df)
    widget_tabulator.value = df_activities
    widget_tabulator.loading = False



def update_interactive_elements_temporalization(event):
    df_activities=widget_tabulator.value
    

    

def update_bokeh_pane(event):
    pane_bokeh.loading = True
    bokeh_figure = dataframe_to_graph(grouped_df=dataframe_manipulation(df_temporalized))
    pane_bokeh.object = bokeh_figure
    pane_bokeh.loading = False


# https://panel.holoviz.org/reference/widgets/Button.html#buttonhttps://panel.holoviz.org/reference/widgets/Button.html#button
widget_button_activity.on_click(update_interactive_elements_lca)

# https://panel.holoviz.org/reference/widgets/Button.html#buttonhttps://panel.holoviz.org/reference/widgets/Button.html#button
widget_button_tabulator.on_click(update_interactive_elements_temporalization)

# https://panel.holoviz.org/reference/widgets/Button.html#buttonhttps://panel.holoviz.org/reference/widgets/Button.html#button
widget_button_update_figure.on_click(update_bokeh_pane)






# https://panel.holoviz.org/reference/layouts/Column.html
pn.Column(
    widget_autocomplete_input_activity,
    widget_autocomplete_input_method,
    widget_amount_activity,
    widget_amount_cut_off,
    widget_checkbox_market,
    widget_checkbox_transport,
    widget_button_activity,
    widget_static_text,
    widget_tabulator,
    widget_button_tabulator,
    widget_button_update_figure,
    pane_bokeh
).servable()
#%%
