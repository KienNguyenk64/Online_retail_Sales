import dash
from dash import html, dcc, Input, Output, State
import dash_table
import plotly.express as px
import pandas as pd
import base64
import io
from flask_caching import Cache

# Initialize Dash app
app = dash.Dash(__name__)
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})

# Global DataFrame
df_global = pd.DataFrame()

# Layout
app.layout = html.Div([
    html.H1("Dash Data Visualization App", style={'textAlign': 'center'}),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center', 'margin': '10px'
        },
        multiple=False
    ),
    html.Div(id='file-info'),

    # Control Panel
    html.Div([
        html.Div([
            html.Label('Select X-axis:'),
            dcc.Dropdown(id='xaxis-dropdown')
        ], style={'width': '20%', 'display': 'inline-block', 'padding': '0 10px'}),
        html.Div([
            html.Label('Select Y-axis:'),
            dcc.Dropdown(id='yaxis-dropdown')
        ], style={'width': '20%', 'display': 'inline-block', 'padding': '0 10px'}),
        html.Div([
            html.Label('Select Color:'),
            dcc.Dropdown(id='color-dropdown')
        ], style={'width': '20%', 'display': 'inline-block', 'padding': '0 10px'}),
        html.Div([
            html.Label('Select Chart Type:'),
            dcc.Dropdown(
                id='chart-type-dropdown',
                options=[
                    {'label': 'Scatter', 'value': 'scatter'},
                    {'label': 'Bar', 'value': 'bar'},
                    {'label': 'Line', 'value': 'line'},
                    {'label': 'Histogram', 'value': 'histogram'},
                    {'label': 'Box', 'value': 'box'}
                ],
                value='scatter',
                clearable=False
            )
        ], style={'width': '20%', 'display': 'inline-block', 'padding': '0 10px'}),
    ], style={'margin': '10px 0'}),

    # Search and Filters
    html.Div([
        html.Div([
            html.Label('Filter Search:'),
            dcc.Input(id='search-input', type='text', placeholder='Search...')
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '0 10px'}),
        html.Div([
            html.Label('Date Range:'),
            dcc.DatePickerRange(id='date-picker', start_date=None, end_date=None)
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '0 10px'}),
        html.Div([
            html.Label('X Numeric Range:'),
            dcc.RangeSlider(id='x-range-slider', min=0, max=100, step=1, value=[0, 100]),
            html.Div(id='x-slider-output')
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '0 10px'})
    ], style={'margin': '20px 0'}),
    html.Div([
        html.Div([
            html.Label('Y Numeric Range:'),
            dcc.RangeSlider(id='y-range-slider', min=0, max=100, step=1, value=[0, 100]),
            html.Div(id='y-slider-output')
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '0 10px'})
    ], style={'margin': '20px 0'}),

    # Main Graph
    dcc.Graph(id='main-graph'),

    # Data Table
    html.H2('Data Table'),
    dash_table.DataTable(
        id='data-table',
        columns=[],
        data=[],
        filter_action='native',
        sort_action='native',
        page_size=10,
        export_format='csv'
    ),
])

# Parse uploaded file and cache
@cache.memoize()
def parse_data(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error parsing file {filename}: {e}")
        return pd.DataFrame()
    return df

# Update global df and dropdown options
@app.callback(
    [Output('file-info', 'children'),
     Output('xaxis-dropdown', 'options'),
     Output('yaxis-dropdown', 'options'),
     Output('color-dropdown', 'options')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_file(contents, filename):
    global df_global
    if contents:
        df = parse_data(contents, filename)
        df_global = df
        cols = [{'label': col, 'value': col} for col in df.columns]
        # Optionally dynamically set x/y sliders
        return (
            html.Div(f"Loaded {filename} with {df.shape[0]} rows and {df.shape[1]} columns."),
            cols, cols, cols
        )
    return html.Div("No file loaded."), [], [], []

# Update graph and table based on filters and chart type
@app.callback(
    [Output('main-graph', 'figure'),
     Output('data-table', 'columns'),
     Output('data-table', 'data')],
    [
        Input('xaxis-dropdown', 'value'),
        Input('yaxis-dropdown', 'value'),
        Input('color-dropdown', 'value'),
        Input('chart-type-dropdown', 'value'),
        Input('search-input', 'value'),
        Input('date-picker', 'start_date'),
        Input('date-picker', 'end_date'),
        Input('x-range-slider', 'value'),
        Input('y-range-slider', 'value')
    ]
)
def update_graph_table(xcol, ycol, ccol, chart_type, search, start_date, end_date, x_range, y_range):
    dff = df_global.copy()
    # Text search filter
    if search:
        mask = dff.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        dff = dff[mask]
    # Date range filter
    if start_date and end_date:
        for col in dff.columns:
            if pd.api.types.is_datetime64_any_dtype(dff[col]) or 'date' in col.lower():
                try:
                    dff[col] = pd.to_datetime(dff[col])
                    dff = dff[(dff[col] >= start_date) & (dff[col] <= end_date)]
                except:
                    continue
    # Numeric range filter on selected X axis
    if xcol and pd.api.types.is_numeric_dtype(dff[xcol]):
        dff = dff[(dff[xcol] >= x_range[0]) & (dff[xcol] <= x_range[1])]
    # Numeric range filter on selected Y axis
    if ycol and pd.api.types.is_numeric_dtype(dff[ycol]):
        dff = dff[(dff[ycol] >= y_range[0]) & (dff[ycol] <= y_range[1])]
    # Build figure based on chart type
    if chart_type == 'scatter' and xcol and ycol:
        fig = px.scatter(dff, x=xcol, y=ycol, color=ccol)
    elif chart_type == 'bar' and xcol and ycol:
        fig = px.bar(dff, x=xcol, y=ycol, color=ccol)
    elif chart_type == 'line' and xcol and ycol:
        fig = px.line(dff, x=xcol, y=ycol, color=ccol)
    elif chart_type == 'histogram' and xcol:
        fig = px.histogram(dff, x=xcol, color=ccol)
    elif chart_type == 'box' and xcol and ycol:
        fig = px.box(dff, x=xcol, y=ycol, color=ccol)
    else:
        fig = px.scatter(title="Please select valid X and Y columns for the chosen chart type.")
    # Update DataTable
    columns = [{'name': col, 'id': col} for col in dff.columns]
    data = dff.to_dict('records')
    return fig, columns, data

# Update slider output displays
@app.callback(
    Output('x-slider-output', 'children'),
    Input('x-range-slider', 'value')
)
def display_x_slider(value):
    return f"X range: {value[0]} to {value[1]}"

@app.callback(
    Output('y-slider-output', 'children'),
    Input('y-range-slider', 'value')
)
def display_y_slider(value):
    return f"Y range: {value[0]} to {value[1]}"

# if __name__ == '__main__':
#     app.run(debug=True)

app.run(debug=True, host='0.0.0.0', port='8888')