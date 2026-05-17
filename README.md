<h4> Setting up and running the code: </h4>
1. clone the repository locally
<br>2. Run the command setx GEMINI_API_KEY "your gemini api key" to set your gemini api key as a system environment variable
<br>3. open terminal and navigate to invoice_processing -> python_extraction
<br>4. in case some packages are missing, run the command <b>pip install -r requirements.txt</b> in terminal/bash
<br>5. run multiple_main.py once
<br>6. run <b>uvicorn multiple_main:app</b> to get the server up and running for the API
<br>7. open http://127.0.0.1:8000/docs in a browser to run the API
<br>8. In swagger, upload the invoice PDFs and execute
<br>9. For ease of reading the extracted information, navigate to the created exports folder and check the latest excel file.
<br><br>
  
_AI Usage in development:_ Used ChatGPT free tier to set up a basic structure of the system and code.s
