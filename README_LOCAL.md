
# Running with Ollama (Local)
To run the demo locally using Ollama, refer to the [Ollama Setup Guide](#ollama-setup-guide).

## Installation Instructions
### Install Ollama
[Ollama](https://ollama.ai/) allows you to run open-source large language models, such as Mistral AI, locally.

Ollama bundles model weights, configuration, and data into a single package, defined by a Modelfile.

It optimizes setup and configuration details, including GPU usage.

1. [Download and run](https://ollama.ai/download) the app
2. Once Ollma is up and running, you should download a model. For this sample we'll used `mistral` model.

For a complete list of supported models and model variants, see the [Ollama model library](http://ollama.ai/library).

3. From command line, fetch the llava model.
   
```shell
ollama pull mistral
```

When the app is running, all models are automatically served on [localhost:11434](http://localhost:11434)

> In some OS configuration you should [allow additional web origins to access Ollama](https://github.com/ollama/ollama/blob/main/docs/faq.md#how-can-i-allow-additional-web-origins-to-access-ollama)

> This demonstration has been tested with `mistral` model. You can used another model but we cannot garantee this will worked correctly.

### Clone the code
1. Open a new terminal
```shell
git clone https://github.com/DecisionsDev/rule-based-llms.git
cd rule-based-llms
```

### Setup variable

Since we’re running this demo with Ollama locally we will used the ollama.env settings.

Copy the `ollama.env` file to llm.env so that the demonstration will used this mode.

```shell
cp ollama.env llm.env
```

### Launch the docker topology

1. Open a new terminal
2. Build the docker demonstration 
```shell
docker-compose build
```
Once the build process completes

3. Run the demonstration
```shell
docker-compose up
```
This will run the ODM for Developpers docker images in conjonction with the sample web application.
Wait
4. Wait a few minutes until you see the message `` * Running on all addresses (0.0.0.0)```
5. Then  you are ready to open a browser to this url : http://localhost:8000


> Notes: 
> If you are already running ODM somewhere, you need to set-up the following environment variables:
>```sh
> export ODM_SERVER_URL=<ODM Runtime URL>
> export ODM_USERNAME=<ODM user, default odmAdmin>
> export ODM_PASSWORD=<ODM user password, default odmAdmin>
> ```
> And change the docker-compose.yml file accordingly. 


> If you want to run this demonstration with ADS instead of Operation Decision Manager see this [documentation](README_ADS.md)



# License
The files in this repository are licensed under the [Apache License 2.0](LICENSE).

# Copyright
© Copyright IBM Corporation 2024.
