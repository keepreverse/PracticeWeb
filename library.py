from datetime import datetime
from enum import Enum
import json
from typing import List, Optional
import pandas as pd

#Чтение JSON-файла
with open('log.txt', "r", encoding="utf-8") as f:
	DATA: dict = json.load(f)

#Класс для выбора значения осреднения
class AverageValues(str, Enum):
	one_hour = "1h"
	three_hours = "3h"
	one_day = "1d"

#Получение даты за определённый промежуток времени
def get_picker_data(user_start_date: str, user_end_date: str) -> dict:
	picker_data = {}
	if (user_start_date is not None) and (user_end_date is not None):
		dt_user_start_date = datetime.strptime(user_start_date, '%Y-%m-%d')
		dt_user_end_date = datetime.strptime(user_end_date, '%Y-%m-%d')
		for key in DATA:
			if dt_user_start_date <= datetime.strptime(DATA[key]['Date'][0:10], 			'%Y-%m-%d') <= dt_user_end_date:
				picker_data[key] = DATA[key]
	elif (user_start_date is not None) and (user_end_date is None):
		dt_user_start_date = datetime.strptime(user_start_date, '%Y-%m-%d')
		for key in DATA:
			if dt_user_start_date <= datetime.strptime(DATA[key]['Date'][0:10], 			'%Y-%m-%d'):
				picker_data[key] = DATA[key] 
	elif (user_start_date is None) and (user_end_date is not None):
		dt_user_end_date = datetime.strptime(user_end_date, '%Y-%m-%d')
		for key in DATA:
			if datetime.strptime(DATA[key]['Date'][0:10], '%Y-%m-%d') <= 				dt_user_end_date:
				picker_data[key] = DATA[key]
	else:
		picker_data = DATA
	return picker_data

#Получение всех данных с датчика
def get_device_data(device: str, params: List[str], user_start_date: Optional[str] = None, user_end_date: Optional[str] = None) -> pd.DataFrame:
	device_data: List[dict] = []
	picker_data = get_picker_data(user_start_date=user_start_date, 	user_end_date=user_end_date)
	for row in picker_data.values():
		current_device = f"{row['uName']} {row['serial']}"
		if current_device == device:
			device_cur_values = {"Date": row['Date']}
			for param in params:
				try:
					device_cur_values[param] = float(row['data'][param])
				except ValueError:
					device_cur_values[param] = row['data'][param]
			device_data.append(device_cur_values)
	df = pd.DataFrame(device_data)
	df = df.set_index("Date")
	df.index = pd.to_datetime(df.index)
	return df

#Получение эффективной температуры
def get_effective_temp(df: pd.DataFrame, sensors: List[str]) -> pd.DataFrame:
	for sensor in sensors:
		df[f"{sensor}_effective_temp"] = (
			df[f"{sensor}_temp"] - 0.4 * (df[f"{sensor}_temp"] - 10) * (1 - 				(df[f"{sensor}_humidity"] / 100))
		)
	return df

#Добавление к эффективной температуре уровни теплоощущения
def get_feeling_temp(df: pd.DataFrame, sensors: List[str]) -> pd.DataFrame:
	for sensor in sensors:
		df.loc[df[f"{sensor}_effective_temp"] > 30, f"{sensor}_feeling"] = "Очень 		жарко"
		df.loc[(df[f"{sensor}_effective_temp"] > 24) & 			(df[f"{sensor}_effective_temp"] <= 	30), f"{sensor}_feeling"] = "Жарко"
		df.loc[(df[f"{sensor}_effective_temp"] > 18) & 		(df[f"{sensor}_effective_temp"] <= 	24), f"{sensor}_feeling"] = "Тепло"
		df.loc[(df[f"{sensor}_effective_temp"] > 12) & 			(df[f"{sensor}_effective_temp"] <= 	18), f"{sensor}_feeling"] = "Умеренно тепло"
		df.loc[(df[f"{sensor}_effective_temp"] > 6) & (df[f"{sensor}_effective_temp"] 		<= 	12), f"{sensor}_feeling"] = "Прохладно"
		df.loc[(df[f"{sensor}_effective_temp"] > 0) & (df[f"{sensor}_effective_temp"] 		<= 	6), f"{sensor}_feeling"] = "Умеренно"
		df.loc[(df[f"{sensor}_effective_temp"] > -12) & 		(df[f"{sensor}_effective_temp"] <= 	0), f"{sensor}_feeling"] = "Холодно"
		df.loc[(df[f"{sensor}_effective_temp"] > -24) & 		(df[f"{sensor}_effective_temp"] <= 	-12), f"{sensor}_feeling"] = "Очень холодно"
		df.loc[(df[f"{sensor}_effective_temp"] > -30) & 		(df[f"{sensor}_effective_temp"] <= 	-24), f"{sensor}_feeling"] = "Крайне холодно"

		df.loc[df[f"{sensor}_feeling"] == 'Очень жарко', f"{sensor}_lvl_feeling"] = 9
		df.loc[df[f"{sensor}_feeling"] == 'Жарко', f"{sensor}_lvl_feeling"] = 8
		df.loc[df[f"{sensor}_feeling"] == 'Тепло', f"{sensor}_lvl_feeling"] = 7
		df.loc[df[f"{sensor}_feeling"] == 'Умеренно тепло', f"{sensor}_lvl_feeling"] 		= 6
		df.loc[df[f"{sensor}_feeling"] == 'Прохладно', f"{sensor}_lvl_feeling"] = 5
		df.loc[df[f"{sensor}_feeling"] == 'Умеренно', f"{sensor}_lvl_feeling"] = 4
		df.loc[df[f"{sensor}_feeling"] == 'Холодно', f"{sensor}_lvl_feeling"] = 3
		df.loc[df[f"{sensor}_feeling"] == 'Очень холодно', f"{sensor}_lvl_feeling"] = 		2
		df.loc[df[f"{sensor}_feeling"] == 'Крайне холодно', f"{sensor}_lvl_feeling"] 		= 1
	return df

#Осреденение данных (используется DataFrame)
def average_data(df: pd.DataFrame, average_val: AverageValues) -> pd.DataFrame:
	return df.resample(average_val.value, label='right').mean()

#Получение максимумов и минимумов (используется DataFrame)
def agg_per_day_min_max(df: pd.DataFrame) -> pd.DataFrame:
	agg_params = {param: ["min", "max"] for param in df.columns}
	return df.resample(AverageValues.one_day.value, label='right').agg(agg_params)