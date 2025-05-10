import dash
from dash import dcc, html, Input, Output, State, ctx, dash_table
import pandas as pd
import plotly.express as px
import base64
import io

app = dash.Dash(__name__)
app.title = "CSV Data Visualization"

app.layout = html.Div([
    html.H2("📊 Data Visualization App with Dash", style={"textAlign": "center"}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Drag and Drop or ', html.A('Select CSV File')]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px'
        },
        multiple=False
    ),

    html.Div(id='output-data-upload'),
    html.Div(id='dropdown-container'),

    dcc.Graph(id='data-graph')
])

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    except Exception as e:
        return html.Div(['❌ Error processing file: ', str(e)])
    
    return df

@app.callback(
    Output('dropdown-container', 'children'),
    Output('output-data-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
)
def update_dropdown(contents, filename):
    if contents is None:
        return dash.no_update, None

    df = parse_contents(contents, filename)
    if isinstance(df, pd.DataFrame):
        options = [{'label': col, 'value': col} for col in df.columns]

        return (
            html.Div([
                html.Hr(),
                html.Label("Chọn trục X:"),
                dcc.Dropdown(id='xaxis-dropdown', options=options, value=df.columns[0]),
                html.Label("Chọn trục Y:"),
                dcc.Dropdown(id='yaxis-dropdown', options=options, value=df.columns[1]),
                html.Label("Chọn loại biểu đồ:"),
                dcc.Dropdown(
                    id='chart-type',
                    options=[
                        {'label': 'Line', 'value': 'line'},
                        {'label': 'Bar', 'value': 'bar'},
                        {'label': 'Scatter', 'value': 'scatter'}
                    ],
                    value='line'
                ),
                html.Button("📈 Vẽ biểu đồ", id='plot-button', n_clicks=0),
                html.Hr()
            ]),
            dash_table.DataTable(
                data=df.head().to_dict('records'),
                columns=[{'name': i, 'id': i} for i in df.columns],
                page_size=5
            )
        )
    else:
        return None, df  # error message div

@app.callback(
    Output('data-graph', 'figure'),
    Input('plot-button', 'n_clicks'),
    State('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('xaxis-dropdown', 'value'),
    State('yaxis-dropdown', 'value'),
    State('chart-type', 'value')
)
def update_graph(n_clicks, contents, filename, x_col, y_col, chart_type):
    if n_clicks == 0 or not contents:
        return dash.no_update

    df = parse_contents(contents, filename)
    if not isinstance(df, pd.DataFrame):
        return dash.no_update

    fig = getattr(px, chart_type)(df, x=x_col, y=y_col, title=f"{chart_type.title()} Chart")
    return fig

if __name__ == '__main__':
    app.run(debug=True)
