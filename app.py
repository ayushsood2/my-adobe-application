import os
import boto3
from flask import Flask,flash,request,redirect,send_file,render_template,Response, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
import time
import sys
import subprocess

thismodule = sys.modules[__name__]
app = Flask(__name__, template_folder='templates')
UPLOAD_FOLDER = 'uploads/'
DOWNLOAD_FOLDER = 'output_file/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
BUCKET_NAME = 'serverless-flask-dev-serverlessdeploymentbucket-1wdb3e4zzsp3'

s3 = boto3.client('s3')
glue = boto3.client('glue')
global job_id
thismodule.input_file_name = ''
global output_file_name

# Upload API
@app.route("/uploadfile", methods=['GET', 'POST'])
def upload_file():
    print(request)
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            print('no file')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            print('no filename')
            return redirect(request.url)
        else:
            # filename = secure_filename(file.filename)
            # print(filename)
            tsv = request.files['file']
            if tsv:
                thismodule.input_file_name = secure_filename(tsv.filename)
                print(input_file_name)
                tsv.save("/tmp/{}".format(input_file_name))
                s3.upload_file(
                    Bucket = BUCKET_NAME,
                    Filename="/tmp/{}".format(input_file_name),
                    Key = f'input_file/{input_file_name}'
                )
                msg = f"Upload Done at {BUCKET_NAME}/input_file/{input_file_name} ! "
            print("saved file successfully")

      # send file name as parameter to downlad
            return render_template('upload_complete.html',msg = msg)
            # return redirect('/downloadfile/'+ filename)
    return render_template('file_upload_to_s3.html')

#Process API
@app.route("/processfile", methods = ['GET', 'POST'])
def process_file():
    print(request)
    if request.method == 'POST':
        print('Starting Glue job for processing')
        job_response = glue.start_job_run(
                JobName="serverless-flask-dev-ProcessData",
                Arguments={
                    # Specify any arguments needed based on bucket and keys (e.g. input/output S3 locations)
                    "--JOB_NAME": "serverless-flask-dev-ProcessData",
                    "--input_file_path": f"s3://{BUCKET_NAME}/input_file/{input_file_name}",
                    "--job-bookmark-option": "job-bookmark-enable",
                    "--output-file-path": ""
                }
            )
        thismodule.job_id =  job_response['JobRunId']
        print(job_id)
        return redirect(url_for('check_job_status'))

    return render_template('processing_file.html')

#Get Status API
@app.route("/checkjobstatus", methods = ['GET', 'POST'])
def check_job_status():
    print(request)
    if request.method == 'GET':
        response = glue.get_job_run(
            JobName = 'serverless-flask-dev-ProcessData',
            RunId = job_id
            )
        status = response['JobRun']['JobRunState']
        if status == 'SUCCEEDED':
            print('Job Finished Successfully')
            return redirect(url_for('download_file'))
        else:
            print(f"job is still running with {status}")
            # time.sleep(20)
            return render_template('processing_file.html')
            # return redirect(url_for('check_job_status'))
    return render_template('processing_file.html')

@app.route("/downloadfile", methods = ['GET', 'POST'])
def download_file():
    thismodule.output_file_name= glue.get_job(JobName= 'process_data')['Job']['DefaultArguments']['--output-file-name']
    print(output_file_name)
    msg = f"File Processed and uploaded at {BUCKET_NAME}/output_file/{output_file_name} ! "
    return render_template('downloading_file.html', msg = msg)

@app.route("/download", methods = ['GET', 'POST'])
def download():
    s3_client = boto3.resource('s3')
    file_name = f'output_file/{output_file_name}'
    file_path = f'/tmp/{output_file_name}'
    print(f'output is {output_file_name}')
    output = s3_client.meta.client.download_file(BUCKET_NAME,file_name , file_path)
    return send_file(file_path, as_attachment= True, attachment_filename=output_file_name)

@app.route('/', methods=['GET', 'POST'])
def homepage():
    return redirect(url_for('upload_file'))

if __name__ == "__main__":
    app.run()
