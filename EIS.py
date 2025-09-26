import pandas as pd
import glob
import os
import plotly.graph_objects as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from datetime import datetime
import io

# --- Step 1: Load all data into memory ---
mpt_files = glob.glob('txt/*.mpt')
files_found_count = len(mpt_files)
cell_data = {}
failed_files = []
for filepath in mpt_files:
    try:
        df = pd.read_csv(filepath, sep='\t', skiprows=63, encoding='latin-1')
        if 'Re(Z)/Ohm' in df.columns and '-Im(Z)/Ohm' in df.columns:
            filename = os.path.basename(filepath)
            cell_name = os.path.splitext(filename)[0]
            cell_data[cell_name] = df
        else:
            failed_files.append(os.path.basename(filepath))
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        failed_files.append(os.path.basename(filepath))
        
files_loaded_count = len(cell_data)
status_message = f"Status: Successfully loaded {files_loaded_count} of {files_found_count} .mpt files found in the 'data' folder."

#Find the file with the largest initial number
largest_file_message = "Largest Cell Number: None"
if mpt_files:
    try:
        largest_filepath = max(mpt_files, key=lambda p: int(os.path.basename(p).split('_')[0]))
        largest_cell_name = os.path.splitext(os.path.basename(largest_filepath))[0]
        largest_file_message = f"Largest Cell Number: {largest_cell_name}"
    except (ValueError, IndexError):
        largest_file_message = "Largest Cell Number: Could not parse filenames."

if failed_files:
    failed_files_content = [
        html.P("The following files could not be loaded and were ignored,",
               style={'color': '#d9534f', 'fontWeight': 'bold', 'marginTop': '10px'}),
        html.Ul([html.Li(f) for f in sorted(failed_files)])
    ]
else:
    failed_files_content = [] #render nothing if all files loaded successfully
    
def parse_search_string(query_string):
    """Parses a string with numbers and ranges (e.g., '1-3, 5') into a set of strings."""
    if not query_string:
        return set()
    
    ids = set()
    parts = query_string.split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start > end:
                    start, end = end, start
                for i in range(start, end + 1):
                    ids.add(str(i))
            except ValueError:
                continue
        else:
            if part.isdigit():
                ids.add(part)
    return ids

def get_legend_name(full_cell_name):
    """Extracts the part of the name before the final '_C##' suffix."""
    parts = full_cell_name.rsplit('_', 1)
    if len(parts) == 2 and parts[1].startswith('C') and parts[1][1:].isdigit():
        return parts[0]
    return full_cell_name

# --- Step 2: Initialize the Dash App ---
app = dash.Dash(__name__)
app.title = "US SD EIS"
server = app.server

# --- Step 3: Define the App Layout ---
app.layout = html.Div([
    html.Div([
        html.H1("EIS", style={'textAlign': 'left', 'margin': '0'}),
        html.Button("Download Data (.csv)", id="download-button", style={
            'padding': '6px 12px', 'fontSize': '14px'
        })
    ], style={
        'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
        'padding': '10px 2.5%'
    }),
    
    html.Hr(),
    
    html.Div([
        html.Label("Enter Cell IDs (e.g., 17153, 17155-17157):", style={'fontWeight': 'bold', 'display': 'block'}),
        dcc.Input(id='search-box', type='text', placeholder="Enter IDs and press Enter or click Search...", style={'width': '80%', 'marginRight': '1%'}),
        html.Button('Search', id='search-button', n_clicks=0, style={'width': '18%'}),
    ], style={'width': '95%', 'margin': 'auto', 'padding': '10px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),
    
    dcc.Graph(id='nyquist-plot', style={'height': '70vh'}, config={'scrollZoom': True}),

    html.Div(
        children=[
            html.P(status_message, style={'textAlign': 'center', 'color': 'grey', 'fontStyle': 'italic'}),
            html.P(largest_file_message, style={'textAlign': 'center', 'color': 'grey', 'fontStyle': 'italic', 'margin': '2px'})
    ], style={'width': '95%', 'margin': '10px auto'}),
    
    html.Div(children=failed_files_content, style={'width': '95%', 'margin': 'auto'}),
    
    dcc.Download(id="download-data-csv"),
    dcc.Store(id='plotted-data-store')
])

# --- Step 4: Define Callbacks ---
@app.callback(
    Output('nyquist-plot', 'figure'),
    Output('plotted-data-store', 'data'),
    Input('search-button', 'n_clicks'),
    Input('search-box', 'n_submit'),
    State('search-box', 'value')
)
def update_graph_and_store_data(button_clicks, enter_presses, search_query):
    # Check if the callback was triggered by any user action yet
    if button_clicks == 0 and (enter_presses is None or enter_presses == 0):
        fig = go.Figure()
        fig.add_annotation(text="Enter Cell IDs and click Search or press Enter", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=20, color="grey"))
        return fig, None

    target_ids = parse_search_string(search_query)
    fig = go.Figure()
    
    plotted_dfs = []
    if target_ids:
        for exp_id in sorted(list(target_ids)):
            matching_cells = [cell for cell in cell_data.keys() if cell.split('_')[0] == exp_id]
            for cell_name in matching_cells:
                df = cell_data[cell_name]
                legend_name = get_legend_name(cell_name)
                
                fig.add_trace(go.Scatter(
                    x=df['Re(Z)/Ohm'], y=df['-Im(Z)/Ohm'], name=legend_name,
                    legendgroup=legend_name, customdata=[cell_name] * len(df),
                    hovertemplate='<b>Cell</b>: %{customdata}<br><b>Re(Z)</b>: %{x:.3f} Ohm<br><b>-Im(Z)</b>: %{y:.3f} Ohm',
                    mode='lines+markers'
                ))
                
                df_to_store = df.copy()
                df_to_store['source_file'] = cell_name
                plotted_dfs.append(df_to_store)

    fig.update_layout(
        xaxis_title="Re(Z) (Ohm)", yaxis_title="-Im(Z) (Ohm)",
        legend_title_text="Experiment Name", template="plotly_white",
        yaxis_scaleratio=1,
    )
    
    if not plotted_dfs:
        fig.add_annotation(text="No matching cells found.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=20, color="grey"))
        return fig, None

    combined_df = pd.concat(plotted_dfs, ignore_index=True)
    return fig, combined_df.to_json(orient='split')

@app.callback(
    Output("download-data-csv", "data"),
    Input("download-button", "n_clicks"),
    State("plotted-data-store", "data"),
    prevent_initial_call=True,
)
def download_data(n_clicks, json_data):
    if not json_data:
        return
    
    df_long = pd.read_json(io.StringIO(json_data), orient='split')
    
    df_long['measurement_index'] = df_long.groupby('source_file').cumcount()
    
    df_wide = df_long.pivot(
        index='measurement_index', 
        columns='source_file', 
        values=['Re(Z)/Ohm', '-Im(Z)/Ohm']
    )
    
    df_wide.columns = [f'{val}_{col}' for val, col in df_wide.columns]
    df_wide = df_wide.reindex(sorted(df_wide.columns), axis=1)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"nyquist_data_wide_{timestamp}.csv"
    return dcc.send_data_frame(df_wide.to_csv, filename, index=False)

# --- Step 5: Run the App's Web Server ---
if __name__ == '__main__':
    if not cell_data:
        print("❌ No valid .mpt files found in the 'data' folder. The app will not run.")
    else:
        app.run(debug=False)
