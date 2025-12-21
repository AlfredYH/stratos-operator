'''
Created on 2020年1月30日

@author: JM
'''
#sqlalchemy 资料说不需要创建表，但在本例里面，还是需要先创建表，原因待查
import pandas as pd
import tushare as ts
from sqlalchemy import create_engine

#'数据库类型+数据库驱动名称://用户名:口令@机器地址:端口号/数据库名'
engine_ts = create_engine('mysql+pymysql://root:528491@localhost:3306/alfred_database')
ts.set_token('5eb191319dffb2bb1d87ec3cdcec2adacd2d5d7c205e5b108f080739')

def read_data():
    sql = """SELECT * FROM t2 LIMIT 20"""
    df = pd.read_sql_query(sql, engine_ts)
    return df

df = read_data()
#print(df)


def write_data(df):
    res = df.to_sql('stock_basic', con=engine_ts, index=False, if_exists='append', chunksize=5000)
    print(res)

def get_data():
    pro = ts.pro_api()
    df = pro.daily(ts_code='000001.SZ', start_date='20180701', end_date='20180718')
    return df

df = get_data()
print(df)

if __name__ == '__main__':
    #df = read_data()
    df = get_data()
    write_data(df)
    print(df)

#以上代码成功运行