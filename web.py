# -*- coding: utf-8 -*-
from flask import Flask, request, render_template, send_file
from jinja2 import Markup, Environment, FileSystemLoader
from pyecharts.globals import CurrentConfig
from pyecharts import options as opts
from pyecharts.charts import Line
import random
import json
import datetime
import sqlite3
import os
import pandas as pd

app = Flask(__name__, static_folder="templates")
database = ""
log_file = ""
alarming_file = ""

# 佛祖保佑！永无 Bug！
# 三玖天下第一！！！

# 当数据表不存在时创建
# 创建 sensorlog 表用于温度记录，包含列 sensorid (传感器ID, int), sensorvalue (传感器读数, float), updatetime (数据更新时间, text)
# 创建 sensorkey 表用于记录传感器 Key 与 传感器 ID 的对应关系，包含列 sensorkey (传感器 Key, text), sensorid (传感器 ID， int), sensorname (传感器名称, text)
def create_table_if_not_exist():
	db = sqlite3.connect(database)
	cur = db.cursor()
	cur.execute("CREATE TABLE IF NOT EXISTS sensorlog(sensorid int, sensorvalue float, updatetime text, status text);")
	cur.execute("CREATE TABLE IF NOT EXISTS sensorkey(sensorkey text, sensorid int, sensorname text)")
	db.commit()
	cur.close()
	db.close()

# 读取数据库
def read_database(item, location, condition):
	db = sqlite3.connect(database)
	cur = db.cursor()
	if condition == None:
		cur.execute("SELECT %s from %s" % (item, location))
	else:
		cur.execute("SELECT %s from %s where %s" % (item, location, condition))
	data = cur.fetchall()
	cur.close()
	db.close()
	return data

# 从数据库中删除值
def delete_from_database(location, condition):
	db = sqlite3.connect(database)
	cur = db.cursor()
	cur.execute("DELETE from %s where %s" % (location, condition))
	db.commit()
	cur.close()
	db.close()

# 数据库导出，输出到 output.csv
def sensorlog_to_csv(condition):
	file = open("output.csv", "w", newline = "")
	db = sqlite3.connect(database)
	cur = db.cursor()
	if condition == None:
		cur.execute("SELECT * from sensorlog")
	else:
		cur.execute("SELECT * from sensorlog where %s" % condition)
	dataframe = pd.DataFrame(cur.fetchall(), columns = ["Sensor ID", "Degree (Celsius)", "Update Time", "Alarm"])
	dataframe.to_csv(file)
	file.close()
	cur.close()
	db.close()

# 把传感器信息添加到数据库中
def add_to_sensorkey(sensorkey, sensorid, sensorname):
	db = sqlite3.connect(database)
	cur = db.cursor()
	cur.execute("INSERT INTO sensorkey(sensorkey, sensorid, sensorname) values('%s', %d, '%s')" % (sensorkey, sensorid, sensorname))
	db.commit()
	cur.close()
	db.close()

# 将添加的传感器数据写入到数据库中
def add_to_sensorlog(sensorid, sensorvalue, updatetime, alarm_status):
	db = sqlite3.connect(database)
	cur = db.cursor()
	cur.execute("INSERT INTO sensorlog(sensorid, sensorvalue, updatetime, status) VALUES(%d, %f, '%s', '%s')" % (sensorid, sensorvalue, updatetime, alarm_status))
	db.commit()
	cur.close()
	db.close()

# 配置文件中加载报警温度
def load_alarming_temperature():
	config_file = open(alarming_file, "r")
	config_file_lines = config_file.readline()
	config_jsonval = json.loads(config_file_lines)
	if config_jsonval[0]['AlarmingStatus'] == "on":
		return config_jsonval[0]['AlarmingTemperature']
	else:
		return -1

# 写操作日志文件
def write_log(content):
	nowtime = datetime.datetime.now()
	nowtime = nowtime.strftime("%Y-%m-%d %H:%M:%S")
	file = open(log_file, "a")
	file.write("[" + nowtime + "] " + content + "\n")
	file.close()

# 创建 16 位包含大小写的随机字符串, 作为 sensorkey
def generate_key():
	key = ""
	for i in range(0, 16):
		key += random.choice("AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz")
	return key

def line_base(sensorid):
	time_list = []
	sensorvalue_list = []
	# # SB Python 两个变量连等当一个变量
	for updatetime in read_database("updatetime", "sensorlog", None):
		time_list.append(updatetime[0])
	if sensorid == None:
		for sensorvalue in read_database("sensorvalue", "sensorlog", None):
			print("Sensorvalue = ", sensorvalue[0], " ")
			sensorvalue_list.append(sensorvalue[0])
			line_args = (
			Line(init_opts=opts.InitOpts(width="1200px", height="300px"))
			.add_xaxis(xaxis_data = time_list)
			.add_yaxis(series_name = "所有传感器温度（摄氏度）", y_axis = sensorvalue_list))
	else:
		for sensorvalue in read_database("sensorvalue", "sensorlog", int(sensorid)):
			print("Sensorvalue = ", sensorvalue[0], " ")
			sensorvalue_list.append(sensorvalue[0])
			line_args = (
			Line(init_opts=opts.InitOpts(width="1200px", height="300px"))
			.add_xaxis(xaxis_data = time_list)
			.add_yaxis(series_name = "温度", y_axis = sensorvalue_list))
	return line_args

 # 渲染主页面 (index)
@app.route("/")
def index():
	# 读取数据库，检测 sensorkey 表是否为空 (未添加任何传感器), 为空则返回初次使用欢迎页面
	sensorname = read_database("*", "sensorkey", None)
	sensortemp = read_database("*", "sensorlog", None)
	if sensorname == []:
		return render_template("index.html", new_coming = 1, per_sensor_view = 0)
	else:
		return render_template("index.html", new_coming = 0, per_sensor_view = 0, sensorname = sensorname, sensortemp = sensortemp)

# 渲染传感器列表页面
@app.route("/sensorlist")
def render_sensorlist():
	sensorlist = []
	sensortemp = []
	for i in read_database("*", "sensorkey", None):
		tmp = read_database("*", "sensorlog", "sensorid = %d" % int(i[1]))
		if tmp != []:
			sensortemp.append(tmp[len(tmp) - 1])
		sensorlist.append(read_database("*", "sensorkey", "sensorid = %d" % int(i[1])))
	return render_template("sensorlist.html", sensorlist = sensorlist, sensortemp = sensortemp)


# 渲染传感器数据单独查看页面，需要参数 sensorid
@app.route("/per_sensor_view")
def per_sensor_view():
	sensorid = request.args.get("sensorid")
	sensorname = read_database("sensorname", "sensorkey", "sensorid = %d" % (int(sensorid)))
	sensortemp = read_database("*", "sensorlog", "sensorid = %d" % (int(sensorid)))
	return render_template("index.html", new_coming = 0, per_sensor_view = 1, sensorid = sensorid, sensorname = sensorname, sensortemp = sensortemp)

# 渲染传感器 Key 查看页面，需要参数 sensorid
@app.route("/show_key")
def show_key():
	sensorid = request.args.get("sensorid")
	sensorkey = read_database("*", "sensorkey", "sensorid = %d" % int(sensorid))
	return render_template("show_key.html", sensorkey = sensorkey)

# 渲染添加新传感器页面
@app.route("/add_new")
def render_add_new():
	return render_template("add_sensor.html", succeed = 0)

# 渲染删除传感器页面，需要参数 sensorid
@app.route("/delete_sensor")
def render_del_sensor():
	sensorid = request.args.get("sensorid")
	sensorname = read_database("sensorname", "sensorkey", "sensorid = %d" % int(sensorid))
	delete_from_database("sensorkey", "sensorid = %d" % int(sensorid))
	delete_from_database("sensorlog", "sensorid = %d" % int(sensorid))
	write_log("Deleted sensor '%s' (ID: %d) from database" % (sensorname[0][0], int(sensorid)))
	return render_template("delete_sensor.html", sensorid = sensorid)

@app.route("/csv_output")
def csv_output():
	sensorid = request.args.get("sensorid")
	if sensorid == "ALL":
		sensorlog_to_csv(None)
		return send_file("output.csv")
	else:
		sensorlog_to_csv("sensorid = %d" % int(sensorid))
		return send_file("output.csv")


# 返回渲染折线图所需的数据 (图表数据), 需要参数 sensorid
@app.route("/render_charts")
def draw_charts():
	sensorid = request.args.get("sensorid")
	if sensorid == None or sensorid == "":
		chart_options = line_base(None)
	else:
		chart_options = line_base(int(sensorid))
	if chart_options == -1:
		return json.dumps([{"ExecutionStatus":"InvalidArgs"}])
	return chart_options.dump_options_with_quotes()

# 添加传感器接口，需要参数 sensorname, not_from_browser (当在浏览器中添加传感器时渲染 HTML 页面，其他方式调用则返回 JSON 数据)
@app.route("/add_sensor")
def add_sensor():
	sensorname = request.args.get('sensorname')
	not_from_browser = request.args.get('not_from_browser')
	sensorkey = generate_key()
	sensorlist = read_database("*", "sensorkey", None)
	if len(sensorlist) == 0:
		sensorid = 1
	else:
		sensorid = sensorlist[len(sensorlist) - 1][1] + 1
	add_to_sensorkey(sensorkey, sensorid, sensorname)
	write_log("Added sensor '%s' (ID:%d) to database" % (sensorname, sensorid))
	if not_from_browser == "1":
		return json.dumps([{"ExecutionStatus":"Succeeded", "SensorName":sensorname, "SensorID":sensorid, "SensorKey":sensorkey}])
	else:
		return render_template("add_sensor.html", succeed = 1, sensorkey = sensorkey)

# 传感器数据输入接口，需要参数 sensorkey, sensorvalue
@app.route("/data_input")
def data_input():
	sensorkey = request.args.get("sensorkey")
	sensorvalue = float(request.args.get("sensorvalue"))
	# 获取当前系统系统时间
	nowtime = datetime.datetime.now()
	nowtime = nowtime.strftime("%Y-%m-%d %H:%M:%S")
	data = read_database("*", "sensorkey", None)
	sensorid = -1
	for i in data:
		if i[0] == sensorkey:
			sensorid = i[1]
	# 当在数据库中找不到对应的 sensorkey
	if sensorid == -1:
		return json.dumps([{"ExecutionStatus":"InvalidSensorKey"}])
	# 数据库中存在对应 sensorkey
	else:
		# add_to_sensorlog(sensorid, sensorvalue, nowtime)
		sensorname = read_database("sensorname", "sensorkey", "sensorid = %d" % sensorid)
		write_log("Added temperature data %f to sensor '%s' (ID: %d)" % (sensorvalue, sensorname[0][0], sensorid))
		# 判断传感器报警是否打开
		alarming_temperature = load_alarming_temperature()
		if not alarming_temperature == -1:
			if sensorvalue >= alarming_temperature:
				write_log("Sensor '%s' (ID: %d) alarming, temperature %f" % (sensorname[0][0], sensorid, sensorvalue))
				add_to_sensorlog(sensorid, sensorvalue, nowtime, "报警")
				return json.dumps([{"ExecutionStatus":"Alarming"}])
			else:
				add_to_sensorlog(sensorid, sensorvalue, nowtime, "正常")
				return json.dumps([{"ExecutionStatus":"Succeeded"}])
		else:
			add_to_sensorlog(sensorid, sensorvalue, nowtime, "正常")
			return json.dumps([{"ExecutionStatus":"Succeeded"}])

@app.route("/alarm_setting")
def alarm_setting():
	return render_template("alarm_setting.html", setting = 1, current_temperature = load_alarming_temperature())

@app.route("/edit_alarm_settings")
def edit_alarm_settings():
	# 传感器开启状态
	# 报警温度
	# 报警邮件发送设置
	alarming_status = request.args.get("alarming_status")
	alarming_temperature = request.args.get("alarming_temperature")

	if alarming_status == "on" and alarming_temperature == "-1":
		alarming_temperature = 1000
	# 写配置文件
	file = open(alarming_file, "w")
	file.write(json.dumps([{"AlarmingStatus":alarming_status, "AlarmingTemperature":float(alarming_temperature)}]))
	file.close()
	return render_template("alarm_setting.html", setting = 0)

if __name__ == "__main__":
	# 默认数据库保存于主程序所在目录，监听 127.0.0.1 8080 端口，不启用 Flask 调试模式
	# 当配置文件不存在时自动创建
	if not os.path.isfile("app_config.txt"):
		file = open("app_config.txt", "w")
		file.write(json.dumps([{"AlarmingFilePath":"alarming_config.txt", "LogFilePath":"log.txt", "DatabasePath":"data.db", "AppListenAddress":"127.0.0.1", "AppListenPort":8080, "DebugModeStatus":0}]))
		file.close()
	config_file = open("app_config.txt", "r")
	config_file_lines = config_file.readline()
	config_jsonval = json.loads(config_file_lines)

	# 读取配置文件中的数据库路径、程序监听地址、端口、是否开启调试模式
	database = config_jsonval[0]["DatabasePath"]
	app_listen_addr = config_jsonval[0]["AppListenAddress"]
	app_listen_port = config_jsonval[0]["AppListenPort"]
	debug_mode_status = config_jsonval[0]["DebugModeStatus"]
	log_file = config_jsonval[0]["LogFilePath"]
	alarming_file = config_jsonval[0]["AlarmingFilePath"]

	if not os.path.isfile(log_file):
		file = open(log_file, "w")
		file.close()
	if not os.path.isfile(alarming_file):
		file = open(alarming_file, "w")
		file.write(json.dumps([{"AlarmingStatus":"off", "AlarmingTemperature":1000}]))
		file.close()

	create_table_if_not_exist() # 数据表不存在时创建
	app.run(host = app_listen_addr, port = app_listen_port, debug = debug_mode_status)
