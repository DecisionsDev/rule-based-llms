# Decision Services

This directory contains some examples of Decision Services that can be deployed in ODM Decision Server. 

## How to run ODM

Use the script `start_odm.sh` to start a basic ODM topology with a Decision Center and a Decision Server. 

ODM Decision Server needs to be started before deploying a Decision Service into it. 

When ODM is started, use the URL http://localhost:9060⁠ to display a welcome page that lists all the ODM components. You can also directly access the individual components through the following URLs:

| Component	| URL	| Username	| Password
---
| Decision Server console⁠	| http://localhost:9060/res⁠	| odmAdmin	| odmAdmin
| Decision Server Runtime⁠	| http://localhost:9060/DecisionService⁠	| odmAdmin	| odmAdmin
| Decision Center Business console⁠	| http://localhost:9060/decisioncenter⁠	| odmAdmin	| odmAdmin
| Decision Runner⁠	| http://localhost:9060/DecisionRunner⁠	| odmAdmin	| odmAdmin
| Sample application⁠	| http://localhost:9060/loan-server⁠		


# How to deploy a Decision Service to ODM

Use ```deploy_ruleapp_to_odm.sh``` script to deploy a ruleapp to ODM. 
Example: 

```sh
export ODM_SERVER_URL=http://localhost:9060
./deploy_to_odm.sh hr_decision_service/hr_decision_service/ruleapp/hr_decision_service.jar
```

