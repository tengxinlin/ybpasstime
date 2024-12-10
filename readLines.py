import configparser

"""读取配置文件中的航道里程线"""
"""根据上界限标的经纬度坐标29.5969127895924,106.797736287117
来选取上游前n个里程线区域和下游m个里程线区域
"""
def readlines(given_point,n,m):
    """读取配置文件中的航道里程线，根据上界限标的经纬度坐标29.5969127895924,106.797736287117
    来选取上游前n个里程线区域和下游m个里程线区域"""
    # 创建一个ConfigParser对象
    config = configparser.ConfigParser()
    # 读取INI文件
    config.read('航道里程线.ini')

    # 创建一个航道里程线空字典来存储键值对
    data_dict = {}

    # 检查是否存在名为“航道里程线”的节
    if '航道里程线' in config.sections():
        # 获取“航道里程线”节下的所有键值对
        for key in config['航道里程线']:
            # 将键转换为整数类型
            int_key = int(key)

            # 获取包含两个点经纬度坐标的字符串
            coordinate_str = config['航道里程线'][key]

            # 分割字符串，得到两个点的经纬度坐标
            coordinates = coordinate_str.split(',')

            # 将坐标字符串转换为浮点数，并分成两个点
            point1 = (float(coordinates[0]), float(coordinates[1]))
            point2 = (float(coordinates[2]), float(coordinates[3]))

            # 将两个点的坐标列表添加到字典中
            data_dict[int_key] = [point1, point2]

    # 根据关键字的大小顺序对字典进行排序
    sorted_data_dict = {k: data_dict[k] for k in sorted(data_dict)}

    # 打印排序后的字典以查看结果
    '''
    for key, value in sorted_data_dict.items():
        print(f"Key: {key}, Value: {value}")
    '''

    """根据获得的航道里程线字典获取每邻的两条航道里程线围成的区域集合，
    两根相邻里程线的四个点围成的区域的集合 
    初始化应用排序，前两个点为下游里程线的点后两个点为上游里程线点"""
    # 存储所有相邻两条航道里程线围成多边形的四个点的列表
    areaTwoLinesALL = []

    # 迭代排序后的字典，提取相邻两条航道里程线的四个点
    for current_key, current_value in sorted_data_dict.items():
        # 当前航道里程线的两个点
        current_points = current_value

        # 检查是否存在下一条航道里程线
        if current_key + 1 in sorted_data_dict:
            next_key = current_key + 1
            next_points = sorted_data_dict[next_key]

            # 将当前航道和下一条航道的四个点组合在一起
            combined_points = current_points + next_points

            # 添加到areaTwoLinesALL列表中
            areaTwoLinesALL.append(combined_points)


    # given_point = (29.5889408833593,106.709067821503)
    # 存储坐标点所在的区域的前6个区域和后3个区域的坐标点
    areaTwoLines = []
    index=0

    # 遍历areaTwoLinesALL列表，检查给定的经纬度坐标是否在每个区域的四个点围成的多边形内
    for i, polygon in enumerate(areaTwoLinesALL):
        if is_point_in_polygon(given_point[0], given_point[1], polygon):
            # 如果坐标在某个区域内，记录该区域的索引
            index = i
            break

    # 根据记录的索引，选取该区域的前n个区域和后m个区域
    start_index = max(0, index - n)
    end_index = min(len(areaTwoLinesALL), index + m+1)  # 因为要包括后m个区域，所以是index + m+1

    for i in range(start_index, end_index):
        areaTwoLines.append(areaTwoLinesALL[i])

    #这样给定上界限坐标，就能得到想要的航道里程线范围的列表索引
    return areaTwoLines
    # # 打印areaTwoLines列表
    # for i, polygon in enumerate(areaTwoLines):
    #     print(f"Polygon {i + 1}: {polygon}")


"""判断两线段p1p2和p3p4是否相交"""
def do_line_segments_intersect(p1, p2, p3, p4):
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    # 检查线段是否相交
    return ccw(p1, p2, p3) != ccw(p1, p2, p4) and ccw(p3, p4, p1) != ccw(p3, p4, p2)

"""调整多边形的后两个点，使得前两个点连线与后两个点连线不相交,获得一个顺序排列得多边形区域坐标点"""
def adjust_polygon(polygon):
    p1, p2, p3, p4 = polygon[0],polygon[1],polygon[2],polygon[3]
    #构建区域是第一条里程线和第二条里程线，现在要判断这个区域坐标排列是否顺序，应该是第一个点和第四个点的线段与第二个点与第三个点的线段来判断
    if do_line_segments_intersect(p1, p4, p3, p2):
        # 交换p3和p4的位置
        return [p1, p2, p4, p3]
    return polygon

def is_point_in_polygon(x, y, polygon):
    """
    判断点是否在多边形内
    :param x: 点的x坐标
    :param y: 点的y坐标
    :param polygon: 多边形顶点列表，每个顶点是一个(x, y)元组
    :return: 点在多边形内返回True，否则返回False
    """
    #将多边形区域按照顺序的坐标点排列
    polygon=adjust_polygon(polygon)

    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]

    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside



def get_areaTwoLines_100(areaTwoLines):
    """把获取到的里程线区域，每个区域划分为默认100个小区域，相当于一个区域占10米"""
    # 对每个区域进行划分
    areaTwoLines_100=[]
    for polygon in areaTwoLines:
        small_regions = divide_polygon_into_small_regions(polygon)
        areaTwoLines_100.extend(small_regions)
    return areaTwoLines_100


def divide_polygon_into_small_regions(polygon,number=100):
    """
    将获得的控制河段的里程线区域的每一个区域划分为默认100个小区域
    :param polygon: 多边形顶点列表，每个顶点是一个(x, y)元组
    :return: 划分后的小区域顶点列表
    """
    small_regions = []
    # 将多边形区域按照顺序的坐标点排列，这样划分为100份小区域的时候，就是第1个点和第3个点连成的线段、第2个点和第4个点连成的线段来划分
    polygon = adjust_polygon(polygon)

    n = len(polygon)

    for i in range(n):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % n]
        p3 = polygon[(i + 2) % n]
        p4 = polygon[(i + 3) % n]

        # 使用线性插值找到p1和p3之间的100个点
        x1_values = [p1[0] + (p3[0] - p1[0]) * t / number for t in range(number+1)]
        y1_values = [p1[1] + (p3[1] - p1[1]) * t / number for t in range(number+1)]


        # 使用线性插值找到p2和p4之间的100个点
        x2_values = [p2[0] + (p4[0] - p2[0]) * t / number for t in range(number+1)]
        y2_values = [p2[1] + (p4[1] - p2[1]) * t / number for t in range(number+1)]

        # 将这些点作为小区域的顶点
        for j in range(number):
            p11=(x1_values[j],y1_values[j])
            p22=(x2_values[j],y2_values[j])
            p33=(x1_values[j+1],y1_values[j+1])
            p44=(x2_values[j+1],y2_values[j+1])
            small_region = (p11,p22,p33,p44)
            small_regions.append(small_region)

    return small_regions


def get_AISPointIndex(aisPoint,small_regions):
    """计算AIS点在小里程线区域内的索引号
    上界限标的中心点在每默认10米的小里程线区域（10米一个区域）的与AIS坐标点在每10米的小里程线区域的索引号只差就等于
    :param aisPoint: AIS坐标点
    :param riverPoint：控制河段上界限表中心点所在的索引号
    :param small_regions：将获得的控制河段的里程线区域的每一个区域划分为默认100个小区域
    :return: 距离，索引号乘以默认10米一个区域，若AIS不在计算区域内，返回NONE
    """
    indexAISPoint = 0

    # 遍历small_regions列表，检查给定的经纬度坐标是否在每个区域的四个点围成的多边形内
    for i, polygon in enumerate(small_regions):
        if is_point_in_polygon(aisPoint[0], aisPoint[1], polygon):
            # 如果坐标在某个区域内，记录该区域的索引
            indexAISPoint = i
            break
    else:#AIS点不在计算区域内，返回距离为空
        return None

    for i, polygon in enumerate(small_regions):
        if is_point_in_polygon(aisPoint[0], aisPoint[1], polygon):
            # 如果坐标在某个区域内，记录该区域的索引
            indexAISPoint = i
            break
    return indexAISPoint

def get_UpBorderPointIndex(riverPoint,small_regions):
    """计算控制河段上界限标的中心点在每10米的小里程线区域（默认10米一个区域）的索引号
    :param
    riverPoint：控制河段上界限表中心点坐标
    :param
    small_regions：将获得的控制河段的里程线区域的每一个区域划分为默认100个小区域
    :return 索引号
    """
    index = 0

    # 遍历small_regions列表，检查给定的经纬度坐标是否在每个区域的四个点围成的多边形内
    for i, polygon in enumerate(small_regions):
        if is_point_in_polygon(riverPoint[0], riverPoint[1], polygon):
            # 如果坐标在某个区域内，记录该区域的索引
            index = i
            break
    return index

def get_UpWhistlePointIndex(riverPoint,small_regions):
    """计算控制河段上鸣笛标标的中心点在每10米的小里程线区域（默认10米一个区域）的索引号
    :param
    riverPoint：控制河段上鸣笛标标中心点坐标
    :param
    small_regions：将获得的控制河段的里程线区域的每一个区域划分为默认100个小区域
    :return 索引号
    """
    index = 0

    # 遍历small_regions列表，检查给定的经纬度坐标是否在每个区域的四个点围成的多边形内
    for i, polygon in enumerate(small_regions):
        if is_point_in_polygon(riverPoint[0], riverPoint[1], polygon):
            # 如果坐标在某个区域内，记录该区域的索引
            index = i
            break
    return index

def get_DownBorderPointIndex(riverPoint,small_regions):
    """计算控制河段下界限标的中心点在每10米的小里程线区域（默认10米一个区域）的索引号
    :param
    riverPoint：控制河段下界限表中心点坐标
    :param
    small_regions：将获得的控制河段的里程线区域的每一个区域划分为默认100个小区域
    :return 索引号
    """
    index = 0

    # 遍历small_regions列表，检查给定的经纬度坐标是否在每个区域的四个点围成的多边形内
    for i, polygon in enumerate(small_regions):
        if is_point_in_polygon(riverPoint[0], riverPoint[1], polygon):
            # 如果坐标在某个区域内，记录该区域的索引
            index = i
            break
    return index

def get_DownWhistlePointIndex(riverPoint,small_regions):
    """计算控制河段下鸣笛标标的中心点在每10米的小里程线区域（默认10米一个区域）的索引号
    :param
    riverPoint：控制河段下鸣笛标标中心点坐标
    :param
    small_regions：将获得的控制河段的里程线区域的每一个区域划分为默认100个小区域
    :return 索引号
    """
    index = 0

    # 遍历small_regions列表，检查给定的经纬度坐标是否在每个区域的四个点围成的多边形内
    for i, polygon in enumerate(small_regions):
        if is_point_in_polygon(riverPoint[0], riverPoint[1], polygon):
            # 如果坐标在某个区域内，记录该区域的索引
            index = i
            break
    return index

get_areaTwoLines_100(readlines((29.5858527082969,106.844653487206),6,5))