# Comprehensive Install Guide

This guide provides step-by-step instructions to set up this project on macOS and Windows(coming soon!).

## Table of Contents
- [macOS Installation](#macos-installation)
  - [Step 1: Install Homebrew](#step-1-install-homebrew)
  - [Step 2: Install Colima](#step-2-install-colima)
  - [Step 3: Install Docker and Docker Compose](#step-3-install-docker-and-docker-compose)
  - [Step 4: Start Colima](#step-4-start-colima)
  - [Step 5: Clone the Repository](#step-5-clone-the-repository)
  - [Step 6: Setup IBM watsonx.ai](#step-6-setup-ibm-watsonxai)
  - [Step 7: Setup the Project](#step-7-setup-the-project)
  - [Step 8: Run the Project](#step-8-run-the-project)

## macOS Installation

### Step 1: Install Homebrew
Homebrew is a package manager for macOS that simplifies the installation of software.

To install Homebrew, open your Terminal and run the following command:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After the installation is complete, verify that Homebrew is installed:

```bash
brew --version
```

### Step 2: Install Colima
Colima is a lightweight container runtime for macOS that works with Docker.

To install Colima, run:

```bash
brew install colima
```

If you have an Apple Silicon (M1/M2) Mac, you need to install Rosetta:

```bash
softwareupdate --install-rosetta
```

### Step 3: Install Docker and Docker Compose
Docker is essential for containerization, and Docker Compose helps in managing multi-container applications.

To install Docker and Docker Compose, run:

```bash
brew install docker docker-compose
```

### Step 4: Start Colima
Now, you can start Colima with the desired configuration. If you have an Intel Mac, run:

```bash
colima start --cpu 4 --memory 8
```

For Apple Silicon (M1/M2) Macs, run:

```bash
colima start --cpu 4 --memory 8 --vm-type=vz --vz-rosetta
```

### Step 5: Clone the Repository
Now that your environment is set up, you can clone the `rule-based-llms` repository. If you don't have Git installed, you can do so by running:

```bash
brew install git
```

Then, clone the repository and navigate into the project directory:

```bash
git clone https://github.com/DecisionsDev/rule-based-llms.git
cd rule-based-llms
```

### Step 6: Setup IBM watsonx.ai

1. **Create an IBM watsonx.ai account**  
   Visit the [IBM watsonx.ai](https://www.ibm.com/products/watsonx-ai) page and follow the links to set up a Cloud instance.

2. **Generate an API key**  
   In your IBM Cloud account, go to `Profile and settings` and generate an API key.

3. **Instantiate a watsonx.ai service**  
   From your IBM Cloud account, create a new watsonx.ai service instance.

4. **Edit the `wastonx.env` file**  
   Open the `wastonx.env` file and uncomment the lines to configure your environment:

   ```plaintext
   # Uncomment the lines and change the values.
   # LLM_TYPE=WATSONX
   # WATSONX_URL=<your watsonx.ai URL> # example value = https://us-south.ml.cloud.ibm.com/
   # WATSONX_APIKEY=<your watsonx.ai API Key>
   # WATSONX_PROJECT_ID=<your watsonx.ai Project ID>
   # Uncomment one of these tested models
   # WATSONX_MODEL_NAME=ibm/granite-13b-chat-v2
   # WATSONX_MODEL_NAME=mistralai/mixtral-8x7b-instruct-v01
   ```

### Step 7: Setup the Project

To set up the project, you need to run the following commands:

1. **Start ODM (IBM Operational Decision Manager)**  
   This command starts the ODM service required for the project:

   ```sh
   docker-compose --profile odm up
   ```

   *Note: If `docker-compose` doesn't work, try using `docker compose` without the hyphen.*

2. **Build the Application**  
   Build the necessary Docker containers for development:

   ```sh
   docker-compose --profile dev build
   ```

### Step 8: Run the Project

Once everything is set up, you can run the project by executing:

```sh
docker-compose --profile dev up
```

After the project is running, you can access the chatbot at:

```plaintext
http://localhost:8080
```

Try asking the following question to interact with the chatbot:

```plaintext
John Doe is an Acme Corp employee who has been hired on November 1st, 1999. How many vacation days the employee John Doe can take each year?
```

---

Your environment should now be fully set up and ready for development and testing. If you encounter any issues, please refer to the documentation or raise an issue in the GitHub repository.


## Windows Installation (Coming Soon!)

### Step 1: Install Rancher Desktop
Rancher Desktop provides an easy way to run Kubernetes and containerized applications on Windows.

1. Download the Rancher Desktop installer from the official website: [Rancher Desktop](https://rancherdesktop.io/)
2. Run the installer and follow the on-screen instructions to complete the installation.
3. After the installation, launch Rancher Desktop and follow the initial setup steps.

Rancher Desktop includes Docker support, so no additional installation for Docker is required.

---

