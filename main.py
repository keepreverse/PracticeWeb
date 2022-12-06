from collections import defaultdict
from typing import List

from dash import Dash, html, dcc, Input, Output
import numpy as np
import plotly.graph_objects as go

import library
from library import DATA, AverageValues

#Список выбора осреднения
AVERAGE_LIST = ['Data as is', 'Average per hour', 'Average per three hours', 'Average per day', 'Minimum and maximum values per day']
#Кнопки переключения
TEMP_FEEL_LIST = ['Effective temperature', 'Feeling']
#Список выбора прибора
DEVICES_SET = set(f"{row['uName']} {row['serial']}" for row in DATA.values())

#Начало программы (создаётся веб-приложение)
app = Dash(__name__)

#Графический интерфейс веб-приложения (здесь описываются раскрывающиеся списки, кнопки, графики и т.п. с использованием html)
app.layout = html.Div(children=[
	html.H1(children='Graphs'),
	html.Div([
		html.P(children='Device:'),
		dcc.Dropdown(id='dropdown-device', options=list(DEVICES_SET)),
		html.Div(id='output-device'),
		html.P(children='Parameters:'),
		dcc.Dropdown(id='dropdown-parametr', multi=True),
		html.Div(id='output-parametr'),
		html.P(children='Average:'),
		dcc.Dropdown(id='dropdown-average', options=AVERAGE_LIST, value='Data as is'),
]),
	html.P(children='Date:'),
	dcc.DatePickerRange(id='date-picker-range'),
	dcc.Graph(id='example-graph'),
	html.Div([
		html.H2(children='Graph of effective temperature:'),
		dcc.Dropdown(id="dropdown-sensor-temp-humidity", multi=True),
		dcc.RadioItems(id='button-temp-feel', options=TEMP_FEEL_LIST, 				value=TEMP_FEEL_LIST[0], inline=True),
		dcc.Graph(id="graph-sensor-temp-humidity")
	]),
])

#Callback-и нужны, чтобы при выборе каких-либо параметров данные графика обновлялись. В данном случае возвращается раскрывающийся список датчиков в зависимости от того какой прибор выбрал пользователь
@app.callback(
	Output('dropdown-parametr', 'options'),
	Input('dropdown-device', 'value')
)
#К каждому callback-у нужно прописывать функцую возвращения. В данном случае возвращается лист датчиков из конкретного прибора.
def get_device_params(device: str) -> List[dict]:
	if not device:
		return []
	for row in DATA.values():
		current_device = f"{row['uName']} {row['serial']}"
		if current_device == device:
			params = []
			for param in row['data']:
				params.append(param)
			return [{"label": param, "value": param} for param in params]

@app.callback(
	Output("example-graph", "figure"),
	[Input('dropdown-device', 'value'),
	 Input("dropdown-parametr", "value"),
	 Input('dropdown-average', 'value'),
	 Input('date-picker-range', 'start_date'),
	 Input('date-picker-range', 'end_date')]
)
#Построение графика
def update_plot(device: str, params: List[str], average_val: str, start_date: str, end_date: str) -> go.Figure:
	if not device or not params:
		return go.Figure()

	#Здесь происходит конвертация в DataFrame
	df = library.get_device_data(device=device, params=params, 	user_start_date=start_date, user_end_date=end_date)
	#Начало построения графика
	fig = go.Figure()

	#Ищется вариант осреднения
	if average_val == 'Data as is':
		for param in params:
			#Построение линейного графика
			fig.add_trace(
				go.Scatter(x=df.index, y=df[param], mode='lines', 						name=param)
			)

	elif average_val == 'Average per hour':
		df_averaged = 		library.average_data(df=df,average_val=AverageValues.one_hour)
		for param in params:
			fig.add_trace(
				go.Scatter(x=df_averaged.index, y=df_averaged[param], 					mode='lines', name=param)
			)

	elif average_val == 'Average per three hours':
		df_averaged = library.average_data(df=df, 		average_val=AverageValues.three_hours)
		for param in params:
			fig.add_trace(
				go.Scatter(x=df_averaged.index, y=df_averaged[param], 					mode='lines', name=param)
			)

	elif average_val == 'Average per day':
		df_averaged = library.average_data(df=df, 		average_val=AverageValues.one_day)
		for param in params:
			fig.add_trace(
				go.Scatter(x=df_averaged.index, y=df_averaged[param], 					mode='lines', name=param)
		)

	elif average_val == 'Minimum and maximum values per day':
		#В DataFrame добавляются "столбцы" минимальных и максимальных 		значений
		df_agg = library.agg_per_day_min_max(df=df)
		for param in params:
			delta = df_agg[param]["max"] - df_agg[param]["min"]
			#Построение столбчатого графика, где начало - минимальное 			значение по y
			fig.add_trace(
				go.Bar( 
					x=df_agg.index,
					y=delta,
					base=df_agg[param]["min"],
					name=param,
					hovertemplate="Max: %{y} <br>Min: %{base}<br>" 
				)
			)
	fig.update_layout(hovermode="x unified")
	return fig

@app.callback(
	Output('dropdown-sensor-temp-humidity', 'options'),
	Input('dropdown-device', 'value')
)
#Здесь ищутся датчики с данными температуры и влажности
def get_sensor_hum_temp_params(device: str) -> List[dict]:
	if not device:
		return []
	for row in DATA.values():
		current_device = f"{row['uName']} {row['serial']}"
		if current_device == device:
			sensors_with_hum_temp_status = defaultdict(dict)
			for param in row['data']:
				sensor = param.rsplit("_")[0]
				if param.endswith("humidity"):
					sensors_with_hum_temp_status[sensor]["humidity"] = 					True
				else:
					if not "humidity" in 				sensors_with_hum_temp_status[sensor]:
						sensors_with_hum_temp_status[sensor]								["humidity"] = False
				if param.endswith("temp"):
					sensors_with_hum_temp_status[sensor]["temp"] = True
				else:
					if not "temp" in sensors_with_hum_temp_status[sensor]:
						sensors_with_hum_temp_status[sensor]["temp"] = 						False
			return [
				{"label": sensor, "value": sensor}
				for sensor, status in sensors_with_hum_temp_status.items()
				if status["humidity"] and status["temp"]
			]
	return []

@app.callback(
	Output("graph-sensor-temp-humidity", "figure"),
	[Input('dropdown-device', 'value'),
	 Input('dropdown-sensor-temp-humidity', "value"),
	 Input('dropdown-average', 'value'),
	 Input('date-picker-range', 'start_date'),
	 Input('date-picker-range', 'end_date'),
	 Input('button-temp-feel', 'value')
	]
)
#Построение графика эффективной температуры или теплоощущения
def update_plot_temp_humidity(device: str, sensors: List[str], average_val: str, start_date: str, end_date: str, button: str) -> go.Figure:
	if not device or not sensors:
		return go.Figure()
	params: List[str] = []
	for sensor in sensors:
		params.append(f"{sensor}_temp")
		params.append(f"{sensor}_humidity")
	df = library.get_device_data(device=device, params=params, 	user_start_date=start_date, user_end_date=end_date)
	df_eff = library.get_effective_temp(df=df, sensors=sensors)
	if average_val == 'Average per hour':
		df_eff = library.average_data(df=df_eff, 		average_val=AverageValues.one_hour)
	elif average_val == 'Average per three hours':
		df_eff = library.average_data(df=df_eff, 		average_val=AverageValues.three_hours)
	elif average_val == 'Average per day':
		df_eff = library.average_data(df=df_eff, 		average_val=AverageValues.one_day)
	#Построение эффективной температуры (точечно-линейный)
	if button != 'Feeling':
		if average_val != 'Minimum and maximum values per day':
			fig = go.Figure()
			for sensor in sensors:
				fig.add_trace(
					go.Scatter(
						x=df_eff.index,
						y=df_eff[f"{sensor}_effective_temp"],
						mode='lines+markers',
						name=sensor,
					)
				)
		else:
			df_eff = library.agg_per_day_min_max(df=df_eff)
			fig = go.Figure()
			for sensor in sensors:
				delta = df_eff[f'{sensor}_effective_temp']["max"] - 			df_eff[f'{sensor}_effective_temp']["min"]
				fig.add_trace(
					go.Bar(
						x=df_eff.index,
						y=delta,
						base=df_eff[f'{sensor}_effective_temp']["min"],
						name=f'{sensor}_effective_temp',
						hovertemplate="Max: %{y} <br>Min: %{base}<br>"
					)
				)
	#Построение графика теплоощущения (стобчатый, где по оси y - уровни 	теплоощущения)
	else:
		df_eff = library.get_feeling_temp(df=df_eff, sensors=sensors)
		if average_val != 'Minimum and maximum values per day':
			fig = go.Figure()
			for sensor in sensors:
				customdata = np.stack((df_eff[f'{sensor}_feeling']), axis=-1)
				fig.add_trace(
					go.Bar(
						x=df_eff.index,
						y=df_eff[f"{sensor}_lvl_feeling"],
						customdata=customdata,
						hovertemplate="Feeling: %{customdata}",
						name=sensor,
					)
				)
		else:
			df_eff = library.agg_per_day_min_max(df=df_eff)
			fig = go.Figure()
			for sensor in sensors:
				delta = df_eff[f'{sensor}_lvl_feeling']['max'] - 				df_eff[f'{sensor}_lvl_feeling']['min']
				fig.add_trace(
					go.Bar(
						x=df_eff.index,
						y=delta,
						base=df_eff[f'{sensor}_lvl_feeling']["min"],
						name=f'{sensor}_lvl_feeling',
						hovertemplate="Max: %{y} <br>Min: %							{base}<br>"
					)
				)
		fig.update_layout(hovermode="x unified")
		return fig

if __name__ == '__main__':
	app.run(debug=False,host='0.0.0.0')