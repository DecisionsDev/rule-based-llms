# Underwriting Rule Generation Workflow

This document provides visual diagrams of the complete underwriting workflow system.

## Complete Workflow Diagram

```mermaid
flowchart TD
    Start([User Request]) --> API[POST /process_policy_from_s3]

    API --> Input{Input Parameters}
    Input -->|Required| S3URL[S3 URL to Policy PDF]
    Input -->|Optional| PolicyType[Policy Type: insurance/loan/auto]
    Input -->|Recommended| BankID[Bank ID: chase/bofa/wells-fargo]
    Input -->|Optional| ContainerID[Container ID Override]

    S3URL --> Step0[Step 0: Parse S3 URL]
    PolicyType --> Step0
    BankID --> Step0

    Step0 --> ContainerGen{Container ID<br/>Provided?}
    ContainerGen -->|No| AutoGen[Auto-generate:<br/>bank_id-policy_type-underwriting-rules]
    ContainerGen -->|Yes| UseProvided[Use Provided Container ID]

    AutoGen --> Step01
    UseProvided --> Step01

    Step01[Step 0.1: Ensure Bank Exists] --> CheckBank{Bank Exists<br/>in Database?}
    CheckBank -->|No| CreateBank[Auto-create Bank Entry<br/>Normalized ID + Name]
    CheckBank -->|Yes| BankOK[Bank Ready]
    CreateBank --> Step02
    BankOK --> Step02

    Step02[Step 0.2: Ensure Policy Type Exists] --> CheckPolicy{Policy Type<br/>Exists?}
    CheckPolicy -->|No| CreatePolicy[Auto-create Policy Type<br/>Normalized ID + Name]
    CheckPolicy -->|Yes| PolicyOK[Policy Type Ready]
    CreatePolicy --> Step1
    PolicyOK --> Step1

    Step1[Step 1: Extract Text from Document] --> FormatDetect{Document<br/>Format?}
    FormatDetect -->|PDF| S3Read{S3 or Local?}
    FormatDetect -->|Excel| ExcelRead[Read Excel with pandas/openpyxl]
    FormatDetect -->|Word| WordRead[Read Word with python-docx]
    FormatDetect -->|Text| TextRead[Direct Text Read]

    ExcelRead --> ComputeHash
    WordRead --> ComputeHash
    TextRead --> ComputeHash
    S3Read -->|S3| ReadS3[Read PDF from S3 into Memory<br/>No Local Download]
    S3Read -->|Local| ReadLocal[Read from Local File]

    ReadS3 --> PyPDF2[PyPDF2: Extract Text]
    ReadLocal --> PyPDF2
    PyPDF2 --> ComputeHash

    ComputeHash[Compute SHA-256 Hash<br/>for Version Tracking] --> Step2[Step 2: Generate Extraction Queries]

    Step2 --> QueryType{Template or<br/>LLM Generated?}
    QueryType -->|Template| TemplateQ[Use Template Queries<br/>for Policy Type]
    QueryType -->|LLM| LLMGen[LLM Generates Custom Queries<br/>Based on Document]

    TemplateQ --> Step3
    LLMGen --> Step3

    Step3[Step 3: Extract Structured Data] --> TextractCheck{AWS Textract<br/>Available?}

    TextractCheck -->|Yes| TextractS3{S3 Document?}
    TextractS3 -->|Yes| TextractNative[Textract with S3Object<br/>No Download Required]
    TextractS3 -->|No| TextractLocal[Textract with Local File]

    TextractCheck -->|No| MockExtract[Mock Extraction<br/>LLM-based Text Analysis]

    TextractNative --> Step35
    TextractLocal --> Step35
    MockExtract --> Step35

    Step35[Step 3.5: Save Extraction Queries to DB] --> SaveQueries[Save to policy_extraction_queries:<br/>- query_text<br/>- response_text<br/>- confidence_score<br/>- document_hash]
    SaveQueries --> Step4

    Step4[Step 4: Generate Drools DRL Rules] --> RuleGen[LLM Generates:<br/>- DRL Rules<br/>- Decision Tables<br/>- Explanations]

    RuleGen --> Step45[Step 4.5: Save Extracted Rules to DB]

    Step45 --> ParseDRL2[Parse DRL Rules]
    ParseDRL2 --> TransformLLM[Transform to User-Friendly Text<br/>using OpenAI GPT-4]
    TransformLLM --> SaveExtracted[Save to extracted_rules:<br/>- rule_name<br/>- requirement (natural language)<br/>- category<br/>- document_hash]

    SaveExtracted --> Step46[Step 4.6: Generate Hierarchical Rules]

    Step46 --> HierarchicalAgent[HierarchicalRulesAgent<br/>Analyzes Policy with LLM]
    HierarchicalAgent --> GenerateTree[Generate Tree Structure:<br/>- Parent-child relationships<br/>- Unlimited nesting depth<br/>- Rule dependencies]
    GenerateTree --> SaveHierarchical[Save to hierarchical_rules:<br/>- rule_id (1.1.1)<br/>- parent_id<br/>- level, order_index<br/>- name, description<br/>- expected, confidence]

    SaveHierarchical --> Step47[Step 4.7: Generate Test Cases]

    Step47 --> TestCaseGen[TestCaseGenerator<br/>LLM Analyzes Policy + Rules]
    TestCaseGen --> GenerateTests[Generate 5-10 Test Cases:<br/>- Positive cases<br/>- Negative cases<br/>- Boundary cases<br/>- Edge cases]
    GenerateTests --> SaveTestCases[Save to test_cases:<br/>- test_case_name<br/>- description, category<br/>- applicant_data, policy_data<br/>- expected_decision<br/>- generation_method: llm/template]

    SaveTestCases --> Step5[Step 5: Automated Drools Deployment]

    Step5 --> TempDir[Create Temporary Directory]
    TempDir --> SaveDRL[Save DRL File]
    SaveDRL --> CreateKJar[Create KJar Structure<br/>Maven Project Layout]
    CreateKJar --> MavenBuild[Maven Build:<br/>mvn clean install]

    MavenBuild --> BuildSuccess{Build<br/>Success?}
    BuildSuccess -->|No| BuildFail[Status: Partial<br/>Manual Build Required]
    BuildSuccess -->|Yes| CopyFiles[Copy JAR & DRL to<br/>Temp Location for S3]

    CopyFiles --> CheckOrchestration{Container-Per-Ruleset<br/>Architecture?}

    CheckOrchestration -->|Yes| ContainerOrch[ContainerOrchestrator:<br/>Create Dedicated Container]
    ContainerOrch --> CreateDockerContainer[Create Docker/K8s Container:<br/>drools-{bank}-{policy}-rules<br/>Dedicated Port 8081+]
    CreateDockerContainer --> RegisterContainer[Register in rule_containers DB:<br/>- container_id<br/>- endpoint URL<br/>- platform: docker/k8s<br/>- status: deploying]

    CheckOrchestration -->|No| DeployKIE[Deploy to Shared KIE Server]

    RegisterContainer --> DeployToNewContainer[Deploy KJar to<br/>Dedicated Container]
    DeployToNewContainer --> UpdateContainerStatus[Update status: running<br/>Set health_status: healthy]

    DeployKIE --> ContainerExists{Container<br/>Exists?}
    ContainerExists -->|Yes| Dispose[Dispose Old Container]
    Dispose --> CreateNew[Create New Container<br/>with New Version]
    ContainerExists -->|No| CreateNew

    CreateNew --> DeploySuccess{Deployment<br/>Success?}
    UpdateContainerStatus --> DeploySuccess
    DeploySuccess -->|No| DeployFail[Status: Partial<br/>KJar Built, Deployment Failed]
    DeploySuccess -->|Yes| CleanTemp[Auto-Delete Temp Build Directory]

    CleanTemp --> Step6[Step 6: Upload Files to S3]

    Step6 --> UploadJAR[Upload JAR File<br/>s3://bucket/generated-rules/<br/>container_id/version/file.jar]
    UploadJAR --> UploadDRL[Upload DRL File<br/>s3://bucket/generated-rules/<br/>container_id/version/file.drl]

    UploadDRL --> CheckBank{Bank ID<br/>Provided?}
    CheckBank -->|Yes| GenerateExcel[Generate Excel Spreadsheet]
    CheckBank -->|No| SkipExcel[Skip Excel Generation]

    GenerateExcel --> ParseDRL[Parse DRL Rules:<br/>- Rule Names<br/>- Conditions<br/>- Actions<br/>- Priority]

    ParseDRL --> CreateExcel[Create Multi-Sheet Excel:<br/>1. Summary Sheet<br/>2. Rules Sheet<br/>3. Raw DRL Sheet]

    CreateExcel --> UploadExcel[Upload Excel to S3<br/>Filename: bank_id_policy_type_rules_timestamp.xlsx]

    UploadExcel --> CleanExcel[Delete Temp Excel File]
    SkipExcel --> FinalClean
    CleanExcel --> FinalClean[Clean Up All Temp Files]

    FinalClean --> Response[Return Response JSON]
    BuildFail --> Response
    DeployFail --> Response

    Response --> ResponseContent{Response Contains}
    ResponseContent --> RC1[container_id]
    ResponseContent --> RC2[status: completed/partial/failed]
    ResponseContent --> RC3[jar_s3_url]
    ResponseContent --> RC4[drl_s3_url]
    ResponseContent --> RC5[excel_s3_url]
    ResponseContent --> RC6[Detailed Steps Results]

    RC1 --> End([Workflow Complete])
    RC2 --> End
    RC3 --> End
    RC4 --> End
    RC5 --> End
    RC6 --> End

    style Start fill:#e1f5e1
    style End fill:#e1f5e1
    style Step1 fill:#e3f2fd
    style Step2 fill:#e3f2fd
    style Step3 fill:#e3f2fd
    style Step4 fill:#e3f2fd
    style Step5 fill:#e3f2fd
    style Step6 fill:#e3f2fd
    style GenerateExcel fill:#fff3e0
    style CreateExcel fill:#fff3e0
    style UploadExcel fill:#fff3e0
    style DeployKIE fill:#f3e5f5
    style CreateNew fill:#f3e5f5
```

## Policy Evaluation Workflow (Runtime)

```mermaid
flowchart TD
    EvalStart([POST /api/v1/evaluate-policy]) --> EvalInput{Input Data}

    EvalInput -->|Required| BankPolicyID[bank_id + policy_type_id]
    EvalInput -->|Required| ApplicantData[applicant: age, income, etc.]
    EvalInput -->|Optional| PolicyData[policy: coverage, etc.]

    BankPolicyID --> LookupContainer[Lookup Active Container<br/>from rule_containers table]
    ApplicantData --> LookupContainer
    PolicyData --> LookupContainer

    LookupContainer --> ContainerFound{Container<br/>Found?}
    ContainerFound -->|No| ErrorNoContainer[Error: No rules deployed<br/>for this bank+policy]
    ContainerFound -->|Yes| HealthCheck[Health Check Container]

    HealthCheck --> HealthOK{Health<br/>Status?}
    HealthOK -->|Unhealthy| ErrorUnhealthy[Error: Container unhealthy]
    HealthOK -->|Healthy| InvokeDrools[Invoke Drools KIE Server]

    InvokeDrools --> InsertFacts[Insert Facts:<br/>- Applicant<br/>- Policy<br/>- Decision object]
    InsertFacts --> FireRules[Fire All Rules]
    FireRules --> ExtractDecision[Extract Decision Object:<br/>- approved: true/false<br/>- reasons: list<br/>- riskCategory: 1-5]

    ExtractDecision --> GetHierarchical[Get Hierarchical Rules<br/>from database]
    GetHierarchical --> MapperCheck{Use<br/>Mapper?}

    MapperCheck -->|Yes| DroolsMapper[DroolsHierarchicalMapper<br/>Single Source of Truth]
    MapperCheck -->|No| SkipMapping[Skip Hierarchical Mapping]

    DroolsMapper --> Strategy1[Strategy 1: Check Rejection Reasons<br/>Does Drools mention this rule?]
    Strategy1 --> Strategy2[Strategy 2: Validate Known Fields<br/>Compare actual vs expected]
    Strategy2 --> Strategy3[Strategy 3: Overall Approval<br/>If approved + no reasons = all pass]
    Strategy3 --> Strategy4[Strategy 4: Derive Parent Status<br/>Parent fails if any child fails]

    Strategy4 --> MappedRules[Mapped Hierarchical Rules:<br/>- Each rule has passed: true/false<br/>- actual values from Drools<br/>- NO re-evaluation]

    MappedRules --> CalculateSummary[Calculate Summary:<br/>- total_rules<br/>- passed count<br/>- failed count<br/>- pass_rate %]

    SkipMapping --> BuildResponse
    CalculateSummary --> BuildResponse[Build Complete Response]

    BuildResponse --> ReturnJSON{Response Contains}
    ReturnJSON --> R1[decision: approved/rejected]
    ReturnJSON --> R2[hierarchical_rules: tree]
    ReturnJSON --> R3[rule_evaluation_summary]
    ReturnJSON --> R4[execution_time_ms]

    R1 --> EvalEnd([Return Response])
    R2 --> EvalEnd
    R3 --> EvalEnd
    R4 --> EvalEnd

    ErrorNoContainer --> EvalEnd
    ErrorUnhealthy --> EvalEnd

    style EvalStart fill:#e1f5e1
    style EvalEnd fill:#e1f5e1
    style DroolsMapper fill:#f3e5f5
    style Strategy1 fill:#f3e5f5
    style Strategy2 fill:#f3e5f5
    style Strategy3 fill:#f3e5f5
    style Strategy4 fill:#f3e5f5
    style MappedRules fill:#c5e1a5
    style CalculateSummary fill:#c5e1a5
```

## Database Schema

```mermaid
erDiagram
    banks ||--o{ rule_containers : "has many"
    banks ||--o{ extracted_rules : "has many"
    banks ||--o{ hierarchical_rules : "has many"
    banks ||--o{ policy_extraction_queries : "has many"
    banks ||--o{ test_cases : "has many"

    policy_types ||--o{ rule_containers : "has many"
    policy_types ||--o{ extracted_rules : "has many"
    policy_types ||--o{ hierarchical_rules : "has many"
    policy_types ||--o{ policy_extraction_queries : "has many"
    policy_types ||--o{ test_cases : "has many"

    hierarchical_rules ||--o{ hierarchical_rules : "parent-child"

    test_cases ||--o{ test_case_executions : "has many"

    rule_containers ||--o{ container_deployment_history : "has many"
    rule_containers ||--o{ rule_requests : "has many"

    banks {
        varchar bank_id PK
        varchar bank_name
        text description
        varchar contact_email
        boolean is_active
        timestamp created_at
    }

    policy_types {
        varchar policy_type_id PK
        varchar policy_name
        text description
        varchar category
        boolean is_active
        timestamp created_at
    }

    rule_containers {
        serial id PK
        varchar container_id UK
        varchar bank_id FK
        varchar policy_type_id FK
        varchar platform
        varchar endpoint
        varchar status
        varchar health_status
        varchar version
        boolean is_active
        varchar s3_policy_url
        varchar s3_jar_url
        varchar s3_drl_url
        varchar s3_excel_url
        timestamp deployed_at
        timestamp stopped_at
    }

    extracted_rules {
        serial id PK
        varchar bank_id FK
        varchar policy_type_id FK
        varchar rule_name
        text requirement
        varchar category
        varchar source_document
        varchar document_hash
        boolean is_active
        timestamp created_at
    }

    hierarchical_rules {
        serial id PK
        varchar bank_id FK
        varchar policy_type_id FK
        varchar rule_id
        int parent_id FK
        int level
        int order_index
        varchar name
        text description
        text expected
        text actual
        decimal confidence
        boolean passed
        varchar document_hash
        varchar source_document
        timestamp created_at
    }

    policy_extraction_queries {
        serial id PK
        varchar bank_id FK
        varchar policy_type_id FK
        text query_text
        text response_text
        int confidence_score
        varchar extraction_method
        varchar document_hash
        varchar source_document
        timestamp created_at
    }

    container_deployment_history {
        serial id PK
        int container_id FK
        varchar action
        varchar version
        text changes_description
        varchar deployed_by
        timestamp deployed_at
    }

    rule_requests {
        serial id PK
        int container_id FK
        varchar request_id
        jsonb request_payload
        jsonb response_payload
        int execution_time_ms
        int status_code
        text error_message
        timestamp created_at
    }

    test_cases {
        serial id PK
        varchar bank_id FK
        varchar policy_type_id FK
        varchar test_case_name
        text description
        varchar category
        int priority
        jsonb applicant_data
        jsonb policy_data
        varchar expected_decision
        text[] expected_reasons
        int expected_risk_category
        varchar document_hash
        boolean is_auto_generated
        varchar generation_method
        boolean is_active
        timestamp created_at
    }

    test_case_executions {
        serial id PK
        int test_case_id FK
        varchar execution_id
        varchar container_id
        varchar actual_decision
        text[] actual_reasons
        int actual_risk_category
        jsonb response_payload
        boolean test_passed
        text pass_reason
        text fail_reason
        int execution_time_ms
        timestamp executed_at
    }
```

## Multi-Tenant Container Architecture

```mermaid
graph TB
    subgraph "Bank: Chase"
        C1[chase-insurance-underwriting-rules]
        C2[chase-loan-underwriting-rules]
        C3[chase-auto-underwriting-rules]
    end

    subgraph "Bank: Bank of America"
        B1[bofa-insurance-underwriting-rules]
        B2[bofa-loan-underwriting-rules]
        B3[bofa-auto-underwriting-rules]
    end

    subgraph "Bank: Wells Fargo"
        W1[wellsfargo-insurance-underwriting-rules]
        W2[wellsfargo-loan-underwriting-rules]
        W3[wellsfargo-auto-underwriting-rules]
    end

    subgraph "Drools KIE Server"
        KIE[KIE Server<br/>Multiple Isolated Containers]
    end

    C1 --> KIE
    C2 --> KIE
    C3 --> KIE
    B1 --> KIE
    B2 --> KIE
    B3 --> KIE
    W1 --> KIE
    W2 --> KIE
    W3 --> KIE

    style C1 fill:#4fc3f7
    style C2 fill:#4fc3f7
    style C3 fill:#4fc3f7
    style B1 fill:#81c784
    style B2 fill:#81c784
    style B3 fill:#81c784
    style W1 fill:#ffb74d
    style W2 fill:#ffb74d
    style W3 fill:#ffb74d
    style KIE fill:#f06292
```

## S3 Storage Organization

```mermaid
graph TD
    S3[S3 Bucket: uw-data-extraction]

    S3 --> Policies[/policies/]
    S3 --> Rules[/generated-rules/]

    Policies --> P1[chase/insurance_2025.pdf]
    Policies --> P2[bofa/loan_policy.pdf]
    Policies --> P3[wellsfargo/auto_policy.pdf]

    Rules --> Container1[/chase-insurance-underwriting-rules/]
    Rules --> Container2[/bofa-loan-underwriting-rules/]
    Rules --> Container3[/wellsfargo-auto-underwriting-rules/]

    Container1 --> V1[/20250104.143000/]
    V1 --> V1JAR[chase-insurance...jar]
    V1 --> V1DRL[chase-insurance...drl]
    V1 --> V1XLSX[chase_insurance_rules_20250104_143000.xlsx]

    Container2 --> V2[/20250104.150000/]
    V2 --> V2JAR[bofa-loan...jar]
    V2 --> V2DRL[bofa-loan...drl]
    V2 --> V2XLSX[bofa_loan_rules_20250104_150000.xlsx]

    Container3 --> V3[/20250104.153000/]
    V3 --> V3JAR[wellsfargo-auto...jar]
    V3 --> V3DRL[wellsfargo-auto...drl]
    V3 --> V3XLSX[wellsfargo_auto_rules_20250104_153000.xlsx]

    style S3 fill:#ff6f00
    style Policies fill:#ffa726
    style Rules fill:#ffa726
    style V1XLSX fill:#66bb6a
    style V2XLSX fill:#66bb6a
    style V3XLSX fill:#66bb6a
```

## Excel Spreadsheet Structure

```mermaid
graph LR
    Excel[Excel Workbook:<br/>bank_id_policy_type_rules_timestamp.xlsx]

    Excel --> Sheet1[Summary Sheet]
    Excel --> Sheet2[Rules Sheet]
    Excel --> Sheet3[Raw DRL Sheet]

    Sheet1 --> S1C1[Bank ID: chase]
    Sheet1 --> S1C2[Policy Type: insurance]
    Sheet1 --> S1C3[Container ID: chase-insurance...]
    Sheet1 --> S1C4[Version: 20250104.143000]
    Sheet1 --> S1C5[Generated Date: 2025-01-04 14:30:00]
    Sheet1 --> S1C6[Total Rules: 12]

    Sheet2 --> S2C1[Rule Name]
    Sheet2 --> S2C2[Priority Salience]
    Sheet2 --> S2C3[Conditions When]
    Sheet2 --> S2C4[Actions Then]
    Sheet2 --> S2C5[Attributes]

    Sheet3 --> S3C1[Complete DRL Content<br/>for Technical Reference]

    style Excel fill:#4caf50
    style Sheet1 fill:#81c784
    style Sheet2 fill:#aed581
    style Sheet3 fill:#c5e1a5
```

## Update/Replacement Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Workflow
    participant Drools
    participant S3

    User->>API: POST /process_policy_from_s3<br/>bank_id=chase, policy_type=insurance
    API->>Workflow: Generate container_id:<br/>chase-insurance-underwriting-rules

    Note over Workflow: Process Steps 1-4<br/>Extract, Analyze, Generate Rules

    Workflow->>Drools: Check if container exists:<br/>chase-insurance-underwriting-rules

    alt Container Exists
        Drools-->>Workflow: Container found (version: v1)
        Workflow->>Drools: Dispose old container (v1)
        Drools-->>Workflow: Disposed successfully
    end

    Workflow->>Drools: Create new container (version: v2)
    Drools-->>Workflow: Container created with v2

    Workflow->>S3: Upload JAR (v2)
    Workflow->>S3: Upload DRL (v2)
    Workflow->>S3: Upload Excel (v2)

    S3-->>Workflow: All files uploaded

    Note over S3: Both v1 and v2 files<br/>preserved in S3<br/>for audit history

    Note over Drools: Only v2 active<br/>in KIE Server

    Workflow->>API: Return result with S3 URLs
    API->>User: Response:<br/>- container_id<br/>- jar_s3_url<br/>- drl_s3_url<br/>- excel_s3_url
```

## System Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI[Web UI / Swagger / Postman]
        CURL[cURL / Scripts]
    end

    subgraph "API Layer"
        Flask[Flask REST API<br/>Port 9000]
        Swagger[Swagger UI<br/>/rule-agent/docs]
    end

    subgraph "Workflow Orchestration"
        UW[UnderwritingWorkflow]
        PA[PolicyAnalyzerAgent]
        RG[RuleGeneratorAgent]
        EE[ExcelRulesExporter]
    end

    subgraph "External Services"
        Textract[AWS Textract<br/>Document Analysis]
        S3Svc[AWS S3<br/>Storage Service]
        LLM[LLM Service<br/>Watsonx/OpenAI/Ollama]
    end

    subgraph "Drools Components"
        DD[DroolsDeploymentService]
        Maven[Maven Build]
        KIE[Drools KIE Server<br/>Port 9060]
    end

    subgraph "Storage"
        S3[(S3 Bucket:<br/>uw-data-extraction)]
        TempFS[Temporary File System<br/>Auto-Cleanup]
    end

    UI --> Flask
    CURL --> Flask
    Flask --> Swagger
    Flask --> UW

    UW --> PA
    UW --> RG
    UW --> EE
    UW --> DD

    PA --> LLM
    RG --> LLM

    UW --> Textract
    UW --> S3Svc

    DD --> Maven
    Maven --> KIE

    S3Svc --> S3
    Textract --> S3
    DD --> TempFS
    EE --> TempFS

    S3 --> |JAR/DRL/Excel| S3Svc

    style Flask fill:#4fc3f7
    style UW fill:#81c784
    style LLM fill:#ffb74d
    style KIE fill:#f06292
    style S3 fill:#ff6f00
    style EE fill:#66bb6a
```

## Key Features

### 1. Auto-Create Bank & Policy Type (NEW!)
- **Step 0.1-0.2**: Automatically creates missing banks and policy types
- Prevents foreign key violation errors
- ID normalization: "Chase" → "chase", "Life Insurance" → "life-insurance"
- Idempotent: checks existence first, creates only if needed
- Auto-generates human-readable names and descriptions

### 2. Multi-Format Document Support (NEW!)
- **PDF**: PyPDF2 + AWS Textract
- **Excel**: pandas/openpyxl
- **Word**: python-docx
- **Text**: direct read
- Auto-detects format and selects appropriate extractor
- SHA-256 hash for version tracking

### 3. Hierarchical Rules Generation (NEW!)
- **Step 4.6**: LLM generates tree-structured rules
- Unlimited nesting depth with parent-child relationships
- Typical output: 5 top-level rules, 87 total rules
- Stored in `hierarchical_rules` table with self-referential parent_id
- Includes confidence scores from LLM (0.0-1.0)

### 4. Database Persistence (NEW!)
- **Step 3.5**: Saves extraction queries + Textract responses
- **Step 4.5**: Saves user-friendly extracted rules
- **Step 4.6**: Saves hierarchical rules tree
- Linked by document hash for version tracking
- Multi-tenant isolation via bank_id + policy_type_id

### 5. User-Friendly Rule Transformation (NEW!)
- Technical DRL rules → Natural language using OpenAI GPT-4
- Example: `WHEN: age < 18` → "Applicant must be 18 years or older"
- Stored in `extracted_rules` table with categories
- Frontend-ready for non-technical users

### 6. Drools Hierarchical Mapper (NEW!)
- **Single source of truth**: Uses Drools decision, NO re-evaluation
- 4 intelligent mapping strategies:
  1. Check rejection reasons for rule mentions
  2. Validate known fields against Drools data
  3. Use overall approval status
  4. Derive parent status from children
- Maps Drools decision → Hierarchical rules with pass/fail
- Returns rule evaluation summary (total, passed, failed, pass_rate)

### 7. Container-Per-Ruleset Architecture
- Each bank+policy gets dedicated Drools container
- Complete isolation, independent scaling, version control
- Dynamic creation via ContainerOrchestrator
- Registered in `rule_containers` database table
- Health monitoring and status tracking
- Example:
  - Port 8080: Default shared Drools (backward compat)
  - Port 8081: drools-chase-insurance-rules
  - Port 8082: drools-bofa-loan-rules

### 8. Zero Persistent Local Storage
- All files use temporary directories with automatic cleanup
- Input documents read directly from S3 into memory
- Maven builds in temp directories (auto-deleted after completion)
- Generated files (JAR, DRL, Excel) uploaded to S3 and then deleted locally

### 9. Multi-Tenant Isolation
- Separate containers per bank and policy type
- Format: `{bank_id}-{policy_type}-underwriting-rules`
- Examples:
  - `chase-insurance-underwriting-rules`
  - `bofa-loan-underwriting-rules`
  - `wellsfargo-auto-underwriting-rules`

### 10. Excel Export
- Automatically generated for each deployment (when bank_id provided)
- Filename includes bank and policy type: `{bank_id}_{policy_type}_rules_{timestamp}.xlsx`
- Three sheets: Summary, Parsed Rules, Raw DRL
- Uploaded to S3 alongside JAR and DRL files

### 11. Container Update Strategy
- Detects existing containers
- Disposes old version before creating new
- Preserves version history in S3
- Only latest version active in KIE Server

### 12. Flexible LLM Support
- OpenAI GPT-4 (primary for rule generation and transformation)
- Watsonx.ai
- IBM BAM
- Ollama (local)
- Template queries (no LLM required)

### 13. AWS Integration
- Native S3 integration for document storage
- AWS Textract for intelligent data extraction
- Fallback to PyPDF2 + LLM when Textract unavailable
- Pre-signed URLs for secure file access (24h expiration)

### 14. Automated Test Case Generation ✨ NEW!
- **Step 4.7**: LLM generates comprehensive test cases during policy processing
- 5-10 test cases per policy covering all scenarios
- Four categories: positive, negative, boundary, edge_case
- Stored in `test_cases` table with expected results
- Execution tracking in `test_case_executions` table
- Returned in GET /api/v1/policies with `include_test_cases=true`
- Template-based fallback when LLM fails

---

## Complete Workflow Steps Summary

### Policy Processing Workflow (10 Steps)

**Step 0**: Parse S3 URL and auto-generate container ID
- Format: `{bank_id}-{policy_type}-underwriting-rules`

**Step 0.1**: Ensure Bank Exists ✨ NEW!
- Check if bank exists in database
- Auto-create with normalized ID if missing
- Prevents foreign key violations

**Step 0.2**: Ensure Policy Type Exists ✨ NEW!
- Check if policy type exists in database
- Auto-create with normalized ID if missing
- Prevents foreign key violations

**Step 1**: Extract Text from Document ✨ ENHANCED!
- Multi-format support: PDF, Excel, Word, Text
- Auto-detect format
- Compute SHA-256 hash for versioning

**Step 2**: Generate Extraction Queries
- LLM analyzes document
- Generates custom queries based on content
- Identifies key sections and rule categories

**Step 3**: Extract Structured Data
- AWS Textract query-based extraction
- Returns data with confidence scores
- Fallback to LLM if Textract unavailable

**Step 3.5**: Save Extraction Queries to Database ✨ NEW!
- Save to `policy_extraction_queries` table
- Links queries to responses with confidence
- Document hash for version tracking

**Step 4**: Generate Drools DRL Rules
- LLM converts extracted data to DRL
- Generates decision tables
- Creates Excel format rules

**Step 4.5**: Save Extracted Rules to Database ✨ NEW!
- Parse DRL to extract individual rules
- Transform to user-friendly text using OpenAI GPT-4
- Save to `extracted_rules` table with categories

**Step 4.6**: Generate Hierarchical Rules ✨ NEW!
- LLM analyzes policy and generates rule tree
- Parent-child relationships, unlimited nesting
- Save to `hierarchical_rules` table
- Typical output: 87 rules in hierarchy

**Step 4.7**: Generate Test Cases ✨ NEW!
- LLM analyzes policy text, extracted rules, and hierarchical rules
- Generates 5-10 comprehensive test scenarios
- Covers positive, negative, boundary, and edge cases
- Save to `test_cases` table with expected results
- Template-based fallback if LLM fails

**Step 5**: Automated Drools Deployment
- Create KJar structure (Maven project)
- Build with Maven: `mvn clean install`
- Option 1: Deploy to dedicated container (container-per-ruleset)
- Option 2: Deploy to shared KIE server
- Register in `rule_containers` database

**Step 6**: Upload Files to S3
- Upload JAR, DRL, Excel to S3
- Generate pre-signed URLs (24h)
- Update container registry with S3 URLs
- Clean up temporary files

### Policy Evaluation Workflow (Runtime)

**Step 1**: Receive Application Data
- bank_id, policy_type_id
- applicant data (age, income, etc.)
- policy data (coverage, etc.)

**Step 2**: Lookup and Route to Container
- Query `rule_containers` table
- Find active container for bank+policy
- Health check container
- Resolve endpoint URL

**Step 3**: Invoke Drools Rule Engine
- Insert facts: Applicant, Policy, Decision
- Fire all rules
- Extract decision: approved/rejected, reasons, risk category

**Step 4**: Map to Hierarchical Rules ✨ NEW!
- Use DroolsHierarchicalMapper (single source of truth)
- No re-evaluation, only mapping
- Apply 4 intelligent strategies
- Mark each rule as passed/failed
- Extract actual values from Drools data

**Step 5**: Calculate Summary
- Total rules evaluated
- Passed count, failed count
- Pass rate percentage

**Step 6**: Return Complete Response
- Decision (approved/rejected)
- Hierarchical rules with pass/fail status
- Rule evaluation summary
- Execution time

---

## Recent Features (Highlighted with ✨)

1. **Auto-Create Bank & Policy Type** - Prevents FK violations
2. **Multi-Format Document Support** - PDF, Excel, Word, Text
3. **Database Persistence** - Steps 3.5, 4.5, 4.6, 4.7 save to DB
4. **Hierarchical Rules Generation** - Tree-structured rules with LLM
5. **User-Friendly Rule Transformation** - DRL → Natural language
6. **Drools Hierarchical Mapper** - Single source of truth, no re-evaluation
7. **Container-Per-Ruleset** - Dedicated Drools containers per tenant
8. **Document Hash Versioning** - SHA-256 tracking across all tables
9. **Automated Test Case Generation** - LLM-powered test scenarios with execution tracking

---

## File References

**Main Workflow:**
- [rule-agent/UnderwritingWorkflow.py](rule-agent/UnderwritingWorkflow.py) - Complete orchestration

**LLM Agents:**
- [rule-agent/PolicyAnalyzerAgent.py](rule-agent/PolicyAnalyzerAgent.py) - Query generation
- [rule-agent/RuleGeneratorAgent.py](rule-agent/RuleGeneratorAgent.py) - DRL generation
- [rule-agent/HierarchicalRulesAgent.py](rule-agent/HierarchicalRulesAgent.py) - Tree generation
- [rule-agent/TestCaseGenerator.py](rule-agent/TestCaseGenerator.py) - Test case generation

**Rule Services:**
- [rule-agent/DroolsService.py](rule-agent/DroolsService.py) - Drools integration
- [rule-agent/DroolsHierarchicalMapper.py](rule-agent/DroolsHierarchicalMapper.py) - Intelligent mapping

**Database:**
- [rule-agent/DatabaseService.py](rule-agent/DatabaseService.py) - All DB operations
- [db/migrations/001_create_extracted_rules_table.sql](db/migrations/001_create_extracted_rules_table.sql)
- [db/migrations/002_create_policy_extraction_queries_table.sql](db/migrations/002_create_policy_extraction_queries_table.sql)
- [db/migrations/003_create_hierarchical_rules_table.sql](db/migrations/003_create_hierarchical_rules_table.sql)
- [db/migrations/004_create_test_cases_table.sql](db/migrations/004_create_test_cases_table.sql)

**API:**
- [rule-agent/ChatService.py](rule-agent/ChatService.py) - REST endpoints
- [rule-agent/swagger.yaml](rule-agent/swagger.yaml) - API documentation

**Documentation:**
- [AUTO_CREATE_BANK_POLICY.md](AUTO_CREATE_BANK_POLICY.md) - Auto-creation feature
- [COMPLETE_HIERARCHICAL_RULES_SUMMARY.md](COMPLETE_HIERARCHICAL_RULES_SUMMARY.md) - Hierarchical rules
- [DROOLS_MAPPER_IMPLEMENTATION.md](DROOLS_MAPPER_IMPLEMENTATION.md) - Mapper logic
- [CONTAINER_PER_RULESET.md](CONTAINER_PER_RULESET.md) - Container architecture
- [TEST_CASES_FEATURE.md](TEST_CASES_FEATURE.md) - Test case generation and execution
