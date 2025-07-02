from py2neo import Graph, Node, Relationship, NodeMatcher, RelationshipMatcher
#知识图谱可视化
color = {
    "CLASS": "#5470c6",
    "TIME": "#e474c6",
    "LOC": "#147fc6",
    "RES": "#947dc6",
    "EVE": "#847986",
    "EVC": "#8374c6",
    "other": "#111111"
}


def get_node_by_name(g, node_type, name):
    # g=Graph('http://localhost:7474',user='neo4j',password='123456') #连接
    matcher = NodeMatcher(g)
    endnode = matcher.match(node_type, name=name).first()
    print(endnode)
    if endnode != None:
        return endnode
    else:
        return None


def get_str_by_dict(mydict):
    last = ""
    for key in mydict:
        last = str(key) + ":" + str(mydict[key]) + "<br>" + last
    return last


def get_all_relation(start="", relation="", end=""):
    # 重置全局变量
    global cache, datas, links, legend_data, categories
    cache = []
    datas = []
    links = []
    legend_data = []
    categories = []
    
    default_return = {
        "datas": [],
        "links": [],
        "legend_data": [],
        "categories": []
    }
    
    try:
        # 改用bolt协议连接
        g = Graph('bolt://localhost:7687', 
                 user='neo4j', 
                 password='5253812138',
                 secure=False)  # 将 encrypted 改为 secure
        
        sql = "MATCH (n)-[%s]-(b) %s RETURN n,r,b limit 100"
        param = ""
        
        if start != "":
            param = f"WHERE n.name='{start}'"
        if relation != "":
            mr = f"r:{relation}"
        else:
            mr = "r"
        if end != "":
            if "WHERE" in param:
                param += f" AND b.name='{end}'"
            else:
                param = f"WHERE b.name='{end}'"
                
        sql = sql % (mr, param)
        print(f"最终执行的查询语句: {sql}")  # 添加打印语句
        nodes_data_all = g.run(sql).data()
        
        for nodes_relations in nodes_data_all:
            process_node_relation(nodes_relations)
            
        return {
            "datas": datas,
            "links": links,
            "legend_data": legend_data,
            "categories": categories
        }
        
    except Exception as e:
        print(f"Neo4j连接错误: {e}")
        return default_return

def process_node_relation(nodes_relations):
    global cache, datas, links, legend_data, categories
    
    start_node = nodes_relations['n']
    end_node = nodes_relations['b']
    relation = nodes_relations['r']
    
    start_label = str(start_node.labels).replace(":", "")
    end_label = str(end_node.labels).replace(":", "")
    start_dict = dict(start_node)
    end_dict = dict(end_node)
    
    if "name" not in start_dict or "name" not in end_dict:
        return
        
    start_name = start_dict["name"]
    end_name = end_dict["name"]
    
    try:
        relation_type = str(relation.keys).split(" ")[4]
    except Exception as e:
        print(f"获取关系类型错误: {e}")
        return
    
    # 处理起始节点
    if start_name not in cache:
        node_color = color.get(start_label, color["other"])
        datas.append({
            "name": start_name,
            "attr": start_dict,
            "color": node_color,
            "des": get_str_by_dict(start_dict),
            "category": start_label
        })
        cache.append(start_name)
    
    # 处理结束节点
    if end_name not in cache:
        node_color = color.get(end_label, color["other"])
        datas.append({
            "name": end_name,
            "attr": end_dict,
            "color": node_color,
            "des": get_str_by_dict(end_dict),
            "category": end_label
        })
        cache.append(end_name)
    
    # 处理图例和分类
    if start_label not in legend_data:
        legend_data.append(start_label)
        categories.append({"name": start_label})
    if end_label not in legend_data:
        legend_data.append(end_label)
        categories.append({"name": end_label})
    
    # 处理关系
    cache_relation = f"{start_name}-{end_name}"
    if cache_relation not in cache:
        links.append({
            "source": start_name,
            "target": end_name,
            "name": relation_type
        })
        cache.append(cache_relation)
