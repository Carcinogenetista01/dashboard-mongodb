import dash
from dash import Dash, dcc, html, Input, Output, callback, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dateutil import parser
from io import StringIO
from dash.exceptions import PreventUpdate
from flask import Flask, send_from_directory

server = Flask(__name__)  # Esta variable DEBE llamarse 'server'
# Ruta para el root (dashboard principal)
@server.route('/')
def dash_app():
    return app.index()

# Rutas para archivos estáticos
@server.route('/home.html')
def serve_home():
    return send_from_directory('.', 'home.html')

@server.route('/login.html')
def serve_login():
    return send_from_directory('.', 'login.html')

# Ruta para assets (CSS, imágenes)
@server.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory('assets', path)


app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Conexión a MongoDB Atlas
client = MongoClient("mongodb+srv://joseadmon:1@cluster0.7gchhux.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["calidad_aire_2"]

# Paleta de colores para contaminantes (verdes y compatibles)
CONTAMINANT_COLORS = {
    "PM2.5": "#43a047",
    "PM10": "#388e3c",
    "O3": "#66bb6a",
    "SO2": "#81c784",
    "NO2": "#a5d6a7",
    "CO": "#c8e6c9"
}

# ========== Layout del Dashboard ==========
app.title = "GreenTech Solutions - Monitoreo Atmosférico"

app.layout = dbc.Container([
    # Navbar
    dbc.Navbar(
        dbc.Container([
            html.A(
                dbc.Row([
                    dbc.Col(html.Img(src="assets/logo.png", height="100px", className="me-3")),
                    dbc.Col(html.H3("GreenTech Solutions", className="mb-0 fw-bold", style={"color": "#388e3c"})),
                ], align="center", className="g-0"),
                href="#",
                style={"textDecoration": "none"}
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse(
                dbc.Row([
                    dbc.Col(
                        dbc.ButtonGroup(
                            [
                                dbc.Button("Mediciones", id="btn-mediciones", color="success", outline=True, n_clicks=0, className="fw-bold"),
                                dbc.Button("Pronósticos", id="btn-forecast", color="secondary", outline=True, n_clicks=0, className="fw-bold"),
                            ],
                            size="md",
                            className="me-3"
                        ),
                        width="auto"
                    ),
                    dbc.Col(
                        html.Div(id="data-source-legend", className="text-muted small"),
                        width="auto"
                    ),
                    dbc.Col(
                        html.Div(id="last-update", className="text-end text-success fw-bold"),
                        width="auto"
                    ),
                ], className="g-2 align-items-center justify-content-end flex-nowrap"),
                id="navbar-collapse",
                is_open=True,
                navbar=True,
            ),
        ], fluid=True),
        color="white",
        dark=False,
        sticky="top",
        className="shadow-sm border-bottom mb-4"
    ),
    # Componente oculto para almacenar la fuente de datos seleccionada
    dcc.Store(id='data-source', data='mediciones'),
    # Filtros principales
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Filtros", className="card-title mb-3 fw-bold text-success"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Estado:", className="fw-bold text-success"),
                            dcc.Dropdown(
                                id='state-filter',
                                options=[],
                                value=None,
                                clearable=False,
                                className="mb-2"
                            )
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Contaminante:", className="fw-bold text-success"),
                            dcc.Dropdown(
                                id='pollutant-filter',
                                options=[],
                                value=None,
                                clearable=False,
                                className="mb-2"
                            )
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Estación:", className="fw-bold text-success"),
                            dcc.Dropdown(
                                id='station-filter',
                                options=[],
                                value=None,
                                clearable=False,
                                className="mb-2"
                            )
                        ], md=4)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Fecha y Hora:", className="fw-bold text-success"),
                            html.Div([
                                dcc.DatePickerRange(
                                    id='date-range',
                                    min_date_allowed=datetime(2023, 1, 1),
                                    max_date_allowed=datetime.today(),
                                    start_date=datetime.today() - timedelta(days=7),
                                    end_date=datetime.today(),
                                    className="mb-2"
                                ),
                                html.Div([
                                    dbc.Label("Hora inicial:", className="fw-bold text-success me-2"),
                                    dcc.Slider(
                                        id='start-hour',
                                        min=0, max=23, step=1, value=0,
                                        marks={i: f"{i}:00" for i in range(0, 24, 3)},
                                        tooltip={"placement": "bottom", "always_visible": False},
                                        className="mb-2"
                                    ),
                                    dbc.Label("Hora final:", className="fw-bold text-success me-2"),
                                    dcc.Slider(
                                        id='end-hour',
                                        min=0, max=23, step=1, value=23,
                                        marks={i: f"{i}:00" for i in range(0, 24, 3)},
                                        tooltip={"placement": "bottom", "always_visible": False},
                                        className="mb-2"
                                    ),
                                ], className="mt-2")
                            ])
                        ], md=8),
                        dbc.Col([
                            dbc.Label("Rango de Valores:", className="fw-bold text-success"),
                            dcc.RangeSlider(
                                id='value-range',
                                min=0,
                                max=500,
                                step=10,
                                marks={0: '0', 100: '100', 200: '200', 300: '300', 400: '400', 500: '500'},
                                value=[0, 200],
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], md=4)
                    ], className="mt-3")
                ])
            ], className="shadow-lg rounded-4 border-0 mb-4 bg-white p-3")
        ], width=12)
    ]),

    # KPIs
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Valor Promedio", className="card-subtitle text-muted"),
                    html.H2(id="avg-value", className="card-title text-center text-success fw-bold"),
                    html.P(id="value-unit", className="card-text text-center")
                ])
            ], className="shadow-sm text-center border-0 rounded-4 bg-light")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Máximo Registrado", className="card-subtitle text-muted"),
                    html.H2(id="max-value", className="card-title text-center text-danger fw-bold"),
                    html.P(id="max-location", className="card-text text-center")
                ])
            ], className="shadow-sm text-center border-0 rounded-4 bg-light")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Mínimo Registrado", className="card-subtitle text-muted"),
                    html.H2(id="min-value", className="card-title text-center text-success fw-bold"),
                    html.P(id="min-location", className="card-text text-center")
                ])
            ], className="shadow-sm text-center border-0 rounded-4 bg-light")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Nivel de Riesgo", className="card-subtitle text-muted"),
                    html.H2(id="risk-level", className="card-title text-center text-warning fw-bold"),
                    html.P(id="risk-description", className="card-text text-center")
                ])
            ], className="shadow-sm text-center border-0 rounded-4 bg-light")
        ], md=3)
    ], className="mb-4"),

    # Gráficos principales
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Tendencia Temporal", className="fw-bold text-success"),
                dbc.CardBody([
                    dcc.Graph(id='time-series-chart', config={"displayModeBar": False})
                ])
            ], className="shadow-lg rounded-4 border-0 bg-white mb-4")
        ], md=8),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Concentración por Contaminante", className="fw-bold text-success"),
                dbc.CardBody([
                    dcc.Graph(id='contaminant-bar', config={"displayModeBar": False})
                ])
            ], className="shadow-lg rounded-4 border-0 bg-white mb-4")
        ], md=4),
    ]),

    # Mapa y análisis detallado
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Mapa de Contaminación", className="fw-bold text-success"),
                dbc.CardBody([
                    dcc.Graph(id='pollution-map', config={"displayModeBar": False})
                ])
            ], className="shadow-lg rounded-4 border-0 bg-white mb-4")
        ], md=7),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Análisis por Contaminante", className="fw-bold text-success"),
                dbc.CardBody([
                    dcc.Graph(id='pollutant-analysis', config={"displayModeBar": False})
                ])
            ], className="shadow-lg rounded-4 border-0 bg-white mb-4")
        ], md=5)
    ]),

    # Almacenamiento de datos
    dcc.Store(id='filtered-data'),
    dcc.Interval(
        id='interval-component',
        interval=3600*1000,  # Actualizar cada hora
        n_intervals=0
    )
], fluid=True, className="py-4 bg-white")

# ========== Callbacks ==========

@app.callback(
    Output('data-source', 'data'),
    [Input('btn-mediciones', 'n_clicks'), Input('btn-forecast', 'n_clicks')],
    prevent_initial_call=True
)
def toggle_data_source(btn_mediciones, btn_forecast):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "btn-mediciones":
        return "mediciones"
    elif button_id == "btn-forecast":
        return "forecast"
    raise PreventUpdate

@app.callback(
    [Output('btn-mediciones', 'color'), Output('btn-forecast', 'color')],
    [Input('data-source', 'data')]
)
def update_button_colors(data_source):
    if data_source == "mediciones":
        return "success", "secondary"
    else:
        return "secondary", "success"

@app.callback(
    Output('data-source-legend', 'children'),
    [Input('data-source', 'data')]
)
def update_legend(data_source):
    if data_source == "mediciones":
        return "Mediciones: Datos reales obtenidos de sensores en tiempo real."
    else:
        return "Pronósticos: Datos estimados a partir de modelos predictivos."

@app.callback(
    Output('last-update', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_last_update(n):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return f"Última actualización (live): {now}"

@app.callback(
    [
        Output('state-filter', 'options'),
        Output('state-filter', 'value'),
        Output('pollutant-filter', 'options'),
        Output('pollutant-filter', 'value'),
        Output('station-filter', 'options'),
        Output('station-filter', 'value'),
    ],
    [
        Input('data-source', 'data'),
        Input('state-filter', 'value'),
        Input('pollutant-filter', 'value'),
        Input('station-filter', 'value'),
        Input('interval-component', 'n_intervals')
    ]
)
def update_cascade_filters(data_source, state, pollutant, station, n_intervals):
    collection = db[data_source]
    # 1. Estados siempre disponibles
    states = collection.distinct('estado')
    state_options = [{'label': 'Todos', 'value': 'Todos'}] + [{'label': s, 'value': s} for s in states]
    state_value = state if state in states or state == 'Todos' else 'Todos'

    # 2. Si no hay estado seleccionado, los demás filtros quedan vacíos
    if not state_value:
        return state_options, state_value, [], None, [], None

    # 3. Opciones de contaminante para el estado
    if state_value == 'Todos':
        pollutants = collection.distinct('contaminante')
    else:
        pollutants = collection.distinct('contaminante', {'estado': state_value})
    pollutant_options = [{'label': 'Todos', 'value': 'Todos'}] + [{'label': p, 'value': p} for p in pollutants]
    pollutant_value = pollutant if pollutant in pollutants or pollutant == 'Todos' else 'Todos'

    # 4. Opciones de estación para el estado
    if state_value == 'Todos':
        stations = collection.distinct('estacion')
    else:
        stations = collection.distinct('estacion', {'estado': state_value})
    station_options = [{'label': 'Todas', 'value': 'Todas'}] + [{'label': s, 'value': s} for s in stations]
    station_value = station if station in stations or station == 'Todas' else 'Todas'

    return state_options, state_value, pollutant_options, pollutant_value, station_options, station_value

@app.callback(
    Output('filtered-data', 'data'),
    [
        Input('data-source', 'data'),
        Input('state-filter', 'value'),
        Input('pollutant-filter', 'value'),
        Input('station-filter', 'value'),
        Input('date-range', 'start_date'),
        Input('date-range', 'end_date'),
        Input('start-hour', 'value'),
        Input('end-hour', 'value'),
        Input('value-range', 'value'),
        Input('interval-component', 'n_intervals')
    ]
)
def update_filtered_data(data_source, state, pollutant, station, start_date, end_date, start_hour, end_hour, value_range, n_intervals):
    collection = db[data_source]
    query = {}

    if state and state != 'Todos':
        query["estado"] = state
    if pollutant and pollutant != 'Todos':
        query["contaminante"] = pollutant
    if station and station != 'Todas':
        query["estacion"] = station

    # Fechas y horas
    try:
        start_dt = parser.parse(start_date).replace(hour=start_hour)
        end_dt = parser.parse(end_date).replace(hour=end_hour)
        query["fecha"] = {
            "$gte": start_dt.strftime('%Y-%m-%dT%H:%M:%S'),
            "$lte": end_dt.strftime('%Y-%m-%dT%H:%M:%S')
        }
    except Exception as e:
        print("Error parsing dates:", e)

    query["valor"] = {"$gte": value_range[0], "$lte": value_range[1]}

    data = list(collection.find(query))
    df = pd.DataFrame(data)
    if not df.empty and '_id' in df.columns:
        df = df.drop(columns=['_id'])
    return df.to_json(date_format='iso', orient='split')

@app.callback(
    [Output('avg-value', 'children'),
     Output('value-unit', 'children'),
     Output('max-value', 'children'),
     Output('max-location', 'children'),
     Output('min-value', 'children'),
     Output('min-location', 'children'),
     Output('risk-level', 'children'),
     Output('risk-description', 'children')],
    [Input('filtered-data', 'data'),
     Input('pollutant-filter', 'value')]
)
def update_kpis(json_data, pollutant):
    if json_data is None:
        raise PreventUpdate
    
    df = pd.read_json(StringIO(json_data), orient='split')
    
    if df.empty:
        return ["-", "-", "-", "-", "-", "-", "-", "-"]
    
    # Obtener unidad (puede variar entre colecciones)
    unit = df['unidad'].iloc[0] if 'unidad' in df.columns else 'AQI'
    
    # Cálculos básicos
    avg_value = round(df['valor'].mean(), 1)
    max_value = round(df['valor'].max(), 1)
    max_location = df.loc[df['valor'].idxmax(), 'estacion']
    min_value = round(df['valor'].min(), 1)
    min_location = df.loc[df['valor'].idxmin(), 'estacion']
    
    # Determinar nivel de riesgo
    risk_info = calculate_risk_level(avg_value, pollutant)
    
    return [
        avg_value,
        unit,
        max_value,
        max_location,
        min_value,
        min_location,
        risk_info['level'],
        risk_info['description']
    ]

@app.callback(
    Output('time-series-chart', 'figure'),
    [Input('filtered-data', 'data'),
     Input('pollutant-filter', 'value'),
     Input('data-source', 'data')]
)
def update_time_series(json_data, pollutant, data_source):
    if json_data is None:
        raise PreventUpdate

    df = pd.read_json(StringIO(json_data), orient='split')
    if df.empty:
        return px.line(title="No hay datos disponibles")

    # Normaliza fechas a naive (sin zona horaria)
    df['fecha_hora'] = pd.to_datetime(df['fecha'], errors='coerce')
    if pd.api.types.is_datetime64tz_dtype(df['fecha_hora']):
        df['fecha_hora'] = df['fecha_hora'].dt.tz_localize(None)
    # Agrupa por fecha, estación y contaminante
    if data_source == 'forecast':
        df_grouped = df.groupby(['fecha', 'estacion', 'contaminante'])['valor'].mean().reset_index()
        x_col = 'fecha'
    else:
        df_grouped = df.groupby([pd.Grouper(key='fecha_hora', freq='h'), 'estacion', 'contaminante'])['valor'].mean().reset_index()
        x_col = 'fecha_hora'

    # Si hay varios contaminantes, muestra una línea por estación+contaminante
    fig = px.line(
        df_grouped,
        x=x_col,
        y='valor',
        color='estacion' if isinstance(pollutant, str) or (pollutant and len(pollutant) == 1) else 'contaminante',
        line_dash='contaminante' if isinstance(pollutant, list) and len(pollutant) > 1 else None,
        markers=True,
        title="Tendencia temporal",
        labels={'valor': 'Concentración', x_col: 'Fecha/Hora'}
    )

    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# Mapa de contaminación
@app.callback(
    Output('pollution-map', 'figure'),
    [Input('filtered-data', 'data'),
     Input('pollutant-filter', 'value')]
)
def update_pollution_map(json_data, pollutant):
    if json_data is None:
        raise PreventUpdate

    df = pd.read_json(StringIO(json_data), orient='split')

    if df.empty or not all(col in df.columns for col in ['lat', 'lon', 'valor', 'estacion']):
        # Si no hay datos o faltan columnas necesarias
        return go.Figure(layout={"title": "No hay datos disponibles"})

    # Agrupar por ubicación
    df_map = df.groupby(['lat', 'lon', 'estacion'])['valor'].mean().reset_index()

    fig = px.scatter_mapbox(
        df_map,
        lat="lat",
        lon="lon",
        color="valor",
        size="valor",
        hover_name="estacion",
        hover_data=["valor"],
        color_continuous_scale=px.colors.sequential.Viridis,
        zoom=5,
        height=500,
        mapbox_style="open-street-map"
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    return fig

# Análisis por contaminante
@app.callback(
    Output('pollutant-analysis', 'figure'),
    [Input('filtered-data', 'data')]
)
def update_pollutant_analysis(json_data):
    if json_data is None:
        raise PreventUpdate
    
    df = pd.read_json(StringIO(json_data), orient='split')
    
    if df.empty:
        return go.Figure()
    
    fig = px.box(
        df,
        y='valor',
        x='contaminante',
        color='contaminante',
        title="Distribución por Contaminante"
    )
    
    return fig

@app.callback(
    Output('contaminant-bar', 'figure'),
    [Input('filtered-data', 'data')]
)
def update_contaminant_bar(json_data):
    if json_data is None:
        raise PreventUpdate

    df = pd.read_json(StringIO(json_data), orient='split')
    if df.empty or 'contaminante' not in df.columns:
        return go.Figure(layout={"title": "No hay datos disponibles"})

    # Agrupa por contaminante y calcula el promedio
    df_bar = df.groupby('contaminante')['valor'].mean().reset_index()

    fig = px.bar(
        df_bar,
        x='contaminante',
        y='valor',
        color='contaminante',
        text_auto='.2s',
        labels={'valor': 'Concentración promedio', 'contaminante': 'Contaminante'},
        title="Concentración promedio por contaminante"
    )
    fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    return fig

# ========== Funciones auxiliares ==========

def calculate_risk_level(value, pollutant):
    """Calcula el nivel de riesgo basado en el valor y tipo de contaminante"""
    thresholds = {
        'PM2.5': [(0, 12, 'Buena'), (12.1, 35.4, 'Moderada'), 
                 (35.5, 55.4, 'Dañina'), (55.5, 150.4, 'Muy dañina'), 
                 (150.5, float('inf'), 'Peligrosa')],
        'PM10': [(0, 54, 'Buena'), (55, 154, 'Moderada'), 
                (155, 254, 'Dañina'), (255, 354, 'Muy dañina'), 
                (355, float('inf'), 'Peligrosa')],
        'O3': [(0, 54, 'Buena'), (55, 70, 'Moderada'), 
              (71, 85, 'Dañina'), (86, 105, 'Muy dañina'), 
              (106, float('inf'), 'Peligrosa')],
        'SO2': [(0, 35, 'Buena'), (36, 75, 'Moderada'), 
               (76, 185, 'Dañina'), (186, 304, 'Muy dañina')],
        'CO': [(0, 4.4, 'Buena'), (4.5, 9.4, 'Moderada'), 
              (9.5, 12.4, 'Dañina'), (12.5, 15.4, 'Muy dañina')]
    }
    
    for min_val, max_val, level in thresholds.get(pollutant, [(0, float('inf'), 'Desconocido')]):
        if min_val <= value <= max_val:
            return {'level': level, 'description': f"{value} {level}"}
    
    return {'level': 'Desconocido', 'description': ''}


if __name__ == '__main__':
    server.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)))