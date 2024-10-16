
# Extending the Application with a Custom Use-Case

This guide provides step-by-step instructions for adding a new use-case to the existing application. By following this process, you can integrate custom policies and decision services (e.g., IBM Operational Decision Manager (ODM) or Automated Decision Services (ADS)) into the application's workflow.

## Procedure to Add a New Use-Case

To extend the application with a new use-case, follow these steps:

1. **Create a New Directory**:  
   Add a new directory in the `data` folder named after your use-case.
   ```
   data/<your-use-case>/
   ```

2. **Add Policy Documents**:  
   In the `data/<your-use-case>/catalog` directory, upload a PDF containing the policies relevant to your use-case. These will be brought into the LLM context.

3. **Add Decision Service Descriptor**:  
   In the `data/<your-use-case>/tool_descriptors` directory, add a JSON file describing how to interface with your decision service. This allows the LLM to interact with your service.

4. **Deploy Your Decision Service (ODM)**:  
   If using ODM, you can place your decision application (ruleapp) in the `data/<your-use-case>/decisionapps` directory for automatic deployment by the application.

---

## Adding a Policy Document

To provide policy information for your use-case:

1. Place your policy document as a PDF in the following directory:  
   ```
   data/<your-use-case>/catalog
   ```

2. The LLM application will automatically bring this policy into context when handling the use-case.

---

## Registering Decision Services

To integrate decision services such as ODM or ADS:

### 1. Deploying the Decision Service

Your decision service (whether in ODM or ADS) must be deployed and exposed as a REST API. Below are examples of how decision service URLs would appear:

- **ODM example (running locally)**:  
  ```
  http://localhost:9060/DecisionService/hr_decision_service/1.0/number_of_timeoff_days/1.0
  ```

- **ADS example**:  
  ```
  https://<ads_host>:443/ads/runtime/api/v1/deploymentSpaces/embedded/decisions/<userid>/%2Fhrdecisionautomation%2Fhrdecisionservice%2FHRDecisionServiceDecisionService%2F1.0.0%2FHRDecisionServiceDecisionService-1.0.0.jar/operations/mainflow_flow/execute
  ```

Ensure that the decision service is accessible at the appropriate endpoint before proceeding.

---

### 2. Creating a Tool Descriptor

Once your decision service is deployed, you need to create a **Tool Descriptor**. This descriptor, in JSON format, will define the decision service's interface for the LLM application. Place the descriptor file in:  
```
data/<your-use-case>/tool_descriptors
```

The JSON file should follow this format:

```json
{
    "engine": "<odm or ads>",
    "toolName": "<name of the tool>",
    "toolDescription": "<description of the tool>",
    "toolPath": "<path to the deployed decision service>",
    "args": [
        {
            "argName": "<parameter name>",
            "argType": "<str, number, bool>",
            "argDescription": "<description of the parameter>"
        }
    ],
    "output": "<property of the returned object to be used as the answer>"
}
```

#### Example for ODM:

```json
{
    "engine": "odm",
    "toolName": "GetNumberOfVacationDaysPerYearInput",
    "toolDescription": "Retrieve the number of vacation days per year for a given employee and hiring date.",
    "toolPath": "/hr_decision_service/1.0/number_of_timeoff_days/1.0",
    "args": [
        {
            "argName": "employeeId",
            "argType": "str",
            "argDescription": "The employee's ID"
        },
        {
            "argName": "hiringDate",
            "argType": "str",
            "argDescription": "The employee's hiring date"
        }
    ],
    "output": "timeoffDays"
}
```

#### Example for ADS:

```json
{
    "engine": "ads",
    "toolName": "GetNumberOfVacationDaysPerYearInput",
    "toolDescription": "Retrieve the number of vacation days per year for a given employee and hiring date.",
    "toolPath": "%2Fhrdecisionautomation%2Fhrdecisionservice%2FHRDecisionServiceDecisionService%2F1.0.0%2FHRDecisionServiceDecisionService-1.0.0.jar/operations/mainflow_flow/execute",
    "args": [
        {
            "argName": "employeeId",
            "argType": "str",
            "argDescription": "The employee's ID"
        },
        {
            "argName": "hiringDate",
            "argType": "str",
            "argDescription": "The employee's hiring date"
        }
    ],
    "output": "timeoffDays"
}
```

---

## Deploying Ruleapps (ODM only)

If you are using ODM, the application can automatically deploy ruleapps stored in:  
```
data/<your-use-case>/decisionapps
```

You can also manually deploy the decision service using the ODM RES Console or ODM Decision Center. Ensure that the URL and path described in your tool descriptor match the deployed decision service.

