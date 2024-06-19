{
    "engine" :  "ads",
    "toolName" : "GetNumberOfVacationDaysPerYearInput",
    "toolDescription" : "retrieve the number of vacation days per year for a given employee and his hiring date.",
    "toolPath" :  "%2Fhrdecisionautomation%2Fhrdecisionservice%2FHRDecisionServiceDecisionService%2F1.0.0%2FHRDecisionServiceDecisionService-1.0.0.jar/operations/mainflow_flow/execute",
    "args" : [
        {
            "argName" : "employeeId", "argType": "str", "argDescription": "the employee name"
        },
        {
            "argName" : "hiringDate", "argType": "str", "argDescription": "the hiring date"
        }
    ],
    "output" : "timeoffDays"
}
