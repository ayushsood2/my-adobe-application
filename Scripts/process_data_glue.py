import sys
import os
import boto3
from datetime import datetime
from pyspark.sql.window import Window
from pyspark.sql import SparkSession
from pyspark.sql import SQLContext
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.transforms import *
from awsglue.job import Job
from awsglue.utils import getResolvedOptions

args = getResolvedOptions(sys.argv, ["JOB_NAME","input_file_path", "role_name"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)
client = boto3.client('glue')

# spark = SparkSession.builder.appName('abc').getOrCreate()
# path = 's3://serverless-flask-dev-serverlessdeploymentbucket-1wdb3e4zzsp3/input_file/data_adobe.tsv'
path = args["input_file_path"]
role_name = args['role_name']
output_file_path = f"s3://serverless-flask-dev-serverlessdeploymentbucket-1wdb3e4zzsp3/output_file/{datetime.today().strftime('%Y-%m-%d')}_SearchKeywordPerformance.tab.tsv"
output_file_name = output_file_path.split('/')[-1]
hits_data = spark.read.csv(path,header=True, sep= '\t', inferSchema=True)
hits_data.createOrReplaceTempView('hits_data')
revenue_data = spark.sql('''
                SELECT
                    SEARCH_ENGINE_DOMAIN,
                    SEARCH_KEYWORD,
                    SUM(`total_revenue`) as REVENUE
                    FROM
                        (
                         SELECT
                             date_time,
                             ip,
                             CONCAT(SPLIT(PARSE_URL(`first_referrer`, 'HOST'),'[.]')[1],'.',
                                     SPLIT(PARSE_URL(`first_referrer`, 'HOST'),'[.]')[2])
                             as SEARCH_ENGINE_DOMAIN,
                             REPLACE(LOWER(PARSE_URL(`first_referrer`,'QUERY','[a-z]')),'+',' ') as SEARCH_KEYWORD,
                             SPLIT(`product_list`,';')[1] as product_name,
                             CAST(SPLIT(`product_list`,';')[3] as Integer) as total_revenue
                             FROM
                             (
                                 SELECT
                                     date_time,
                                     ip,
                                     product_list,
                                     FIRST_VALUE(referrer)over (PARTITION BY ip ORDER BY date_time ASC) as first_referrer
                                     FROM hits_data
                                )
                            )
                            GROUP BY
                                SEARCH_KEYWORD,
                                SEARCH_ENGINE_DOMAIN
                            ORDER BY
                                REVENUE DESC
                                ''')

revenue_data.toPandas().to_csv(output_file_path, sep = '\t',index = False)

response = client.update_job(
    JobName='process_data',
    JobUpdate={
        'Description': 'updating arguments',
        'Role': f'{role_name}',
        'Command': {
            'Name': 'glueetl',
            'ScriptLocation': 's3://aws-glue-scripts-965206423999-us-east-1/ayushsood/process_data_glue.py',
            'PythonVersion': '3'

        },
        'DefaultArguments': {
            '--output-file-name': '{}'.format(output_file_name)
        }
    }
)

job.commit()
