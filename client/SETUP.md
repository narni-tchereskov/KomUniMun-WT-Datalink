# Setup

## 1. Python

You need to have python installed, this is necessary to build the project.

## 2. Utilize pyinstaller

You will need to use pyinstaller to compile the code, run the following command:

pip install pyinstaller

## 3. Build the project

Run the following command to compile the project:

pyinstaller --name "WT-Datalink" --noconsole --onefile --paths "." --collect-all "uvicorn" --collect-all "starlette" --add-data "src/infrastructure/templates;src/infrastructure/templates" src/drivers/handler.py

## 4. Configure the output

Copy the resulting .exe file in the dist folder to a folder of your preference.
Inside this folder, create the auth and logs folders.

## 5. Generate your private key

Inside the project's auth folder, the key_generator.py file exists, configure the password and run the file.
Your client_private.pem file will have been created inside the same folder, now copy it to the auth folder where your .exe file is.
The public key must be used by the server, follow the server setup in order to utilize it.
