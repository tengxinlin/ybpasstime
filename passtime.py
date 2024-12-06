import mysql.connector
from datetime import datetime, timedelta
import math
import taos
import readLines

readLines.sorted_data_dict

# Haversine公式计算两点之间的球面距离
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # 地球半径，单位为千米
    phi1, phi2 = map(math.radians, [lat1, lat2])
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

# 将经纬度转换为弧度
def lat_lon_to_rad(lat, lon):
    return math.radians(lat), math.radians(lon)

# 计算P点到直线AB的距离
def point_to_line_distance(latP, lonP, latA, lonA, latB, lonB):
    # 将经纬度转换为弧度
    phiP, lambdaP = lat_lon_to_rad(latP, lonP)
    phiA, lambdaA = lat_lon_to_rad(latA, lonA)
    phiB, lambdaB = lat_lon_to_rad(latB, lonB)

    # 计算点P到点A和点B的球面距离
    dAB = haversine(latA, lonA, latB, lonB)
    dAP = haversine(latP, lonP, latA, lonA)
    dBP = haversine(latP, lonP, latB, lonB)

    # 使用球面余弦定理计算角PAB的余弦值
    cosP = (dAP ** 2 + dBP ** 2 - dAB ** 2) / (2 * dAP * dBP)

    # 计算角PAB的弧度值
    PAB = math.acos(cosP)

    # 计算点P到直线AB的垂直距离，即球面三角形的高
    h = dAP * math.sin(PAB)
    return h


def getshiptra(mmsi, arrivetime, upordownwater, reachcode):
    """
    通过mmsi查询TD数据库中数据表，得到船舶到达鸣笛标前一小时的轨迹，通过轨迹得到船舶航行到指定位置的时间
    :param mmsi: MMSI号，字符串类型
    :param arrivetime: 船舶到达鸣笛标的事时间，datetime类型
    :param upordownwater: 船舶上水或者下水,int类型,0表示上水,1表示下水
    :param reachcode: 控制河段名,int类型,11筲箕背,12铜鼓滩,13香炉滩
    :return: 到达鸣笛标前1km、2km、3km的时间
    """
    conn = taos.connect(
                        host='127.0.0.1',
                        user="root",
                        password="taosdata",
                        port=6030,
                        # database="demo",
                        config="C:\TDengine\cfg",  # for windows the default value is C:\TDengine\cfg
                        timezone="Asia/Shanghai")  # default your host's timezone
    cursor = conn.cursor()
    cursor.execute("USE YB_ship_tra")

    try:
        tablename = "mmis" + mmsi
        # 创建一个表示一个小时的timedelta对象
        # one_hour = timedelta(hours=1)
        one_hour = timedelta(minutes=30)  # 30分钟
        one_hour_ago = arrivetime - one_hour
        sql = f"SELECT * FROM {tablename} WHERE post_time > '{one_hour_ago}' AND post_time <= '{arrivetime}' ORDER BY post_time DESC;"
        cursor.execute(sql)
        results = cursor.fetchall()
        # print("查询表" + tablename + "成功!")
        if reachcode == 11:
            if upordownwater == 0:
                # 上水,看下鸣笛标
                lonA, latA, lonB, latB = 104.95222127067784, 28.81696770899918, 104.96622280749287, 28.809749179281148
                # print(lonA, latA, lonB, latB)
            else:
                # 下水,看上鸣笛标
                lonA, latA, lonB, latB = 104.93803017254517, 28.78191105307374, 104.95075799442837, 28.77565556833888
                # print(lonA, latA, lonB, latB)
        elif reachcode == 12:
            if upordownwater == 0:
                lonA, latA, lonB, latB = 105.02024687162802, 28.838667400070694, 105.01152296738127, 28.822655023760966
            else:
                lonA, latA, lonB, latB = 104.99629977095651, 28.845955335325492, 104.99731738558947, 28.839225573949264
        elif reachcode == 13:
            if upordownwater == 0:
                lonA, latA, lonB, latB = 105.02079748989885, 28.755289987109393, 105.00651626634304, 28.746605894420618
            else:
                lonA, latA, lonB, latB = 105.03216232242518, 28.76619651651376, 105.02576236006293, 28.785901087004518

        xkmtowhistle = list()
        lon, lat = results[0][1], results[0][2]
        for i in results:
            lonP, latP = i[1], i[2]
            # 计算距离
            distance = haversine(lat, lon, latP, lonP)
            if abs(distance - 1) < 0.1 and len(xkmtowhistle) == 0:
                time = i[0].replace(tzinfo=None)
                onekmtowhistle = str(round((arrivetime - time).seconds / 60, 2)) + 'min'
                xkmtowhistle.append(onekmtowhistle)
            if abs(distance - 2) < 0.1 and len(xkmtowhistle) == 1:
                time = i[0].replace(tzinfo=None)
                twokmtowhistle = str(round((arrivetime - time).seconds / 60, 2)) + 'min'
                xkmtowhistle.append(twokmtowhistle)
            if abs(distance - 3) < 0.1 and len(xkmtowhistle) == 2:
                time = i[0].replace(tzinfo=None)
                threekmtowhistle = str(round((arrivetime - time).seconds / 60, 2)) + 'min'
                xkmtowhistle.append(threekmtowhistle)

        # print(xkmtowhistle)
        cursor.close()
        conn.close()

        return xkmtowhistle
    except :
        cursor.close()
        conn.close()
        print("表" + tablename + "不存在!")
        return []  # 表不存在,与上面返回值类型保持一致,返回一个空列表(不然返回值为None,后续使用得到的返回值会报错)




# 创建数据库连接
db = mysql.connector.connect(
    host="localhost",  # MySQL服务器地址
    user="root",   # 用户名
    password="123456",  # 密码
)
# 创建游标对象，用于执行SQL查询
cursor = db.cursor()
cursor.execute("use yibin")
cursor.execute('drop table shippasstime')
cursor.execute(
    'create table shippasstime (shipmmsi varchar(9) not null, shipupordown int not null, reachcode int not null, waterlevel double not null, tonnage int,inorouttime datetime, passtime varchar(20), 1kmtowhistle varchar(20), 2kmtowhistle varchar(20), 3kmtowhistle varchar(20), primary key (shipmmsi, shipupordown, reachcode, waterlevel));')


cursor.execute("select * from shippassrecord")
results = cursor.fetchall()

passrecorddata = list()
for i in results:
    data = list()
    try:
        passtime = str(round((i[12] - i[11]).seconds / 60, 2)) + 'min'
    except TypeError:
        continue
    data.append(i[1])           # shipmmsi
    data.append(i[6])           # shipupordown  0表示上水,1表示下水
    data.append(int(i[26]))     # reachcode     11筲箕背,12铜鼓滩,13香炉滩
    data.append(i[17])          # waterlevel
    data.append(i[14])          # tonnage
    data.append(i[11])          # inorouttime
    data.append(passtime)       # passtime
    mmsi = i[1]
    xkmtowhistle = getshiptra(mmsi, i[11], i[6], int(i[26]))
    if len(xkmtowhistle):
        data.extend(xkmtowhistle)
    passrecorddata.append(data)
    insert_stmt = (
        "INSERT INTO shippasstime (shipmmsi, shipupordown, reachcode, waterlevel, tonnage, inorouttime, passtime, 1kmtowhistle, 2kmtowhistle, 3kmtowhistle) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        "on duplicate key update tonnage=%s, inorouttime=%s, passtime=%s, 1kmtowhistle=%s, 2kmtowhistle=%s, 3kmtowhistle=%s"
    )

    # shipmmsi,shipupordown,reachcode,waterlevel为空值的话不插入（目前只有waterlevel可能出现空值）
    # 要存入数据库的数据
    # 判断水位是否为空值
    if data[3] is None:
        continue
    else:
        if len(data) < 10:
            data.extend([''] * (10 - len(data)))
        # 当mmsi,shipupordown,reachcode,waterlevel重复时，获取需要更新的数据
        last_six_elements = data[-6:]
        data += last_six_elements
        cursor.execute(insert_stmt, data)
        # 提交到数据库执行
        db.commit()
        print(data)



cursor.close()
db.close()


# 控制河段代码:(下水船舶看上水鸣笛标.上水船舶看下水鸣笛标)
# 11筲箕背
# 下鸣笛标:左岸[104.95222127067784, 28.81696770899918] 右岸[104.96622280749287, 28.809749179281148]
# 上鸣笛标:左岸[104.93803017254517, 28.78191105307374] 右岸[104.95075799442837, 28.77565556833888]

# 12铜鼓滩
# 下鸣笛标:左岸[105.02024687162802, 28.838667400070694] 右岸[105.01152296738127, 28.822655023760966]
# 上鸣笛标:左岸[104.99629977095651, 28.845955335325492] 右岸[104.99731738558947, 28.839225573949264]


# 13香炉滩
# 下鸣笛标:左岸[105.02079748989885, 28.755289987109393] 右岸[105.00651626634304, 28.746605894420618]
# 上鸣笛标:左岸[105.03216232242518, 28.76619651651376] 右岸[105.02576236006293, 28.785901087004518]




