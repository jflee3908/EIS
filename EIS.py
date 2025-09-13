import pandas as pd
import glob
import os
import plotly.graph_objects as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# --- Step 1: Find all .mpt files in the 'data' subfolder ---
# The path 'data/*.mpt' finds all files ending in .mpt inside the data folder.
mpt_files = glob.glob('txt/*.mpt')

# --- Step 2: Load data from the found paths into memory ---
cell_data = {}
for filepath in mpt_files:
    try:
        df = pd.read_csv(filepath, sep='\t', skiprows=63, encoding='latin-1')
        if 'Re(Z)/Ohm' in df.columns and '-Im(Z)/Ohm' in df.columns:
            filename = os.path.basename(filepath)
            cell_name = os.path.splitext(filename)[0]
            cell_data[cell_name] = df
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

# --- Step 3: Initialize the Dash App ---
app = dash.Dash(__name__)
app.title = "Nyquist Plot Viewer"
server = app.server

# --- Step 4: Define the App Layout ---
app.layout = html.Div([
    html.H1("EIS", style={'textAlign': 'center'}),
    html.Hr(),
    html.Div([
        html.Label("Cell Numbers:", style={'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='cell-dropdown',
            options=[{'label': name, 'value': name} for name in cell_data.keys()],
            value=[],
            multi=True,
            placeholder="Search and select one or more cells..."
        ),
    ], style={'width': '95%', 'margin': 'auto', 'padding': '10px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),
    dcc.Graph(id='nyquist-plot', style={'height': '70vh'})
])

# --- Step 5: Define the Callback to Update the Graph ---
@app.callback(
    Output('nyquist-plot', 'figure'),
    Input('cell-dropdown', 'value')
)
def update_graph(selected_cells):
    fig = go.Figure()
    for cell_name in selected_cells:
        df = cell_data[cell_name]
        fig.add_trace(go.Scatter(
            x=df['Re(Z)/Ohm'],
            y=df['-Im(Z)/Ohm'],
            name=cell_name,
            mode='lines+markers',
            hovertemplate='<b>Re(Z)</b>: %{x:.3f} Ohm<br><b>-Im(Z)</b>: %{y:.3f} Ohm'
        ))

    fig.update_layout(
        xaxis_title="Re(Z) (Ohm)",
        yaxis_title="-Im(Z) (Ohm)",
        legend_title_text="Files",
        template="plotly_white",
        yaxis_scaleanchor="x",
        yaxis_scaleratio=1
    )
    if not selected_cells:
        fig.add_annotation(
            text="Use the search box above to select cells to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20, color="grey")
        )
    return fig

# --- Step 6: Run the App's Web Server ---
if __name__ == '__main__':
    if not cell_data:
        print("❌ No valid .mpt files found in the 'data' folder. The app will not run.")
    else:
        app.run(debug=False)
