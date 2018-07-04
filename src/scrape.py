import requests
import datetime
import json
import boto3
import os
import dotenv
import sys



project_dir = os.path.join(os.pardir)
sys.path.append(project_dir)
dotenv_path = os.path.join(project_dir,'.env')
dotenv.load_dotenv(dotenv_path)

#GLOBALS
yesterday = datetime.date.today() - datetime.timedelta(1)
session = requests.Session()
username = os.environ.get("USER_NAME")
password = os.environ.get("PASSWORD")
auth_url = os.environ.get("URL")
raw_bucket = os.environ.get("S3BUCKET_RAW")
equipment = os.environ.get("EQUIPAMENTOS")
url = os.environ.get("URL_ENDPOINT")


#Connect to S3 and check existing reports
s3 = boto3.client('s3')


def get_all_s3_keys(bucket):
    keys = []
    kwargs = {'Bucket': bucket}
    while True:
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp['Contents']:
            keys.append(obj['Key'])
        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break
    return keys


session = requests.Session()  
auth_url = 'http://monitran.com.br/joinville/login'
auth = session.post(auth_url, data={'login': username, 'senha': password})

#Get equipment list
with open(equipment) as json_data:
    equipamentos = json.load(json_data)
equip_set = set([equipamento["equipamento"] for equipamento in equipamentos])
equip_list = list(equip_set)
equip_list.sort()

#Scope for download of reports  
day = str(yesterday.day) #int(os.environ.get("START_DAY"))
month = str(yesterday.month) #int(os.environ.get("START_MONTH"))
year = str(yesterday.year) #int(os.environ.get("START_YEAR"))
start_time = '00'
end_time = '23'


#MODIFICAR LOGICA POIS O TIMEOUT CONSOME MUITO TEMPO
for equip in equip_list:      
    querystring_date = day+"/"+month+"/"+year

    
    params = {"equipamento": equip,
              "dataStr": querystring_date,
              "horaInicio": start_time,
              "horaFim": end_time,
              "opcao": 'excel',
              "exibir": "on"
              }
    req = requests.Request("GET", url, params=params)
    response = session.get(url, params=params, stream=True)
    key = equip + "/" + year + "-" + month.zfill(2) + "-" + day.zfill(2) + '.xlsx'        
    s3.put_object(Body=response.content, Bucket=raw_bucket, Key=key)
    print('S3RAWOBJECT', '-',str(datetime.datetime.now()),'-',equip)