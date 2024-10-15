
# Running with Watsonx.ai (Watsonx)
To run the demo locally using IBM Watsonx.ai, follow the instructions below. For more information, refer to the [Watsonx AI](https://www.ibm.com/products/watsonx-ai) product page.

## Installation Instructions

### Setup IBM Watsonx.ai

1. **Create an IBM Watsonx.ai Account**: 
   - Follow [this guide](https://dataplatform.cloud.ibm.com/docs/content/wsj/getting-started/overview-wx.html?context=wx&audience=wdp) to set up your IBM Cloud instance.

2. **Instantiate Watsonx.ai Service**: 
   - Once your account is created, instantiate a Watsonx.ai service from your IBM account.

3. **Generate an API Key**:
   - In your IBM Watsonx console, navigate to the `Profile and settings` section and generate an API key. 
   - [Learn how to generate an API key](https://eu-gb.dataplatform.cloud.ibm.com/docs/content/wsj/admin/admin-apikeys.html?context=wx&audience=wdp).
     * The API key will follow this format: `cpd-apikey-{username}-{timestamp}` where `{username}` is your IBMid and `{timestamp}` indicates when the key was generated.

4. **Create a Project**: 
   - Create a project within your IBM Watsonx account. Refer to [this guide](https://dataplatform.cloud.ibm.com/docs/content/wsj/manage-data/manage-projects.html?context=wx&audience=wdp).
   - Make a note of the project ID. To get the project ID:
     1. Open your project in Watsonx.ai.
     2. Click the **Manage** tab.
     3. Copy the Project ID from the **Details** section under the **General** tab.

### Clone the code
1. Open a new terminal
```shell
git clone https://github.com/DecisionsDev/rule-based-llms.git
cd rule-based-llms
```

### Setup variables

Since this demo runs with Watsonx.ai in the cloud, we’ll use the watsonx.env configuration.


1. Copy the `watsonx.env` file to llm.env so that the demonstration will used this mode.

```shell
cp watsonx.env llm.env
```


2. Edit the llm.env file and replace the placeholders with your specific information:
You should adjust the variables :
   * WATSONX_APIKEY=<your watsonx.ai API Key>
   * WATSONX_PROJECT_ID=<your watsonx.ai Project ID>
   * WATSONX_URL=https://us-south.ml.cloud.ibm.com (Depending of your location)
   

### Launch the Demo


Once the environment is set up, you are ready to run the demo. Follow the instructions on [how to launch the demo with docker](README.md#launch-the-docker-topology)


# License
The files in this repository are licensed under the [Apache License 2.0](LICENSE).

# Copyright
© Copyright IBM Corporation 2024.
