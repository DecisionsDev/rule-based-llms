## HR Decision Service

This directory contains the ODM and ADS versions of a HR Decision Service which compute the number
of timeoff days and employee can take. 

This directory contains:
   * hr_decision_service_xom: the XOM of the ODM version of the HR Decision Service
   * hr_decision_service: the ODM version of the HR Decision Service
   * HRDecisionService.zip: the ADS version of the HR Decision Service

The policy document corresponding to this use-case can be found in ```<root>/data/hrservice/catalog/Benefits Summary US 2024 TimeOff.pdf```.    

### Instructions for ODM

The Decision Service needs to be deployed to a running Rule Execution Server and accessible through a REST API. 

Provided you have ODM installed and running, you can import the XOM and the decision project in Rule Designer and you can deploy the Decision Service. 

A pre-built ruleapp is provided. You can deploy it with the following command:

```
cd ..
./deploy_ruleapp_to_odm.sh hr_decision_service/hr_decision_service/ruleapp/hr_decision_service.jar 
```

### Instructions for ADS

The decision service project ZIP can be imported in ADS. From there, you can deploy it to the Decision Runtime. 

### Registering the Decision Service to the application

See instructions on how to register the decision service to the LLM application in the README at the root folder of this application. 

