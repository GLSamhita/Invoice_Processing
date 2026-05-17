<h4> Setting up and running the code: </h4>
\n1. clone the repository locally
\n2. Run the command setx GEMINI_API_KEY "<your gemini api key here>" to set your gemini api key as a system environment variable
\n3. open terminal and navigate to invoice_processing -> python_extraction
\n4. in case some packages are missing, run the command ```pip install -r requirements.txt``` in terminal/bash
\n5. run multiple_main.py once
6. run ```uvicorn multiple_main:app``` to get the server up and running for the API
7. open http://127.0.0.1:8000/docs in a browser to run the API
8. In swagger, upload the invoice PDFs and execute
9. For ease of reading the extracted information, navigate to the created exports folder and check the latest excel file.


<h4> Flow of program: </h4>
The backend system takes in digitally generated GST invoices or scanned GST invoices and extracts important fields into a json and an excel sheet.


_AI Usage in development:_ Used ChatGPT free tier to set up a basic structure of the system and code.s
