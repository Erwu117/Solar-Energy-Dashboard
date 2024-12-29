from dash import Dash, html, dcc, callback, Output, Input
import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import geopandas as gpd
import pandas as pd
from pathlib import Path
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from geopy.geocoders import Nominatim

# Data Preprocessing
dataset_folder = Path('datasets')
solar_data = gpd.read_file(dataset_folder / 'solar_data.geojson', driver='GeoJSON')
gadm_data = gpd.read_file(dataset_folder / 'gadm41_PHL_shp/gadm41_PHL_3.shp')
consump = pd.read_csv(dataset_folder / 'Consumption CO2 Philippines.csv')
gener = pd.read_csv(dataset_folder / 'Electricity generation by source Philippines.csv')
share = pd.read_csv(dataset_folder / 'Energy Share in the Philippines.csv')
px.set_mapbox_access_token(open(".mapbox_token").read())
converted_gdf = solar_data.copy()
converted_gdf = converted_gdf.to_crs("EPSG:4326")
converted_gdf_subset = converted_gdf[['geometry', 'capacity','suitarea','potential']]
converted_gdf_indexed = converted_gdf.set_index('city')

metro_manila_data = gadm_data.query("NAME_1 == 'Metropolitan Manila'")
metro_manila_data = metro_manila_data[["NAME_2","NAME_3", "geometry"]]
metro_manila_data.head(60)
merged_data = gpd.sjoin(converted_gdf, metro_manila_data, how='inner', op='within')
merged_data = merged_data.rename(columns={'capacity':'Estimated Capacity (kWp)','suitarea':'Estimated Suitable Area (sq.m)', 'potential':'Estimated Yearly Potential Power (kWh)'})
valid_indices = merged_data['index_right'].unique()

filtered_gadm_data = gadm_data[gadm_data.index.isin(valid_indices)]
max_group_per_name3 = merged_data.groupby('NAME_3')[['Estimated Capacity (kWp)','Estimated Suitable Area (sq.m)','Estimated Yearly Potential Power (kWh)']].max().reset_index()
gadm_data_with_group = filtered_gadm_data.merge(max_group_per_name3, on='NAME_3', how='left')
# gadm_data_with_group = gadm_data_with_group.rename(columns={'capacity':'Estimated Capacity (kWp)','suitarea':'Estimated Suitable Area (sq.m)', 'potential':'Estimated Yearly Potential Power (kWh)'})
gadm_data_with_group = gadm_data_with_group[gadm_data_with_group['NAME_3'] != 'n.a.']
# gadm_data_with_group.head()
gadm_data_with_dropdup_group = gadm_data_with_group.drop_duplicates(subset=['NAME_3'])
gadm_data_with_dropdup_group_sorted = gadm_data_with_dropdup_group.sort_values(by='Estimated Capacity (kWp)', ascending=False).head(20)

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],suppress_callback_exceptions=True, assets_folder='assets', assets_url_path='/assets/')

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Home", href="#", id="home-link", n_clicks=0)),
        dbc.NavItem(dbc.NavLink("Building Map Locator", href="#", id="building-locator-link",n_clicks=1)),
        dbc.NavItem(dbc.NavLink("Choropleth Map Locator", href="#", id="choropleth-locator-link",n_clicks=2)),
    ],
    brand="Solar Energy Dashboard",
    brand_href="#",
    color="dark",
    dark=True,
    className="fixed-top"
)

# ==== Electricity and CO2 Emissions Graph ===
# Create traces
trace1 = go.Scatter(x=consump['Year'], y=consump['Electricity consumption'], mode='lines+markers', name='Electricity Consumption', visible=True, line=dict(color='#4477AA'))
trace2 = go.Scatter(x=consump['Year'], y=consump['CO2 emissions'], mode='lines+markers', name='CO2 Emissions', visible=True, line=dict(color='#CCBB44'))


# Create layout
layout = go.Layout(title=go.layout.Title(text='Electricity Consumption and CO2 Emissions in the PH (1990-2021)', xanchor='left'),
                   xaxis=dict(title='Year'),
                   yaxis=dict(title='Consumption and Emissions'),
                   updatemenus=[dict(x=0.05,
                                     y=0.95,  # Adjusting the 'y' value slightly downwards
                                     xanchor='left',
                                     yanchor='top',
                                     buttons=[{'label': 'Electricity Consumption',
                                               'method': 'update',
                                               'args': [{'visible': [True, False]},
                                                        {'yaxis': {'title': 'Electricity Consumption (Terawatt hours, TWh)'}}]},
                                              {'label': 'CO2 Emissions',
                                               'method': 'update',
                                               'args': [{'visible': [False, True]},
                                                        {'yaxis': {'title': 'CO2 Emissions (Megatons, Mt)'}}]},
                                              {'label': 'Both',
                                               'method': 'update',
                                               'args': [{'visible': [True, True]},
                                                        {'yaxis': {'title': 'Consumption and Emissions'}}]}],
                                     # Set the default state of the dropdown to 'Both'
                                     direction='down',
                                     showactive=True,
                                     active=2)])

# Add hover info with units
trace1.hoverinfo = 'x+y+text'
trace2.hoverinfo = 'x+y+text'

# Define hover template with units
hover_template_electricity = 'Year: %{x}<br>%{y} TWh'
hover_template_co2 = 'Year: %{x}<br>%{y} Mt'

# Update hover templates
trace1.hovertemplate = hover_template_electricity
trace2.hovertemplate = hover_template_co2

consump_fig = go.Figure(data=[trace1, trace2], layout=layout)
# === End code ===

# === Electricity Generation by Source Stacked Bar Chart ===
colors = ['#4A4A4A', '#708090', '#96C98B', '#1E88E5', '#A52A2A', '#E88E5A', '#F2DB77', '#AED6F1', '#B8860B']
fig_gen = go.Figure()
# Add traces for each energy source
for i, source in enumerate(['Coal', 'Oil', 'Biofuels', 'Hydro', 'Geothermal', 'Natural gas', 'Solar PV', 'Wind', 'Biomass']):
    fig_gen.add_trace(go.Bar(
        x=gener['Year'],
        y=gener[source],
        name=source,
        marker_color=colors[i],
        hoverinfo='y+name',  # Display only y-value and name on hover
        hovertemplate='Year: %{x}<br>%{y} GWh'  # Include both y-value and x (Year) in hover
    ))
# Update layout
fig_gen.update_layout(
    barmode='stack',
    title='Electricity Generation by Source in the PH (1990-2021)',
    xaxis_title='Year',
    yaxis_title='Electricity Generation (Gigawatt hours, GWh)',
    showlegend=True,
    updatemenus=[
        {
            'buttons': [
                {
                    'args': [None, {'showlegend': False}],
                    'label': 'Show All',
                    'method': 'relayout'
                }
            ],
            'direction': 'down',
            'showactive': True,
            'x': 0.01,
            'xanchor': 'left',
            'y': 1,
            'yanchor': 'top'
        },
        {
            'buttons': [
                {
                    'args': [{'visible': [True] * len(fig_gen.data)}],
                    'label': 'All',
                    'method': 'update'
                }
            ],
            'direction': 'down',
            'showactive': True,
            'x': 0.01,
            'xanchor': 'left',
            'y': 0.9,
            'yanchor': 'top'
        },
        {
            'buttons': [
                {
                    'args': [{'visible': [True if i == idx else False for i in range(len(fig_gen.data))]}],
                    'label': source,
                    'method': 'update'
                } for idx, source in enumerate(['Coal', 'Oil', 'Biofuels', 'Hydro', 'Geothermal', 'Natural gas', 'Solar PV', 'Wind', 'Biomass'])
            ],
            'direction': 'down',
            'showactive': True,
            'x': 0.01,
            'xanchor': 'left',
            'y': 0.8,
            'yanchor': 'top'
        }
    ]
)
# Add checkbox for each energy source
fig_gen.update_layout(
    updatemenus=[
        {
            'buttons': [
                {
                    'args': [{'visible': [True if i == idx else False for i in range(len(fig_gen.data))]}],
                    'label': source,
                    'method': 'update'
                } for idx, source in enumerate(['Coal', 'Oil', 'Biofuels', 'Hydro', 'Geothermal', 'Natural gas', 'Solar PV', 'Wind', 'Biomass'])
            ],
            'direction': 'down',
            'showactive': True,
            'x': 0,
            'xanchor': 'left',
            'y': 1,
            'yanchor': 'top'
        },
        {
            'buttons': [
                {
                    'args': [{'visible': [True] * len(fig_gen.data)}],
                    'label': 'All',
                    'method': 'update'
                }
            ],
            'direction': 'down',
            'showactive': True,
            'x': 0.01,
            'xanchor': 'left',
            'y': 0.89,  # Adjust the y position to place it below the dropdown menu
            'yanchor': 'top'
        }
    ]
)
# === End Code ===

# === Renewable Energy Horizontal Bar Chart ===
renewables_color = '#4477AA'
nonrenewables_color = '#CCBB44'

# Create initial data for the chart (Renewables and Nonrenewables)
labels1 = ['Renewables', 'Nonrenewables']
values1 = [share['Renewables'].iloc[0], share['Nonrenewables'].iloc[0]]

# Create the horizontal bar chart
fig1_bar = go.Figure(data=[go.Bar(y=labels1, x=values1,
                              orientation='h',
                              marker=dict(color=[renewables_color, nonrenewables_color]),
                              name='Energy Share',
                              hovertemplate='%{x}%<extra></extra>')])

# Update layout for the chart (with title, legend, axis labels, and dropdown menu position)
fig1_bar.update_layout(title_text="Energy Generation Share in the PH",
                   title_x=0.5,  # Title position in the center
                   title_y=0.98,  # Title position from the top
                   margin=dict(l=100, r=20, t=60, b=80),  # Add space around the chart
                   width=800,  # Set width
                   height=400,  # Set height
                   xaxis_title="%",  # X-axis label
                   yaxis_title="Type of Energy",  # Y-axis label
                   legend=dict(x=0.05, y=0.95),  # Position of the legend
                   annotations=[
                       dict(
                           x=0.5,
                           y=-0.32,
                           xref='paper',
                           yref='paper',
                           text="Nonrenewables: Coal, Oil, Natural Gas<br>Renewables: Biofuels, Hydro, Geothermal, Solar PV, Wind, Biomass",
                           showarrow=False,
                           font=dict(size=10),
                           align='center'
                       )
                   ],
                   updatemenus=[dict(buttons=[
                       dict(method='update',
                            args=[{'y': [labels1],
                                   'x': [[share['Renewables'].iloc[i], share['Nonrenewables'].iloc[i]]],
                                   'marker.color': [[renewables_color, nonrenewables_color]],
                                   'title': f"Energy Share in the PH - {year}"}],
                            label=str(year)) for i, year in enumerate(share['Year'])],
                                    direction='down',
                                    showactive=True,
                                    x=0.95,  # Position of the dropdown menu on the x-axis
                                    xanchor='right',  # Align dropdown menu to the right
                                    y=0.05,  # Position of the dropdown menu on the y-axis
                                    yanchor='bottom')])
# === End Code ===

# === Supplementary Dropdown code ===
solar_options = []
for i in gadm_data_with_group.columns[17:]:
    solar_options.append({
        'label': i, 
        'value': i
    })
location_options = [{'label': location, 'value': location} for location in gadm_data_with_dropdup_group['NAME_2'].unique()]

#=== Cluster Map ===
geolocator = Nominatim(user_agent="dash-reverse-geocoder")
fig = px.scatter_mapbox(converted_gdf_indexed, 
                        lat=converted_gdf_indexed.geometry.centroid.y,
                        lon=converted_gdf_indexed.geometry.centroid.x,
                        hover_name="b_type",
                        color="b_type",
                        zoom=11,
                        height=1500,
                        width=1000)
fig.update_traces(cluster=dict(enabled=True))
#=== End Cluster Map ===

# Definining layout
app.layout = html.Div(style={'background-image': 'url("/assets/solar.png")', 
                             'background-size': 'cover', 'background-repeat': 'repeat',
                             'background-position': 'center', 'height': '250vh', 'background-color': 'rgba(0,0,0,0)',
                            },children=[
    navbar,
    dbc.Container(id="page-content",  style={'margin': '40px','margin-top': '50px'}),
])    
    
    
    
#=== Callback Function ===
# Callback to render page once a tab is clicked
@app.callback(
    Output("page-content", "children"),
    [Input("home-link", "n_clicks"),
     Input("building-locator-link", "n_clicks"),
     Input("choropleth-locator-link", "n_clicks")]
)
def render_content(home_clicks, building_types_clicks, choropleth_map_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        tab_id = "home-link"
    else:
        tab_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if tab_id == "home-link":
        return html.Div(children=[
            html.Div(children=[
                dbc.Row(children=[
                  dbc.Col(html.H6('''Solar energy is a renewable source of electricity derived from the sun's radiation.
                   It is harnessed using photovoltaic cells or solar panels that convert sunlight into energy through a process called the photovoltaic effect.'''), style={'text-align': 'justify'}),
                    ], style={'margin-bottom': '20px'}),
                dbc.Row(children=[
                  dbc.Col(html.H6('''The rising adoption of renewable energy stems from heightened environmental awareness and the urgent need to address climate change.
                   This global shift away from fossil fuels towards renewables is motivated by the recognition of their harmful environmental effects, such as greenhouse gas emissions, driving momentum towards cleaner, more sustainable energy solutions.'''), style={'text-align': 'justify'}),
                  ], style={'margin-bottom': '20px'}),
                dbc.Row(children=[
                  dbc.Col(html.H6(''' Despite abundant sunlight, the Philippines has not fully utilized its solar energy potential amidst growing environmental awareness.
                  Embracing rooftop solar panels in cities like Metro Manila can reduce carbon footprints, showcase sustainable practices, and enhance urban sustainability through renewable energy adoption.'''), style={'text-align': 'justify'}),
                  ], style={'margin-bottom': '20px'}),
            ], style={'background-color': 'rgba(50,50,50,0.5)', 'padding': '10px', 'color': 'white'}),
            html.Div(style={'margin-top': '40px'}, children=[
                dbc.Row(children=[
                    dbc.Col(children=[
                        dcc.Loading(id="map-loading", type="cube", children=dcc.Graph(id='consump_gofig',figure=consump_fig, responsive=True))
                    ],style={'width': '50%', 'display': 'inline-block', 'float': 'left'}),
                    dbc.Col(children=[
                        html.H3('Electricity Consumption and CO2 Emissions in the PH'),
                        html.H6('''Historically, the Philippines has relied heavily on fossil fuels for electricity generation,
                        particularly coal and natural gas. With a significant portion of electricity generation coming from fossil fuels, 
                        the Philippines faces challenges related to CO2 emissions and their environmental impact. 
                        Coal, in particular, is a major contributor to greenhouse gas emissions. Efforts to mitigate CO2 emissions include promoting energy 
                        efficiency measures, increasing the share of renewable energy in the energy mix, and implementing policies to reduce carbon intensity.''')
                    ],style={'background-color': 'rgba(50,50,50,0.5)', 'width': '50%','color': 'white', 'display': 'inline-block', 'float': 'right', 'margin-left': '20px','background-color': 'rgba(50, 50, 50, 0.5)'}),
                ]),
            ]),
            html.Div(style={'margin-top': '40px'}, children=[
                 dbc.Row(children=[
                    dbc.Col(children=[
                        html.H3('Energy Generation by Source'),
                        html.H6('''The energy generation in the Philippines comes from a mix of different sources namely coal,
                        natural gas, biomass, oil and renewable resources which includes hydropower, geothermal, wind, and solar energy. 
                        There has been a growing interest in renewable energy sources such as hydroelectric, geothermal, wind, solar,
                        and biomass as the Philippines is vulnerable to the impacts of climate change, and the movement to address CO2 emissions and 
                        transitioning to cleaner energy sources are crucial for mitigating impacts and building resilience. ''')
                    ],style={'background-color': 'rgba(50,50,50,0.5)', 'width': '50%', 'display': 'inline-block', 'float': 'left', 'color': 'white'}),
                    dbc.Col(children=[
                        dcc.Loading(id="map-loading", type="cube", children=dcc.Graph(id='gen_gofig',figure=fig_gen, responsive=True)),
                    ],style={'width': '50%', 'display': 'inline-block', 'float': 'right'}),
                ]),
            ]),
            html.Div(style={'margin-top': '40px'}, children=[
                dbc.Row(children=[
                     dbc.Col(children=[
                            dcc.Loading(id="map-loading", children=dcc.Graph(id='pie1_share',figure=fig1_bar, responsive=True)),
                    ],style={'width': '50%', 'height':'50%', 'display': 'inline-block', 'float': 'left'}),
                    dbc.Col(children=[
                        html.H3('Energy Generation Share in the PH'),
                        html.H6('''This bar chart categorizes energy sources into two main groups: Renewables and Nonrenewables, 
                        offering users a broad overview of the distribution of electricity generation sources. This enables them 
                        to make part-to-whole judgments and understand the relative contributions of renewables and nonrenewables 
                        to the total energy generated. ''')
                    ],style={'background-color': 'rgba(50,50,50,0.5)', 'width': '50%','color': 'white', 'display': 'inline-block', 'float': 'right', 'margin-left': '20px','background-color': 'rgba(50, 50, 50, 0.5)'}),
                ]),
            ]),
        ])
    elif tab_id == "building-locator-link":
        return html.Div(children=[
            dbc.Row(children=[
                 dbc.Col(children=[
                        html.H3('Building Map Locator', style={'text-align': 'center'}),
                        html.H6('''The Building Map Locator page contains the map that presents the different types of buildings located in the specified location. 
                        As observed, the circles on the map represent a different type of building and are distinguished by the color provided. 
                        While the number presented indicated the number of that particular building type in the location. '''),
                        html.H6('''Understanding the distribution and types of buildings in a particular area can be useful for various purposes:'''),
                        html.H5('''1. Urban & Energy Planning: ''', style={'margin-left': '40px'}),
                        html.H6('''Understanding land use patterns can aid in urban and energy planning through making appropriate plans for future infrastructure or 
                        development projects. In addition, gaining information on the kinds and locations of buildings can help determine the possibility of 
                        installing solar panels and estimate the area's capacity for producing solar energy.''', style={'margin-left': '80px'}),
                     html.H5('''2. Economic Analysis: ''', style={'margin-left': '40px'}),
                     html.H6('''Examining the different building types and their locations can provide important information about the opportunities for economic 
                     activity in the region. This information can then be used to guide business decisions and strategies for economic development.''', style={'margin-left': '80px'})
                    ],style={'background-color': 'rgba(50,50,50,0.5)', 'width': '50%', 'display': 'inline-block', 'float': 'left', 'color': 'white', 'margin-bottom': '40px'}),
           ],justify="center"),
            dbc.Row(children=[
                dbc.Col(children=[
                   dcc.Loading(id="map-loading", type="cube", children=dcc.Graph(id='cluster-map', figure=fig, responsive=True)),
               ],align="center", style={'display': 'inline-block'}),
            ], justify="center"),
             dbc.Row(children=[
                dbc.Col(children=[
                   html.H6(id='potential-info',style={'text-align': 'center', 'color': 'white'}),
               ],align="center", style={'background-color': 'rgba(50,50,50,0.5)', 'width': '50%', 'display': 'inline-block', 'color': 'white', 'margin-top': '40px'}),
            ], justify="center"),
            ])
    elif tab_id == "choropleth-locator-link":
        return html.Div(children=[
            dbc.Row(children=[
                html.H3('Choropleth Map Locator', style={'text-align': 'center', 'background-color': 'rgba(50,50,50,0.5)', 'color': 'white'}),
            ]),
            dbc.Container(children=[
            dbc.Row(children=[
               html.H6('''The Choropleth Map presents the geographic information on suitable areas, 
               as well as energy capacity and yearly potential power for various cities. Different colors on the 
               map represent different levels of energy capacity and potential, making it easy for users to see how things 
               differ across locations. The main goal of the map is to help users understand these differences and compare them
               between cities.''', style={'margin-bottom': '10px'}), 
            ], style={'margin-bottom': '40px','background-color': 'rgba(50,50,50,0.5)', 'color': 'white'})
            ]),
            dbc.Row(children=[
            dcc.Dropdown(
            id='solar-dropdown',
            options=solar_options,
            value=solar_options[0]['value']
        )
           ],align="center",style={'margin': '20px'}),
             dbc.Row(children=[
            dcc.Dropdown(
            id='location-filter',
            options=location_options,
            value=location_options[0]['value']
        )
           ],align="center",style={'margin': '20px'}),
            dbc.Container(children=[
                dbc.Row(children=[
                    dcc.Loading(id="map-loading", type="cube", children=dcc.Graph(id='bar-chart'))
                ])
            ]),

                dbc.Container(children=[
                    dbc.Row(children=[
                        dbc.Col(children=[
                            dcc.Loading(id="map-loading", type="cube", children=dcc.Graph(id='left-graph', responsive=True))
                       ], style={'width': '49%', 'display': 'inline-block', 'float': 'left'}),
                        dbc.Col(children=[
                           dcc.Loading(id="map-loading", type="cube", children=dcc.Graph(id='right-graph', responsive=True))
                       ], style={'width': '49%', 'display': 'inline-block', 'float': 'right'}),
            
            ], style={'margin-top': '40px'}),
        ]),

    ])
    
@app.callback(
    Output('potential-info', 'children'),
    [Input('cluster-map', 'clickData')]
)
def display_click_data(clickData):
    print("Clicked data:", clickData)
    if clickData is not None:
        # Get the index of the clicked point
        point_index = clickData['points'][0]['pointIndex']
        lat = clickData['points'][0]['lat']
        lon = clickData['points'][0]['lon']
        location = geolocator.reverse((lat, lon))
        # Get the corresponding potential value from your data
        potential_value = converted_gdf_indexed.iloc[point_index]['potential']
        capacity_value = converted_gdf_indexed.iloc[point_index]['capacity']
        suitarea_value = converted_gdf_indexed.iloc[point_index]['capacity']
        # Display the potential value

        return html.Div([
            html.P('Exact Location: ' + str(location.address)),
            html.P('Estimated Suitable Area: ' + str(suitarea_value) + ' sq. meters'),
            html.P('Estimated Installable Capacity: ' + str(capacity_value) + ' kWp'),
            html.P('Estimated Annual Power Potential: ' + str(potential_value) + ' kWh'),
            
        ])
    
    else:
        return html.P('Information will be display here once a data point is clicked.'),
    
@app.callback(
    Output('left-graph', 'figure'),
    [Input('solar-dropdown', 'value')],
    [Input('location-filter', 'value')]
)
#Bottom left graph
def update_left_graph(selected_option,selected_location):
    filtered_data = gadm_data_with_group[gadm_data_with_group['NAME_2'] == selected_location]
    fig = px.choropleth_mapbox(
        filtered_data,
        geojson=filtered_data.geometry,
        locations=filtered_data.index,
        color=selected_option,
        mapbox_style="carto-positron",
        center={"lat": 14.61, "lon": 121.0},
        zoom=11,
        opacity=0.8,
        color_continuous_scale="Viridis",
        labels={selected_option: selected_option},
        hover_name='NAME_3',
        hover_data={selected_option: True},
        height=700
    )
    fig.update_layout(
        title='Max Capacity Distribution per NAME_3',
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    return fig

# Bottom right graph
@app.callback(
    Output('right-graph', 'figure'),
    [Input('solar-dropdown', 'value')],
    [Input('location-filter', 'value')]
)
def update_right_graph(selected_option,selected_location):
    filtered_data = merged_data[merged_data['NAME_2'] == selected_location]
    scatter_data = filtered_data.explode().reset_index()  
    scatter_data['centroid_lon'] = scatter_data.geometry.centroid.x
    scatter_data['centroid_lat'] = scatter_data.geometry.centroid.y

    fig = px.scatter_mapbox(
        scatter_data,
        lat='centroid_lat',
        lon='centroid_lon',
        color=selected_option,
        hover_name='NAME_3',
        hover_data={selected_option: True},
        labels={'centroid_lat': 'Latitude', 'centroid_lon': 'Longitude'},
        height=700
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=11,
        mapbox_center={"lat": 14.61, "lon": 121.0},
        coloraxis_colorbar=dict(title=selected_option),
        margin=dict(l=0, r=0, t=0, b=0)
    )
    return fig

@app.callback(
    Output('bar-chart', 'figure'),
    [Input('solar-dropdown', 'value')],
    [Input('location-filter', 'value')]
)
def update_bar_chart(selected_name,location_options):
    filtered_data = gadm_data_with_dropdup_group[gadm_data_with_dropdup_group['NAME_2'] == location_options]
    filtered_data_sorted = filtered_data.sort_values(by=selected_name, ascending=False).head(20)
    fig = px.bar(filtered_data_sorted, x='NAME_3', y=selected_name, title=str(selected_name) + str(" By Area"), color='NAME_3')
    fig.update_layout(xaxis_title='Area', yaxis_title=str(selected_name))
    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
#=== End Callback Function ===