#!/usr/bin/env python
import os
import sys
import xlrd
import json
import boto3
import xlwt
from io import BytesIO, StringIO
import time
import dotenv
import pandas as pd

from sqlalchemy import create_engine, exc, MetaData, select
from sqlalchemy.engine.url import URL

project_dir = os.path.join(os.pardir)
sys.path.append(project_dir)
dotenv_path = os.path.join(project_dir,'.env')
dotenv.load_dotenv(dotenv_path)


def create_clean_file():
    clean_file = xlwt.Workbook(encoding='utf-8')
    tab = clean_file.add_sheet('tab1')
    tab.write(0, 0, 'pubdate')
    tab.write(0, 1, 'equipment')
    tab.write(0, 2, 'direction')
    tab.write(0, 3, 'time_range')
    tab.write(0, 4, 'speed_00_10')
    tab.write(0, 5, 'speed_11_20')
    tab.write(0, 6, 'speed_21_30')
    tab.write(0, 7, 'speed_31_40')
    tab.write(0, 8, 'speed_41_50')
    tab.write(0, 9, 'speed_51_60')
    tab.write(0, 10, 'speed_61_70')
    tab.write(0, 11, 'speed_71_80')
    tab.write(0, 12, 'speed_81_90')
    tab.write(0, 13, 'speed_91_100')
    tab.write(0, 14, 'speed_100_up')
    tab.write(0, 15, 'total')

    return clean_file

def clean_direction(df):
    df.direction = df.direction.str.split(pat="/", n=1).str.get(1)
    df.direction = df.direction.replace({"^N$": "Norte",
                                         "^S$": "Sul",
                                         "^L$": "Leste",
                                         "^O$": "Oeste"}, regex=True)
    return df   


s3 = boto3.client('s3')
#bucket="production-monitran-data-incoming"
bucket="test-monitran-incoming"

print("Iterate over all s3 incoming objects")
all_incoming_objects = []
paginator = s3.get_paginator('list_objects')
page_iterator = paginator.paginate(Bucket=bucket)
for page in page_iterator:
    all_incoming_objects += [c["Key"] for c in page["Contents"] if "xlsx" in c["Key"]]

#Create cleaned workbook
for file in all_incoming_objects:
    start = time.time()
    print("Begin processing file:", file)
    #Read raw file
    equip, date = file.split("/")
    title_date = date.split(".")[0]
    key = file
    obj = s3.get_object(Bucket=bucket, Key=key)
    wb = xlrd.open_workbook(file_contents=obj['Body'].read())
    sheet = wb.sheets()[0]
    len_data_block = 96

    #check date
    date_parts = sheet.cell(2,1).value.split("\n")[0].split(" ")[1].replace("/", "-").split("-")
    file_date = date_parts[2] + "-" + date_parts[1].zfill(2) + "-" + date_parts[0].zfill(2) #%Y-%m-%d

    if file_date != title_date:
        raise Exception("Data dentro do arquivo não bate com data no nome do arquivo ")

    #check equip
    equip = sheet.cell(5,1).value.split("-")[0]
    if equip != file.split("/")[0]:
        raise Exception("Equipamento dentro do arquivo não bate com equipamento no nome do arquivo ")

    #Create clean file
    clean_file = create_clean_file()
    tab = clean_file.get_sheet("tab1")

    #Define template type
    if (sheet.nrows==109) and (sheet.cell(105,1).value.strip() == "Total Geral"):
        template = 1
    elif (sheet.nrows==210) and (sheet.cell(206,1).value.strip() == "Total Geral"):
        template = 2
    elif (sheet.nrows==205) and (sheet.cell(201,1).value.strip() == "Total Geral"):
        template = 3
    else:
        print("No template was found for ", equip, file_date)
        continue

    if template == 1:
        len_data_block = 96
        block1_begin = 8
        direction = sheet.cell(5,15).value       
        blocks_list = [(0, block1_begin, direction)]

    #Template 2 para relatórios que possuem dois sentidos
    if template == 2:
        len_data_block = 96
        block1_begin = 8
        block2_begin = 109
        block1_direction = sheet.cell(5,15).value
        block2_direction = sheet.cell(106,15).value
        blocks_list = [(0, block1_begin, block1_direction), (len_data_block, block2_begin, block2_direction)]

    if template == 3:
        len_data_block = 192
        block1_begin = 8
        direction = sheet.cell(5,15).value
        blocks_list = [(0, block1_begin, direction)]

    #Get and write data
    for a, block_begin, direction in blocks_list: #First block, than second block
        for i in range(0, len_data_block): #row by row, in each block
            #Read data
            read_row = block_begin + i

            time_slot = sheet.cell(read_row,1).value 
            flow00 = sheet.cell(read_row,5).value 
            flow11 = sheet.cell(read_row,7).value
            flow21 = sheet.cell(read_row,9).value
            flow31 = sheet.cell(read_row,10).value
            flow41 = sheet.cell(read_row,12).value
            flow51 = sheet.cell(read_row,13).value
            flow61 = sheet.cell(read_row,14).value
            flow71 = sheet.cell(read_row,15).value
            flow81 = sheet.cell(read_row,17).value
            flow91 = sheet.cell(read_row,18).value
            flow100 = sheet.cell(read_row,20).value
            flowTotal = sheet.cell(read_row,21).value

            #Write data to excel file
            write_row = a + i + 1

            tab.write(write_row, 0, file_date)
            tab.write(write_row, 1, equip)
            tab.write(write_row, 2, direction)
            tab.write(write_row, 3, time_slot)
            tab.write(write_row, 4, flow00)
            tab.write(write_row, 5, flow11)
            tab.write(write_row, 6, flow21)
            tab.write(write_row, 7, flow31)
            tab.write(write_row, 8, flow41)
            tab.write(write_row, 9, flow51)
            tab.write(write_row, 10, flow61)
            tab.write(write_row, 11, flow71)
            tab.write(write_row, 12, flow81)
            tab.write(write_row, 13, flow91)
            tab.write(write_row, 14, flow100)
            tab.write(write_row, 15, flowTotal)          

    #Create pandas DataFrame
    stream = BytesIO()
    clean_file.save(stream)
    stream.seek(0)
    df = (pd.read_excel(stream)
          .assign(pubdate = lambda df: pd.to_datetime(df.pubdate))
          .pipe(clean_direction)
         )

    #Save to s3 object
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    write_key = equip + "/" + file_date + '.csv'
    s3.put_object(Body=csv_buffer.getvalue(), Bucket='production-monitran-data-processed', Key=write_key)

    #Store in Database
    DATABASE = {
        'drivername': os.environ.get("RADARS_DRIVERNAME"),
        'host': os.environ.get("RADARS_HOST"), 
        'port': os.environ.get("RADARS_PORT"),
        'username': os.environ.get("RADARS_USERNAME"),
        'password': os.environ.get("RADARS_PASSWORD"),
        'database': os.environ.get("RADARS_DATABASE"),
        }

    db_url = URL(**DATABASE)
    engine = create_engine(db_url)
    meta = MetaData()
    meta.bind = engine
    meta.reflect(schema="radars")
    df.to_sql("flows", schema="radars", con=meta.bind, if_exists="append", index=False)

    #If we got here, the database has been populated and the clean document has been successfully stored.
    #Only now should we proceed and delete the file from the incoming bucket

    end = time.time()
    duration = str(round(end - start))
    print("Successfully stored equip " + equip + ", on date " + file_date + ", in " + duration + " s.")
