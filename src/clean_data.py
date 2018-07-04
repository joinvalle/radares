#!/usr/bin/env python
import os
import xlrd
import json
import boto3
import xlwt
from io import BytesIO
import time

def create_clean_file():
    clean_file = xlwt.Workbook(encoding='utf-8')
    tab = clean_file.add_sheet('tab1')
    tab.write(0, 0, 'Endereco')
    tab.write(0, 1, 'Corredor')
    tab.write(0, 2, 'Ciclofaixa')
    tab.write(0, 3, 'Numero de faixas')
    tab.write(0, 4, 'Latitude')
    tab.write(0, 5, 'Longitude')
    tab.write(0, 6, 'Sentido')
    tab.write(0, 7, 'Data')
    tab.write(0, 8, 'Equipamento')
    tab.write(0, 9, 'Horario')
    tab.write(0, 10, '00 a 10')
    tab.write(0, 11, '11 a 20')
    tab.write(0, 12, '21 a 30')
    tab.write(0, 13, '31 a 40')
    tab.write(0, 14, '41 a 50')
    tab.write(0, 15, '51 a 60')
    tab.write(0, 16, '61 a 70')
    tab.write(0, 17, '71 a 80')
    tab.write(0, 18, '81 a 90')
    tab.write(0, 19, '91 a 100')
    tab.write(0, 20, 'Acima de 100')
    tab.write(0, 21, 'Total')

    return clean_file

#Get equipment list
with open('equipamentos.json') as json_data:
    equip_list = json.load(json_data)
equip_dict = {i['equipamento']: i for i in equip_list}

s3 = boto3.client('s3')
bucket="monit-data"
#Iterate over all s3 raw data objects
all_raw_files = []
paginator = s3.get_paginator('list_objects')
page_iterator = paginator.paginate(Bucket=bucket, Prefix="raw/")
for page in page_iterator:
    all_raw_files += [c["Key"].split("/", 1)[1] for c in page["Contents"]]

#Iterate over all s3 clean data objectsall_raw_files = []
all_clean_files = []
page_iterator = paginator.paginate(Bucket=bucket, Prefix="clean/")
for page in page_iterator:
    if "Contents" not in page: #in case there is no clean files yet
        break
    all_clean_files += [c["Key"].split("/", 1)[1]  for c in page["Contents"]]

all_files = [file for file in all_raw_files if file not in all_clean_files]

#Create cleaned workbook
for file in all_files:
    start = time.time()

    #Read raw file
    read_key = "raw/" + file
    obj = s3.get_object(Bucket=bucket, Key=read_key)
    wb = xlrd.open_workbook(file_contents=obj['Body'].read())
    sheet = wb.sheets()[0]
    len_data_block = 96

    #check date
    date_parts = sheet.cell(2,1).value.split("\n")[0].split(" ")[1].replace("/", "-").split("-")
    date = date_parts[2] + "-" + date_parts[1] + "-" + date_parts[0] #%Y-%m-%d
    if date != file.split("/")[1].split(".")[0]:
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
        print("No template was found for ", equip, date)
        continue

    if template == 1:
        len_data_block = 96
        block1_begin = 8
        direction = sheet.cell(5,15).value       
        blocks_list = [(0, block1_begin, direction)]

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

            tab.write(write_row, 9, time_slot)
            tab.write(write_row, 10, flow00)
            tab.write(write_row, 11, flow11)
            tab.write(write_row, 12, flow21)
            tab.write(write_row, 13, flow31)
            tab.write(write_row, 14, flow41)
            tab.write(write_row, 15, flow51)
            tab.write(write_row, 16, flow61)
            tab.write(write_row, 17, flow71)
            tab.write(write_row, 18, flow81)
            tab.write(write_row, 19, flow91)
            tab.write(write_row, 20, flow100)
            tab.write(write_row, 21, flowTotal)
            tab.write(write_row, 0, equip_dict[equip]['endereco'])
            tab.write(write_row, 1, equip_dict[equip]['corredor'])
            tab.write(write_row, 2, equip_dict[equip]['ciclofaixa'])
            tab.write(write_row, 3, equip_dict[equip]['n_faixa_carro_sentido'])
            tab.write(write_row, 4, equip_dict[equip]['latitude'])
            tab.write(write_row, 5, equip_dict[equip]['longitude'])           
            tab.write(write_row, 6, direction)
            tab.write(write_row, 7, date)
            tab.write(write_row, 8, equip)

    #Save to s3 object
    stream = BytesIO()
    clean_file.save(stream)
    stream.seek(0)
    write_key = "clean/" + equip + "/" + date + '.xlsx'
    s3.put_object(Body=stream.read(), Bucket='monit-data', Key=write_key)
    
    end = time.time()
    duration = str(round(end - start))
    print("Successfully stored equip " + equip + ", on date " + date + ", in " + duration + " s.")