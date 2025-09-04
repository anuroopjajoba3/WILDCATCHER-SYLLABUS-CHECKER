# NECHE Compliance Checker Chatbot (NECHECker)

## Overview

NECHECker is a Flask-based web service that extracts structured course and instructor data from PDF and DOCX syllabi and verifies NECHE compliance. It leverages OpenAI’s gpt-3.5-turbo for intelligent information extraction, a Chroma vector store for semantic retrieval, and provides multiple upload options (single file, folder, or ZIP) with caching and concurrency support.

## Key Components

-   **Multi-format Extraction:** PDF (via `pdfplumber` + OCR fallback) and Word (`python-docx`) support.
-   **Chunking & Embeddings:** Text is split into overlapping chunks (`RecursiveCharacterTextSplitter`), embedded using `text-embedding-ada-002`, and stored in a local Chroma vector store.
-   **Semantic Retrieval:** Similarity search retrieves relevant syllabus sections for user queries.
-   **Asynchronous LLM Calls:** Non-blocking OpenAI requests for course information extraction and chat responses.
-   **Caching:** MD5-hashed document caches in a SQLite database (via SQLAlchemy) to avoid reprocessing.
-   **Multiple Upload Endpoints:**
    -   `/upload_pdf` – single PDF or DOCX file
    -   `/upload_folder` – batch upload of multiple files
    -   `/upload_zip` – ZIP archive extraction and processing with thread pool concurrency
-   **Interactive QA:** `/ask` endpoint uses a custom prompt template to answer user questions about syllabus content.
-   **Email Reporting:** `/email_report` endpoint sends HTML reports via Gmail SMTP (environment-configured credentials).
-   **Chat History & Memory:** Stores Q&A pairs and conversation context in JSON for deduplication and session persistence.

### Query Handling

-   **Input Validation and Caching:**  
    Incoming queries and file extractions are validated and cached. Chat history and conversation memory are stored in JSON files to reduce redundant processing.
-   **Similarity Search:**  
    When queries are made, relevant content is retrieved from the vector store.
-   **Custom Prompt Creation:**  
    Predefined prompt templates merge retrieved syllabus sections with a list of NECHE-related instructions.
-   **Response Generation:**  
    OpenAI’s gpt-3.5-turbo processes prompts to generate responses that indicate whether the syllabus is NECHE compliant or, if not, which required fields are missing.

### Post-Processing

-   **Compliance Verification:**  
    A dedicated function checks the extracted information against required NECHE elements and provides a compliance status along with details on missing fields.
-   **Response Delivery:**  
    Users receive quick, context-aware messages about the compliance status of their uploaded document along with options to view or download a detailed report.

## Architecture Diagram

## Setup and Installation

### Prerequisites

-   Python 3.12 (recommended) or Python 3.10-3.11
-   An OpenAI API key (obtained from [OpenAI](https://openai.com/))
-   Required Python packages (see requirements.txt for complete list)

## Creating an OpenAI API Key

To use OpenAI's GPT-3.5 turbo API, you need to create an API key from OpenAI's platform.

1. **Sign up or log in to OpenAI**:

    - Visit [OpenAI's website](https://platform.openai.com/signup/) and create an account or log in to your existing account.

2. **Create an API key**:
    - Navigate to the **API Keys** section under your OpenAI dashboard.
    - Click on "Create API Key."
    - Copy the generated API key and store it securely.

## Adding Credits to OpenAI Account

To ensure your API key has sufficient credits for usage:

1. **Log in to OpenAI**:

    - Visit [OpenAI's website](https://platform.openai.com/login) and log in to your account.

2. **Navigate to Billing**:

    - Go to the **Billing** section on the OpenAI dashboard.

3. **Add a payment method**:

    - Add your credit/debit card or other payment methods to your OpenAI account.

4. **Purchase Credits**:

    - In the billing section, choose a payment plan or purchase credits as needed.
    - Ensure you monitor your API usage to avoid exceeding your credits.

5. **Check Remaining Credits**:
    - Under **Usage** on the OpenAI dashboard, you can monitor your credit usage and remaining balance.

---

By following these steps, you can ensure your OpenAI API key is properly set up and has sufficient credits for smooth operation of your chatbot.

### Installation

1. Clone the repository:

```bash
git clone https://github.com/UNHM-TEAM-PROJECT/Fall2025-Team-Alpha.git
cd Fall2025-Team-Alpha
```

2. Create a virtual environment:

```bash
python -m venv venv

# On Mac/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file from the template:

```bash
cp .env.example .env
```

5. Edit the `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=your-openai-api-key-here
```

Alternatively, you can set it as an environment variable:

-   **Linux/MacOS**:
    bash
    export OPENAI_API_KEY="your-openai-api-key"
    echo $OPENAI_API_KEY # To verify the key is exported correctly
-   **Windows**:
    cmd
    set OPENAI_API_KEY="your-openai-api-key"
    echo %OPENAI_API_KEY% # To verify the key is exported correctly

---

## Usage

1. Run the chatbot:

```bash
python chatbot.py
```

2. Open your browser and navigate to:

```
http://127.0.0.1:5000/
```

# Deploying Chatbot to AWS

This guide provides step-by-step instructions for deploying applications on Amazon Web Services (AWS). It covers the entire process from account creation to application deployment using EC2 instances.

## Prerequisites

-   Basic knowledge of AWS services.
-   Installed tools:
    -   AWS CLI
    -   Python 3.12 (recommended) or 3.10+
    -   Virtual environment tools (e.g., `venv` or `virtualenv`)
    -   MobaXTerm or an SSH client for server access.

## Steps to Deploy

### 1. **Create an AWS Account**

1. Go to the [AWS website](https://aws.amazon.com/).
2. Click **"Create an AWS Account"**.
3. Follow the steps to sign up, including:
    - Adding payment information.
    - Verifying your email and phone number.
4. Log in to AWS using your credentials.

### 2. **Launch an EC2 Instance**

1. Go to the AWS Management Console and open the EC2 Dashboard.
2. Click Launch Instance.
3. Configure the instance:
    - Choose an Amazon Machine Image (AMI): Select Amazon Linux 2.
4. Select an instance type: Use t3.2xlarge or similar for performance.

5. Create a new key pair (.pem file) during the instance setup.
6. Download and save the .pem file securely on your local machine. This file will be used for SSH access.
7. Add storage: Allocate at least 100GB.

8. Configure security group to allow the following:

    - Open ports 22 (SSH) and 80 (HTTP).

9. Launch the instance.

### 3. **Start the EC2 Instance**

1. From EC2 Dashboard, select your instance
2. Click "Start Instance"
3. Wait for the instance state to become "Running"
4. Note the Public IPv4 address

### 4. **SSH Connection Setup**

1. Download MobaXterm on windows:

    - Visit the official MobaXterm website: https://mobaxterm.mobatek.net/.
    - Download the "Home Edition" (Installer version or Portable version).
    - Open the downloaded .exe file.
    - Follow the on-screen instructions to install the application.
    - Once installed, open MobaXterm from the Start Menu or Desktop Shortcut.

2. Click "Session" → "New Session"
3. Select "SSH"
4. Configure SSH session:
    - Enter Public IPv4 address in "Remote host"
    - Check "Specify username" and enter "ec2-user"
    - In "Advanced SSH settings", use "Use private key" and select your .pem file
5. Then you will be logged into AWS Linux terminal.

### 5. **Application Deployment**

1. In AWS Linux terminal, switch to root user:
   bash
   sudo su
2. Update system packages:
   bash
   sudo yum update -y
3. Install necessary tools:
   bash
   sudo yum install git -y
   sudo yum install python3-pip -y
4. Clone your repository from Github:
   bash
   git clone https://github.com/UNHM-TEAM-PROJECT/Fall2025-Team-Alpha.git
   cd Fall2025-Team-Alpha
5. Install project dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
6. Create a .env file and add your OpenAI API key:
   ```bash
   cp .env.example .env
   nano .env  # Add your API key
   ```
7. Run the Application:
   ```bash
   python3 chatbot.py
   ```
8. Ensure the application is running, and open any browser:

    - Navigate to `http://<public-ip>:5000` in your browser.


## Setting Up the Chatbot in VM

### Prerequisites

-   Access to the school’s VPN
-   Command prompt/terminal access
-   School credentials
-   GitHub account
-   Python 3 and pip3 installed

### Steps

1. **Connect to the School's VPN:**

    - Visit the [UNH VPN setup guide](https://td.usnh.edu/TDClient/60/Portal/KB/ArticleDet?ID=4787) and follow the instructions to set up the VPN.

2. **Access the School Server via SSH:**
    ```bash
    ssh username@whitemount.sr.unh.edu
    ```

-   Replace username with your school username.

-   Enter your school password when prompted.

3. **Generate an SSH Key:**
    ```bash
    ssh-keygen -t rsa -b 4096 -C "your-email@example.com"
    ```

-   Replace your-email@example.com with your actual email address.

-   Press Enter for all prompts to use default settings.

4. **Copy the SSH Public Key:**

    ```bash

    cat ~/.ssh/id_rsa.pub
    ```

-   Copy the output and add it to your GitHub account under **Settings > SSH and GPG keys > New SSH key**.

5. **Clone the Git Repository:**

    ```bash
    git clone git@github.com:UNHM-TEAM-PROJECT/Fall2025-Team-Alpha.git
    cd Fall2025-Team-Alpha
    ```

6. **Install Dependencies:**

    ```bash
    pip3 install -r requirements.txt
    ```

7. **Create and configure the .env file:**

    ```bash
    cp .env.example .env
    nano .env  # Add your OpenAI API key
    ```

8. **Run the Chatbot:**

    ```bash
    python3 chatbot.py
    ```

9. **Troubleshooting:**

-   If any packages are missing, install them manually:

    ```bash
    pip3 install package_name

    ```

-   If there are import errors, adjust the Python file paths as needed.
