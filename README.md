# Welcome to Cloud based File Processing Application 

Completely serverless flask, docker and AWS based web application with deployment scripts, architecture diagrams and complete installation and run steps.

# Information about the workflow

1. This application is based on `Serverless` Framework and deploys the whole application through `cloudformation` templates.
2. Once the deployment completes and necessary infrastructure is ready on `AWS`, you will get a deployed  `API URL` to access the application.
3. It takes input of valid `tsv` file from user through a `flask` based web UI.
4. Once user provides the file and clicks on `upload` button, application uploads the file to an `S3` Bucket. It also paritions the data through `year, month, day and hour` and converts it to parquet format. It also creates a `Glue` catalog for the raw input data which can be accessed in `AWS Athena`.
5. Then it redirects to the file ready to process page and ask for user input through a button.
6. Once user clicks the button, Upload Files API is called which in back end triggers a Spark job in GLUE which runs the python script in `Scripts` directory.
7. This API request will keep refreshing itself until Glue job finishes processing.
8. This `Spark ETL Glue` job runs the business logic and after processing, copies the processed file to S3 output directory specified and does a call back to the Web UI to signal completion.
9. API will take the output file name and sends message to the web users with the location of processed file in S3 and also creates a `glue` catalog for the processed data which can be accessed in `Athena`.
9. Users now also have the option to download the processed file on their local system as well.
10. Quicksight dashboard is created to analyse the input raw data and processed output data. Link for that is provided below.



# Prerequisite
1. AWS must be configured on your machine. Run `aws configure` to check.
2. `Git` should be installed and configured to clone the repo.
3. Since `serverless` framework dockerizes everything, `docker daemon` must be running. 
4. `nodejs` must be installed to package node modules and install `serverless` framework.

# Installation Steps

1. Clone the branch : `git clone https://github.com/ayushsood2/my-adobe-application.git`
2. `cd my-adobe-application`
2. Install serverless : `npm install -g serverless`
3. Install wsgi plugin for `requirements.txt` : `npm install --save-dev serverless-wsgi serverless-python-requirements `
4. Donwload awswrangler lamda layer  from here:  https://github.com/awslabs/aws-data-wrangler/releases/download/2.11.0/awswrangler-layer-2.11.0-py3.6.zip. Rename it to `awswrangler.zip` and copy it in Scripts folder.
5. `sls deploy` to deploy it.
# Quicksight Dashboard URL:

https://us-west-2.quicksight.aws.amazon.com/sn/dashboards/e4da48b9-b333-4022-aa1c-1e867abd7a75


# Architecture

![Image](https://github.com/ayushsood2/my-adobe-application/blob/main/Adobe%20Challenge%20Architecture.jpeg)

