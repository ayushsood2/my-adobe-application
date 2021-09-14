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

#Initialize Glue and Spark Variables
args = getResolvedOptions(sys.argv, ["JOB_NAME","input_file_path", "role_name"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

#Create required services client
client = boto3.client('glue')

#Get data supplied through input
path = args["input_file_path"]
BUCKET_NAME = args['input_file_path'].split('/')[2]
role_name = args['role_name']
output_file_path = f"s3://{BUCKET_NAME}/output_file/{datetime.today().strftime('%Y-%m-%d')}_SearchKeywordPerformance.tab.tsv"
output_file_name = output_file_path.split('/')[-1]

#Create Spark DataFrame from the input data for processing
hits_data = spark.read.csv(path,header=True, sep= '\t', inferSchema=True)
hits_data.createOrReplaceTempView('hits_data')

#Business Logic transforming the data using Spark SQL
# 1. Parition Data by IP Addresss and ordered by timestamp of the hits.
# 2. Update partitions referrer as the first referrer value for that IP.
# 3. Parse referrer URL to get HOST and QUERY informationself.
# 4. QUERY will provide us the SEARCH_KEYWORD using regex.
# 5. SUM of the Product_list field will give us the REVENUE for that search term.
# 6. This will be our resulting dataframe.
# 7. This job can now handle the load of bigger size files by distributing computing.
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

#Convert Resulting Spark DF to Pandas DF to get single csv file as output in an S3 bucket without using repartitioning
revenue_data.toPandas().to_csv(output_file_path, sep = '\t',index = False)

#Update Job Input parameter with Output File name which will be passed to API to be available for download.
response = client.update_job(
    JobName='process_data',
    JobUpdate={
        'Description': 'updating arguments',
        'Role': f'{role_name}',
        'Command': {
            'Name': 'glueetl',
            'ScriptLocation': 's3://{BUCKET_NAME}/Scripts/process_data_glue.py'
        },
        'DefaultArguments': {
            '--output-file-name': f'{output_file_name}'
            }
    }
)

job.commit()
