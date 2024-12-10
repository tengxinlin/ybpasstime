"""
源文件:passtime.py
在源文件基础上修改了MySQL,TD engine密码,TD数据库名称
"""
import cursor
import mysql.connector
from datetime import datetime, timedelta
import math
import taos
import readLines


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
    通过mmsi查询TD数据库中数据表，得到船舶到达上界限表前一小时的轨迹，通过轨迹得到船舶航行到指定位置的时间,下水就是距离上界限表1-5km的时间距离，上水就是距离下界限标1-3km的时间
    :param mmsi: MMSI号，字符串类型
    :param arrivetime: 船舶到达鸣笛标的事时间，datetime类型
    :param upordownwater: 船舶上水或者下水,int类型,0表示上水,1表示下水
    :param reachcode: 控制河段名,int类型,11筲箕背,12铜鼓滩,13香炉滩
    :return: 到达鸣笛标前1km、2km、3km的时间
    """
    conn = taos.connect(
        host='127.0.0.1',
        user="root",
        password="cqdx2504@A412",
        port=6030,
        # database="demo",
        config="C:\TDengine\cfg",  # for windows the default value is C:\TDengine\cfg
        timezone="Asia/Shanghai")  # default your host's timezone
    cursor = conn.cursor()
    cursor.execute("USE ais_ships_mmsi")

    try:
        tablename = "mmis" + mmsi
        # 创建一个表示一个小时的timedelta对象
        # one_hour = timedelta(hours=1)
        one_hour = timedelta(minutes=40)  # 30分钟
        one_hour_ago = arrivetime - one_hour
        sql = f"SELECT * FROM {tablename} WHERE post_time > '{one_hour_ago}' AND post_time <= '{arrivetime}' ORDER BY post_time DESC;"
        cursor.execute(sql)
        results = cursor.fetchall()
        # print("查询表" + tablename + "成功!")

        timeToBorderList = list()
        areaTwoLines=[]
        riverPointIndex = 0
        distance = 0
        # 11筲箕背,12铜鼓滩,13香炉滩
        if reachcode == 11:
            areaTwoLines=areaTwoLines_SJB_100
            if upordownwater == 1:
                riverPointIndex = index_SJB_UpBorder
            else:
                riverPointIndex = index_SJB_DownBorder
        if reachcode == 12:
            areaTwoLines = areaTwoLines_TGT_100
            if upordownwater == 1:
                riverPointIndex = index_TGT_UpBorder
            else:
                riverPointIndex = index_TGT_DownBorder
        if reachcode == "13":
            areaTwoLines = areaTwoLines_XLT_100
            if upordownwater == 1:
                riverPointIndex = index_XLT_UpBorder
            else:
                riverPointIndex = index_XLT_DownBorder
        t1,t2,t3,t4,t5=[],[],[],[],[]
        t6,t7,t8=[],[],[]
        for i in results:
            #字段名：
            """
            posttime:时间戳
            Longitude：经度
            latitude：纬度
            cog：航向
            HEADING：转向角
            SPEED：速度，步长1/10节
            """
            lonP, latP = i[1], i[2]
            point = (latP, lonP)  # 计算索引的时候纬度lat在前，经度log在后
            indexpoint = readLines.get_AISPointIndex(point, areaTwoLines)
            distance = (indexpoint-riverPointIndex )* 10
            if upordownwater:#如果是下水，计算到距离5km
                speed = i[5] * 10 * 0.5144444  # 1节约等于0.5144444米/秒
                aistime = i[0].replace(tzinfo=None)  # 该AIS点的时间戳
                if 0 < distance <= 1000:  # 船舶距离界限标1km内
                    #按1km里程线区域内匀速来计算船舶刚好距离界限表1km的时间
                    time=10*(100-((indexpoint-riverPointIndex) % 100))/speed#时间差
                    alltime=round(((aistime-arrivetime).seconds +time)/60,2) #距离刚好1km时，到达上界限表所需的时间（min）
                    t1.append(alltime)
                # 因为在1km内肯定会有好多点在次区域内
                # 按照比例的方法，以该点的速度和距离界来等比例匀速计算，刚好距离1km的点距离的时间（多个点就要平均）
                if 1000 < distance <= 2000:  # 船舶距离界限标2km内
                    # 按1km里程线区域内匀速来计算船舶刚好距离界限表2km的时间
                    time = 10 * (100 - ((indexpoint - riverPointIndex) % 100)) / speed  # 时间差
                    alltime = round(((aistime - arrivetime).seconds + time) / 60, 2)  # 距离刚好1km时，到达上界限表所需的时间（min）
                    t2.append(alltime)
                if 2000 < distance <= 3000:  # 船舶距离界限标3km内
                    # 按1km里程线区域内匀速来计算船舶刚好距离界限表3km的时间
                    time = 10 * (100 - ((indexpoint - riverPointIndex) % 100)) / speed  # 时间差
                    alltime = round(((aistime - arrivetime).seconds + time) / 60, 2)  # 距离刚好3km时，到达上界限表所需的时间（min）
                    t3.append(alltime)
                if 3000 < distance <= 4000:  # 船舶距离界限标4km内
                    # 按1km里程线区域内匀速来计算船舶刚好距离界限表4km的时间
                    time = 10 * (100 - ((indexpoint - riverPointIndex) % 100)) / speed  # 时间差
                    alltime = round(((aistime - arrivetime).seconds + time) / 60, 2)  # 距离刚好4km时，到达上界限表所需的时间（min）
                    t4.append(alltime)
                if 4000 < distance <= 5000:  # 船舶距离界限标5km内
                    # 按1km里程线区域内匀速来计算船舶刚好距离界限表5km的时间
                    time = 10 * (100 - ((indexpoint - riverPointIndex) % 100)) / speed  # 时间差
                    alltime = round(((aistime - arrivetime).seconds + time) / 60, 2)  # 距离刚好5km时，到达上界限表所需的时间（min）
                    t5.append(alltime)
            else:  # 如果是上水，计算到距离3km
                if 0 < distance <= 1000:  # 船舶距离界限标1km内
                    # 按1km里程线区域内匀速来计算船舶刚好距离界限表1km的时间
                    time = 10 * (100 - ((riverPointIndex-indexpoint) % 100)) / speed  # 时间差
                    alltime = round(((aistime - arrivetime).seconds + time) / 60, 2)  # 距离刚好1km时，到达上界限表所需的时间（min）
                    t6.append(alltime)
                # 因为在1km内肯定会有好多点在次区域内
                # 按照比例的方法，以该点的速度和距离界来等比例匀速计算，刚好距离1km的点距离的时间（多个点就要平均）
                if 1000 < distance <= 2000:  # 船舶距离界限标2km内
                    # 按1km里程线区域内匀速来计算船舶刚好距离界限表2km的时间
                    time = 10 * (100 - ((riverPointIndex - indexpoint) % 100)) / speed  # 时间差
                    alltime = round(((aistime - arrivetime).seconds + time) / 60, 2)  # 距离刚好2km时，到达上界限表所需的时间（min）
                    t7.append(alltime)
                if 2000 < distance <= 3000:  # 船舶距离界限标3km内
                    # 按1km里程线区域内匀速来计算船舶刚好距离界限表3km的时间
                    time = 10 * (100 - ((riverPointIndex - indexpoint) % 100)) / speed  # 时间差
                    alltime = round(((aistime - arrivetime).seconds + time) / 60, 2)  # 距离刚好3km时，到达上界限表所需的时间（min）
                    t8.append(alltime)
                    
            #计算多个点求得的平均速度
                if not t1:  # 如果列表为空
                    t1average= 0  # 时间为0，可能是上水船舶，计算的就是0
                else :
                    t1average=sum(t1)/len(t1)
                if not t2:  # 如果列表为空
                    t2average = 0  # 时间为0，可能是上水船舶，计算的就是0
                else:
                    t2average = sum(t2) / len(t2)
                if not t3:  # 如果列表为空
                    t3average = 0  # 时间为0，可能是上水船舶，计算的就是0
                else:
                    t3average = sum(t3) / len(t3)
                if not t4:  # 如果列表为空
                    t4average = 0  # 时间为0，可能是上水船舶，计算的就是0
                else:
                    t4average = sum(t4) / len(t4)
                if not t5:  # 如果列表为空
                    t5average = 0  # 时间为0，可能是上水船舶，计算的就是0
                else:
                    t5average = sum(t5) / len(t5)

                if not t6:  # 如果列表为空
                    t6average = 0  # 时间为0，可能是下水船舶，计算的就是0
                else:
                    t6average = sum(t6) / len(t6)
                if not t7:  # 如果列表为空
                    t7average = 0  # 时间为0，可能是下水船舶，计算的就是0
                else:
                    t7average = sum(t7) / len(t7)
                if not t8:  # 如果列表为空
                    t8average = 0  # 时间为0，可能是下水船舶，计算的就是0
                else:
                    t8average = sum(t8) / len(t8)
                timeToBorderList.append(t1average)
                timeToBorderList.append(t2average)
                timeToBorderList.append(t3average)
                timeToBorderList.append(t4average)
                timeToBorderList.append(t5average)
                timeToBorderList.append(t6average)
                timeToBorderList.append(t7average)
                timeToBorderList.append(t8average)
                return timeToBorderList

        cursor.close()
        conn.close()

        return xkmtowhistle
    except:
        cursor.close()
        conn.close()
        print("表" + tablename + "不存在!")
        return []  # 表不存在,与上面返回值类型保持一致,返回一个空列表(不然返回值为None,后续使用得到的返回值会报错)


# 创建数据库连接
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="cqdx2504@A412",
)
# 创建游标对象，用于执行SQL查询
cursor = db.cursor()
cursor.execute("use yibin")
cursor.execute('drop table shippasstime')
cursor.execute(
    'create table shippasstime (shipmmsi varchar(9) not null, shipupordown int not null, reachcode int not null, waterlevel double not null, tonnage int,inorouttime datetime, passtime varchar(20),'
    ' 1kmtoUpBorder varchar(20), 2kmtoUpBorder varchar(20), 3kmtoUpBorder varchar(20), 4kmtoUpBorder varchar(20),5kmtoUpBorder varchar(20),1kmtoDownBorder varchar(20), 2kmtoDownBorder varchar(20), 3kmtoDownBorder varchar(20), primary key (shipmmsi, shipupordown, reachcode, waterlevel, tonnage));')

cursor.execute("select * from shippassrecord")
results = cursor.fetchall()

# 筲箕背控制河段的上游6个区域，下游4个区域的航道里程线
SJB_UpBorder = (29, 108)  # 筲箕背的上界限表的中心点，纬度lat在前，经度log在后
SJB_DownBorder = (29,109)  # 筲箕背的下界限表的中心点，纬度lat在前，经度log在后
areaTwoLines_SJB = readLines.readlines(SJB_UpBorder, 6, 5)  # 筲箕背控制河段的上游6个，下游5个的航道里程线区域（1km一个区域）
areaTwoLines_SJB_100 = readLines.get_areaTwoLines_100(
    areaTwoLines_SJB)  # 筲箕背控制河段的上游6个，下游5个的航道里程线区域（1km一个区域），每个区域划分为100份
index_SJB_UpBorder = readLines.get_UpBorderPointIndex(SJB_UpBorder, areaTwoLines_SJB_100)  # 筲箕背控制河段的上界限表所作的索引
index_SJB_DownBorder = readLines.get_DownBorderPointIndex(SJB_DownBorder, areaTwoLines_SJB_100)  # 筲箕背控制河段的下界限表所作的索引

# 铜鼓滩控制河段的上游6个区域，下游4个区域的航道里程线
TGT_UpBorder = (29.5969267830225,106.828431487083)  # 铜鼓滩的上界限表的中心点，纬度lat在前，经度log在后
TGT_DownBorder = (29.5969267830225,106.828431487083)  # 铜鼓滩的下界限表的中心点，纬度lat在前，经度log在后
areaTwoLines_TGT = readLines.readlines(TGT_UpBorder, 6, 5)  # 铜鼓滩控制河段的上游6个，下游5个的航道里程线区域（1km一个区域）
areaTwoLines_TGT_100 = readLines.get_areaTwoLines_100(
    areaTwoLines_TGT)  # 铜鼓滩控制河段的上游6个，下游5个的航道里程线区域（1km一个区域），每个区域划分为100份
index_TGT_UpBorder = readLines.get_UpBorderPointIndex(TGT_UpBorder, areaTwoLines_TGT_100)  # 铜鼓滩控制河段的上界限表所作的索引
index_TGT_DownBorder = readLines.get_DownBorderPointIndex(TGT_DownBorder, areaTwoLines_TGT_100)  # 铜鼓滩控制河段的下界限表所作的索引

# 香炉摊控制河段的上游6个区域，下游4个区域的航道里程线
XLT_UpBorder = (29, 108)  # 香炉摊的上界限表的中心点，纬度lat在前，经度log在后
XLT_DownBorder = (29.5969267830225,106.828431487083)  # 香炉摊的下界限表的中心点，纬度lat在前，经度log在后
areaTwoLines_XLT = readLines.readlines(XLT_UpBorder, 6, 5)  # 香炉摊控制河段的上游6个，下游5个的航道里程线区域（1km一个区域）
areaTwoLines_XLT_100 = readLines.get_areaTwoLines_100(
    areaTwoLines_XLT)  # 香炉摊控制河段的上游6个，下游5个的航道里程线区域（1km一个区域），每个区域划分为100份
index_XLT_UpBorder = readLines.get_UpBorderPointIndex(XLT_UpBorder, areaTwoLines_XLT_100)  # 香炉摊控制河段的上界限表所作的索引
index_XLT_DownBorder = readLines.get_DownBorderPointIndex(XLT_DownBorder, areaTwoLines_XLT_100)  # 香炉滩控制河段的下界限表所作的索引

passrecorddata = list()
for i in results:
    data = list()
    try:
        passtime = str(round((i[12] - i[11]).seconds / 60, 2)) + 'min'
    except TypeError:
        continue
    if i[17] is None:  # waterlevel为空就不需要
        continue
    # 备注有松车下或下界限标等候,说明不是正常上下水通过的船舶，船舶有所减速或停留，需要舍弃
    if ("松车下" in i[21]) or ("下界限标等候" in i[21]) or ("下界限标外等候" in i[21]):
        continue

    data.append(i[1])  # shipmmsi
    data.append(i[6])  # shipupordown  0表示上水,1表示下水
    data.append(int(i[26]))  # reachcode     11筲箕背,12铜鼓滩,13香炉滩
    data.append(i[17])  # waterlevel
    data.append(i[14])  # tonnage
    data.append(i[11])  # inorouttime
    data.append(passtime)  # passtime
    mmsi = i[1]

    xkmtowhistle = getshiptra(mmsi, i[11], int(i[6]), int(i[26]))
    if len(xkmtowhistle):
        data.extend(xkmtowhistle) #下水1-5km的时间和上水1-3km的时间都在一起
    #需要把水位和载重也按区间来分开
    #水位0.5米为一个区间，载重500为一个区间
    #因为之前可能存储过这个区间定位的时间了，需要读取出这个时间来，然后计算平均数，没有平均数就插入这个新的标签数据


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
